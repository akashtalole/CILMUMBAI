"""Acceptance tests for SPEC-008: the citizen desk, with the agent's turns scripted and the real API behind it."""

from __future__ import annotations

import pytest

from hishob.agentkit.citizen import answer_question, review
from tests.fakes import FakeClient, call, idle, say
from tests.integration.test_spec007_api import api  # noqa: F401  (fixture: API over the SPEC-006 scenario)

pytestmark = [pytest.mark.integration, pytest.mark.graph]
LOCK = {
    "agents": {"citizen-desk": {"id": "agent_desk", "version": 1}},
    "environments": {"civic-cloud": {"id": "env_1"}},
}


@pytest.fixture
def desk(api, conn):  # type: ignore[no-untyped-def]  # noqa: F811
    client, _, _ = api

    def fact(node_id: str) -> str:
        row = conn.execute("SELECT fact_id FROM ledger.current WHERE node_id = %s", (node_id,)).fetchone()
        conn.commit()
        return str(row[0])

    return client, fact


def ask(http, turns, question: str, **kwargs):  # type: ignore[no-untyped-def]
    client = FakeClient(turns)
    return client, answer_question(client, http, question, lock=LOCK, **kwargs)


# AC1 · R1 -------------------------------------------------------------------------------------------------------


def test_spec008_ac1_every_figure_comes_from_a_tool_result(desk) -> None:  # type: ignore[no-untyped-def]
    http, fact = desk
    tender = fact("tender:kw-roads-1")
    turns = [
        [
            call("find_place", text="S. V. Road"),
            call("trace_money", node_id="road:sv"),
            say(f"The tender TEST/KW/ROADS/0001 [{tender}] was estimated at Rs. 4,20,00,000 [{tender}]."),
            idle(),
        ]
    ]
    client, answer = ask(http, turns, "How much was spent on S. V. Road?")
    assert answer.status == "answered" and answer.cited_fact_ids == [tender]
    assert answer.sources[0]["quote"] == "Tender Ref. No. TEST/KW/ROADS/0001"
    assert "Rs. 4,20,00,000" in answer.text and "[f_" not in answer.text
    results = [e for e in client.sent if e["type"] == "user.custom_tool_result"]
    assert len(results) == 2 and tender in results[1]["content"][0]["text"]


# AC2 · R2 -------------------------------------------------------------------------------------------------------


def test_spec008_ac2_a_reply_in_the_wrong_language_is_rewritten(desk) -> None:  # type: ignore[no-untyped-def]
    http, fact = desk
    tender = fact("tender:kw-roads-1")
    turns = [
        [call("trace_money", node_id="road:sv"), say(f"Estimated cost Rs. 4,20,00,000 [{tender}]."), idle()],
        [say(f"या कामाचा अंदाजित खर्च Rs. 4,20,00,000 [{tender}] आहे."), idle()],
    ]
    client, answer = ask(http, turns, "एस. व्ही. रोडच्या कामाला किती खर्च आला?")
    assert answer.language == "mr" and answer.status == "answered" and answer.attempts == 2
    nudge = [e for e in client.sent if e["type"] == "user.message"][1]["content"][0]["text"]
    assert "not in mr" in nudge


# AC3 · R3 -------------------------------------------------------------------------------------------------------


def test_spec008_ac3_without_a_place_the_desk_asks_for_one(desk) -> None:  # type: ignore[no-untyped-def]
    http, _ = desk
    client, answer = ask(
        http, [[say("Which road or lane is the pothole on?"), idle()]], "Who fixes the pothole outside my building?"
    )
    assert answer.status == "asked_location" and answer.cited_fact_ids == []
    assert not [e for e in client.sent if e["type"] == "user.custom_tool_result"]


# AC4 · R4 -------------------------------------------------------------------------------------------------------


def test_spec008_ac4_two_failed_checks_give_a_reply_built_in_code(desk) -> None:  # type: ignore[no-untyped-def]
    http, fact = desk
    tender = fact("tender:kw-roads-1")
    invented = say(f"The work cost ₹9 crore [{tender}] and was finished in March 2026 [{tender}].")
    turns = [[call("trace_money", node_id="road:sv"), invented, idle()], [invented, idle()]]
    _, answer = ask(http, turns, "How much did S. V. Road cost?")
    assert answer.status == "fallback" and answer.attempts == 2
    assert answer.text.startswith("The records we hold do not show this.")
    assert "9 crore" not in answer.text and "Budget head" in answer.text
    assert any("amount not in the cited facts" in p for p in answer.problems)


def test_spec008_ac4_the_fallback_is_in_the_residents_language(desk) -> None:  # type: ignore[no-untyped-def]
    http, _ = desk
    turns = [[say("₹9 crore."), idle()], [say("₹9 crore."), idle()]]
    _, answer = ask(http, turns, "रस्त्याच्या कामाला किती खर्च आला?")
    assert answer.status == "fallback" and answer.text.startswith("आमच्याकडील नोंदींमध्ये")


# AC5 · R5 -------------------------------------------------------------------------------------------------------


def test_spec008_ac5_naming_a_private_official_fails_review(desk) -> None:  # type: ignore[no-untyped-def]
    http, _ = desk
    seen = [
        {
            "rows": [
                {
                    "hop": "post",
                    "node": {"id": "person:x", "label": "Person", "name": "Ravi Kulkarni", "fact_id": "f_" + "0" * 32},
                }
            ]
        }
    ]
    problems = review(http, "Contact Ravi Kulkarni.", "en", seen)
    assert any("not an elected representative" in p for p in problems)
    assert not [p for p in review(http, "Contact the Assistant Engineer.", "en", seen) if "representative" in p]


# AC6 · R6 -------------------------------------------------------------------------------------------------------


def test_spec008_ac6_the_liability_end_date_must_be_stated(desk) -> None:  # type: ignore[no-untyped-def]
    http, fact = desk
    post, dlp = fact("post:ae-roads-kw"), fact("dlp:kw-roads-1")
    silent = say(f"Complain to the Assistant Engineer (Roads), K/West [{post}].")
    full = say(
        f"Complain to the Assistant Engineer (Roads), K/West [{post}]. The contractor must repair it at "
        f"their own cost until 31 May 2031 [{dlp}]."
    )
    turns = [[call("who_is_responsible", asset_id="road:sv", issue="pothole"), silent, idle()], [full, idle()]]
    client, answer = ask(http, turns, "Who will fix the pothole on S. V. Road?")
    assert answer.status == "answered", answer.problems
    assert answer.attempts == 2 and "31 May 2031" in answer.text
    nudge = [e for e in client.sent if e["type"] == "user.message"][1]["content"][0]["text"]
    assert "liable for repairs until 2031-05-31" in nudge


# AC7 · R7 -------------------------------------------------------------------------------------------------------


def test_spec008_ac7_the_agent_never_sees_the_residents_details(desk) -> None:  # type: ignore[no-untyped-def]
    http, _ = desk
    client, _ = ask(
        http,
        [[say("Which road is it?"), idle()]],
        "My name is Sunita Patil, 98200 12345. Who fixes the drain near my building?",
    )
    sent = client.sent[0]["content"][0]["text"]
    assert "Sunita" not in sent and "98200" not in sent and "[name]" in sent and "[phone]" in sent


# The letter -----------------------------------------------------------------------------------------------------


def test_a_requested_letter_is_returned_separately_and_checked(desk) -> None:  # type: ignore[no-untyped-def]
    http, fact = desk
    tender, post = fact("tender:kw-roads-1"), fact("post:ae-roads-kw")
    reply = (
        f"The work is under tender TEST/KW/ROADS/0001 [{tender}].\nLETTER:\nTo the Assistant Engineer (Roads),"
        f" K/West [{post}].\nThe road under tender TEST/KW/ROADS/0001 [{tender}] is broken outside [____]."
        " Please repair."
    )
    _, answer = ask(
        http, [[call("trace_money", node_id="road:sv"), say(reply), idle()]], "Write a complaint about S. V. Road."
    )
    assert answer.status == "answered", answer.problems
    assert answer.draft_letter is not None
    assert answer.draft_letter.startswith("To the Assistant Engineer") and "LETTER" not in answer.text


def test_spec008_a_source_lookup_that_fails_does_not_crash_the_answer(desk) -> None:  # type: ignore[no-untyped-def]
    # Found by the first live SPEC-012 run: a rate-limited API reply has no "source", and the desk raised KeyError.
    from hishob.agentkit.citizen import _source

    class Limited:
        def get(self, *args, **kwargs):  # type: ignore[no-untyped-def]
            return type("R", (), {"status_code": 429, "json": lambda self: {"detail": "too many requests"}})()

    assert _source(Limited(), "f_" + "0" * 32, None) is None
