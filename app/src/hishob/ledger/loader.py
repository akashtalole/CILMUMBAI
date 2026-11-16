"""Validate extracted facts and append the accepted ones to the ledger (SPEC-003).

Order of checks for each record: shape of the record (kind, label or type, JSON Schema, properties),
SHACL shapes for the whole batch, source and page, quote, then edge endpoints and their labels.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections import Counter
from collections.abc import Callable, Iterable
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import psycopg

from hishob.archive import Archive
from hishob.archive.storage import ObjectStore
from hishob.ledger import quotes
from hishob.schema import whitelist as wl
from hishob.schema.validate import json_problems, shacl_problems_batch

BATCH_ID = re.compile(r"^[A-Za-z0-9_-]{3,80}$")
Conn = psycopg.Connection[tuple[object, ...]]


class BatchAlreadyLoadedError(RuntimeError):
    pass


@dataclass
class BatchReport:
    batch_id: str
    accepted: int = 0
    unchanged: int = 0
    superseded: int = 0
    extended: int = 0
    corroborating: int = 0
    notes: int = 0
    held: dict[str, int] = field(default_factory=dict)
    quote_check: dict[str, int] = field(default_factory=dict)
    files: list[str] = field(default_factory=list)

    @property
    def held_total(self) -> int:
        return sum(self.held.values())


def identity(record: dict[str, Any]) -> str:
    if record["kind"] == "node":
        return f"node|{record['label']}|{record['id']}"
    return f"edge|{record['type']}|{record['from']}|{record['to']}"


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def fact_id(record: dict[str, Any]) -> str:
    basis = _canonical([identity(record), record["source"], record["page"], record.get("props") or {}])
    return "f_" + hashlib.sha256(basis.encode("utf-8")).hexdigest()[:32]


def _major(version: str) -> str:
    return version.split(".", 1)[0]


class Loader:
    def __init__(
        self,
        conn: Conn,
        archive: Archive,
        data: ObjectStore,
        *,
        now: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        self.conn = conn
        self.archive = archive
        self.data = data
        self.now = now

    # ---- public --------------------------------------------------------------------------------------------

    def load_file(self, path: Path, **kwargs: Any) -> BatchReport:
        lines = path.read_text(encoding="utf-8").splitlines()
        records = []
        for number, line in enumerate(lines, start=1):
            if not line.strip():
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError as error:
                records.append({"_unparseable": line, "_error": f"line {number}: {error.msg}"})
        return self.load(records, **kwargs)

    def load(
        self,
        records: Iterable[dict[str, Any]],
        *,
        batch_id: str,
        extractor: str,
        ontology_version: str | None = None,
    ) -> BatchReport:
        if not BATCH_ID.match(batch_id):
            raise ValueError("batch_id must be 3 to 80 letters, digits, '-' or '_'")
        if self.conn.execute("SELECT 1 FROM ledger.batches WHERE batch_id = %s", (batch_id,)).fetchone():
            self.conn.commit()
            raise BatchAlreadyLoadedError(batch_id)
        self.conn.commit()

        current_version = wl.load()["ontology_version"]
        self._new_in_batch: set[str] = set()
        at = self.now()
        report = BatchReport(batch_id)
        records = list(records)
        held: list[dict[str, Any]] = []
        notes: list[dict[str, Any]] = []
        problems: dict[int, list[str]] = {}

        def hold(index: int, reason: str) -> None:
            problems.setdefault(index, []).append(reason)

        # 1. Shape of each record
        for i, record in enumerate(records):
            if "_unparseable" in record:
                hold(i, f"schema_invalid: {record['_error']}")
                continue
            if record.get("kind") == "note":
                notes.append(record)
                continue
            if ontology_version and _major(ontology_version) != _major(current_version):
                hold(i, f"unknown_ontology_major: extracted under {ontology_version}, ledger is {current_version}")
                continue
            for p in self._shape(record):
                hold(i, p)

        # 2. SHACL, once for the whole batch
        shaped = [i for i, r in enumerate(records) if i not in problems and r.get("kind") in {"node", "edge"}]
        for i, found in shacl_problems_batch([records[i] for i in shaped]).items():
            for p in found:
                hold(shaped[i], p)

        # 3. Source, page and quote
        page_counts: dict[str, int | None] = {}
        for i, record in enumerate(records):
            if i in problems or record.get("kind") not in {"node", "edge"}:
                continue
            reason, status = self._quote(record, page_counts)
            if reason:
                hold(i, reason)
            else:
                record["quote_check"] = status

        # 4. Nodes: label conflicts with the ledger; then edges: endpoints and their labels
        batch_labels: dict[str, str] = {}
        for i, record in enumerate(records):
            if i in problems or record.get("kind") != "node":
                continue
            known = self._known_label(record["id"])
            if known and known != record["label"]:
                hold(i, f"label_conflict: {record['id']} is a {known} in the ledger, not a {record['label']}")
            elif batch_labels.get(record["id"], record["label"]) != record["label"]:
                hold(i, f"label_conflict: {record['id']} has two labels in this batch")
            else:
                batch_labels[record["id"]] = record["label"]
        for i, record in enumerate(records):
            if i in problems or record.get("kind") != "edge":
                continue
            ends = []
            for end in ("from", "to"):
                label = batch_labels.get(record[end]) or self._known_label(record[end])
                if label is None:
                    hold(i, f"dangling_endpoint: {end} {record[end]} is not in this batch or the ledger")
                ends.append(label)
            if None not in ends:
                for p in wl.check_edge(record["type"], str(ends[0]), str(ends[1])):
                    hold(i, p)

        # 5. Decide: hold, skip as unchanged, supersede, corroborate or add
        accepted: list[dict[str, Any]] = []
        seen_ids: set[str] = set()
        held_now: dict[str, dict[str, tuple[str, Any]]] = {}  # identity -> {property: (fact id, value)}
        for i, record in enumerate(records):
            if i in problems:
                reasons = problems[i]
                held.append({"record": record, "reason": reasons[0].split(":", 1)[0], "detail": reasons})
                report.held[reasons[0].split(":", 1)[0]] = report.held.get(reasons[0].split(":", 1)[0], 0) + 1
                continue
            if record.get("kind") == "note":
                continue
            entry = self._ledger_entry(record, batch_id, extractor, current_version, at)
            outcome = self._compare(entry, seen_ids, held_now)
            if outcome == "unchanged":
                report.unchanged += 1
                continue
            if outcome == "superseded":
                report.superseded += 1
            elif outcome == "extended":
                report.extended += 1
            elif outcome == "corroborating":
                report.corroborating += 1
            accepted.append(entry)
            seen_ids.add(entry["fact_id"])

        report.accepted = len(accepted)
        report.notes = len(notes)
        report.quote_check = dict(Counter(e["quote_check"] for e in accepted))
        self._write(report, accepted, held, notes, batch_id, extractor, current_version, at)
        return report

    def rebuild_index(self) -> int:
        """Drop the index and rebuild it from the ledger files alone (constitution C9). Returns facts indexed."""
        entries = []
        for key in self.data.list("facts/"):
            for line in self.data.get(key).decode("utf-8").splitlines():
                entry = json.loads(line)
                entry["_file_key"] = key
                entries.append(entry)
        entries.sort(key=lambda e: (e["loaded_at"], e["batch_id"], e["_file_key"], e["seq"]))
        with self.conn.transaction():
            self.conn.execute("TRUNCATE ledger.current_props, ledger.current, ledger.facts, ledger.batches")
            batches: dict[str, dict[str, Any]] = {}
            for e in entries:
                batches.setdefault(e["batch_id"], e)
            for batch_id, e in batches.items():
                self.conn.execute(
                    "INSERT INTO ledger.batches (batch_id, extractor, ontology_version, loaded_at, accepted, held,"
                    " report_key) VALUES (%s, %s, %s, %s, %s, 0, %s)",
                    (
                        batch_id,
                        e["extractor"],
                        e["ontology_version"],
                        e["loaded_at"],
                        sum(1 for x in entries if x["batch_id"] == batch_id),
                        f"staging/{batch_id}/report.json",
                    ),
                )
            self._index(entries)
        return len(entries)

    # ---- checks --------------------------------------------------------------------------------------------

    def _shape(self, record: dict[str, Any]) -> list[str]:
        kind = record.get("kind")
        labels = wl.load()["labels"]
        if kind == "node" and record.get("label") not in labels:
            return [f"unknown_label: {record.get('label')}"]
        if kind == "edge" and record.get("type") not in wl.load()["edges"]:
            return [f"unknown_edge: {record.get('type')}"]
        found = json_problems(record)
        if found:
            return found
        if kind == "node":
            return wl.check_node(record["label"], record.get("props") or {})
        return []

    def _quote(self, record: dict[str, Any], page_counts: dict[str, int | None]) -> tuple[str | None, str]:
        source, page = record["source"], record["page"]
        if source not in page_counts:
            row = self.archive.registry.get(source)
            page_counts[source] = row.page_count if row else None
        count = page_counts[source]
        if count is None:
            return f"unknown_source: {source} is not in the archive", ""
        if page > count:
            return f"page_out_of_range: page {page} of a {count}-page document", ""
        status = quotes.check(record["quote"], self.archive.page_text(source, page))
        if status == "quote_not_found":
            return f"quote_not_found: not on page {page}", ""
        return None, status

    def _known_label(self, node_id: str) -> str | None:
        row = self.conn.execute("SELECT label FROM ledger.current WHERE node_id = %s LIMIT 1", (node_id,)).fetchone()
        self.conn.commit()
        return str(row[0]) if row else None

    # ---- writing -------------------------------------------------------------------------------------------

    def _ledger_entry(
        self, record: dict[str, Any], batch_id: str, extractor: str, version: str, at: datetime
    ) -> dict[str, Any]:
        entry = {
            "fact_id": fact_id(record),
            "identity": identity(record),
            "kind": record["kind"],
            "props": record.get("props") or {},
            "source": record["source"],
            "page": record["page"],
            "quote": record["quote"],
            "tier": record["tier"],
            "confidence": record["confidence"],
            "quote_check": record["quote_check"],
            "extractor": extractor,
            "ontology_version": version,
            "batch_id": batch_id,
            "loaded_at": at.isoformat(),
            "change": "new",
            "supersedes": [],
            "holds": [],
        }
        if record["kind"] == "node":
            entry.update(label=record["label"], id=record["id"])
        else:
            entry.update(type=record["type"], **{"from": record["from"], "to": record["to"]})
        return entry

    def _compare(
        self, entry: dict[str, Any], seen_ids: set[str], held_now: dict[str, dict[str, tuple[str, Any]]]
    ) -> str:
        """Classify a record against what is currently held for its identity, property by property (R7).

        Sets entry["change"], entry["supersedes"] (fact ids replaced) and entry["holds"] (properties this fact now
        holds), and updates `held_now` for later records in the batch.
        """
        if entry["fact_id"] in seen_ids:
            return "unchanged"
        exists = self.conn.execute("SELECT 1 FROM ledger.facts WHERE fact_id = %s", (entry["fact_id"],)).fetchone()
        self.conn.commit()
        if exists:
            return "unchanged"
        identity_ = entry["identity"]
        if identity_ not in held_now:
            held_now[identity_] = self._held(identity_)
        current = held_now[identity_]
        known = bool(current) or self._identity_known(identity_)
        props = entry["props"]
        changed = sorted(k for k, v in props.items() if k in current and _canonical(current[k][1]) != _canonical(v))
        added = sorted(k for k in props if k not in current)
        if not known:
            change = "new"
        elif changed:
            change = "superseded"
        elif added:
            change = "extended"
        else:
            change = "corroborating"
        entry["change"] = change
        entry["supersedes"] = sorted({current[k][0] for k in changed})
        entry["holds"] = sorted(changed + added) if change != "corroborating" else []
        for key in entry["holds"]:
            current[key] = (entry["fact_id"], props[key])
        if change == "new":
            self._new_in_batch.add(identity_)
        return change

    def _held(self, identity_: str) -> dict[str, tuple[str, Any]]:
        rows = self.conn.execute(
            "SELECT key, fact_id, value FROM ledger.current_props WHERE identity = %s", (identity_,)
        ).fetchall()
        self.conn.commit()
        return {str(k): (str(f), v) for k, f, v in rows}

    def _identity_known(self, identity_: str) -> bool:
        if identity_ in self._new_in_batch:
            return True
        row = self.conn.execute("SELECT 1 FROM ledger.current WHERE identity = %s", (identity_,)).fetchone()
        self.conn.commit()
        return row is not None

    def current_properties(self, identity_: str) -> dict[str, Any]:
        """The value currently held for each property of an identity."""
        return {k: v for k, (_, v) in self._held(identity_).items()}

    def fact(self, fid: str) -> dict[str, Any] | None:
        """The full ledger entry for a fact id, or None."""
        row = self.conn.execute("SELECT file_key FROM ledger.facts WHERE fact_id = %s", (fid,)).fetchone()
        self.conn.commit()
        if row is None:
            return None
        for line in self.data.get(str(row[0])).decode("utf-8").splitlines():
            stored: dict[str, Any] = json.loads(line)
            if stored["fact_id"] == fid:
                return stored
        return None

    def props_of(self, fid: str) -> dict[str, Any]:
        entry = self.fact(fid)
        props: dict[str, Any] = entry["props"] if entry else {}
        return props

    def _write(
        self,
        report: BatchReport,
        accepted: list[dict[str, Any]],
        held: list[dict[str, Any]],
        notes: list[dict[str, Any]],
        batch_id: str,
        extractor: str,
        version: str,
        at: datetime,
    ) -> None:
        labels = wl.load()["labels"]
        node_labels = {e["id"]: e["label"] for e in accepted if e["kind"] == "node"}
        by_file: dict[str, list[dict[str, Any]]] = {}
        for entry in accepted:
            label = entry["label"] if entry["kind"] == "node" else self._label_for(entry["from"], node_labels)
            module = labels.get(label, {}).get("module", "core")
            key = f"facts/{module}/{at:%Y-%m-%d}/{batch_id}.jsonl"
            entry["seq"] = len(by_file.setdefault(key, []))
            by_file[key].append(entry)

        # Ledger files first (append-only: a key that exists is never rewritten), then the index.
        for key, entries in sorted(by_file.items()):
            body = "".join(json.dumps(e, ensure_ascii=False, sort_keys=True) + "\n" for e in entries)
            if not self.data.put_new(key, body.encode("utf-8"), "application/x-ndjson"):
                raise BatchAlreadyLoadedError(f"{key} already exists; a partial earlier load needs investigating")
            for e in entries:
                e["_file_key"] = key
            report.files.append(key)

        staging = f"staging/{batch_id}"
        if held:
            self.data.put_new(f"{staging}/held.jsonl", _jsonl(held), "application/x-ndjson")
        if notes:
            self.data.put_new(f"{staging}/notes.jsonl", _jsonl(notes), "application/x-ndjson")
        report_json = json.dumps({**asdict(report), "held_total": report.held_total}, indent=2, ensure_ascii=False)
        self.data.put_new(f"{staging}/report.json", report_json.encode("utf-8"), "application/json")

        with self.conn.transaction():
            self.conn.execute(
                "INSERT INTO ledger.batches (batch_id, extractor, ontology_version, loaded_at, accepted, held,"
                " report_key) VALUES (%s, %s, %s, %s, %s, %s, %s)",
                (batch_id, extractor, version, at, report.accepted, report.held_total, f"{staging}/report.json"),
            )
            self._index([e for entries in by_file.values() for e in entries])

    def _label_for(self, node_id: str, node_labels: dict[str, str]) -> str:
        return node_labels.get(node_id) or self._known_label(node_id) or ""

    def _index(self, entries: list[dict[str, Any]]) -> None:
        for e in entries:
            node = e["kind"] == "node"
            self.conn.execute(
                "INSERT INTO ledger.facts (fact_id, identity, kind, name, node_id, from_id, to_id, source, page,"
                " batch_id, file_key, supersedes, loaded_at) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                (
                    e["fact_id"],
                    e["identity"],
                    e["kind"],
                    e["label"] if node else e["type"],
                    e.get("id"),
                    e.get("from"),
                    e.get("to"),
                    e["source"],
                    e["page"],
                    e["batch_id"],
                    e["_file_key"],
                    e["supersedes"],
                    e["loaded_at"],
                ),
            )
            if e["change"] == "corroborating":
                continue
            self.conn.execute(
                "INSERT INTO ledger.current (identity, fact_id, label, node_id) VALUES (%s, %s, %s, %s)"
                " ON CONFLICT (identity) DO UPDATE SET fact_id = EXCLUDED.fact_id",
                (e["identity"], e["fact_id"], e.get("label"), e.get("id")),
            )
            for key in e["holds"]:
                self.conn.execute(
                    "INSERT INTO ledger.current_props (identity, key, fact_id, value) VALUES (%s, %s, %s, %s)"
                    " ON CONFLICT (identity, key) DO UPDATE SET fact_id = EXCLUDED.fact_id, value = EXCLUDED.value",
                    (e["identity"], key, e["fact_id"], json.dumps(e["props"][key], ensure_ascii=False)),
                )


def _jsonl(rows: list[dict[str, Any]]) -> bytes:
    return "".join(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n" for r in rows).encode("utf-8")
