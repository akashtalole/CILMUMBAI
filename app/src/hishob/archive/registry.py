"""The document registry in Postgres (SPEC-001/R3)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

import psycopg
from psycopg.rows import class_row


@dataclass(frozen=True)
class DocumentRow:
    sha256: str
    publisher: str
    media_type: str
    extension: str
    size_bytes: int
    page_count: int
    scripts: list[str]
    licence: str
    storage_key: str
    first_seen_at: datetime


@dataclass(frozen=True)
class OriginRow:
    origin_kind: str
    origin_ref: str
    fetched_at: datetime
    last_seen_at: datetime
    account_id: str | None


@dataclass(frozen=True)
class PageRow:
    page: int
    has_text_layer: bool
    text_key: str | None


@dataclass(frozen=True)
class FailureRow:
    url: str
    publisher: str
    reason: str
    detail: str | None
    attempted_at: datetime


Conn = psycopg.Connection[tuple[object, ...]]


class Registry:
    def __init__(self, conn: Conn) -> None:
        self.conn = conn

    def get(self, sha256: str) -> DocumentRow | None:
        with self.conn.cursor(row_factory=class_row(DocumentRow)) as cur:
            row = cur.execute(
                "SELECT sha256, publisher, media_type, extension, size_bytes, page_count, scripts, licence,"
                " storage_key, first_seen_at FROM registry.documents WHERE sha256 = %s",
                (sha256,),
            ).fetchone()
        self.conn.commit()
        return row

    def insert(self, doc: DocumentRow, pages: list[PageRow], origin: OriginRow) -> None:
        with self.conn.transaction():
            self.conn.execute(
                "INSERT INTO registry.documents (sha256, publisher, media_type, extension, size_bytes,"
                " page_count, scripts, licence, storage_key, first_seen_at)"
                " VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
                (
                    doc.sha256,
                    doc.publisher,
                    doc.media_type,
                    doc.extension,
                    doc.size_bytes,
                    doc.page_count,
                    doc.scripts,
                    doc.licence,
                    doc.storage_key,
                    doc.first_seen_at,
                ),
            )
            with self.conn.cursor() as cur:
                cur.executemany(
                    "INSERT INTO registry.pages (sha256, page, has_text_layer, text_key) VALUES (%s, %s, %s, %s)",
                    [(doc.sha256, p.page, p.has_text_layer, p.text_key) for p in pages],
                )
            self._upsert_origin(doc.sha256, origin)

    def add_origin(self, sha256: str, origin: OriginRow) -> None:
        with self.conn.transaction():
            self._upsert_origin(sha256, origin)

    def _upsert_origin(self, sha256: str, origin: OriginRow) -> None:
        self.conn.execute(
            "INSERT INTO registry.origins (sha256, origin_kind, origin_ref, fetched_at, last_seen_at, account_id)"
            " VALUES (%s, %s, %s, %s, %s, %s)"
            " ON CONFLICT (sha256, origin_kind, origin_ref) DO UPDATE SET last_seen_at = EXCLUDED.last_seen_at",
            (sha256, origin.origin_kind, origin.origin_ref, origin.fetched_at, origin.last_seen_at, origin.account_id),
        )

    def origins(self, sha256: str) -> list[OriginRow]:
        with self.conn.cursor(row_factory=class_row(OriginRow)) as cur:
            rows = cur.execute(
                "SELECT origin_kind, origin_ref, fetched_at, last_seen_at, account_id"
                " FROM registry.origins WHERE sha256 = %s ORDER BY id",
                (sha256,),
            ).fetchall()
        self.conn.commit()
        return rows

    def pages(self, sha256: str) -> list[PageRow]:
        with self.conn.cursor(row_factory=class_row(PageRow)) as cur:
            rows = cur.execute(
                "SELECT page, has_text_layer, text_key FROM registry.pages WHERE sha256 = %s ORDER BY page",
                (sha256,),
            ).fetchall()
        self.conn.commit()
        return rows

    def record_failure(self, failure: FailureRow) -> None:
        with self.conn.transaction():
            self.conn.execute(
                "INSERT INTO registry.fetch_failures (url, publisher, reason, detail, attempted_at)"
                " VALUES (%s, %s, %s, %s, %s)",
                (failure.url, failure.publisher, failure.reason, failure.detail, failure.attempted_at),
            )

    def failures(self) -> list[FailureRow]:
        with self.conn.cursor(row_factory=class_row(FailureRow)) as cur:
            rows = cur.execute(
                "SELECT url, publisher, reason, detail, attempted_at FROM registry.fetch_failures ORDER BY id"
            ).fetchall()
        self.conn.commit()
        return rows
