"""Run the Mumbai Civic Graph agents on Claude Managed Agents.

Agents, the environment and the memory stores are defined as files in this
directory and created with `ant apply`, which writes their ids to
claude-lock.json. This script only starts sessions and answers their tool calls.

    python civic_client.py ingest ../data/raw/*.pdf
    python civic_client.py load ../data/extracted/<session>/facts.jsonl
    python civic_client.py audit "K/West"
    python civic_client.py ask "Who is responsible for the potholes on SV Road near Andheri station?"

Credentials come from the environment (ANTHROPIC_API_KEY or an `ant auth login`
profile). The graph is reached over Bolt, so HydraDB and Neo4j both work:
GRAPH_URI, GRAPH_USER, GRAPH_PASSWORD.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import re
import sys
import time
from pathlib import Path

import anthropic
from neo4j import GraphDatabase

HERE = Path(__file__).parent
LOCK = json.loads((HERE / "claude-lock.json").read_text()) if (HERE / "claude-lock.json").exists() else {"resources": {}}
SCHEMA = (HERE / "schema.md").read_text()
LABELS = set(re.findall(r"`([A-Z][A-Za-z]+)`", SCHEMA.split("## Node labels")[1].split("## Edge types")[0]))
EDGE_TYPES = set(re.findall(r"`([A-Z_]+)`", SCHEMA.split("## Edge types")[1]))

client = anthropic.Anthropic()
_driver = None


def resource_id(path: str) -> str:
    try:
        return LOCK["resources"][path]["id"]
    except KeyError:
        sys.exit(f"{path} is not in claude-lock.json. Run `ant apply` in {HERE} first.")


def graph():
    global _driver
    if _driver is None:
        _driver = GraphDatabase.driver(
            os.environ.get("GRAPH_URI", "neo4j://127.0.0.1:7687"),
            auth=(os.environ.get("GRAPH_USER", "neo4j"), os.environ.get("GRAPH_PASSWORD", "")),
        )
    return _driver


def read(query: str, **params) -> list[dict]:
    with graph().session() as s:
        return s.execute_read(lambda tx: [r.data() for r in tx.run(query, **params)][:200])


# ---- graph tools the agents can call -------------------------------------

WRITE_WORDS = re.compile(r"\b(create|merge|delete|set|remove|drop|load|call)\b", re.I)


def tool_cypher_read(query: str, params: dict | None = None) -> list[dict]:
    if WRITE_WORDS.search(query):
        raise ValueError("only read queries are allowed")
    return read(query, **(params or {}))


def tool_find_entity(text: str, label: str | None = None) -> list[dict]:
    if label and label not in LABELS:
        raise ValueError(f"unknown label {label}")
    match = f"MATCH (n:{label})" if label else "MATCH (n)"
    return read(
        match + " WHERE toLower(n.name) CONTAINS toLower($t) OR toLower(n.name_en) CONTAINS toLower($t) "
        "RETURN n.id AS id, labels(n) AS labels, n.name AS name, n.name_en AS name_en LIMIT 20",
        t=text,
    )


def tool_get_source(source_id: str, page: int | None = None) -> list[dict]:
    return read(
        "MATCH (s:SourceDocument {id: $id}) RETURN s.id AS id, s.title AS title, s.url AS url, "
        "s.fetched_at AS fetched_at, s.sha256 AS sha256",
        id=source_id,
    ) + ([{"page": page}] if page else [])


def tool_locate(lat: float, lon: float) -> dict:
    rows = read(
        "MATCH (a:Asset)-[:LOCATED_IN]->(w:AdminWard) "
        "WHERE abs(a.lat - $lat) < 0.01 AND abs(a.lon - $lon) < 0.01 "
        "OPTIONAL MATCH (ag:Agency)-[:OWNS]->(a) "
        "RETURN a.id AS asset_id, a.name AS asset, a.lat AS lat, a.lon AS lon, w.code AS ward, "
        "ag.name AS agency, a.source_id AS source_id, a.tier AS tier",
        lat=lat, lon=lon,
    )
    if not rows:
        return {"found": False}
    nearest = min(rows, key=lambda r: math.hypot(r["lat"] - lat, (r["lon"] - lon) * math.cos(math.radians(lat))))
    nearest["distance_m"] = round(111_000 * math.hypot(nearest["lat"] - lat, (nearest["lon"] - lon) * math.cos(math.radians(lat))))
    return {"found": True, **nearest}


def tool_trace_money(node_id: str) -> list[dict]:
    return read(
        "MATCH (w:Work) WHERE w.id = $id OR (w)-[:IMPROVES]->(:Asset {id: $id}) "
        "OPTIONAL MATCH (w)-[:FUNDED_BY]->(al:Allocation)-[:UNDER]->(bh:BudgetHead) "
        "OPTIONAL MATCH (t:Tender)-[:FOR_WORK]->(w) "
        "OPTIONAL MATCH (c:Contract)-[:FOR_WORK]->(w) "
        "OPTIONAL MATCH (k:Contractor)-[:PARTY_TO]->(c) "
        "OPTIONAL MATCH (w)-[:HAS_DLP]->(d:DefectLiabilityPeriod) "
        "RETURN w, bh, al, t, c, k, d ORDER BY t.published_on DESC",
        id=node_id,
    )


def tool_who_is_responsible(asset_id: str, issue: str | None = None) -> dict:
    today = time.strftime("%Y-%m-%d")
    owner = read(
        "MATCH (a:Asset {id: $id})-[:LOCATED_IN]->(w:AdminWard) "
        "OPTIONAL MATCH (ag:Agency)-[:OWNS]->(a) "
        "OPTIONAL MATCH (p:Post)-[:COVERS]->(w) "
        "OPTIONAL MATCH (p)-[:IN]->(d:Department)-[:PART_OF]->(ag) "
        "OPTIONAL MATCH (p)-[:REPORTS_TO*1..3]->(up:Post) "
        "RETURN a.name AS asset, w.code AS ward, ag.name AS agency, d.name AS department, "
        "p.title AS post, collect(DISTINCT up.title) AS escalation",
        id=asset_id,
    )
    liable = read(
        "MATCH (:Asset {id: $id})<-[:IMPROVES]-(w:Work)-[:HAS_DLP]->(d:DefectLiabilityPeriod) "
        "WHERE d.from <= $today AND d.to >= $today "
        "MATCH (k:Contractor)-[:PARTY_TO]->(:Contract)-[:FOR_WORK]->(w) "
        "RETURN w.title AS work, k.name AS contractor, d.to AS liable_until, d.source_id AS source_id, d.page AS page, d.quote AS quote",
        id=asset_id, today=today,
    )
    reps = read(
        "MATCH (:Asset {id: $id})-[:LOCATED_IN]->(:AdminWard)<-[:WITHIN]-(e:ElectoralWard)<-[:REPRESENTS]-(p:Person) "
        "RETURN e.number AS electoral_ward, p.name AS representative",
        id=asset_id,
    )
    return {"issue": issue, "responsible": owner, "under_liability": liable, "representatives": reps}


TOOLS = {
    "cypher_read": tool_cypher_read,
    "find_entity": tool_find_entity,
    "get_source": tool_get_source,
    "locate": tool_locate,
    "trace_money": tool_trace_money,
    "who_is_responsible": tool_who_is_responsible,
}


def call_tool(name: str, tool_input: dict) -> str:
    try:
        return json.dumps(TOOLS[name](**tool_input), default=str, ensure_ascii=False)
    except Exception as error:  # the agent can recover from a failed call
        return json.dumps({"error": f"{type(error).__name__}: {error}"})


# ---- session loop --------------------------------------------------------


def run(session_id: str, kickoff: dict) -> str:
    """Send one kickoff event and follow the session until its work is done."""
    open_runs: set[str] = set()
    with client.beta.sessions.events.stream(session_id=session_id) as stream:
        client.beta.sessions.events.send(session_id=session_id, events=[kickoff])
        for event in stream:
            match event.type:
                case "agent.message":
                    for block in event.content:
                        if block.type == "text":
                            print(block.text, end="", flush=True)
                case "agent.custom_tool_use":
                    try:
                        client.beta.sessions.events.send(
                            session_id=session_id,
                            events=[{
                                "type": "user.custom_tool_result",
                                "custom_tool_use_id": event.id,
                                "content": [{"type": "text", "text": call_tool(event.name, event.input)}],
                            }],
                        )
                    except anthropic.BadRequestError as error:
                        print(f"\n[answer to {event.name} refused: {error.message}]")
                case "agent.tool_use" | "agent.mcp_tool_use":
                    if event.evaluated_permission == "ask":
                        # Nobody is watching this run, so a call the server could not clear is denied.
                        client.beta.sessions.events.send(
                            session_id=session_id,
                            events=[{"type": "user.tool_confirmation", "tool_use_id": event.id, "result": "deny"}],
                        )
                case "workflow_run.created":
                    open_runs.add(event.workflow_run_id)
                    print(f"\n[workflow run started: {event.name}]")
                case "workflow_run.status_ended":
                    open_runs.discard(event.workflow_run_id)
                    print(f"\n[workflow run ended: {event.result.type}]")
                case "span.outcome_evaluation_end":
                    print(f"\n[grader, iteration {event.iteration}: {event.result}]")
                case "session.error":
                    print(f"\n[session error: {event.error.message}]")
                case "session.status_idle":
                    reason = event.stop_reason.type
                    if reason == "requires_action":
                        continue
                    if reason == "end_turn" and open_runs:
                        continue
                    return reason
                case "session.status_terminated":
                    return "terminated"
    return "stream_closed"


def memory(access_ward_notes: str) -> list[dict]:
    return [
        {"type": "memory_store", "memory_store_id": resource_id("./memory_stores/civic-playbook.yaml"), "access": "read_only"},
        {"type": "memory_store", "memory_store_id": resource_id("./memory_stores/ward-notes.yaml"), "access": access_ward_notes},
    ]


def upload(path: Path, mount_path: str) -> dict:
    with path.open("rb") as f:
        uploaded = client.beta.files.upload(file=f)
    return {"type": "file", "file_id": uploaded.id, "mount_path": mount_path}


def start(agent: str, title: str, resources: list[dict], dollars: int):
    session = client.beta.sessions.create(
        agent=resource_id(f"./agents/{agent}.md"),
        environment_id=resource_id("./environments/civic-cloud.yaml"),
        title=title,
        resources=resources,
        budget={"type": "limit", "max_list_cost": {"amount": str(dollars * 100), "currency": "USD"}},
    )
    print(f"Session {session.id}\nTrace: https://platform.claude.com/workspaces/default/sessions/{session.id}\n")
    return session


def download_outputs(session_id: str, into: Path) -> Path:
    into.mkdir(parents=True, exist_ok=True)
    for attempt in range(3):
        files = client.beta.files.list(scope_id=session_id, betas=["managed-agents-2026-04-01"]).data
        if files:
            break
        time.sleep(2)
    for f in files:
        client.beta.files.download(f.id).write_to_file(into / Path(f.filename).name)
        print(f"saved {into / Path(f.filename).name}")
    return into


# ---- commands ------------------------------------------------------------


def known_entities() -> Path:
    path = HERE / ".entities.jsonl"
    rows = read(
        "MATCH (n) WHERE n:Contractor OR n:Company OR n:Asset OR n:Department OR n:AdminWard OR n:Agency "
        "RETURN n.id AS id, labels(n) AS labels, n.name AS name, n.name_en AS name_en, n.reg_no AS reg_no"
    )
    path.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows) or "{}\n")  # never upload an empty file
    return path


def ingest(paths: list[str]) -> Path:
    resources = [upload(Path(p), f"/corpus/{Path(p).name}") for p in paths]
    resources += [upload(HERE / "schema.md", "/schema.md"), upload(known_entities(), "/entities.jsonl")]
    session = start("ingest-lead", f"Ingest {len(paths)} documents", resources + memory("read_write"), dollars=25)
    reason = run(session.id, {
        "type": "user.define_outcome",
        "description": "Extract, verify and resolve facts from every document under /mnt/session/uploads/corpus/ "
                       "into /mnt/session/outputs/facts.jsonl, with review.jsonl and report.md.",
        "rubric": {"type": "text", "content": (HERE / "rubrics" / "ingest.md").read_text()},
        "max_iterations": 3,
    })
    out = download_outputs(session.id, HERE.parent / "data" / "extracted" / session.id)
    print(f"\nFinished ({reason}). Check quotes and load with: python civic_client.py load {out / 'facts.jsonl'}")
    return out / "facts.jsonl"


def quote_on_page(pdf: Path, page: int, quote: str) -> bool | None:
    """True or False when the page has a text layer; None for scans, which need a human."""
    import pymupdf

    with pymupdf.open(pdf) as doc:
        if not 1 <= page <= len(doc):
            return False
        text = " ".join(doc[page - 1].get_text().split())
    return None if not text else " ".join(quote.split()) in text


def load(facts_path: str, corpus: str) -> tuple[int, int]:
    """Check every quote against its source page, then write the facts that pass to the graph."""
    records = [json.loads(line) for line in Path(facts_path).read_text().splitlines() if line.strip()]
    good, held = [], []
    for r in records:
        known = (r["kind"] == "node" and r.get("label") in LABELS) or (r["kind"] == "edge" and r.get("type") in EDGE_TYPES)
        found = quote_on_page(Path(corpus) / r["source_file"], r["page"], r["quote"]) if known else False
        r["quote_checked"] = {True: "matched", None: "scan_unchecked"}.get(found, "failed")
        (good if known and found is not False else held).append(r)
    Path(facts_path).with_name("held.jsonl").write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in held))

    def provenance(r: dict) -> dict:
        return {**r.get("props", {}), "source_id": "source:" + r["source_file"], "page": r["page"], "quote": r["quote"],
                "confidence": r["confidence"], "tier": r["tier"], "quote_checked": r["quote_checked"]}

    with graph().session() as s:
        for label in LABELS:
            rows = [{"id": r["id"], "props": provenance(r)} for r in good if r["kind"] == "node" and r["label"] == label]
            if rows:
                # MERGE must be confirmed against HydraDB's cypher-compat.md; Neo4j accepts it.
                s.run(f"UNWIND $rows AS row MERGE (n:{label} {{id: row.id}}) SET n += row.props", rows=rows)
        for edge_type in EDGE_TYPES:
            rows = [{"from": r["from"], "to": r["to"], "props": provenance(r)} for r in good if r["kind"] == "edge" and r["type"] == edge_type]
            if rows:
                s.run(f"UNWIND $rows AS row MATCH (a {{id: row.from}}), (b {{id: row.to}}) "
                      f"MERGE (a)-[e:{edge_type}]->(b) SET e += row.props", rows=rows)
    print(f"loaded {len(good)} records; {len(held)} held for review in held.jsonl")
    return len(good), len(held)


def audit(ward: str) -> Path:
    session = start("audit-lead", f"Ward audit {ward}", [upload(HERE / "schema.md", "/schema.md")] + memory("read_write"), dollars=15)
    reason = run(session.id, {
        "type": "user.define_outcome",
        "description": f"Audit public works in ward {ward} from the civic graph and write the ward brief, reviewed case files, "
                       "drafts and gaps file to /mnt/session/outputs/.",
        "rubric": {"type": "text", "content": (HERE / "rubrics" / "ward-audit.md").read_text()},
        "max_iterations": 3,
    })
    out = download_outputs(session.id, HERE.parent / "data" / "audits" / session.id)
    print(f"\nFinished ({reason}). A person reviews these files before anything is published.")
    return out


def ask(question: str) -> None:
    # Residents' messages are untrusted input, so this agent can read the stores but not write them.
    session = start("citizen-desk", question[:60], memory("read_only"), dollars=2)
    run(session.id, {"type": "user.message", "content": [{"type": "text", "text": question}]})
    print()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("ingest").add_argument("paths", nargs="+")
    loader = sub.add_parser("load")
    loader.add_argument("facts")
    loader.add_argument("--corpus", default=str(HERE.parent / "data" / "raw"))
    sub.add_parser("audit").add_argument("ward")
    sub.add_parser("ask").add_argument("question")
    args = parser.parse_args()
    if args.command == "ingest":
        ingest(args.paths)
    elif args.command == "load":
        load(args.facts, args.corpus)
    elif args.command == "audit":
        audit(args.ward)
    else:
        ask(args.question)
