"""Run the sets against a system and produce the report (SPEC-012)."""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from hishob.evals import datasets, report, scoring
from hishob.evals.live import ask_all

SETS = ("extraction", "questions", "refusals")


@dataclass
class Systems:
    """What is being evaluated. Tests pass stubs; `hishob eval run` passes the real desks."""

    extract: Callable[[list[datasets.ExtractionItem]], tuple[dict[str, scoring.ExtractionResult], float | None]]
    ask: Callable[[str, str], scoring.AskResult]
    workers: int = 4


def run_sets(
    systems: Systems, which: tuple[str, ...] = SETS, root: Path = datasets.EVALS_DIR, commit: str | None = None
) -> dict[str, Any]:
    scored: dict[str, list[scoring.ItemScore]] = {}
    cost: dict[str, float | None] = {}
    duration: dict[str, float] = {}
    for name in which:
        started = time.monotonic()
        if name == "extraction":
            items = datasets.load_extraction(root)
            results, spent = systems.extract(items)
            scored[name] = [scoring.score_extraction(i, results[i.id]) for i in items]
        elif name == "questions":
            qs = datasets.load_questions(root)
            answers = ask_all(systems.ask, [(q.question, q.language) for q in qs], systems.workers)
            scored[name] = [scoring.score_question(q, a) for q, a in zip(qs, answers, strict=True)]
            spent = _sum(a.cost_usd for a in answers)
        elif name == "refusals":
            rs = datasets.load_refusals(root)
            answers = ask_all(systems.ask, [(r.question, r.language) for r in rs], systems.workers)
            scored[name] = [scoring.score_refusal(r, a.text) for r, a in zip(rs, answers, strict=True)]
            spent = _sum(a.cost_usd for a in answers)
        else:
            raise ValueError(f"unknown set {name}")
        cost[name], duration[name] = spent, time.monotonic() - started
    return report.build_report(scored, cost_usd=cost, duration_s=duration, commit=commit)


def _sum(values: Any) -> float | None:
    known = [v for v in values if v is not None]
    return round(sum(known), 4) if known else None
