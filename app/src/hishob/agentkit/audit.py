"""Run the audit desk for one ward (SPEC-011).

One session of the audit lead, with the Challenger and the Drafter on its roster, reads the graph through the API
under the reviewer tier (R1) and is graded against the ward-audit rubric (R7). Code then arranges the outputs by
the Challenger's verdicts (R3, R4) and checks them (R5, R6). If the check finds problems, the lead is asked once
to fix them; whatever still fails is held. The outputs are written to staging; publishing waits for the release
gate (R8, SPEC-009).
"""

from __future__ import annotations

import json
import time
from collections.abc import Callable
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath
from typing import Any

from hishob.agentkit.definitions import AGENTS_DIR
from hishob.agentkit.outputs import Arranged, OutputCheck, Violation, arrange, check_outputs, hold
from hishob.agentkit.provision import read_lock
from hishob.agentkit.session import follow, read_file, session_files
from hishob.agentkit.tools import ApiTools

OUTPUTS_ROOT = "/mnt/session/outputs/"


@dataclass
class AuditRun:
    run_id: str
    ward: str
    session_id: str | None = None
    status: str = "running"  # complete, incomplete, failed
    status_detail: str = ""
    files: list[str] = field(default_factory=list)  # staging keys that may be released
    held: dict[str, str] = field(default_factory=dict)  # staging key -> reason
    violations: list[dict[str, str]] = field(default_factory=list)  # from the final check
    fix_requested: bool = False
    grader_results: list[str] = field(default_factory=list)
    threads: list[dict[str, str]] = field(default_factory=list)
    cost_usd: float | None = None
    duration_s: int = 0
    started_at: str = ""


def run_audit(
    client: Any,
    http: Any,
    ward: str,
    data: Any,
    *,
    run_id: str,
    token: str | None,
    cap_usd: int = 10,
    keep_names: tuple[str, ...] = (),
    lock: dict[str, Any] | None = None,
    agents_dir: Path = AGENTS_DIR,
    clock: Callable[[], float] = time.monotonic,
    sleep: Callable[[float], None] = time.sleep,
) -> AuditRun:
    previous = _finished(data, run_id)
    if previous is not None:
        return previous  # a repeat after a restart returns the run that already finished
    run_id = _free_run_id(data, run_id)
    lock = lock or read_lock(agents_dir / ".lock.json")
    if "audit-lead" not in lock["agents"] or "civic-cloud" not in lock["environments"]:
        raise RuntimeError("the audit desk is not applied to this account; run `hishob agents apply` first")
    lead = lock["agents"]["audit-lead"]
    started = clock()
    run = AuditRun(run_id, ward, started_at=datetime.now(UTC).isoformat(timespec="seconds"))
    session = client.beta.sessions.create(
        agent={"type": "agent", "id": lead["id"], "version": lead["version"]},
        environment_id=lock["environments"]["civic-cloud"]["id"],
        title=f"Ward audit {ward} {run_id}",
        budget={"type": "limit", "max_list_cost": {"amount": str(cap_usd * 100), "currency": "USD"}},
        metadata={"project": "aamcha-hishob", "run_id": run_id, "ward": ward},
    )
    run.session_id = session.id
    tools = ApiTools(http, token)
    kickoff = {
        "type": "user.define_outcome",
        "description": (
            f"Audit ward {ward}. Write ward-brief.md, cases/, held/, drafts/ and gaps.jsonl to {OUTPUTS_ROOT}, "
            "with every case file reviewed by a Challenger."
        ),
        "rubric": {"type": "text", "content": (agents_dir / "rubrics" / "ward-audit.md").read_text(encoding="utf-8")},
        "max_iterations": 3,
    }
    outcome = follow(client, session.id, kickoff, on_tool=tools)
    run.grader_results, run.threads = list(outcome.grader_results), list(outcome.threads)

    arranged = arrange(_download(client, session.id, sleep))
    names = _names(tools.seen)
    check = _check(arranged, http, token, names, keep_names)
    if not check.ok and outcome.stop_reason != "budget_reached":
        run.fix_requested = True
        message = (
            "Code checked your outputs and found these problems. Fix each one in the file named, then stop:\n- "
            + "\n- ".join(f"{v.path}: {v.kind}: {v.detail}" for v in check.violations[:60])
        )
        follow(
            client, session.id, {"type": "user.message", "content": [{"type": "text", "text": message}]}, on_tool=tools
        )
        arranged = arrange(_download(client, session.id, sleep))
        names = _names(tools.seen)
        check = _check(arranged, http, token, names, keep_names)
    for path in sorted(check.paths()):
        if path in arranged.files and path.startswith(("cases/", "drafts/")) and not path.endswith(".challenge.md"):
            hold(arranged, path, _reasons(check, path))
        elif path.endswith(".challenge.md") and path in arranged.files:
            hold(arranged, path.removesuffix(".challenge.md") + ".md", "its review failed the output check")
    final = _check(arranged, http, token, names, keep_names)
    run.violations = [asdict(v) for v in final.violations]

    prefix = f"staging/{run_id}/"
    for path, body in sorted(arranged.files.items()):
        data.put_new(prefix + path, body, "text/markdown" if path.endswith(".md") else "application/x-ndjson")
        if not path.startswith("held/"):
            run.files.append(prefix + path)
    for path, reason in arranged.held.items():
        data.put_new(prefix + path.removesuffix(".md") + ".held.md", f"Held: {reason}\n".encode(), "text/markdown")
        run.held[prefix + path] = reason

    run.cost_usd = _cost(client, session.id)
    run.duration_s = int(clock() - started)
    if final.violations:
        run.status = "incomplete"
        run.status_detail = "; ".join(sorted({f"{v.path}: {v.kind}" for v in final.violations}))[:500]
    elif not outcome.finished:
        run.status, run.status_detail = "incomplete", f"session ended: {outcome.stop_reason}"
    else:
        run.status = "complete"
        cases = [f for f in run.files if "/cases/" in f and not f.endswith(".challenge.md")]
        run.status_detail = f"{len(cases)} cases, {len(run.held)} held"
    data.put_new(
        prefix + "manifest.json", json.dumps(asdict(run), ensure_ascii=False, indent=2).encode(), "application/json"
    )
    return run


def _check(
    arranged: Arranged, http: Any, token: str | None, names: dict[str, list[str]], keep: tuple[str, ...]
) -> OutputCheck:
    check = check_outputs(
        arranged.files,
        http,
        token=token,
        private_names=names["people"],
        contractor_names=names["contractors"],
        keep_names=keep,
    )
    check.violations += [Violation(p, "unexpected", "not part of the audit layout") for p in arranged.unexpected]
    return check


def _reasons(check: OutputCheck, path: str) -> str:
    return "failed the output check: " + "; ".join(f"{v.kind} {v.detail}" for v in check.violations if v.path == path)


def _names(seen: list[Any]) -> dict[str, list[str]]:
    people: set[str] = set()
    contractors: set[str] = set()

    def walk(value: Any) -> None:
        if isinstance(value, dict):
            if value.get("label") == "Person" and value.get("name"):
                people.add(str(value["name"]))
            if value.get("label") == "Contractor" and value.get("name"):
                contractors.add(str(value["name"]))
            for v in value.values():
                walk(v)
        elif isinstance(value, list):
            for v in value:
                walk(v)

    walk(seen)
    return {"people": sorted(people), "contractors": sorted(contractors)}


def _download(client: Any, session_id: str, sleep: Callable[[float], None]) -> dict[str, bytes]:
    """The session's output files by path relative to the outputs folder. A later file at the same path wins."""
    for attempt in range(4):
        items = session_files(client, session_id)
        if items or attempt == 3:
            break
        sleep(2)  # outputs are indexed a moment after the session goes idle
    out: dict[str, bytes] = {}
    for item in items:
        name = str(item.filename)
        relative = name.split(OUTPUTS_ROOT, 1)[-1].lstrip("/") or PurePosixPath(name).name
        out[relative] = read_file(client, item.id, sleep)
    return out


def _finished(data: Any, run_id: str) -> AuditRun | None:
    key = f"staging/{run_id}/manifest.json"
    if not data.exists(key):
        return None
    return AuditRun(**json.loads(data.get(key)))


def _free_run_id(data: Any, run_id: str) -> str:
    """A run interrupted while writing leaves files but no manifest; a new attempt writes beside it, not over it."""
    candidate, n = run_id, 1
    while data.list(f"staging/{candidate}/"):
        n += 1
        candidate = f"{run_id}-r{n}"
    return candidate


def _cost(client: Any, session_id: str) -> float | None:
    session = client.beta.sessions.retrieve(session_id)
    cost = getattr(getattr(session, "usage", None), "list_cost", None)
    return int(cost.amount) / 100 if cost is not None else None
