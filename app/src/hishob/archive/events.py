"""Where archive events go."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Protocol


class EventSink(Protocol):
    def emit(self, event: dict[str, Any]) -> None: ...


class MemorySink:
    def __init__(self) -> None:
        self.events: list[dict[str, Any]] = []

    def emit(self, event: dict[str, Any]) -> None:
        self.events.append(event)


class FileSink:
    """Appends one JSON line per event; for laptops."""

    def __init__(self, path: Path) -> None:
        self.path = path

    def emit(self, event: dict[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(event, ensure_ascii=False) + "\n")


class SqsSink:
    def __init__(self, client: Any, queue_url: str) -> None:
        self.client = client
        self.queue_url = queue_url

    def emit(self, event: dict[str, Any]) -> None:
        self.client.send_message(QueueUrl=self.queue_url, MessageBody=json.dumps(event, ensure_ascii=False))
