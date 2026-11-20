"""SPEC-021 (release slice): the review endpoints. A worker engine starts a run with stub desks; a separate engine
in the API process, which can only answer gates and publish, shows it to a reviewer and takes their decision."""

from __future__ import annotations

from contextlib import contextmanager
from typing import Any

import pytest
from fastapi.testclient import TestClient

from hishob.api.app import ApiConfig, create_app
from hishob.api.tiers import sign
from hishob.archive.storage import LocalStore
from hishob.workflows.w1 import Engine, PublishOnlySteps, publish_outputs
from tests.conftest import TEST_DB

pytestmark = pytest.mark.integration
SECRET = "review-test-secret"


class WorkerSteps:
    """The worker's desks: each ward gets a brief, a case and a held case, as the audit desk would stage them."""

    def __init__(self, data: LocalStore, public: LocalStore) -> None:
        self.data, self.public = data, public

    def intake(self, hashes: list[str], run_id: str) -> dict[str, Any]:
        return {"run_id": run_id, "accepted": 10, "held": 0}

    def audit(self, ward: str, run_id: str) -> dict[str, Any]:
        files, prefix = [], f"staging/{run_id}/"
        for name, text in (
            ("ward-brief.md", f"# Ward {ward}\n\nThe records we hold do not show this.\n"),
            ("cases/case-01-a.md", "case"),
        ):
            self.data.put_new(prefix + name, text.encode(), "text/markdown")
            files.append(prefix + name)
        self.data.put_new(prefix + "held/case-02-b.md", b"held case", "text/markdown")
        return {"ward": ward, "run_id": run_id, "files": files, "status": "complete",
                "held": {prefix + "held/case-02-b.md": "the Challenger held it"}}  # fmt: skip

    def publish(self, audit: dict[str, Any]) -> list[str]:
        return publish_outputs(self.data, self.public, audit)


@pytest.fixture
def world(conn, tmp_path):  # type: ignore[no-untyped-def]
    data, public = LocalStore(tmp_path / "data"), LocalStore(tmp_path / "public")
    worker = Engine(TEST_DB, WorkerSteps(data, public))
    worker.start("t-review", ["a" * 64], ["K/W", "H/W"])  # waits at the release gate

    @contextmanager
    def connect():  # type: ignore[no-untyped-def]
        yield conn

    def client(engine: Any = "api") -> TestClient:
        review = Engine(TEST_DB, PublishOnlySteps(data, public)) if engine == "api" else engine
        config = ApiConfig(connect=connect, sources=data, data=data, graph_driver=None, token_secret=SECRET,
                           public_per_minute=10_000, review=review)  # fmt: skip
        return TestClient(create_app(config))

    return client, public, worker


def token(tier: str, account: str = "acct_nair") -> dict[str, str]:
    return {"Authorization": "Bearer " + sign(tier, account, SECRET)}


# AC1 · R1 -------------------------------------------------------------------------------------------------------


def test_spec021_ac1_only_a_reviewer_may_use_the_review_endpoints(world) -> None:  # type: ignore[no-untyped-def]
    client, _, _ = world
    web = client()
    for headers in ({}, token("contributor"), token("official"), token("researcher")):
        assert web.get("/review/threads", headers=headers).status_code == 403
        assert web.get("/review/files", params={"key": "staging/x"}, headers=headers).status_code == 403
        assert (
            web.post(
                "/review/threads/t-review/decision", json={"decision": "approve", "reason": "ok"}, headers=headers
            ).status_code
            == 403
        )
    assert web.get("/review/threads", headers=token("reviewer")).status_code == 200
    assert client(engine=None).get("/review/threads", headers=token("reviewer")).status_code == 503  # not enabled


# AC2 · R2 -------------------------------------------------------------------------------------------------------


def test_spec021_ac2_a_waiting_run_shows_its_gate_its_staged_files_and_what_is_held(world) -> None:  # type: ignore[no-untyped-def]
    client, _, _ = world
    [run] = client().get("/review/threads", headers=token("reviewer")).json()
    assert run["thread"] == "t-review" and run["finished"] is False and run["decisions"] == []
    gate = run["waiting"]
    assert gate["gate"] == "release" and gate["wards"] == ["H/W", "K/W"]
    assert sorted(f.rsplit("/", 1)[-1] for f in gate["staged"]["K/W"]) == ["case-01-a.md", "ward-brief.md"]
    [(held_key, reason)] = gate["held"]["K/W"].items()
    assert held_key.endswith("held/case-02-b.md") and reason == "the Challenger held it"
    assert not any("/held/" in f for files in gate["staged"].values() for f in files)  # held files are never offered
    assert any(line.startswith("audit: K/W") for line in run["log"])


# AC3 · R3 -------------------------------------------------------------------------------------------------------


def test_spec021_ac3_a_reviewer_reads_staged_files_and_nothing_else(world) -> None:  # type: ignore[no-untyped-def]
    client, _, _ = world
    web, reviewer = client(), token("reviewer")
    [run] = web.get("/review/threads", headers=reviewer).json()
    brief = next(f for f in run["waiting"]["staged"]["K/W"] if f.endswith("ward-brief.md"))
    got = web.get("/review/files", params={"key": brief}, headers=reviewer).json()
    assert got["key"] == brief and "# Ward K/W" in got["text"] and got["truncated"] is False
    for bad in (
        "published/x",
        "../etc/passwd",
        "staging/../secrets",
        "staging/a\\b",
        "data/ledger.jsonl",
        "staging/missing.md",
    ):
        assert web.get("/review/files", params={"key": bad}, headers=reviewer).status_code == 404, bad


# AC4 · R4, R5 ---------------------------------------------------------------------------------------------------


def test_spec021_ac4_a_decision_needs_a_reviewer_and_a_reason_and_is_recorded(world) -> None:  # type: ignore[no-untyped-def]
    client, public, _ = world
    web, reviewer = client(), token("reviewer", "acct_nair")
    url = "/review/threads/t-review/decision"
    assert (
        web.post(url, json={"decision": "approve", "reason": "fine"}, headers=token("contributor")).status_code == 403
    )
    assert web.post(url, json={"decision": "approve", "reason": ""}, headers=reviewer).status_code == 422
    assert web.post(url, json={"decision": "release it all"}, headers=reviewer).status_code == 422  # no reason at all
    assert (
        web.post(url, json={"decision": "maybe", "reason": "unsure"}, headers=reviewer).status_code == 422
    )  # not an answer
    assert public.list("") == []  # nothing public so far

    done = web.post(url, json={"decision": ["K/W"], "reason": "H/W brief needs rework"}, headers=reviewer)
    assert done.status_code == 200 and done.json()["finished"] is True
    published = public.list("published/")
    assert published and {p.split("/")[1] for p in published} == {"k-w"}  # only the approved ward
    assert not any("held" in p for p in published)  # the held case stays held
    [run] = web.get("/review/threads", headers=reviewer).json()
    [decision] = run["decisions"]
    assert (decision["gate"], decision["decision"], decision["reason"], decision["account_id"]) == (
        "release", ["K/W"], "H/W brief needs rework", "acct_nair",
    )  # fmt: skip
    assert (
        web.post(url, json={"decision": "approve", "reason": "again"}, headers=reviewer).status_code == 409
    )  # no longer waiting


def test_spec021_ac4_holding_publishes_nothing(world) -> None:  # type: ignore[no-untyped-def]
    client, public, _ = world
    done = client().post(
        "/review/threads/t-review/decision",
        json={"decision": "hold", "reason": "needs legal review"},
        headers=token("reviewer"),
    )
    assert done.status_code == 200 and done.json()["finished"] is True and public.list("") == []


# AC5 · R6 -------------------------------------------------------------------------------------------------------


def test_spec021_ac5_the_api_process_answers_a_gate_a_worker_started_and_never_runs_a_desk(world) -> None:  # type: ignore[no-untyped-def]
    client, public, worker = world
    steps = PublishOnlySteps(LocalStore(public.root.parent / "data"), public)  # type: ignore[attr-defined]
    with pytest.raises(RuntimeError, match="worker"):
        steps.intake(["a"], "r")
    with pytest.raises(RuntimeError, match="worker"):
        steps.audit("K/W", "r")
    # a different engine, with other steps, resumes the run and publishes: state lives in Postgres
    done = client().post(
        "/review/threads/t-review/decision",
        json={"decision": "approve", "reason": "checked"},
        headers=token("reviewer"),
    )
    assert done.json()["finished"] is True and len(public.list("published/")) == 4  # two wards, two released files each
    assert worker.status("t-review").finished is True
