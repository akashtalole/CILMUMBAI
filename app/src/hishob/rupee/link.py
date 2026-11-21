"""Complaint to issue to work order (SPEC-040/R1). Messy, duplicated, multilingual complaints become issues, and each
issue is tied to the work order that fixed it, or marked as never fixed.

Everything here is deterministic: the ward from the complaint, the gazetteer or the GPS; the category from words in
four languages; the road from its name in the text or the nearest segment. Each choice records how it was made, so
a reader can see which links are given by the data and which we inferred.
"""

from __future__ import annotations

import re
import unicodedata
from collections import defaultdict
from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any

from hishob.rupee.data import Dataset, Row, metres, ts

CATEGORIES = (
    "Road cave-in",
    "Open or broken manhole",
    "Broken paver blocks",
    "Choked drain / nullah overflow",
    "Waterlogging",
    "Pothole",
)
# Checked in this order: a cave-in full of water is a cave-in, a pothole under water is still a pothole on the road.
WORDS: dict[str, tuple[str, ...]] = {
    "Road cave-in": (
        "cave-in",
        "cave in",
        "caved",
        "sinkhole",
        "collapsed",
        "dhas",
        "dhans",
        "khachla",
        "धस",
        "धंस",
        "खचल",
        "खचला",
    ),
    "Open or broken manhole": ("manhole", "chamber", "dhakkan", "dhakan", "ढक्कन", "झाकण", "मॅनहोल", "मैनहोल", "मेनहोल"),
    "Broken paver blocks": ("paver", "पेव्हर", "पेवर", "blocks"),
    "Choked drain / nullah overflow": (
        "drain",
        "nullah",
        "nala",
        "naala",
        "gutter",
        "naali",
        "nali",
        "नाला",
        "नाले",
        "गटार",
        "नाली",
        "गटर",
    ),
    "Waterlogging": (
        "waterlog",
        "water logging",
        "flooded",
        "flood",
        "knee",
        "paani bhar",
        "pani bhar",
        "paani jama",
        "pani saachl",
        "पाणी साच",
        "पानी भर",
        "पाणी भर",
        "जलभराव",
        "तुंब",
        "पंप",
        "pump bhej",
        "send pump",
    ),
    "Pothole": ("pothole", "pot hole", "khadda", "khadde", "gadda", "gaddha", "gadde", "crater", "खड्ड", "गड्ढ", "गड्ढे"),
}
VAGUE = {"Road related", "Other", ""}
SEVERITY_BY_SLA = {24: 5, 48: 4, 72: 3, 120: 2, 168: 1}
CLUSTER_DAYS = 7
OPEN = {"Open", "In Progress"}


@dataclass
class Linked:
    complaint_id: str
    received_at: str
    ward_code: str
    ward_from: str  # complaint | locality | gps | none
    category: str
    category_from: str  # work order | reported | text | reported-vague
    road_id: str
    road_from: str  # work order | name in text | gps | locality | none
    status: str
    work_order_id: str
    issue_id: str
    state: str  # fixed | fixed, failed | duplicate of a fixed one | open | open, overdue | rejected | forwarded
    language: str
    upvotes: int
    cite: str

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def fold(text: str) -> str:
    return unicodedata.normalize("NFC", text).casefold()


def infer_category(text: str) -> str | None:
    t = fold(text)
    for category in CATEGORIES:
        if any(w in t for w in WORDS[category]):
            return category
    return None


class Gazetteer:
    """Locality names and aliases (Latin and Devanagari) to ward and point; roads by name and by position."""

    def __init__(self, data: Dataset) -> None:
        self.names: dict[str, Row] = {}
        for loc in data.localities:
            for name in [loc["locality"], *loc["aliases"].split(";")]:
                if name.strip():
                    self.names[fold(name.strip())] = loc
        self.roads = data.roads
        self.mid = {
            r["road_id"]: ((r.num("start_lat") + r.num("end_lat")) / 2, (r.num("start_lon") + r.num("end_lon")) / 2)
            for r in data.roads
        }
        self.road_names = sorted({fold(r["road_name"]) for r in data.roads}, key=len, reverse=True)

    def locality(self, text: str) -> Row | None:
        t = fold(text)
        if not t:
            return None
        if t in self.names:
            return self.names[t]
        hits = [n for n in self.names if len(n) >= 4 and re.search(rf"(?<!\w){re.escape(n)}(?!\w)", t)]
        return self.names[max(hits, key=len)] if hits else None

    def nearest_road(self, lat: float, lon: float, ward: str = "") -> str:
        pool = [r for r in self.roads if not ward or r["ward_code"] == ward] or self.roads
        return min(pool, key=lambda r: metres(lat, lon, *self.mid[r["road_id"]]))["road_id"]

    def road_in_text(self, text: str, ward: str) -> str:
        t = fold(text)
        for name in self.road_names:
            if name in t:
                pool = [r for r in self.roads if fold(r["road_name"]) == name]
                in_ward = [r for r in pool if r["ward_code"] == ward]
                return (in_ward or pool)[0]["road_id"]
        return ""


def severity_by_type(data: Dataset) -> dict[str, int]:
    """Severity per kind of issue, read off the SLA hours BMC attached to its work orders (24 h is severity 5)."""
    hours: dict[str, list[int]] = defaultdict(list)
    for wo in data.work_orders:
        hours[wo["work_type"]].append(int(wo.num("sla_hours")))
    out = {}
    for kind, hs in hours.items():
        hs.sort()
        out[kind] = SEVERITY_BY_SLA.get(hs[len(hs) // 2], 3)
    return out


def run(data: Dataset, now: datetime | None = None) -> list[Linked]:
    gaz = Gazetteer(data)
    wo_of: dict[str, Row] = {}
    for job in data.work_orders:
        for cid in filter(None, job["linked_complaint_ids"].split("|")):
            wo_of[cid] = job
    severity = severity_by_type(data)
    sla = {s: h for h, s in SEVERITY_BY_SLA.items()}
    latest = max(filter(None, (ts(c["received_at"]) for c in data.complaints)))
    now = now or latest

    out: list[Linked] = []
    for c in data.complaints:
        text = " ".join((c["description"], c["photo_description"]))
        # ward
        ward, ward_from = c["ward_code"], "complaint"
        loc = gaz.locality(c["locality_text"]) or gaz.locality(c["description"])
        has_gps = bool(c["lat"] and c["lon"])
        if not ward:
            if loc:
                ward, ward_from = loc["ward_code"], "locality"
            elif has_gps:
                road = gaz.nearest_road(c.num("lat"), c.num("lon"))
                ward, ward_from = next(r["ward_code"] for r in data.roads if r["road_id"] == road), "gps"
            else:
                ward_from = "none"
        # category: what the work order fixed, when there is one; otherwise read from the words
        wo = wo_of.get(c["complaint_id"])
        reported, guessed = c["category_reported"], infer_category(text)
        if wo:
            category, category_from = wo["work_type"], "work order"
        elif guessed and guessed != reported:
            category, category_from = guessed, "text"
        elif reported in VAGUE:
            category, category_from = reported or "Other", "reported-vague"
        else:
            category, category_from = reported, "reported"
        # road
        if wo:
            road_id, road_from = wo["road_id"], "work order"
            ward = ward or wo["ward_code"]
        elif rid := gaz.road_in_text(c["description"], ward):
            road_id, road_from = rid, "name in text"
        elif has_gps:
            road_id, road_from = gaz.nearest_road(c.num("lat"), c.num("lon"), ward), "gps"
        elif loc:
            road_id, road_from = gaz.nearest_road(loc.num("lat"), loc.num("lon"), ward), "locality"
        else:
            road_id, road_from = "", "none"
        # state
        status = c["status"]
        if wo:
            failed = wo.flag("reopened_within_30d")
            dup = status.startswith("Closed - Duplicate")
            state = "duplicate of a fixed one" if dup else ("fixed, failed" if failed else "fixed")
        elif status in OPEN:
            received = ts(c["received_at"])
            hours = sla.get(severity.get(category, 3), 72)
            overdue = received is not None and (now - received).total_seconds() / 3600 > hours
            state = "open, overdue" if overdue else "open"
        elif status.startswith("Rejected"):
            state = "rejected"
        elif status.startswith("Forwarded"):
            state = "forwarded"
        else:
            state = "closed, no work order"
        out.append(
            Linked(
                complaint_id=c["complaint_id"],
                received_at=c["received_at"],
                ward_code=ward,
                ward_from=ward_from,
                category=category,
                category_from=category_from,
                road_id=road_id,
                road_from=road_from,
                status=status,
                work_order_id=wo["work_order_id"] if wo else "",
                issue_id="",
                state=state,
                language=c["language"],
                upvotes=int(c.num("upvotes")),
                cite=c.cite,
            )
        )
    _issues(out)
    return out


def _issues(rows: list[Linked]) -> None:
    """One issue per work order; open complaints about the same road and kind of problem, a week or less apart, are
    one issue too, so ten people reporting one pothole count once."""
    for r in rows:
        if r.work_order_id:
            r.issue_id = "I-" + r.work_order_id
    pending: dict[tuple[str, str, str, bool], list[Linked]] = defaultdict(list)
    for r in rows:
        if not r.issue_id:
            pending[(r.ward_code, r.road_id or "?", r.category, r.state.startswith("open"))].append(r)
    n = 0
    for (_, road, _, _), group in sorted(pending.items()):
        group.sort(key=lambda r: r.received_at)
        last: datetime | None = None
        for r in group:
            t = ts(r.received_at)
            still_open = r.state.startswith("open")  # an open problem is one problem however long it waits
            if road == "?" or last is None or t is None or (not still_open and (t - last).days > CLUSTER_DAYS):
                n += 1
            r.issue_id = (
                f"I-OPEN-{n:05d}" if r.state.startswith("open") else f"I-{r.state.split(',')[0].upper()}-{n:05d}"
            )
            last = t


def summary(rows: list[Linked]) -> dict[str, Any]:
    by_state: dict[str, int] = defaultdict(int)
    for r in rows:
        by_state[r.state] += 1
    issues = {r.issue_id for r in rows}
    open_issues = {r.issue_id for r in rows if r.state.startswith("open")}
    return {
        "complaints": len(rows),
        "issues": len(issues),
        "open_issues": len(open_issues),
        "by_state": dict(sorted(by_state.items())),
        "ward_inferred": sum(r.ward_from in {"locality", "gps"} for r in rows),
        "ward_unknown": sum(r.ward_from == "none" for r in rows),
        "category_corrected": sum(r.category_from == "text" for r in rows),
        "languages": dict(sorted(_count(r.language for r in rows).items())),
    }


def _count(items: Any) -> dict[str, int]:
    out: dict[str, int] = defaultdict(int)
    for i in items:
        out[i] += 1
    return out
