"""Acceptance tests for SPEC-009: workflow engine and human gates, with stub desks."""

from __future__ import annotations

import json
from collections import Counter
from typing import Any

import boto3
import pytest
from moto import mock_aws

from hishob.archive.storage import LocalStore
from hishob.workflows.w1 import Engine, GateError, consume, publish_outputs
from tests.conftest import TEST_DB

pytestmark = pytest.mark.integration


class StubSteps:
    """Records calls; writes two output files per audited ward to the data store."""

    def __init__(self, data: LocalStore, public: LocalStore, accepted: int = 9, held: int = 1) -> None:
        self.data, self.public = data, public
        self.accepted, self.held = accepted, held
        self.calls: Counter[str] = Counter()
        self.fail_publish_after: int | None = None

    def intake(self, hashes: list[str], run_id: str) -> dict[str, Any]:
        self.calls["intake"] += 1
        return {"run_id": run_id, "accepted": self.accepted, "held": self.held}

    def audit(self, ward: str, run_id: str) -> dict[str, Any]:
        self.calls[f"audit:{ward}"] += 1
        files = []
        for name, text in (("ward-brief.md", f"# {ward}\n"), ("gaps.jsonl", '{"record": "budget head"}\n')):
            key = f"staging/{run_id}/{name}"
            self.data.put_new(key, text.encode(), "text/plain")
            files.append(key)
        return {"ward": ward, "run_id": run_id, "files": files}

    def publish(self, audit: dict[str, Any]) -> list[str]:
        self.calls["publish"] += 1
        if self.fail_publish_after is not None:
            limit, self.fail_publish_after = self.fail_publish_after, None
            partial = dict(audit, files=audit["files"][:limit])
            publish_outputs(self.data, self.public, partial)
            raise RuntimeError("worker killed while publishing")
        return publish_outputs(self.data, self.public, audit)


@pytest.fixture
def setup(conn, tmp_path):  # type: ignore[no-untyped-def]
    data, public = LocalStore(tmp_path / "data"), LocalStore(tmp_path / "public")
    steps = StubSteps(data, public)
    return steps, public, lambda: Engine(TEST_DB, steps)


# AC1 · R1 -------------------------------------------------------------------------------------------------------


def test_spec009_ac1_w1_runs_to_the_release_gate(setup) -> None:  # type: ignore[no-untyped-def]
    steps, _, engine = setup
    status = engine().start("t-ac1", ["a" * 64], ["K/W", "H/W"])
    assert status.waiting == {
        "gate": "release",
        "wards": ["H/W", "K/W"],
        "question": "Review each ward's outputs. Which may be published?",
    }
    # the two audits run in parallel (one Send per ward), so their order in the log is not fixed
    assert status.log[0] == "intake: 9 facts loaded, 1 held"
    assert sorted(status.log[1:]) == ["audit: H/W", "audit: K/W"]
    assert steps.calls == Counter({"intake": 1, "audit:K/W": 1, "audit:H/W": 1})


# AC2 · R2 -------------------------------------------------------------------------------------------------------


def test_spec009_ac2_a_new_process_resumes_from_the_gate(setup) -> None:  # type: ignore[no-untyped-def]
    steps, public, engine = setup
    engine().start("t-ac2", ["a" * 64], ["K/W"])
    # Every call below uses a fresh engine and fresh connections: nothing is carried in memory, as after a restart.
    assert engine().status("t-ac2").waiting["gate"] == "release"
    done = engine().resume("t-ac2", "approve", reason="checked brief and gaps", account="acct_nair", tier="reviewer")
    assert done.finished and len(done.published) == 2
    assert steps.calls["intake"] == 1 and steps.calls["audit:K/W"] == 1  # nothing was redone
    assert public.list("published/") == sorted(done.published)


# AC3 · R3 -------------------------------------------------------------------------------------------------------


@mock_aws
def test_spec009_ac3_a_queue_message_starts_a_run(setup) -> None:  # type: ignore[no-untyped-def]
    _, _, engine = setup
    sqs = boto3.client("sqs", region_name="ap-south-1")
    queue = sqs.create_queue(QueueName="workflow-runs")["QueueUrl"]
    body = {"workflow": "W1", "thread": "t-ac3", "hashes": ["a" * 64], "wards": ["K/W"]}
    sqs.send_message(QueueUrl=queue, MessageBody=json.dumps(body))
    [status] = consume(sqs, queue, engine())
    assert status.thread == "t-ac3" and status.waiting["gate"] == "release"
    assert sqs.receive_message(QueueUrl=queue, WaitTimeSeconds=0).get("Messages") is None  # deleted once started


def test_spec009_ac3_a_thread_id_is_used_once(setup) -> None:  # type: ignore[no-untyped-def]
    _, _, engine = setup
    engine().start("t-once", ["a" * 64], ["K/W"])
    with pytest.raises(ValueError, match="already exists"):
        engine().start("t-once", ["a" * 64], ["K/W"])


# AC4 · R4 -------------------------------------------------------------------------------------------------------


def test_spec009_ac4_many_held_facts_pause_for_review(setup) -> None:  # type: ignore[no-untyped-def]
    steps, _, engine = setup
    steps.accepted, steps.held = 7, 3  # 30% held, threshold 20%
    status = engine().start("t-ac4", ["a" * 64], ["K/W"])
    assert status.waiting["gate"] == "review_facts" and not any("audit" in c for c in steps.calls)
    after = engine().resume("t-ac4", "continue", reason="held facts are scans", account="acct_nair", tier="reviewer")
    assert after.waiting["gate"] == "release" and steps.calls["audit:K/W"] == 1


def test_spec009_ac4_few_held_facts_go_straight_to_audit(setup) -> None:  # type: ignore[no-untyped-def]
    steps, _, engine = setup
    steps.accepted, steps.held = 9, 1  # 10%
    assert engine().start("t-ac4b", ["a" * 64], ["K/W"]).waiting["gate"] == "release"


def test_spec009_ac4_stop_at_review_ends_the_run(setup) -> None:  # type: ignore[no-untyped-def]
    steps, _, engine = setup
    steps.accepted, steps.held = 5, 5
    engine().start("t-stop", ["a" * 64], ["K/W"])
    done = engine().resume("t-stop", "stop", reason="extraction looks wrong", account="acct_nair", tier="reviewer")
    assert done.finished and "review_facts: stop" in done.log and not steps.calls["audit:K/W"]


# AC5 · R5 -------------------------------------------------------------------------------------------------------


def test_spec009_ac5_nothing_is_public_while_waiting_for_release(setup) -> None:  # type: ignore[no-untyped-def]
    _, public, engine = setup
    engine().start("t-ac5", ["a" * 64], ["K/W"])
    assert public.list("") == []
    engine().resume("t-ac5", "hold", reason="needs legal review", account="acct_nair", tier="reviewer")
    assert public.list("") == []  # held: still nothing public


def test_spec009_release_can_approve_some_wards(setup) -> None:  # type: ignore[no-untyped-def]
    _, public, engine = setup
    engine().start("t-some", ["a" * 64], ["K/W", "H/W"])
    done = engine().resume("t-some", ["K/W"], reason="H/W brief needs rework", account="acct_nair", tier="reviewer")
    assert {k.split("/")[1] for k in public.list("published/")} == {"k-w"}
    assert done.log[-2] == "release: K/W"


# AC6 · R6 -------------------------------------------------------------------------------------------------------


def test_spec009_ac6_only_a_reviewer_may_resume_and_decisions_are_recorded(setup, conn) -> None:  # type: ignore[no-untyped-def]
    _, _, engine = setup
    engine().start("t-ac6", ["a" * 64], ["K/W"])
    with pytest.raises(GateError):
        engine().resume("t-ac6", "approve", reason="looks fine", account="acct_resident", tier="contributor")
    with pytest.raises(ValueError, match="reason"):
        engine().resume("t-ac6", "approve", reason=" ", account="acct_nair", tier="reviewer")
    engine().resume("t-ac6", "approve", reason="checked every case file", account="acct_nair", tier="reviewer")
    rows = conn.execute(
        "SELECT gate, decision, reason, account_id FROM flow.decisions WHERE thread_id = 't-ac6'"
    ).fetchall()
    assert rows == [("release", '"approve"', "checked every case file", "acct_nair")]


# AC7 · R7 -------------------------------------------------------------------------------------------------------


def test_spec009_ac7_a_publish_interrupted_part_way_completes_once(setup) -> None:  # type: ignore[no-untyped-def]
    steps, public, engine = setup
    engine().start("t-ac7", ["a" * 64], ["K/W"])
    steps.fail_publish_after = 1  # the "worker" dies after publishing one of two files
    with pytest.raises(RuntimeError, match="killed"):
        engine().resume("t-ac7", "approve", reason="ok", account="acct_nair", tier="reviewer")
    assert len(public.list("published/")) == 1
    done = engine().retry("t-ac7")
    assert done.finished and len(public.list("published/")) == 2 and sorted(done.published) == public.list("published/")
    assert steps.calls["intake"] == 1 and steps.calls["audit:K/W"] == 1


def test_spec009_ac6_cli_refuses_a_resume_without_a_reviewer_token(monkeypatch, capsys) -> None:  # type: ignore[no-untyped-def]
    from hishob import cli
    from hishob.api.tiers import sign

    monkeypatch.setenv("HISHOB_TOKEN_SECRET", "s3cret")
    for token in (sign("contributor", "acct_resident", "s3cret"), sign("reviewer", "acct_nair", "wrong-secret")):
        code = cli.main(["workflow", "resume", "t1", "approve", "--reason", "fine", "--token", token])
        assert code == 2 and "refused" in capsys.readouterr().err
