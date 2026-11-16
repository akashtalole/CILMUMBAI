"""Acceptance tests for SPEC-011: the audit desk, with the agent's turns and files scripted and the real API behind."""

from __future__ import annotations

import json
from typing import Any

import pytest

from hishob.agentkit.audit import run_audit
from hishob.api.tiers import sign
from hishob.archive.storage import LocalStore
from tests.conftest import TEST_DB
from tests.fakes import FakeClient, call, event, idle
from tests.integration.test_spec007_api import SECRET, api  # noqa: F401  (fixture: API over the SPEC-006 scenario)

pytestmark = [pytest.mark.integration, pytest.mark.graph]
LOCK = {"agents": {"audit-lead": {"id": "agent_lead", "version": 3}}, "environments": {"civic-cloud": {"id": "env_1"}}}
TOKEN = sign("reviewer", "audit-desk", SECRET)
OUT = "/mnt/session/outputs/"


class RoundClient(FakeClient):
    """Files listed after the n-th turn come from rounds[n]: the lead's first outputs, then its fixed ones."""

    def __init__(self, turns: list[list[Any]], rounds: list[dict[str, bytes]]) -> None:
        super().__init__(turns)
        self.rounds, self.opened = rounds, 0
        events = self.beta.sessions.events
        original = events.stream

        def stream(session_id: str) -> Any:
            self.opened += 1
            return original(session_id)

        events.stream = stream
        files = self.beta.files
        files.list = lambda scope_id, betas: _listing(self.rounds[min(self.opened, len(self.rounds)) - 1])
        files.download = lambda file_id: _Body(self._current()[file_id.removeprefix("out_")])

    def _current(self) -> dict[str, bytes]:
        return self.rounds[min(self.opened, len(self.rounds)) - 1]


class _Body:
    def __init__(self, data: bytes) -> None:
        self.data = data

    def read(self) -> bytes:
        return self.data


def _listing(files: dict[str, bytes]) -> Any:
    from types import SimpleNamespace as NS

    return NS(data=[NS(id=f"out_{name}", filename=name) for name in files])


@pytest.fixture
def ids(api, conn):  # type: ignore[no-untyped-def]  # noqa: F811
    http, _, _ = api

    def fact(node_id: str) -> str:
        row = conn.execute("SELECT fact_id FROM ledger.current WHERE node_id = %s", (node_id,)).fetchone()
        conn.commit()
        return str(row[0])

    names = ("tender:kw-roads-1", "work:kw-roads-1", "contractor:shree-ganesh", "award:sc-0003")
    return http, {n.split(":")[0]: fact(n) for n in names}


def good_outputs(f: dict[str, str]) -> dict[str, bytes]:
    t, w, c = f["tender"], f["work"], f["contractor"]
    files = {
        "ward-brief.md": f"# Ward K/W\n\nOne work is past its due date. The tender TEST/KW/ROADS/0001 [{t}] "
        f"was estimated at Rs. 4,20,00,000 [{t}]. The work was due on 31 May 2026 [{w}].\n\n"
        "No cancelled tenders were found.\n",
        "cases/case-01-overdue.md": f"## What the records show\n\nThe work Concretisation of S. V. Road [{w}] "
        f"was due on 31 May 2026 [{w}]. The records we hold do not show a completion certificate.\n\n## Evidence\n\n"
        f"| Claim | Value | Fact | Page |\n|---|---|---|---|\n| Due date | 31 May 2026 | {w} | 1 |\n\n"
        "## What is not known\n\nWhether the work was completed. The Executive Engineer (Roads) holds the record.\n",
        "cases/case-01-overdue.challenge.md": "Each claim matches its quote. A monsoon ban may explain the delay.\n\n"
        "Verdict: publish with changes\n",
        "held/case-02-award.md": f"## What the records show\n\nM/s Shree Ganesh Infra Pvt. Ltd. [{c}] won the work.\n",
        "held/case-02-award.challenge.md": "The award date is not in the evidence.\n\nVerdict: hold\n",
        "cases/case-03-unreviewed.md": f"The tender TEST/KW/ROADS/0001 [{t}] has one award on record.\n",
        "drafts/rti-01.md": "To the Public Information Officer, Roads and Traffic Department, K/West Ward.\n\n"
        f"1. The completion certificate for the work [{w}], for 1 April 2026 to date.\n",
        "drafts/questions.md": f"1. When will the work on S. V. Road, due on 31 May 2026, be completed? [{w}]\n",
        "gaps.jsonl": json.dumps(
            {
                "hop": "completion",
                "node_id": "work:kw-roads-1",
                "record_needed": "Completion certificate",
                "holder": "Executive Engineer (Roads), Western Suburbs",
            }
        )
        + "\n",
    }
    return {OUT + k: v.encode() for k, v in files.items()}


def turns() -> list[list[Any]]:
    return [
        [
            call("ward_summary", ward="K/W"),
            call("trace_money", node_id="road:sv"),
            event("span.outcome_evaluation_end", result="needs_revision"),
            event("span.outcome_evaluation_end", result="satisfied"),
            idle(),
        ],
        [idle()],
    ]


def audit(http, client, data, run_id="aud-1"):  # type: ignore[no-untyped-def]
    return run_audit(client, http, "K/W", data, run_id=run_id, token=TOKEN, lock=LOCK, sleep=lambda s: None)


# AC1 · R1 (tools answer through the API as a reviewer), AC2 · R2, AC3 · R3, AC4 · R4, AC7 · R7 ------------------


def test_spec011_a_clean_run_lays_out_reviewed_cases_held_cases_drafts_and_gaps(ids, tmp_path) -> None:  # type: ignore[no-untyped-def]
    http, f = ids
    data = LocalStore(tmp_path)
    client = RoundClient(turns(), [good_outputs(f)])
    run = audit(http, client, data)

    assert run.status == "complete", run.violations
    keys = data.list("staging/aud-1/")
    # AC2: every R2 file and folder is present
    assert {"ward-brief.md", "gaps.jsonl", "manifest.json"} <= {k.rsplit("/", 1)[-1] for k in keys}
    assert {k.split("/")[2] for k in keys} >= {"cases", "held", "drafts"}
    # AC3: each case left in cases/ has a passing review beside it
    assert "staging/aud-1/cases/case-01-overdue.challenge.md" in keys
    # AC4: the held case and the unreviewed one are in held/ with a reason, and not in cases/
    assert run.held == {
        "staging/aud-1/held/case-02-award.md": "the Challenger held it",
        "staging/aud-1/held/case-03-unreviewed.md": "not reviewed by a Challenger",
    }
    assert data.get("staging/aud-1/held/case-03-unreviewed.held.md") == b"Held: not reviewed by a Challenger\n"
    assert not any("/cases/case-02" in k or "/cases/case-03" in k for k in keys)
    assert not any("/held/" in k for k in run.files)  # held files are never offered for release
    # R1: the tools were answered through the API (the trace came back with fact ids)
    results = [e for e in client.sent if e["type"] == "user.custom_tool_result"]
    assert len(results) == 2 and f["tender"] in results[1]["content"][0]["text"]
    # AC7: graded against the rubric, revised until satisfied
    kickoff = client.sent[0]
    assert kickoff["type"] == "user.define_outcome" and kickoff["max_iterations"] == 3
    assert ".challenge.md" in kickoff["rubric"]["content"]
    assert run.grader_results == ["needs_revision", "satisfied"] and not run.fix_requested


def test_spec011_a_repeat_returns_the_finished_run(ids, tmp_path) -> None:  # type: ignore[no-untyped-def]
    http, f = ids
    data = LocalStore(tmp_path)
    first = audit(http, RoundClient(turns(), [good_outputs(f)]), data)
    again = RoundClient([], [])
    assert audit(http, again, data) == first and again.beta.sessions.created == []


# AC5 · R5, AC6 · R6 ---------------------------------------------------------------------------------------------


def test_spec011_ac5_ac6_problems_go_back_to_the_lead_once_then_the_file_is_held(ids, tmp_path) -> None:  # type: ignore[no-untyped-def]
    http, f = ids
    w = f["work"]
    first = good_outputs(f)
    bad_case = (
        f"The work [{w}] cost Rs. 5,00,00,000 [{w}] and looks like a scam approved by Shri Ramesh Patil. "
        f"See also [f_{'0' * 32}].\n"
    )
    first[OUT + "cases/case-01-overdue.md"] = bad_case.encode()
    first[OUT + "drafts/complaint-01.md"] = "This is भ्रष्टाचार.\n".encode()
    second = dict(first)
    second[OUT + "drafts/complaint-01.md"] = b"Please repair the road. [to be filled by the resident]\n"
    client = RoundClient(turns(), [first, second])  # the lead fixes the complaint but not the case
    run = audit(http, client, LocalStore(tmp_path))

    assert run.fix_requested
    request = next(e for e in client.sent if e["type"] == "user.message")["content"][0]["text"]
    for problem in (
        "banned_word: scam",
        "named_person: Shri Ramesh Patil",
        "unsourced: amount 'Rs. 5,00,00,000'",
        f"unknown_fact: f_{'0' * 32}",
        "banned_word: भ्रष्टाचार",
    ):
        assert f"cases/case-01-overdue.md: {problem}" in request or f"drafts/complaint-01.md: {problem}" in request
    reason = run.held["staging/aud-1/held/case-01-overdue.md"]
    assert reason.startswith("failed the output check:") and "scam" in reason
    assert "staging/aud-1/drafts/complaint-01.md" in run.files  # fixed on the second round, so not held
    assert run.violations == [] and run.status == "complete"


def test_spec011_ac6_a_missing_brief_is_reported_not_invented(ids, tmp_path) -> None:  # type: ignore[no-untyped-def]
    http, f = ids
    outputs = {k: v for k, v in good_outputs(f).items() if not k.endswith("ward-brief.md")}
    run = audit(http, RoundClient(turns(), [outputs]), LocalStore(tmp_path))
    assert (
        run.status == "incomplete"
        and {"path": "ward-brief.md", "kind": "missing", "detail": "ward-brief.md was not written"} in run.violations
    )


# AC8 · R8 -------------------------------------------------------------------------------------------------------


def test_spec011_ac8_nothing_is_public_until_release_then_only_approved_files(ids, tmp_path, conn) -> None:  # type: ignore[no-untyped-def]
    from hishob.workflows.live import LiveSteps
    from hishob.workflows.w1 import Engine

    http, f = ids
    data, public = LocalStore(tmp_path / "data"), LocalStore(tmp_path / "public")
    client = RoundClient(turns(), [good_outputs(f)])

    class Steps(LiveSteps):
        def intake(self, hashes: list[str], run_id: str) -> dict[str, Any]:
            return {"run_id": run_id, "accepted": 10, "held": 0}

    loader = type("L", (), {"data": data})()
    steps = Steps(client, None, loader, public, http=http, reviewer_token=TOKEN)  # type: ignore[arg-type]
    import hishob.workflows.live as live

    original = live.run_audit
    live.run_audit = lambda *a, **k: original(*a, **{**k, "lock": LOCK, "sleep": lambda s: None})  # type: ignore[assignment]
    try:
        status = Engine(TEST_DB, steps).start("t-ac8", ["a" * 64], ["K/W"])
        assert status.waiting["gate"] == "release" and public.list("") == []
        assert status.waiting["held"]["K/W"]  # the reviewer sees what stays held
        done = Engine(TEST_DB, steps).resume(
            "t-ac8", "approve", reason="read every case", account="acct_nair", tier="reviewer"
        )
    finally:
        live.run_audit = original  # type: ignore[assignment]
    published = public.list("published/")
    assert done.finished and published == sorted(done.published)
    names = {p.rsplit("/", 1)[-1] for p in published}
    assert {"ward-brief.md", "case-01-overdue.md", "case-01-overdue.challenge.md", "gaps.jsonl", "rti-01.md"} <= names
    assert not any("/held/" in p or "case-02" in p or "case-03" in p or "manifest" in p for p in published)
