"""SPEC-001/T9: the command line, end to end against the test database."""

from __future__ import annotations

import json

import pytest

from hishob import cli, db
from tests.conftest import FIXTURES, TEST_DB

pytestmark = pytest.mark.integration


def test_migrations_apply_once(conn) -> None:
    assert db.migrate(conn) == []


def test_cli_adds_and_shows_a_document(conn, tmp_path, monkeypatch, capsys) -> None:
    monkeypatch.setenv("HISHOB_DATABASE_URL", TEST_DB)
    monkeypatch.setenv("HISHOB_LOCAL_ROOT", str(tmp_path))

    assert (
        cli.main(["archive", "add", str(FIXTURES / "tender-en.pdf"), "--publisher", "bmc", "--licence", "public"]) == 0
    )
    added = json.loads(capsys.readouterr().out)
    assert added["created"] is True and added["page_count"] == 2

    assert cli.main(["archive", "show", added["sha256"]]) == 0
    shown = json.loads(capsys.readouterr().out)
    assert shown["publisher"] == "bmc" and shown["origins"][0].startswith("file:")

    events = (tmp_path / "events.jsonl").read_text(encoding="utf-8").splitlines()
    assert json.loads(events[0])["sha256"] == added["sha256"]


def test_cli_reports_unknown_documents(conn, tmp_path, monkeypatch, capsys) -> None:
    monkeypatch.setenv("HISHOB_DATABASE_URL", TEST_DB)
    monkeypatch.setenv("HISHOB_LOCAL_ROOT", str(tmp_path))
    assert cli.main(["archive", "show", "0" * 64]) == 1
    assert "not found" in capsys.readouterr().err
