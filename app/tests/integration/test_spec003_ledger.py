"""Acceptance tests for SPEC-003: facts ledger and loader."""

from __future__ import annotations

import hashlib
import json
from typing import Any

import pytest

from hishob.archive import Archive
from hishob.ledger import BatchAlreadyLoadedError, Loader
from tests.conftest import FIXED_NOW, FIXTURES

pytestmark = pytest.mark.integration

EN = hashlib.sha256((FIXTURES / "tender-en.pdf").read_bytes()).hexdigest()
MIXED = hashlib.sha256((FIXTURES / "tender-mixed.pdf").read_bytes()).hexdigest()


@pytest.fixture
def loader(make_archive, conn) -> Loader:
    archive: Archive = make_archive()
    archive.add_file(FIXTURES / "tender-en.pdf", publisher="bmc", licence="public")
    archive.add_file(FIXTURES / "tender-mixed.pdf", publisher="bmc", licence="public")
    return Loader(conn, archive, archive.data, now=lambda: FIXED_NOW)


def node(node_id: str, label: str, quote: str, *, source: str = EN, page: int = 1, **props: Any) -> dict[str, Any]:
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


def edge(kind: str, start: str, end: str, quote: str, *, source: str = EN, page: int = 1) -> dict[str, Any]:
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


TENDER = node(
    "tender:TEST-KW-ROADS-0001",
    "Tender",
    "Tender Ref. No. TEST/KW/ROADS/0001",
    ref_no="TEST/KW/ROADS/0001",
    estimated_cost=42000000,
)
WORK = node("work:kw-roads-0001", "Work", "Roads and Traffic Department, K/West Ward", title="Road works, K/West")


def load(loader: Loader, records: list[dict[str, Any]], batch: str) -> Any:
    return loader.load([dict(r) for r in records], batch_id=batch, extractor="doc-extractor@1")


def held_rows(loader: Loader, batch: str) -> list[dict[str, Any]]:
    key = f"staging/{batch}/held.jsonl"
    if not loader.data.exists(key):
        return []
    return [json.loads(line) for line in loader.data.get(key).decode("utf-8").splitlines()]


def ledger_rows(loader: Loader) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for key in loader.data.list("facts/")
        for line in loader.data.get(key).decode("utf-8").splitlines()
    ]


# AC1 · R1, R4 ---------------------------------------------------------------------------------------------------


def test_spec003_ac1_unknown_label_is_held_with_its_reason(loader: Loader) -> None:
    report = load(loader, [node("ufo:1", "Spaceship", "Brihanmumbai Municipal Corporation")], "b-ac1")
    assert report.accepted == 0 and report.held == {"unknown_label": 1}
    [row] = held_rows(loader, "b-ac1")
    assert row["reason"] == "unknown_label" and row["record"]["id"] == "ufo:1"


def test_spec003_ac1_schema_and_property_problems_are_held(loader: Loader) -> None:
    no_quote = dict(TENDER, quote="")
    bad_type = node("tender:x", "Tender", "Tender Ref. No. TEST/KW/ROADS/0001", estimated_cost="4.2 crore")
    unknown_prop = node("tender:y", "Tender", "Tender Ref. No. TEST/KW/ROADS/0001", colour="blue")
    report = load(loader, [no_quote, bad_type, unknown_prop], "b-ac1b")
    assert report.held == {"schema_invalid": 1, "wrong_type": 1, "unknown_property": 1}


# AC2, AC3, AC4 · R2, R3 -----------------------------------------------------------------------------------------


def test_spec003_ac2_quote_with_different_line_breaks_is_matched(loader: Loader) -> None:
    record = node("work:a", "Work", "Brihanmumbai Municipal Corporation Roads and Traffic Department")
    report = load(loader, [record], "b-ac2")
    assert report.accepted == 1 and report.quote_check == {"matched": 1}


def test_spec003_ac2_marathi_quote_is_matched(loader: Loader) -> None:
    record = node(
        "agency:bmc",
        "Agency",
        "बृहन्मुंबई महानगरपालिका",
        source=MIXED,
        name="बृहन्मुंबई महानगरपालिका",
        name_en="Brihanmumbai Municipal Corporation",
    )
    assert load(loader, [record], "b-ac2mr").quote_check == {"matched": 1}


def test_spec003_ac3_quote_not_on_its_page_is_held(loader: Loader) -> None:
    wrong_page = dict(TENDER, page=2)
    invented = node("work:b", "Work", "Completed on 1 January 2026")
    report = load(loader, [wrong_page, invented], "b-ac3")
    assert report.accepted == 0 and report.held == {"quote_not_found": 2}


def test_spec003_ac4_scanned_page_is_accepted_but_marked(loader: Loader) -> None:
    record = node("work:scan", "Work", "work order", source=MIXED, page=4)
    report = load(loader, [record], "b-ac4")
    assert report.accepted == 1 and report.quote_check == {"scan_unchecked": 1}
    [entry] = ledger_rows(loader)
    assert entry["quote_check"] == "scan_unchecked"


def test_spec003_source_and_page_must_exist(loader: Loader) -> None:
    report = load(loader, [dict(TENDER, page=9), dict(TENDER, source="b" * 64)], "b-src")
    assert report.held == {"page_out_of_range": 1, "unknown_source": 1}


# AC5 · R5 -------------------------------------------------------------------------------------------------------


def test_spec003_ac5_earlier_ledger_files_never_change(loader: Loader) -> None:
    load(loader, [TENDER, WORK], "b-first")
    before = {key: loader.data.get(key) for key in loader.data.list("facts/")}
    load(loader, [node("work:c", "Work", "Brihanmumbai Municipal Corporation")], "b-second")
    after = {key: loader.data.get(key) for key in before}
    assert before == after
    assert len(loader.data.list("facts/")) > len(before)


def test_spec003_ac5_a_batch_id_can_be_used_once(loader: Loader) -> None:
    load(loader, [TENDER], "b-once")
    with pytest.raises(BatchAlreadyLoadedError):
        load(loader, [WORK], "b-once")


# AC6 · R6 -------------------------------------------------------------------------------------------------------


def test_spec003_ac6_every_ledger_record_carries_full_provenance(loader: Loader) -> None:
    load(
        loader,
        [TENDER, WORK, edge("FOR_WORK", TENDER["id"], WORK["id"], "Tender Ref. No. TEST/KW/ROADS/0001")],
        "b-ac6",
    )
    required = {
        "fact_id",
        "kind",
        "source",
        "page",
        "quote",
        "tier",
        "confidence",
        "quote_check",
        "extractor",
        "ontology_version",
        "batch_id",
        "loaded_at",
        "supersedes",
        "props",
    }
    rows = ledger_rows(loader)
    assert len(rows) == 3
    for row in rows:
        assert required <= row.keys()
        assert ("label" in row and "id" in row) or ("type" in row and "from" in row and "to" in row)
        assert row["extractor"] == "doc-extractor@1" and row["ontology_version"] == "0.1.0"


# AC7 · R7 -------------------------------------------------------------------------------------------------------


def test_spec003_ac7_a_changed_property_supersedes_only_what_it_changes(loader: Loader) -> None:
    load(loader, [TENDER], "b-v1")
    [first] = ledger_rows(loader)
    revised = node(TENDER["id"], "Tender", "Estimated cost: Rs. 4,20,00,000", estimated_cost=45000000)
    report = load(loader, [revised], "b-v2")
    assert report.superseded == 1
    second = next(r for r in ledger_rows(loader) if r["batch_id"] == "b-v2")
    assert second["supersedes"] == [first["fact_id"]] and second["holds"] == ["estimated_cost"]
    identity = f"node|Tender|{TENDER['id']}"
    held = dict(
        loader.conn.execute("SELECT key, fact_id FROM ledger.current_props WHERE identity = %s", (identity,)).fetchall()
    )
    assert held == {"estimated_cost": second["fact_id"], "ref_no": first["fact_id"]}
    assert loader.current_properties(identity) == {"estimated_cost": 45000000, "ref_no": "TEST/KW/ROADS/0001"}


def test_spec003_ac7_records_split_by_quote_build_up_one_node(loader: Loader) -> None:
    """What the first live intake run produced: one tender as two records, one quote each."""
    part1 = node("tender:split", "Tender", "Tender Ref. No. TEST/KW/ROADS/0001", ref_no="TEST/KW/ROADS/0001")
    part2 = node("tender:split", "Tender", "Estimated cost: Rs. 4,20,00,000", estimated_cost=42000000)
    report = load(loader, [part1, part2], "b-split")
    assert report.accepted == 2 and report.extended == 1 and report.superseded == 0
    assert loader.current_properties("node|Tender|tender:split") == {
        "ref_no": "TEST/KW/ROADS/0001",
        "estimated_cost": 42000000,
    }


def test_spec003_ac7_replays_are_unchanged_and_corroboration_keeps_the_current_fact(loader: Loader) -> None:
    load(loader, [TENDER], "b-r1")
    [first] = ledger_rows(loader)
    assert load(loader, [TENDER], "b-r2").unchanged == 1
    other_source = node(TENDER["id"], "Tender", "Tender Ref. No. TEST/KW/SWD/0002", source=MIXED, **TENDER["props"])
    report = load(loader, [other_source], "b-r3")
    assert report.corroborating == 1 and report.superseded == 0
    current = loader.conn.execute("SELECT fact_id FROM ledger.current WHERE node_id = %s", (TENDER["id"],)).fetchone()
    assert current == (first["fact_id"],)


# AC8 · R8 -------------------------------------------------------------------------------------------------------


def test_spec003_ac8_edge_to_an_unknown_node_is_held(loader: Loader) -> None:
    dangling = edge("FOR_WORK", TENDER["id"], "work:missing", "Tender Ref. No. TEST/KW/ROADS/0001")
    report = load(loader, [TENDER, dangling], "b-ac8")
    assert report.accepted == 1 and report.held == {"dangling_endpoint": 1}


def test_spec003_ac8_edge_endpoints_may_come_from_the_ledger(loader: Loader) -> None:
    load(loader, [TENDER, WORK], "b-nodes")
    linked = edge("FOR_WORK", TENDER["id"], WORK["id"], "Tender Ref. No. TEST/KW/ROADS/0001")
    assert load(loader, [linked], "b-edges").accepted == 1


def test_spec003_edges_must_join_the_right_classes(loader: Loader) -> None:
    road = node("road:sv", "Road", "Roads and Traffic Department, K/West Ward", name="S.V. Road")
    wrong = edge("FOR_WORK", road["id"], WORK["id"], "Roads and Traffic Department, K/West Ward")
    report = load(loader, [road, WORK, wrong], "b-domain")
    assert report.held == {"domain_range": 1}


def test_spec003_a_node_id_keeps_one_label(loader: Loader) -> None:
    load(loader, [WORK], "b-label1")
    same_id = node(WORK["id"], "Road", "Roads and Traffic Department, K/West Ward")
    assert load(loader, [same_id], "b-label2").held == {"label_conflict": 1}


# AC9 · R9 -------------------------------------------------------------------------------------------------------


def test_spec003_ac9_batch_report_counts(loader: Loader) -> None:
    good = [node(f"work:w{i}", "Work", "Brihanmumbai Municipal Corporation", title=f"Work {i}") for i in range(93)]
    bad_quotes = [node(f"work:q{i}", "Work", "This sentence is not in the document") for i in range(5)]
    unknown = [node(f"ufo:{i}", "Spaceship", "Brihanmumbai Municipal Corporation") for i in range(2)]
    report = load(loader, good + bad_quotes + unknown, "b-ac9")
    assert report.accepted == 93
    assert report.held == {"quote_not_found": 5, "unknown_label": 2}
    stored = json.loads(loader.data.get("staging/b-ac9/report.json"))
    assert stored["accepted"] == 93 and stored["held_total"] == 7


# Notes and rebuild ----------------------------------------------------------------------------------------------


def test_spec003_notes_go_to_people_not_the_ledger(loader: Loader) -> None:
    note = {"kind": "note", "text": "A stamp on page 2 may change the date.", "source": EN, "page": 2}
    report = load(loader, [note], "b-note")
    assert report.notes == 1 and report.accepted == 0 and ledger_rows(loader) == []
    assert loader.data.exists("staging/b-note/notes.jsonl")


def test_spec003_index_can_be_rebuilt_from_the_ledger_alone(loader: Loader) -> None:
    load(loader, [TENDER, WORK], "b-x1")
    load(loader, [dict(TENDER, props={**TENDER["props"], "estimated_cost": 1})], "b-x2")
    query = (
        "SELECT c.identity, c.fact_id, p.key, p.fact_id FROM ledger.current c"
        " LEFT JOIN ledger.current_props p USING (identity) ORDER BY 1, 3"
    )
    snapshot = loader.conn.execute(query).fetchall()
    loader.conn.commit()
    assert loader.rebuild_index() == 3
    assert loader.conn.execute(query).fetchall() == snapshot
