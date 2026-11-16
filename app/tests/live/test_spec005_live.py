"""SPEC-005 against the real Claude API. Costs money: runs only with HISHOB_LIVE=1 and a credential.

    HISHOB_LIVE=1 ANTHROPIC_API_KEY=... uv run pytest tests/live -s

Applies the agents in agents/ to the account (once; later runs reuse them via agents/.lock.json) and reads
four fixture documents with a $5 cap.
"""

from __future__ import annotations

import hashlib
import json
import os

import pytest

from hishob.agentkit.client import make_client
from hishob.agentkit.intake import run_intake
from hishob.agentkit.provision import apply
from hishob.archive import Archive
from hishob.ledger import Loader
from tests.conftest import FIXTURES

pytestmark = [
    pytest.mark.live,
    pytest.mark.integration,
    pytest.mark.skipif(os.environ.get("HISHOB_LIVE") != "1", reason="live tests need HISHOB_LIVE=1"),
]
DOCS = ["tender-en.pdf", "tender-mixed.pdf", "award-notice.pdf", "damaged.pdf"]


def sha(name: str) -> str:
    return hashlib.sha256((FIXTURES / name).read_bytes()).hexdigest()


def test_spec005_live_intake_run(make_archive, conn) -> None:  # type: ignore[no-untyped-def]
    client = make_client()
    for item in apply(client):
        print(item)
    archive: Archive = make_archive()
    for name in DOCS:
        archive.add_file(FIXTURES / name, publisher="bmc", licence="test fixture")
    loader = Loader(conn, archive, archive.data)

    run = run_intake(client, archive, loader, [sha(n) for n in DOCS], cap_usd=5)
    print(json.dumps(run.__dict__, indent=2, default=str))

    # AC1: all three outputs came back
    assert {"facts.jsonl", "report.md"} <= set(run.outputs), run.status_detail
    report_md = loader.data.get(f"staging/{run.run_id}/report.md").decode("utf-8")
    # AC4: the damaged file is listed as not covered; every input appears
    assert run.not_in_report == []
    damaged_line = next(line for line in report_md.splitlines() if sha("damaged.pdf") in line)
    assert "not covered" in damaged_line.lower()
    # AC2: each readable document had an extractor and a verifier thread
    agents = [t["agent"] for t in run.threads]
    assert sum("Document extractor" in a for a in agents) >= 3, agents
    assert sum("Fact verifier" in a for a in agents) >= 3, agents
    # AC5: the two spellings of the contractor were not silently merged
    review = (
        loader.data.get(f"staging/{run.run_id}/review.jsonl").decode("utf-8") if "review.jsonl" in run.outputs else ""
    )
    contractors = loader.conn.execute(
        "SELECT count(*) FROM ledger.current WHERE label IN ('Contractor', 'Company')"
    ).fetchone()[0]
    loader.conn.commit()
    assert "Ganesh" in review or contractors >= 2
    # AC7: the run record is complete
    assert run.session_id and run.cost_usd is not None and run.load_report
    assert run.status in {"complete", "incomplete"}
