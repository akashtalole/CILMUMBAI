"""Check that an answer only states what its cited facts say (SPEC-007/R5, R6; constitution C3).

Every amount, date, identifier and proper name in the answer must appear in a cited fact: in its
properties or in its quote. Amounts understand lakh and crore and the rounding the answer itself states
("₹4.2 crore" matches 4,20,00,000 and 4,24,00,000 but not 5 crore). Devanagari digits and Marathi and
Hindi month names are understood. Proper names are checked in Latin script only; Devanagari names are left
to the evaluation set until a reliable detector exists.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date
from typing import Any

from hishob.place.names import normalise

DEVANAGARI_DIGITS = str.maketrans("०१२३४५६७८९", "0123456789")
UNITS = {
    "crore": 10**7,
    "crores": 10**7,
    "cr": 10**7,
    "कोटी": 10**7,
    "कोटि": 10**7,
    "करोड़": 10**7,
    "करोड": 10**7,
    "lakh": 10**5,
    "lakhs": 10**5,
    "lac": 10**5,
    "lacs": 10**5,
    "लाख": 10**5,
}
CURRENCY = r"(?:₹|Rs\.?|INR|रु\.?|रुपये)"
NUMBER = r"\d[\d,]*(?:\.\d+)?"
AMOUNT = re.compile(
    rf"(?P<cur>{CURRENCY})\s*(?P<num>{NUMBER})(?:\s*(?P<unit>{'|'.join(map(re.escape, UNITS))}))?"
    rf"|(?P<num2>{NUMBER})\s*(?P<unit2>{'|'.join(map(re.escape, UNITS))})(?![A-Za-z])",
    re.IGNORECASE,
)
MONTHS = {
    **{
        m: i
        for i, m in enumerate(
            [
                "january",
                "february",
                "march",
                "april",
                "may",
                "june",
                "july",
                "august",
                "september",
                "october",
                "november",
                "december",
            ],
            start=1,
        )
    },
    **{
        m: i
        for i, m in enumerate(
            ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"], start=1
        )
    },
    "sept": 9,
    **{
        m: i
        for i, m in enumerate(
            ["जानेवारी", "फेब्रुवारी", "मार्च", "एप्रिल", "मे", "जून", "जुलै", "ऑगस्ट", "सप्टेंबर", "ऑक्टोबर", "नोव्हेंबर", "डिसेंबर"],
            start=1,
        )
    },
    **{
        m: i
        for i, m in enumerate(
            ["जनवरी", "फ़रवरी", "मार्च", "अप्रैल", "मई", "जून", "जुलाई", "अगस्त", "सितंबर", "अक्टूबर", "नवंबर", "दिसंबर"], start=1
        )
    },
    "फरवरी": 2,
    "सितम्बर": 9,
    "नवम्बर": 11,
    "दिसम्बर": 12,
    "अक्तूबर": 10,
}
_MONTH = "|".join(sorted(map(re.escape, MONTHS), key=len, reverse=True))
DATES = [
    (re.compile(r"\b(\d{4})-(\d{2})-(\d{2})\b"), "ymd"),
    (re.compile(r"\b(\d{1,2})[/.-](\d{1,2})[/.-](\d{4})\b"), "dmy"),
    (re.compile(rf"(?<!\w)(\d{{1,2}})\s+({_MONTH})\.?,?\s+(\d{{4}})\b", re.IGNORECASE), "d_month_y"),
    (re.compile(rf"(?<!\w)({_MONTH})\.?\s+(\d{{1,2}}),?\s+(\d{{4}})\b", re.IGNORECASE), "month_d_y"),
    (re.compile(rf"(?<!\w)({_MONTH})\.?,?\s+(\d{{4}})\b", re.IGNORECASE), "month_y"),
]
IDENTIFIER = re.compile(
    r"(?<![\w/])(?=[A-Za-z0-9_/-]*\d)(?=[A-Za-z0-9_/-]*[A-Za-z/_-])[A-Za-z0-9][A-Za-z0-9_/-]{5,}"
    r"|(?<!\d)\d{8,}(?!\d)"
)
# Capitalised words or initials ("S."), joined only by spaces, so a name never runs across a full stop.
_CAP = r"(?:[A-Z][a-z][\w'&-]*|[A-Z]\.|[A-Z]{2,})"
NAME = re.compile(rf"(?:M/s\.?\s+)?{_CAP}(?:\s+(?:{_CAP}|of|and|&))*\s+{_CAP}")
ALLOWED_NAMES = {
    normalise(n)
    for n in (
        "Aamcha Hishob",
        "Brihanmumbai Municipal Corporation",
        "Municipal Corporation",
        "Public Information Officer",
        "Right to Information",
        "RTI Act",
        "Ward Office",
        "Mumbai",
        "Maharashtra",
        "Standing Committee",
    )
}
WORD_DAYS = {"monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"}


@dataclass(frozen=True)
class Claim:
    kind: str  # amount, date, identifier, name, fact_id
    text: str


@dataclass
class CheckResult:
    ok: bool
    matched: list[Claim] = field(default_factory=list)
    unmatched: list[Claim] = field(default_factory=list)


@dataclass(frozen=True)
class _Amount:
    value: float
    tolerance: float


def parse_amounts(text: str) -> list[tuple[str, _Amount, tuple[int, int]]]:
    found = []
    for m in AMOUNT.finditer(text.translate(DEVANAGARI_DIGITS)):
        number = (m.group("num") or m.group("num2")).replace(",", "")
        unit = (m.group("unit") or m.group("unit2") or "").lower()
        multiplier = UNITS.get(unit, 1)
        decimals = len(number.split(".")[1]) if "." in number else 0
        value = float(number) * multiplier
        tolerance = 0.5 * 10 ** (-decimals) * multiplier if unit else 0.5
        found.append((m.group(0).strip(), _Amount(value, tolerance), m.span()))
    return found


def parse_dates(text: str) -> list[tuple[str, tuple[int, int, int | None], tuple[int, int]]]:
    """(matched text, (year, month, day or None), span)."""
    text = text.translate(DEVANAGARI_DIGITS)
    found: list[tuple[str, tuple[int, int, int | None], tuple[int, int]]] = []
    taken: list[tuple[int, int]] = []
    for pattern, shape in DATES:
        for m in pattern.finditer(text):
            if any(a < m.end() and m.start() < b for a, b in taken):
                continue
            g = m.groups()
            try:
                if shape == "ymd":
                    ymd: tuple[int, int, int | None] = (int(g[0]), int(g[1]), int(g[2]))
                elif shape == "dmy":
                    ymd = (int(g[2]), int(g[1]), int(g[0]))
                elif shape == "d_month_y":
                    ymd = (int(g[2]), MONTHS[g[1].lower()], int(g[0]))
                elif shape == "month_d_y":
                    ymd = (int(g[2]), MONTHS[g[0].lower()], int(g[1]))
                else:
                    ymd = (int(g[1]), MONTHS[g[0].lower()], None)
                if ymd[2] is not None:
                    date(ymd[0], ymd[1], ymd[2])
            except (KeyError, ValueError):
                continue
            taken.append(m.span())
            found.append((m.group(0), ymd, m.span()))
    return found


def _blank(text: str, spans: list[tuple[int, int]]) -> str:
    chars = list(text)
    for a, b in spans:
        chars[a:b] = " " * (b - a)
    return "".join(chars)


def check(answer: str, facts: list[dict[str, Any]], missing_ids: list[str] | None = None) -> CheckResult:
    """`facts` are ledger entries for the cited fact ids; `missing_ids` are cited ids that do not exist."""
    result = CheckResult(ok=True)
    for fid in missing_ids or []:
        result.unmatched.append(Claim("fact_id", fid))

    texts: list[str] = []
    amounts: list[float] = []
    dates: set[tuple[int, int, int | None]] = set()
    for fact in facts:
        quote = str(fact.get("quote", ""))
        texts.append(quote)
        amounts += [a.value for _, a, _ in parse_amounts(quote)]
        dates |= {d for _, d, _ in parse_dates(quote)}
        for value in (fact.get("props") or {}).values():
            if isinstance(value, bool):
                continue
            if isinstance(value, int | float):
                amounts.append(float(value))
            elif isinstance(value, str):
                texts.append(value)
                dates |= {d for _, d, _ in parse_dates(value)}
    corpus_norm = " | ".join(normalise(t) for t in texts)
    corpus_raw = " | ".join(texts).translate(DEVANAGARI_DIGITS).lower()

    text = answer.translate(DEVANAGARI_DIGITS)
    spans: list[tuple[int, int]] = []
    for raw, amount, span in parse_amounts(text):
        spans.append(span)
        hit = any(abs(v - amount.value) <= amount.tolerance for v in amounts)
        (result.matched if hit else result.unmatched).append(Claim("amount", raw))
    for raw, (year, month, day), span in parse_dates(_blank(text, spans)):
        spans.append(span)
        hit = any(fy == year and fm == month and (day is None or fd == day) for fy, fm, fd in dates)
        (result.matched if hit else result.unmatched).append(Claim("date", raw))
    rest = _blank(text, spans)
    for m in IDENTIFIER.finditer(rest):
        hit = m.group(0).lower() in corpus_raw
        (result.matched if hit else result.unmatched).append(Claim("identifier", m.group(0)))
        spans.append(m.span())
    rest = _blank(text, spans)
    for m in NAME.finditer(rest):
        name = m.group(0).strip()
        norm = normalise(name)
        words = norm.split()
        if norm in ALLOWED_NAMES or all(w in MONTHS or w in WORD_DAYS for w in words):
            continue
        hit = norm in corpus_norm or any(normalise(t) and normalise(t) in norm for t in texts if len(t) > 3)
        (result.matched if hit else result.unmatched).append(Claim("name", name))
    result.ok = not result.unmatched
    return result
