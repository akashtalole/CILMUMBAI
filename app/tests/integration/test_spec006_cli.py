"""SPEC-006: `hishob graph apply` and `hishob graph view` end to end."""

from __future__ import annotations

import json

import pytest

from hishob import cli
from tests.conftest import FIXTURES, TEST_DB, TEST_GRAPH

pytestmark = [pytest.mark.integration, pytest.mark.graph]


def test_cli_applies_the_ledger_and_runs_a_view(conn, graph_driver, tmp_path, monkeypatch, capsys) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setenv("HISHOB_DATABASE_URL", TEST_DB)
    monkeypatch.setenv("HISHOB_LOCAL_ROOT", str(tmp_path))
    monkeypatch.setenv("HISHOB_GRAPH_URI", TEST_GRAPH)
    assert cli.main(["archive", "add", str(FIXTURES / "tender-en.pdf"), "--publisher", "bmc", "--licence", "x"]) == 0
    sha = json.loads(capsys.readouterr().out)["sha256"]
    work = {
        "kind": "node",
        "id": "work:a",
        "label": "Work",
        "props": {"title": "Road works"},
        "source": sha,
        "page": 1,
        "quote": "Brihanmumbai Municipal Corporation",
        "tier": "official",
        "confidence": 0.9,
    }
    facts = tmp_path / "facts.jsonl"
    facts.write_text(json.dumps(work) + "\n", encoding="utf-8")
    assert cli.main(["load", str(facts), "--batch", "cli-g1", "--extractor", "test@1"]) == 0
    capsys.readouterr()

    assert cli.main(["graph", "apply"]) == 0
    assert json.loads(capsys.readouterr().out)["facts_applied"] == 1
    assert cli.main(["graph", "view", "trace_money", "work:a"]) == 0
    result = json.loads(capsys.readouterr().out)
    assert result["rows"][0]["hops"][0]["node"]["title"] == "Road works"
    assert [g["hop"].split(" ")[0] for g in result["gaps"]] == ["budget_head", "tender"]
