"""Check records against the generated whitelist: labels, properties and their types, edge endpoints."""

from __future__ import annotations

import json
import re
from functools import cache
from pathlib import Path
from typing import Any

WHITELIST = Path(__file__).with_name("whitelist.json")
DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


@cache
def load(path: Path = WHITELIST) -> dict[str, Any]:
    data: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    return data


def _type_ok(value: object, expected: str) -> bool:
    if expected == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if expected == "number":
        return isinstance(value, int | float) and not isinstance(value, bool)
    if expected == "date":
        return isinstance(value, str) and bool(DATE.match(value))
    if expected == "boolean":
        return isinstance(value, bool)
    return isinstance(value, str)


def check_node(label: str, props: dict[str, object], wl: dict[str, Any] | None = None) -> list[str]:
    wl = wl or load()
    if label not in wl["labels"]:
        return [f"unknown_label: {label}"]
    allowed: dict[str, str] = wl["labels"][label]["properties"]
    problems = []
    for key, value in props.items():
        if key not in allowed:
            problems.append(f"unknown_property: {label}.{key}")
        elif not _type_ok(value, allowed[key]):
            problems.append(f"wrong_type: {label}.{key} must be {allowed[key]}")
    return problems


def check_edge(edge_type: str, source_label: str, target_label: str, wl: dict[str, Any] | None = None) -> list[str]:
    wl = wl or load()
    pairs = wl["edges"].get(edge_type)
    if pairs is None:
        return [f"unknown_edge: {edge_type}"]
    if [source_label, target_label] in pairs:
        return []
    sources = sorted({p[0] for p in pairs})
    targets = sorted({p[1] for p in pairs if p[0] == source_label}) or sorted({p[1] for p in pairs})
    return [
        f"domain_range: {edge_type} cannot go from {source_label} to {target_label}; "
        f"it goes from {', '.join(sources)} to {', '.join(targets)}"
    ]
