"""SPEC-005: the intake runner against a scripted session (AC1, AC4, AC6, AC7, AC8)."""

from __future__ import annotations

import hashlib
import json

import pytest

from hishob.agentkit.intake import run_intake
from hishob.archive import Archive
from hishob.ledger import Loader
from tests.conftest import FIXED_NOW, FIXTURES
from tests.fakes import FakeClient, event, idle

pytestmark = pytest.mark.integration

LOCK = {
    "agents": {
        "ingest-lead": {"id": "agent_lead", "version": 3},
        "doc-extractor": {"id": "agent_ext", "version": 1},
        "fact-verifier": {"id": "agent_ver", "version": 1},
        "entity-resolver": {"id": "agent_res", "version": 1},
    },
    "environments": {"civic-cloud": {"id": "env_1"}},
}
EN = hashlib.sha256((FIXTURES / "tender-en.pdf").read_bytes()).hexdigest()
MIXED = hashlib.sha256((FIXTURES / "tender-mixed.pdf").read_bytes()).hexdigest()
DAMAGED = hashlib.sha256((FIXTURES / "damaged.pdf").read_bytes()).hexdigest()


@pytest.fixture
def setup(make_archive, conn):  # type: ignore[no-untyped-def]
    archive: Archive = make_archive()
    for name in ("tender-en.pdf", "tender-mixed.pdf", "damaged.pdf"):
        archive.add_file(FIXTURES / name, publisher="bmc", licence="public")
    return archive, Loader(conn, archive, archive.data, now=lambda: FIXED_NOW)


def facts(*records: dict) -> bytes:
    return "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in records).encode("utf-8")


def node(node_id: str, label: str, quote: str, source: str, page: int = 1) -> dict:
    return {
        "kind": "node",
        "id": node_id,
        "label": label,
        "props": {},
        "source": source,
        "page": page,
        "quote": quote,
        "tier": "official",
        "confidence": 0.9,
    }


THREADS = [
    event("session.thread_created", agent_name="Hishob dev · Document extractor", session_thread_id="sthr_1"),
    event("session.thread_created", agent_name="Hishob dev · Fact verifier", session_thread_id="sthr_2"),
    event("span.outcome_evaluation_end", result="satisfied"),
    idle(),
]


def test_spec005_ac1_mounts_documents_schema_and_entities_and_downloads_outputs(setup) -> None:  # type: ignore[no-untyped-def]
    archive, loader = setup
    outputs = {
        "facts.jsonl": facts(node("tender:a", "Tender", "Tender Ref. No. TEST/KW/ROADS/0001", EN)),
        "review.jsonl": b"",
        "report.md": f"| {EN}.pdf | covered | | 1 |\n".encode(),
    }
    client = FakeClient(THREADS, outputs, cost_cents=231)
    run = run_intake(client, archive, loader, [EN], lock=LOCK, cap_usd=4, run_id="intake-ac1")

    mounts = {r["mount_path"] for r in client.beta.sessions.created[0]["resources"]}
    assert mounts == {f"/corpus/{EN}.pdf", "/schema/records.json", "/schema/reference.md", "/entities.jsonl"}
    assert client.beta.sessions.created[0]["budget"]["max_list_cost"] == {"amount": "400", "currency": "USD"}
    assert set(run.outputs) == {"facts.jsonl", "review.jsonl", "report.md"}
    assert loader.data.exists("staging/intake-ac1/facts.jsonl")
    assert client.sent[0]["type"] == "user.define_outcome"


def test_spec005_ac4_an_unreadable_file_is_reported_and_the_rest_covered(setup) -> None:  # type: ignore[no-untyped-def]
    archive, loader = setup
    report = f"| {EN}.pdf | covered | | 1 |\n| {DAMAGED}.pdf | not covered | file could not be opened | 0 |\n"
    outputs = {
        "facts.jsonl": facts(node("tender:a", "Tender", "Tender Ref. No. TEST/KW/ROADS/0001", EN)),
        "report.md": report.encode(),
    }
    run = run_intake(FakeClient(THREADS, outputs), archive, loader, [EN, DAMAGED], lock=LOCK, run_id="intake-ac4")
    assert run.status == "complete" and run.not_in_report == []


def test_spec005_ac4_an_input_missing_from_the_report_makes_the_run_incomplete(setup) -> None:  # type: ignore[no-untyped-def]
    archive, loader = setup
    outputs = {
        "facts.jsonl": facts(node("tender:a", "Tender", "Tender Ref. No. TEST/KW/ROADS/0001", EN)),
        "report.md": f"| {EN}.pdf | covered |\n".encode(),
    }
    run = run_intake(FakeClient(THREADS, outputs), archive, loader, [EN, MIXED], lock=LOCK, run_id="intake-ac4b")
    assert run.status == "incomplete" and run.not_in_report == [MIXED]


def test_spec005_ac6_facts_from_a_scanned_page_reach_the_loader_marked(setup) -> None:  # type: ignore[no-untyped-def]
    archive, loader = setup
    outputs = {
        "facts.jsonl": facts(node("work:scan", "Work", "work order", MIXED, page=4)),
        "report.md": f"| {MIXED}.pdf | covered |\n".encode(),
    }
    run = run_intake(FakeClient(THREADS, outputs), archive, loader, [MIXED], lock=LOCK, run_id="intake-ac6")
    report = json.loads(loader.data.get(run.load_report))
    assert report["accepted"] == 1 and report["quote_check"] == {"scan_unchecked": 1}


def test_spec005_ac7_the_run_record_has_everything(setup) -> None:  # type: ignore[no-untyped-def]
    archive, loader = setup
    outputs = {
        "facts.jsonl": facts(node("tender:a", "Tender", "Tender Ref. No. TEST/KW/ROADS/0001", EN)),
        "report.md": f"| {EN}.pdf | covered |\n".encode(),
    }
    run = run_intake(
        FakeClient(THREADS, outputs, cost_cents=231), archive, loader, [EN], lock=LOCK, run_id="intake-ac7"
    )
    row = loader.conn.execute(
        "SELECT session_id, agents, inputs, outputs, status, cost_usd, duration_s, threads, load_report_key"
        " FROM agentkit.runs WHERE run_id = 'intake-ac7'"
    ).fetchone()
    session_id, agents, inputs, outputs_row, status, cost, duration, threads, load_key = row
    assert session_id == "sesn_test" and status == "complete"
    assert agents["ingest-lead"] == "agent_lead@3" and inputs == [EN]
    assert set(outputs_row) == {"facts.jsonl", "report.md"} and float(cost) == 2.31 and duration is not None
    assert [t["agent"] for t in threads] == ["Hishob dev · Document extractor", "Hishob dev · Fact verifier"]
    assert load_key == run.load_report and loader.data.exists(load_key)
    batch = loader.conn.execute("SELECT extractor FROM ledger.batches WHERE batch_id = 'intake-ac7'").fetchone()
    assert batch == ("ingest-lead@3",)


def test_spec005_ac8_a_run_stopped_at_the_cap_is_incomplete(setup) -> None:  # type: ignore[no-untyped-def]
    archive, loader = setup
    run = run_intake(FakeClient([idle("budget_reached")], {}), archive, loader, [EN], lock=LOCK, run_id="intake-ac8")
    assert run.status == "incomplete" and "cap" in run.status_detail


def test_spec005_refuses_to_run_without_applied_agents(setup) -> None:  # type: ignore[no-untyped-def]
    archive, loader = setup
    with pytest.raises(RuntimeError, match="hishob agents apply"):
        run_intake(FakeClient([]), archive, loader, [EN], lock={"agents": {}, "environments": {}})
