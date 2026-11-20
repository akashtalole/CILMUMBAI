"""SPEC-030 through the API: a photo in, a job out, with the vision model and the desk's turns scripted and the real
query API and ledger behind the desk. Includes what must never be logged or kept (AC6)."""

from __future__ import annotations

import io
import json
import logging
import time
from dataclasses import replace
from types import SimpleNamespace as NS
from typing import Any

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from hishob.agentkit.photo import public_report, report_from_photo
from hishob.api.app import create_app
from tests.fakes import FakeClient, call, idle, say
from tests.integration.test_spec007_api import api  # noqa: F401  (fixture: API over the SPEC-006 scenario)

pytestmark = [pytest.mark.integration, pytest.mark.graph]
LOCK = {
    "agents": {"citizen-desk": {"id": "agent_desk", "version": 1}},
    "environments": {"civic-cloud": {"id": "env_1"}},
}
HEADERS = {"Content-Type": "image/jpeg"}
WHERE = {"lat": 19.1137, "lon": 72.8355}


def jpeg() -> bytes:
    out = io.BytesIO()
    Image.new("RGB", (320, 240), (80, 80, 85)).save(out, "JPEG")
    return out.getvalue()


def photo_app(config: Any, tender: str, vision_reply: str, **changes: Any) -> tuple[TestClient, list[dict[str, Any]]]:
    sent: list[dict[str, Any]] = []

    def run(http: Any, question: str, **kwargs: Any) -> dict[str, Any]:
        turns = [
            [
                call("trace_money", node_id="road:sv"),
                say(f"The tender TEST/KW/ROADS/0001 [{tender}] was estimated at Rs. 4,20,00,000 [{tender}]."),
                idle(),
            ]
        ]
        client = FakeClient(turns)

        def create(**request: Any) -> NS:
            sent.append(request)
            return NS(content=[NS(type="text", text=vision_reply)])

        client.messages = NS(create=create)  # type: ignore[attr-defined]
        return public_report(
            report_from_photo(client, http, kwargs.pop("photo"), lock=LOCK, **kwargs)  # type: ignore[arg-type]
        )

    return TestClient(create_app(replace(config, photo=run, **changes))), sent


def finish(client: TestClient, job_id: str) -> dict[str, Any]:
    for _ in range(100):
        job = client.get(f"/report/{job_id}").json()
        if job["status"] != "running":
            return job
        time.sleep(0.05)
    raise AssertionError("the job did not finish")


# AC5 · R4, R6 ---------------------------------------------------------------------------------------------------


def test_spec030_ac5_a_photo_becomes_a_job_with_the_finding_and_a_sourced_answer(api) -> None:  # type: ignore[no-untyped-def]  # noqa: F811
    _, config, ids = api
    client, sent = photo_app(config, ids["tender"], '{"issue": "pothole", "confidence": "high"}')
    started = client.post("/report", params={"language": "en", **WHERE}, content=jpeg(), headers=HEADERS)
    assert started.status_code == 202
    job = finish(client, started.json()["id"])
    assert job["status"] == "done", job
    result = job["answer"]
    assert (result["status"], result["issue"], result["confidence"], result["location_from"]) == (
        "answered", "pothole", "high", "device",
    )  # fmt: skip
    assert result["answer"]["sources"][0]["quote"] == "Tender Ref. No. TEST/KW/ROADS/0001"
    image = sent[0]["messages"][0]["content"][0]
    assert image["source"]["media_type"] == "image/jpeg" and len(image["source"]["data"]) > 100


def test_spec030_ac5_an_unclear_photo_and_a_missing_location_are_answered_without_a_desk_session(api) -> None:  # type: ignore[no-untyped-def]  # noqa: F811
    _, config, ids = api
    unclear, _ = photo_app(config, ids["tender"], '{"issue": "none", "confidence": "high"}')
    job = finish(
        unclear,
        unclear.post("/report", params={"language": "mr", **WHERE}, content=jpeg(), headers=HEADERS).json()["id"],
    )
    assert job["answer"]["status"] == "unclear" and job["answer"]["answer"] is None
    nowhere, sent = photo_app(config, ids["tender"], '{"issue": "pothole", "confidence": "high"}')
    job = finish(
        nowhere, nowhere.post("/report", params={"language": "hi"}, content=jpeg(), headers=HEADERS).json()["id"]
    )
    assert job["answer"]["status"] == "no_location" and sent == []  # the model was never called


def test_spec030_ac5_uploads_that_are_not_photos_are_refused_before_any_model_call(api) -> None:  # type: ignore[no-untyped-def]  # noqa: F811
    _, config, ids = api
    client, sent = photo_app(config, ids["tender"], '{"issue": "pothole", "confidence": "high"}')
    params = {"language": "en", **WHERE}
    assert client.post("/report", params=params, json={"photo": "x"}).status_code == 415  # not an image content type
    assert client.post("/report", params=params, content=b"just text", headers=HEADERS).status_code == 422
    assert client.post("/report", params=params, content=b"\x00" * 10_000_001, headers=HEADERS).status_code == 413
    assert client.post("/report", params={"language": "fr"}, content=jpeg(), headers=HEADERS).status_code == 422
    assert (
        client.post(
            "/report", params={"language": "en", "lat": 95, "lon": 0}, content=jpeg(), headers=HEADERS
        ).status_code
        == 422
    )
    assert sent == []


def test_spec030_ac5_photo_reports_are_off_without_credentials_and_limited_per_client(api) -> None:  # type: ignore[no-untyped-def]  # noqa: F811
    client, config, ids = api
    assert (
        client.post("/report", params={"language": "en", **WHERE}, content=jpeg(), headers=HEADERS).status_code == 503
    )
    limited, _ = photo_app(config, ids["tender"], '{"issue": "pothole", "confidence": "high"}', photo_per_hour=2)
    posts = [
        limited.post("/report", params={"language": "en", **WHERE}, content=jpeg(), headers=HEADERS) for _ in range(3)
    ]
    assert [p.status_code for p in posts] == [202, 202, 429]
    for accepted in posts[:2]:
        finish(limited, accepted.json()["id"])  # polling is never limited, and the jobs end before the stores close
    assert limited.get("/report/not-a-job").status_code == 404


# AC6 · R5 -------------------------------------------------------------------------------------------------------


def test_spec030_ac6_neither_the_photo_nor_where_it_was_taken_is_logged_or_kept(api, caplog) -> None:  # type: ignore[no-untyped-def]  # noqa: F811
    _, config, ids = api
    client, _ = photo_app(config, ids["tender"], '{"issue": "pothole", "confidence": "high"}')
    with caplog.at_level(logging.INFO, logger="hishob.api.requests"):
        started = client.post("/report", params={"language": "en", **WHERE}, content=jpeg(), headers=HEADERS)
        job = finish(client, started.json()["id"])
    lines = [r.getMessage() for r in caplog.records if r.name == "hishob.api.requests"]
    report_lines = [json.loads(line) for line in lines if '"/report"' in line]
    assert report_lines and report_lines[0]["params"]["lat"] == "<7 chars>"  # logged by length only
    assert not any("19.1137" in line or "72.8355" in line for line in lines)
    kept = json.dumps(job)  # everything the server keeps about the job, which is what the page is sent
    assert "19.1137" not in kept and "72.8355" not in kept and "photo" not in job["answer"]
    assert "base64" not in kept and "image/jpeg" not in kept  # no image content in the result
