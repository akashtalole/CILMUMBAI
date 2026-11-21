"""The repair auditor (SPEC-040/R2). Rules in code, each with its threshold written down, so a flag can be checked
by anyone with the data and a calculator. Each flag names the work order, says why in one line, puts a rupee figure
on it and cites the rows it rests on.

The thresholds come from the data dictionary: normal jobs vary 20 to 30% around the rate card, so a bill above 1.5x
is outside normal variation; a duplicate is the same road and the same kind of work within a week with no complaint
behind it; a road under its Defect Liability Period should be repaired by the original contractor at no cost to BMC.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import asdict, dataclass, field
from itertools import pairwise
from typing import Any

from hishob.rupee.data import Dataset, Row, ts

OVERBILL_RATIO = 1.5  # above the 20-30% normal band, with room to spare
NORMAL_TOP = 1.3  # the top of normal variation: what we count as the fair price of an over-billed job
DUPLICATE_DAYS = 7
DUPLICATE_COST_GAP = 0.15  # a copy bills within 15% of the original
REPEAT_DAYS = 30

RULES = {
    "overbilled": "Billed well above the rate card",
    "duplicate": "Same road, same work, billed twice within a week, no complaint behind the second bill",
    "dlp_paid": "BMC paid for a repair on a road still under the contractor's Defect Liability Period",
    "repeat_paid": "A fix that failed within 30 days was paid for again, to the same contractor",
}
CORE = ("overbilled", "duplicate", "dlp_paid")  # the money problems; repeat_paid is a lead, not a finding


@dataclass
class Flag:
    work_order_id: str
    rule: str
    reason: str
    amount_inr: int  # the money this flag puts in question
    ward_code: str
    contractor_id: str
    contractor_name: str
    road_id: str
    evidence: list[str] = field(default_factory=list)
    detail: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def expected_cost(wo: Row, rate: Row | None) -> float | None:
    if rate is None:
        return None
    standard = rate.num("standard_rate_inr")
    return standard * wo.num("area_sqm") if rate["unit"] == "per sqm" else standard


def inr(amount: float) -> str:
    """Indian grouping: 1,23,456."""
    n = round(amount)
    s, sign = str(abs(n)), "-" if n < 0 else ""
    if len(s) <= 3:
        return f"{sign}₹{s}"
    head, tail = s[:-3], s[-3:]
    groups: list[str] = []
    while len(head) > 2:
        groups.insert(0, head[-2:])
        head = head[:-2]
    if head:
        groups.insert(0, head)
    return f"{sign}₹{','.join(groups)},{tail}"


def _flag(wo: Row, rule: str, reason: str, amount: float, evidence: list[str], **detail: Any) -> Flag:
    return Flag(
        work_order_id=wo["work_order_id"],
        rule=rule,
        reason=reason,
        amount_inr=round(amount),
        ward_code=wo["ward_code"],
        contractor_id=wo["contractor_id"],
        contractor_name=wo["contractor_name"],
        road_id=wo["road_id"],
        evidence=[wo.cite, *evidence],
        detail=detail,
    )


def overbilled(data: Dataset) -> list[Flag]:
    rates = data.by("rate_card", "repair_method")
    out = []
    for wo in data.work_orders:
        rate = rates.get(wo["repair_method"])
        expected = expected_cost(wo, rate)
        if not expected or rate is None:
            continue
        ratio = wo.num("cost_inr") / expected
        if ratio > OVERBILL_RATIO:
            basis = (
                f"{wo['area_sqm']} sqm x {inr(rate.num('standard_rate_inr'))}"
                if rate["unit"] == "per sqm"
                else "per job"
            )
            reason = (
                f"{wo['repair_method']} billed {inr(wo.num('cost_inr'))}, {ratio:.1f}x the rate card "
                f"({inr(expected)}, {basis}); normal jobs vary 20-30%"
            )
            excess = wo.num("cost_inr") - expected * NORMAL_TOP
            out.append(
                _flag(
                    wo, "overbilled", reason, excess, [rate.cite], ratio=round(ratio, 2), expected_inr=round(expected)
                )
            )
    return out


def duplicates(data: Dataset) -> list[Flag]:
    groups: dict[tuple[str, str], list[Row]] = defaultdict(list)
    for wo in data.work_orders:
        groups[(wo["road_id"], wo["work_type"])].append(wo)
    out = []
    for wo in data.work_orders:
        if wo["linked_complaint_ids"]:
            continue
        done = ts(wo["completed_at"])
        if done is None:
            continue
        best: tuple[float, Row] | None = None
        for other in groups[(wo["road_id"], wo["work_type"])]:
            other_done = ts(other["completed_at"])
            if other is wo or other_done is None:
                continue
            gap_days = abs((done - other_done).total_seconds()) / 86400
            cost_gap = abs(other.num("cost_inr") - wo.num("cost_inr")) / max(wo.num("cost_inr"), 1)
            if gap_days <= DUPLICATE_DAYS and cost_gap <= DUPLICATE_COST_GAP and (best is None or gap_days < best[0]):
                best = (gap_days, other)
        if best:
            gap_days, original = best
            reason = (
                f"{wo['work_type']} on {wo['road_id']} billed {inr(wo.num('cost_inr'))} with no complaint linked, "
                f"{gap_days:.0f} day{'' if round(gap_days) == 1 else 's'} from {original['work_order_id']} "
                f"for the same work "
                f"({inr(original.num('cost_inr'))})"
            )
            out.append(
                _flag(
                    wo,
                    "duplicate",
                    reason,
                    wo.num("cost_inr"),
                    [original.cite],
                    original=original["work_order_id"],
                    days_apart=round(gap_days, 1),
                )
            )
    return out


def dlp_paid(data: Dataset) -> list[Flag]:
    roads = data.by("roads", "road_id")
    out = []
    for wo in data.work_orders:
        road = roads.get(wo["road_id"])
        if road is None or not road.flag("under_dlp") or wo.num("cost_inr") <= 0:
            continue
        resurfaced, done = ts(road["last_resurfaced"]), ts(wo["completed_at"])
        if resurfaced and done and done < resurfaced:
            continue  # the repair came before the resurfacing that started the DLP
        reason = (
            f"{road['road_name']} ({road['road_id']}) was resurfaced on {road['last_resurfaced']} and is under its "
            f"Defect Liability Period, yet BMC paid {inr(wo.num('cost_inr'))}; the original contractor should have "
            f"repaired it at no cost"
        )
        out.append(
            _flag(wo, "dlp_paid", reason, wo.num("cost_inr"), [road.cite], last_resurfaced=road["last_resurfaced"])
        )
    return out


def repeat_paid(data: Dataset) -> list[Flag]:
    groups: dict[tuple[str, str], list[Row]] = defaultdict(list)
    for wo in data.work_orders:
        groups[(wo["road_id"], wo["work_type"])].append(wo)
    out = []
    for jobs in groups.values():
        jobs.sort(key=lambda r: r["completed_at"])
        for first, later in pairwise(jobs):
            a, b = ts(first["completed_at"]), ts(later["completed_at"])
            if not (a and b) or not first.flag("reopened_within_30d"):
                continue
            if (
                first["contractor_id"] == later["contractor_id"]
                and (b - a).days <= REPEAT_DAYS
                and later["linked_complaint_ids"]
            ):
                reason = (
                    f"{first['work_order_id']} failed within 30 days and the same contractor was paid "
                    f"{inr(later.num('cost_inr'))} to fix it again {(b - a).days} days later"
                )
                out.append(
                    _flag(
                        later, "repeat_paid", reason, later.num("cost_inr"), [first.cite], failed=first["work_order_id"]
                    )
                )
    return out


def run(data: Dataset) -> list[Flag]:
    flags = overbilled(data) + duplicates(data) + dlp_paid(data) + repeat_paid(data)
    order = {r: i for i, r in enumerate(RULES)}
    return sorted(flags, key=lambda f: (order[f.rule], -f.amount_inr, f.work_order_id))


def at_risk(flags: list[Flag], rules: tuple[str, ...] = CORE) -> int:
    """Money in question, counting each work order once at its largest flag."""
    per: dict[str, int] = {}
    for f in flags:
        if f.rule in rules:
            per[f.work_order_id] = max(per.get(f.work_order_id, 0), f.amount_inr)
    return sum(per.values())
