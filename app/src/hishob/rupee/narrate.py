"""Plain-language scorecards and ward summaries, written by Claude and checked in code (SPEC-040/R5).

Claude gets the computed figures and nothing else, and writes for a citizen or a corporator. The text is kept only
if it passes the same checks as the audit desk: no banned conclusions ("fraud", "scam", ...), and every number in it
must be one of the figures it was given, so it cannot invent or misremember one. Otherwise, or with no API key, a
written template is used. Either way the page says which it is.
"""

from __future__ import annotations

import json
import re
from collections.abc import Callable
from typing import Any

from hishob.agentkit.outputs import banned_words
from hishob.rupee.audit import inr

MODEL = "claude-sonnet-5-5"
SYSTEM = """You write short, fair, plain-language accountability notes about Mumbai monsoon road repairs for citizens
and corporators. The data is synthetic and the contractors are fictional.
Rules:
- Use only the figures given. Do not compute new numbers; you may round a percentage to a whole number.
- No accusations or conclusions about intent: never say fraud, scam, corrupt, cartel, siphon, or similar.
  Say what the records show, e.g. "billed above the rate card", "paid for while under its guarantee".
- Give context before blame: a score of 50 means "as expected for these jobs, given method, rain and ward".
- Plain words, no jargon. Explain DLP once as "the contractor's guarantee period".
- Output plain text only, no headings, no lists, no markdown."""

NUMBER = re.compile(r"(?<![\w/])(\d[\d,]*(?:\.\d+)?)\s*(lakh|crore|%)?", re.I)
ALWAYS = {7.0, 30.0, 50.0, 100.0, 2024.0, 2025.0, 24.0, 48.0, 72.0, 120.0, 168.0, 1.0, 2.0, 3.0}


def allowed_numbers(facts: Any) -> set[float]:
    out = set(ALWAYS)

    def walk(v: Any) -> None:
        if isinstance(v, bool):
            return
        if isinstance(v, (int, float)):
            x = float(v)
            for y in (x, x * 100, x / 1e5, x / 1e7):
                for d in (0, 1, 2):
                    out.add(round(y, d))
        elif isinstance(v, str):
            for m in NUMBER.finditer(v):
                walk(float(m.group(1).replace(",", "")))
        elif isinstance(v, dict):
            for x in v.values():
                walk(x)
        elif isinstance(v, list):
            for x in v:
                walk(x)

    walk(facts)
    return out


def unknown_numbers(text: str, facts: Any) -> list[str]:
    ok = allowed_numbers(facts)
    bad = []
    for m in NUMBER.finditer(text):
        raw = m.group(1).replace(",", "")
        try:
            x = float(raw)
        except ValueError:
            continue
        if not any(abs(x - a) <= 0.051 for a in ok):
            bad.append(m.group(0).strip())
    return bad


def check(text: str, facts: Any, max_words: int) -> list[str]:
    problems = [f"banned word: {w}" for w in banned_words(text)]
    problems += [f"number not in the figures: {n}" for n in unknown_numbers(text, facts)]
    if len(text.split()) > max_words * 1.15:
        problems.append(f"too long: {len(text.split())} words")
    if not text.strip():
        problems.append("empty")
    return problems


def contractor_facts(c: dict[str, Any]) -> dict[str, Any]:
    return {
        "name": c["name"],
        "grade": c["grade"],
        "overall_score": c["overall"],
        "scores": c["scores"],
        "jobs": c["jobs"],
        "spend": inr(c["spend_inr"]),
        "wards": c["wards"],
        "ward_count": len(c["wards"]),
        "reopened_within_30_days_pct": round(100 * c["reopen_rate"]),
        "expected_reopened_pct_for_these_jobs": round(100 * c["expected_reopen_rate"]),
        "sla_met_pct": round(100 * c["sla_met_rate"]),
        "expected_sla_met_pct": round(100 * c["expected_sla_met_rate"]),
        "median_bill_vs_rate_card": c["median_bill_vs_rate_card"],
        "overbilling_threshold_x_rate_card": 1.5,
        "jobs_billed_over_1_5x_rate_card": c["flags"]["overbilled"]["count"],
        "duplicate_bills": c["flags"]["duplicate"]["count"],
        "paid_jobs_on_roads_under_guarantee": c["flags"]["dlp_paid"]["count"],
    }


def ward_facts(w: dict[str, Any], plan: dict[str, Any]) -> dict[str, Any]:
    top = plan["items"][:3]
    return {
        "ward": f"{w['ward_code']} ({w['ward_name']})",
        "grade": w["grade"],
        "overall_score": w["overall"],
        "scores": w["scores"],
        "budget": inr(w["budget_inr"]),
        "spent": inr(w["spend_inr"]),
        "budget_used_pct": round(100 * (w["budget_used"] or 0)),
        "jobs": w["jobs"],
        "spent_on_fixes_that_failed_within_30_days": inr(w["failed_spend_inr"]),
        "money_in_question": inr(w["money_in_question_inr"]),
        "overbilling_threshold_x_rate_card": 1.5,
        "billed_over_1_5x_rate_card": w["flags"]["overbilled"]["count"],
        "duplicate_bills": w["flags"]["duplicate"]["count"],
        "paid_on_roads_under_guarantee": w["flags"]["dlp_paid"]["count"],
        "paid_on_roads_under_guarantee_amount": inr(w["flags"]["dlp_paid"]["amount_inr"]),
        "open_overdue_issues": w["open_overdue_issues"],
        "low_lying_index": w["low_lying_index"],
        "top_contractor_by_spend": w["by_contractor"][0]["name"] if w["by_contractor"] else None,
        "remaining_budget": inr(plan["remaining_inr"]),
        "next_fixes": [
            {
                "road": i["road_name"],
                "issue": i["category"],
                "risk": i["risk"],
                "method": i["method"],
                "cost": inr(i["cost_inr"]),
                "why": i["why"][:3],
            }
            for i in top
        ],
    }


PROMPTS = {
    "contractor": (
        "Write a scorecard for this contractor for citizens, under 120 words: speed, how long repairs "
        "lasted, cost against the rate card, and one thing they should improve.",
        120,
    ),
    "ward": (
        "Write a one-paragraph summary for this ward's corporator and residents, under 170 words: where the "
        "money went, whether the repairs held, what is in question, and the next three fixes and why.",
        170,
    ),
}


def template_contractor(f: dict[str, Any]) -> str:
    better = "fewer" if f["reopened_within_30_days_pct"] <= f["expected_reopened_pct_for_these_jobs"] else "more"
    improve = (
        "keep bills within the rate card"
        if f["jobs_billed_over_1_5x_rate_card"] >= 10
        else "make repairs last longer"
        if better == "more"
        else "finish more jobs within the SLA"
    )
    return (
        f"{f['name']}: grade {f['grade']} ({f['overall_score']} of 100, where 50 is as expected for these jobs). "
        f"It did {f['jobs']} jobs worth {f['spend']} across {len(f['wards'])} wards. "
        f"{f['sla_met_pct']}% met the SLA, against {f['expected_sla_met_pct']}% expected. "
        f"{f['reopened_within_30_days_pct']}% failed within 30 days, {better} than the "
        f"{f['expected_reopened_pct_for_these_jobs']}% expected for the same methods and weather. "
        f"{f['jobs_billed_over_1_5x_rate_card']} jobs were billed above 1.5 times the rate card and "
        f"{f['duplicate_bills']} look like duplicate bills. One thing to improve: {improve}."
    )


def template_ward(f: dict[str, Any]) -> str:
    nxt = "; ".join(f"{n['issue'].lower()} on {n['road']} (risk {n['risk']})" for n in f["next_fixes"])
    return (
        f"Ward {f['ward']} spent {f['spent']} of its {f['budget']} monsoon repair budget ({f['budget_used_pct']}%) on "
        f"{f['jobs']} jobs. {f['spent_on_fixes_that_failed_within_30_days']} went on fixes that failed within 30 days. "
        f"{f['money_in_question']} is in question: {f['billed_over_1_5x_rate_card']} bills above 1.5 times the rate "
        f"card, {f['duplicate_bills']} likely duplicate bills, and {f['paid_on_roads_under_guarantee']} repairs paid "
        f"for on roads still under the contractor's guarantee period ({f['paid_on_roads_under_guarantee_amount']}). "
        f"{f['open_overdue_issues']} reported problems are open past their SLA. Fix next: {nxt}."
    )


TEMPLATES: dict[str, Callable[[dict[str, Any]], str]] = {"contractor": template_contractor, "ward": template_ward}


def write(client: Any, kind: str, facts: dict[str, Any], *, model: str = MODEL) -> dict[str, Any]:
    ask, words = PROMPTS[kind]
    fallback = {"text": TEMPLATES[kind](facts), "by": "template", "problems": []}
    if client is None:
        return fallback
    try:
        message = client.messages.create(
            model=model,
            max_tokens=4000,
            system=SYSTEM,
            messages=[
                {"role": "user", "content": f"{ask}\n\nFigures:\n{json.dumps(facts, ensure_ascii=False, indent=1)}"}
            ],
        )
        text = "".join(getattr(b, "text", "") for b in message.content).strip()
        cut = getattr(message, "stop_reason", None) == "max_tokens"
    except Exception as e:
        return {**fallback, "problems": [f"api: {type(e).__name__}"]}
    problems = check(text, facts, words) + (["cut off before the end"] if cut else [])
    if problems:
        return {**fallback, "problems": problems, "rejected": text}
    return {"text": text, "by": model, "problems": []}
