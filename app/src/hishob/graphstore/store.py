"""Project the facts ledger into a property graph over Bolt (Neo4j, Neptune) (SPEC-006/R1 to R4, R6).

Every node carries the label `Node` and its ontology label, an `id`, its current properties, and the
provenance of the fact that last changed it; `_prov_<property>` holds each property's own provenance as JSON.
Each fact is
also a `Fact` node linked from its subject by `HAS_FACT`, with `SUPERSEDES` links to the facts it replaced,
so history stays queryable. Queries stay within the openCypher subset Neo4j and Neptune share.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any

import psycopg

from hishob.archive.storage import ObjectStore
from hishob.schema import whitelist as wl

Conn = psycopg.Connection[tuple[object, ...]]
BATCH = 500


@dataclass(frozen=True)
class Watermark:
    files_applied: int
    facts_applied: int
    last_file: str | None


@dataclass(frozen=True)
class RebuildReport:
    nodes: int
    relationships: int
    facts: int
    fingerprint: str


class GraphStore:
    def __init__(self, driver: Any, conn: Conn, data: ObjectStore, database: str | None = None) -> None:
        self.driver = driver
        self.conn = conn
        self.data = data
        self.database = database

    # ---- projection ----------------------------------------------------------------------------------------

    def ensure_schema(self) -> None:
        for statement in (
            "CREATE CONSTRAINT node_id IF NOT EXISTS FOR (n:Node) REQUIRE n.id IS UNIQUE",
            "CREATE CONSTRAINT fact_id IF NOT EXISTS FOR (f:Fact) REQUIRE f.fact_id IS UNIQUE",
        ):
            self._run(statement)

    def apply(self) -> Watermark:
        """Apply ledger files not yet in the graph, in the order they were loaded (R1)."""
        self.ensure_schema()
        applied = {str(r[0]) for r in self.conn.execute("SELECT file_key FROM graphstore.applied").fetchall()}
        self.conn.commit()
        pending = [key for key in self.data.list("facts/") if key not in applied]
        entries = []
        for key in pending:
            for line in self.data.get(key).decode("utf-8").splitlines():
                entries.append({**json.loads(line), "_file": key})
        entries.sort(key=lambda e: (e["loaded_at"], e["batch_id"], e["_file"], e["seq"]))
        nodes = [e for e in entries if e["kind"] == "node"]
        edges = [e for e in entries if e["kind"] == "edge"]
        labels = wl.load()["labels"]
        edge_types = wl.load()["edges"]
        for entry in nodes:
            if entry["label"] not in labels:
                raise ValueError(f"label not in the ontology: {entry['label']}")
        for entry in edges:
            if entry["type"] not in edge_types:
                raise ValueError(f"relationship not in the ontology: {entry['type']}")
        for chunk in _chunks(nodes):
            self._apply_nodes(chunk)
        for chunk in _chunks(edges):
            self._apply_edges(chunk)
        with self.conn.transaction():
            for key in pending:
                count = sum(1 for e in entries if e["_file"] == key)
                self.conn.execute("INSERT INTO graphstore.applied (file_key, facts) VALUES (%s, %s)", (key, count))
        return self.watermark()

    def rebuild(self) -> RebuildReport:
        """Drop the graph and rebuild it from the whole ledger (R2; constitution C9)."""
        self._run("MATCH (n) DETACH DELETE n")
        with self.conn.transaction():
            self.conn.execute("TRUNCATE graphstore.applied")
        self.apply()
        return self.fingerprint()

    def watermark(self) -> Watermark:
        row = self.conn.execute(
            "SELECT count(*), coalesce(sum(facts), 0), max(file_key) FROM graphstore.applied"
        ).fetchone()
        self.conn.commit()
        assert row is not None
        return Watermark(int(str(row[0])), int(str(row[1])), str(row[2]) if row[2] else None)

    def fingerprint(self) -> RebuildReport:
        nodes = self._single("MATCH (n:Node) RETURN count(n) AS c")
        rels = self._single("MATCH (:Node)-[r]->(:Node) RETURN count(r) AS c")
        facts = self._records("MATCH (f:Fact) RETURN f.fact_id AS id ORDER BY id")
        digest = hashlib.sha256("\n".join(r["id"] for r in facts).encode()).hexdigest()
        return RebuildReport(nodes, rels, len(facts), digest)

    # ---- internals -----------------------------------------------------------------------------------------

    def _apply_nodes(self, entries: list[dict[str, Any]]) -> None:
        by_label: dict[str, list[dict[str, Any]]] = {}
        for e in entries:
            by_label.setdefault(e["label"], []).append(_node_row(e))
        for label, rows in by_label.items():
            # The label is checked against the ontology above, so it is safe to place in the query.
            self._run(
                f"UNWIND $rows AS row "
                f"MERGE (n:Node {{id: row.id}}) SET n:{label} "
                "WITH n, row "
                "CREATE (f:Fact {fact_id: row.fact_id, identity: row.identity, change: row.change,"
                " props: row.props_json, source: row.source, page: row.page, quote: row.quote, tier: row.tier,"
                " quote_check: row.quote_check, loaded_at: row.loaded_at, batch_id: row.batch_id,"
                " extractor: row.extractor}) "
                "CREATE (n)-[:HAS_FACT]->(f) "
                "WITH n, f, row WHERE row.change <> 'corroborating' "
                "SET n += row.props, n.fact_id = row.fact_id, n.source = row.source, n.page = row.page,"
                " n.tier = row.tier, n.quote_check = row.quote_check "
                "WITH f, row UNWIND row.supersedes AS old "
                "MATCH (o:Fact {fact_id: old}) CREATE (f)-[:SUPERSEDES]->(o)",
                rows=rows,
            )

    def _apply_edges(self, entries: list[dict[str, Any]]) -> None:
        by_type: dict[str, list[dict[str, Any]]] = {}
        for e in entries:
            by_type.setdefault(e["type"], []).append(
                {
                    "from": e["from"],
                    "to": e["to"],
                    "props": _scalars(e["props"]),
                    "fact_id": e["fact_id"],
                    "source": e["source"],
                    "page": e["page"],
                    "tier": e["tier"],
                    "quote_check": e["quote_check"],
                    "quote": e["quote"],
                    "change": e.get("change", "new"),
                }
            )
        for edge_type, rows in by_type.items():
            self._run(
                "UNWIND $rows AS row "
                "MATCH (a:Node {id: row.from}) MATCH (b:Node {id: row.to}) "
                f"MERGE (a)-[r:{edge_type}]->(b) "
                "ON CREATE SET r.fact_id = row.fact_id, r.source = row.source, r.page = row.page, r.tier = row.tier,"
                " r.quote_check = row.quote_check, r.quote = row.quote "
                "WITH r, row WHERE row.change <> 'corroborating' "
                "SET r += row.props, r.fact_id = row.fact_id, r.source = row.source, r.page = row.page,"
                " r.tier = row.tier, r.quote_check = row.quote_check, r.quote = row.quote",
                rows=rows,
            )

    def _run(self, query: str, **params: Any) -> None:
        with self.driver.session(database=self.database) as session:
            session.run(query, **params).consume()

    def _records(self, query: str, **params: Any) -> list[dict[str, Any]]:
        with self.driver.session(database=self.database) as session:
            return [record.data() for record in session.run(query, **params)]

    def _single(self, query: str, **params: Any) -> int:
        rows = self._records(query, **params)
        return int(rows[0]["c"]) if rows else 0


def _scalars(props: dict[str, Any]) -> dict[str, Any]:
    """Graph properties must be scalars or lists of scalars; anything else is stored as JSON text."""
    return {
        k: v if isinstance(v, str | int | float | bool) else json.dumps(v, ensure_ascii=False) for k, v in props.items()
    }


def _node_row(e: dict[str, Any]) -> dict[str, Any]:
    holds = e.get("holds", list(e["props"]))
    provenance = json.dumps(
        {
            "fact_id": e["fact_id"],
            "source": e["source"],
            "page": e["page"],
            "tier": e["tier"],
            "quote_check": e["quote_check"],
        },
        sort_keys=True,
    )
    return {
        "id": e["id"],
        "identity": e["identity"],
        "fact_id": e["fact_id"],
        "change": e.get("change", "new"),
        # Current values plus, per property, the fact that holds it: `_prov_<key>` (JSON).
        "props": {**_scalars({k: e["props"][k] for k in holds}), **{f"_prov_{k}": provenance for k in holds}},
        "props_json": json.dumps(e["props"], ensure_ascii=False, sort_keys=True),
        "supersedes": e.get("supersedes") or [],
        "source": e["source"],
        "page": e["page"],
        "quote": e["quote"],
        "tier": e["tier"],
        "quote_check": e["quote_check"],
        "loaded_at": e["loaded_at"],
        "batch_id": e["batch_id"],
        "extractor": e["extractor"],
    }


def _chunks(items: list[dict[str, Any]]) -> list[list[dict[str, Any]]]:
    return [items[i : i + BATCH] for i in range(0, len(items), BATCH)]
