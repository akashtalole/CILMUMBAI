"""The API side of the resident view (SPEC-020 demo slice): place shapes for the map, asking the citizen desk over
HTTP as a job, and serving the built web app. The desk's turns are scripted; the API behind it is real."""

from __future__ import annotations

import time
from dataclasses import replace
from typing import Any

import pytest
from fastapi.testclient import TestClient

from hishob.agentkit.citizen import answer_question
from hishob.api.app import create_app
from hishob.api.ask import public_answer
from hishob.api.tiers import sign
from tests.fakes import FakeClient, call, idle, say
from tests.integration.test_spec007_api import SECRET, api  # noqa: F401  (fixture: API over the SPEC-006 scenario)

pytestmark = [pytest.mark.integration, pytest.mark.graph]
LOCK = {
    "agents": {"citizen-desk": {"id": "agent_desk", "version": 1}},
    "environments": {"civic-cloud": {"id": "env_1"}},
}


def desk_app(config: Any, tender: str, seen: list[dict[str, Any]], **changes: Any) -> TestClient:
    def run(http: Any, question: str, **kwargs: Any) -> dict[str, Any]:
        seen.append(kwargs)
        turns = [
            [
                call("find_place", text="S. V. Road"),
                call("trace_money", node_id="road:sv"),
                call("get_fact", fact_id=tender),
                say(f"The tender TEST/KW/ROADS/0001 [{tender}] was **estimated** at Rs. 4,20,00,000 [{tender}]."),
                idle(),
            ]
        ]
        answer = answer_question(
            FakeClient(turns),
            http,
            question,
            language_hint=kwargs["language"],
            location=kwargs["location"],
            token=kwargs["token"],
            lock=LOCK,
        )
        return public_answer(answer)

    return TestClient(create_app(replace(config, ask=run, **changes)))


def wait(client: TestClient, job_id: str) -> dict[str, Any]:
    for _ in range(100):
        job = client.get(f"/ask/{job_id}").json()
        if job["status"] != "running":
            return job
        time.sleep(0.05)
    raise AssertionError("the job did not finish")


def test_spec020_ac7_a_ward_has_a_shape_for_the_map_and_an_unknown_place_does_not(api) -> None:  # type: ignore[no-untyped-def]  # noqa: F811
    client, _, _ = api
    shape = client.get("/places/adminward:k-w/shape").json()
    assert shape["type"] == "Feature" and shape["geometry"]["type"] in {"Polygon", "MultiPolygon"}
    assert shape["properties"] == {"node_id": "adminward:k-w", "name": "K/W", "kind": "AdminWard"}
    assert client.get("/places/road:nowhere/shape").status_code == 404


def test_spec020_ac6_asking_is_off_without_claude_credentials(api) -> None:  # type: ignore[no-untyped-def]  # noqa: F811
    client, _, _ = api
    assert client.post("/ask", json={"question": "Who fixes S. V. Road?"}).status_code == 503


def test_spec020_ac5_a_question_becomes_a_job_with_a_sourced_answer(api) -> None:  # type: ignore[no-untyped-def]  # noqa: F811
    _, config, ids = api
    seen: list[dict[str, Any]] = []
    client = desk_app(config, ids["tender"], seen)
    token = sign("contributor", "acct_resident1", SECRET)
    started = client.post(
        "/ask",
        json={"question": "How much was S. V. Road?", "language": "en", "lat": 19.1, "lon": 72.83},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert started.status_code == 202
    job = wait(client, started.json()["id"])
    assert job["status"] == "done", job
    answer = job["answer"]
    assert "**estimated**" in answer["body"] and "Sources:" not in answer["body"] and "Sources:" in answer["text"]
    assert answer["sources"][0]["quote"] == "Tender Ref. No. TEST/KW/ROADS/0001"
    # the desk read through the API as the resident, at the resident's tier and location
    assert seen == [{"language": "en", "location": (19.1, 72.83), "token": token}]
    assert client.get("/ask/not-a-job").status_code == 404


def test_spec020_ac6_the_desk_s_own_calls_do_not_spend_the_resident_s_limit(api) -> None:  # type: ignore[no-untyped-def]  # noqa: F811
    _, config, ids = api
    client = desk_app(config, ids["tender"], [], public_per_minute=2)  # fewer than the desk's tool calls
    job = wait(client, client.post("/ask", json={"question": "How much was S. V. Road?"}).json()["id"])
    assert job["status"] == "done", job  # every tool call went through
    # but an outside caller is still limited
    codes = [client.get("/places", params={"q": "K/W"}).status_code for _ in range(4)]
    assert 429 in codes


def test_spec020_ac6_questions_are_limited_per_client_per_hour(api) -> None:  # type: ignore[no-untyped-def]  # noqa: F811
    _, config, ids = api
    client = desk_app(config, ids["tender"], [], ask_per_hour=2)
    replies = [client.post("/ask", json={"question": f"Question number {i}?"}) for i in range(3)]
    assert [r.status_code for r in replies] == [202, 202, 429]
    assert "2 questions an hour" in client.post("/ask", json={"question": "One more?"}).json()["detail"]
    for reply in replies[:2]:
        wait(client, reply.json()["id"])  # let the accepted jobs finish before the stores close


def test_spec020_ac8_the_built_web_app_is_served_beside_the_api(api, tmp_path) -> None:  # type: ignore[no-untyped-def]  # noqa: F811
    _, config, _ = api
    (tmp_path / "index.html").write_text("<!doctype html><title>Aamcha Hishob</title>", encoding="utf-8")
    client = TestClient(create_app(replace(config, web_dir=tmp_path)))
    assert "Aamcha Hishob" in client.get("/").text
    assert client.get("/places", params={"q": "K/W"}).json()[0]["node_id"] == "adminward:k-w"  # API routes first
