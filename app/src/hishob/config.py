"""Settings read from the environment."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    database_url: str
    storage: str  # "local" or "s3"
    local_root: Path
    archive_bucket: str
    data_bucket: str
    events: str  # "log" or "sqs"
    events_queue_url: str | None
    fetch_delay_s: float

    @classmethod
    def from_env(cls) -> Settings:
        env = os.environ
        return cls(
            database_url=env.get("HISHOB_DATABASE_URL", "postgresql://postgres:hishob@localhost:5432/hishob"),
            storage=env.get("HISHOB_STORAGE", "local"),
            local_root=Path(env.get("HISHOB_LOCAL_ROOT", "var")),
            archive_bucket=env.get("HISHOB_ARCHIVE_BUCKET", "hishob-archive"),
            data_bucket=env.get("HISHOB_DATA_BUCKET", "hishob-data"),
            events=env.get("HISHOB_EVENTS", "log"),
            events_queue_url=env.get("HISHOB_EVENTS_QUEUE_URL"),
            fetch_delay_s=float(env.get("HISHOB_FETCH_DELAY_S", "5")),
        )
