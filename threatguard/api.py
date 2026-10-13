import hmac
import threading
import time
from collections import deque
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import Depends, FastAPI, Header, HTTPException
from starlette.responses import JSONResponse

from ml.artifacts import load_model
from ml.evaluate import predict_labels

from .config import Settings
from .drift import detect
from .validation import Batch, validate_records


class BodyLimit:
    """Bound bytes even for chunked requests before JSON parsing."""

    def __init__(self, app, limit):
        self.app, self.limit = app, limit

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        chunks, total = [], 0
        while True:
            message = await receive()
            if message["type"] == "http.disconnect":
                return
            total += len(message.get("body", b""))
            if total > self.limit:
                return await JSONResponse({"detail": "Request body too large"}, status_code=413)(
                    scope, receive, send
                )
            chunks.append(message)
            if not message.get("more_body", False):
                break
        index = 0

        async def replay():
            nonlocal index
            if index < len(chunks):
                message = chunks[index]
                index += 1
                return message
            return await receive()

        await self.app(scope, replay, send)


def create_app(settings=None):
    settings = settings or Settings.from_env()
    state = {
        "pipeline": None,
        "metadata": None,
        "ready": False,
        "requests": 0,
        "predicted_rows": 0,
        "drift_checks": 0,
        "last_drift": None,
    }
    lock = threading.Lock()
    calls = deque()

    @asynccontextmanager
    async def lifespan(app):
        try:
            pipeline, metadata = load_model(settings.model_dir)
            state.update(pipeline=pipeline, metadata=metadata, ready=True)
        except Exception:
            # Fail readiness without exposing paths, artifact internals, or tracebacks.
            state["ready"] = False
        yield

    app = FastAPI(title="ThreatGuard ML", version="1.0.0", lifespan=lifespan)
    app.add_middleware(BodyLimit, limit=settings.max_body_bytes)

    @app.exception_handler(500)
    async def safe_error(request, exc):
        return JSONResponse({"detail": "Internal processing error"}, status_code=500)

    def protected(x_api_key: str | None = Header(default=None)):
        if (
            x_api_key is None
            or len(x_api_key) > 256
            or not hmac.compare_digest(x_api_key.encode(), settings.api_key.encode())
        ):
            raise HTTPException(401, "Valid X-API-Key required")
        now = time.monotonic()
        # Single global authenticated-client bucket: bounded memory; no spoofable IP dependency.
        with lock:
            while calls and calls[0] <= now - 60:
                calls.popleft()
            if len(calls) >= settings.rate_limit:
                raise HTTPException(429, "Rate limit exceeded", headers={"Retry-After": "60"})
            calls.append(now)
            state["requests"] += 1

    def ready():
        if not state["ready"]:
            raise HTTPException(503, "No approved local model available")
        return state["metadata"]

    @app.get("/health")
    def health():
        return JSONResponse(
            {"status": "ready" if state["ready"] else "not_ready"}, status_code=200 if state["ready"] else 503
        )

    auth = [Depends(protected)]

    @app.get("/model/info", dependencies=auth)
    def info():
        m = ready()
        return {
            k: m[k]
            for k in (
                "version",
                "data_source",
                "target",
                "classes",
                "threshold",
                "feature_schema",
                "evaluation",
                "quality_gate",
                "threshold_policy",
            )
        }

    @app.post("/predict", dependencies=auth)
    def predict(batch: Batch):
        m = ready()
        x = validate_records(batch.records, m["feature_schema"], settings.max_batch)
        labels, probabilities = predict_labels(state["pipeline"], x, m["target"], m["threshold"])
        with lock:
            state["predicted_rows"] += len(x)
        return {
            "model_version": m["version"],
            "data_source": m["data_source"],
            "predictions": [
                {
                    "label": str(label),
                    "probabilities": dict(zip(m["classes"], map(float, probs), strict=True)),
                }
                for label, probs in zip(labels, probabilities, strict=True)
            ],
        }

    @app.get("/metrics", dependencies=auth)
    def metrics():
        with lock:
            return {k: state[k] for k in ("requests", "predicted_rows", "drift_checks", "ready")}

    @app.post("/monitor/drift", dependencies=auth)
    def monitor(batch: Batch):
        m = ready()
        x = validate_records(batch.records, m["feature_schema"], settings.max_batch)
        if len(x) < settings.min_drift_rows:
            raise HTTPException(422, f"Drift monitoring needs at least {settings.min_drift_rows} rows")
        report = detect(m["baseline"], x)
        report.update(model_version=m["version"], timestamp=datetime.now(timezone.utc).isoformat())
        with lock:
            state["last_drift"] = report
            state["drift_checks"] += 1
        return report

    @app.get("/monitor/report", dependencies=auth)
    def monitor_report():
        ready()
        with lock:
            return {"report": state["last_drift"], "persistence": "In-memory, per process; resets on restart"}

    return app
