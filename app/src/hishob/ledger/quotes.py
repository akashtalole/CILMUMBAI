"""Check that a quote appears on its page (SPEC-003/R2, R3; constitution C2)."""

from __future__ import annotations

import re
import unicodedata

_INVISIBLE = dict.fromkeys(map(ord, "​‌‍­﻿"))
_SPACE = re.compile(r"\s+")


def normalise(text: str) -> str:
    """NFC, drop zero-width characters and soft hyphens, collapse whitespace.

    NFC also unifies precomposed and decomposed nukta letters (क़ and क़), because the precomposed forms are
    composition exclusions. Case and punctuation are kept: amounts and identifiers must match exactly.
    """
    text = unicodedata.normalize("NFC", text).translate(_INVISIBLE)
    return _SPACE.sub(" ", text).strip()


def looks_garbled(text: str) -> bool:
    """Devanagari mixed with Latin-1 or Latin Extended letters: the signature of a shaped PDF whose text layer
    does not map back to Unicode. Such pages are treated like scans (SPEC-003 open question, interim rule)."""
    deva = odd = 0
    for ch in text:
        code = ord(ch)
        if 0x0900 <= code <= 0x097F:
            deva += 1
        elif 0x00C0 <= code <= 0x024F:
            odd += 1
    return deva > 0 and odd >= 2


def check(quote: str, page_text: str | None) -> str:
    """Return matched, scan_unchecked or quote_not_found."""
    if page_text is None or looks_garbled(page_text):
        return "scan_unchecked"
    return "matched" if normalise(quote) in normalise(page_text) else "quote_not_found"
