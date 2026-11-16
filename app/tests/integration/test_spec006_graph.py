"""Acceptance tests for SPEC-006: graph projection and named views. Needs Postgres and a test graph database."""

from __future__ import annotations

import hashlib
from datetime import date
from typing import Any

import pytest

from hishob.archive import Archive
from hishob.graphstore import GraphStore, Views
from hishob.ledger import Loader
from tests.conftest import FIXED_NOW, FIXTURES

pytestmark = [pytest.mark.integration, pytest.mark.graph]

EN = hashlib.sha256((FIXTURES / "tender-en.pdf").read_bytes()).hexdigest()
AWARD = hashlib.sha256((FIXTURES / "award-notice.pdf").read_bytes()).hexdigest()
TODAY = date(2026, 11, 16)


def node(node_id: str, label: str, quote: str, source: str = EN, page: int = 1, **props: Any) -> dict[str, Any]:
    return {
        "kind": "node",
        "id": node_id,
        "label": label,
        "props": props,
        "source": source,
        "page": page,
        "quote": quote,
        "tier": "official",
        "confidence": 0.9,
    }


def edge(kind: str, start: str, end: str, quote: str, source: str = EN, page: int = 1) -> dict[str, Any]:
    return {
        "kind": "edge",
        "type": kind,
        "from": start,
        "to": end,
        "source": source,
        "page": page,
        "quote": quote,
        "tier": "official",
        "confidence": 0.8,
    }


HEAD = "Roads and Traffic Department, K/West Ward"
REF = "Tender Ref. No. TEST/KW/ROADS/0001"
RESOLUTION = "Standing Committee resolution TEST/SC/0003"
SCENARIO = [
    node("adminward:k-w", "AdminWard", HEAD, code="K/W", name="K/W"),
    node("road:sv", "Road", HEAD, name="S. V. Road"),
    node("road:unloved", "Road", HEAD, name="Lane with no records"),
    node("agency:bmc", "Agency", "Brihanmumbai Municipal Corporation", name="Brihanmumbai Municipal Corporation"),
    node("department:roads", "Department", HEAD, name="Roads and Traffic Department"),
    node("issuetype:pothole", "IssueType", HEAD, code="pothole", name="Pothole"),
    node("post:ae-roads-kw", "Post", HEAD, title="Assistant Engineer (Roads), K/West"),
    node("post:ee-roads-ws", "Post", HEAD, title="Executive Engineer (Roads), Western Suburbs"),
    node("work:kw-roads-1", "Work", HEAD, title="Concretisation of S. V. Road", due_on="2026-05-31"),
    node("tender:kw-roads-1", "Tender", REF, ref_no="TEST/KW/ROADS/0001", estimated_cost=42000000),
    node("award:sc-0003", "Award", RESOLUTION, source=AWARD, value=9840000),
    node(
        "contractor:shree-ganesh",
        "Contractor",
        "M/s Shree Ganesh Infra Pvt. Ltd. at Rs. 98,40,000.",
        source=AWARD,
        name="M/s Shree Ganesh Infra Pvt. Ltd.",
    ),
    node("contract:kw-roads-1", "Contract", RESOLUTION, source=AWARD, value=9840000),
    node(
        "dlp:kw-roads-1",
        "DefectLiabilityPeriod",
        "Defect liability period: 5 years from completion",
        page=2,
        from_date="2026-06-01",
        to_date="2031-05-31",
    ),
    node(
        "payment:mob-advance",
        "Payment",
        "Mobilisation advance released to Shree Ganesh Infrastructure",
        source=AWARD,
        page=2,
        paid_on="2026-09-12",
    ),
    edge("LOCATED_IN", "road:sv", "adminward:k-w", HEAD),
    edge("OWNS", "agency:bmc", "road:sv", "Brihanmumbai Municipal Corporation"),
    edge("PART_OF", "department:roads", "agency:bmc", HEAD),
    edge("HANDLED_BY", "issuetype:pothole", "department:roads", HEAD),
    edge("IN", "post:ae-roads-kw", "department:roads", HEAD),
    edge("COVERS", "post:ae-roads-kw", "adminward:k-w", HEAD),
    edge("REPORTS_TO", "post:ae-roads-kw", "post:ee-roads-ws", HEAD),
    edge("IMPROVES", "work:kw-roads-1", "road:sv", HEAD),
    edge("FOR_WORK", "tender:kw-roads-1", "work:kw-roads-1", REF),
    edge("OF", "award:sc-0003", "tender:kw-roads-1", RESOLUTION, source=AWARD),
    edge("TO", "award:sc-0003", "contractor:shree-ganesh", RESOLUTION, source=AWARD),
    edge("FROM_AWARD", "contract:kw-roads-1", "award:sc-0003", RESOLUTION, source=AWARD),
    edge("FOR_WORK", "contract:kw-roads-1", "work:kw-roads-1", RESOLUTION, source=AWARD),
    edge("PARTY_TO", "contractor:shree-ganesh", "contract:kw-roads-1", RESOLUTION, source=AWARD),
    edge("HAS_DLP", "work:kw-roads-1", "dlp:kw-roads-1", "Defect liability period: 5 years from completion", page=2),
    edge(
        "UNDER_CONTRACT",
        "payment:mob-advance",
        "contract:kw-roads-1",
        "Mobilisation advance released to Shree Ganesh Infrastructure",
        source=AWARD,
        page=2,
    ),
]


@pytest.fixture
def world(make_archive, conn, graph_driver):  # type: ignore[no-untyped-def]
    archive: Archive = make_archive()
    for name in ("tender-en.pdf", "award-notice.pdf"):
        archive.add_file(FIXTURES / name, publisher="bmc", licence="test fixture")
    loader = Loader(conn, archive, archive.data, now=lambda: FIXED_NOW)
    report = loader.load([dict(r) for r in SCENARIO], batch_id="world-1", extractor="test@1")
    assert report.held == {}, report.held
    store = GraphStore(graph_driver, conn, archive.data)
    return loader, store, Views(graph_driver, today=TODAY)


def hops(result: Any) -> list[str]:
    return [h["hop"] for h in result.rows[0]["hops"]]


# AC1 · R1 -------------------------------------------------------------------------------------------------------


def test_spec006_ac1_only_new_ledger_files_are_applied(world) -> None:  # type: ignore[no-untyped-def]
    loader, store, _ = world
    first = store.apply()
    assert first.files_applied >= 1 and first.facts_applied == len(SCENARIO)
    loader.load([node("road:new", "Road", HEAD, name="New Road")], batch_id="world-2", extractor="test@1")
    second = store.apply()
    assert second.facts_applied == len(SCENARIO) + 1
    assert store.apply() == second  # nothing new: nothing applied


# AC2 · R2 -------------------------------------------------------------------------------------------------------


def test_spec006_ac2_drop_and_rebuild_gives_the_same_graph(world) -> None:  # type: ignore[no-untyped-def]
    _, store, _ = world
    store.apply()
    before = store.fingerprint()
    assert store.rebuild() == before
    assert before.nodes == 15 and before.relationships == 16 and before.facts == 15


# AC3 · R3 -------------------------------------------------------------------------------------------------------


def test_spec006_ac3_a_superseded_due_date_is_history_not_current(world) -> None:  # type: ignore[no-untyped-def]
    loader, store, views = world
    store.apply()
    revised = node(
        "work:kw-roads-1", "Work", "Period of work: 18 months including monsoon", page=2, due_on="2026-12-31"
    )
    assert loader.load([revised], batch_id="world-rev", extractor="test@1").superseded == 1
    store.apply()
    status = views.work_status("work:kw-roads-1").rows
    assert status[0]["node"]["due_on"] == "2026-12-31"
    history = status[1]["items"]
    assert [h["due_on"] for h in history] == ["2026-05-31", "2026-12-31"]
    assert history[1]["supersedes"] == [history[0]["fact_id"]]
    assert status[2]["overdue"] is False


# AC4 · R4 -------------------------------------------------------------------------------------------------------


def test_spec006_ac4_every_returned_node_carries_provenance(world) -> None:  # type: ignore[no-untyped-def]
    _, store, views = world
    store.apply()
    for result in (views.trace_money("road:sv"), views.who_is_responsible("road:sv", "pothole")):
        items = [h for r in result.rows for h in (r.get("hops") or [r])]
        nodes = [h.get("node") or h.get("work") for h in items if h.get("node") or h.get("work")]
        assert nodes
        for n in nodes:
            assert {"fact_id", "source", "page", "tier", "quote_check"} <= n.keys(), n
            assert all("fact_id" in p for p in n["provenance"].values())


# AC5 · R5 -------------------------------------------------------------------------------------------------------


def test_spec006_ac5_trace_money_from_a_road_returns_the_trail_in_order(world) -> None:  # type: ignore[no-untyped-def]
    _, store, views = world
    store.apply()
    result = views.trace_money("road:sv")
    assert hops(result) == ["work", "tender", "award", "contract", "contractor", "defect_liability", "payment"]
    trail = {h["hop"]: h["node"] for h in result.rows[0]["hops"]}
    assert trail["tender"]["estimated_cost"] == 42000000 and trail["tender"]["source"] == EN
    assert trail["contractor"]["source"] == AWARD and result.query_ms < 3000


def test_spec006_ac5_who_is_responsible_names_the_post_and_the_liable_contractor(world) -> None:  # type: ignore[no-untyped-def]
    _, store, views = world
    store.apply()
    rows = views.who_is_responsible("road:sv", "pothole").rows
    by_hop: dict[str, list[dict]] = {}
    for row in rows:
        by_hop.setdefault(row["hop"], []).append(row)
    assert by_hop["post"][0]["node"]["title"] == "Assistant Engineer (Roads), K/West"
    assert by_hop["escalation"][0]["node"]["title"] == "Executive Engineer (Roads), Western Suburbs"
    [liable] = by_hop["under_liability"]
    assert liable["period"]["to_date"] == "2031-05-31" and liable["contractor"]["id"] == "contractor:shree-ganesh"


def test_spec006_ac5_ward_summary(world) -> None:  # type: ignore[no-untyped-def]
    _, store, views = world
    store.apply()
    rows = views.ward_summary("K/W").rows
    assert rows[1]["counts"] == {"Road": 1}
    assert rows[2]["tendered_value"] == 42000000 and rows[2]["overdue"] == 1


# AC6 · R6 -------------------------------------------------------------------------------------------------------
# The same suite against Neptune runs in a nightly job once an instance exists (see the spec's change log).


def test_spec006_ac6_queries_avoid_vendor_procedures() -> None:
    import inspect

    from hishob.graphstore import store, views

    source = inspect.getsource(views) + inspect.getsource(store)
    for forbidden in ("apoc.", "gds.", "CALL db.", "CALL {"):
        assert forbidden not in source


# AC7 · R7 -------------------------------------------------------------------------------------------------------


def test_spec006_ac7_missing_hops_are_returned_as_gaps(world) -> None:  # type: ignore[no-untyped-def]
    _, store, views = world
    store.apply()
    gaps = views.trace_money("road:sv").gaps
    assert [g.hop.split(" ")[0] for g in gaps] == ["budget_head"]
    assert "Budget head" in gaps[0].record_needed and gaps[0].holder.startswith("BMC Chief Accountant")
    nothing = views.gaps_for("road:unloved")
    assert {g.hop.split(" ")[0] for g in nothing.gaps} >= {"ward", "owner"}
