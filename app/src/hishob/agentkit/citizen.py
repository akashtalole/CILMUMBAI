"""Answer one resident's question with the citizen desk (SPEC-008).

Order of work: redact the message (R7), detect its language (R2), run one session whose tools read through the
API under the resident's tier (R1, R8), then review the reply in code: citation check (R4), language (R2),
no private names (R5), liability end date when there is one (R6). One rewrite is allowed; after that the reply
is built in code from what the tools returned.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from hishob.agentkit import language as lang
from hishob.agentkit.definitions import AGENTS_DIR
from hishob.agentkit.provision import read_lock
from hishob.agentkit.redact import redact
from hishob.agentkit.session import follow
from hishob.agentkit.tools import ApiTools
from hishob.api.citations import parse_dates

FACT_MARK = re.compile(r"\s?\[(f_[0-9a-f]{32}(?:\s*,\s*f_[0-9a-f]{32})*)\]")
FACT_ID = re.compile(r"f_[0-9a-f]{32}")
LETTER = re.compile(r"^\s*(?:LETTER|पत्र)\s*:\s*$", re.MULTILINE)

FALLBACK = {
    "en": ("The records we hold do not show this.", "Closest records we have:", "To find out, ask"),
    "mr": ("आमच्याकडील नोंदींमध्ये याबद्दल माहिती नाही.", "आमच्याकडील जवळच्या नोंदी:", "माहितीसाठी विचारा"),
    "hi": ("हमारे पास मौजूद रिकॉर्ड में इसकी जानकारी नहीं है।", "हमारे पास सबसे नज़दीकी रिकॉर्ड:", "जानकारी के लिए पूछें"),
}
SOURCES = {"en": "Sources", "mr": "स्रोत", "hi": "स्रोत"}


@dataclass
class Answer:
    text: str
    language: str
    status: str  # answered, asked_location, fallback
    cited_fact_ids: list[str] = field(default_factory=list)
    sources: list[dict[str, Any]] = field(default_factory=list)
    draft_letter: str | None = None
    gaps: list[dict[str, Any]] = field(default_factory=list)
    problems: list[str] = field(default_factory=list)  # from the last review, if it fell back
    attempts: int = 0
    session_id: str | None = None


def answer_question(
    client: Any,
    http: Any,
    question: str,
    *,
    language_hint: str | None = None,
    location: tuple[float, float] | None = None,
    token: str | None = None,
    keep_names: tuple[str, ...] = (),
    lock: dict[str, Any] | None = None,
    cap_usd: int = 2,
    agents_dir: Path = AGENTS_DIR,
) -> Answer:
    lock = lock or read_lock(agents_dir / ".lock.json")
    if "citizen-desk" not in lock["agents"] or "civic-cloud" not in lock["environments"]:
        raise RuntimeError("the citizen desk is not applied to this account; run `hishob agents apply` first")
    clean = redact(question, keep_names)
    language = language_hint or lang.detect(clean)
    desk = lock["agents"]["citizen-desk"]
    session = client.beta.sessions.create(
        agent={"type": "agent", "id": desk["id"], "version": desk["version"]},
        environment_id=lock["environments"]["civic-cloud"]["id"],
        title="Citizen question",
        budget={"type": "limit", "max_list_cost": {"amount": str(cap_usd * 100), "currency": "USD"}},
        metadata={"project": "aamcha-hishob", "kind": "citizen"},
    )
    tools = ApiTools(http, token)
    header = f"language: {language}\n" + (f"location: {location[0]}, {location[1]}\n" if location else "")
    message = header + "\nquestion:\n" + clean

    reply, problems, attempts = "", ["no reply"], 0
    for attempt in range(2):
        attempts = attempt + 1
        texts: list[str] = []
        follow(
            client,
            session.id,
            {"type": "user.message", "content": [{"type": "text", "text": message}]},
            on_tool=tools,
            on_text=texts.append,
        )
        reply = texts[-1].strip() if texts else ""
        problems = review(http, reply, language, tools.seen, token)
        if not problems:
            break
        message = (
            "Your reply did not pass the checks:\n- "
            + "\n- ".join(problems)
            + "\nRewrite it using only the tool results, with a fact id after every claim, in the language "
            f"`{language}`."
        )

    gaps = [g for result in tools.seen if isinstance(result, dict) for g in result.get("gaps", [])]
    if problems:
        return Answer(
            text=fallback(language, tools.seen, gaps),
            language=language,
            status="fallback",
            gaps=gaps,
            problems=problems,
            attempts=attempts,
            session_id=session.id,
        )
    cited = sorted(set(FACT_ID.findall(reply)))
    body = FACT_MARK.sub("", reply)
    letter = None
    parts = LETTER.split(body, maxsplit=1)
    if len(parts) == 2:
        body, letter = parts[0].strip(), parts[1].strip()
    sources = [_source(http, fid, token) for fid in cited]
    status = "asked_location" if not cited and body.rstrip().endswith("?") else "answered"
    text = (
        body
        if not sources
        else body
        + f"\n\n{SOURCES[language]}:\n"
        + "\n".join(
            f'- {s["publisher"]} document {s["document"][:12]}…, page {s["page"]}: "{s["quote"]}"' for s in sources
        )
    )
    return Answer(
        text=text,
        language=language,
        status=status,
        cited_fact_ids=cited,
        sources=sources,
        draft_letter=letter,
        gaps=gaps,
        attempts=attempts,
        session_id=session.id,
    )


def review(http: Any, reply: str, language: str, seen: list[Any], token: str | None = None) -> list[str]:
    """Problems with a reply, checked in code. Empty means it may be sent."""
    if not reply:
        return ["the reply was empty"]
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    problems = []
    cited = sorted(set(FACT_ID.findall(reply)))
    body = FACT_MARK.sub("", reply)
    check = http.post(
        "/answers/check", json={"text": body, "cited_fact_ids": cited, "language": language}, headers=headers
    ).json()
    for item in check.get("unmatched", []):
        problems.append(f"{item['kind']} not in the cited facts: {item['text']}")
    if lang.detect(body) != language:
        problems.append(f"the reply is not in {language}")
    for name in _private_names(seen):
        if name.lower() in body.lower():
            problems.append(f"names a person who is not an elected representative: {name}")
    for end in _liability_ends(seen):
        if not any(d[:2] == tuple(int(x) for x in end.split("-")[:2]) for _, d, _ in parse_dates(body)):
            problems.append(f"does not say the contractor is liable for repairs until {end}")
    return problems


def fallback(language: str, seen: list[Any], gaps: list[dict[str, Any]]) -> str:
    opening, nearest_heading, ask = FALLBACK.get(language, FALLBACK["en"])
    lines = [opening]
    nearest = _nodes(seen)[:3]
    if nearest:
        lines += ["", nearest_heading]
        lines += [
            f"- {n.get('title') or n.get('name') or n.get('id')} ({n['label']}; page {n.get('page')})" for n in nearest
        ]
    for gap in gaps[:3]:
        lines += ["", f"{ask}: {gap['holder']} — {gap['record_needed']}."]
    return "\n".join(lines)


def _source(http: Any, fid: str, token: str | None) -> dict[str, Any]:
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    fact = http.get(f"/facts/{fid}", headers=headers).json()
    document = http.get(f"/sources/{fact['source']}/pages/{fact['page']}", headers=headers)
    publisher = document.json().get("publisher", "") if document.status_code == 200 else ""
    return {
        "fact_id": fid,
        "document": fact["source"],
        "page": fact["page"],
        "quote": fact["quote"],
        "publisher": publisher,
        "fetched_at": fact.get("source_fetched_at"),
    }


def _nodes(value: Any) -> list[dict[str, Any]]:
    found: list[dict[str, Any]] = []
    if isinstance(value, dict):
        if "fact_id" in value and "label" in value:
            found.append(value)
        for v in value.values():
            found += _nodes(v)
    elif isinstance(value, list):
        for v in value:
            found += _nodes(v)
    return found


def _private_names(seen: list[Any]) -> list[str]:
    return sorted({str(n["name"]) for n in _nodes(seen) if n.get("label") == "Person" and n.get("name")})


def _liability_ends(seen: list[Any]) -> list[str]:
    ends = []
    for result in seen:
        for row in result.get("rows", []) if isinstance(result, dict) else []:
            if isinstance(row, dict) and row.get("hop") == "under_liability" and row.get("period"):
                ends.append(str(row["period"]["to_date"]))
    return ends


def as_json(answer: Answer) -> str:
    return json.dumps(answer.__dict__, ensure_ascii=False, indent=2)
