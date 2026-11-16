"""Acceptance tests for SPEC-002: ontology, shapes and generated schema."""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest
from rdflib import OWL, RDF, RDFS, Literal

from hishob import cli
from hishob.schema import build
from hishob.schema.model import MCO, ONTOLOGY_DIR, load_graph, read_version
from hishob.schema.validate import json_problems, shacl_problems
from hishob.schema.whitelist import check_edge, check_node

SHA = "a" * 64


def tender(**overrides: object) -> dict[str, object]:
    record: dict[str, object] = {
        "kind": "node",
        "id": "tender:2026_MCGM_1303610_1",
        "label": "Tender",
        "props": {
            "ref_no": "TEST/KW/ROADS/0001",
            "estimated_cost": 42000000,
            "published_on": "2026-08-11",
            "closes_on": "2026-08-25",
        },
        "source": SHA,
        "page": 1,
        "quote": "Tender Ref. No. TEST/KW/ROADS/0001",
        "tier": "official",
        "confidence": 0.9,
    }
    record.update(overrides)
    return record


# AC1 · R1, R2 ---------------------------------------------------------------------------------------------------


def test_spec002_ac1_every_class_and_property_has_english_and_marathi_labels() -> None:
    graph = load_graph()
    missing = []
    for kind in (OWL.Class, OWL.ObjectProperty, OWL.DatatypeProperty):
        for subject in graph.subjects(RDF.type, kind):
            if not str(subject).startswith(str(MCO)):
                continue
            langs = {lit.language for lit in graph.objects(subject, RDFS.label) if isinstance(lit, Literal)}
            if not {"en", "mr"} <= langs:
                missing.append(str(subject).rsplit("#", 1)[-1])
    assert missing == []


@pytest.mark.parametrize(
    ("cls", "counterpart"),
    [
        ("Tender", "https://standard.open-contracting.org/latest/en/schema/reference/#tender"),
        ("Award", "https://standard.open-contracting.org/latest/en/schema/reference/#award"),
        ("Contract", "https://standard.open-contracting.org/latest/en/schema/reference/#contract"),
        ("Agency", "http://www.w3.org/ns/org#Organization"),
        ("Department", "http://www.w3.org/ns/org#OrganizationalUnit"),
        ("Post", "http://www.w3.org/ns/org#Post"),
        ("SourceDocument", "http://www.w3.org/ns/prov#Entity"),
        ("BudgetHead", "http://www.w3.org/2004/02/skos/core#Concept"),
        ("FiscalYear", "http://www.w3.org/2006/time#Interval"),
        ("AdminWard", "http://www.opengis.net/ont/geosparql#Feature"),
        ("Asset", "http://www.opengis.net/ont/geosparql#Feature"),
    ],
)
def test_spec002_ac1_classes_declare_their_standard_counterparts(cls: str, counterpart: str) -> None:
    from hishob.schema.model import default_model

    assert counterpart in default_model().classes[cls].matches


# AC2, AC3 · R3 --------------------------------------------------------------------------------------------------


def test_spec002_ac2_a_complete_tender_conforms() -> None:
    record = tender()
    assert json_problems(record) == []
    assert shacl_problems(record) == []


def test_spec002_ac3_a_tender_without_a_quote_fails_naming_quote() -> None:
    record = tender()
    del record["quote"]
    shapes = shacl_problems(record)
    assert shapes and all("quote" in p for p in shapes)
    assert any("quote" in p for p in json_problems(record))


def test_spec002_ac3_shapes_check_values_and_date_order() -> None:
    late = tender(props={"published_on": "2026-08-25", "closes_on": "2026-08-11"})
    assert any("close before it is published" in p for p in shacl_problems(late))
    assert any("tier" in p for p in shacl_problems(tender(tier="rumour")))
    assert any("confidence" in p for p in shacl_problems(tender(confidence=1.5)))
    dlp = {
        "kind": "node",
        "id": "dlp:w1",
        "label": "DefectLiabilityPeriod",
        "source": SHA,
        "page": 2,
        "quote": "Defect liability period: 5 years",
        "tier": "official",
        "confidence": 0.8,
        "props": {"from_date": "2031-01-01", "to_date": "2026-01-01"},
    }
    assert any("end before it starts" in p for p in shacl_problems(dlp))


def test_spec002_ac3_edges_need_provenance_too() -> None:
    edge = {
        "kind": "edge",
        "type": "FOR_WORK",
        "from": "tender:x",
        "to": "work:y",
        "source": SHA,
        "page": 1,
        "tier": "official",
        "confidence": 0.7,
    }
    assert any("quote" in p for p in shacl_problems(edge))


# AC4 · R4, R5 ---------------------------------------------------------------------------------------------------


def test_spec002_ac4_build_produces_three_artefacts_stamped_with_the_version() -> None:
    files = build.generate()
    version = read_version()
    assert set(files) == {"src/hishob/schema/records.json", "src/hishob/schema/whitelist.json", "ontology/REFERENCE.md"}
    assert all(version in content for content in files.values())


def test_spec002_ac4_generation_is_deterministic() -> None:
    assert build.generate() == build.generate()


# AC5 · R4 -------------------------------------------------------------------------------------------------------


def test_spec002_ac5_an_edge_from_the_wrong_class_is_rejected() -> None:
    [problem] = check_edge("FOR_WORK", "Contractor", "Work")
    assert problem.startswith("domain_range") and "Tender" in problem and "Contract" in problem
    assert check_edge("FOR_WORK", "Tender", "Work") == []
    assert check_edge("IMPROVES", "Work", "Road") == []  # Road inherits from Asset
    assert check_edge("TELEPORTS", "Work", "Road") == ["unknown_edge: TELEPORTS"]


def test_spec002_ac5_properties_are_checked_by_label_and_type() -> None:
    assert check_node("Tender", {"estimated_cost": 4200, "published_on": "2026-08-11"}) == []
    assert check_node("Tender", {"estimated_cost": "4.2 crore"}) == [
        "wrong_type: Tender.estimated_cost must be integer"
    ]
    assert check_node("Tender", {"colour": "blue"}) == ["unknown_property: Tender.colour"]
    assert check_node("Spaceship", {}) == ["unknown_label: Spaceship"]


# AC6 · R6 -------------------------------------------------------------------------------------------------------


def test_spec002_ac6_committed_artefacts_are_up_to_date() -> None:
    assert build.stale(build.generate()) == []
    assert cli.main(["ontology", "build", "--check"]) == 0


def test_spec002_ac6_editing_the_ontology_without_regenerating_is_caught(tmp_path: Path) -> None:
    edited = tmp_path / "ontology"
    shutil.copytree(ONTOLOGY_DIR, edited)
    with (edited / "mco-works.ttl").open("a", encoding="utf-8") as handle:
        handle.write(
            '\nmco:Footpath a owl:Class ; mco:module "works" ; rdfs:subClassOf mco:Asset ;\n'
            '    rdfs:label "Footpath"@en , "पदपथ"@mr .\n'
        )
    assert set(build.stale(build.generate(edited))) == {
        "src/hishob/schema/records.json",
        "src/hishob/schema/whitelist.json",
        "ontology/REFERENCE.md",
    }


def test_spec002_ac6_version_mismatch_is_an_error(tmp_path: Path) -> None:
    edited = tmp_path / "ontology"
    shutil.copytree(ONTOLOGY_DIR, edited)
    (edited / "VERSION").write_text("9.9.9\n", encoding="utf-8")
    with pytest.raises(build.OntologyError):
        build.generate(edited)
