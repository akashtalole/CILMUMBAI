"""Reading a session's files: all pages, the newest file per name, and retrying a file that is listed before it can
be read. Found by the first live SPEC-012 run: ten documents wrote 37 files and only the first 20 were read."""

from __future__ import annotations

from types import SimpleNamespace as NS
from typing import Any

import pytest

from hishob.agentkit.session import newest_by_name, read_file, session_files


class Page:
    def __init__(self, items: list[Any]) -> None:
        self.items = items
        self.data = items[:20]  # a first page of twenty, as the API returns

    def __iter__(self) -> Any:  # like the SDK's page: iterating continues onto the next pages
        return iter(self.items)


def file(name: str, minute: int, ident: str | None = None) -> NS:
    return NS(id=ident or f"file_{name}_{minute}", filename=name, created_at=f"2026-11-17T08:{minute:02d}:00+00:00")


def test_every_page_of_the_listing_is_read_oldest_first() -> None:
    files = [file(f"doc-{n}.jsonl", 59 - n) for n in range(37)]  # newest first, 37 of them
    client = NS(beta=NS(files=NS(list=lambda scope_id, betas: Page(files))))
    got = session_files(client, "sesn_1")
    assert len(got) == 37 and got[0].filename == "doc-36.jsonl" and got[-1].filename == "doc-0.jsonl"


def test_a_page_object_without_paging_falls_back_to_its_data() -> None:
    client = NS(beta=NS(files=NS(list=lambda scope_id, betas: NS(data=[file("a", 1)]))))
    assert [f.filename for f in session_files(client, "sesn_1")] == ["a"]


def test_the_last_written_file_of_a_name_wins() -> None:
    files = [
        file("facts.jsonl", 1, "draft"),
        file("outputs/report.md", 2),
        file("/mnt/session/outputs/facts.jsonl", 3, "final"),
    ]
    kept = newest_by_name(files, ("facts.jsonl", "report.md"))
    assert sorted(f.id for f in kept) == ["file_outputs/report.md_2", "final"]


class NotFoundError(Exception):
    pass


def test_a_file_that_is_listed_before_it_is_readable_is_retried() -> None:
    calls: list[str] = []

    def download(file_id: str) -> NS:
        calls.append(file_id)
        if len(calls) < 3:
            raise NotFoundError("not yet")
        return NS(read=lambda: b"content")

    sleeps: list[float] = []
    client = NS(beta=NS(files=NS(download=download)))
    assert read_file(client, "f1", sleeps.append) == b"content" and len(calls) == 3 and sleeps == [2, 4]


def test_other_errors_and_persistent_not_found_are_raised() -> None:
    def broken(file_id: str) -> NS:
        raise ValueError("bad")

    with pytest.raises(ValueError):
        read_file(NS(beta=NS(files=NS(download=broken))), "f", lambda s: None)

    def gone(file_id: str) -> NS:
        raise NotFoundError("never")

    with pytest.raises(NotFoundError):
        read_file(NS(beta=NS(files=NS(download=gone))), "f", lambda s: None, attempts=3)
