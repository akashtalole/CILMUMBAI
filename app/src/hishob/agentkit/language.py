"""Tell Marathi, Hindi and English apart well enough to answer in the resident's language (SPEC-008/R2)."""

from __future__ import annotations

import re

MARATHI = {
    "आहे",
    "नाही",
    "कोण",
    "कुठे",
    "काय",
    "कधी",
    "आणि",
    "च्या",
    "चा",
    "ची",
    "चे",
    "ला",
    "मध्ये",
    "आमच्या",
    "माझ्या",
    "रस्त्यावर",
    "झाले",
    "होते",
    "करा",
    "पाहिजे",
    "किती",
    "कोणी",
    "दुरुस्त",
    "कोणाची",
    "पर्यंत",
    "आम्ही",
}
HINDI = {
    "है",
    "हैं",
    "नहीं",
    "कौन",
    "कहाँ",
    "कहां",
    "क्या",
    "कब",
    "और",
    "का",
    "की",
    "के",
    "में",
    "हमारे",
    "मेरे",
    "सड़क",
    "हुआ",
    "था",
    "करें",
    "चाहिए",
    "कितना",
    "किसकी",
    "ठीक",
    "तक",
    "हम",
}
WORD = re.compile(r"[ऀ-ॿ]+")


def detect(text: str) -> str:
    """Return mr, hi or en."""
    words = WORD.findall(text)
    latin = len(re.findall(r"[A-Za-z]", text))
    if not words or latin > 3 * sum(len(w) for w in words):
        return "en"
    mr = sum(w in MARATHI for w in words) + sum(w.endswith(("च्या", "ाचे", "ाची", "ाला")) for w in words)
    hi = sum(w in HINDI for w in words)
    return "hi" if hi > mr else "mr"
