"""Normalise place names so that different spellings and scripts meet.

`normalise` keeps the script and removes punctuation and spacing differences: "S. V. Road" -> "sv road".
`latin_key` turns Devanagari into a plain Latin key and simplifies Latin spellings the same way, so
"अंधेरी" and "Andheri" both become "andheri".
"""

from __future__ import annotations

import re
import unicodedata

_SPACE = re.compile(r"\s+")

_INDEPENDENT = {
    "अ": "a",
    "आ": "a",
    "इ": "i",
    "ई": "i",
    "उ": "u",
    "ऊ": "u",
    "ऋ": "ri",
    "ए": "e",
    "ऐ": "ai",
    "ओ": "o",
    "औ": "au",
    "ऑ": "o",
    "ॲ": "a",
    "ऍ": "e",
}
_MATRA = {
    "ा": "a",
    "ि": "i",
    "ी": "i",
    "ु": "u",
    "ू": "u",
    "ृ": "ri",
    "े": "e",
    "ै": "ai",
    "ो": "o",
    "ौ": "au",
    "ॉ": "o",
    "ॅ": "e",
}
_CONSONANT = {
    "क": "k",
    "ख": "kh",
    "ग": "g",
    "घ": "gh",
    "ङ": "n",
    "च": "ch",
    "छ": "chh",
    "ज": "j",
    "झ": "jh",
    "ञ": "n",
    "ट": "t",
    "ठ": "th",
    "ड": "d",
    "ढ": "dh",
    "ण": "n",
    "त": "t",
    "थ": "th",
    "द": "d",
    "ध": "dh",
    "न": "n",
    "प": "p",
    "फ": "f",
    "ब": "b",
    "भ": "bh",
    "म": "m",
    "य": "y",
    "र": "r",
    "ल": "l",
    "ळ": "l",
    "व": "v",
    "श": "sh",
    "ष": "sh",
    "स": "s",
    "ह": "h",
}
_NUKTA = {"क": "k", "ख": "kh", "ग": "g", "ज": "z", "ड": "r", "ढ": "rh", "फ": "f", "य": "y"}
_SIGNS = {"\u0902": "n", "\u0901": "n", "\u0903": "h"}  # anusvara, chandrabindu, visarga
_VIRAMA, _NUKTA_SIGN = "्", "़"
_DIGITS = {chr(0x0966 + i): str(i) for i in range(10)}


def normalise(text: str) -> str:
    """Lower case, punctuation removed, whitespace collapsed, runs of single letters joined."""
    text = unicodedata.normalize("NFC", text).lower()
    # Remove punctuation and symbols only; Devanagari vowel signs are combining marks and must stay.
    text = "".join(" " if unicodedata.category(c)[0] in "PS" else c for c in text)
    words = _SPACE.sub(" ", text).strip().split(" ")
    out: list[str] = []
    run = ""
    for word in words:
        if len(word) == 1 and word.isalpha():
            run += word
            continue
        if run:
            out.append(run)
            run = ""
        if word:
            out.append(word)
    if run:
        out.append(run)
    return " ".join(out)


def _transliterate_word(word: str) -> str:
    chars = list(unicodedata.normalize("NFD", word))
    out = []
    i = 0
    while i < len(chars):
        ch = chars[i]
        nxt = chars[i + 1] if i + 1 < len(chars) else ""
        if ch in _CONSONANT:
            sound = _CONSONANT[ch]
            if nxt == _NUKTA_SIGN:
                sound = _NUKTA.get(ch, sound)
                i += 1
                nxt = chars[i + 1] if i + 1 < len(chars) else ""
            out.append(sound)
            if nxt == _VIRAMA:
                i += 1
            elif nxt in _MATRA:
                out.append(_MATRA[nxt])
                i += 1
            else:
                out.append("a")  # inherent vowel; dropped at the end of a word below
        elif ch in _INDEPENDENT:
            out.append(_INDEPENDENT[ch])
        elif ch in _SIGNS:
            out.append(_SIGNS[ch])
        elif ch in _DIGITS:
            out.append(_DIGITS[ch])
        elif ch.isascii():
            out.append(ch)
        i += 1
    latin = "".join(out)
    if len(latin) > 2 and latin.endswith("a") and word and word[-1] in _CONSONANT:
        latin = latin[:-1]
    return latin


def latin_key(text: str) -> str:
    """A rough Latin key for matching across scripts. Not a transliteration for display."""
    words = [_transliterate_word(w) if any("ऀ" <= c <= "ॿ" for c in w) else w for w in normalise(text).split(" ")]
    key = " ".join(words)
    for old, new in (("ph", "f"), ("w", "v"), ("ee", "i"), ("oo", "u"), ("aa", "a"), ("oa", "o")):
        key = key.replace(old, new)
    return re.sub(r"(.)\1+", r"\1", key)
