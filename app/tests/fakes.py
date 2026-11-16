"""A scripted stand-in for the parts of the Claude client the agent kit uses."""

from __future__ import annotations

from types import SimpleNamespace as NS
from typing import Any


def event(kind: str, **fields: Any) -> NS:
    return NS(type=kind, **fields)


def idle(reason: str = "end_turn") -> NS:
    return event("session.status_idle", stop_reason=NS(type=reason))


class _Stream:
    def __init__(self, events: list[NS]) -> None:
        self.events = events

    def __enter__(self) -> list[NS]:
        return self.events

    def __exit__(self, *exc: object) -> None:
        return None


class _Events:
    def __init__(self, script: list[NS]) -> None:
        self.script = script
        self.sent: list[dict[str, Any]] = []

    def stream(self, session_id: str) -> _Stream:
        return _Stream(self.script)

    def send(self, session_id: str, events: list[dict[str, Any]]) -> None:
        self.sent.extend(events)


class _Download:
    def __init__(self, data: bytes) -> None:
        self.data = data

    def read(self) -> bytes:
        return self.data


class _Files:
    def __init__(self, outputs: dict[str, bytes]) -> None:
        self.outputs = outputs
        self.uploaded: list[tuple[str, bytes, str]] = []

    def upload(self, file: tuple[str, bytes, str]) -> NS:
        self.uploaded.append(file)
        return NS(id=f"file_{len(self.uploaded)}")

    def list(self, scope_id: str, betas: list[str]) -> NS:
        return NS(data=[NS(id=f"out_{name}", filename=name) for name in self.outputs])

    def download(self, file_id: str) -> _Download:
        return _Download(self.outputs[file_id.removeprefix("out_")])


class _Sessions:
    def __init__(self, script: list[NS], cost_cents: int | None) -> None:
        self.events = _Events(script)
        self.created: list[dict[str, Any]] = []
        self.cost_cents = cost_cents

    def create(self, **kwargs: Any) -> NS:
        self.created.append(kwargs)
        return NS(id="sesn_test")

    def retrieve(self, session_id: str) -> NS:
        cost = None if self.cost_cents is None else NS(amount=str(self.cost_cents), currency="USD")
        return NS(id=session_id, usage=NS(list_cost=cost))


class FakeClient:
    def __init__(self, script: list[NS], outputs: dict[str, bytes] | None = None, cost_cents: int | None = 0) -> None:
        self.beta = NS(sessions=_Sessions(script, cost_cents), files=_Files(outputs or {}))

    @property
    def sent(self) -> list[dict[str, Any]]:
        return self.beta.sessions.events.sent
