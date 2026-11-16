"""The archive: one way in for every source document (SPEC-001)."""

from __future__ import annotations

import hashlib
import io
import re
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import BinaryIO
from urllib.parse import urlsplit

from hishob.archive import media, pages
from hishob.archive.events import EventSink
from hishob.archive.fetch import Fetcher, FetchFailure
from hishob.archive.registry import DocumentRow, FailureRow, OriginRow, PageRow, Registry
from hishob.archive.scripts import detect_scripts
from hishob.archive.storage import ObjectStore

PUBLISHER = re.compile(r"^[a-z0-9][a-z0-9-]{1,40}$")
# Opaque account ids only. No '@' (emails) and not all digits (phone numbers): SPEC-001/R8.
ACCOUNT_ID = re.compile(r"^(?!\d+$)[A-Za-z0-9_-]{6,64}$")
CONTRIBUTOR_PUBLISHER = "contributor"
CONTRIBUTOR_LICENCE = "contributor-upload"


class NotADocumentError(ValueError):
    """The bytes are empty or not a document, for example an HTML page."""


@dataclass(frozen=True)
class DocumentRef:
    sha256: str
    publisher: str
    media_type: str
    storage_key: str
    page_count: int
    scripts: list[str]
    created: bool  # False when the bytes were already archived and only an origin was added


class Archive:
    """Stores documents once, by content hash, and never changes or removes them.

    There is deliberately no method to overwrite or delete (SPEC-001/R4).
    """

    def __init__(
        self,
        registry: Registry,
        sources: ObjectStore,
        data: ObjectStore,
        events: EventSink,
        fetcher: Fetcher | None = None,
        now: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        self.registry = registry
        self.sources = sources
        self.data = data
        self.events = events
        self.fetcher = fetcher
        self.now = now

    # ---- ways in ---------------------------------------------------------

    def add_file(self, path: Path, publisher: str, licence: str) -> DocumentRef:
        data = path.read_bytes()
        return self._ingest(
            data, publisher, licence, "file", str(path.resolve()), filename=path.name, content_type=None
        )

    def add_url(self, url: str, publisher: str, licence: str) -> DocumentRef | FetchFailure:
        _check_publisher(publisher, licence)
        if self.fetcher is None:
            raise RuntimeError("this archive has no fetcher")
        result = self.fetcher.fetch(url)
        if isinstance(result, FetchFailure):
            self._record_failure(result, publisher)
            return result
        filename = Path(urlsplit(result.final_url).path).name or None
        if media.sniff(result.data, filename, result.content_type) is None:
            failure = FetchFailure(url, "not_a_document", f"content-type {result.content_type}")
            self._record_failure(failure, publisher)
            return failure
        return self._ingest(
            result.data, publisher, licence, "url", url, filename=filename, content_type=result.content_type
        )

    def add_upload(self, data: bytes, filename: str, account_id: str) -> DocumentRef:
        if not ACCOUNT_ID.match(account_id):
            raise ValueError("account_id must be an opaque account id, not contact details")
        # The filename may carry personal details, so it is used only to recognise the format, not stored.
        reference = f"upload/{uuid.uuid4()}"
        return self._ingest(
            data,
            CONTRIBUTOR_PUBLISHER,
            CONTRIBUTOR_LICENCE,
            "upload",
            reference,
            filename=filename,
            content_type=None,
            account_id=account_id,
        )

    # ---- reading ---------------------------------------------------------

    def open(self, sha256: str) -> BinaryIO:
        row = self.registry.get(sha256)
        if row is None:
            raise KeyError(sha256)
        return io.BytesIO(self.sources.get(row.storage_key))

    def page_text(self, sha256: str, page: int) -> str | None:
        for row in self.registry.pages(sha256):
            if row.page == page:
                return self.data.get(row.text_key).decode("utf-8") if row.text_key else None
        raise KeyError(f"{sha256} page {page}")

    # ---- internals -------------------------------------------------------

    def _ingest(
        self,
        data: bytes,
        publisher: str,
        licence: str,
        origin_kind: str,
        origin_ref: str,
        *,
        filename: str | None,
        content_type: str | None,
        account_id: str | None = None,
    ) -> DocumentRef:
        _check_publisher(publisher, licence)
        kind = media.sniff(data, filename, content_type)
        if kind is None:
            raise NotADocumentError(f"not a document: {filename or origin_ref}")
        sha256 = hashlib.sha256(data).hexdigest()
        at = self.now()
        origin = OriginRow(origin_kind, origin_ref, at, at, account_id)

        existing = self.registry.get(sha256)
        if existing is not None:
            self.registry.add_origin(sha256, origin)
            return _ref(existing, created=False)

        analysis = pages.analyse(data, kind)
        storage_key = f"source/{publisher}/{at:%Y}/{sha256}.{kind.extension}"
        # Store first, register second, announce last: a crash between steps leaves nothing half-registered,
        # and a retry finds the stored object already present and carries on.
        self.sources.put_new(storage_key, data, kind.mime)
        page_rows = []
        for page in analysis.pages:
            if page.text is None:
                page_rows.append(PageRow(page.number, False, None))
                continue
            text_key = f"parsed/{sha256}/page-{page.number}.txt"
            self.data.put_new(text_key, page.text.encode("utf-8"), "text/plain; charset=utf-8")
            page_rows.append(PageRow(page.number, True, text_key))

        row = DocumentRow(
            sha256=sha256,
            publisher=publisher,
            media_type=kind.mime,
            extension=kind.extension,
            size_bytes=len(data),
            page_count=analysis.page_count,
            scripts=detect_scripts(p.text for p in analysis.pages if p.text),
            licence=licence,
            storage_key=storage_key,
            first_seen_at=at,
        )
        self.registry.insert(row, page_rows, origin)
        self.events.emit(
            {"type": "archive.document_added", "sha256": sha256, "publisher": publisher, "at": at.isoformat()}
        )
        return _ref(row, created=True)

    def _record_failure(self, failure: FetchFailure, publisher: str) -> None:
        self.registry.record_failure(
            FailureRow(failure.url, publisher, failure.reason, failure.detail or None, self.now())
        )


def _check_publisher(publisher: str, licence: str) -> None:
    if not PUBLISHER.match(publisher):
        raise ValueError(f"publisher must be a lowercase slug, got {publisher!r}")
    if not licence.strip():
        raise ValueError("licence is required")


def _ref(row: DocumentRow, *, created: bool) -> DocumentRef:
    return DocumentRef(
        row.sha256, row.publisher, row.media_type, row.storage_key, row.page_count, list(row.scripts), created
    )
