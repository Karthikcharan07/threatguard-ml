"""Create authenticated prediction/drift payloads from a local CSV and served schema."""

import argparse
import json
import os
from pathlib import Path

import httpx
import pandas as pd


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--csv", default="data/synthetic.csv")
    p.add_argument("--url", default="http://127.0.0.1:8000")
    p.add_argument("--drift", action="store_true")
    a = p.parse_args()
    key = os.environ["TG_API_KEY"]
    # Use HTTPS if the service is remote; default requests stay on loopback.
    with httpx.Client(base_url=a.url, headers={"X-API-Key": key}, timeout=30) as client:
        response = client.get("/model/info")
        response.raise_for_status()
        schema = response.json()["feature_schema"]
        data = pd.read_csv(Path(a.csv))[list(schema)].head(64 if a.drift else 1)
        records = json.loads(data.to_json(orient="records"))
        result = client.post("/monitor/drift" if a.drift else "/predict", json={"records": records})
        result.raise_for_status()
        print(json.dumps(result.json(), indent=2))


if __name__ == "__main__":
    main()
