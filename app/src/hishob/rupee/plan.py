"""The next-rupee planner (SPEC-040/R4). For each ward: the open issues ranked by risk, the method that lasts for
each, its likely cost, and which ones the ward's remaining budget pays for.

Risk is a weighted sum of six parts, each 0 to 1 and each shown with the score so a ward officer can see why an
issue is high: how severe it is, flooding at that spot, traffic, road accidents there, a hospital or school that
depends on the road, and how many people reported it. A road still under its Defect Liability Period goes to the
original contractor at no cost to BMC, whatever its rank.
"""

from __future__ import annotations

import math
import statistics
from collections import defaultdict
from dataclasses import asdict, dataclass, field
from typing import Any

from hishob.rupee.data import Dataset, Row, metres
from hishob.rupee.link import Linked, severity_by_type

WEIGHTS = {"severity": 0.25, "flood": 0.20, "traffic": 0.15, "accidents": 0.15, "facilities": 0.15, "demand": 0.10}
NEAR_M = 500  # a flood hotspot this close to the road's midpoint floods it
FACILITY_M = 400
ROAD_CAUSES = {"Pothole", "Uneven road / open chamber", "Waterlogged road", "Skid on wet road"}
SEVERITY_WEIGHT = {"Minor": 1, "Grievous": 3, "Fatal": 6}
WATER_KINDS = {"Waterlogging", "Choked drain / nullah overflow", "Open or broken manhole", "Road cave-in"}
COLABA_ZONES = {"Zone 1", "Zone 2"}


@dataclass
class Item:
    issue_id: str
    ward_code: str
    road_id: str
    road_name: str
    category: str
    complaints: list[str]
    first_reported: str
    risk: int
    parts: dict[str, float]
    why: list[str]
    method: str
    method_reopen_rate: float
    cheapest_method: str
    cheapest_reopen_rate: float
    cost_inr: int
    under_dlp: bool
    funded: bool = False
    evidence: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


class Planner:
    def __init__(self, data: Dataset) -> None:
        self.data = data
        self.roads = data.by("roads", "road_id")
        self.traffic = data.by("traffic", "road_id")
        self.mid = {
            r["road_id"]: ((r.num("start_lat") + r.num("end_lat")) / 2, (r.num("start_lon") + r.num("end_lon")) / 2)
            for r in data.roads
        }
        self.severity = severity_by_type(data)
        wards = data.by("wards", "ward_code")
        rain = {(r["station"], r["date"]): r.num("rainfall_mm") for r in data.rainfall_daily}
        self.big_tides = len({t["date"] for t in data.tides if t.flag("big_tide_flag")})
        # how often each hotspot's flooding rain fell last season, at its own station
        self.flood_days: dict[str, int] = {}
        for h in data.flood_hotspots:
            w = wards.get(h["ward_code"])
            st = "Colaba" if w and w["zone"] in COLABA_ZONES else "Santacruz"
            self.flood_days[h["hotspot_id"]] = sum(
                1 for (s, _), mm in rain.items() if s == st and mm >= h.num("flood_threshold_mm_per_day")
            )
        self.accidents: dict[str, list[Row]] = defaultdict(list)
        for a in data.accidents:
            if a["probable_cause"] in ROAD_CAUSES:
                self.accidents[a["road_id"]].append(a)
        self.max_acc = max((self._acc_weight(r) for r in self.roads), default=1) or 1
        self.max_veh = max((t.num("peak_hour_vehicles") for t in data.traffic), default=1) or 1
        self.max_bus = max((t.num("bus_routes_count") for t in data.traffic), default=1) or 1
        self.methods = self._methods()

    def _acc_weight(self, road_id: str) -> float:
        return sum(SEVERITY_WEIGHT.get(a["severity"], 1) for a in self.accidents.get(road_id, []))

    def _methods(self) -> dict[str, list[dict[str, Any]]]:
        """For each kind of issue, the methods BMC used, how often each failed within 30 days and its median bill."""
        jobs: dict[tuple[str, str], list[Row]] = defaultdict(list)
        for wo in self.data.work_orders:
            jobs[(wo["work_type"], wo["repair_method"])].append(wo)
        out: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for (kind, method), js in jobs.items():
            if len(js) < 10:
                continue  # too few jobs to say how long the method lasts
            out[kind].append(
                {
                    "method": method,
                    "jobs": len(js),
                    "reopen_rate": round(sum(j.flag("reopened_within_30d") for j in js) / len(js), 3),
                    "median_cost_inr": int(statistics.median(j.num("cost_inr") for j in js)),
                }
            )
        for kind in out:
            out[kind].sort(key=lambda m: (m["reopen_rate"], m["median_cost_inr"]))
        return out

    def parts(
        self, road_id: str, category: str, reports: int, upvotes: int
    ) -> tuple[dict[str, float], list[str], list[str]]:
        why: list[str] = []
        cites: list[str] = []
        road = self.roads.get(road_id)
        sev = self.severity.get(category, 3)
        p = {"severity": sev / 5}
        if sev >= 4:
            why.append(f"{category} is a severity {sev} issue (SLA {24 if sev == 5 else 48} hours)")
        # flood
        flood = 0.0
        if road_id in self.mid:
            lat, lon = self.mid[road_id]
            for h in self.data.flood_hotspots:
                d = metres(lat, lon, h.num("lat"), h.num("lon"))
                if d <= NEAR_M:
                    days = self.flood_days[h["hotspot_id"]]
                    f = (
                        0.5 * h.num("years_flagged_last_5") / 5
                        + 0.3 * min(1.0, days / 10)
                        + 0.2 * h.flag("tide_sensitive")
                    )
                    f *= 1.0 if category in WATER_KINDS else 0.6
                    if f > flood:
                        flood = f
                        tide = (
                            f", floods at big tides ({self.big_tides} days last season)"
                            if h.flag("tide_sensitive")
                            else ""
                        )
                        why_flood = (
                            f"{int(d)} m from {h['name']}, which floods above {h['flood_threshold_mm_per_day']} mm "
                            f"a day ({days} such days last season){tide}"
                        )
                        cite_flood = h.cite
            if flood:
                why.append(why_flood)
                cites.append(cite_flood)
        p["flood"] = round(flood, 3)
        # traffic
        t = self.traffic.get(road_id)
        if t:
            p["traffic"] = round(
                0.5 * t.num("congestion_index_0_10") / 10
                + 0.25 * t.num("peak_hour_vehicles") / self.max_veh
                + 0.25 * t.num("bus_routes_count") / self.max_bus,
                3,
            )
            if p["traffic"] >= 0.6:
                why.append(
                    f"{int(t.num('peak_hour_vehicles')):,} vehicles at peak hour, "
                    f"{int(t.num('bus_routes_count'))} bus routes"
                )
            cites.append(t.cite)
        else:
            p["traffic"] = 0.0
        # accidents
        acc = self.accidents.get(road_id, [])
        p["accidents"] = round(min(1.0, self._acc_weight(road_id) / self.max_acc), 3)
        if acc:
            fatal = sum(a["severity"] == "Fatal" for a in acc)
            why.append(f"{len(acc)} road-condition accidents here in 2024-25" + (f", {fatal} fatal" if fatal else ""))
            cites += [a.cite for a in acc[:3]]
        # facilities
        fac = 0.0
        named = ""
        for fa in self.data.facilities:
            if fa["ambulance_entry_road"] == road_id and fa["type"] == "Hospital":
                v = 1.0 if fa.flag("emergency_services") else 0.8
                if v > fac:
                    fac, named = v, f"the ambulance road to {fa['name']}"
                    cites.append(fa.cite)
            elif road_id in self.mid and metres(*self.mid[road_id], fa.num("lat"), fa.num("lon")) <= FACILITY_M:
                v = 0.5 if fa["type"] == "Hospital" else 0.4
                if v > fac:
                    fac, named = v, f"near {fa['name']}"
                    cites.append(fa.cite)
        p["facilities"] = fac
        if named:
            why.append(named[0].upper() + named[1:])
        # demand
        p["demand"] = round(min(1.0, math.log1p(reports + upvotes) / math.log1p(200)), 3)
        why.append(f"{reports} complaint{'s' if reports != 1 else ''}, {upvotes} 'me too'")
        if road and road.flag("under_dlp"):
            why.append(
                f"Under DLP since resurfacing on {road['last_resurfaced']}: the original contractor repairs it free"
            )
        return p, why, cites

    def items(self, linked: list[Linked]) -> list[Item]:
        groups: dict[str, list[Linked]] = defaultdict(list)
        for r in linked:
            if r.state.startswith("open") and r.road_id:
                groups[r.issue_id].append(r)
        out = []
        for issue, rs in groups.items():
            first = min(rs, key=lambda r: r.received_at)
            kinds = [r.category for r in rs if r.category in self.severity]
            category = max(set(kinds), key=kinds.count) if kinds else "Pothole"
            road = self.roads.get(first.road_id)
            parts, why, cites = self.parts(first.road_id, category, len(rs), sum(r.upvotes for r in rs))
            risk = round(100 * sum(WEIGHTS[k] * v for k, v in parts.items()))
            options = self.methods.get(category) or self.methods.get("Pothole", [])
            best: dict[str, Any] = (
                options[0] if options else {"method": "Inspect", "reopen_rate": 0.0, "median_cost_inr": 0}
            )
            cheap: dict[str, Any] = min(options, key=lambda m: m["median_cost_inr"]) if options else best
            dlp = bool(road and road.flag("under_dlp"))
            out.append(
                Item(
                    issue_id=issue,
                    ward_code=first.ward_code,
                    road_id=first.road_id,
                    road_name=road["road_name"] if road else "",
                    category=category,
                    complaints=sorted(r.complaint_id for r in rs),
                    first_reported=first.received_at,
                    risk=risk,
                    parts=parts,
                    why=why,
                    method=("Call the original contractor under DLP; " + best["method"]) if dlp else best["method"],
                    method_reopen_rate=best["reopen_rate"],
                    cheapest_method=cheap["method"],
                    cheapest_reopen_rate=cheap["reopen_rate"],
                    cost_inr=0 if dlp else best["median_cost_inr"],
                    under_dlp=dlp,
                    evidence=[r.cite for r in rs[:3]] + ([road.cite] if road else []) + cites,
                )
            )
        return sorted(out, key=lambda i: (-i.risk, i.first_reported, i.issue_id))


def run(data: Dataset, linked: list[Linked], wards: list[dict[str, Any]]) -> dict[str, Any]:
    planner = Planner(data)
    items = planner.items(linked)
    out: dict[str, Any] = {"weights": WEIGHTS, "methods": planner.methods, "wards": {}}
    for w in wards:
        code = w["ward_code"]
        remaining = w["budget_inr"] - w["spend_inr"]
        mine = [i for i in items if i.ward_code == code]
        left = max(0, remaining)
        for i in mine:
            if i.cost_inr <= left:
                i.funded = True
                left -= i.cost_inr
        out["wards"][code] = {
            "ward_code": code,
            "budget_inr": w["budget_inr"],
            "spent_inr": w["spend_inr"],
            "remaining_inr": remaining,
            "open_issues": len(mine),
            "funded": sum(i.funded for i in mine),
            "funded_cost_inr": sum(i.cost_inr for i in mine if i.funded),
            "unfunded_cost_inr": sum(i.cost_inr for i in mine if not i.funded),
            "free_under_dlp": sum(i.under_dlp for i in mine),
            "items": [i.as_dict() for i in mine],
        }
    out["city_top"] = [i.as_dict() for i in items[:25]]
    return out
