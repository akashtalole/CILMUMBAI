"""Aggregate scores, compare them with the last released baseline, and decide the gate (SPEC-012/R3, R5, R6).

A report holds, for each set, the mean of every metric overall, by language and by route, plus the cost and
duration of the run. The gate looks at overall and per language: if any score falls below its baseline by more
than the tolerance, it fails unless an owner has recorded an approval for exactly that score.
"""

from __future__ import annotations

import json
from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from hishob.evals.datasets import EVALS_DIR
from hishob.evals.scoring import ItemScore

EPS = 1e-9


def aggregate(items: list[ItemScore]) -> dict[str, Any]:
    def means(group: list[ItemScore]) -> dict[str, float]:
        sums: dict[str, list[float]] = defaultdict(list)
        for item in group:
            for metric, value in item.metrics.items():
                if value is not None:
                    sums[metric].append(value)
        return {m: round(sum(v) / len(v), 4) for m, v in sorted(sums.items())}

    by_language: dict[str, list[ItemScore]] = defaultdict(list)
    by_route: dict[str, list[ItemScore]] = defaultdict(list)
    for item in items:
        by_language[item.language].append(item)
        by_route[item.route].append(item)
    return {
        "n": len(items),
        "overall": means(items),
        "by_language": {k: means(v) for k, v in sorted(by_language.items())},
        "by_route": {k: means(v) for k, v in sorted(by_route.items())},
    }


def build_report(
    sets: dict[str, list[ItemScore]],
    *,
    cost_usd: dict[str, float | None],
    duration_s: dict[str, float],
    commit: str | None = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    """The report: scores per set, the failed items with their reasons, cost and duration (R6)."""
    return {
        "created_at": (now or datetime.now(UTC)).isoformat(timespec="seconds"),
        "commit": commit,
        "sets": {name: aggregate(items) for name, items in sets.items()},
        "failures": {
            name: [{"id": i.id, "language": i.language, "route": i.route, "notes": i.notes} for i in items if i.notes]
            for name, items in sets.items()
        },
        "cost_usd": {**{k: v for k, v in cost_usd.items()}, "total": round(sum(v or 0 for v in cost_usd.values()), 4)},
        "duration_s": {**{k: round(v, 1) for k, v in duration_s.items()}, "total": round(sum(duration_s.values()), 1)},
    }


def load_baseline(root: Path = EVALS_DIR) -> dict[str, Any]:
    data: dict[str, Any] = json.loads((root / "baseline.json").read_text(encoding="utf-8"))
    return data


def load_approvals(root: Path = EVALS_DIR) -> list[dict[str, Any]]:
    path = root / "approvals.jsonl"
    return (
        [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
        if path.exists()
        else []
    )


@dataclass(frozen=True)
class Delta:
    key: str  # set.metric.group, e.g. questions.values.mr
    baseline: float
    score: float

    @property
    def change(self) -> float:
        return round(self.score - self.baseline, 4)


@dataclass(frozen=True)
class Regression:
    delta: Delta
    approved_by: str | None = None


def compare(report: dict[str, Any], baseline: dict[str, Any]) -> list[Delta]:
    """Every score present in both, overall, by language and by route (R3)."""
    deltas: list[Delta] = []
    for name, now in report["sets"].items():
        before = (baseline.get("scores") or {}).get(name)
        if not before:
            continue
        groups: list[tuple[str, dict[str, float], dict[str, float]]] = [
            ("all", now["overall"], before.get("overall", {}))
        ]
        for kind in ("by_language", "by_route"):
            for group, scores in now[kind].items():
                groups.append((group, scores, before.get(kind, {}).get(group, {})))
        for group, scores, previous in groups:
            for metric, score in scores.items():
                if metric in previous:
                    deltas.append(Delta(f"{name}.{metric}.{group}", previous[metric], score))
    return deltas


def gate(report: dict[str, Any], baseline: dict[str, Any], approvals: list[dict[str, Any]]) -> list[Regression]:
    """Regressions beyond the tolerance, in overall or any language. An approval waives one only for the score it
    names or a higher one, and only with an approver and a reason (R5)."""
    tolerance = float(baseline.get("tolerance", 0.1))
    languages = {"all", "mr", "hi", "en"}
    out = []
    for delta in compare(report, baseline):
        if delta.key.rsplit(".", 1)[1] not in languages or delta.change >= -tolerance - EPS:
            continue
        approval = next(
            (
                a
                for a in approvals
                if a.get("key") == delta.key
                and str(a.get("reason", "")).strip()
                and str(a.get("approver", "")).strip()
                and delta.score >= float(a.get("approved_score", 2)) - EPS
            ),
            None,
        )
        out.append(Regression(delta, approval["approver"] if approval else None))
    return out


def blocking(regressions: list[Regression]) -> list[Regression]:
    return [r for r in regressions if r.approved_by is None]


def render_markdown(report: dict[str, Any], baseline: dict[str, Any], regressions: list[Regression]) -> str:
    deltas = {d.key: d for d in compare(report, baseline)}
    lines = [
        "# Evaluation report",
        "",
        f"Run {report['created_at']}" + (f" at commit `{report['commit']}`" if report.get("commit") else ""),
    ]
    lines += [
        "",
        f"Cost: ${report['cost_usd']['total']:.2f}. Duration: {report['duration_s']['total']:.0f} s. "
        + (", ".join(f"{k} ${v:.2f}" for k, v in report["cost_usd"].items() if k != "total" and v is not None) or ""),
    ]
    for name, scores in report["sets"].items():
        lines += [
            "",
            f"## {name} ({scores['n']} items)",
            "",
            "| Group | Metric | Score | Baseline | Change |",
            "|---|---|---|---|---|",
        ]
        groups: list[tuple[str, dict[str, float]]] = [("all", scores["overall"])]
        groups += [(g, s) for g, s in scores["by_language"].items()] + [
            (f"route: {g}", s) for g, s in scores["by_route"].items()
        ]
        for group, metrics in groups:
            for metric, score in metrics.items():
                key = f"{name}.{metric}.{group.removeprefix('route: ')}"
                d = deltas.get(key)
                lines.append(
                    f"| {group} | {metric} | {score:.2f} | {d.baseline:.2f} | {d.change:+.2f} |"
                    if d
                    else f"| {group} | {metric} | {score:.2f} | n/a | |"
                )
        failed = report["failures"].get(name) or []
        if failed:
            lines += ["", "Items with problems:", ""] + [f"- `{f['id']}`: " + "; ".join(f["notes"]) for f in failed]
    lines += ["", "## Gate", ""]
    if not regressions:
        lines.append(
            "No score fell below its baseline by more than the tolerance."
            if baseline.get("scores")
            else "No baseline recorded yet: nothing to compare."
        )
    for r in regressions:
        status = f"approved by {r.approved_by}" if r.approved_by else "**blocking**"
        lines.append(
            f"- `{r.delta.key}`: {r.delta.baseline:.2f} to {r.delta.score:.2f} ({r.delta.change:+.2f}), {status}"
        )
    return "\n".join(lines) + "\n"
