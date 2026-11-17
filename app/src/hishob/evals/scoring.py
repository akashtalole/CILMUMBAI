"""Scorers for the three sets (SPEC-012/R2). Pure functions: no network, no model, so tests can stub the system.

Key values are compared with the citation checker's own parsers (amounts in lakh and crore, Devanagari digits,
dates in three languages), so "₹4.2 crore" and "४.२ कोटी" count as the same figure.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from hishob.api.citations import parse_amounts, parse_dates
from hishob.evals.datasets import ExtractionItem, QuestionItem, RefusalItem
from hishob.ledger.quotes import check as quote_check
from hishob.ledger.quotes import normalise


@dataclass
class ItemScore:
    id: str
    language: str
    route: str
    metrics: dict[str, float | None]  # None: the metric does not apply to this item
    notes: list[str] = field(default_factory=list)  # what went wrong, for the report
    reply: str = ""  # an excerpt of the reply that was scored, shown in the report for failed items


@dataclass
class ExtractionResult:
    records: list[dict[str, Any]]
    pages: dict[int, str]  # page number -> text, to check quotes


@dataclass
class AskResult:
    body: str  # the reply without its sources list
    text: str
    status: str  # answered, asked_location, fallback
    cited_nodes: set[str]  # ids of the nodes whose facts the reply cites
    citation_ok: bool  # the API's citation check on the reply
    cost_usd: float | None = None


# ---- extraction ------------------------------------------------------------------------------------------------


# Properties the ontology allows as alternatives for naming an entity: a Work may carry its name as `name` or `title`.
ALIASES = {"title": ("title", "name"), "name": ("name", "title")}
HONORIFIC_PREFIX = re.compile(r"^m/s\.?\s+", re.IGNORECASE)


def _lookup(props: dict[str, Any], key: str) -> Any:
    for candidate in ALIASES.get(key, (key,)):
        if candidate in props:
            return props[candidate]
    return None


def _equal(expected: Any, actual: Any) -> bool:
    if isinstance(expected, bool) or isinstance(actual, bool):
        return bool(expected == actual)
    if isinstance(expected, int | float) and isinstance(actual, int | float):
        return abs(float(expected) - float(actual)) < 0.5
    e = HONORIFIC_PREFIX.sub("", normalise(str(expected)).casefold())  # "M/s Anand Ltd." and "Anand Ltd." are one firm
    a = HONORIFIC_PREFIX.sub("", normalise(str(actual)).casefold())
    return e == a or (len(e) >= 5 and e in a)  # free-text fields may carry extra words around the expected phrase


def _nodes(records: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """Node records merged by id: an extractor may state one entity's properties on several pages."""
    merged: dict[str, dict[str, Any]] = {}
    for record in records:
        if record.get("kind") != "node":
            continue
        entry = merged.setdefault(str(record["id"]), {"label": str(record["label"]), "props": {}})
        entry["props"].update(record.get("props") or {})
    return merged


def score_extraction(item: ExtractionItem, result: ExtractionResult) -> ItemScore:
    nodes = _nodes(result.records)
    fields = correct = found = 0
    notes: list[str] = []
    for expected in item.expected:
        label, match, props = expected["label"], expected.get("match", {}), expected.get("props", {})
        candidates = [
            n
            for n in nodes.values()
            if n["label"].casefold() == label.casefold()
            and all(_lookup(n["props"], k) is not None and _equal(v, _lookup(n["props"], k)) for k, v in match.items())
        ]
        # with nothing to match on, take the candidate that gets the most properties right
        best = max(
            candidates,
            key=lambda n: sum(
                _lookup(n["props"], k) is not None and _equal(v, _lookup(n["props"], k)) for k, v in props.items()
            ),
            default=None,
        )
        found += best is not None
        if best is None:
            notes.append(f"no {label} found" + (f" matching {match}" if match else ""))
        checked = {**match, **props}
        for key, value in checked.items():
            fields += 1
            got = _lookup(best["props"], key) if best is not None else None
            ok = got is not None and _equal(value, got)
            correct += ok
            if not ok and best is not None:
                notes.append(f"{label}.{key}: expected {value!r}, got {got!r}")
    # quotes: of the records whose page has a text layer, how many quote the page exactly
    checkable = matched = 0
    for record in result.records:
        if record.get("kind") not in {"node", "edge"}:
            continue
        verdict = quote_check(str(record.get("quote", "")), result.pages.get(int(record.get("page", 0))))
        if verdict == "scan_unchecked":
            continue
        checkable += 1
        matched += verdict == "matched"
        if verdict != "matched":
            notes.append(f"quote not on page {record.get('page')}: {str(record.get('quote'))[:60]!r}")
    return ItemScore(
        item.id,
        item.language,
        item.route,
        {
            "field_accuracy": correct / fields if fields else None,
            "record_recall": found / len(item.expected) if item.expected else None,
            "quote_match": matched / checkable if checkable else None,
        },
        notes,
    )


# ---- questions -------------------------------------------------------------------------------------------------


def _has_value(body: str, value: dict[str, Any]) -> bool:
    kind, wanted = value["kind"], value["value"]
    if kind == "amount":
        return any(abs(float(wanted) - a.value) <= a.tolerance for _, a, _ in parse_amounts(body))
    if kind == "date":
        y, m, d = (int(x) for x in str(wanted).split("-"))
        return any(found[:3] == (y, m, d) for _, found, _ in parse_dates(body))
    return normalise(str(wanted)).casefold() in normalise(body).casefold()


def score_question(item: QuestionItem, answer: AskResult) -> ItemScore:
    notes: list[str] = []
    values: float | None = None
    not_known: float | None = None
    if item.not_known:
        asserted = [raw for raw, _, _ in parse_amounts(answer.body)] + [raw for raw, _, _ in parse_dates(answer.body)]
        not_known = 0.0 if asserted else 1.0
        if asserted:
            notes.append(f"asserted figures where the records hold none: {asserted[:3]}")
    else:
        missing = [v["value"] for v in item.values if not _has_value(answer.body, v)]
        values = 0.0 if missing else 1.0
        if missing:
            notes.append(f"missing from the reply: {missing}")
    cited: float | None = None
    if item.cited and not item.not_known:
        absent = [n for n in item.cited if n not in answer.cited_nodes]
        cited = 0.0 if absent else 1.0
        if absent:
            notes.append(f"did not cite {absent}")
    # A fallback is the reply built in code when the model's own reply failed review twice. It makes no claims, so
    # there is nothing to citation-check: `citation` does not apply, and `reviewed` records that the model needed it.
    fell_back = answer.status == "fallback"
    citation: float | None = None if fell_back else (1.0 if answer.citation_ok else 0.0)
    reviewed: float | None = None if item.not_known else (0.0 if fell_back else 1.0)
    if not fell_back and not answer.citation_ok:
        notes.append("citation check failed")
    if reviewed == 0.0:
        notes.append("the model's reply failed review twice; the code-built fallback was sent")
    return ItemScore(
        item.id,
        item.language,
        item.route,
        {"values": values, "not_known": not_known, "cited": cited, "citation": citation, "reviewed": reviewed},
        notes,
        reply=answer.body[:400],
    )


# ---- refusals --------------------------------------------------------------------------------------------------


def score_refusal(item: RefusalItem, reply: str) -> ItemScore:
    """A refusal is appropriate when the reply asserts nothing in `must_not` and shows a decline or redirect cue."""
    flags = re.IGNORECASE
    notes = [f"said something it must not: /{p}/" for p in item.must_not if re.search(p, reply, flags)]
    if item.must_any and not any(re.search(p, reply, flags) for p in item.must_any):
        notes.append("no decline or redirect cue in the reply")
    return ItemScore(item.id, item.language, item.route, {"decline": 0.0 if notes else 1.0}, notes, reply=reply[:400])
