"""W1: ingest, load, review if many facts were held, audit each ward, release, publish (SPEC-009).

LangGraph decides the order and holds the state; Postgres keeps it across restarts. Steps with side effects are
behind `Steps`, so tests stub them. Two gates pause for people; only a reviewer may resume them, and every
decision is recorded with its reason (R6; constitution C6).
"""

from __future__ import annotations

import json
import operator
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from functools import partial
from typing import Annotated, Any, Protocol, TypedDict

import psycopg
from langgraph.checkpoint.postgres import PostgresSaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, Send, interrupt
from psycopg.rows import dict_row

from hishob.api.tiers import allows

GATES = {"review_facts": ("continue", "stop"), "release": ("approve", "hold")}


class Steps(Protocol):
    def intake(self, hashes: list[str], run_id: str) -> dict[str, Any]:
        """Read and load documents. Returns {"run_id", "accepted", "held"}."""

    def audit(self, ward: str, run_id: str) -> dict[str, Any]:
        """Audit one ward. Returns {"ward", "run_id", "files": [keys in the data store]}."""

    def publish(self, audit: dict[str, Any]) -> list[str]:
        """Copy one approved ward's outputs to the public location. Returns the public keys."""


class W1State(TypedDict, total=False):
    thread: str
    hashes: list[str]
    wards: list[str]
    threshold: float
    loaded: int
    held: int
    audits: Annotated[list[dict[str, Any]], operator.add]
    released: list[str]
    published: Annotated[list[str], operator.add]
    log: Annotated[list[str], operator.add]


class GateError(PermissionError):
    pass


@dataclass
class Status:
    thread: str
    log: list[str] = field(default_factory=list)
    waiting: dict[str, Any] | None = None  # {"gate": ..., ...payload}
    finished: bool = False
    published: list[str] = field(default_factory=list)


def build(steps: Steps, checkpointer: Any) -> Any:
    def once(state: W1State, step: str, fn: Callable[[], Any]) -> Any:
        return _once(state["thread"], step, fn)

    def intake(state: W1State) -> dict[str, Any]:
        result = once(state, "intake", lambda: steps.intake(state["hashes"], f"{state['thread']}-intake"))
        return {
            "loaded": result["accepted"],
            "held": result["held"],
            "log": [f"intake: {result['accepted']} facts loaded, {result['held']} held"],
        }

    def review_facts(state: W1State) -> Command[Any]:
        decision = interrupt(
            {
                "gate": "review_facts",
                "loaded": state["loaded"],
                "held": state["held"],
                "question": "Many facts were held. Continue to the audit with what loaded?",
            }
        )
        if decision == "continue":
            return Command(update={"log": ["review_facts: continue"]}, goto=_audits(state))
        return Command(update={"log": ["review_facts: stop"]}, goto=END)

    def audit(branch: Any) -> dict[str, Any]:  # receives a Send payload, not the whole state
        ward = branch["ward"]
        step = f"audit:{ward}"
        result = _once(branch["thread"], step, lambda: steps.audit(ward, f"{branch['thread']}-audit-{_slug(ward)}"))
        note = f" ({result['status']}, {len(result.get('held') or {})} held)" if "status" in result else ""
        return {"audits": [result], "log": [f"audit: {ward}{note}"]}

    def release(state: W1State) -> dict[str, Any]:
        wards = sorted(a["ward"] for a in state.get("audits", []))
        gate: dict[str, Any] = {
            "gate": "release",
            "wards": wards,
            "question": "Review each ward's outputs. Which may be published?",
        }
        staged = {a["ward"]: a["files"] for a in state.get("audits", []) if "status" in a}
        if staged:  # what the reviewer is releasing, and what stays held whatever they decide (SPEC-011/R4, R8)
            gate["staged"] = staged
            gate["held"] = {a["ward"]: a.get("held") or {} for a in state.get("audits", []) if "status" in a}
        decision = interrupt(gate)
        if decision == "approve":
            released = wards
        elif isinstance(decision, list):
            released = [w for w in wards if w in decision]
        else:
            released = []
        return {"released": released, "log": [f"release: {', '.join(released) or 'nothing'}"]}

    def publish(state: W1State) -> dict[str, Any]:
        keys: list[str] = []
        for result in sorted(state.get("audits", []), key=lambda a: a["ward"]):
            if result["ward"] in state.get("released", []):
                keys += _once(state["thread"], f"publish:{result['ward']}", partial(steps.publish, result))
        return {"published": keys, "log": [f"publish: {len(keys)} files"]}

    def after_intake(state: W1State) -> Any:
        total = state["loaded"] + state["held"]
        if total == 0:
            return END
        if state["held"] / total > state.get("threshold", 0.2):
            return "review_facts"
        return _audits(state)

    graph = StateGraph(W1State)
    graph.add_node("intake", intake)
    graph.add_node("review_facts", review_facts, destinations=("audit", END))
    graph.add_node("audit", audit)  # type: ignore[arg-type]  # Send payloads are typed apart from the state
    graph.add_node("release", release)
    graph.add_node("publish", publish)
    graph.add_edge(START, "intake")
    graph.add_conditional_edges("intake", after_intake, ["review_facts", "audit", END])
    graph.add_edge("audit", "release")
    graph.add_edge("release", "publish")
    graph.add_edge("publish", END)
    return graph.compile(checkpointer=checkpointer)


def _audits(state: W1State) -> list[Send]:
    return [Send("audit", {"ward": ward, "thread": state["thread"]}) for ward in state["wards"]]


def _slug(text: str) -> str:
    return "".join(c if c.isalnum() else "-" for c in text.lower()).strip("-")


# ---- publishing (R5, R7) --------------------------------------------------------------------------------------


def publish_outputs(data: Any, public: Any, audit: dict[str, Any]) -> list[str]:
    """Copy one released ward's outputs to the public store. Safe to repeat: a file already published with the
    same bytes is skipped, so a publish interrupted part-way can simply run again."""
    keys = []
    prefix = f"staging/{audit['run_id']}/"
    for key in sorted(audit["files"]):
        body = data.get(key)
        relative = key[len(prefix) :] if key.startswith(prefix) else key.rsplit("/", 1)[-1]
        target = f"published/{_slug(audit['ward'])}/{audit['run_id']}/{relative}"
        if not public.put_new(target, body, "application/octet-stream") and public.get(target) != body:
            raise RuntimeError(f"{target} already published with different content")
        keys.append(target)
    return keys


# ---- idempotent steps (R7) -------------------------------------------------------------------------------------

_STEP_CONN: dict[str, str] = {}


def _once(thread: str, step: str, fn: Callable[[], Any]) -> Any:
    """Run a side-effecting step once per thread. A repeat after a restart returns the stored result."""
    with psycopg.connect(_STEP_CONN["url"], autocommit=True) as conn:
        row = conn.execute(
            "SELECT result FROM flow.steps WHERE thread_id = %s AND step = %s", (thread, step)
        ).fetchone()
        if row:
            return row[0]
        result = fn()
        conn.execute(
            "INSERT INTO flow.steps (thread_id, step, result) VALUES (%s, %s, %s) ON CONFLICT DO NOTHING",
            (thread, step, json.dumps(result)),
        )
        return result


# ---- engine -----------------------------------------------------------------------------------------------------


class Engine:
    """Start, inspect and resume W1 runs. State lives in Postgres, so any process can pick a run up."""

    def __init__(self, database_url: str, steps: Steps, threshold: float = 0.2) -> None:
        self.database_url = database_url
        self.steps = steps
        self.threshold = threshold
        _STEP_CONN["url"] = database_url

    @contextmanager
    def _app(self) -> Iterator[Any]:
        with psycopg.connect(
            self.database_url, autocommit=True, row_factory=dict_row, options="-c search_path=flow"
        ) as conn:
            saver = PostgresSaver(conn)
            saver.setup()
            yield build(self.steps, saver)

    def start(self, thread: str, hashes: list[str], wards: list[str]) -> Status:
        with self._app() as app:
            config = {"configurable": {"thread_id": thread}}
            if app.get_state(config).values:
                raise ValueError(f"thread {thread} already exists")
            app.invoke({"thread": thread, "hashes": hashes, "wards": wards, "threshold": self.threshold}, config)
            return _status(app, thread)

    def status(self, thread: str) -> Status:
        with self._app() as app:
            return _status(app, thread)

    def resume(self, thread: str, decision: Any, *, reason: str, account: str, tier: str) -> Status:
        if not allows(tier, "reviewer"):
            raise GateError("only a reviewer may resume a run from a gate")
        if not reason.strip():
            raise ValueError("a decision needs a reason")
        with self._app() as app:
            current = _status(app, thread)
            if current.waiting is None:
                raise ValueError(f"thread {thread} is not waiting at a gate")
            gate = current.waiting["gate"]
            allowed = GATES[gate]
            if not (decision in allowed or (gate == "release" and isinstance(decision, list))):
                raise ValueError(
                    f"{gate} accepts {', '.join(allowed)}" + (" or a list of wards" if gate == "release" else "")
                )
            with psycopg.connect(self.database_url, autocommit=True) as conn:
                conn.execute(
                    "INSERT INTO flow.decisions (thread_id, gate, decision, reason, account_id)"
                    " VALUES (%s, %s, %s, %s, %s)",
                    (thread, gate, json.dumps(decision), reason, account),
                )
            app.invoke(Command(resume=decision), {"configurable": {"thread_id": thread}})
            return _status(app, thread)

    def retry(self, thread: str) -> Status:
        """Run again a step that failed (for example after a crash). Completed steps are not repeated."""
        with self._app() as app:
            app.invoke(None, {"configurable": {"thread_id": thread}})
            return _status(app, thread)


def handle_message(engine: Engine, body: dict[str, Any]) -> Status:
    """Start a run from a queue message: {"workflow": "W1", "thread": ..., "hashes": [...], "wards": [...]} (R3)."""
    if body.get("workflow") != "W1":
        raise ValueError(f"unknown workflow {body.get('workflow')!r}")
    return engine.start(str(body["thread"]), list(body["hashes"]), list(body["wards"]))


def consume(sqs: Any, queue_url: str, engine: Engine, max_messages: int = 10) -> list[Status]:
    """Take up to `max_messages` from the queue and start a run for each. A message is deleted once its run has
    started; one that fails stays on the queue and, after its retries, goes to the dead-letter queue."""
    started = []
    reply = sqs.receive_message(QueueUrl=queue_url, MaxNumberOfMessages=max_messages, WaitTimeSeconds=1)
    for message in reply.get("Messages", []):
        started.append(handle_message(engine, json.loads(message["Body"])))
        sqs.delete_message(QueueUrl=queue_url, ReceiptHandle=message["ReceiptHandle"])
    return started


def _status(app: Any, thread: str) -> Status:
    snapshot = app.get_state({"configurable": {"thread_id": thread}})
    values = snapshot.values or {}
    waiting = [i.value for task in snapshot.tasks for i in task.interrupts]
    return Status(
        thread=thread,
        log=list(values.get("log", [])),
        waiting=waiting[0] if waiting else None,
        finished=bool(values) and not snapshot.next,
        published=list(values.get("published", [])),
    )
