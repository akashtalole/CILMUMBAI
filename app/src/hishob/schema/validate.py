"""Validate extracted records with the JSON Schema and the SHACL shapes (SPEC-002/R3)."""

from __future__ import annotations

import json
from decimal import Decimal, InvalidOperation
from functools import cache
from pathlib import Path
from typing import Any
from urllib.parse import quote

from jsonschema import Draft202012Validator
from pyshacl import validate as shacl_validate
from rdflib import RDF, XSD, BNode, Graph, Literal, URIRef
from rdflib.namespace import SH

from hishob.schema.model import DATA, MCO, default_model, load_graph, load_shapes

RECORDS_SCHEMA = Path(__file__).with_name("records.json")
_XSD = {"string": XSD.string, "integer": XSD.integer, "number": XSD.decimal, "date": XSD.date, "boolean": XSD.boolean}


@cache
def _json_validator() -> Draft202012Validator:
    return Draft202012Validator(json.loads(RECORDS_SCHEMA.read_text(encoding="utf-8")))


@cache
def _graphs() -> tuple[Graph, Graph]:
    return load_graph(), load_shapes()


def json_problems(record: dict[str, Any]) -> list[str]:
    """Problems against the generated JSON Schema, one line each."""
    errors = sorted(_json_validator().iter_errors(record), key=lambda e: list(e.path))
    if not errors:
        return []
    best = min(errors, key=lambda e: len(e.context or []))
    leaves = [c for c in (best.context or [])] or [best]
    return sorted({f"schema_invalid: {'/'.join(map(str, e.path)) or '(record)'}: {e.message}" for e in leaves})


def _literal(value: object, kind: str) -> Literal:
    """Plain literals for strings (as SHACL sh:in compares them); exact decimals for numbers."""
    if kind == "string":
        return Literal(str(value))
    if kind in {"number", "decimal"} and isinstance(value, int | float) and not isinstance(value, bool):
        try:
            return Literal(Decimal(str(value)), datatype=XSD.decimal)
        except InvalidOperation:
            return Literal(str(value), datatype=XSD.decimal)
    return Literal(value, datatype=_XSD[kind])


def node_iri(node_id: str) -> URIRef:
    return URIRef(str(DATA) + quote(node_id, safe=":_-."))


def to_graph(record: dict[str, Any], subject: URIRef | None = None) -> Graph:
    """Express one record as RDF for SHACL validation. Unknown props are skipped (the whitelist reports them).

    `subject` overrides the node's IRI, so that a batch can give every record its own subject.
    """
    model = default_model()
    graph = Graph()
    if record.get("kind") == "node":
        subject = subject or node_iri(str(record.get("id", "")))
        graph.add((subject, RDF.type, MCO[str(record.get("label", "Node"))]))
        allowed = model.properties_for(str(record.get("label", "")))
        for key, value in (record.get("props") or {}).items():
            if key in allowed and key in model.properties:
                graph.add((subject, URIRef(model.properties[key].iri), _literal(value, allowed[key])))
    else:
        subject = subject or URIRef(str(DATA) + "_edge/" + str(BNode()))
        graph.add((subject, RDF.type, MCO.EdgeAssertion))
        if "type" in record:
            graph.add((subject, MCO.edgeTypeValue, Literal(record["type"])))
        if "from" in record:
            graph.add((subject, MCO.edgeSubject, node_iri(record["from"])))
        if "to" in record:
            graph.add((subject, MCO.edgeObject, node_iri(record["to"])))
    for key, kind in (
        ("source", "string"),
        ("page", "integer"),
        ("quote", "string"),
        ("tier", "string"),
        ("confidence", "number"),
    ):
        if key in record:
            graph.add((subject, MCO[key], _literal(record[key], kind)))
    return graph


def shacl_problems(record: dict[str, Any]) -> list[str]:
    """Problems against the SHACL shapes, naming the record field at fault."""
    if record.get("kind") == "note":
        return []
    return shacl_problems_batch([record]).get(0, [])


def shacl_problems_batch(records: list[dict[str, Any]]) -> dict[int, list[str]]:
    """Validate many records in one SHACL run. Returns {record index: problems} for records with problems."""
    graph = Graph()
    owners: dict[URIRef, int] = {}
    for index, record in enumerate(records):
        if record.get("kind") == "note":
            continue
        subject = URIRef(f"{DATA}_record/{index}")
        owners[subject] = index
        graph += to_graph(record, subject)
    if not owners:
        return {}
    ontology, shapes = _graphs()
    conforms, report, _ = shacl_validate(graph, shacl_graph=shapes, ont_graph=ontology, inference="none")
    if conforms:
        return {}
    model = default_model()
    keys = {URIRef(p.iri): p.key for p in model.properties.values()}
    keys.update({MCO[k]: k for k in ("source", "page", "quote", "tier", "confidence")})
    found: dict[int, set[str]] = {}
    for result in report.subjects(RDF.type, SH.ValidationResult):
        focus = report.value(result, SH.focusNode)
        if focus not in owners:
            continue
        path = report.value(result, SH.resultPath)
        field = keys.get(path, str(path).rsplit("#", 1)[-1]) if isinstance(path, URIRef) else "(record)"
        found.setdefault(owners[focus], set()).add(
            f"shape_violation: {field}: {report.value(result, SH.resultMessage)}"
        )
    return {index: sorted(problems) for index, problems in found.items()}
