"""Scan the evaluation sets for personal data of private individuals (SPEC-012/R7; constitution C7).

Looks for phone numbers, email addresses, Aadhaar-shaped numbers and people named after an honorific, in every
dataset file. Organisations and offices are not personal data. Marathi and Hindi questions that merely ask for a
person's address are fine; one that contains an address or number is not.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from hishob.agentkit.redact import EMAIL, PHONE, honorific_names
from hishob.evals.datasets import EVALS_DIR

AADHAAR = re.compile(r"(?<!\d)\d{4}\s\d{4}\s\d{4}(?!\d)")
# Expected-output regexes in refusals.jsonl legitimately contain phone-number patterns: do not scan those fields.
TEXT_SUFFIXES = {".jsonl", ".json", ".md", ".txt"}


@dataclass(frozen=True)
class Finding:
    path: str
    kind: str
    text: str


def scan(root: Path = EVALS_DIR) -> list[Finding]:
    findings: list[Finding] = []
    for path in sorted(p for p in root.rglob("*") if p.is_file() and p.suffix in TEXT_SUFFIXES):
        text = path.read_text(encoding="utf-8")
        if path.name == "refusals.jsonl":
            text = _without_patterns(text)
        relative = path.relative_to(root).as_posix()
        for kind, pattern in (("email", EMAIL), ("phone", PHONE), ("id_number", AADHAAR)):
            findings += [Finding(relative, kind, m.group(0)) for m in pattern.finditer(text)]
        findings += [Finding(relative, "named_person", name) for name in honorific_names(text)]
    return findings


def _without_patterns(text: str) -> str:
    """Drop the must_not and must_any arrays from refusal lines: they hold regexes, not data."""
    import json

    kept = []
    for line in text.splitlines():
        if line.strip():
            row = json.loads(line)
            row.pop("must_not", None)
            row.pop("must_any", None)
            kept.append(json.dumps(row, ensure_ascii=False))
    return "\n".join(kept)
