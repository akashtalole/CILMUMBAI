"""The query API (SPEC-007). Every read goes through here, under exactly one access tier."""

from __future__ import annotations

import hmac
import json
import logging
import os
import secrets
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

from hishob import alerts
from hishob.api import access, citations
from hishob.api.ask import AskDesk, AskRun, Refused
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
FREE_TEXT_PARAMS = {
    "q",
    "text",
    "lat",
    "lon",
}  # logged by length only: typed text, or where a phone says its owner is (C7)
MAX_PHOTO_BYTES = 10_000_000


@dataclass
class ApiConfig:
    connect: Callable[[], Any]  # returns a context manager yielding a psycopg connection
    sources: ObjectStore
    data: ObjectStore
    graph_driver: Any
    graph_database: str | None = None
    token_secret: str | None = None
    public_per_minute: int = 60
    ask: AskRun | None = None  # runs the citizen desk; None turns POST /ask off (no Claude credentials)
    ask_per_hour: int = 10
    ask_max_running: int = 4
    review: Any = None  # a workflows.w1.Engine that answers gates and publishes; None turns the /review endpoints off
    photo: AskRun | None = None  # reads a photo report; None turns POST /report off (no Claude credentials)
    photo_per_hour: int = 5
    web_dir: Path | None = None  # the built web app (app/web/dist), served at /


class AnswerCheck(BaseModel):
    text: str = Field(min_length=1, max_length=20000)
    cited_fact_ids: list[str] = Field(default_factory=list, max_length=200)
    language: str | None = Field(default=None, pattern="^(mr|hi|en)$")


class Question(BaseModel):
    question: str = Field(min_length=3, max_length=1000)
    language: str | None = Field(default=None, pattern="^(mr|hi|en)$")
    lat: float | None = Field(default=None, ge=-90, le=90)
    lon: float | None = Field(default=None, ge=-180, le=180)


class SavedArea(BaseModel):
    """A point with a radius, or named roads (SPEC-010/R1)."""

    kind: str = Field(pattern="^(point|roads)$")
    language: str = Field(pattern="^(mr|hi|en)$")
    lat: float | None = Field(default=None, ge=-90, le=90)
    lon: float | None = Field(default=None, ge=-180, le=180)
    radius_m: int | None = None
    road_ids: list[str] = Field(default_factory=list, max_length=20)


class GateDecision(BaseModel):
    decision: str | list[str]  # continue, stop, approve, hold, or the wards to release
    reason: str = Field(min_length=1, max_length=1000)


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
    # The citizen desk's own tool calls come back into this app in-process. They carry the resident's token, so
    # they read under the resident's tier, and this header, known only to this process, so the resident's
    # per-minute limit is not spent on them.
    internal_key = secrets.token_urlsafe(24)
    desk = AskDesk(config.ask, config.ask_per_hour, config.ask_max_running) if config.ask else None
    photo_desk = AskDesk(config.photo, config.photo_per_hour, 2) if config.photo else None

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
        internal = hmac.compare_digest(request.headers.get("x-hishob-internal", ""), internal_key)
        # Polling for an answer is an in-memory lookup by an unguessable id; it must not use up the limit.
        internal = internal or (request.method == "GET" and request.url.path.startswith(("/ask/", "/report/")))
        if tier == "public" and not internal and not limiter.allow(client):
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

    @app.get("/places/{node_id}/shape")
    def place_shape(node_id: str, ctx: Context = Depends(context)) -> dict[str, Any]:
        """A ward's boundary or a road's line, as GeoJSON, for the map. Roads include every segment of the name."""
        found = geo.shape(ctx.conn, node_id)
        if found is None:
            raise HTTPException(404, "no shape for this place")
        return found

    @app.post("/ask", status_code=202)
    def ask(body: Question, request: Request) -> dict[str, Any]:
        """Ask the citizen desk a question. Returns a job id; poll GET /ask/{id} for the answer."""
        if desk is None:
            raise HTTPException(503, "asking the desk is not enabled on this server")
        from fastapi.testclient import TestClient

        authorization = request.headers.get("authorization")
        token = authorization.removeprefix("Bearer ").strip() if authorization else None
        http = TestClient(app, raise_server_exceptions=False, headers={"x-hishob-internal": internal_key})
        location = (body.lat, body.lon) if body.lat is not None and body.lon is not None else None
        client = request.client.host if request.client else "unknown"
        try:
            job = desk.submit(client, http, body.question, language=body.language, location=location, token=token)
        except Refused as reason:
            raise HTTPException(429, str(reason)) from None
        return {"id": job.id, "status": job.status}

    def job_status(owner: AskDesk | None, job_id: str, what: str) -> dict[str, Any]:
        job = owner.get(job_id) if owner else None
        if job is None or owner is None:
            raise HTTPException(404, f"no such {what}")
        end = job.finished if job.finished is not None else owner.clock()
        out: dict[str, Any] = {"id": job.id, "status": job.status, "elapsed_s": round(end - job.started, 1)}
        if job.answer is not None:
            out["answer"] = job.answer
        if job.error is not None:
            out["error"] = "the desk could not answer this time"
        return out

    @app.get("/ask/{job_id}")
    def ask_status(job_id: str) -> dict[str, Any]:
        return job_status(desk, job_id, "question")

    @app.post("/report", status_code=202)
    async def report(
        request: Request,
        language: str = Query(pattern="^(mr|hi|en)$"),
        lat: float | None = Query(default=None, ge=-90, le=90),
        lon: float | None = Query(default=None, ge=-180, le=180),
    ) -> dict[str, Any]:
        """Report a problem from a photo: the request body is the image itself (SPEC-030). Returns a job id; poll
        GET /report/{id}. The photo is processed in memory and is never stored or logged."""
        from hishob.agentkit.photo import PhotoError, read_photo

        if photo_desk is None:
            raise HTTPException(503, "photo reports are not enabled on this server")
        if not request.headers.get("content-type", "").startswith("image/"):
            raise HTTPException(415, "send the photo as the request body with an image content type")
        if int(request.headers.get("content-length") or 0) > MAX_PHOTO_BYTES:
            raise HTTPException(413, "the photo is larger than 10 MB")
        chunks: list[bytes] = []
        total = 0
        async for chunk in request.stream():  # a client with no length header is cut off at the limit
            total += len(chunk)
            if total > MAX_PHOTO_BYTES:
                raise HTTPException(413, "the photo is larger than 10 MB")
            chunks.append(chunk)
        try:
            photo = read_photo(b"".join(chunks))
        except PhotoError as problem:
            raise HTTPException(422, str(problem)) from None
        from fastapi.testclient import TestClient

        authorization = request.headers.get("authorization")
        token = authorization.removeprefix("Bearer ").strip() if authorization else None
        http = TestClient(app, raise_server_exceptions=False, headers={"x-hishob-internal": internal_key})
        where = (lat, lon) if lat is not None and lon is not None else None
        client = request.client.host if request.client else "unknown"
        try:
            job = photo_desk.submit(client, http, "photo", photo=photo, language=language, location=where, token=token)
        except Refused as reason:
            raise HTTPException(429, str(reason)) from None
        return {"id": job.id, "status": job.status}

    @app.get("/report/{job_id}")
    def report_status(job_id: str) -> dict[str, Any]:
        return job_status(photo_desk, job_id, "report")

    def subscriber(ctx: Context) -> str:
        """Saved areas belong to an account: contributor tier or above (SPEC-010/R1)."""
        if ctx.account is None or not allows(ctx.tier, "contributor"):
            raise HTTPException(401, "sign in to save an area")
        return ctx.account

    @app.post("/subscriptions", status_code=201)
    def subscribe(body: SavedArea, ctx: Context = Depends(context)) -> dict[str, Any]:
        account = subscriber(ctx)
        try:
            if body.kind == "point":
                if body.lat is None or body.lon is None or body.radius_m is None:
                    raise ValueError("a point needs lat, lon and radius_m")
                saved = alerts.save_point(ctx.conn, account, body.lat, body.lon, body.radius_m, body.language)
            else:
                saved = alerts.save_roads(ctx.conn, account, body.road_ids, body.language)
        except ValueError as problem:
            raise HTTPException(422, str(problem)) from None
        return _area(saved)

    @app.get("/subscriptions")
    def subscriptions(ctx: Context = Depends(context)) -> list[dict[str, Any]]:
        return [_area(s) for s in alerts.list_subscriptions(ctx.conn, subscriber(ctx))]

    @app.delete("/subscriptions/{subscription_id}", status_code=204)
    def unsubscribe(subscription_id: int, ctx: Context = Depends(context)) -> Response:
        if not alerts.unsubscribe(ctx.conn, subscriber(ctx), subscription_id):
            raise HTTPException(404, "no such saved area")
        return Response(status_code=204)

    @app.get("/alerts")
    def my_alerts(request: Request, ctx: Context = Depends(context)) -> list[dict[str, Any]]:
        """The caller's alerts, newest first, each in its saved area's language with a link to the source page."""
        base = str(request.base_url).rstrip("/")
        return alerts.list_alerts(ctx.conn, subscriber(ctx), base_url=base)

    def reviewer(ctx: Context) -> str:
        """The review screen is for the reviewer tier only (SPEC-021/R1)."""
        if ctx.account is None or not allows(ctx.tier, "reviewer"):
            raise HTTPException(403, "reviewer access is needed")
        if config.review is None:
            raise HTTPException(503, "the review screen is not enabled on this server")
        return ctx.account

    @app.get("/review/threads")
    def review_threads(ctx: Context = Depends(context)) -> list[dict[str, Any]]:
        """Workflow runs, newest first: where each waits, what is staged and held, and the decisions so far."""
        reviewer(ctx)
        out = []
        for thread in config.review.threads(30):
            status = config.review.status(thread)
            out.append(
                {
                    "thread": thread,
                    "log": status.log,
                    "waiting": status.waiting,
                    "finished": status.finished,
                    "published": status.published,
                    "decisions": config.review.decisions(thread),
                }
            )
        return out

    @app.get("/review/files")
    def review_file(key: str = Query(min_length=1, max_length=300), ctx: Context = Depends(context)) -> dict[str, Any]:
        """One staged output, as text, for the reviewer to read before releasing it."""
        reviewer(ctx)
        if not key.startswith("staging/") or ".." in key.split("/") or "\\" in key:
            raise HTTPException(404, "no such file")
        try:
            raw = config.data.get(key)
        except Exception:
            raise HTTPException(404, "no such file") from None
        return {"key": key, "text": raw[:200_000].decode("utf-8", errors="replace"), "truncated": len(raw) > 200_000}

    @app.post("/review/threads/{thread}/decision")
    def review_decide(thread: str, body: GateDecision, ctx: Context = Depends(context)) -> dict[str, Any]:
        """Answer a gate. Only a reviewer can, the reason is required, and the decision is recorded."""
        from hishob.workflows.w1 import GateError

        account = reviewer(ctx)
        try:
            status = config.review.resume(thread, body.decision, reason=body.reason, account=account, tier=ctx.tier)
        except GateError as refused:
            raise HTTPException(403, str(refused)) from None
        except ValueError as problem:
            raise HTTPException(409 if "not waiting" in str(problem) else 422, str(problem)) from None
        return {
            "thread": thread,
            "log": status.log,
            "waiting": status.waiting,
            "finished": status.finished,
            "published": status.published,
        }

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

    if config.web_dir is not None and (config.web_dir / "index.html").exists():
        from fastapi.staticfiles import StaticFiles

        app.mount("/", StaticFiles(directory=config.web_dir, html=True), name="web")  # after every API route
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


def _area(saved: alerts.Subscription) -> dict[str, Any]:
    out = asdict(saved)
    del out["account_id"]  # the caller knows who they are; nothing else needs it
    out["created_at"] = saved.created_at.isoformat()
    return out


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
    web = Path(os.environ.get("HISHOB_WEB_DIR") or Path(__file__).resolve().parents[3] / "web" / "dist")
    return create_app(
        ApiConfig(
            connect=connect,
            sources=sources,
            data=data,
            graph_driver=make_driver(settings),
            graph_database=settings.graph_database,
            token_secret=os.environ.get("HISHOB_TOKEN_SECRET"),
            public_per_minute=int(os.environ.get("HISHOB_PUBLIC_PER_MINUTE", "60")),
            ask=_live_desk() if os.environ.get("HISHOB_ASK_ENABLED", "1") != "0" else None,
            ask_per_hour=int(os.environ.get("HISHOB_ASK_PER_HOUR", "10")),
            review=_review_engine(settings, data),
            photo=_live_photo() if os.environ.get("HISHOB_PHOTO_ENABLED", "1") != "0" else None,
            photo_per_hour=int(os.environ.get("HISHOB_PHOTO_PER_HOUR", "5")),
            web_dir=web,
        )
    )


def _live_desk() -> AskRun | None:
    """The real citizen desk, if this server can reach Claude and the desk has been applied to the account."""
    if not (os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_AWS_WORKSPACE_ID")):
        return None
    from hishob.agentkit.citizen import answer_question
    from hishob.agentkit.client import make_client
    from hishob.api.ask import public_answer

    def run(http: Any, question: str, **kwargs: Any) -> dict[str, Any]:
        return public_answer(
            answer_question(make_client(), http, question, language_hint=kwargs.pop("language"), **kwargs)
        )

    return run


def _live_photo() -> AskRun | None:
    """The real photo report: a vision model names the problem, the citizen desk answers. Needs Claude credentials."""
    if not (os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_AWS_WORKSPACE_ID")):
        return None
    from hishob.agentkit.client import make_client
    from hishob.agentkit.photo import public_report, report_from_photo

    def run(http: Any, question: str, **kwargs: Any) -> dict[str, Any]:
        return public_report(report_from_photo(make_client(), http, kwargs.pop("photo"), **kwargs))

    return run


def _review_engine(settings: Any, data: ObjectStore) -> Any:
    """The engine behind the review screen: it answers gates and publishes to the public store. Off unless access
    tiers are configured, since only a reviewer may use it."""
    if os.environ.get("HISHOB_REVIEW_ENABLED", "1") == "0" or not os.environ.get("HISHOB_TOKEN_SECRET"):
        return None
    from hishob.archive.storage import LocalStore, S3Store
    from hishob.workflows.w1 import Engine, PublishOnlySteps

    public: ObjectStore
    if settings.storage == "s3":
        import boto3

        public = S3Store(boto3.client("s3"), os.environ["HISHOB_PUBLIC_BUCKET"])
    else:
        public = LocalStore(settings.local_root / "public")
    return Engine(settings.database_url, PublishOnlySteps(data, public))
