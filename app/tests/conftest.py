from __future__ import annotations

import os
from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path

import psycopg
import pytest

from hishob import db
from hishob.archive import Archive
from hishob.archive.events import MemorySink
from hishob.archive.fetch import Fetcher
from hishob.archive.registry import Registry
from hishob.archive.storage import LocalStore

FIXTURES = Path(__file__).parent / "fixtures"
TEST_DB = os.environ.get("HISHOB_TEST_DATABASE_URL", "postgresql://postgres:hishob@localhost:5432/hishob_test")
FIXED_NOW = datetime(2026, 11, 16, 9, 30, tzinfo=UTC)


@pytest.fixture
def conn() -> Iterator[psycopg.Connection[tuple[object, ...]]]:
    """A migrated, empty database. Skips the test if no test database is reachable."""
    try:
        connection = db.connect(TEST_DB)
    except psycopg.OperationalError as error:
        pytest.skip(f"no test database at HISHOB_TEST_DATABASE_URL: {error}")
    with connection.transaction():
        connection.execute("DROP SCHEMA IF EXISTS flow CASCADE")
        connection.execute("DROP SCHEMA IF EXISTS graphstore CASCADE")
        connection.execute("DROP SCHEMA IF EXISTS geo CASCADE")
        connection.execute("DROP SCHEMA IF EXISTS agentkit CASCADE")
        connection.execute("DROP SCHEMA IF EXISTS ledger CASCADE")
        connection.execute("DROP SCHEMA IF EXISTS registry CASCADE")
        connection.execute("DROP TABLE IF EXISTS public.hishob_migrations")
    db.migrate(connection)
    yield connection
    connection.close()


TEST_GRAPH = os.environ.get("HISHOB_TEST_GRAPH_URI", "neo4j://127.0.0.1:7687")
TEST_GRAPH_AUTH = (
    os.environ.get("HISHOB_TEST_GRAPH_USER", "neo4j"),
    os.environ.get("HISHOB_TEST_GRAPH_PASSWORD", "hishob-local-only"),
)


@pytest.fixture
def graph_driver():  # type: ignore[no-untyped-def]
    """An EMPTY graph database. Everything in it is deleted: point HISHOB_TEST_GRAPH_URI at a test instance only."""
    from neo4j import GraphDatabase
    from neo4j.exceptions import ServiceUnavailable

    driver = GraphDatabase.driver(TEST_GRAPH, auth=TEST_GRAPH_AUTH, notifications_min_severity="OFF")
    try:
        driver.verify_connectivity()
    except (ServiceUnavailable, OSError) as error:
        driver.close()
        pytest.skip(f"no test graph database at HISHOB_TEST_GRAPH_URI: {error}")
    with driver.session() as session:
        session.run("MATCH (n) DETACH DELETE n").consume()
    yield driver
    driver.close()


@pytest.fixture
def sink() -> MemorySink:
    return MemorySink()


@pytest.fixture
def make_archive(conn, sink, tmp_path):  # type: ignore[no-untyped-def]
    def build(fetcher: Fetcher | None = None, sources=None, data=None) -> Archive:  # type: ignore[no-untyped-def]
        return Archive(
            Registry(conn),
            sources or LocalStore(tmp_path / "archive"),
            data or LocalStore(tmp_path / "data"),
            sink,
            fetcher,
            now=lambda: FIXED_NOW,
        )

    return build
