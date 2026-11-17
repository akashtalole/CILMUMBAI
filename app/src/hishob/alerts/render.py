"""Alert text in Marathi, Hindi and English (SPEC-010/R4, R6; constitution C1, C10).

A payload holds facts only (what changed, the tender number, the date, the source page), never anything about
the subscriber. The Marathi and Hindi wording is a first draft for the language reviewer.
"""

from __future__ import annotations

from typing import Any

WHAT = {
    "tender_published": {
        "en": "A tender has been published for work on {road}.",
        "mr": "{road} वरील कामासाठी निविदा प्रसिद्ध झाली आहे.",
        "hi": "{road} पर काम के लिए निविदा प्रकाशित हुई है।",
    },
    "awarded": {
        "en": "The work on {road} has been awarded.",
        "mr": "{road} वरील कामाचा ठेका मंजूर झाला आहे.",
        "hi": "{road} पर काम का ठेका मंज़ूर हो गया है।",
    },
    "corrigendum": {
        "en": "The tender for work on {road} has been changed by a corrigendum.",
        "mr": "{road} वरील कामाच्या निविदेत शुद्धिपत्रकाने बदल झाला आहे.",
        "hi": "{road} पर काम की निविदा में शुद्धिपत्र से बदलाव हुआ है।",
    },
    "overdue": {
        "en": "The work on {road} has passed its completion date, and the records we hold show no completion.",
        "mr": "{road} वरील कामाची पूर्ण होण्याची मुदत उलटली आहे; आमच्या नोंदींमध्ये काम पूर्ण झाल्याची नोंद नाही.",
        "hi": "{road} पर काम की पूरा होने की समय-सीमा बीत गई है; हमारे रिकॉर्ड में काम पूरा होने का उल्लेख नहीं है।",
    },
}
LABELS = {
    "en": {"tender": "Tender no.", "date": "Date", "due": "Was due on", "source": "Source", "work": "Work",
           "unsure": "We matched this work to your area from its description and may be wrong. Judge from the title.",
           "no_ref": "not stated in the record", "changed": "Changed"},
    "mr": {"tender": "निविदा क्र.", "date": "दिनांक", "due": "मुदत होती", "source": "स्रोत", "work": "काम",
           "unsure": "हे काम तुमच्या भागाशी त्याच्या वर्णनावरून जोडले आहे; चूक असू शकते. शीर्षक पाहून ठरवा.",
           "no_ref": "नोंदीत दिलेला नाही", "changed": "बदल"},
    "hi": {"tender": "निविदा क्र.", "date": "दिनांक", "due": "समय-सीमा थी", "source": "स्रोत", "work": "काम",
           "unsure": "यह काम आपके इलाके से उसके विवरण के आधार पर जोड़ा गया है; गलती हो सकती है। शीर्षक देखकर तय करें।",
           "no_ref": "रिकॉर्ड में नहीं दिया", "changed": "बदलाव"},
}  # fmt: skip


def render(payload: dict[str, Any], language: str, base_url: str = "") -> str:
    """One alert as plain text. Tender numbers, dates and titles stay exactly as the record gives them."""
    lang = language if language in LABELS else "en"
    label = LABELS[lang]
    road = (payload.get("road_name_mr") if lang == "mr" else None) or payload.get("road_name") or payload["asset_id"]
    lines = [WHAT[payload["kind"]][lang].format(road=road)]
    if payload.get("low_confidence") and payload.get("work_title"):
        lines.append(f"{label['work']}: {payload['work_title']}")
        lines.append(label["unsure"])
    elif payload.get("work_title") and payload["kind"] == "overdue":
        lines.append(f"{label['work']}: {payload['work_title']}")
    lines.append(f"{label['tender']}: {payload.get('tender_ref') or label['no_ref']}")
    if payload.get("changed_field"):
        lines.append(f"{label['changed']}: {payload['changed_field']}")
    lines.append(f"{label['due'] if payload['kind'] == 'overdue' else label['date']}: {payload['date']}")
    lines.append(f"{label['source']}: {base_url.rstrip('/')}/sources/{payload['source']}/pages/{payload['page']}")
    return "\n".join(lines)
