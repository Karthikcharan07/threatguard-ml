"""Artificial data for smoke tests. It is NOT UNSW-NB15."""

import argparse
from pathlib import Path

import numpy as np
import pandas as pd


def generate(n=1200, seed=42):
    if n < 50:
        raise ValueError("Generate at least 50 rows")
    rng = np.random.default_rng(seed)
    # Overlapping, noisy patterns; labels are synthetic, not real attack traces.
    label = rng.binomial(1, 0.4, n)
    frame = pd.DataFrame(
        {
            "id": np.arange(n),
            "dur": rng.gamma(2, 0.4 + label * 0.3),
            "proto": rng.choice(["tcp", "udp", "icmp"], n),
            "service": rng.choice(["http", "dns", "-"], n),
            "state": rng.choice(["FIN", "CON", "INT"], n),
            "spkts": rng.poisson(8 + label * 12),
            "dpkts": rng.poisson(10 - label * 4),
            "sbytes": rng.lognormal(6 + label * 0.8, 0.8),
            "dbytes": rng.lognormal(7 - label, 0.9),
            "rate": rng.lognormal(3 + label, 0.7),
            "attack_cat": np.where(label == 0, "Normal", "SyntheticAttack"),
            "label": label,
        }
    )
    noisy = rng.random(n) < 0.06
    frame.loc[noisy, "label"] = 1 - frame.loc[noisy, "label"]
    frame["attack_cat"] = np.where(frame["label"] == 0, "Normal", "SyntheticAttack")
    return frame


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", default="data/synthetic.csv")
    parser.add_argument("--rows", type=int, default=1200)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    path = Path(args.output)
    path.parent.mkdir(parents=True, exist_ok=True)
    generate(args.rows, args.seed).to_csv(path, index=False)
    print(f"SYNTHETIC DEVELOPMENT DATA: {args.rows} rows -> {path}")


if __name__ == "__main__":
    main()
