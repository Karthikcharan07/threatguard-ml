import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    model_dir: Path
    api_key: str
    max_batch: int = 128
    rate_limit: int = 60
    max_body_bytes: int = 256_000
    min_drift_rows: int = 30

    def __post_init__(self):
        if not 32 <= len(self.api_key) <= 256:
            raise ValueError("TG_API_KEY must contain 32..256 characters")
        if not (
            1 <= self.max_batch <= 4096
            and 1 <= self.rate_limit <= 10000
            and 1024 <= self.max_body_bytes <= 10_000_000
            and 10 <= self.min_drift_rows <= self.max_batch
        ):
            raise ValueError("Invalid API resource limits")

    @classmethod
    def from_env(cls):
        return cls(
            Path(os.getenv("TG_MODEL_DIR", "models")),
            os.getenv("TG_API_KEY", ""),
            int(os.getenv("TG_MAX_BATCH", "128")),
            int(os.getenv("TG_RATE_LIMIT", "60")),
        )
