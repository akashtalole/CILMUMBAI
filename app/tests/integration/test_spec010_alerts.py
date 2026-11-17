"""Acceptance tests for SPEC-010: saved areas and street alerts, on the fixture roads and the S. V. Road scenario."""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from typing import Any

import pytest

from hishob import alerts
from hishob.ledger import Loader
from hishob.place import geo
from hishob.place.importer import import_roads
from tests.conftest import FIXTURES
from tests.integration.test_spec006_graph import EN, edge, node

pytestmark = [pytest.mark.integration, pytest.mark.graph]
T0 = datetime(2026, 11, 1, 9, 0, tzinfo=UTC)
SV = "road:osm-1001"  # fixture S. V. Road, a line from (19.10, 72.835) to (19.13, 72.836)
NEAR_SV = (19.11, 72.8355)
HEAD = "Roads and Traffic Department, K/West Ward"
REF = "Tender Ref. No. TEST/KW/ROADS/0001"
PAGE2 = "Period of work: 18 months including monsoon"


@pytest.fixture
def world(make_archive, conn):  # type: ignore[no-untyped-def]
    archive = make_archive()
    archive.add_file(FIXTURES / "tender-en.pdf", publisher="bmc", licence="test fixture")
    clock = {"now": T0}
    loader = Loader(conn, archive, archive.data, now=lambda: clock["now"])
    import_roads(archive, loader, FIXTURES / "roads-fixture.json", publisher="osm", licence="test", batch_id="roads")
    geo.build(conn)

    def load(records: list[dict[str, Any]], batch: str, at: datetime) -> None:
        clock["now"] = at
        report = loader.load(records, batch_id=batch, extractor="test@1")
        assert report.held == {}, report.held

    return conn, loader, load


def tender(link_confidence: float = 0.9) -> list[dict[str, Any]]:
    link = edge("IMPROVES", "work:kw-roads-1", SV, HEAD)
    link["confidence"] = link_confidence
    return [
        node("work:kw-roads-1", "Work", HEAD, title="Concretisation of S. V. Road", due_on="2026-05-31"),
        node("tender:kw-roads-1", "Tender", REF, ref_no="TEST/KW/ROADS/0001", estimated_cost=42000000),
        edge("FOR_WORK", "tender:kw-roads-1", "work:kw-roads-1", REF),
        link,
    ]


def outbox(conn) -> list[tuple[int, str]]:  # type: ignore[no-untyped-def]
    rows = conn.execute("SELECT subscription_id, event_key FROM alerts.outbox ORDER BY id").fetchall()
    conn.commit()
    return [(r[0], r[1]) for r in rows]


# AC1 · R1 -------------------------------------------------------------------------------------------------------


def test_spec010_ac1_a_point_with_a_radius_is_saved_and_bad_radii_are_rejected(world) -> None:  # type: ignore[no-untyped-def]
    conn, _, _ = world
    saved = alerts.save_point(conn, "acct_lata", *NEAR_SV, 300, "mr")
    assert (saved.kind, saved.radius_m, saved.language) == ("point", 300, "mr")
    assert round(saved.lat, 4) == 19.11 and alerts.list_subscriptions(conn, "acct_lata") == [saved]
    for radius in (50, 2000):
        with pytest.raises(ValueError, match="between 100 and 1000"):
            alerts.save_point(conn, "acct_lata", *NEAR_SV, radius, "mr")
    roads = alerts.save_roads(conn, "acct_imran", [SV], "en")
    assert roads.road_ids == [SV]
    with pytest.raises(ValueError, match="not a road we know"):
        alerts.save_roads(conn, "acct_imran", ["road:made-up"], "en")
    assert not alerts.unsubscribe(conn, "acct_imran", saved.id)  # someone else's
    assert alerts.unsubscribe(conn, "acct_lata", saved.id)


# AC2 · R2 -------------------------------------------------------------------------------------------------------


def test_spec010_ac2_a_new_tender_in_a_saved_area_queues_one_alert_each(world) -> None:  # type: ignore[no-untyped-def]
    conn, loader, load = world
    near = alerts.save_point(conn, "acct_lata", *NEAR_SV, 300, "mr", now=T0)
    named = alerts.save_roads(conn, "acct_imran", [SV], "en", now=T0)
    alerts.save_point(conn, "acct_far", 19.20, 72.90, 300, "en", now=T0)  # kilometres away
    late = alerts.save_point(conn, "acct_late", *NEAR_SV, 300, "en", now=T0 + timedelta(days=2))  # saved afterwards
    load(tender(), "tender-1", T0 + timedelta(days=1))

    assert alerts.evaluate(conn, loader) == 2
    assert outbox(conn) == [
        (near.id, f"{near.id}:tender:kw-roads-1:tender_published"),
        (named.id, f"{named.id}:tender:kw-roads-1:tender_published"),
    ]
    assert alerts.list_alerts(conn, "acct_late") == [] and late.id  # not sent the street's history

    # an award and a corrigendum later are their own events
    load(
        [
            node("award:sc-0003", "Award", HEAD, value=9840000, awarded_on="2026-11-05"),
            edge("OF", "award:sc-0003", "tender:kw-roads-1", HEAD),
            node(
                "corrigendum:kw-1", "Corrigendum", REF, ref_no="TEST/KW/ROADS/0001/C1", changed_field="bid closing date"
            ),
            edge("AMENDS", "corrigendum:kw-1", "tender:kw-roads-1", REF),
        ],
        "award-1",
        T0 + timedelta(days=3),
    )
    assert alerts.evaluate(conn, loader) == 6  # three subscribers near the road now, two events each
    kinds = sorted(a["kind"] for a in alerts.list_alerts(conn, "acct_lata"))
    assert kinds == ["awarded", "corrigendum", "tender_published"]


# AC3 · R3, R5 ---------------------------------------------------------------------------------------------------


def test_spec010_ac3_an_overdue_work_is_alerted_once(world) -> None:  # type: ignore[no-untyped-def]
    conn, loader, load = world
    alerts.save_point(conn, "acct_lata", *NEAR_SV, 300, "en", now=T0)
    load(
        [
            node("work:w1", "Work", HEAD, title="Resurfacing", due_on="2026-11-15"),
            edge("IMPROVES", "work:w1", SV, HEAD),
            node("work:done", "Work", HEAD, title="Footpath", due_on="2026-10-01", completed_on="2026-09-30"),
            edge("IMPROVES", "work:done", SV, HEAD),
        ],
        "works",
        T0 + timedelta(days=1),
    )
    assert alerts.evaluate_overdue(conn, loader, today=date(2026, 11, 15)) == 0  # due today is not yet overdue
    assert alerts.evaluate_overdue(conn, loader, today=date(2026, 11, 16)) == 1
    assert alerts.evaluate_overdue(conn, loader, today=date(2026, 11, 17)) == 0  # the daily check again
    [alert] = alerts.list_alerts(conn, "acct_lata")
    assert alert["kind"] == "overdue" and "Was due on: 2026-11-15" in alert["text"] and "Resurfacing" in alert["text"]

    # the date is extended and passes again: a new event
    load([node("work:w1", "Work", PAGE2, page=2, due_on="2026-12-31")], "extension", T0 + timedelta(days=20))
    assert alerts.evaluate_overdue(conn, loader, today=date(2026, 12, 20)) == 0
    assert alerts.evaluate_overdue(conn, loader, today=date(2027, 1, 1)) == 1


# AC4 · R4 -------------------------------------------------------------------------------------------------------


def test_spec010_ac4_an_alert_is_rendered_in_the_subscribers_language_with_number_date_and_source(world) -> None:  # type: ignore[no-untyped-def]
    conn, loader, load = world
    alerts.save_point(conn, "acct_lata", *NEAR_SV, 300, "mr", now=T0)
    alerts.save_roads(conn, "acct_h", [SV], "hi", now=T0)
    records = tender()
    records[1]["props"]["published_on"] = "2026-11-02"
    load(records, "tender-1", T0 + timedelta(days=1))
    alerts.evaluate(conn, loader)

    [marathi] = alerts.list_alerts(conn, "acct_lata", base_url="https://hishob.example")
    assert marathi["text"].splitlines() == [
        "एस. व्ही. रोड वरील कामासाठी निविदा प्रसिद्ध झाली आहे.",
        "निविदा क्र.: TEST/KW/ROADS/0001",
        "दिनांक: 2026-11-02",
        f"स्रोत: https://hishob.example/sources/{EN}/pages/1",
    ]
    [hindi] = alerts.list_alerts(conn, "acct_h")
    assert hindi["text"].startswith("S. V. Road पर काम के लिए निविदा प्रकाशित हुई है।")
    # C7: nothing about the subscriber is in the payload
    assert "acct_lata" not in str(marathi["payload"])


# AC5 · R5 -------------------------------------------------------------------------------------------------------


def test_spec010_ac5_replaying_the_same_facts_queues_no_duplicates(world) -> None:  # type: ignore[no-untyped-def]
    conn, loader, load = world
    alerts.save_point(conn, "acct_lata", *NEAR_SV, 300, "en", now=T0)
    load(tender(), "tender-1", T0 + timedelta(days=1))
    assert alerts.evaluate(conn, loader) == 1
    assert alerts.evaluate(conn, loader) == 0
    loader.rebuild_index()  # the ledger index rebuilt from its files, as a projector replay would
    assert alerts.evaluate(conn, loader) == 0
    # a later fact about the same tender (a corrected cost) is not a second "published" alert
    load([node("tender:kw-roads-1", "Tender", PAGE2, page=2, estimated_cost=43000000)], "fix", T0 + timedelta(days=5))
    assert alerts.evaluate(conn, loader) == 0 and len(outbox(conn)) == 1


# AC6 · R6 -------------------------------------------------------------------------------------------------------


def test_spec010_ac6_a_weak_location_match_shows_the_title_so_the_resident_can_judge(world) -> None:  # type: ignore[no-untyped-def]
    conn, loader, load = world
    alerts.save_point(conn, "acct_lata", *NEAR_SV, 300, "en", now=T0)
    load(tender(link_confidence=0.5), "tender-1", T0 + timedelta(days=1))
    alerts.evaluate(conn, loader)
    [alert] = alerts.list_alerts(conn, "acct_lata")
    assert alert["payload"]["low_confidence"] is True
    assert "Work: Concretisation of S. V. Road" in alert["text"] and "may be wrong" in alert["text"]


def test_spec010_a_confident_match_does_not_carry_the_warning(world) -> None:  # type: ignore[no-untyped-def]
    conn, loader, load = world
    alerts.save_point(conn, "acct_lata", *NEAR_SV, 300, "en", now=T0)
    load(tender(), "tender-1", T0 + timedelta(days=1))
    alerts.evaluate(conn, loader)
    assert "may be wrong" not in alerts.list_alerts(conn, "acct_lata")[0]["text"]


# The API over the same functions ----------------------------------------------------------------------------------


def test_spec010_ac1_the_api_saves_areas_for_signed_in_contributors_only(world, graph_driver) -> None:  # type: ignore[no-untyped-def]
    from contextlib import contextmanager

    from fastapi.testclient import TestClient

    from hishob.api.app import ApiConfig, create_app
    from hishob.api.tiers import sign

    conn, loader, load = world

    @contextmanager
    def connect():  # type: ignore[no-untyped-def]
        yield conn

    config = ApiConfig(
        connect=connect,
        sources=loader.archive.sources,
        data=loader.data,
        graph_driver=graph_driver,
        token_secret="s",
        public_per_minute=1000,
    )
    client = TestClient(create_app(config))
    area = {"kind": "point", "lat": NEAR_SV[0], "lon": NEAR_SV[1], "radius_m": 300, "language": "mr"}
    assert client.post("/subscriptions", json=area).status_code == 401  # not signed in
    lata = {"Authorization": "Bearer " + sign("contributor", "acct_lata", "s")}
    other = {"Authorization": "Bearer " + sign("contributor", "acct_other", "s")}
    saved = client.post("/subscriptions", json=area, headers=lata)
    assert saved.status_code == 201 and "account_id" not in saved.json()
    assert client.post("/subscriptions", json={**area, "radius_m": 50}, headers=lata).status_code == 422
    assert client.post("/subscriptions", json={**area, "radius_m": 2000}, headers=lata).status_code == 422
    assert len(client.get("/subscriptions", headers=lata).json()) == 1
    assert client.get("/subscriptions", headers=other).json() == []

    load(tender(), "tender-1", datetime.now(UTC) + timedelta(minutes=1))
    alerts.evaluate(conn, loader)
    [alert] = client.get("/alerts", headers=lata).json()
    assert "निविदा क्र.: TEST/KW/ROADS/0001" in alert["text"] and "http://testserver/sources/" in alert["text"]
    assert client.get("/alerts", headers=other).json() == []
    assert client.delete(f"/subscriptions/{saved.json()['id']}", headers=other).status_code == 404
    assert client.delete(f"/subscriptions/{saved.json()['id']}", headers=lata).status_code == 204
    assert client.get("/alerts", headers=lata).json() == []  # its alerts go with it
