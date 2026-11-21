"""Follow the Rupee endpoints (SPEC-040/R8). Read-only and public: the dataset is synthetic and the contractors are
fictional. Served from the bundle `hishob rupee build` wrote; nothing is computed per request but filtering."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, Query

from hishob.rupee.data import DEFAULT_DIR, read_csv
from hishob.rupee.trail import Trail

BRIEF_WARD = (
    "ward_code",
    "ward_name",
    "zone",
    "grade",
    "overall",
    "scores",
    "budget_inr",
    "spend_inr",
    "budget_used",
    "failed_spend_inr",
    "money_in_question_inr",
    "open_overdue_issues",
    "jobs",
    "low_lying_index",
)
BRIEF_CONTRACTOR = (
    "contractor_id",
    "name",
    "grade",
    "overall",
    "scores",
    "jobs",
    "spend_inr",
    "reopen_rate",
    "expected_reopen_rate",
    "sla_met_rate",
    "expected_sla_met_rate",
    "money_in_question_inr",
    "flags",
)


class Store:
    def __init__(self, bundle_dir: Path) -> None:
        self.bundle_dir = bundle_dir
        self._loaded: dict[str, Any] | None = None

    def get(self) -> dict[str, Any]:
        if self._loaded is None:
            path = self.bundle_dir / "bundle.json"
            if not path.exists():
                raise HTTPException(503, "Follow the Rupee has not been built on this server (hishob rupee build)")
            b = json.loads(path.read_text(encoding="utf-8"))
            root = Path(b["summary"].get("dataset") or DEFAULT_DIR)
            if not (root / "work_orders.csv").exists():
                root = DEFAULT_DIR
            wos = {r["work_order_id"]: {**r, "cite": r.cite} for r in read_csv(root / "work_orders.csv")}
            self._loaded = {
                "bundle": b,
                "work_orders": wos,
                "wards": {w["ward_code"]: w for w in b["wards"]},
                "contractors": {c["contractor_id"]: c for c in b["contractors"]},
                "trail": Trail(b, wos),
            }
        return self._loaded


def router(bundle_dir: Path, store: Store | None = None) -> APIRouter:
    store = store or Store(bundle_dir)
    r = APIRouter(prefix="/rupee", tags=["rupee"])

    @r.get("/summary")
    def summary() -> dict[str, Any]:
        s = store.get()
        b = s["bundle"]
        return {
            **b["summary"],
            "wards": [{k: w[k] for k in BRIEF_WARD} for w in b["wards"]],
            "contractors": [{k: c[k] for k in BRIEF_CONTRACTOR} for c in b["contractors"]],
            "top_plan": b["plan"]["city_top"][:10],
        }

    @r.get("/ward")
    def ward(code: str = Query(min_length=1, max_length=4)) -> dict[str, Any]:
        s = store.get()
        w = s["wards"].get(code.upper())
        if w is None:
            raise HTTPException(404, "no such ward")
        flags = [f for f in s["bundle"]["flags"] if f["ward_code"] == w["ward_code"]]
        return {**w, "plan": s["bundle"]["plan"]["wards"][w["ward_code"]], "flag_list": flags}

    @r.get("/contractor")
    def contractor(id: str = Query(min_length=2, max_length=8)) -> dict[str, Any]:
        s = store.get()
        c = s["contractors"].get(id.upper())
        if c is None:
            raise HTTPException(404, "no such contractor")
        return {**c, "flag_list": [f for f in s["bundle"]["flags"] if f["contractor_id"] == c["contractor_id"]]}

    @r.get("/flags")
    def flags(
        rule: str | None = None,
        ward: str | None = None,
        contractor: str | None = None,
        limit: int = Query(100, ge=1, le=1000),
        offset: int = Query(0, ge=0),
    ) -> dict[str, Any]:
        out = [
            f
            for f in store.get()["bundle"]["flags"]
            if (not rule or f["rule"] == rule)
            and (not ward or f["ward_code"] == ward.upper())
            and (not contractor or f["contractor_id"] == contractor.upper())
        ]
        return {"total": len(out), "items": out[offset : offset + limit]}

    @r.get("/workorder")
    def workorder(id: str = Query(min_length=4, max_length=20)) -> dict[str, Any]:
        s = store.get()
        wo = s["work_orders"].get(id.strip().upper())
        if wo is None:
            raise HTTPException(404, "no such work order")
        return {
            "work_order": wo,
            "flags": [f for f in s["bundle"]["flags"] if f["work_order_id"] == wo["work_order_id"]],
            "complaints": [c for c in s["bundle"]["complaints"] if c["work_order_id"] == wo["work_order_id"]],
        }

    @r.get("/complaint")
    def complaint(
        id: str = Query(min_length=4, max_length=20), lang: str = Query("en", pattern="^(mr|hi|en)$")
    ) -> dict[str, Any]:
        trail: Trail = store.get()["trail"]
        got = trail(id, lang)
        if got is None:
            raise HTTPException(404, "no such complaint")
        return got

    @r.get("/wards.geojson")
    def wards_geojson() -> dict[str, Any]:
        s = store.get()
        root = Path(s["bundle"]["summary"].get("dataset") or DEFAULT_DIR)
        path = root / "wards.geojson" if (root / "wards.geojson").exists() else DEFAULT_DIR / "wards.geojson"
        shapes = json.loads(path.read_text(encoding="utf-8"))
        for f in shapes.get("features", []):
            props = f.setdefault("properties", {})
            w = s["wards"].get(props.get("ward_code", ""))
            if w:
                props.update({k: w[k] for k in ("grade", "overall", "budget_used", "money_in_question_inr")})
        return shapes  # type: ignore[no-any-return]

    @r.get("/plan")
    def plan() -> dict[str, Any]:
        p = store.get()["bundle"]["plan"]
        return {"weights": p["weights"], "methods": p["methods"], "city_top": p["city_top"]}

    return r
