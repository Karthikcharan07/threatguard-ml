import numpy as np
import pandas as pd

from ml.data import CATEGORICAL


def proportions(counts):
    a = np.asarray(counts, dtype=float) + 0.5
    return a / a.sum()


def numeric_counts(series, cuts):
    values = pd.to_numeric(series, errors="raise").to_numpy(dtype=float)
    present = values[~np.isnan(values)]
    hist = np.histogram(present, bins=[-np.inf, *cuts, np.inf])[0].tolist()
    return [*hist, int(np.isnan(values).sum())]


def category_counts(series, categories):
    values = series.fillna("__MISSING__").astype(str)
    return [int(values.eq(c).sum()) for c in categories] + [int((~values.isin(categories)).sum())]


def baseline(x):
    result = {}
    for c in x:
        if c in CATEGORICAL:
            cats = sorted(x[c].fillna("__MISSING__").astype(str).unique().tolist())
            result[c] = {"kind": "categorical", "categories": cats, "counts": category_counts(x[c], cats)}
        else:
            present = x[c].dropna().to_numpy(dtype=float)
            cuts = (
                sorted(set(np.quantile(present, np.linspace(0.1, 0.9, 9)).tolist()))
                if len(present)
                else [0.0]
            )
            if len(cuts) == 1:
                delta = max(abs(cuts[0]) * 0.001, 0.001)
                cuts = [cuts[0] - delta, cuts[0] + delta]
            result[c] = {"kind": "numeric", "cuts": cuts, "counts": numeric_counts(x[c], cuts)}
    return result


def detect(reference, x, psi_threshold=0.2, tv_threshold=0.2):
    features = {}
    for c, spec in reference.items():
        if spec["kind"] == "numeric":
            actual = proportions(numeric_counts(x[c], spec["cuts"]))
            expected = proportions(spec["counts"])
            value = float(np.sum((actual - expected) * np.log(actual / expected)))
            metric, threshold = "PSI", psi_threshold
        else:
            actual = proportions(category_counts(x[c], spec["categories"]))
            expected = proportions(spec["counts"])
            value = float(0.5 * np.abs(actual - expected).sum())
            metric, threshold = "total_variation", tv_threshold
        features[c] = {"metric": metric, "score": value, "threshold": threshold, "drifted": value > threshold}
    return {
        "rows": len(x),
        "drift_detected": any(v["drifted"] for v in features.values()),
        "features": features,
        "interpretation": "Input drift is not proof of accuracy loss; evaluate new labelled data.",
    }
