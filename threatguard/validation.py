import math

import numpy as np
import pandas as pd
from fastapi import HTTPException
from pydantic import BaseModel, ConfigDict


class Batch(BaseModel):
    model_config = ConfigDict(extra="forbid")
    records: list[dict[str, object]]


def validate_records(records, schema, max_batch):
    if not 1 <= len(records) <= max_batch:
        raise HTTPException(422, f"Batch must contain 1..{max_batch} records")
    cleaned = []
    for row in records:
        if set(row) != set(schema):
            raise HTTPException(422, "Feature names must exactly match /model/info")
        record = {}
        for name, kind in schema.items():
            value = row[name]
            if value is None:
                record[name] = np.nan
            elif kind == "numeric":
                if isinstance(value, bool) or not isinstance(value, (int, float)):
                    raise HTTPException(422, "Numeric features require numbers or null")
                try:
                    number = float(value)
                except (OverflowError, ValueError):
                    raise HTTPException(422, "Numeric value out of range") from None
                if not math.isfinite(number) or abs(number) > 1e15:
                    raise HTTPException(422, "Numeric values must be finite and bounded")
                record[name] = number
            else:
                if not isinstance(value, str) or not 1 <= len(value) <= 128:
                    raise HTTPException(422, "Categorical features require 1..128 character strings or null")
                record[name] = value
        cleaned.append(record)
    return pd.DataFrame(cleaned, columns=list(schema))
