"""Follow one Managed Agents session to the end of its work (SPEC-005/R2, R8).

The loop answers custom tool calls, denies calls that pause for approval (nobody is watching), tracks
workflow runs, records which agent ran in each thread, and ends at an idle that means the work is done.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

ToolHandler = Callable[[str, dict[str, Any]], str]


@dataclass
class SessionOutcome:
    stop_reason: str  # end_turn, budget_reached, retries_exhausted, terminated, stream_closed
    threads: list[dict[str, str]] = field(default_factory=list)  # {agent, thread_id}
    grader_results: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    denied_tool_calls: int = 0
    events: int = 0

    @property
    def finished(self) -> bool:
        return self.stop_reason == "end_turn"


def follow(
    client: Any,
    session_id: str,
    kickoff: dict[str, Any],
    *,
    on_tool: ToolHandler | None = None,
    on_text: Callable[[str], None] | None = None,
) -> SessionOutcome:
    outcome = SessionOutcome("stream_closed")
    open_runs: set[str] = set()
    with client.beta.sessions.events.stream(session_id=session_id) as stream:
        client.beta.sessions.events.send(session_id=session_id, events=[kickoff])
        for event in stream:
            outcome.events += 1
            kind = event.type
            if kind == "agent.message" and on_text:
                for block in event.content:
                    if getattr(block, "type", None) == "text":
                        on_text(block.text)
            elif kind == "agent.custom_tool_use":
                answer = _answer(on_tool, event.name, event.input)
                client.beta.sessions.events.send(
                    session_id=session_id,
                    events=[
                        {
                            "type": "user.custom_tool_result",
                            "custom_tool_use_id": event.id,
                            "content": [{"type": "text", "text": answer}],
                        }
                    ],
                )
            elif (
                kind in {"agent.tool_use", "agent.mcp_tool_use"}
                and getattr(event, "evaluated_permission", None) == "ask"
            ):
                outcome.denied_tool_calls += 1
                client.beta.sessions.events.send(
                    session_id=session_id,
                    events=[{"type": "user.tool_confirmation", "tool_use_id": event.id, "result": "deny"}],
                )
            elif kind == "session.thread_created":
                outcome.threads.append({"agent": event.agent_name, "thread_id": event.session_thread_id})
            elif kind == "workflow_run.created":
                open_runs.add(event.workflow_run_id)
            elif kind == "workflow_run.status_ended":
                open_runs.discard(event.workflow_run_id)
            elif kind == "span.outcome_evaluation_end":
                outcome.grader_results.append(str(event.result))
            elif kind == "session.error":
                outcome.errors.append(str(getattr(getattr(event, "error", None), "message", event)))
            elif kind == "session.status_idle":
                reason = event.stop_reason.type
                if reason == "requires_action" or (reason == "end_turn" and open_runs):
                    continue
                outcome.stop_reason = reason
                return outcome
            elif kind == "session.status_terminated":
                outcome.stop_reason = "terminated"
                return outcome
    return outcome


def _answer(handler: ToolHandler | None, name: str, arguments: dict[str, Any]) -> str:
    if handler is None:
        return json.dumps({"error": f"no handler for tool {name}"})
    try:
        return handler(name, arguments)
    except Exception as error:  # the agent can recover from a failed tool call
        return json.dumps({"error": f"{type(error).__name__}: {error}"})
