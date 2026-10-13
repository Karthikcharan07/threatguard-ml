import json

import numpy as np
import pytest

from ml.artifacts import load_model
from ml.data import load_dataset
from ml.synthetic import generate
from ml.train import train
from threatguard.drift import baseline, detect


def test_real_columns_and_leakage(artifacts):
    root, _, metadata, _ = artifacts
    x, y, report = load_dataset(root / "synthetic.csv")
    assert {"id", "label", "attack_cat"}.isdisjoint(x)
    assert y.nunique() == 2 and report["target"] == "label"
    assert metadata["data_source"] == "synthetic"
    assert metadata["training_rows"] < len(x)


@pytest.mark.parametrize(
    "mode",
    [
        "missing_target",
        "missing_feature",
        "bad_numeric",
        "inf",
        "target_null",
        "unknown_column",
        "invalid_label",
    ],
)
def test_data_validation(tmp_path, mode):
    data = generate(100)
    if mode == "missing_target":
        data = data.drop(columns=["label", "attack_cat"])
    elif mode == "missing_feature":
        data = data.drop(columns=["proto"])
    elif mode == "bad_numeric":
        data["dur"] = "not numeric"
    elif mode == "inf":
        data.loc[0, "dur"] = np.inf
    elif mode == "target_null":
        data.loc[0, "label"] = np.nan
    elif mode == "unknown_column":
        data["sneaky_target_copy"] = data["label"]
    elif mode == "invalid_label":
        data["label"] = data["label"].astype(float)
        data.loc[0, "label"] = 0.5
    csv = tmp_path / "input.csv"
    data.to_csv(csv, index=False)
    with pytest.raises(ValueError):
        load_dataset(csv)


def test_unseen_categories_and_missing_values(artifacts):
    root, data, metadata, _ = artifacts
    pipeline, _ = load_model(root / "models")
    x = data[list(metadata["feature_schema"])].iloc[:3].copy()
    x["proto"] = "never_seen"
    x["dur"] = np.nan
    assert pipeline.predict(x).shape == (3,)


def test_model_integrity_check(artifacts, tmp_path):
    import shutil

    root, _, metadata, _ = artifacts
    shutil.copytree(root / "models", tmp_path / "models")
    with (tmp_path / "models" / metadata["version"] / "model.joblib").open("ab") as f:
        f.write(b"corrupted")
    with pytest.raises(ValueError, match="integrity"):
        load_model(tmp_path / "models")


def test_reproducibility_and_failed_gate(artifacts, tmp_path):
    root, _, first, _ = artifacts
    second, _ = train(
        root / "synthetic.csv",
        tmp_path / "models",
        tmp_path / "reports",
        provenance="synthetic",
        trees=20,
        min_f1=0,
        min_recall=0,
    )
    assert first["evaluation"] == second["evaluation"]
    assert first["baseline"] == second["baseline"]
    _, folder = train(
        root / "synthetic.csv",
        tmp_path / "failed",
        tmp_path / "badreport",
        provenance="synthetic",
        trees=20,
        min_f1=1,
        min_recall=1,
    )
    assert not json.loads((folder / "metadata.json").read_text())["quality_gate"]["passed"]
    assert not (tmp_path / "failed" / "CURRENT").exists()
    train(
        root / "synthetic.csv",
        tmp_path / "models",
        tmp_path / "badreport",
        provenance="synthetic",
        trees=20,
        min_f1=1,
        min_recall=1,
    )
    assert (tmp_path / "models" / "CURRENT").read_text() == second["version"]


def test_external_partition_and_overlap(tmp_path):
    a, b = generate(200, 42), generate(100, 43)
    import pandas as pd

    pd.concat([b, a.iloc[:5]], ignore_index=True).to_csv(tmp_path / "test.csv", index=False)
    a.to_csv(tmp_path / "train.csv", index=False)
    m, _ = train(
        tmp_path / "train.csv",
        tmp_path / "models",
        tmp_path / "reports",
        test_csv=tmp_path / "test.csv",
        trees=10,
        min_f1=0,
        min_recall=0,
    )
    assert m["test_overlap_removed"] == 5 and m["evaluation"]["test_rows"] == 100


def test_multiclass(tmp_path):
    data = generate(150)
    data.loc[data["label"] == 1, "attack_cat"] = np.resize(["A", "B"], int(data["label"].sum()))
    data.to_csv(tmp_path / "data.csv", index=False)
    m, _ = train(
        tmp_path / "data.csv",
        tmp_path / "models",
        tmp_path / "reports",
        target="attack_cat",
        trees=10,
        min_f1=0,
        min_recall=0,
    )
    assert m["threshold"] is None and len(m["classes"]) == 3


def test_drift_stable_and_shifted():
    x = generate(2000).drop(columns=["id", "label", "attack_cat"])
    ref = baseline(x)
    assert not detect(ref, x)["drift_detected"]
    shifted = x.copy()
    shifted["dur"] += 100
    shifted["proto"] = "unknown"
    report = detect(ref, shifted)
    assert report["features"]["dur"]["drifted"] and report["features"]["proto"]["drifted"]


def test_missingness_drift():
    x = generate(100).drop(columns=["id", "label", "attack_cat"])
    ref = baseline(x)
    x["dur"] = np.nan
    assert detect(ref, x)["features"]["dur"]["drifted"]
