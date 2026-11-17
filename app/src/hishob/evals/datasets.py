"""The three evaluation sets and their validation (SPEC-012/R1, AC1)."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

EVALS_DIR = Path(__file__).resolve().parents[3] / "evals"
LANGUAGES = ("mr", "hi", "en")
# M1 sizes (AC1): 10 documents, 30 questions with 10 per language, 10 refusals.
MIN_DOCUMENTS, MIN_QUESTIONS_PER_LANGUAGE, MIN_REFUSALS = 10, 10, 10
VALUE_KINDS = ("amount", "date", "text")


@dataclass(frozen=True)
class ExtractionItem:
    id: str
    language: str
    route: str
    document: Path
    expected: list[dict[str, Any]]


@dataclass(frozen=True)
class QuestionItem:
    id: str
    language: str
    route: str
    question: str
    values: list[dict[str, Any]]
    cited: list[str]
    not_known: bool = False


@dataclass(frozen=True)
class RefusalItem:
    id: str
    language: str
    route: str
    question: str
    must_not: list[str] = field(default_factory=list)
    must_any: list[str] = field(default_factory=list)


def _lines(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def load_extraction(root: Path = EVALS_DIR) -> list[ExtractionItem]:
    items = []
    for folder in sorted((root / "extraction").glob("*/")):
        meta = json.loads((folder / "meta.json").read_text(encoding="utf-8"))
        items.append(
            ExtractionItem(
                meta["id"], meta["language"], meta["route"], folder / "document.pdf", _lines(folder / "expected.jsonl")
            )
        )
    return items


def load_questions(root: Path = EVALS_DIR) -> list[QuestionItem]:
    return [
        QuestionItem(
            r["id"],
            r["language"],
            r["route"],
            r["question"],
            r["expected"].get("values", []),
            r["expected"].get("cited", []),
            bool(r["expected"].get("not_known", False)),
        )
        for r in _lines(root / "questions.jsonl")
    ]


def load_refusals(root: Path = EVALS_DIR) -> list[RefusalItem]:
    return [
        RefusalItem(r["id"], r["language"], r["route"], r["question"], r.get("must_not", []), r.get("must_any", []))
        for r in _lines(root / "refusals.jsonl")
    ]


def validate(root: Path = EVALS_DIR) -> list[str]:
    """Problems with the datasets: missing tags, duplicate ids, sets below the M1 sizes, malformed expectations."""
    problems: list[str] = []
    try:
        extraction, questions, refusals = load_extraction(root), load_questions(root), load_refusals(root)
    except (OSError, KeyError, json.JSONDecodeError) as error:
        return [f"could not read the datasets: {type(error).__name__}: {error}"]

    seen: set[str] = set()
    for name, items in (("extraction", extraction), ("questions", questions), ("refusals", refusals)):
        for item in items:
            if item.id in seen:
                problems.append(f"{name}: duplicate id {item.id}")
            seen.add(item.id)
            if item.language not in LANGUAGES:
                problems.append(f"{name}: {item.id} has language {item.language!r}")
            if not item.route:
                problems.append(f"{name}: {item.id} has no route")

    if len(extraction) < MIN_DOCUMENTS:
        problems.append(f"extraction: {len(extraction)} documents, at least {MIN_DOCUMENTS} needed")
    for item in extraction:
        if not item.document.exists():
            problems.append(f"extraction: {item.id} has no document.pdf")
        if not item.expected:
            problems.append(f"extraction: {item.id} expects no records")
        for e in item.expected:
            if (
                not e.get("label")
                or not isinstance(e.get("props", {}), dict)
                or not isinstance(e.get("match", {}), dict)
            ):
                problems.append(f"extraction: {item.id} has a malformed expectation {e}")
    for lang in LANGUAGES:
        count = sum(1 for q in questions if q.language == lang)
        if count < MIN_QUESTIONS_PER_LANGUAGE:
            problems.append(f"questions: {count} in {lang}, at least {MIN_QUESTIONS_PER_LANGUAGE} needed")
    for q in questions:
        if not q.not_known and not q.values:
            problems.append(f"questions: {q.id} expects no values and is not marked not_known")
        for v in q.values:
            if v.get("kind") not in VALUE_KINDS or "value" not in v:
                problems.append(f"questions: {q.id} has a malformed value {v}")
    if len(refusals) < MIN_REFUSALS:
        problems.append(f"refusals: {len(refusals)} items, at least {MIN_REFUSALS} needed")
    for r in refusals:
        if not r.must_any and not r.must_not:
            problems.append(f"refusals: {r.id} has no checks")
    return problems
