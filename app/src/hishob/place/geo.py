"""Build the geo tables from the ledger, and answer place lookups (SPEC-004/R3, R4, R5)."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

import psycopg

from hishob.place.names import latin_key, normalise

Conn = psycopg.Connection[tuple[object, ...]]
NEAR_ROAD_M = 50


@dataclass(frozen=True)
class PlaceMatch:
    node_id: str
    kind: str
    name: str
    matched: str
    score: float
    segments: int = 1


@dataclass(frozen=True)
class PointResult:
    road: dict[str, Any] | None
    admin_ward: dict[str, Any] | None
    electoral_ward: dict[str, Any] | None
    note: str = ""


def _current(conn: Conn, label: str) -> list[tuple[str, dict[str, Any]]]:
    rows = conn.execute(
        "SELECT c.node_id, p.key, p.value FROM ledger.current c JOIN ledger.current_props p USING (identity)"
        " WHERE c.label = %s ORDER BY c.node_id",
        (label,),
    ).fetchall()
    nodes: dict[str, dict[str, Any]] = {}
    for node_id, key, value in rows:
        nodes.setdefault(str(node_id), {})[str(key)] = value
    return list(nodes.items())


def build(conn: Conn) -> dict[str, int]:
    """Rebuild the geo tables from the ledger's current facts. Returns row counts."""
    with conn.transaction():
        conn.execute("TRUNCATE geo.admin_wards, geo.electoral_wards, geo.road_segments, geo.aliases")
        names: list[tuple[str, str, str, str]] = []
        skipped = 0  # places known only by name (e.g. a road named in a tender) have no geometry to map
        for node_id, p in _current(conn, "AdminWard"):
            if not p.get("geometry_wkt"):
                skipped += 1
                continue
            conn.execute(
                "INSERT INTO geo.admin_wards VALUES (%s, %s, %s, ST_Multi(ST_GeomFromText(%s, 4326)))",
                (node_id, p.get("code"), p.get("name"), p["geometry_wkt"]),
            )
            names += _names(node_id, "AdminWard", p, ("code", "name", "name_mr", "name_en"))
        for node_id, p in _current(conn, "ElectoralWard"):
            if not p.get("geometry_wkt"):
                skipped += 1
                continue
            conn.execute(
                "INSERT INTO geo.electoral_wards VALUES (%s, %s, %s, ST_Multi(ST_GeomFromText(%s, 4326)))",
                (node_id, p.get("number"), p.get("name"), p["geometry_wkt"]),
            )
            names += _names(node_id, "ElectoralWard", p, ("name", "name_mr", "name_en"))
        for node_id, p in _current(conn, "Road"):
            if not p.get("geometry_wkt"):
                skipped += 1
                continue
            conn.execute(
                "INSERT INTO geo.road_segments VALUES (%s, %s, %s, %s, ST_GeomFromText(%s, 4326))",
                (node_id, p.get("name"), p.get("name_mr"), p.get("osm_way_id"), p["geometry_wkt"]),
            )
            names += _names(node_id, "Road", p, ("name", "name_mr", "name_en"))
        kinds = {n[0]: n[1] for n in names}
        alias_names = dict(_current(conn, "Alias"))
        for from_id, to_id in conn.execute(
            "SELECT f.from_id, f.to_id FROM ledger.current c JOIN ledger.facts f ON f.fact_id = c.fact_id"
            " WHERE f.kind = 'edge' AND f.name = 'ALIAS_OF'"
        ).fetchall():
            alias = alias_names.get(str(from_id), {}).get("name")
            if alias and str(to_id) in kinds:
                names.append((str(to_id), kinds[str(to_id)], str(alias), "alias"))
        with conn.cursor() as cur:
            cur.executemany(
                "INSERT INTO geo.aliases VALUES (%s, %s, %s, %s, %s, %s) ON CONFLICT DO NOTHING",
                [(n, k, a, normalise(a), latin_key(a), o) for n, k, a, o in names],
            )
        counts = {
            table: _count(conn, table) for table in ("admin_wards", "electoral_wards", "road_segments", "aliases")
        }
        counts["without_geometry"] = skipped
    return counts


def _count(conn: Conn, table: str) -> int:
    row = conn.execute(f"SELECT count(*) FROM geo.{table}").fetchone()
    return int(str(row[0])) if row else 0


NameRow = tuple[str, str, str, str]  # node id, kind, name, where the name came from


def _names(node_id: str, kind: str, props: dict[str, Any], keys: tuple[str, ...]) -> list[NameRow]:
    return [(node_id, kind, str(props[k]), k) for k in keys if props.get(k)]


def find_place(conn: Conn, text: str, kinds: set[str] | None = None, limit: int = 10) -> list[PlaceMatch]:
    """Places whose names match `text` in either script, best first. Road segments sharing a name are
    returned once, with the number of segments."""
    norm, key = normalise(text), latin_key(text)
    rows = conn.execute(
        "SELECT a.node_id, a.kind, a.alias, GREATEST(CASE WHEN a.norm = %(n)s THEN 1.0 ELSE 0 END,"
        "  similarity(a.norm, %(n)s), 0.95 * similarity(a.key, %(k)s)) AS score"
        " FROM geo.aliases a"
        " WHERE (a.norm %% %(n)s OR a.key %% %(k)s OR a.norm = %(n)s)"
        "   AND (%(kinds)s::text[] IS NULL OR a.kind = ANY(%(kinds)s::text[]))"
        " ORDER BY score DESC, a.node_id",
        {"n": norm, "k": key, "kinds": sorted(kinds) if kinds else None},
    ).fetchall()
    conn.commit()
    best: dict[tuple[str, str], PlaceMatch] = {}
    for node_id, kind, alias, score in rows:
        name = _display_name(conn, str(kind), str(node_id))
        group = (str(kind), normalise(name))
        if group in best:
            current = best[group]
            best[group] = PlaceMatch(
                current.node_id,
                current.kind,
                current.name,
                current.matched,
                current.score,
                current.segments + (1 if node_id != current.node_id else 0),
            )
            continue
        best[group] = PlaceMatch(str(node_id), str(kind), name, str(alias), round(float(str(score)), 3))
    ranked = sorted(best.values(), key=lambda m: (-m.score, m.name))
    return ranked[:limit]


def _display_name(conn: Conn, kind: str, node_id: str) -> str:
    table = {"AdminWard": "admin_wards", "ElectoralWard": "electoral_wards", "Road": "road_segments"}[kind]
    column = "code" if kind == "AdminWard" else "name"
    row = conn.execute(f"SELECT {column} FROM geo.{table} WHERE node_id = %s", (node_id,)).fetchone()
    return str(row[0]) if row and row[0] is not None else node_id


def at_point(conn: Conn, lat: float, lon: float) -> PointResult:
    """The nearest road within 50 m, and the wards containing the point (R4, R5)."""
    point = "ST_SetSRID(ST_MakePoint(%(lon)s, %(lat)s), 4326)"
    params = {"lat": lat, "lon": lon, "near": NEAR_ROAD_M}
    road = conn.execute(
        f"SELECT node_id, name, name_mr, round(ST_Distance(geom::geography, {point}::geography)::numeric, 1)"
        f" FROM geo.road_segments WHERE ST_DWithin(geom::geography, {point}::geography, %(near)s)"
        f" ORDER BY geom::geography <-> {point}::geography LIMIT 1",
        params,
    ).fetchone()
    admin = conn.execute(
        f"SELECT node_id, code, name FROM geo.admin_wards WHERE ST_Covers(geom, {point}) ORDER BY node_id LIMIT 1",
        params,
    ).fetchone()
    electoral = conn.execute(
        f"SELECT node_id, number, name FROM geo.electoral_wards WHERE ST_Covers(geom, {point})"
        " ORDER BY node_id LIMIT 1",
        params,
    ).fetchone()
    conn.commit()
    notes = []
    if road is None:
        notes.append(f"no road within {NEAR_ROAD_M} m")
    if admin is None:
        notes.append("outside every administrative ward loaded")
    if electoral is None:
        notes.append("no electoral ward loaded for this point")
    return PointResult(
        road=None
        if road is None
        else {"node_id": road[0], "name": road[1], "name_mr": road[2], "distance_m": float(str(road[3]))},
        admin_ward=None if admin is None else {"node_id": admin[0], "code": admin[1], "name": admin[2]},
        electoral_ward=None
        if electoral is None
        else {"node_id": electoral[0], "number": electoral[1], "name": electoral[2]},
        note="; ".join(notes),
    )


def as_json(result: Any) -> str:
    return json.dumps(result.__dict__ if hasattr(result, "__dict__") else result, ensure_ascii=False, indent=2)
