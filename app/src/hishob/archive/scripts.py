"""Find which writing systems appear in text, as ISO 15924 codes."""

from __future__ import annotations

from collections.abc import Iterable

MIN_CHARS = 5


def detect_scripts(texts: Iterable[str]) -> list[str]:
    deva = latn = 0
    for text in texts:
        for ch in text:
            code = ord(ch)
            if 0x0900 <= code <= 0x097F or 0xA8E0 <= code <= 0xA8FF:
                deva += 1
            elif ch.isascii() and ch.isalpha():
                latn += 1
    found = []
    if deva >= MIN_CHARS:
        found.append("Deva")
    if latn >= MIN_CHARS:
        found.append("Latn")
    return found
