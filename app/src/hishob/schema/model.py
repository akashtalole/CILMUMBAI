"""Read the ontology files into a small model the generator and validators use (SPEC-002)."""

from __future__ import annotations

from dataclasses import dataclass, field
from functools import cache
from pathlib import Path

from rdflib import OWL, RDF, RDFS, SKOS, Graph, Literal, Namespace, URIRef

MCO = Namespace("https://akashtalole.github.io/CILMUMBAI/ontology/mco#")
DATA = Namespace("https://akashtalole.github.io/CILMUMBAI/id/")
ONTOLOGY_DIR = Path(__file__).resolve().parents[3] / "ontology"

XSD_TO_JSON = {
    "string": "string",
    "integer": "integer",
    "decimal": "number",
    "date": "date",
    "boolean": "boolean",
}
TIERS = ["official", "reported", "citizen", "derived"]


@dataclass(frozen=True)
class ClassDef:
    name: str
    module: str
    abstract: bool
    label_en: str
    label_mr: str
    parents: tuple[str, ...]
    matches: tuple[str, ...]


@dataclass(frozen=True)
class PropertyDef:
    key: str
    iri: str
    xsd: str
    label_en: str
    label_mr: str
    owners: tuple[str, ...]


@dataclass(frozen=True)
class EdgeDef:
    iri: str
    edge_type: str
    source: str
    target: str
    label_en: str
    label_mr: str


@dataclass
class Model:
    version: str
    classes: dict[str, ClassDef]
    properties: dict[str, PropertyDef]
    edges: list[EdgeDef]
    _children: dict[str, set[str]] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for cls in self.classes.values():
            for parent in cls.parents:
                self._children.setdefault(parent, set()).add(cls.name)

    def ancestors(self, name: str) -> list[str]:
        seen: list[str] = []
        stack = [name]
        while stack:
            current = stack.pop()
            if current in seen or current not in self.classes:
                continue
            seen.append(current)
            stack.extend(self.classes[current].parents)
        return seen

    def concrete_descendants(self, name: str) -> list[str]:
        found: set[str] = set()
        stack = [name]
        while stack:
            current = stack.pop()
            if current in found:
                continue
            found.add(current)
            stack.extend(self._children.get(current, ()))
        return sorted(c for c in found if c in self.classes and not self.classes[c].abstract)

    def labels(self) -> list[str]:
        return sorted(name for name, cls in self.classes.items() if not cls.abstract)

    def properties_for(self, label: str) -> dict[str, str]:
        lineage = set(self.ancestors(label))
        return {
            p.key: XSD_TO_JSON[p.xsd]
            for p in sorted(self.properties.values(), key=lambda p: p.key)
            if lineage & set(p.owners)
        }

    def allowed_pairs(self) -> dict[str, list[list[str]]]:
        pairs: dict[str, set[tuple[str, str]]] = {}
        for edge in self.edges:
            for source in self.concrete_descendants(edge.source):
                for target in self.concrete_descendants(edge.target):
                    pairs.setdefault(edge.edge_type, set()).add((source, target))
        return {t: [list(p) for p in sorted(v)] for t, v in sorted(pairs.items())}


def _label(graph: Graph, subject: URIRef, lang: str) -> str:
    for value in graph.objects(subject, RDFS.label):
        if isinstance(value, Literal) and value.language == lang:
            return str(value)
    return ""


def _local(iri: object) -> str:
    return str(iri).split("#", 1)[-1]


def load_graph(directory: Path = ONTOLOGY_DIR) -> Graph:
    graph = Graph()
    for path in sorted(directory.glob("mco-*.ttl")):
        graph.parse(path, format="turtle")
    return graph


def load_shapes(directory: Path = ONTOLOGY_DIR) -> Graph:
    graph = Graph()
    for path in sorted((directory / "shapes").glob("*.ttl")):
        graph.parse(path, format="turtle")
    return graph


def build_model(graph: Graph, version: str) -> Model:
    classes: dict[str, ClassDef] = {}
    for subject in graph.subjects(RDF.type, OWL.Class):
        if not isinstance(subject, URIRef) or not str(subject).startswith(str(MCO)):
            continue
        name = _local(subject)
        parents = tuple(
            sorted(_local(p) for p in graph.objects(subject, RDFS.subClassOf) if str(p).startswith(str(MCO)))
        )
        matches = tuple(
            sorted(
                str(o)
                for pred in (SKOS.closeMatch, SKOS.exactMatch, OWL.equivalentClass, RDFS.subClassOf)
                for o in graph.objects(subject, pred)
                if not str(o).startswith(str(MCO))
            )
        )
        classes[name] = ClassDef(
            name=name,
            module=str(graph.value(subject, MCO.module) or ""),
            abstract=bool(graph.value(subject, MCO.abstract)),
            label_en=_label(graph, subject, "en"),
            label_mr=_label(graph, subject, "mr"),
            parents=parents,
            matches=matches,
        )

    properties: dict[str, PropertyDef] = {}
    for subject in graph.subjects(RDF.type, OWL.DatatypeProperty):
        key = graph.value(subject, MCO.jsonKey)
        owners = tuple(sorted(_local(o) for o in graph.objects(subject, MCO.propertyOf)))
        if key is None or not owners or not isinstance(subject, URIRef):
            continue  # provenance and internal properties are not record props
        xsd = str(graph.value(subject, RDFS.range)).rsplit("#", 1)[-1]
        properties[str(key)] = PropertyDef(
            str(key), str(subject), xsd, _label(graph, subject, "en"), _label(graph, subject, "mr"), owners
        )

    edges = []
    for subject in graph.subjects(MCO.edgeType, None):
        if not isinstance(subject, URIRef):
            continue
        edges.append(
            EdgeDef(
                iri=str(subject),
                edge_type=str(graph.value(subject, MCO.edgeType)),
                source=_local(graph.value(subject, MCO.edgeFrom)),
                target=_local(graph.value(subject, MCO.edgeTo)),
                label_en=_label(graph, subject, "en"),
                label_mr=_label(graph, subject, "mr"),
            )
        )
    edges.sort(key=lambda e: (e.edge_type, e.source, e.target))
    return Model(version, classes, properties, edges)


def read_version(directory: Path = ONTOLOGY_DIR) -> str:
    return (directory / "VERSION").read_text(encoding="utf-8").strip()


@cache
def default_model() -> Model:
    return build_model(load_graph(), read_version())
