"""KML from GeoJSON (SPEC-040/R10), for Google Earth and Google My Maps.

`convert` turns any GeoJSON FeatureCollection into KML: points, lines, polygons with holes, and their multi- forms;
each feature's properties become its description and ExtendedData. `rupee_kml` does the same for the challenge's
wards and roads with the results attached: wards coloured by grade, roads by what is in question on them, and the
next fixes as pins. GeoJSON is longitude, latitude; so is KML, so coordinates pass through unchanged.
"""

from __future__ import annotations

import json
from collections import defaultdict
from collections.abc import Iterable
from pathlib import Path
from typing import Any
from xml.sax.saxutils import escape

from hishob.rupee.audit import CORE, inr

# KML colours are aabbggrr.
GRADE = {"A": "a6449e2f", "B": "a616b874", "C": "a6009ff5", "D": "a60767f7", "E": "a63131e0"}
ROAD = {"flagged": "ff3131e0", "dlp": "ff0767f7", "plain": "ff9e958e"}


def _xml(text: Any) -> str:
    return escape(str(text), {'"': "&quot;"})


def _coords(points: Iterable[Iterable[float]]) -> str:
    return " ".join(",".join(str(v) for v in list(p)[:3]) for p in points)


def _ring(points: list[list[float]]) -> str:
    if points and points[0] != points[-1]:
        points = [*points, points[0]]  # KML rings must close
    return f"<LinearRing><coordinates>{_coords(points)}</coordinates></LinearRing>"


def geometry(g: dict[str, Any] | None) -> str:
    if not g:
        return ""
    kind, c = g.get("type"), g.get("coordinates")
    if kind == "Point":
        return f"<Point><coordinates>{_coords([c])}</coordinates></Point>"  # type: ignore[list-item]
    if kind == "LineString":
        return f"<LineString><tessellate>1</tessellate><coordinates>{_coords(c)}</coordinates></LineString>"  # type: ignore[arg-type]
    if kind == "Polygon":
        outer, *holes = c  # type: ignore[misc]
        inner = "".join(f"<innerBoundaryIs>{_ring(h)}</innerBoundaryIs>" for h in holes)
        return f"<Polygon><outerBoundaryIs>{_ring(outer)}</outerBoundaryIs>{inner}</Polygon>"
    if kind in {"MultiPoint", "MultiLineString", "MultiPolygon"}:
        single = kind.removeprefix("Multi")
        return "<MultiGeometry>" + "".join(geometry({"type": single, "coordinates": x}) for x in c) + "</MultiGeometry>"  # type: ignore[union-attr]
    if kind == "GeometryCollection":
        return "<MultiGeometry>" + "".join(geometry(x) for x in g.get("geometries", [])) + "</MultiGeometry>"
    raise ValueError(f"unknown geometry type: {kind}")


def placemark(name: str, geom: dict[str, Any] | None, props: dict[str, Any], style: str = "", html: str = "") -> str:
    data = "".join(
        f'<Data name="{_xml(k)}"><value>{_xml(v)}</value></Data>'
        for k, v in props.items()
        if not isinstance(v, (dict, list))
    )
    desc = html or "<br/>".join(
        f"<b>{_xml(k)}</b>: {_xml(v)}" for k, v in props.items() if not isinstance(v, (dict, list))
    )
    return (
        f"<Placemark><name>{_xml(name)}</name>"
        + (f"<styleUrl>#{style}</styleUrl>" if style else "")
        + f"<description><![CDATA[{desc}]]></description><ExtendedData>{data}</ExtendedData>"
        + geometry(geom)
        + "</Placemark>"
    )


def document(name: str, body: str, styles: str = "", description: str = "") -> str:
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n<kml xmlns="http://www.opengis.net/kml/2.2"><Document>'
        f"<name>{_xml(name)}</name><description>{_xml(description)}</description>{styles}{body}</Document></kml>\n"
    )


def folder(name: str, body: str) -> str:
    return f"<Folder><name>{_xml(name)}</name>{body}</Folder>"


def _name(props: dict[str, Any], i: int) -> str:
    for key in ("name", "title", "ward_name", "road_name", "id"):
        if props.get(key):
            return str(props[key])
    return f"Feature {i + 1}"


def convert(collection: dict[str, Any], name: str = "GeoJSON") -> str:
    """Any GeoJSON FeatureCollection (or a single Feature) to KML."""
    features = collection.get("features") or ([collection] if collection.get("type") == "Feature" else [])
    body = "".join(
        placemark(_name(f.get("properties") or {}, i), f.get("geometry"), f.get("properties") or {})
        for i, f in enumerate(features)
    )
    return document(name, body)


def _styles() -> str:
    out = []
    for g, colour in GRADE.items():
        out.append(
            f'<Style id="grade-{g}"><LineStyle><color>ffffffff</color><width>1.5</width></LineStyle>'
            f"<PolyStyle><color>{colour}</color></PolyStyle></Style>"
        )
    for k, colour in ROAD.items():
        width = 3 if k == "plain" else 5
        out.append(f'<Style id="road-{k}"><LineStyle><color>{colour}</color><width>{width}</width></LineStyle></Style>')
    out.append(
        '<Style id="fix"><IconStyle><color>ff0f48d9</color><scale>1.1</scale><Icon>'
        "<href>https://maps.google.com/mapfiles/kml/shapes/caution.png</href></Icon></IconStyle></Style>"
    )
    return "".join(out)


def _ward_html(w: dict[str, Any]) -> str:
    f = w["flags"]
    return (
        f"<b>Grade {w['grade']}</b> ({w['overall']} of 100; 50 is as expected for these jobs)<br/>"
        f"Spent {inr(w['spend_inr'])} of {inr(w['budget_inr'])} ({round(100 * (w['budget_used'] or 0))}%) "
        f"on {w['jobs']} jobs<br/>"
        f"On fixes that failed within 30 days: {inr(w['failed_spend_inr'])}<br/>"
        f"In question: {inr(w['money_in_question_inr'])} ({f['overbilled']['count']} over-billed, "
        f"{f['duplicate']['count']} duplicates, {f['dlp_paid']['count']} paid under DLP)<br/>"
        f"Open problems past their SLA: {w['open_overdue_issues']}<br/><br/>{_xml(w['note']['text'])}"
    )


def rupee_kml(bundle: dict[str, Any], data_dir: Path, fixes_per_ward: int = 3) -> dict[str, str]:
    """wards.kml, roads.kml and follow-the-rupee.kml (both layers plus the next fixes) for a built bundle."""
    wards_geo = json.loads((data_dir / "wards.geojson").read_text(encoding="utf-8"))
    roads_geo = json.loads((data_dir / "roads.geojson").read_text(encoding="utf-8"))
    wards = {w["ward_code"]: w for w in bundle["wards"]}

    ward_marks = []
    for f in wards_geo["features"]:
        p = f["properties"]
        w = wards.get(p.get("ward_code", ""))
        if w is None:
            ward_marks.append(placemark(f"Ward {p.get('ward_code', '?')}", f["geometry"], p))
            continue
        props = {
            **p,
            "grade": w["grade"],
            "score": w["overall"],
            "budget_inr": w["budget_inr"],
            "spend_inr": w["spend_inr"],
            "money_in_question_inr": w["money_in_question_inr"],
            "open_overdue_issues": w["open_overdue_issues"],
        }
        ward_marks.append(
            placemark(
                f"Ward {w['ward_code']} · grade {w['grade']}",
                f["geometry"],
                props,
                f"grade-{w['grade']}",
                _ward_html(w),
            )
        )

    by_road: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for fl in bundle["flags"]:
        if fl["rule"] in CORE:
            by_road[fl["road_id"]].append(fl)
    road_marks = []
    mid: dict[str, list[float]] = {}
    for f in roads_geo["features"]:
        p = f["properties"]
        rid = p.get("road_id", "")
        coords = f["geometry"]["coordinates"]
        mid[rid] = [(coords[0][0] + coords[-1][0]) / 2, (coords[0][1] + coords[-1][1]) / 2]
        flags = by_road.get(rid, [])
        dlp = any(x["rule"] == "dlp_paid" for x in flags)
        money = sum(x["amount_inr"] for x in flags)
        kind = "flagged" if any(x["rule"] != "dlp_paid" for x in flags) else "dlp" if dlp else "plain"
        lines = "".join(f"<li>{_xml(x['work_order_id'])}: {_xml(x['reason'])}</li>" for x in flags[:8])
        html = (
            f"<b>{_xml(p.get('road_name', rid))}</b> ({_xml(rid)}), ward {_xml(p.get('ward_code', ''))}<br/>"
            f"{_xml(p.get('road_type', ''))}, {_xml(p.get('surface', ''))}<br/>"
            + (f"In question: {inr(money)} across {len(flags)} flags<ul>{lines}</ul>" if flags else "Nothing flagged")
        )
        road_marks.append(
            placemark(
                f"{p.get('road_name', rid)} ({rid})",
                f["geometry"],
                {**p, "flags": len(flags), "money_in_question_inr": money},
                f"road-{kind}",
                html,
            )
        )

    fix_marks = []
    for code, plan in bundle["plan"]["wards"].items():
        for rank, item in enumerate(plan["items"][:fixes_per_ward], start=1):
            if item["road_id"] not in mid:
                continue
            html = (
                f"<b>Risk {item['risk']}</b>: {_xml(item['category'])} on {_xml(item['road_name'])}<br/>"
                f"Method: {_xml(item['method'])}, {'₹0 to BMC (DLP)' if item['under_dlp'] else inr(item['cost_inr'])}"
                f"<ul>{''.join(f'<li>{_xml(w)}</li>' for w in item['why'])}</ul>"
            )
            point = {"type": "Point", "coordinates": mid[item["road_id"]]}
            fix_marks.append(
                placemark(
                    f"{code} #{rank}: {item['category']} (risk {item['risk']})",
                    point,
                    {"ward_code": code, "rank": rank, "risk": item["risk"], "issue_id": item["issue_id"]},
                    "fix",
                    html,
                )
            )

    about = "Follow the Rupee, Claude Impact Lab Mumbai. Synthetic data; all contractors are fictional."
    styles = _styles()
    wards_doc = folder("Wards, coloured by grade", "".join(ward_marks))
    roads_doc = folder("Roads: red flagged, orange paid under DLP", "".join(road_marks))
    fixes_doc = folder(f"Next fixes, top {fixes_per_ward} per ward", "".join(fix_marks))
    return {
        "wards.kml": document("Follow the Rupee: wards", wards_doc, styles, about),
        "roads.kml": document("Follow the Rupee: roads", roads_doc, styles, about),
        "follow-the-rupee.kml": document("Follow the Rupee", wards_doc + roads_doc + fixes_doc, styles, about),
    }


def write(files: dict[str, str], out: Path) -> list[Path]:
    out.mkdir(parents=True, exist_ok=True)
    paths = []
    for name, text in files.items():
        path = out / name
        path.write_text(text, encoding="utf-8")
        paths.append(path)
    return paths
