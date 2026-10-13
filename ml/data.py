from pathlib import Path

import numpy as np
import pandas as pd

CATEGORICAL = {"proto", "service", "state"}
NUMERIC = set(
    "dur spkts dpkts sbytes dbytes rate sttl dttl sload dload sloss dloss sinpkt dinpkt "
    "sjit djit swin stcpb dtcpb dwin tcprtt synack ackdat smean dmean trans_depth "
    "response_body_len ct_srv_src ct_state_ttl ct_dst_ltm ct_src_dport_ltm "
    "ct_dst_sport_ltm ct_dst_src_ltm is_ftp_login ct_ftp_cmd ct_flw_http_mthd "
    "ct_src_ltm ct_srv_dst is_sm_ips_ports".split()
)
MINIMUM = CATEGORICAL | {"dur", "spkts", "dpkts", "sbytes", "dbytes", "rate"}
EXCLUDED = {"id", "label", "attack_cat", "srcip", "dstip", "sport", "dsport", "stime", "ltime"}


def load_dataset(path: Path, target=None):
    if not path.is_file() or path.stat().st_size > 1_000_000_000:
        raise ValueError("CSV must exist and be smaller than 1 GB")
    # Header duplicates otherwise silently become column.1 in pandas.
    import csv

    with path.open(encoding="utf-8-sig", newline="") as handle:
        header = next(csv.reader(handle), [])
    normalized = [c.strip().lower() for c in header]
    if len(normalized) != len(set(normalized)):
        raise ValueError("Duplicate column names")
    frame = pd.read_csv(path, low_memory=False)
    frame.columns = normalized
    target = target or ("label" if "label" in frame else "attack_cat")
    if target not in {"label", "attack_cat"} or target not in frame:
        raise ValueError("Required target label or attack_cat is missing")
    if not MINIMUM.issubset(frame.columns):
        raise ValueError(f"Missing required features: {sorted(MINIMUM - set(frame.columns))}")
    unknown = set(frame.columns) - NUMERIC - CATEGORICAL - EXCLUDED
    if unknown:
        raise ValueError(f"Unknown columns; map raw CSV schema explicitly: {sorted(unknown)}")
    features = [c for c in frame.columns if c in NUMERIC | CATEGORICAL]
    x = frame[features].copy()
    for c in features:
        if c in NUMERIC:
            x[c] = pd.to_numeric(x[c], errors="raise").astype(float)
            if np.isinf(x[c]).any():
                raise ValueError("Infinite numeric feature")
        else:
            x[c] = x[c].map(lambda v: str(v).strip() if pd.notna(v) else np.nan)
    if frame[target].isna().any():
        raise ValueError("Missing target values")
    if target == "label":
        values = pd.to_numeric(frame[target], errors="raise")
        if not set(values.unique()).issubset({0, 1}):
            raise ValueError("Binary label must contain only 0 and 1")
        y = values.astype(int).astype(str)
    else:
        y = frame[target].astype(str).str.strip()
        if y.eq("").any():
            raise ValueError("Empty attack category")
    if len(x) < 20 or y.nunique() < 2 or y.value_counts().min() < 3:
        raise ValueError("Need at least 20 rows and at least 3 samples per class")
    report = {
        "rows": len(x),
        "target": target,
        "features": features,
        "excluded_columns": [c for c in frame if c not in features],
        "missing_values": {c: int(x[c].isna().sum()) for c in features},
        "class_distribution": {str(k): int(v) for k, v in y.value_counts().items()},
    }
    return x, y, report


def row_hashes(x):
    return pd.util.hash_pandas_object(x, index=False).astype(str)
