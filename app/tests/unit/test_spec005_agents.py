"""SPEC-005: agent definitions (AC3) and the session loop (AC2, AC8)."""

from __future__ import annotations

import json
from pathlib import Path

from hishob.agentkit.definitions import AGENTS_DIR, apply_order, load_agents, load_environment
from hishob.agentkit.provision import agent_payload, apply
from hishob.agentkit.session import follow
from tests.fakes import FakeClient, event, idle

INTAKE = ["ingest-lead", "doc-extractor", "fact-verifier", "entity-resolver"]
KICKOFF = {"type": "user.message", "content": [{"type": "text", "text": "go"}]}


# AC3 · R3 -------------------------------------------------------------------------------------------------------


def _enabled_tools(config: dict) -> set[str]:
    names = {"bash", "read", "write", "edit", "glob", "grep", "web_fetch", "web_search"}
    enabled = set()
    for tool in config.get("tools", []):
        if tool["type"] != "agent_toolset_20260401":
            continue
        default = (tool.get("default_config") or {}).get("enabled", True)
        overrides = {c["name"]: c.get("enabled", default) for c in tool.get("configs", [])}
        enabled |= {n for n in names if overrides.get(n, default)}
    return enabled


def test_spec005_ac3_no_intake_agent_can_reach_the_web_or_write_outside_its_sandbox() -> None:
    agents = load_agents()
    for key in INTAKE:
        config = agents[key].config
        assert not _enabled_tools(config) & {"web_fetch", "web_search"}, key
        assert [t for t in config.get("tools", []) if t["type"] != "agent_toolset_20260401"] == [], key
        assert "mcp_servers" not in config, key


def test_spec005_ac3_the_environment_allows_no_outbound_hosts() -> None:
    networking = load_environment(AGENTS_DIR / "environments" / "civic-cloud.yaml")["config"]["networking"]
    assert networking == {"type": "limited", "allow_package_managers": False, "allow_mcp_servers": False}


def test_spec005_readers_use_the_smallest_capable_models() -> None:
    agents = load_agents()
    assert agents["doc-extractor"].config["model"] == "claude-haiku-5-5"
    assert agents["ingest-lead"].config["model"] == "claude-opus-5-5"


def test_spec005_roster_references_resolve_leaves_first() -> None:
    order = apply_order(load_agents())
    assert order.index("doc-extractor") < order.index("ingest-lead")
    assert order.index("fact-verifier") < order.index("ingest-lead")


def test_spec005_provisioning_creates_once_and_resolves_roster_ids(tmp_path: Path) -> None:
    created: list[dict] = []

    class Agents:
        def create(self, **payload):  # type: ignore[no-untyped-def]
            created.append(payload)
            from types import SimpleNamespace

            return SimpleNamespace(id=f"agent_{len(created)}", version=1)

    class Environments:
        def create(self, **payload):  # type: ignore[no-untyped-def]
            from types import SimpleNamespace

            return SimpleNamespace(id="env_1")

    from types import SimpleNamespace

    client = SimpleNamespace(beta=SimpleNamespace(agents=Agents(), environments=Environments()))
    lock = tmp_path / "lock.json"
    first = apply(client, AGENTS_DIR, lock)
    assert {r.action for r in first} == {"created"}
    lead = next(p for p in created if p["name"].endswith("Ingest lead"))
    roster = lead["multiagent"]["subagents"]["predefined_agents"]
    assert all(entry["type"] == "agent" and entry["id"].startswith("agent_") for entry in roster)
    second = apply(client, AGENTS_DIR, lock)
    assert {r.action for r in second} == {"unchanged"}
    assert json.loads(lock.read_text())["environments"]["civic-cloud"]["id"] == "env_1"


def test_spec005_payload_carries_the_prompt_and_project_metadata() -> None:
    lock = {"agents": {k: {"id": f"agent_{k}", "version": 2} for k in INTAKE}, "environments": {}}
    payload = agent_payload(load_agents()["ingest-lead"], lock, "Hishob dev · ")
    assert payload["name"] == "Hishob dev · Ingest lead"
    assert payload["system"].startswith("You run document intake")
    assert payload["metadata"] == {"project": "aamcha-hishob", "definition": "ingest-lead"}


# AC2 · R2: threads are recorded per agent -----------------------------------------------------------------------


def test_spec005_ac2_threads_record_which_agent_ran() -> None:
    script = [
        event("session.thread_created", agent_name="Hishob dev · Document extractor", session_thread_id="sthr_1"),
        event("session.thread_created", agent_name="Hishob dev · Fact verifier", session_thread_id="sthr_2"),
        idle(),
    ]
    outcome = follow(FakeClient(script), "sesn_test", KICKOFF)
    assert outcome.finished
    assert [t["agent"].split(" · ")[1] for t in outcome.threads] == ["Document extractor", "Fact verifier"]


# AC8 · R8 -------------------------------------------------------------------------------------------------------


def test_spec005_ac8_reaching_the_cap_ends_the_follow_without_retrying() -> None:
    outcome = follow(FakeClient([idle("budget_reached")]), "sesn_test", KICKOFF)
    assert outcome.stop_reason == "budget_reached" and not outcome.finished


# The loop's other duties -----------------------------------------------------------------------------------------


def test_custom_tools_are_answered_and_paused_calls_are_denied() -> None:
    script = [
        event("agent.custom_tool_use", id="sevt_1", name="find_entity", input={"text": "S.V. Road"}),
        event("agent.tool_use", id="sevt_2", evaluated_permission="ask"),
        idle(),
    ]
    client = FakeClient(script)
    outcome = follow(client, "sesn_test", KICKOFF, on_tool=lambda name, args: f"{name}:{args['text']}")
    sent = {e["type"]: e for e in client.sent}
    assert sent["user.custom_tool_result"]["content"][0]["text"] == "find_entity:S.V. Road"
    assert sent["user.tool_confirmation"]["result"] == "deny" and outcome.denied_tool_calls == 1


def test_an_idle_with_a_workflow_run_open_is_not_the_end() -> None:
    script = [
        event("workflow_run.created", workflow_run_id="wrun_1"),
        idle(),
        event("workflow_run.status_ended", workflow_run_id="wrun_1", result="completed"),
        event("session.thread_created", agent_name="late", session_thread_id="sthr_9"),
        idle(),
    ]
    outcome = follow(FakeClient(script), "sesn_test", KICKOFF)
    assert outcome.finished and outcome.threads[-1]["agent"] == "late"


def test_tool_handler_failures_go_back_to_the_agent() -> None:
    def broken(name: str, args: dict) -> str:
        raise ValueError("graph down")

    client = FakeClient([event("agent.custom_tool_use", id="sevt_1", name="locate", input={}), idle()])
    follow(client, "sesn_test", KICKOFF, on_tool=broken)
    assert "graph down" in client.sent[1]["content"][0]["text"]
