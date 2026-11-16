"""Acceptance tests for SPEC-004: place spine. Fixtures are invented shapes inside the real K/West area."""

from __future__ import annotations

import pytest

from hishob.archive import Archive
from hishob.ledger import Loader
from hishob.place import geo
from hishob.place.importer import confirm_alias, import_roads, import_wards
from tests.conftest import FIXED_NOW, FIXTURES

pytestmark = pytest.mark.integration


@pytest.fixture
def spine(make_archive, conn):  # type: ignore[no-untyped-def]
    archive: Archive = make_archive()
    loader = Loader(conn, archive, archive.data, now=lambda: FIXED_NOW)
    wards = import_wards(
        archive,
        loader,
        FIXTURES / "wards-fixture.geojson",
        kind="admin",
        name_property="name",
        publisher="datameet",
        licence="test fixture",
        batch_id="geo-wards",
    )
    electoral = import_wards(
        archive,
        loader,
        FIXTURES / "electoral-fixture.geojson",
        kind="electoral",
        name_property="ward",
        publisher="sec",
        licence="test fixture",
        batch_id="geo-ewards",
    )
    roads = import_roads(
        archive,
        loader,
        FIXTURES / "roads-fixture.json",
        publisher="openstreetmap",
        licence="ODbL-1.0",
        batch_id="geo-roads",
    )
    counts = geo.build(conn)
    return archive, loader, conn, (wards, electoral, roads), counts


# AC1 · R1 -------------------------------------------------------------------------------------------------------


def test_spec004_ac1_counts_match_the_source_files(spine) -> None:  # type: ignore[no-untyped-def]
    _, _, _, (wards, electoral, roads), counts = spine
    assert (wards.features, wards.skipped) == (2, 1)  # the unnamed feature is skipped, not loaded
    assert (electoral.features, roads.features, roads.skipped) == (2, 4, 1)
    assert counts["admin_wards"] == 2 and counts["electoral_wards"] == 2 and counts["road_segments"] == 4
    for result in (wards, electoral, roads):
        assert result.report.held == {} and result.report.quote_check == {"matched": result.features}


def test_spec004_ac1_places_are_ledger_facts_citing_their_file(spine) -> None:  # type: ignore[no-untyped-def]
    archive, loader, _, (_, _, roads), _ = spine
    props = loader.current_properties("node|AdminWard|adminward:k-w")
    assert props["code"] == "K/W" and props["geometry_wkt"].startswith("MULTIPOLYGON")
    road = loader.current_properties("node|Road|road:osm-1001")
    assert road["name_mr"] == "एस. व्ही. रोड" and road["osm_way_id"] == "1001"
    assert archive.registry.get(roads.source_sha256).publisher == "openstreetmap"


def test_spec004_ac1_escaped_slashes_in_the_source_still_pass_the_quote_check(make_archive, conn) -> None:  # type: ignore[no-untyped-def]
    """Real finding: DataMeet's file writes "K\\/W". The quote must be the file's own spelling."""
    archive: Archive = make_archive()
    loader = Loader(conn, archive, archive.data, now=lambda: FIXED_NOW)
    result = import_wards(
        archive,
        loader,
        FIXTURES / "wards-escaped.geojson",
        kind="admin",
        name_property="name",
        publisher="datameet",
        licence="test fixture",
        batch_id="geo-escaped",
    )
    assert result.report.accepted == 2 and result.report.held == {}
    assert loader.current_properties("node|AdminWard|adminward:k-w")["code"] == "K/W"


# AC2 · R2, R3 ---------------------------------------------------------------------------------------------------


@pytest.mark.parametrize("query", ["SV road", "S.V. Road", "एस व्ही रोड", "एस. व्ही. रोड", "sv rd"])
def test_spec004_ac2_a_road_is_found_by_its_names_in_either_script(spine, query: str) -> None:  # type: ignore[no-untyped-def]
    _, _, conn, _, _ = spine
    [first, *_] = geo.find_place(conn, query, kinds={"Road"})
    assert first.name == "S. V. Road" and first.segments == 2


def test_spec004_ac2_marathi_query_finds_a_road_through_its_latin_key(spine) -> None:  # type: ignore[no-untyped-def]
    _, _, conn, _, _ = spine
    [first, *_] = geo.find_place(conn, "जुहू तारा रोड")
    assert first.name == "Juhu Tara Road"


def test_spec004_wards_are_found_by_code(spine) -> None:  # type: ignore[no-untyped-def]
    _, _, conn, _, _ = spine
    assert geo.find_place(conn, "K/W", kinds={"AdminWard"})[0].node_id == "adminward:k-w"


# AC3 · R4 -------------------------------------------------------------------------------------------------------


def test_spec004_ac3_a_point_near_a_road_resolves_road_and_wards(spine) -> None:  # type: ignore[no-untyped-def]
    _, _, conn, _, _ = spine
    result = geo.at_point(conn, 19.1200, 72.83577)  # about 10 m east of S. V. Road
    assert result.road is not None and result.road["name"] == "S. V. Road" and result.road["distance_m"] < 15
    assert result.admin_ward and result.admin_ward["code"] == "K/W"
    assert result.electoral_ward and result.electoral_ward["number"] == 64


def test_spec004_a_point_on_a_ward_boundary_still_gets_a_ward(spine) -> None:  # type: ignore[no-untyped-def]
    _, _, conn, _, _ = spine
    result = geo.at_point(conn, 19.1150, 72.8100)  # on the line between invented electoral wards 63 and 64
    assert result.electoral_ward is not None and result.electoral_ward["number"] in {63, 64}


# AC4 · R5 -------------------------------------------------------------------------------------------------------


def test_spec004_ac4_a_point_far_from_roads_returns_wards_and_a_reason(spine) -> None:  # type: ignore[no-untyped-def]
    _, _, conn, _, _ = spine
    result = geo.at_point(conn, 19.1450, 72.8050)
    assert result.road is None and "no road within 50 m" in result.note
    assert result.admin_ward and result.admin_ward["code"] == "K/W"


def test_spec004_points_outside_every_ward_say_so(spine) -> None:  # type: ignore[no-untyped-def]
    _, _, conn, _, _ = spine
    result = geo.at_point(conn, 18.9, 72.8)
    assert result.admin_ward is None and "outside every administrative ward" in result.note


# AC5 · R6 -------------------------------------------------------------------------------------------------------


def test_spec004_ac5_a_confirmed_alias_finds_the_place(spine) -> None:  # type: ignore[no-untyped-def]
    archive, loader, conn, _, _ = spine
    assert not [m for m in geo.find_place(conn, "Gulmohar Lane") if m.name == "Station Road"]
    report = confirm_alias(
        archive, loader, "road:osm-1003", "Gulmohar Lane", reviewer_account="acct_reviewer1", batch_id="alias-1"
    )
    assert report.accepted == 2 and report.held == {}
    geo.build(conn)
    [first, *_] = geo.find_place(conn, "Gulmohar Lane")
    assert first.node_id == "road:osm-1003" and first.matched == "Gulmohar Lane"


# Rebuild ---------------------------------------------------------------------------------------------------------


def test_spec004_geo_tables_rebuild_from_the_ledger(spine) -> None:  # type: ignore[no-untyped-def]
    _, _, conn, _, counts = spine
    conn.execute("TRUNCATE geo.admin_wards, geo.electoral_wards, geo.road_segments, geo.aliases")
    conn.commit()
    assert geo.build(conn) == counts
