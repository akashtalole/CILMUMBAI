"""Run the intake desk on a batch of archived documents (SPEC-005)."""

from __future__ import annotations

import hashlib
import json
import time
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from hishob.agentkit.definitions import AGENTS_DIR
from hishob.agentkit.provision import read_lock
from hishob.agentkit.session import follow
from hishob.archive import Archive
from hishob.ledger import Loader
from hishob.schema import whitelist as wl
from hishob.schema.build import OUTPUTS
from hishob.schema.model import ONTOLOGY_DIR

APP_ROOT = ONTOLOGY_DIR.parent
OUTPUT_FILES = ("facts.jsonl", "review.jsonl", "report.md")
ENTITY_PROPS = ("name", "name_en", "reg_no", "code", "tender_id", "bmc_bid_no")


@dataclass
class IntakeRun:
    run_id: str
    session_id: str | None = None
    agents: dict[str, str] = field(default_factory=dict)
    inputs: list[str] = field(default_factory=list)
    outputs: dict[str, str] = field(default_factory=dict)
    status: str = "running"  # complete, incomplete, failed
    status_detail: str = ""
    cost_usd: float | None = None
    duration_s: int = 0
    threads: list[dict[str, str]] = field(default_factory=list)
    load_report: str | None = None
    not_in_report: list[str] = field(default_factory=list)


def known_entities(loader: Loader) -> bytes:
    """The entities the ledger already holds, for the entity resolver. One JSON object per line."""
    rows = loader.conn.execute(
        "SELECT node_id, label, fact_id FROM ledger.current WHERE node_id IS NOT NULL ORDER BY node_id"
    ).fetchall()
    loader.conn.commit()
    lines = []
    for node_id, label, fid in rows:
        props = loader.props_of(str(fid))
        lines.append({"id": node_id, "label": label, **{k: props[k] for k in ENTITY_PROPS if k in props}})
    if not lines:
        lines.append({"note": "no known entities yet"})
    return "".join(json.dumps(x, ensure_ascii=False) + "\n" for x in lines).encode("utf-8")


def run_intake(
    client: Any,
    archive: Archive,
    loader: Loader,
    hashes: list[str],
    *,
    cap_usd: int = 5,
    agents_dir: Path = AGENTS_DIR,
    lock: dict[str, Any] | None = None,
    run_id: str | None = None,
    now: Callable[[], datetime] = lambda: datetime.now(UTC),
    clock: Callable[[], float] = time.monotonic,
    sleep: Callable[[float], None] = time.sleep,
) -> IntakeRun:
    if not hashes:
        raise ValueError("no documents to read")
    lock = lock or read_lock(agents_dir / ".lock.json")
    if "ingest-lead" not in lock["agents"] or "civic-cloud" not in lock["environments"]:
        raise RuntimeError("agents are not applied to this account; run `hishob agents apply` first")
    lead = lock["agents"]["ingest-lead"]
    started_at, started = now(), clock()
    run = IntakeRun(run_id or f"intake-{started_at:%Y%m%d-%H%M%S}-{uuid.uuid4().hex[:6]}")
    run.inputs = list(hashes)
    run.agents = {key: f"{a['id']}@{a['version']}" for key, a in sorted(lock["agents"].items())}
    _record(loader, run, started_at, finished=False)

    resources = []
    for sha in hashes:
        row = archive.registry.get(sha)
        if row is None:
            raise KeyError(f"{sha} is not in the archive")
        name = f"{sha}.{row.extension}"
        resources.append(_mount(client, name, archive.open(sha).read(), row.media_type, f"/corpus/{name}"))
    resources.append(
        _mount(
            client,
            "records.json",
            (APP_ROOT / OUTPUTS["records"]).read_bytes(),
            "application/json",
            "/schema/records.json",
        )
    )
    resources.append(
        _mount(
            client,
            "reference.md",
            (APP_ROOT / OUTPUTS["reference"]).read_bytes(),
            "text/markdown",
            "/schema/reference.md",
        )
    )
    resources.append(
        _mount(client, "entities.jsonl", known_entities(loader), "application/x-ndjson", "/entities.jsonl")
    )

    session = client.beta.sessions.create(
        agent={"type": "agent", "id": lead["id"], "version": lead["version"]},
        environment_id=lock["environments"]["civic-cloud"]["id"],
        title=f"Intake {run.run_id}",
        resources=resources,
        budget={"type": "limit", "max_list_cost": {"amount": str(cap_usd * 100), "currency": "USD"}},
        metadata={"project": "aamcha-hishob", "run_id": run.run_id},
    )
    run.session_id = session.id
    _record(loader, run, started_at, finished=False)

    kickoff = {
        "type": "user.define_outcome",
        "description": (
            f"Extract, verify and resolve facts from all {len(hashes)} documents in /mnt/session/uploads/corpus/ "
            "into /mnt/session/outputs/facts.jsonl, with review.jsonl and report.md."
        ),
        "rubric": {"type": "text", "content": (agents_dir / "rubrics" / "ingest.md").read_text(encoding="utf-8")},
        "max_iterations": 3,
    }
    outcome = follow(client, session.id, kickoff)
    run.threads = outcome.threads

    files = _session_files(client, session.id, sleep)
    facts = b""
    report_text = ""
    for item in files:
        name = Path(item.filename).name
        content = client.beta.files.download(item.id).read()
        loader.data.put_new(f"staging/{run.run_id}/{name}", content, "application/octet-stream")
        run.outputs[name] = _sha256(content)
        if name == "facts.jsonl":
            facts = content
        if name == "report.md":
            report_text = content.decode("utf-8", errors="replace")

    run.cost_usd = _cost(client, session.id)
    run.duration_s = int(clock() - started)

    if "facts.jsonl" not in run.outputs:
        run.status, run.status_detail = "failed", f"no facts.jsonl (session ended: {outcome.stop_reason})"
    else:
        records = [json.loads(line) for line in facts.decode("utf-8").splitlines() if line.strip()]
        report = loader.load(
            records,
            batch_id=run.run_id,
            extractor=f"ingest-lead@{lead['version']}",
            ontology_version=wl.load()["ontology_version"],
        )
        run.load_report = f"staging/{run.run_id}/report.json"
        run.not_in_report = [sha for sha in hashes if sha not in report_text]
        if outcome.stop_reason == "budget_reached":
            run.status, run.status_detail = "incomplete", "stopped at the spending cap"
        elif not outcome.finished:
            run.status, run.status_detail = "incomplete", f"session ended: {outcome.stop_reason}"
        elif run.not_in_report:
            run.status, run.status_detail = "incomplete", f"{len(run.not_in_report)} inputs missing from report.md"
        else:
            run.status = "complete"
            run.status_detail = f"{report.accepted} facts loaded, {report.held_total} held"
    if outcome.stop_reason == "budget_reached" and run.status == "failed":
        run.status, run.status_detail = "incomplete", "stopped at the spending cap before writing facts"
    _record(loader, run, started_at, finished=True, finished_at=now())
    return run


def _mount(client: Any, name: str, data: bytes, mime: str, mount_path: str) -> dict[str, str]:
    uploaded = client.beta.files.upload(file=(name, data, mime))
    return {"type": "file", "file_id": uploaded.id, "mount_path": mount_path}


def _session_files(client: Any, session_id: str, sleep: Callable[[float], None]) -> list[Any]:
    for attempt in range(4):
        page = client.beta.files.list(scope_id=session_id, betas=["managed-agents-2026-04-01"])
        files = [f for f in page.data if Path(f.filename).name in OUTPUT_FILES]
        if files or attempt == 3:
            return files
        sleep(2)  # outputs are indexed a moment after the session goes idle
    return []


def _cost(client: Any, session_id: str) -> float | None:
    session = client.beta.sessions.retrieve(session_id)
    cost = getattr(getattr(session, "usage", None), "list_cost", None)
    return int(cost.amount) / 100 if cost is not None else None


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _record(
    loader: Loader, run: IntakeRun, started_at: datetime, *, finished: bool, finished_at: datetime | None = None
) -> None:
    with loader.conn.transaction():
        loader.conn.execute(
            "INSERT INTO agentkit.runs (run_id, kind, session_id, agents, inputs, outputs, status, status_detail,"
            " cost_usd, duration_s, threads, load_report_key, started_at, finished_at)"
            " VALUES (%s, 'intake', %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"
            " ON CONFLICT (run_id) DO UPDATE SET session_id = EXCLUDED.session_id, outputs = EXCLUDED.outputs,"
            " status = EXCLUDED.status, status_detail = EXCLUDED.status_detail, cost_usd = EXCLUDED.cost_usd,"
            " duration_s = EXCLUDED.duration_s, threads = EXCLUDED.threads,"
            " load_report_key = EXCLUDED.load_report_key, finished_at = EXCLUDED.finished_at",
            (
                run.run_id,
                run.session_id,
                json.dumps(run.agents),
                run.inputs,
                json.dumps(run.outputs),
                run.status,
                run.status_detail or None,
                run.cost_usd,
                run.duration_s if finished else None,
                json.dumps(run.threads),
                run.load_report,
                started_at,
                finished_at,
            ),
        )
