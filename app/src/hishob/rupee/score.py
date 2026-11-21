"""Fair scorecards for contractors and wards (SPEC-040/R3).

Fair means a contractor is compared with what anyone would have achieved on the same jobs, not with a city average.
For each job we work out the expected chance of failing within 30 days (from every job with the same repair method
and the same rain in the week after) and of missing the SLA (same kind of work, same flood-proneness of ward, same
rain during the job). A score of 50 means "as expected for these jobs"; above is better, below is worse. Volume is
shown but never scored, so doing more work is not punished.

We tested the context before using it: in this data rain after a repair did not change how often it failed, the
repair method did, and low-lying wards missed more SLAs. The strata keep whatever matters and wash out what doesn't.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Callable, Iterable
from datetime import date, timedelta
from typing import Any

from hishob.rupee.audit import CORE, Flag, at_risk, expected_cost
from hishob.rupee.data import Dataset, Row, ts
from hishob.rupee.link import Linked

# A contractor answers for its own bills; paying for a road under DLP is the ward's approval, so it counts there.
CONTRACTOR_RULES = ("overbilled", "duplicate")
HEAVY_MM = 64.5  # IMD "heavy rain" in a day
COLABA_ZONES = {"Zone 1", "Zone 2"}  # the island city; the suburbs read Santacruz


class Context:
    def __init__(self, data: Dataset) -> None:
        self.wards = data.by("wards", "ward_code")
        self.rain = {(r["station"], r["date"]): r.num("rainfall_mm") for r in data.rainfall_daily}

    def station(self, ward: str) -> str:
        w = self.wards.get(ward)
        return "Colaba" if w and w["zone"] in COLABA_ZONES else "Santacruz"

    def heavy_between(self, ward: str, start: date, end: date) -> bool:
        st, d = self.station(ward), start
        while d <= end:
            if self.rain.get((st, d.isoformat()), 0.0) >= HEAVY_MM:
                return True
            d += timedelta(days=1)
        return False

    def low_lying(self, ward: str) -> bool:
        w = self.wards.get(ward)
        return bool(w and w.num("low_lying_index") >= 0.6)

    def reopen_stratum(self, wo: Row) -> tuple[Any, ...]:
        done = ts(wo["completed_at"])
        rain = bool(done and self.heavy_between(wo["ward_code"], done.date(), done.date() + timedelta(days=7)))
        return (wo["repair_method"], rain)

    def sla_stratum(self, wo: Row) -> tuple[Any, ...]:
        a, b = ts(wo["assigned_at"]), ts(wo["completed_at"])
        rain = bool(a and b and self.heavy_between(wo["ward_code"], a.date(), b.date()))
        return (wo["work_type"], self.low_lying(wo["ward_code"]), rain)


def rates(jobs: Iterable[Row], key: Callable[[Row], tuple[Any, ...]], bad: Callable[[Row], bool]) -> dict[Any, float]:
    n: dict[Any, int] = defaultdict(int)
    k: dict[Any, int] = defaultdict(int)
    for j in jobs:
        s = key(j)
        n[s] += 1
        k[s] += bad(j)
    return {s: k[s] / n[s] for s in n}


def fair(observed: float, expected: float) -> int:
    """50 is as expected; 100 is no failures at all against an expected rate; 0 is double the expected rate."""
    if expected <= 0:
        return 50 if observed <= 0 else 0
    return round(max(0.0, min(100.0, 50 + 50 * (1 - observed / expected))))


def grade(score: float) -> str:
    return "A" if score >= 70 else "B" if score >= 60 else "C" if score >= 45 else "D" if score >= 30 else "E"


def _money(jobs: list[Row], key: str) -> list[dict[str, Any]]:
    tot: dict[str, float] = defaultdict(float)
    cnt: dict[str, int] = defaultdict(int)
    for j in jobs:
        tot[j[key]] += j.num("cost_inr")
        cnt[j[key]] += 1
    return [{"name": k, "jobs": cnt[k], "spend_inr": int(v)} for k, v in sorted(tot.items(), key=lambda kv: -kv[1])]


class Scorer:
    def __init__(self, data: Dataset, flags: list[Flag], linked: list[Linked]) -> None:
        self.data, self.flags, self.linked = data, flags, linked
        self.ctx = Context(data)
        jobs = data.work_orders
        self.reopen_rate = rates(jobs, self.ctx.reopen_stratum, lambda j: j.flag("reopened_within_30d"))
        self.miss_rate = rates(jobs, self.ctx.sla_stratum, lambda j: not j.flag("sla_met"))
        self.rates = data.by("rate_card", "repair_method")
        spend = sum(j.num("cost_inr") for j in jobs) or 1.0
        self.city_share: dict[tuple[str, ...], float] = {
            rules: at_risk(flags, rules) / spend for rules in (CORE, CONTRACTOR_RULES)
        }

    def _common(self, jobs: list[Row], flags: list[Flag], rules: tuple[str, ...]) -> dict[str, Any]:
        n = len(jobs) or 1
        reopened = sum(j.flag("reopened_within_30d") for j in jobs)
        missed = sum(not j.flag("sla_met") for j in jobs)
        exp_reopen = sum(self.reopen_rate[self.ctx.reopen_stratum(j)] for j in jobs)
        exp_miss = sum(self.miss_rate[self.ctx.sla_stratum(j)] for j in jobs)
        spend = sum(j.num("cost_inr") for j in jobs)
        ratios = sorted(
            j.num("cost_inr") / e for j in jobs if (e := expected_cost(j, self.rates.get(j["repair_method"])))
        )
        by_rule: dict[str, dict[str, int]] = {}
        for rule in (*CORE, "repeat_paid"):
            fs = [f for f in flags if f.rule == rule]
            by_rule[rule] = {"count": len(fs), "amount_inr": sum(f.amount_inr for f in fs)}
        risk = at_risk(flags, rules)
        durability = fair(reopened / n, exp_reopen / n)
        speed = fair(missed / n, exp_miss / n)
        billing = fair(risk / spend if spend else 0, self.city_share[rules])
        return {
            "jobs": len(jobs),
            "spend_inr": int(spend),
            "failed_spend_inr": int(sum(j.num("cost_inr") for j in jobs if j.flag("reopened_within_30d"))),
            "reopened": reopened,
            "reopen_rate": round(reopened / n, 3),
            "expected_reopen_rate": round(exp_reopen / n, 3),
            "sla_met_rate": round(1 - missed / n, 3),
            "expected_sla_met_rate": round(1 - exp_miss / n, 3),
            "median_bill_vs_rate_card": round(ratios[len(ratios) // 2], 2) if ratios else None,
            "flags": by_rule,
            "money_in_question_inr": at_risk(flags),
            "billing_basis": list(rules),
            "scores": {"durability": durability, "speed": speed, "billing": billing},
            "evidence": [j.cite for j in jobs if j.flag("reopened_within_30d")][:5]
            + [f.evidence[0] for f in flags][:5],
        }

    def contractor(self, c: Row) -> dict[str, Any]:
        jobs = [j for j in self.data.work_orders if j["contractor_id"] == c["contractor_id"]]
        flags = [f for f in self.flags if f.contractor_id == c["contractor_id"]]
        out = {
            "contractor_id": c["contractor_id"],
            "name": c["contractor_name"],
            "empanelled_since": c["empanelled_since"],
            "cite": c.cite,
            **self._common(jobs, flags, CONTRACTOR_RULES),
        }
        s = out["scores"]
        out["overall"] = round((s["durability"] + s["speed"] + s["billing"]) / 3)
        out["grade"] = grade(out["overall"])
        out["wards"] = sorted({j["ward_code"] for j in jobs})
        out["by_method"] = _money(jobs, "repair_method")
        return out

    def ward(self, w: Row) -> dict[str, Any]:
        code = w["ward_code"]
        jobs = [j for j in self.data.work_orders if j["ward_code"] == code]
        flags = [f for f in self.flags if f.ward_code == code]
        out = {
            "ward_code": code,
            "ward_name": w["ward_name"],
            "zone": w["zone"],
            "office": w["assistant_commissioner_office"],
            "budget_inr": int(w.num("monsoon_repair_budget_inr_2025")),
            "low_lying_index": w.num("low_lying_index"),
            "population_est": int(w.num("population_est")),
            "crews": int(w.num("engineering_crews")),
            "cite": w.cite,
            **self._common(jobs, flags, CORE),
        }
        out["budget_used"] = round(out["spend_inr"] / out["budget_inr"], 3) if out["budget_inr"] else None
        mine = [r for r in self.linked if r.ward_code == code]
        issues = {r.issue_id for r in self.linked}
        open_overdue = {r.issue_id for r in mine if r.state == "open, overdue"}
        city_overdue = len({r.issue_id for r in self.linked if r.state == "open, overdue"}) / (len(issues) or 1)
        ward_issues = {r.issue_id for r in mine}
        s = out["scores"]
        s["backlog"] = fair(len(open_overdue) / (len(ward_issues) or 1), city_overdue)
        out["complaints"] = len(mine)
        out["open_overdue_issues"] = len(open_overdue)
        out["overall"] = round(sum(s.values()) / len(s))
        out["grade"] = grade(out["overall"])
        out["by_contractor"] = _money(jobs, "contractor_name")
        out["by_method"] = _money(jobs, "repair_method")
        out["by_work_type"] = _money(jobs, "work_type")
        return out


def run(data: Dataset, flags: list[Flag], linked: list[Linked]) -> dict[str, list[dict[str, Any]]]:
    s = Scorer(data, flags, linked)
    return {
        "contractors": sorted((s.contractor(c) for c in data.contractors), key=lambda x: -x["overall"]),
        "wards": [s.ward(w) for w in data.wards],
    }
