"""The real steps for W1: the intake desk (SPEC-005), the audit desk (SPEC-011) and publishing."""

from __future__ import annotations

import json
from typing import Any

from hishob.agentkit.intake import run_intake
from hishob.archive import Archive
from hishob.archive.storage import ObjectStore
from hishob.ledger import Loader
from hishob.workflows.w1 import publish_outputs


class LiveSteps:
    def __init__(self, client: Any, archive: Archive, loader: Loader, public: ObjectStore, cap_usd: int = 5) -> None:
        self.client = client
        self.archive = archive
        self.loader = loader
        self.public = public
        self.cap_usd = cap_usd

    def intake(self, hashes: list[str], run_id: str) -> dict[str, Any]:
        run = run_intake(self.client, self.archive, self.loader, hashes, cap_usd=self.cap_usd, run_id=run_id)
        if run.load_report is None:
            raise RuntimeError(f"intake {run_id} produced no facts: {run.status_detail}")
        report = json.loads(self.loader.data.get(run.load_report))
        return {"run_id": run.run_id, "accepted": report["accepted"], "held": report["held_total"]}

    def audit(self, ward: str, run_id: str) -> dict[str, Any]:
        raise NotImplementedError("the audit desk is SPEC-011; until it is built, W1 cannot run its audit step")

    def publish(self, audit: dict[str, Any]) -> list[str]:
        return publish_outputs(self.loader.data, self.public, audit)
