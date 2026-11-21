"""Static export (SPEC-040/R9): the whole tool as JSON files a plain web host can serve, so the demo runs with no
server, database or API key, on GitHub Pages or a laptop. The files are the answers of the /rupee endpoints
themselves, fetched through the API, so the static site and the API cannot drift apart."""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import Any

from fastapi import FastAPI
from fastapi.testclient import TestClient

from hishob.api.rupee import Store, router

LANGS = ("en", "mr", "hi")
SHARD = 100  # complaints per file, by number: BMC25-000123 is in complaints/1.json


def safe(code: str) -> str:
    """Ward codes have a slash (F/S); a file name cannot."""
    return code.replace("/", "-")


def shard(complaint_id: str) -> int:
    digits = "".join(ch for ch in complaint_id.split("-")[-1] if ch.isdigit())
    return int(digits or 0) // SHARD


def _save(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")


def run(bundle_dir: Path, out: Path) -> dict[str, int]:
    store = Store(bundle_dir)
    app = FastAPI()
    app.include_router(router(bundle_dir, store))
    web = TestClient(app)

    def get(path: str, **params: str) -> Any:
        r = web.get(path, params=params)
        r.raise_for_status()
        return r.json()

    summary = get("/rupee/summary")
    _save(out / "summary.json", summary)
    _save(out / "plan.json", get("/rupee/plan"))
    _save(out / "wards.geojson", get("/rupee/wards.geojson"))
    _save(out / "flags.json", get("/rupee/flags", limit="1000", offset="0") | {"items": _all_flags(get)})
    for w in summary["wards"]:
        _save(out / "ward" / f"{safe(w['ward_code'])}.json", get("/rupee/ward", code=w["ward_code"]))
    for c in summary["contractors"]:
        _save(out / "contractor" / f"{c['contractor_id']}.json", get("/rupee/contractor", id=c["contractor_id"]))

    # Complaint answers come from the same Trail the /rupee/complaint endpoint calls, without 19,500 requests.
    loaded = store.get()
    bundle, trail = loaded["bundle"], loaded["trail"]
    shards: dict[int, dict[str, Any]] = defaultdict(dict)
    for c in bundle["complaints"]:
        cid = c["complaint_id"]
        answers = {lang: trail(cid, lang) for lang in LANGS}
        first = answers["en"]
        shards[shard(cid)][cid] = {
            "complaint": first["complaint"],
            "work_order": first["work_order"],
            "flags": first["flags"],
            "answers": {lang: a["answer"] for lang, a in answers.items()},
        }
    for n, items in shards.items():
        _save(out / "complaints" / f"{n}.json", items)
    return {"wards": len(summary["wards"]), "contractors": len(summary["contractors"]),
            "complaints": len(bundle["complaints"]), "complaint_files": len(shards)}  # fmt: skip


def _all_flags(get: Any) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    while True:
        page = get("/rupee/flags", limit="1000", offset=str(len(items)))
        items += page["items"]
        if len(items) >= page["total"] or not page["items"]:
            return items
