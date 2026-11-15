"""LangGraph pipeline around the Managed Agents desks.

LangGraph owns the order of work, the gates and the pauses for people. Each
agentic step is one Managed Agents session started through civic_client.

    intake -> check quotes and load -> [review facts] -> audit each ward -> release -> publish

    python orchestrator.py run --thread batch-1 --ward "K/West" --ward "H/West" ../data/raw/*.pdf
    python orchestrator.py status --thread batch-1
    python orchestrator.py resume --thread batch-1 --answer approve

State is checkpointed to SQLite after every step, so a run that is waiting for a
reviewer survives a restart and can be resumed days later. Add --dry-run to walk
the pipeline with stand-in steps and no API calls.
"""

from __future__ import annotations

import argparse
import operator
import os
import shutil
from pathlib import Path
from typing import Annotated, TypedDict

from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, Send, interrupt

HERE = Path(__file__).parent
DATA = HERE.parent / "data"
HELD_SHARE_NEEDING_REVIEW = 0.2


class Pipeline(TypedDict, total=False):
    paths: list[str]
    corpus: str
    wards: list[str]
    facts_path: str
    loaded: int
    held: int
    audits: Annotated[list[dict], operator.add]  # one entry per ward, merged from parallel branches
    released: list[str]
    log: Annotated[list[str], operator.add]


def dry_run() -> bool:
    return os.environ.get("CIVIC_DRY_RUN") == "1"


# ---- steps ---------------------------------------------------------------


def intake(state: Pipeline) -> dict:
    """Intake desk: one Managed Agents session reads, verifies and resolves the batch."""
    if dry_run():
        facts = DATA / "extracted" / "dry-run" / "facts.jsonl"
        facts.parent.mkdir(parents=True, exist_ok=True)
        facts.write_text("")
    else:
        import civic_client

        facts = civic_client.ingest(state["paths"])
    return {"facts_path": str(facts), "log": [f"intake: {len(state['paths'])} documents"]}


def check_and_load(state: Pipeline) -> dict:
    """Code, not a model: confirm each quote is on its page, then write to the graph."""
    if dry_run():
        loaded, held = 70, 30
    else:
        import civic_client

        loaded, held = civic_client.load(state["facts_path"], state["corpus"])
    return {"loaded": loaded, "held": held, "log": [f"load: {loaded} loaded, {held} held"]}


def review_facts(state: Pipeline) -> Command:
    """Pause for a person when too many facts failed the quote check."""
    answer = interrupt({
        "question": "A large share of facts failed the quote check. Continue to audit with what loaded?",
        "loaded": state["loaded"],
        "held": state["held"],
        "held_file": str(Path(state["facts_path"]).with_name("held.jsonl")),
        "answers": ["continue", "stop"],
    })
    if answer == "continue":
        return Command(update={"log": ["review: continue"]}, goto=audit_each_ward(state))
    return Command(update={"log": ["review: stopped"]}, goto=END)


def audit(branch: dict) -> dict:
    """Audit desk: one Managed Agents session per ward. Branches run in parallel."""
    ward = branch["ward"]
    if dry_run():
        out = DATA / "audits" / ("dry-run-" + ward.replace("/", "-"))
        out.mkdir(parents=True, exist_ok=True)
        (out / "ward-brief.md").write_text(f"# {ward}\n")
    else:
        import civic_client

        out = civic_client.audit(ward)
    return {"audits": [{"ward": ward, "dir": str(out)}], "log": [f"audit: {ward}"]}


def release(state: Pipeline) -> dict:
    """Pause for the editor or lawyer. Nothing reaches the public without this answer."""
    answer = interrupt({
        "question": "Review each ward's brief, case files and challenge reviews. Which wards may be published?",
        "audits": state["audits"],
        "answers": ["approve", "hold", "a list of ward codes"],
    })
    wards = [a["ward"] for a in state["audits"]]
    if answer == "approve":
        released = wards
    elif isinstance(answer, list):
        released = [w for w in wards if w in answer]
    else:
        released = []
    return {"released": released, "log": [f"release: {released or 'held'}"]}


def publish(state: Pipeline) -> dict:
    """Copy the approved wards' files to the folder the public site serves."""
    for entry in state["audits"]:
        if entry["ward"] in state["released"]:
            shutil.copytree(entry["dir"], DATA / "published" / entry["ward"].replace("/", "-"), dirs_exist_ok=True)
    return {"log": [f"publish: {len(state['released'])} wards"]}


# ---- routing -------------------------------------------------------------


def audit_each_ward(state: Pipeline) -> list[Send]:
    return [Send("audit", {"ward": ward}) for ward in state["wards"]]


def after_load(state: Pipeline):
    total = state["loaded"] + state["held"]
    if total == 0:
        return END
    if state["held"] / total > HELD_SHARE_NEEDING_REVIEW:
        return "review_facts"
    return audit_each_ward(state)


def build(checkpointer):
    graph = StateGraph(Pipeline)
    graph.add_node("intake", intake)
    graph.add_node("check_and_load", check_and_load)
    graph.add_node("review_facts", review_facts, destinations=("audit", END))
    graph.add_node("audit", audit)
    graph.add_node("release", release)
    graph.add_node("publish", publish)
    graph.add_edge(START, "intake")
    graph.add_edge("intake", "check_and_load")
    graph.add_conditional_edges("check_and_load", after_load, ["review_facts", "audit", END])
    graph.add_edge("audit", "release")
    graph.add_edge("release", "publish")
    graph.add_edge("publish", END)
    return graph.compile(checkpointer=checkpointer)


# ---- command line --------------------------------------------------------


def report(app, config) -> None:
    snapshot = app.get_state(config)
    for line in snapshot.values.get("log", []):
        print(" ", line)
    waiting = [i.value for task in snapshot.tasks for i in task.interrupts]
    if waiting:
        for payload in waiting:
            print("\nWaiting for a person:", payload["question"])
            for key, value in payload.items():
                if key != "question":
                    print(f"  {key}: {value}")
    elif not snapshot.next:
        print("\nPipeline finished.")
    else:
        print("\nNext step:", ", ".join(snapshot.next))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--dry-run", action="store_true")
    sub = parser.add_subparsers(dest="command", required=True)
    runner = sub.add_parser("run")
    runner.add_argument("--thread", required=True)
    runner.add_argument("--ward", action="append", required=True)
    runner.add_argument("--corpus", default=str(DATA / "raw"))
    runner.add_argument("paths", nargs="+")
    resumer = sub.add_parser("resume")
    resumer.add_argument("--thread", required=True)
    resumer.add_argument("--answer", required=True, help="continue, stop, approve, hold, or ward codes separated by commas")
    sub.add_parser("status").add_argument("--thread", required=True)
    args = parser.parse_args()
    if args.dry_run:
        os.environ["CIVIC_DRY_RUN"] = "1"

    with SqliteSaver.from_conn_string(str(HERE / ".orchestrator.sqlite")) as saver:
        app = build(saver)
        config = {"configurable": {"thread_id": args.thread}}
        if args.command == "run":
            app.invoke({"paths": args.paths, "corpus": args.corpus, "wards": args.ward}, config)
        elif args.command == "resume":
            answer = args.answer.split(",") if "," in args.answer else args.answer
            app.invoke(Command(resume=answer), config)
        report(app, config)
