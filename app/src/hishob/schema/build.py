"""Generate the record schema, whitelist and reference page from the ontology (SPEC-002/R4 to R6)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from rdflib import OWL, RDF, Graph

from hishob.schema.model import ONTOLOGY_DIR, TIERS, Model, build_model, load_graph, read_version

APP_ROOT = ONTOLOGY_DIR.parent
OUTPUTS = {
    "records": "src/hishob/schema/records.json",
    "whitelist": "src/hishob/schema/whitelist.json",
    "reference": "ontology/REFERENCE.md",
}
ID_PATTERN = r"^[a-z][a-z_]*:\S+$"


class OntologyError(ValueError):
    pass


def _dump(data: Any) -> str:
    return json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def records_schema(model: Model) -> dict[str, Any]:
    provenance = {
        "source": {"type": "string", "pattern": "^[0-9a-f]{64}$", "description": "SHA-256 of the archived document"},
        "page": {"type": "integer", "minimum": 1},
        "quote": {"type": "string", "minLength": 1, "description": "Verbatim words from the page"},
        "tier": {"enum": TIERS},
        "confidence": {"type": "number", "minimum": 0, "maximum": 1},
    }
    required = ["source", "page", "quote", "tier", "confidence"]
    edge_types = sorted({e.edge_type for e in model.edges})
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": "Extracted record",
        "description": "One line of an extracted facts file. Generated from the ontology; do not edit.",
        "x-ontology-version": model.version,
        "oneOf": [{"$ref": "#/$defs/node"}, {"$ref": "#/$defs/edge"}, {"$ref": "#/$defs/note"}],
        "$defs": {
            "node": {
                "type": "object",
                "additionalProperties": False,
                "required": ["kind", "id", "label", *required],
                "properties": {
                    "kind": {"const": "node"},
                    "id": {"type": "string", "pattern": ID_PATTERN},
                    "label": {"enum": model.labels()},
                    "props": {"type": "object"},
                    **provenance,
                },
            },
            "edge": {
                "type": "object",
                "additionalProperties": False,
                "required": ["kind", "type", "from", "to", *required],
                "properties": {
                    "kind": {"const": "edge"},
                    "type": {"enum": edge_types},
                    "from": {"type": "string", "pattern": ID_PATTERN},
                    "to": {"type": "string", "pattern": ID_PATTERN},
                    "props": {"type": "object"},
                    **provenance,
                },
            },
            "note": {
                "type": "object",
                "additionalProperties": False,
                "required": ["kind", "text", "source", "page"],
                "properties": {
                    "kind": {"const": "note"},
                    "text": {"type": "string", "minLength": 1},
                    "source": provenance["source"],
                    "page": provenance["page"],
                    "quote": provenance["quote"],
                },
            },
        },
    }


def whitelist(model: Model) -> dict[str, Any]:
    return {
        "ontology_version": model.version,
        "tiers": TIERS,
        "labels": {
            label: {"module": model.classes[label].module, "properties": model.properties_for(label)}
            for label in model.labels()
        },
        "edges": model.allowed_pairs(),
    }


def reference(model: Model) -> str:
    lines = [
        "# Mumbai Civic Ontology: reference",
        "",
        f"Version {model.version}. Generated from the Turtle files in this folder by `hishob ontology build`; "
        "do not edit by hand. Marathi labels are drafts awaiting the language reviewer.",
        "",
    ]
    modules = sorted({c.module for c in model.classes.values() if not c.abstract})
    for module in modules:
        lines += [
            f"## {module.capitalize()}",
            "",
            "| Node label | English | Marathi | Properties |",
            "|---|---|---|---|",
        ]
        for label in model.labels():
            cls = model.classes[label]
            if cls.module != module:
                continue
            props = ", ".join(f"`{k}`" for k in model.properties_for(label))
            lines.append(f"| `{label}` | {cls.label_en} | {cls.label_mr} | {props} |")
        lines.append("")
    lines += ["## Relationships", "", "| Type | From | To | English | Marathi |", "|---|---|---|---|---|"]
    for edge in model.edges:
        lines.append(f"| `{edge.edge_type}` | `{edge.source}` | `{edge.target}` | {edge.label_en} | {edge.label_mr} |")
    lines += [
        "",
        "## Provenance on every fact",
        "",
        "| Field | Meaning |",
        "|---|---|",
        "| `source` | SHA-256 of the archived document |",
        "| `page` | Page number, from 1 |",
        "| `quote` | Verbatim words from that page that state the fact |",
        "| `tier` | `official`, `reported`, `citizen` or `derived` |",
        "| `confidence` | 0 to 1 |",
        "",
    ]
    return "\n".join(lines)


def _check_version(graph: Graph, version: str) -> None:
    declared = {str(o) for s in graph.subjects(RDF.type, OWL.Ontology) for o in graph.objects(s, OWL.versionInfo)}
    if declared != {version}:
        raise OntologyError(f"VERSION says {version} but the ontology declares {sorted(declared) or 'nothing'}")


def generate(ontology_dir: Path = ONTOLOGY_DIR) -> dict[str, str]:
    """Return {relative output path: content}. Raises OntologyError if the files disagree."""
    graph = load_graph(ontology_dir)
    version = read_version(ontology_dir)
    _check_version(graph, version)
    model = build_model(graph, version)
    return {
        OUTPUTS["records"]: _dump(records_schema(model)),
        OUTPUTS["whitelist"]: _dump(whitelist(model)),
        OUTPUTS["reference"]: reference(model),
    }


def write(files: dict[str, str], root: Path = APP_ROOT) -> None:
    for relative, content in files.items():
        (root / relative).write_text(content, encoding="utf-8")


def stale(files: dict[str, str], root: Path = APP_ROOT) -> list[str]:
    """Paths whose committed content differs from what the ontology now generates."""
    out = []
    for relative, content in files.items():
        path = root / relative
        if not path.exists() or path.read_text(encoding="utf-8") != content:
            out.append(relative)
    return out
