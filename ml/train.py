import argparse
import importlib.metadata
import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path

from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder

from threatguard.drift import baseline

from .artifacts import save_model, sha256
from .data import CATEGORICAL, load_dataset, row_hashes
from .evaluate import evaluate


def train(
    train_csv,
    model_dir,
    report_dir,
    test_csv=None,
    target=None,
    seed=42,
    provenance="local-unverified",
    threshold=0.5,
    min_f1=0.6,
    min_recall=0.6,
    trees=100,
):
    if not (0 < threshold < 1 and 0 <= min_f1 <= 1 and 0 <= min_recall <= 1 and 10 <= trees <= 500):
        raise ValueError("Invalid threshold, quality threshold, or tree count")
    x, y, data_report = load_dataset(Path(train_csv), target)
    target = data_report["target"]
    if target != "label" and threshold != 0.5:
        raise ValueError("Threshold applies only to binary label classification")
    hashes = row_hashes(x)
    # Keep unique feature/target pairs; keep conflicting labels together via groups.
    keep = ~((hashes + ":" + y).duplicated())
    duplicates = int((~keep).sum())
    x, y, hashes = x.loc[keep], y.loc[keep], hashes.loc[keep]
    overlap = 0
    if test_csv:
        if Path(train_csv).resolve() == Path(test_csv).resolve():
            raise ValueError("Training and testing files must differ")
        xt, yt, test_report = load_dataset(Path(test_csv), target)
        if set(xt) != set(x):
            raise ValueError("Training/testing feature schemas differ")
        xt = xt[x.columns]
        ht = row_hashes(xt)
        keep_test = ~ht.isin(set(hashes)) & ~(ht + ":" + yt).duplicated()
        overlap = int(ht.isin(set(hashes)).sum())
        xt, yt = xt.loc[keep_test], yt.loc[keep_test]
        split_method = "external test partition; training-overlapping and duplicate test rows excluded"
    else:
        unique = ~hashes.duplicated()
        train_groups, test_groups = train_test_split(
            hashes.loc[unique], test_size=0.25, random_state=seed, stratify=y.loc[unique]
        )
        mask = hashes.isin(set(train_groups))
        xt, yt = x.loc[~mask], y.loc[~mask]
        x, y = x.loc[mask], y.loc[mask]
        split_method = "seeded 75/25 stratified feature-group split"
        test_report = {"rows": len(xt)}
    if len(xt) < 10 or y.nunique() < 2 or not set(yt).issubset(set(y)):
        raise ValueError("Insufficient independent test rows or unseen test labels")
    if row_hashes(x).isin(set(row_hashes(xt))).any():
        raise ValueError("Overlapping train/test features")
    numeric = [c for c in x if c not in CATEGORICAL]
    categorical = [c for c in x if c in CATEGORICAL]
    pre = ColumnTransformer(
        [
            ("numeric", SimpleImputer(strategy="median", keep_empty_features=True), numeric),
            (
                "categorical",
                Pipeline(
                    [
                        ("impute", SimpleImputer(strategy="constant", fill_value="__MISSING__")),
                        ("encode", OneHotEncoder(handle_unknown="ignore", sparse_output=True)),
                    ]
                ),
                categorical,
            ),
        ]
    )
    pipeline = Pipeline(
        [
            ("preprocess", pre),
            (
                "classifier",
                RandomForestClassifier(
                    n_estimators=trees,
                    max_depth=20,
                    min_samples_leaf=2,
                    class_weight="balanced",
                    random_state=seed,
                    n_jobs=1,
                ),
            ),
        ]
    )
    pipeline.fit(x, y)  # only training partition reaches fit
    scores = evaluate(pipeline, xt, yt, target, threshold)
    gate = {
        "min_f1": min_f1,
        "min_recall": min_recall,
        "passed": scores["f1"] >= min_f1 and scores["recall"] >= min_recall,
    }
    version = uuid.uuid4().hex
    provenance_values = {"synthetic", "unsw-nb15", "local-unverified"}
    if provenance not in provenance_values:
        raise ValueError("Invalid provenance")
    metadata = {
        "schema_version": 1,
        "version": version,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "data_source": provenance,
        "provenance_note": "Dataset origin is operator-declared; file hashes identify bytes, not authenticity.",
        "dataset_sha256": sha256(Path(train_csv)),
        "test_dataset_sha256": sha256(Path(test_csv)) if test_csv else None,
        "seed": seed,
        "model_parameters": {
            "n_estimators": trees,
            "max_depth": 20,
            "min_samples_leaf": 2,
            "class_weight": "balanced",
            "random_state": seed,
            "n_jobs": 1,
        },
        "target": target,
        "classes": pipeline.classes_.astype(str).tolist(),
        "threshold": threshold if target == "label" else None,
        "threshold_policy": "Fixed before evaluation (default 0.5); not tuned on held-out test data.",
        "feature_schema": {c: "categorical" if c in CATEGORICAL else "numeric" for c in x},
        "baseline": baseline(x),
        "training_rows": len(x),
        "training_class_distribution": {str(k): int(v) for k, v in y.value_counts().items()},
        "preprocessing": "Train-only median imputation; categorical constant imputation + one-hot with unknown ignore.",
        "split": split_method,
        "training_duplicates_removed": duplicates,
        "test_overlap_removed": overlap,
        "original_test_inspection": test_report,
        "data_inspection": data_report,
        "evaluation": scores,
        "quality_gate": gate,
        "versions": {p: importlib.metadata.version(p) for p in ["scikit-learn", "pandas", "numpy", "joblib"]},
    }
    folder = save_model(pipeline, metadata, Path(model_dir))
    report_path = Path(report_dir)
    report_path.mkdir(parents=True, exist_ok=True)
    (report_path / "evaluation.json").write_text(
        json.dumps(metadata, indent=2, allow_nan=False), encoding="utf-8"
    )
    return metadata, folder


def main():
    parser = argparse.ArgumentParser(description="Train binary or attack-category Random Forest")
    parser.add_argument("--train-csv", default=os.getenv("TG_TRAIN_CSV"))
    parser.add_argument("--test-csv", default=os.getenv("TG_TEST_CSV"))
    parser.add_argument("--target", choices=["label", "attack_cat"])
    parser.add_argument("--model-dir", default=os.getenv("TG_MODEL_DIR", "models"))
    parser.add_argument("--report-dir", default="reports/latest")
    parser.add_argument(
        "--provenance", choices=["synthetic", "unsw-nb15", "local-unverified"], default="local-unverified"
    )
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--threshold", type=float, default=0.5)
    parser.add_argument("--min-f1", type=float, default=0.6)
    parser.add_argument("--min-recall", type=float, default=0.6)
    parser.add_argument("--trees", type=int, default=100)
    args = parser.parse_args()
    if not args.train_csv:
        parser.error("Provide --train-csv or TG_TRAIN_CSV")
    try:
        metadata, folder = train(**vars(args))
    except (ValueError, OSError, KeyError) as exc:
        parser.exit(2, f"Training validation failed: {exc}\n")
    print(
        json.dumps(
            {
                "source": metadata["data_source"],
                "evaluation": metadata["evaluation"],
                "quality_gate": metadata["quality_gate"],
                "artifact": str(folder),
            },
            indent=2,
        )
    )
    raise SystemExit(0 if metadata["quality_gate"]["passed"] else 1)


if __name__ == "__main__":
    main()
