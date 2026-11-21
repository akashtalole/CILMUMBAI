"""Run everything and write the results (SPEC-040/R6): CSVs a judge or journalist can open, and one JSON bundle the
API serves. The same data always gives the same flags, scores and ranking; only the Claude-written text can vary."""

from __future__ import annotations

import csv
import json
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from hishob.rupee import audit, link, narrate, plan, score
from hishob.rupee.audit import inr
from hishob.rupee.data import DEFAULT_DIR, Dataset, load

DEFAULT_OUT = Path("var/rupee")


def _csv(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        w = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow({k: ("|".join(v) if isinstance(v, list) else v) for k, v in r.items()})


def compute(data: Dataset, client: Any = None) -> dict[str, Any]:
    flags = audit.run(data)
    linked = link.run(data)
    cards = score.run(data, flags, linked)
    planned = plan.run(data, linked, cards["wards"])
    for c in cards["contractors"]:
        c["note"] = narrate.write(client, "contractor", narrate.contractor_facts(c))
    for w in cards["wards"]:
        w["note"] = narrate.write(client, "ward", narrate.ward_facts(w, planned["wards"][w["ward_code"]]))
    spend = sum(wo.num("cost_inr") for wo in data.work_orders)
    budget = sum(w.num("monsoon_repair_budget_inr_2025") for w in data.wards)
    counts = Counter(f.rule for f in flags)
    summary = {
        "built_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "dataset": str(data.root),
        "work_orders": len(data.work_orders),
        "spend_inr": int(spend),
        "budget_inr": int(budget),
        "failed_spend_inr": int(sum(wo.num("cost_inr") for wo in data.work_orders if wo.flag("reopened_within_30d"))),
        "money_in_question_inr": audit.at_risk(flags),
        "flags": {
            r: {
                "label": audit.RULES[r],
                "count": counts.get(r, 0),
                "amount_inr": sum(f.amount_inr for f in flags if f.rule == r),
            }
            for r in audit.RULES
        },
        "complaints": link.summary(linked),
        "severity": link.severity_by_type(data),
        "thresholds": {
            "overbilled_ratio": audit.OVERBILL_RATIO,
            "duplicate_days": audit.DUPLICATE_DAYS,
            "duplicate_cost_gap": audit.DUPLICATE_COST_GAP,
            "plan_weights": plan.WEIGHTS,
        },
        "written_by": dict(Counter(x["note"]["by"] for x in cards["contractors"] + cards["wards"])),
    }
    return {
        "summary": summary,
        "flags": [f.as_dict() for f in flags],
        "complaints": [r.as_dict() for r in linked],
        "contractors": cards["contractors"],
        "wards": cards["wards"],
        "plan": planned,
    }


def write(bundle: dict[str, Any], out: Path) -> list[Path]:
    out.mkdir(parents=True, exist_ok=True)
    paths = []
    p = out / "bundle.json"
    p.write_text(json.dumps(bundle, ensure_ascii=False), encoding="utf-8")
    paths.append(p)
    p = out / "flags.csv"
    _csv(
        p,
        bundle["flags"],
        [
            "work_order_id",
            "rule",
            "reason",
            "amount_inr",
            "ward_code",
            "contractor_id",
            "contractor_name",
            "road_id",
            "evidence",
        ],
    )
    paths.append(p)
    p = out / "complaints_linked.csv"
    _csv(p, bundle["complaints"], list(bundle["complaints"][0].keys()) if bundle["complaints"] else [])
    paths.append(p)
    rows = []
    for code, w in bundle["plan"]["wards"].items():
        for rank, i in enumerate(w["items"], start=1):
            rows.append({"ward_code": code, "rank": rank, **i, "why": " | ".join(i["why"])})
    p = out / "next_rupee.csv"
    _csv(
        p,
        rows,
        [
            "ward_code",
            "rank",
            "issue_id",
            "road_id",
            "road_name",
            "category",
            "risk",
            "method",
            "cost_inr",
            "funded",
            "under_dlp",
            "complaints",
            "why",
        ],
    )
    paths.append(p)
    p = out / "scorecards.csv"
    _csv(
        p,
        [
            {
                "kind": "contractor",
                "id": c["contractor_id"],
                "name": c["name"],
                **c["scores"],
                "overall": c["overall"],
                "grade": c["grade"],
                "note": c["note"]["text"],
            }
            for c in bundle["contractors"]
        ]
        + [
            {
                "kind": "ward",
                "id": w["ward_code"],
                "name": w["ward_name"],
                **w["scores"],
                "overall": w["overall"],
                "grade": w["grade"],
                "note": w["note"]["text"],
            }
            for w in bundle["wards"]
        ],
        ["kind", "id", "name", "durability", "speed", "billing", "backlog", "overall", "grade", "note"],
    )
    paths.append(p)
    return paths


def run(data_dir: Path | str = DEFAULT_DIR, out: Path | str = DEFAULT_OUT, client: Any = None) -> dict[str, Any]:
    bundle = compute(load(data_dir), client)
    write(bundle, Path(out))
    return bundle


def headline(bundle: dict[str, Any]) -> str:
    s = bundle["summary"]
    lines = [
        f"{s['work_orders']} work orders, {inr(s['spend_inr'])} spent of {inr(s['budget_inr'])} budgeted",
        f"{inr(s['failed_spend_inr'])} went on fixes that failed within 30 days",
        f"{inr(s['money_in_question_inr'])} in question:",
    ]
    lines += [f"  {r:12} {v['count']:4}  {inr(v['amount_inr']):>14}  {v['label']}" for r, v in s["flags"].items()]
    c = s["complaints"]
    lines.append(f"{c['complaints']} complaints -> {c['issues']} issues, {c['open_issues']} still open")
    lines.append(f"notes written by: {s['written_by']}")
    return "\n".join(lines)
