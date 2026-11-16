"""Remove private details from a resident's message before storage or any model call (SPEC-008/R7; C7).

Removes phone numbers, email addresses, flat and house numbers, and personal names introduced as such
("my name is …", "माझे नाव …", "मेरा नाम …", or after an honorific). Names on the `keep` list (public office
holders, such as corporators) are left in place.
"""

from __future__ import annotations

import re
from collections.abc import Iterable

PHONE = re.compile(r"(?<!\d)(?:\+?91[\s-]?|0)?[6-9](?:[\s-]?\d){9}(?!\d)")
EMAIL = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
HOUSE = re.compile(
    r"\b(?:flat|room|house|building|bldg|plot|shop|wing)\s*(?:no\.?|number|#)?\s*[:\-]?\s*[A-Za-z]?[-/]?\d+[A-Za-z]?\b"
    r"|\b[A-Z]-?\d{2,4}\b(?=,|\s+[A-Z][a-z])"
    r"|(?:खोली|घर|फ्लॅट|सदनिका|मकान|कमरा)\s*(?:क्र\.?|क्रमांक|नं\.?|नंबर)?\s*[:\-]?\s*[\d०-९]+",
    re.IGNORECASE,
)
_NAME_WORD = r"[A-Z][a-z]+|[ऀ-ॿ]+"
INTRODUCED = re.compile(
    rf"(?P<lead>\b(?:my name is|i am|this is)\s+|(?:माझे नाव|माझं नाव|मी)\s+|(?:मेरा नाम|मैं)\s+)"
    rf"(?P<name>(?:{_NAME_WORD})(?:\s+(?:{_NAME_WORD}))?)",
    re.IGNORECASE,
)
PLACE_WORDS = (
    r"Mandir|Temple|Masjid|Church|Nagar|Road|Marg|Path|Chowk|Lane|Galli|Hospital|School|College|Society|CHS|Garden|"
    r"Udyan|Maidan|Station|Bridge|Market|Colony|Wadi|Chawl|Building|Tower|Complex|"
    r"मंदिर|नगर|रोड|मार्ग|पथ|चौक|गल्ली|रुग्णालय|शाळा|सोसायटी|उद्यान|मैदान|स्थानक|पूल|मंडई|वाडी|चाळ|अस्पताल|स्कूल"
)
HONORIFIC = re.compile(
    rf"(?P<lead>\b(?:Mr|Mrs|Ms|Smt|Shri|Dr)\.?\s+|(?:श्रीमती|श्री|सौ\.?|कु\.?)\s*)"
    rf"(?P<name>(?:{_NAME_WORD})(?:\s+(?:{_NAME_WORD}))?)"
)
PLACE_SET = {w.lower() for w in PLACE_WORDS.split("|")}
# Words that follow "I am" / "मी" without being a name.
NOT_NAMES = {
    "a",
    "an",
    "the",
    "not",
    "from",
    "living",
    "staying",
    "here",
    "writing",
    "asking",
    "worried",
    "very",
    "resident",
    "आहे",
    "राहतो",
    "राहते",
    "विचारत",
    "तक्रार",
    "येथे",
    "इथे",
    "रहता",
    "रहती",
    "यहाँ",
    "पूछ",
}


def _is_place(word: str) -> bool:
    """Latin place words match whole; Devanagari ones also with case endings (मंदिराजवळ = near the temple)."""
    if word in PLACE_SET:
        return True
    return any(word.startswith(p) for p in PLACE_SET if p and "\u0900" <= p[0] <= "\u097f")


def redact(text: str, keep: Iterable[str] = ()) -> str:
    kept = {k.lower() for k in keep}
    text = EMAIL.sub("[email]", text)
    text = PHONE.sub("[phone]", text)
    text = HOUSE.sub("[address]", text)

    def name(match: re.Match[str]) -> str:
        found = match.group("name")
        words = [w.lower() for w in found.split()]
        after = re.match(r"\s*([^\s,.;:]+)", match.string[match.end() :])
        following = after.group(1).lower() if after else ""
        if words[0] in NOT_NAMES or found.lower() in kept or any(_is_place(w) for w in (*words, following)):
            return match.group(0)  # not a person: a phrase, a kept office holder, or a landmark
        return match.group("lead") + "[name]"

    text = INTRODUCED.sub(name, text)
    return HONORIFIC.sub(name, text)
