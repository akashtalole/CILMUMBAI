"""Acceptance tests for SPEC-007: query API, access tiers and citation check."""

from __future__ import annotations

import json
import logging
from contextlib import contextmanager

import pytest
from fastapi.testclient import TestClient

from hishob.api.app import ApiConfig, create_app
from hishob.api.tiers import sign
from hishob.graphstore import GraphStore
from hishob.ledger import Loader
from hishob.place import geo
from hishob.place.importer import import_wards
from tests.conftest import FIXED_NOW, FIXTURES
from tests.integration.test_spec006_graph import AWARD, EN, SCENARIO, edge, node

pytestmark = [pytest.mark.integration, pytest.mark.graph]
SECRET = "test-secret-not-for-production"
RESIDENT_PAYMENT = dict(
    node(
        "payment:resident-report",
        "Payment",
        "Mobilisation advance released to Shree Ganesh Infrastructure",
        source=AWARD,
        page=2,
        paid_on="2026-09-12",
    ),
    tier="citizen",
)


def bearer(tier: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {sign(tier, 'acct_' + tier, SECRET)}"}


@pytest.fixture
def api(make_archive, conn, graph_driver):  # type: ignore[no-untyped-def]
    archive = make_archive()
    for name in ("tender-en.pdf", "award-notice.pdf"):
        archive.add_file(FIXTURES / name, publisher="bmc", licence="test fixture")
    upload = archive.add_upload((FIXTURES / "site-board.png").read_bytes(), "photo.png", account_id="acct_resident1")
    loader = Loader(conn, archive, archive.data, now=lambda: FIXED_NOW)
    report = loader.load(
        [dict(r) for r in SCENARIO]
        + [
            dict(RESIDENT_PAYMENT),
            dict(
                edge(
                    "UNDER_CONTRACT",
                    "payment:resident-report",
                    "contract:kw-roads-1",
                    "Mobilisation advance released to Shree Ganesh Infrastructure",
                    source=AWARD,
                    page=2,
                ),
                tier="citizen",
            ),
        ],
        batch_id="api-world",
        extractor="test@1",
    )
    held = archive.data.get("staging/api-world/held.jsonl").decode() if report.held else ""
    assert report.held == {}, held
    import_wards(
        archive,
        loader,
        FIXTURES / "wards-fixture.geojson",
        kind="admin",
        name_property="name",
        publisher="datameet",
        licence="test fixture",
        batch_id="api-wards",
    )
    geo.build(conn)
    GraphStore(graph_driver, conn, archive.data).apply()

    @contextmanager
    def connect():  # type: ignore[no-untyped-def]
        yield conn

    config = ApiConfig(
        connect=connect,
        sources=archive.sources,
        data=archive.data,
        graph_driver=graph_driver,
        token_secret=SECRET,
        public_per_minute=1000,
    )
    client = TestClient(create_app(config))
    tender_fact = loader.conn.execute(
        "SELECT fact_id FROM ledger.current WHERE node_id = 'tender:kw-roads-1'"
    ).fetchone()[0]
    resident_fact = loader.conn.execute(
        "SELECT fact_id FROM ledger.current WHERE node_id = 'payment:resident-report'"
    ).fetchone()[0]
    conn.commit()
    return client, config, {"tender": tender_fact, "resident": resident_fact, "upload": upload.sha256}


# AC1 · R1 -------------------------------------------------------------------------------------------------------


def test_spec007_ac1_every_endpoint_answers_with_its_shape(api) -> None:  # type: ignore[no-untyped-def]
    client, _, ids = api
    assert client.get("/places", params={"q": "K/W"}).json()[0]["node_id"] == "adminward:k-w"
    assert client.get("/point", params={"lat": 19.10, "lon": 72.82}).json()["admin_ward"]["code"] == "K/W"
    view = client.get("/views/trace_money", params={"id": "road:sv"}).json()
    assert set(view) == {"rows", "gaps", "query_ms"}
    assert client.get(f"/facts/{ids['tender']}").json()["label"] == "Tender"
    page = client.get(f"/sources/{EN}/pages/1").json()
    assert "Tender Ref. No. TEST/KW/ROADS/0001" in page["text"]
    check = client.post(
        "/answers/check", json={"text": "Estimated cost ₹4.2 crore.", "cited_fact_ids": [ids["tender"]]}
    )
    assert check.json()["ok"] is True
    assert client.get("/views/not_a_view", params={"id": "x"}).status_code == 404


# AC2 · R2, R3 ---------------------------------------------------------------------------------------------------


def test_spec007_ac2_no_or_bad_credential_is_public(api) -> None:  # type: ignore[no-untyped-def]
    client, _, _ = api
    assert client.get("/places", params={"q": "K/W"}).headers["X-Hishob-Tier"] == "public"
    forged = {"Authorization": "Bearer reviewer.acct_x.0000"}
    assert client.get("/places", params={"q": "K/W"}, headers=forged).headers["X-Hishob-Tier"] == "public"
    assert (
        client.get("/places", params={"q": "K/W"}, headers=bearer("researcher")).headers["X-Hishob-Tier"]
        == "researcher"
    )


# AC3 · R4 -------------------------------------------------------------------------------------------------------


def test_spec007_ac3_residents_reports_are_hidden_from_the_public(api) -> None:  # type: ignore[no-untyped-def]
    client, _, ids = api

    def payments(headers: dict[str, str]) -> list[str]:
        rows = client.get("/views/trace_money", params={"id": "road:sv"}, headers=headers).json()["rows"]
        return [h["node"]["id"] for h in rows[0]["hops"] if h["hop"] == "payment"]

    assert payments({}) == ["payment:mob-advance"]
    assert payments(bearer("researcher")) == ["payment:mob-advance", "payment:resident-report"]
    assert client.get(f"/facts/{ids['resident']}").status_code == 404
    assert client.get(f"/facts/{ids['resident']}", headers=bearer("researcher")).status_code == 200


def test_spec007_ac3_residents_uploads_are_for_reviewers_only(api) -> None:  # type: ignore[no-untyped-def]
    client, _, ids = api
    assert client.get(f"/sources/{ids['upload']}/pages/1", headers=bearer("researcher")).status_code == 404
    assert client.get(f"/sources/{ids['upload']}/pages/1", headers=bearer("reviewer")).status_code == 200


def test_spec007_ac3_a_public_answer_cannot_cite_a_hidden_fact(api) -> None:  # type: ignore[no-untyped-def]
    client, _, ids = api
    body = {"text": "Paid on 12 September 2026.", "cited_fact_ids": [ids["resident"]]}
    public = client.post("/answers/check", json=body).json()
    assert public["ok"] is False and {"kind": "fact_id", "text": ids["resident"]} in public["unmatched"]
    assert client.post("/answers/check", json=body, headers=bearer("researcher")).json()["ok"] is True


# AC4, AC5 · R5, R6 ----------------------------------------------------------------------------------------------


def test_spec007_ac4_ac5_the_check_through_the_api(api) -> None:  # type: ignore[no-untyped-def]
    client, _, ids = api
    good = client.post(
        "/answers/check",
        json={"text": "Estimated cost Rs. 4,20,00,000 for TEST/KW/ROADS/0001.", "cited_fact_ids": [ids["tender"]]},
    ).json()
    assert good["ok"] is True
    bad = client.post("/answers/check", json={"text": "Estimated cost ₹5 crore.", "cited_fact_ids": [ids["tender"]]})
    assert bad.json() == {"ok": False, "matched": [], "unmatched": [{"kind": "amount", "text": "₹5 crore"}]}


# AC7 · R7 -------------------------------------------------------------------------------------------------------


def test_spec007_ac7_returned_facts_carry_full_provenance(api) -> None:  # type: ignore[no-untyped-def]
    client, _, ids = api
    fact = client.get(f"/facts/{ids['tender']}").json()
    assert {"source", "page", "quote", "tier", "quote_check", "source_fetched_at"} <= fact.keys()
    rows = client.get("/views/trace_money", params={"id": "road:sv"}).json()["rows"]
    for hop in rows[0]["hops"]:
        assert hop["node"]["quote"] and hop["node"]["source_fetched_at"] and hop["node"]["source"] in {EN, AWARD}


# AC8 · R8 -------------------------------------------------------------------------------------------------------


def test_spec007_ac8_requests_are_logged_without_personal_data(api, caplog) -> None:  # type: ignore[no-untyped-def]
    client, _, ids = api
    secret_text = "Sunita Patil 9820012345 says the drain overflows"
    with caplog.at_level(logging.INFO, logger="hishob.api.requests"):
        client.post("/answers/check", json={"text": secret_text, "cited_fact_ids": [ids["tender"]]})
        client.get("/places", params={"q": secret_text})
    lines = [json.loads(r.getMessage()) for r in caplog.records if r.name == "hishob.api.requests"]
    assert lines[0]["tier"] == "public" and lines[0]["endpoint"] == "/answers/check"
    assert lines[0]["fact_ids"] == [ids["tender"]]
    assert lines[1]["params"]["q"] == f"<{len(secret_text)} chars>"
    assert "9820012345" not in caplog.text and "Sunita" not in caplog.text


# AC9 · R9 -------------------------------------------------------------------------------------------------------


def test_spec007_ac9_public_callers_are_rate_limited(api) -> None:  # type: ignore[no-untyped-def]
    _, config, _ = api
    config.public_per_minute = 3
    client = TestClient(create_app(config))
    codes = [client.get("/places", params={"q": "K/W"}).status_code for _ in range(4)]
    assert codes == [200, 200, 200, 429]
    assert client.get("/places", params={"q": "K/W"}, headers=bearer("official")).status_code == 200
