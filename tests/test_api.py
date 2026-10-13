import pytest
from fastapi.testclient import TestClient

from threatguard.api import create_app
from threatguard.config import Settings

KEY = "test-only-key-" + "x" * 40
HEADERS = {"X-API-Key": KEY}


@pytest.fixture
def client(artifacts):
    root, *_ = artifacts
    with TestClient(create_app(Settings(root / "models", KEY))) as c:
        yield c


def test_endpoints(client, example):
    assert client.get("/health").status_code == 200
    assert client.get("/model/info", headers=HEADERS).json()["data_source"] == "synthetic"
    response = client.post("/predict", headers=HEADERS, json={"records": [example]})
    assert response.status_code == 200
    assert response.json()["predictions"][0]["label"] in {"0", "1"}
    assert client.get("/metrics", headers=HEADERS).json()["predicted_rows"] == 1
    assert client.get("/monitor/report", headers=HEADERS).json()["report"] is None
    assert client.post("/monitor/drift", headers=HEADERS, json={"records": [example] * 30}).status_code == 200
    assert client.get("/monitor/report", headers=HEADERS).json()["report"]["rows"] == 30


@pytest.mark.parametrize(
    "path,method",
    [
        ("/model/info", "get"),
        ("/predict", "post"),
        ("/metrics", "get"),
        ("/monitor/drift", "post"),
        ("/monitor/report", "get"),
    ],
)
def test_auth_failures(client, path, method):
    kwargs = {"json": {"records": []}} if method == "post" else {}
    assert getattr(client, method)(path, **kwargs).status_code == 401
    assert getattr(client, method)(path, headers={"X-API-Key": "wrong"}, **kwargs).status_code == 401


@pytest.mark.parametrize(
    "mode", ["missing", "extra", "wrong_type", "boolean", "huge", "empty", "oversize", "nested"]
)
def test_invalid_prediction_inputs(client, example, mode):
    row = example.copy()
    if mode == "missing":
        row.pop("dur")
    elif mode == "extra":
        row["label"] = 1
    elif mode == "wrong_type":
        row["dur"] = "1.2"
    elif mode == "boolean":
        row["dur"] = True
    elif mode == "huge":
        row["dur"] = 1e20
    elif mode == "nested":
        row["proto"] = {"x": 1}
    records = [] if mode == "empty" else [row] * (129 if mode == "oversize" else 1)
    assert client.post("/predict", headers=HEADERS, json={"records": records}).status_code == 422


def test_null_feature_allowed(client, example):
    example["dur"] = None
    example["proto"] = None
    assert client.post("/predict", headers=HEADERS, json={"records": [example]}).status_code == 200


def test_bad_json_and_body_size(client):
    assert client.post("/predict", headers=HEADERS, content="{broken").status_code == 422
    assert client.post("/predict", headers=HEADERS, content="x" * 300000).status_code == 413


def test_rate_limit(artifacts):
    root, *_ = artifacts
    with TestClient(create_app(Settings(root / "models", KEY, rate_limit=1))) as c:
        assert c.get("/metrics", headers=HEADERS).status_code == 200
        assert c.get("/metrics", headers=HEADERS).status_code == 429


def test_missing_model_and_settings(tmp_path):
    with pytest.raises(ValueError):
        Settings(tmp_path, "short")
    with pytest.raises(ValueError):
        Settings(tmp_path, "x" * 257)
    with TestClient(create_app(Settings(tmp_path, KEY))) as c:
        assert c.get("/health").status_code == 503
        assert c.get("/model/info", headers=HEADERS).status_code == 503


def test_small_drift_batch(client, example):
    assert client.post("/monitor/drift", headers=HEADERS, json={"records": [example]}).status_code == 422
