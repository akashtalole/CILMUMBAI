"""Create or update agents and environments in the Claude account from the files in `agents/`.

A local lock file records each resource's id, version and a hash of what was applied, so unchanged agents are
left alone and changed ones are updated (new version) rather than duplicated. The lock is per account and is
not committed.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from hishob.agentkit.definitions import AGENTS_DIR, AgentDef, apply_order, load_agents, load_environment

LOCK = AGENTS_DIR / ".lock.json"
METADATA = {"project": "aamcha-hishob"}


@dataclass(frozen=True)
class Applied:
    key: str
    kind: str  # agent or environment
    id: str
    version: int | None
    action: str  # created, updated, unchanged


def _hash(payload: dict[str, Any]) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()


def read_lock(path: Path = LOCK) -> dict[str, Any]:
    if path.exists():
        data: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
        return data
    return {"agents": {}, "environments": {}}


def agent_payload(agent: AgentDef, lock: dict[str, Any], name_prefix: str) -> dict[str, Any]:
    config = json.loads(json.dumps(agent.config))  # deep copy
    block = config.get("multiagent")
    if block:
        for member in ("subagents", "workflows"):
            entries = (block.get(member) or {}).get("predefined_agents")
            if entries is None:
                continue
            resolved = []
            for entry in entries:
                if isinstance(entry, str) and entry.endswith(".md"):
                    ref = lock["agents"][Path(entry).stem]
                    resolved.append({"type": "agent", "id": ref["id"], "version": ref["version"]})
                else:
                    resolved.append(entry)
            block[member]["predefined_agents"] = resolved
    payload: dict[str, Any] = {
        "name": f"{name_prefix}{config.pop('name')}",
        "model": config.pop("model"),
        "system": agent.system,
        "metadata": {**METADATA, "definition": agent.key},
    }
    payload.update(config)
    return payload


def apply(
    client: Any, directory: Path = AGENTS_DIR, lock_path: Path = LOCK, name_prefix: str = "Hishob dev · "
) -> list[Applied]:
    lock = read_lock(lock_path)
    results: list[Applied] = []

    for env_path in sorted((directory / "environments").glob("*.yaml")):
        key = env_path.stem
        config = load_environment(env_path)
        payload = {"name": f"hishob-dev-{config['name']}", "config": config["config"], "metadata": METADATA}
        digest = _hash(payload)
        known = lock["environments"].get(key)
        if known and known["hash"] == digest:
            results.append(Applied(key, "environment", known["id"], None, "unchanged"))
            continue
        if known:
            raise RuntimeError(f"environment {key} changed; create a new environment file instead of editing it")
        created = client.beta.environments.create(**payload)
        lock["environments"][key] = {"id": created.id, "hash": digest}
        results.append(Applied(key, "environment", created.id, None, "created"))
        _write_lock(lock, lock_path)

    agents = load_agents(directory)
    for key in apply_order(agents):
        payload = agent_payload(agents[key], lock, name_prefix)
        digest = _hash(payload)
        known = lock["agents"].get(key)
        if known and known["hash"] == digest:
            results.append(Applied(key, "agent", known["id"], known["version"], "unchanged"))
            continue
        if known:
            agent = client.beta.agents.update(known["id"], version=known["version"], **payload)
            action = "updated"
        else:
            agent = client.beta.agents.create(**payload)
            action = "created"
        lock["agents"][key] = {"id": agent.id, "version": agent.version, "hash": digest}
        results.append(Applied(key, "agent", agent.id, agent.version, action))
        _write_lock(lock, lock_path)
    return results


def _write_lock(lock: dict[str, Any], path: Path) -> None:
    path.write_text(json.dumps(lock, indent=2, sort_keys=True) + "\n", encoding="utf-8")
