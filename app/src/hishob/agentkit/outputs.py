"""Check and arrange an audit run's outputs in code (SPEC-011/R2 to R6; constitution C3, C5).

The agents are told the rules; this module enforces them. It decides where each file goes from the Challenger's
verdict, not from the folder the agent wrote it to, and it checks every file for banned words, people named
other than by post, and references that do not resolve or whose values the cited fact does not contain.
"""

from __future__ import annotations

import json
import re
import unicodedata
from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import PurePosixPath
from typing import Any

from hishob.agentkit.redact import honorific_names

FACT_ID = re.compile(r"f_[0-9a-f]{32}")
FACT_MARK = re.compile(r"\s?\[\s*f_[0-9a-f]{32}(?:\s*,\s*f_[0-9a-f]{32})*\s*\]")
SHA256 = re.compile(r"\b[0-9a-f]{64}\b")
VERDICT = re.compile(r"^[\s>*_-]*verdict[\s*_]*:[\s*_`]*(publish with changes|publish|hold)\b", re.I | re.M)

# R5. Conclusions, not facts. English by stem; Marathi and Hindi by stem too, so case endings are caught.
# The Marathi and Hindi lists are a first draft, to be settled with the language reviewer and the lawyer.
BANNED_EN = re.compile(r"\b(?:fraud\w*|scam(?:s|med|ming|mer\w*)?|corrupt\w*|cartels?|nexus\w*|siphon\w*)\b", re.I)
BANNED_DEVANAGARI = tuple(
    unicodedata.normalize("NFC", w)
    for w in (
        "घोटाळ",  # mr: scam
        "भ्रष्ट",  # mr, hi: corrupt, corruption
        "लाचखोर",  # mr: bribe-taking
        "फसवणूक",  # mr: fraud
        "फसवणुकी",
        "संगनमत",  # mr: collusion
        "साटेलोटे",  # mr: nexus
        "हडपल",  # mr: siphoned off
        "घोटाल",  # hi: scam
        "धोखाधड़ी",  # hi: fraud
        "धोखाधडी",
        "जालसाज़",  # hi: fraud
        "जालसाज",
        "सांठगांठ",  # hi: nexus
        "साठगांठ",
        "गठजोड़",  # hi: nexus
        "हड़प",  # hi: siphon
    )
)

REQUIRED = ("ward-brief.md", "gaps.jsonl")
DRAFT_NAME = re.compile(r"^(?:rti|complaint)-[\w-]+\.md$|^questions(?:-[\w-]+)?\.md$")
CASE_NAME = re.compile(r"^case-[\w-]+(?:\.challenge)?\.md$")


@dataclass(frozen=True)
class Violation:
    path: str
    kind: str  # banned_word, named_person, unsourced, unknown_fact, bad_gap, missing, unexpected
    detail: str


@dataclass
class OutputCheck:
    violations: list[Violation] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.violations

    def paths(self) -> set[str]:
        return {v.path for v in self.violations}


@dataclass
class Arranged:
    """Outputs under their canonical paths, and the cases held with the reason for each."""

    files: dict[str, bytes]
    held: dict[str, str] = field(default_factory=dict)  # held/<case>.md -> reason
    unexpected: list[str] = field(default_factory=list)


# ---- layout (R2, R3, R4) ---------------------------------------------------------------------------------------


def canonical(path: str) -> str | None:
    """Where a file belongs by its name, whatever folder the agent used. None for files that do not belong."""
    name = PurePosixPath(path).name
    if name in REQUIRED:
        return name
    if CASE_NAME.match(name):
        return f"cases/{name}"  # held or not is decided from the verdict, in arrange()
    if DRAFT_NAME.match(name):
        return f"drafts/{name}"
    return None


def verdict(review: str) -> str | None:
    found = VERDICT.findall(review)
    return found[-1].lower() if found else None


def arrange(raw: dict[str, bytes]) -> Arranged:
    files: dict[str, bytes] = {}
    unexpected = []
    for path, body in sorted(raw.items()):
        target = canonical(path)
        if target is None:
            unexpected.append(path)
        else:
            files[target] = body
    out = Arranged(files, unexpected=unexpected)
    for case in [p for p in sorted(files) if p.startswith("cases/") and not p.endswith(".challenge.md")]:
        review_path = case.removesuffix(".md") + ".challenge.md"
        review = files.get(review_path)
        found = verdict(review.decode("utf-8", errors="replace")) if review is not None else None
        if found in {"publish", "publish with changes"}:
            continue
        reason = (
            "not reviewed by a Challenger"
            if review is None
            else "the Challenger's review has no verdict"
            if found is None
            else "the Challenger held it"
        )
        hold(out, case, reason)
    for review_path in [p for p in sorted(files) if p.endswith(".challenge.md")]:
        if review_path.removesuffix(".challenge.md") + ".md" not in files:
            files.pop(review_path)  # a review whose case was held or never written is not published alone
    return out


def hold(out: Arranged, path: str, reason: str) -> None:
    """Move a file (and a case's review) to held/, recording why."""
    for source in (path, path.removesuffix(".md") + ".challenge.md"):
        if source in out.files:
            name = PurePosixPath(source).name
            out.files[f"held/{name}"] = out.files.pop(source)
    out.held[f"held/{PurePosixPath(path).name}"] = reason


# ---- content (R5, R6) ------------------------------------------------------------------------------------------


def banned_words(text: str) -> list[str]:
    text = unicodedata.normalize("NFC", text)
    found = [m.group(0) for m in BANNED_EN.finditer(text)]
    for word in re.findall(r"[ऀ-ॿ]+", text):
        if any(stem in word for stem in BANNED_DEVANAGARI):
            found.append(word)
    return found


def blocks(markdown: str) -> list[str]:
    """Paragraphs and table rows: the unit a source reference must sit in. Headings and table headers are skipped."""
    lines = markdown.splitlines()
    out: list[str] = []
    paragraph: list[str] = []
    for i, line in enumerate(lines):
        stripped = line.strip()
        is_row = stripped.startswith("|")
        header = is_row and i + 1 < len(lines) and re.match(r"^\|[\s:|-]+\|$", lines[i + 1].strip())
        if not stripped or stripped.startswith("#") or is_row:
            if paragraph:
                out.append(" ".join(paragraph))
                paragraph = []
            if is_row and not header and not re.match(r"^\|[\s:|-]+\|$", stripped):
                out.append(stripped)
            continue
        paragraph.append(stripped)
    if paragraph:
        out.append(" ".join(paragraph))
    return out


def check_outputs(
    files: dict[str, bytes],
    http: Any,
    *,
    token: str | None = None,
    private_names: Iterable[str] = (),
    contractor_names: Iterable[str] = (),
    keep_names: Iterable[str] = (),
) -> OutputCheck:
    """Check arranged outputs. `private_names` are people seen in tool results who are not elected representatives;
    `contractor_names` are contractors seen, which must carry a source wherever they are named in the brief or a
    case; `keep_names` are elected representatives, who may be named."""
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    result = OutputCheck()
    keep = list(keep_names)
    private = [n for n in private_names if n.lower() not in {k.lower() for k in keep}]
    contractors = [c for c in contractor_names if c]
    for missing in [name for name in REQUIRED if name not in files]:
        result.violations.append(Violation(missing, "missing", f"{missing} was not written"))
    for path, body in sorted(files.items()):
        if path.startswith("held/"):
            continue  # held files are never published; the reviewer reads them with the reason
        text = body.decode("utf-8", errors="replace")
        for word in banned_words(text):
            result.violations.append(Violation(path, "banned_word", word))
        for name in honorific_names(text, keep):
            result.violations.append(Violation(path, "named_person", name))
        for name in private:
            if name.lower() in text.lower():
                result.violations.append(Violation(path, "named_person", name))
        if path == "gaps.jsonl":
            result.violations += _check_gaps(path, text)
            continue
        if path.endswith(".challenge.md"):
            continue
        sourced = path == "ward-brief.md" or path.startswith("cases/")
        result.violations += _check_references(path, text, http, headers, sourced, contractors)
    return result


def _check_gaps(path: str, text: str) -> list[Violation]:
    out = []
    for n, line in enumerate(text.splitlines(), 1):
        if not line.strip():
            continue
        try:
            gap = json.loads(line)
        except json.JSONDecodeError:
            out.append(Violation(path, "bad_gap", f"line {n} is not JSON"))
            continue
        if not isinstance(gap, dict) or not gap.get("record_needed") or not gap.get("holder"):
            out.append(Violation(path, "bad_gap", f"line {n} lacks record_needed or holder"))
    return out


def _check_references(
    path: str, text: str, http: Any, headers: dict[str, str], sourced: bool, contractors: list[str]
) -> list[Violation]:
    out: list[Violation] = []
    if not sourced:  # drafts: every reference must resolve; their dates and periods are requests, not claims
        cited = sorted(set(FACT_ID.findall(text)))
        if cited:
            check = http.post("/answers/check", json={"text": "-", "cited_fact_ids": cited}, headers=headers).json()
            out += [Violation(path, "unknown_fact", c["text"]) for c in check["unmatched"] if c["kind"] == "fact_id"]
        return out
    for block in blocks(text):
        cited = sorted(set(FACT_ID.findall(block)))
        body = SHA256.sub("", FACT_ID.sub("", FACT_MARK.sub("", block))).strip()
        if not body:
            continue
        check = http.post("/answers/check", json={"text": body, "cited_fact_ids": cited}, headers=headers).json()
        for claim in check["unmatched"]:
            if claim["kind"] == "fact_id":
                out.append(Violation(path, "unknown_fact", claim["text"]))
            elif claim["kind"] in {"amount", "date", "identifier"}:
                out.append(Violation(path, "unsourced", f"{claim['kind']} {claim['text']!r} in: {_short(block)}"))
        matched_names = [c["text"].lower() for c in check["matched"] if c["kind"] == "name"]
        for contractor in contractors:
            if contractor.lower() in body.lower() and not any(
                contractor.lower() in m or m in contractor.lower() for m in matched_names
            ):
                out.append(Violation(path, "unsourced", f"contractor {contractor!r} in: {_short(block)}"))
    return out


def _short(block: str) -> str:
    return block if len(block) <= 120 else block[:117] + "…"
