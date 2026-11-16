"""The query API (SPEC-007). Every read goes through here, under exactly one access tier."""

from __future__ import annotations

import json
import logging
import os
import time
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import psycopg
from fastapi import Depends, FastAPI, HTTPException, Query, Request, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from hishob.api import access, citations
from hishob.api.ratelimit import RateLimiter
from hishob.api.tiers import allows, resolve
from hishob.archive import Archive
from hishob.archive.events import MemorySink
from hishob.archive.registry import Registry
from hishob.archive.storage import ObjectStore
from hishob.graphstore import Views
from hishob.ledger import Loader
from hishob.place import geo

log = logging.getLogger("hishob.api.requests")
VIEW_NAMES = ("trace_money", "who_is_responsible", "work_status", "ward_summary", "gaps_for")
FREE_TEXT_PARAMS = {"q", "text"}  # logged by length only: they can carry anything a person types (C7)


@dataclass
class ApiConfig:
    connect: Callable[[], Any]  # returns a context manager yielding a psycopg connection
    sources: ObjectStore
    data: ObjectStore
    graph_driver: Any
    graph_database: str | None = None
    token_secret: str | None = None
    public_per_minute: int = 60


class AnswerCheck(BaseModel):
    text: str = Field(min_length=1, max_length=20000)
    cited_fact_ids: list[str] = Field(default_factory=list, max_length=200)
    language: str | None = Field(default=None, pattern="^(mr|hi|en)$")


class Context:
    """What one request may use: its tier and read access to the stores."""

    def __init__(self, tier: str, account: str | None, conn: Any, config: ApiConfig, request: Request) -> None:
        self.tier = tier
        self.account = account
        self.conn = conn
        self.archive = Archive(Registry(conn), config.sources, config.data, MemorySink())
        self.loader = Loader(conn, self.archive, config.data)
        self.views = Views(config.graph_driver, config.graph_database)
        self.request = request
        self._fetched: dict[str, str | None] = {}

    def returned(self, fact_ids: list[str]) -> None:
        self.request.state.fact_ids = [*getattr(self.request.state, "fact_ids", []), *fact_ids]

    def fetched_at(self, sha256: str) -> str | None:
        if sha256 not in self._fetched:
            origins = self.archive.registry.origins(sha256)
            self._fetched[sha256] = min(o.fetched_at for o in origins).isoformat() if origins else None
        return self._fetched[sha256]


def create_app(config: ApiConfig) -> FastAPI:
    app = FastAPI(
        title="Aamcha Hishob API",
        version="0.1.0",
        description="Sourced facts about Mumbai's civic spending and works. Not an official record.",
    )
    limiter = RateLimiter(config.public_per_minute)

    def context(request: Request) -> Iterator[Context]:
        tier, account = resolve(request.headers.get("authorization"), config.token_secret)
        request.state.tier = tier
        with config.connect() as conn:
            yield Context(tier, account, conn, config, request)

    @app.middleware("http")
    async def tier_limit_and_log(request: Request, call_next: Callable[[Request], Any]) -> Response:
        started = time.monotonic()
        tier, _ = resolve(request.headers.get("authorization"), config.token_secret)
        client = request.client.host if request.client else "unknown"
        if tier == "public" and not limiter.allow(client):
            response: Response = JSONResponse({"detail": "too many requests"}, status_code=429)
        else:
            response = await call_next(request)
        response.headers["X-Hishob-Tier"] = tier
        params = {k: (f"<{len(v)} chars>" if k in FREE_TEXT_PARAMS else v) for k, v in request.query_params.items()}
        log.info(
            json.dumps(
                {
                    "tier": tier,
                    "method": request.method,
                    "endpoint": request.url.path,
                    "params": params,
                    "status": response.status_code,
                    "fact_ids": getattr(request.state, "fact_ids", []),
                    "ms": int((time.monotonic() - started) * 1000),
                },
                ensure_ascii=False,
            )
        )
        return response

    @app.get("/places")
    def places(
        q: str = Query(min_length=1, max_length=200), kinds: str | None = None, ctx: Context = Depends(context)
    ) -> list[dict[str, Any]]:
        wanted = set(kinds.split(",")) if kinds else None
        return [asdict(m) for m in geo.find_place(ctx.conn, q, wanted)]

    @app.get("/point")
    def point(
        lat: float = Query(ge=-90, le=90), lon: float = Query(ge=-180, le=180), ctx: Context = Depends(context)
    ) -> dict[str, Any]:
        return asdict(geo.at_point(ctx.conn, lat, lon))

    @app.get("/views/{name}")
    def view(
        name: str,
        id: str = Query(min_length=1, max_length=200),
        issue: str | None = None,
        ctx: Context = Depends(context),
    ) -> dict[str, Any]:
        if name not in VIEW_NAMES:
            raise HTTPException(404, "unknown view")
        if name == "who_is_responsible":
            result = ctx.views.who_is_responsible(id, issue)
        else:
            result = getattr(ctx.views, name)(id)
        out = asdict(result)
        out["rows"] = [_visible(row, ctx) for row in out["rows"]]
        out["rows"] = [row for row in out["rows"] if row is not None]
        return out

    @app.get("/facts/{fact_id}")
    def fact(fact_id: str, ctx: Context = Depends(context)) -> dict[str, Any]:
        entry = ctx.loader.fact(fact_id)
        if entry is None or not allows(ctx.tier, access.required_tier(entry.get("label"), entry.get("tier"))):
            raise HTTPException(404, "no such fact")  # facts above the caller's tier do not exist for them
        ctx.returned([fact_id])
        return {**entry, "source_fetched_at": ctx.fetched_at(entry["source"])}

    @app.get("/sources/{sha256}/pages/{page}")
    def source_page(sha256: str, page: int, ctx: Context = Depends(context)) -> dict[str, Any]:
        row = ctx.archive.registry.get(sha256)
        if row is None or not allows(ctx.tier, access.source_tier(row.publisher)):
            raise HTTPException(404, "no such document")
        if not 1 <= page <= row.page_count:
            raise HTTPException(404, "no such page")
        return {
            "sha256": sha256,
            "page": page,
            "page_count": row.page_count,
            "publisher": row.publisher,
            "licence": row.licence,
            "media_type": row.media_type,
            "fetched_at": ctx.fetched_at(sha256),
            "text": ctx.archive.page_text(sha256, page),
        }

    @app.post("/answers/check")
    def answer_check(body: AnswerCheck, ctx: Context = Depends(context)) -> dict[str, Any]:
        facts, missing = [], []
        for fid in body.cited_fact_ids:
            entry = ctx.loader.fact(fid)
            if entry is None or not allows(ctx.tier, access.required_tier(entry.get("label"), entry.get("tier"))):
                missing.append(fid)
            else:
                facts.append(entry)
        result = citations.check(body.text, facts, missing)
        ctx.returned([f["fact_id"] for f in facts])
        return {
            "ok": result.ok,
            "matched": [asdict(c) for c in result.matched],
            "unmatched": [asdict(c) for c in result.unmatched],
        }

    return app


def openapi_document() -> str:
    """The API's OpenAPI document, generated without any stores (committed and checked in CI)."""
    from hishob.archive.storage import LocalStore

    @contextmanager
    def nothing() -> Iterator[None]:
        yield None

    app = create_app(
        ApiConfig(
            connect=nothing,
            sources=LocalStore(Path("/nonexistent")),
            data=LocalStore(Path("/nonexistent")),
            graph_driver=None,
        )
    )
    return json.dumps(app.openapi(), indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def _is_node(value: Any) -> bool:
    return isinstance(value, dict) and "id" in value and "label" in value and "provenance" in value


def _visible(row: dict[str, Any], ctx: Context) -> dict[str, Any] | None:
    """Drop what the caller's tier may not see, and add each node's quote and fetch date (R4, R7)."""
    out: dict[str, Any] = {}
    for key, value in row.items():
        if _is_node(value):
            if not allows(ctx.tier, access.node_tier(value)):
                if key in {"node", "work"}:
                    return None
                out[key] = None
                continue
            out[key] = _enrich(value, ctx)
        elif isinstance(value, list) and value and all(isinstance(v, dict) for v in value):
            items = [
                _visible(v, ctx)
                if not _is_node(v)
                else (_enrich(v, ctx) if allows(ctx.tier, access.node_tier(v)) else None)
                for v in value
            ]
            out[key] = [v for v in items if v is not None]
        else:
            out[key] = value
    return out


def _enrich(node: dict[str, Any], ctx: Context) -> dict[str, Any]:
    entry = ctx.loader.fact(node["fact_id"]) if node.get("fact_id") else None
    ctx.returned([node["fact_id"]] if node.get("fact_id") else [])
    return {
        **node,
        "quote": entry["quote"] if entry else None,
        "source_fetched_at": ctx.fetched_at(node["source"]) if node.get("source") else None,
    }


def serve() -> FastAPI:
    """App for `uvicorn hishob.api.app:serve --factory`, configured from the environment."""
    from psycopg_pool import ConnectionPool

    from hishob.archive.storage import LocalStore
    from hishob.config import Settings
    from hishob.graphstore.driver import make_driver

    settings = Settings.from_env()
    if not log.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter("%(message)s"))
        log.addHandler(handler)
        log.setLevel(logging.INFO)
    pool = ConnectionPool(settings.database_url, min_size=1, max_size=10, open=True)

    @contextmanager
    def connect() -> Iterator[psycopg.Connection[tuple[object, ...]]]:
        with pool.connection() as conn:
            yield conn

    if settings.storage == "s3":
        import boto3

        from hishob.archive.storage import S3Store

        s3 = boto3.client("s3")
        sources: ObjectStore = S3Store(s3, settings.archive_bucket)
        data: ObjectStore = S3Store(s3, settings.data_bucket)
    else:
        sources, data = LocalStore(settings.local_root / "archive"), LocalStore(settings.local_root / "data")
    return create_app(
        ApiConfig(
            connect=connect,
            sources=sources,
            data=data,
            graph_driver=make_driver(settings),
            graph_database=settings.graph_database,
            token_secret=os.environ.get("HISHOB_TOKEN_SECRET"),
            public_per_minute=int(os.environ.get("HISHOB_PUBLIC_PER_MINUTE", "60")),
        )
    )
