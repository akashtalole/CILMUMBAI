"""Read agent and environment definitions: Markdown with YAML front matter (config) and a body (system prompt)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

AGENTS_DIR = Path(__file__).resolve().parents[3] / "agents"


@dataclass(frozen=True)
class AgentDef:
    key: str  # file stem, e.g. "doc-extractor"
    config: dict[str, Any]
    system: str

    @property
    def references(self) -> list[str]:
        """Keys of other agents this one lists in its multi-agent roster or workflows."""
        found: list[str] = []
        block = self.config.get("multiagent") or {}
        for member in ("subagents", "workflows"):
            for entry in (block.get(member) or {}).get("predefined_agents") or []:
                if isinstance(entry, str) and entry.endswith(".md"):
                    key = Path(entry).stem
                    if key not in found:
                        found.append(key)
        return found


def load_agent(path: Path) -> AgentDef:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        raise ValueError(f"{path} has no front matter")
    _, front, body = text.split("---\n", 2)
    config = yaml.safe_load(front) or {}
    return AgentDef(path.stem, config, body.strip() + "\n")


def load_agents(directory: Path = AGENTS_DIR) -> dict[str, AgentDef]:
    return {p.stem: load_agent(p) for p in sorted(directory.glob("*.md"))}


def load_environment(path: Path) -> dict[str, Any]:
    data: dict[str, Any] = yaml.safe_load(path.read_text(encoding="utf-8"))
    return data


def apply_order(agents: dict[str, AgentDef]) -> list[str]:
    """Agents with no references first, so every reference resolves to an existing id."""
    order: list[str] = []

    def visit(key: str, trail: tuple[str, ...]) -> None:
        if key in order:
            return
        if key in trail:
            raise ValueError(f"agents reference each other in a loop: {' -> '.join((*trail, key))}")
        for ref in agents[key].references:
            if ref not in agents:
                raise ValueError(f"{key} references {ref}.md, which does not exist")
            visit(ref, (*trail, key))
        order.append(key)

    for key in sorted(agents):
        visit(key, ())
    return order
