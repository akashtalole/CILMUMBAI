"""Read the challenge dataset. Each row keeps the file and line it came from, so anything built on it can cite it."""

from __future__ import annotations

import csv
import math
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path
from typing import Any

DEFAULT_DIR = Path(__file__).resolve().parents[3] / "datasets" / "follow-the-rupee" / "data"
FILES = (
    "wards",
    "work_orders",
    "rate_card",
    "contractors",
    "complaints",
    "social_posts",
    "roads",
    "localities",
    "flood_hotspots",
    "rainfall_daily",
    "tides",
    "traffic",
    "accidents",
    "facilities",
)


class Row(dict[str, str]):
    """A CSV row that knows where it came from. `cite` is `file.csv#L<line>`, with line 1 the header."""

    file: str
    line: int

    @property
    def cite(self) -> str:
        return f"{self.file}#L{self.line}"

    def num(self, key: str, default: float = 0.0) -> float:
        value = self.get(key, "")
        try:
            return float(value) if value != "" else default
        except ValueError:
            return default

    def flag(self, key: str) -> bool:
        return self.get(key, "").strip().upper() == "Y"


def read_csv(path: Path) -> list[Row]:
    rows: list[Row] = []
    with path.open(encoding="utf-8", newline="") as handle:
        for i, raw in enumerate(csv.DictReader(handle), start=2):
            row = Row({k: (v or "").strip() for k, v in raw.items() if k is not None})
            row.file, row.line = path.name, i
            rows.append(row)
    return rows


def ts(value: str) -> datetime | None:
    if not value:
        return None
    for fmt in ("%Y-%m-%d %H:%M", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue
    return None


def day(value: str) -> date | None:
    t = ts(value)
    return t.date() if t else None


def metres(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Distance on the ground; equirectangular is plenty at city scale."""
    x = math.radians(lon2 - lon1) * math.cos(math.radians((lat1 + lat2) / 2))
    y = math.radians(lat2 - lat1)
    return 6_371_000 * math.hypot(x, y)


@dataclass
class Dataset:
    root: Path
    tables: dict[str, list[Row]] = field(default_factory=dict)

    def __getattr__(self, name: str) -> list[Row]:
        tables = self.__dict__.get("tables", {})
        if name in tables:
            return tables[name]  # type: ignore[no-any-return]
        raise AttributeError(name)

    def by(self, table: str, key: str) -> dict[str, Row]:
        return {r[key]: r for r in self.tables[table]}

    def geojson(self, name: str) -> Any:
        import json

        return json.loads((self.root / f"{name}.geojson").read_text(encoding="utf-8"))


def load(root: Path | str = DEFAULT_DIR) -> Dataset:
    root = Path(root)
    missing = [f for f in FILES if not (root / f"{f}.csv").exists()]
    if missing:
        raise FileNotFoundError(f"{root} is missing {', '.join(m + '.csv' for m in missing)}")
    return Dataset(root, {f: read_csv(root / f"{f}.csv") for f in FILES})
