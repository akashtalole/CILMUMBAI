"""The real system under test: the intake desk for extraction, the citizen desk for questions and refusals
(SPEC-012). Everything here costs money, so each run has a spending cap.

Extraction runs through the configured archive and ledger. Point `HISHOB_DATABASE_URL` and `HISHOB_LOCAL_ROOT` at a
dedicated evaluation database: the ten invented documents are loaded into it, and must not land in a real one.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from typing import Any

from hishob.agentkit.citizen import answer_question
from hishob.agentkit.intake import run_intake
from hishob.api.ask import public_answer
from hishob.evals.datasets import ExtractionItem
from hishob.evals.scoring import AskResult, ExtractionResult

PUBLISHER = "evals"
LICENCE = "invented documents for evaluating the platform"


def extract_all(
    client: Any, archive: Any, loader: Any, items: list[ExtractionItem], *, cap_usd: int
) -> tuple[dict[str, ExtractionResult], float | None]:
    """Archive every document, read them all in one intake run, and split the extracted records by document."""
    sha_of = {i.id: archive.add_file(i.document, publisher=PUBLISHER, licence=LICENCE).sha256 for i in items}
    run = run_intake(client, archive, loader, sorted(set(sha_of.values())), cap_usd=cap_usd)
    raw = loader.data.get(f"staging/{run.run_id}/facts.jsonl").decode("utf-8") if "facts.jsonl" in run.outputs else ""
    records = [json.loads(line) for line in raw.splitlines() if line.strip()]
    results = {}
    for item in items:
        sha = sha_of[item.id]
        pages = archive.registry.get(sha).page_count
        results[item.id] = ExtractionResult(
            [r for r in records if r.get("source") == sha],
            {n: archive.page_text(sha, n) for n in range(1, pages + 1)},
        )
    return results, run.cost_usd


def make_asker(client: Any, http: Any, token: str | None) -> Callable[[str, str], AskResult]:
    """Ask the citizen desk through the API at `http`, and check the reply the way a resident's page would."""
    headers = {"Authorization": f"Bearer {token}"} if token else {}

    def ask(question: str, language: str) -> AskResult:
        try:
            return asked(question, language)
        except Exception as error:  # one failed question must not lose the rest of a paid run
            return AskResult("", f"[evaluation error: {type(error).__name__}]", "error", set(), False)

    def asked(question: str, language: str) -> AskResult:
        answer = answer_question(client, http, question, language_hint=language, token=token)
        shown = public_answer(answer)
        nodes: set[str] = set()
        for fact_id in answer.cited_fact_ids:
            entry = http.get(f"/facts/{fact_id}", headers=headers).json()
            nodes |= {str(entry[k]) for k in ("id", "from", "to") if entry.get(k)}
        check = http.post(
            "/answers/check",
            json={"text": shown["body"] or "-", "cited_fact_ids": answer.cited_fact_ids, "language": language},
            headers=headers,
        ).json()
        return AskResult(
            body=shown["body"],
            text=answer.text,
            status=answer.status,
            cited_nodes=nodes,
            citation_ok=bool(check.get("ok")),
            cost_usd=answer.cost_usd,
        )

    return ask


def ask_all(
    ask: Callable[[str, str], AskResult], questions: list[tuple[str, str]], workers: int = 4
) -> list[AskResult]:
    with ThreadPoolExecutor(max_workers=workers) as pool:
        return list(pool.map(lambda q: ask(*q), questions))
