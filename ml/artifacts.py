import hashlib
import json
import os
import tempfile
from pathlib import Path

import joblib
import sklearn


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def save_model(pipeline, metadata, directory: Path):
    directory.mkdir(parents=True, exist_ok=True)
    version = metadata["version"]
    version_dir = directory / version
    version_dir.mkdir(exist_ok=False)
    model = version_dir / "model.joblib"
    joblib.dump(pipeline, model)
    metadata["model_sha256"] = sha256(model)
    (version_dir / "metadata.json").write_text(
        json.dumps(metadata, indent=2, allow_nan=False), encoding="utf-8"
    )
    # CURRENT is atomically published only after all artifacts are complete.
    if metadata["quality_gate"]["passed"]:
        fd, name = tempfile.mkstemp(dir=directory, prefix="current-")
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(version)
        os.replace(name, directory / "CURRENT")
    return version_dir


def load_model(directory: Path):
    root = directory.resolve()
    version = (root / "CURRENT").read_text(encoding="utf-8").strip()
    if not version or any(c not in "0123456789abcdef-" for c in version):
        raise ValueError("Invalid artifact version")
    folder = (root / version).resolve()
    if folder.parent != root:
        raise ValueError("Invalid artifact path")
    model = folder / "model.joblib"
    meta = json.loads((folder / "metadata.json").read_text(encoding="utf-8"))
    if meta["schema_version"] != 1 or meta["version"] != version:
        raise ValueError("Unsupported artifact schema")
    if not meta["quality_gate"]["passed"]:
        raise ValueError("Model failed quality gate")
    if meta["versions"]["scikit-learn"] != sklearn.__version__:
        raise ValueError("Use the same scikit-learn version as training")
    if sha256(model) != meta["model_sha256"]:
        raise ValueError("Artifact integrity check failed")
    # joblib is executable deserialization: directory is administrator-controlled.
    # Hash detects corruption only. Never accept external/user-uploaded artifacts.
    pipeline = joblib.load(model)
    return pipeline, meta
