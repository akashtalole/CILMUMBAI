"""Turn place files into ledger facts (SPEC-004/R1, R2, R6).

Each file is archived first (SPEC-001). Every ward or road becomes a node record citing the archived file,
with its name as the quote, and goes through the loader's checks (SPEC-003) like any extracted fact.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from hishob.archive import Archive
from hishob.ledger import BatchReport, Loader
from hishob.schema.model import read_version

SLUG = re.compile(r"[^a-z0-9]+")
TIER = "reported"  # community-digitised boundaries and OpenStreetMap: not official records


@dataclass(frozen=True)
class ImportResult:
    source_sha256: str
    batch_id: str
    features: int
    skipped: int
    report: BatchReport


def _slug(text: str) -> str:
    return SLUG.sub("-", text.lower()).strip("-")


def _wkt_multipolygon(geometry: dict[str, Any]) -> str:
    def ring(points: list[list[float]]) -> str:
        return "(" + ", ".join(f"{x:.7f} {y:.7f}" for x, y, *_ in points) + ")"

    def polygon(rings: list[list[list[float]]]) -> str:
        return "(" + ", ".join(ring(r) for r in rings) + ")"

    if geometry["type"] == "Polygon":
        polygons = [geometry["coordinates"]]
    elif geometry["type"] == "MultiPolygon":
        polygons = geometry["coordinates"]
    else:
        raise ValueError(f"expected a polygon, got {geometry['type']}")
    return "MULTIPOLYGON(" + ", ".join(polygon(p) for p in polygons) + ")"


def import_wards(
    archive: Archive,
    loader: Loader,
    path: Path,
    *,
    kind: str,
    name_property: str,
    publisher: str,
    licence: str,
    batch_id: str,
) -> ImportResult:
    """Import administrative (`kind="admin"`) or electoral (`kind="electoral"`) wards from GeoJSON."""
    if kind not in {"admin", "electoral"}:
        raise ValueError("kind must be admin or electoral")
    ref = archive.add_file(path, publisher=publisher, licence=licence)
    raw = path.read_text(encoding="utf-8")
    features = json.loads(raw)["features"]
    records, skipped = [], 0
    for feature in features:
        value = feature.get("properties", {}).get(name_property)
        geometry = feature.get("geometry")
        if value in (None, "") or not geometry:
            skipped += 1
            continue
        value = str(value)
        props: dict[str, Any]
        if kind == "admin":
            node_id, label, props = f"adminward:{_slug(value)}", "AdminWard", {"code": value, "name": value}
        else:
            number = int(re.sub(r"\D", "", value) or 0)
            node_id, label = f"electoralward:{number}", "ElectoralWard"
            props = {"number": number, "name": value}
        props["geometry_wkt"] = _wkt_multipolygon(geometry)
        records.append(_record(node_id, label, props, ref.sha256, verbatim(raw, value)))
    report = loader.load(records, batch_id=batch_id, extractor="place-importer@1", ontology_version=read_version())
    return ImportResult(ref.sha256, batch_id, len(records), skipped, report)


def import_roads(
    archive: Archive, loader: Loader, path: Path, *, publisher: str, licence: str, batch_id: str
) -> ImportResult:
    """Import named road ways from an OpenStreetMap export in Overpass JSON (`out tags geom;`)."""
    ref = archive.add_file(path, publisher=publisher, licence=licence)
    raw = path.read_text(encoding="utf-8")
    elements = json.loads(raw)["elements"]
    records, skipped = [], 0
    for way in elements:
        tags = way.get("tags", {})
        points = way.get("geometry") or []
        if way.get("type") != "way" or "name" not in tags or len(points) < 2:
            skipped += 1
            continue
        props: dict[str, Any] = {
            "name": tags["name"],
            "osm_way_id": str(way["id"]),
            "geometry_wkt": "LINESTRING(" + ", ".join(f"{p['lon']:.7f} {p['lat']:.7f}" for p in points) + ")",
        }
        if tags.get("name:mr"):
            props["name_mr"] = tags["name:mr"]
        if tags.get("name:en") and tags["name:en"] != tags["name"]:
            props["name_en"] = tags["name:en"]
        records.append(_record(f"road:osm-{way['id']}", "Road", props, ref.sha256, verbatim(raw, tags["name"])))
    report = loader.load(records, batch_id=batch_id, extractor="place-importer@1", ontology_version=read_version())
    return ImportResult(ref.sha256, batch_id, len(records), skipped, report)


def confirm_alias(
    archive: Archive, loader: Loader, node_id: str, alias: str, *, reviewer_account: str, batch_id: str
) -> BatchReport:
    """Record a reviewer's confirmation that `alias` names `node_id` (R6). The decision itself is archived and
    becomes the source the alias cites."""
    decision = {"decision": "alias_confirmed", "node_id": node_id, "alias": alias, "reviewer": reviewer_account}
    data = json.dumps(decision, ensure_ascii=False, indent=2).encode("utf-8")
    ref = archive.add_upload(data, filename="alias-decision.json", account_id=reviewer_account)
    alias_id = f"alias:{_slug(node_id)}--{_slug(alias) or 'x'}"
    records = [
        dict(_record(alias_id, "Alias", {"name": alias}, ref.sha256, alias), tier="derived"),
        {
            "kind": "edge",
            "type": "ALIAS_OF",
            "from": alias_id,
            "to": node_id,
            "source": ref.sha256,
            "page": 1,
            "quote": alias,
            "tier": "derived",
            "confidence": 1.0,
        },
    ]
    return loader.load(records, batch_id=batch_id, extractor="reviewer@1", ontology_version=read_version())


def verbatim(raw: str, value: str) -> str:
    """The value as it is written in the raw file, so the quote check can find it. JSON writers may escape
    "/" as "\\/" or write non-ASCII as \\u escapes; the quote must be the file's own spelling."""
    candidates = [
        value,
        value.replace("/", "\\/"),
        json.dumps(value)[1:-1],
        json.dumps(value)[1:-1].replace("/", "\\/"),
    ]
    return next((c for c in candidates if c in raw), value)


def _record(node_id: str, label: str, props: dict[str, Any], source: str, quote: str) -> dict[str, Any]:
    return {
        "kind": "node",
        "id": node_id,
        "label": label,
        "props": props,
        "source": source,
        "page": 1,
        "quote": quote,
        "tier": TIER,
        "confidence": 0.9,
    }
