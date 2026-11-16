"""SPEC-003/T6: `hishob load` end to end."""

from __future__ import annotations

import json

import pytest

from hishob import cli
from tests.conftest import FIXTURES, TEST_DB

pytestmark = pytest.mark.integration


def test_cli_loads_a_facts_file_and_prints_the_report(conn, tmp_path, monkeypatch, capsys) -> None:
    monkeypatch.setenv("HISHOB_DATABASE_URL", TEST_DB)
    monkeypatch.setenv("HISHOB_LOCAL_ROOT", str(tmp_path))
    assert cli.main(["archive", "add", str(FIXTURES / "tender-en.pdf"), "--publisher", "bmc", "--licence", "x"]) == 0
    sha = json.loads(capsys.readouterr().out)["sha256"]

    good = {
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
    bad = dict(good, id="work:b", quote="not on the page")
    facts = tmp_path / "facts.jsonl"
    facts.write_text("\n".join(json.dumps(r) for r in (good, bad)) + "\n{not json\n", encoding="utf-8")

    assert cli.main(["load", str(facts), "--batch", "cli-1", "--extractor", "doc-extractor@1"]) == 0
    report = json.loads(capsys.readouterr().out)
    assert report["accepted"] == 1
    assert report["held"] == {"quote_not_found": 1, "schema_invalid": 1}
    assert (tmp_path / "data" / "staging" / "cli-1" / "held.jsonl").exists()
