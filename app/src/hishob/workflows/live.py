"""The real steps for W1: the intake desk (SPEC-005), the audit desk (SPEC-011) and publishing."""

from __future__ import annotations

import json
from typing import Any

from hishob.agentkit.audit import run_audit
from hishob.agentkit.intake import run_intake
from hishob.archive import Archive
from hishob.archive.storage import ObjectStore
from hishob.ledger import Loader
from hishob.workflows.w1 import publish_outputs


class LiveSteps:
    """`http` is a client for the query API; the audit desk reads through it with `reviewer_token` (SPEC-011/R1)."""

    def __init__(
        self,
        client: Any,
        archive: Archive,
        loader: Loader,
        public: ObjectStore,
        cap_usd: int = 5,
        *,
        http: Any = None,
        reviewer_token: str | None = None,
        audit_cap_usd: int = 10,
    ) -> None:
        self.client = client
        self.archive = archive
        self.loader = loader
        self.public = public
        self.cap_usd = cap_usd
        self.http = http
        self.reviewer_token = reviewer_token
        self.audit_cap_usd = audit_cap_usd

    def intake(self, hashes: list[str], run_id: str) -> dict[str, Any]:
        run = run_intake(self.client, self.archive, self.loader, hashes, cap_usd=self.cap_usd, run_id=run_id)
        if run.load_report is None:
            raise RuntimeError(f"intake {run_id} produced no facts: {run.status_detail}")
        report = json.loads(self.loader.data.get(run.load_report))
        return {"run_id": run.run_id, "accepted": report["accepted"], "held": report["held_total"]}

    def audit(self, ward: str, run_id: str) -> dict[str, Any]:
        if self.http is None:
            raise RuntimeError("the audit step needs the query API: set HISHOB_API_URL")
        run = run_audit(
            self.client,
            self.http,
            ward,
            self.loader.data,
            run_id=run_id,
            token=self.reviewer_token,
            cap_usd=self.audit_cap_usd,
        )
        # Held files stay in staging; only what may be released is passed to the release gate and publish.
        return {"ward": ward, "run_id": run.run_id, "files": run.files, "status": run.status, "held": run.held}

    def publish(self, audit: dict[str, Any]) -> list[str]:
        return publish_outputs(self.loader.data, self.public, audit)
