"""Command line: `hishob db migrate`, `hishob archive add|show`, `hishob load`, `hishob ontology build [--check]`."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from hishob import db
from hishob.archive import Archive, FetchFailure
from hishob.archive.events import EventSink, FileSink, SqsSink
from hishob.archive.fetch import Fetcher
from hishob.archive.registry import Registry
from hishob.archive.storage import LocalStore, ObjectStore, S3Store
from hishob.config import Settings


def build_archive(settings: Settings) -> Archive:
    conn = db.connect(settings.database_url)
    sources: ObjectStore
    data: ObjectStore
    events: EventSink
    if settings.storage == "s3":
        import boto3

        s3 = boto3.client("s3")
        sources, data = S3Store(s3, settings.archive_bucket), S3Store(s3, settings.data_bucket)
    else:
        sources = LocalStore(settings.local_root / "archive")
        data = LocalStore(settings.local_root / "data")
    if settings.events == "sqs" and settings.events_queue_url:
        import boto3

        events = SqsSink(boto3.client("sqs"), settings.events_queue_url)
    else:
        events = FileSink(settings.local_root / "events.jsonl")
    return Archive(Registry(conn), sources, data, events, Fetcher(delay_s=settings.fetch_delay_s))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="hishob")
    groups = parser.add_subparsers(dest="group", required=True)

    database = groups.add_parser("db").add_subparsers(dest="command", required=True)
    database.add_parser("migrate", help="apply database migrations")

    archive = groups.add_parser("archive").add_subparsers(dest="command", required=True)
    add = archive.add_parser("add", help="archive a local file or a URL")
    add.add_argument("source", help="a file path or an http(s) URL")
    add.add_argument("--publisher", required=True, help="lowercase slug, e.g. bmc, mahatenders")
    add.add_argument("--licence", required=True, help="licence or terms the document is held under")
    show = archive.add_parser("show", help="print a document's registry entry")
    show.add_argument("sha256")

    load = groups.add_parser("load", help="check a facts file and append accepted facts to the ledger (SPEC-003)")
    load.add_argument("facts", type=Path)
    load.add_argument("--batch", required=True, help="unique batch id")
    load.add_argument("--extractor", required=True, help="agent id and version, e.g. doc-extractor@3")
    load.add_argument("--ontology-version", help="ontology version the facts were extracted under")

    place = groups.add_parser("place").add_subparsers(dest="command", required=True)
    wards = place.add_parser("import-wards", help="import ward boundaries from GeoJSON (SPEC-004)")
    wards.add_argument("path", type=Path)
    wards.add_argument("--kind", choices=["admin", "electoral"], required=True)
    wards.add_argument("--name-property", required=True, help="feature property holding the ward code or number")
    wards.add_argument("--publisher", required=True)
    wards.add_argument("--licence", required=True)
    wards.add_argument("--batch", required=True)
    roads = place.add_parser("import-roads", help="import named roads from an OpenStreetMap export (Overpass JSON)")
    roads.add_argument("path", type=Path)
    roads.add_argument("--publisher", default="openstreetmap")
    roads.add_argument("--licence", default="ODbL-1.0")
    roads.add_argument("--batch", required=True)
    place.add_parser("build", help="rebuild the geo tables from the ledger")
    find = place.add_parser("find", help="find a place by name")
    find.add_argument("text")
    at = place.add_parser("at", help="what is at a point")
    at.add_argument("lat", type=float)
    at.add_argument("lon", type=float)

    graph = groups.add_parser("graph").add_subparsers(dest="command", required=True)
    graph.add_parser("apply", help="apply new ledger files to the graph (SPEC-006)")
    graph.add_parser("rebuild", help="drop the graph and rebuild it from the ledger")
    view = graph.add_parser("view", help="run a named view")
    view.add_argument("name", choices=["trace_money", "who_is_responsible", "work_status", "ward_summary", "gaps_for"])
    view.add_argument("node_id", help="node id, or a ward code for ward_summary")
    view.add_argument("--issue", help="issue code for who_is_responsible, e.g. pothole")

    api = groups.add_parser("api").add_subparsers(dest="command", required=True)
    openapi = api.add_parser("openapi", help="write the OpenAPI document to api/openapi.json (SPEC-007)")
    openapi.add_argument("--check", action="store_true", help="fail if the committed document is out of date")

    ask = groups.add_parser("ask", help="ask the citizen desk a question through a running API (SPEC-008)")
    ask.add_argument("question")
    ask.add_argument("--api", default="http://127.0.0.1:8000", help="base URL of the query API")
    ask.add_argument("--lat", type=float)
    ask.add_argument("--lon", type=float)
    ask.add_argument("--language", choices=["mr", "hi", "en"])

    agents = groups.add_parser("agents").add_subparsers(dest="command", required=True)
    agents.add_parser("apply", help="create or update the agents and environment in the Claude account")
    intake = groups.add_parser("intake").add_subparsers(dest="command", required=True)
    run_cmd = intake.add_parser("run", help="read archived documents with the intake desk (SPEC-005)")
    run_cmd.add_argument("sha256", nargs="+")
    run_cmd.add_argument("--cap-usd", type=int, default=5, help="hard spending cap for the session, in dollars")

    audit = groups.add_parser("audit").add_subparsers(dest="command", required=True)
    audit_run = audit.add_parser("run", help="audit one ward with the audit desk, into staging (SPEC-011)")
    audit_run.add_argument("ward", help="ward code, e.g. K/W")
    audit_run.add_argument("--api", default=None, help="query API base URL (default HISHOB_API_URL)")
    audit_run.add_argument("--run-id", default=None)
    audit_run.add_argument("--cap-usd", type=int, default=10, help="hard spending cap for the session, in dollars")

    alerts_cmd = groups.add_parser("alerts").add_subparsers(dest="command", required=True)
    alerts_cmd.add_parser("run", help="queue alerts for new tenders, awards and corrigenda in saved areas (SPEC-010)")
    alerts_cmd.add_parser("overdue", help="the daily check: queue alerts for works past their due date")

    evals = groups.add_parser("eval").add_subparsers(dest="command", required=True)
    evals.add_parser("validate", help="check the evaluation sets and scan them for personal data (SPEC-012)")
    ev_run = evals.add_parser("run", help="run the evaluation sets against the real desks and write a report")
    ev_run.add_argument("--set", dest="sets", action="append", choices=["extraction", "questions", "refusals"])
    ev_run.add_argument("--against", dest="api", default=None, help="query API base URL (default HISHOB_API_URL)")
    ev_run.add_argument("--report", default="out", help="folder for report.json and report.md")
    ev_run.add_argument("--token", default=None, help="access token the desk reads with (default: public)")
    ev_run.add_argument("--workers", type=int, default=4)
    ev_run.add_argument("--cap-usd", type=int, default=8, help="spending cap for the extraction run, in dollars")
    ev_run.add_argument("--commit", default=None)
    ev_gate = evals.add_parser("gate", help="compare a report with the baseline; fail on unapproved regressions")
    ev_gate.add_argument("--report", default="out/report.json")
    ev_base = evals.add_parser("baseline", help="record a report's scores as the baseline of the last release")
    ev_base.add_argument("--report", default="out/report.json")

    workflow = groups.add_parser("workflow").add_subparsers(dest="command", required=True)
    wf_run = workflow.add_parser("run", help="start W1 for archived documents and wards (SPEC-009)")
    wf_run.add_argument("thread", help="a new, unique thread id")
    wf_run.add_argument("--hash", dest="hashes", action="append", required=True, help="archived document sha256")
    wf_run.add_argument("--ward", dest="wards", action="append", required=True, help="ward code, e.g. K/W")
    wf_status = workflow.add_parser("status", help="where a thread is and what it is waiting for")
    wf_status.add_argument("thread")
    wf_resume = workflow.add_parser("resume", help="answer a gate; needs a reviewer token")
    wf_resume.add_argument("thread")
    wf_resume.add_argument("decision", help="continue|stop (review_facts); approve|hold|K/W,H/W (release)")
    wf_resume.add_argument("--reason", required=True)
    wf_resume.add_argument("--token", required=True, help="signed token <tier>.<account>.<signature>")
    wf_retry = workflow.add_parser("retry", help="re-run a thread from its last saved checkpoint")
    wf_retry.add_argument("thread")
    wf_consume = workflow.add_parser("consume", help="start runs from the workflow queue")
    wf_consume.add_argument("--queue-url", required=True)
    wf_consume.add_argument("--max", type=int, default=10)

    ontology = groups.add_parser("ontology").add_subparsers(dest="command", required=True)
    build = ontology.add_parser("build", help="generate the record schema, whitelist and reference page")
    build.add_argument("--check", action="store_true", help="fail if the committed files are out of date")

    args = parser.parse_args(argv)
    if args.group == "ontology":
        return _ontology_build(check=args.check)
    if args.group == "workflow":
        return _workflow(args, Settings.from_env())
    if args.group == "audit":
        return _audit(args, Settings.from_env())
    if args.group == "eval":
        return _eval(args, Settings.from_env())
    if args.group == "alerts":
        from hishob import alerts
        from hishob.ledger import Loader

        held = build_archive(Settings.from_env())
        check = alerts.evaluate if args.command == "run" else alerts.evaluate_overdue
        print(json.dumps({"queued": check(held.registry.conn, Loader(held.registry.conn, held, held.data))}))
        return 0
    if args.group == "api":
        from hishob.api.app import openapi_document

        target = Path(__file__).resolve().parents[2] / "api" / "openapi.json"
        document = openapi_document()
        if args.check:
            if not target.exists() or target.read_text(encoding="utf-8") != document:
                print("api/openapi.json is out of date; run: uv run hishob api openapi", file=sys.stderr)
                return 1
            print("api/openapi.json is up to date")
            return 0
        target.parent.mkdir(exist_ok=True)
        target.write_text(document, encoding="utf-8")
        print(f"wrote {target}")
        return 0
    if args.group == "ask":
        import httpx

        from hishob.agentkit.citizen import answer_question
        from hishob.agentkit.client import make_client

        location = (args.lat, args.lon) if args.lat is not None and args.lon is not None else None
        with httpx.Client(base_url=args.api, timeout=60) as http:
            answer = answer_question(make_client(), http, args.question, language_hint=args.language, location=location)
        print(answer.text)
        if answer.draft_letter:
            print("\n--- letter ---\n" + answer.draft_letter)
        print(f"\n[{answer.status}, {answer.language}, {len(answer.cited_fact_ids)} facts cited]", file=sys.stderr)
        return 0
    if args.group == "agents":
        from hishob.agentkit.client import make_client
        from hishob.agentkit.provision import apply

        for item in apply(make_client()):
            print(f"{item.action:9} {item.kind:11} {item.key:18} {item.id} {item.version or ''}")
        return 0
    settings = Settings.from_env()

    if args.group == "db":
        applied = db.migrate(db.connect(settings.database_url))
        print("applied: " + (", ".join(applied) or "nothing new"))
        return 0

    store = build_archive(settings)
    if args.group == "place":
        return _place(args, store)
    if args.group == "graph":
        return _graph(args, store, settings)
    if args.group == "intake":
        from dataclasses import asdict

        from hishob.agentkit.client import make_client
        from hishob.agentkit.intake import run_intake
        from hishob.ledger import Loader

        run = run_intake(
            make_client(), store, Loader(store.registry.conn, store, store.data), args.sha256, cap_usd=args.cap_usd
        )
        print(json.dumps(asdict(run), ensure_ascii=False, indent=2))
        return 0 if run.status == "complete" else 1
    if args.group == "load":
        from dataclasses import asdict

        from hishob.ledger import Loader

        loader = Loader(store.registry.conn, store, store.data)
        report = loader.load_file(
            args.facts, batch_id=args.batch, extractor=args.extractor, ontology_version=args.ontology_version
        )
        print(json.dumps({**asdict(report), "held_total": report.held_total}, ensure_ascii=False, indent=2))
        return 0
    if args.command == "add":
        if args.source.startswith(("http://", "https://")):
            result = store.add_url(args.source, args.publisher, args.licence)
        else:
            result = store.add_file(Path(args.source), args.publisher, args.licence)
        if isinstance(result, FetchFailure):
            print(f"failed: {result.reason} {result.detail}", file=sys.stderr)
            return 1
        print(json.dumps(result.__dict__, ensure_ascii=False))
        return 0

    row = store.registry.get(args.sha256)
    if row is None:
        print("not found", file=sys.stderr)
        return 1
    print(
        json.dumps(
            {
                **row.__dict__,
                "first_seen_at": row.first_seen_at.isoformat(),
                "origins": [o.origin_kind + ":" + o.origin_ref for o in store.registry.origins(args.sha256)],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


def _place(args: argparse.Namespace, store: Archive) -> int:
    from dataclasses import asdict

    from hishob.ledger import Loader
    from hishob.place import geo
    from hishob.place.importer import import_roads, import_wards

    conn = store.registry.conn
    loader = Loader(conn, store, store.data)
    if args.command == "import-wards":
        result = import_wards(
            store,
            loader,
            args.path,
            kind=args.kind,
            name_property=args.name_property,
            publisher=args.publisher,
            licence=args.licence,
            batch_id=args.batch,
        )
        print(
            json.dumps(
                {
                    "features": result.features,
                    "skipped": result.skipped,
                    "accepted": result.report.accepted,
                    "held": result.report.held,
                    "geo": geo.build(conn),
                },
                ensure_ascii=False,
            )
        )
    elif args.command == "import-roads":
        result = import_roads(
            store, loader, args.path, publisher=args.publisher, licence=args.licence, batch_id=args.batch
        )
        print(
            json.dumps(
                {
                    "features": result.features,
                    "skipped": result.skipped,
                    "accepted": result.report.accepted,
                    "held": result.report.held,
                    "geo": geo.build(conn),
                },
                ensure_ascii=False,
            )
        )
    elif args.command == "build":
        print(json.dumps(geo.build(conn)))
    elif args.command == "find":
        print(json.dumps([asdict(m) for m in geo.find_place(conn, args.text)], ensure_ascii=False, indent=2))
    else:
        print(json.dumps(asdict(geo.at_point(conn, args.lat, args.lon)), ensure_ascii=False, indent=2))
    return 0


def _graph(args: argparse.Namespace, store: Archive, settings: Settings) -> int:
    from dataclasses import asdict

    from hishob.graphstore import GraphStore, Views
    from hishob.graphstore.driver import make_driver

    driver = make_driver(settings)
    try:
        if args.command in {"apply", "rebuild"}:
            graph = GraphStore(driver, store.registry.conn, store.data, settings.graph_database)
            result = graph.apply() if args.command == "apply" else graph.rebuild()
            applied = asdict(result)
            if args.command == "apply":  # new facts were projected: queue street alerts for them (SPEC-010/R2)
                from hishob import alerts
                from hishob.ledger import Loader

                applied["alerts_queued"] = alerts.evaluate(
                    store.registry.conn, Loader(store.registry.conn, store, store.data)
                )
            print(json.dumps(applied))
            return 0
        views = Views(driver, settings.graph_database)
        if args.name == "who_is_responsible":
            out = views.who_is_responsible(args.node_id, args.issue)
        else:
            out = getattr(views, args.name)(args.node_id)
        print(json.dumps(asdict(out), ensure_ascii=False, indent=2, default=str))
        return 0
    finally:
        driver.close()


def _workflow(args: argparse.Namespace, settings: Settings) -> int:
    import os
    from dataclasses import asdict

    from hishob.api.tiers import resolve
    from hishob.workflows.w1 import Engine, GateError, consume

    def engine() -> Engine:
        import httpx

        from hishob.agentkit.client import make_client
        from hishob.ledger import Loader
        from hishob.workflows.live import LiveSteps

        store = build_archive(settings)
        public: ObjectStore
        if settings.storage == "s3":
            import boto3

            public = S3Store(boto3.client("s3"), os.environ["HISHOB_PUBLIC_BUCKET"])
        else:
            public = LocalStore(settings.local_root / "public")
        api_url = os.environ.get("HISHOB_API_URL")
        http = httpx.Client(base_url=api_url, timeout=120) if api_url else None
        loader = Loader(store.registry.conn, store, store.data)
        steps = LiveSteps(make_client(), store, loader, public, http=http, reviewer_token=_audit_token())
        return Engine(settings.database_url, steps)

    def show(status: object) -> int:
        print(json.dumps(asdict(status), ensure_ascii=False, indent=2, default=str))  # type: ignore[call-overload]
        return 0

    if args.command == "run":
        return show(engine().start(args.thread, args.hashes, args.wards))
    if args.command == "status":
        return show(engine().status(args.thread))
    if args.command == "retry":
        return show(engine().retry(args.thread))
    if args.command == "consume":
        import boto3

        for status in consume(boto3.client("sqs"), args.queue_url, engine(), max_messages=args.max):
            show(status)
        return 0
    tier, account = resolve(f"Bearer {args.token}", os.environ.get("HISHOB_TOKEN_SECRET"))
    if tier != "reviewer":  # refuse before connecting to anything; Engine.resume checks again
        print(f"refused: a {tier} token may not answer a gate", file=sys.stderr)
        return 2
    decision: object = args.decision
    if args.decision not in {"continue", "stop", "approve", "hold"}:
        decision = [w.strip() for w in args.decision.split(",") if w.strip()]
    try:
        return show(engine().resume(args.thread, decision, reason=args.reason, account=account or "", tier=tier))
    except GateError as err:
        print(f"refused: {err}", file=sys.stderr)
        return 2


def _eval(args: argparse.Namespace, settings: Settings) -> int:
    import os
    from typing import Any

    from hishob.evals import datasets, pii, report
    from hishob.evals.run import SETS

    if args.command == "validate":
        problems = datasets.validate()
        found = pii.scan()
        for p in problems:
            print(f"dataset: {p}", file=sys.stderr)
        for f in found:
            print(f"personal data: {f.path}: {f.kind}: {f.text}", file=sys.stderr)
        if not problems and not found:
            print("evaluation sets are valid and hold no personal data")
        return 1 if problems or found else 0
    if args.command in {"gate", "baseline"}:
        data = report.reaggregate(json.loads(Path(args.report).read_text(encoding="utf-8")))
        baseline = report.load_baseline()
        if args.command == "baseline":
            baseline["scores"] = {name: {k: v for k, v in s.items() if k != "n"} for name, s in data["sets"].items()}
            baseline["note"] = f"Scores of the release recorded {data['created_at']}" + (
                f" at {data['commit']}" if data.get("commit") else ""
            )
            (datasets.EVALS_DIR / "baseline.json").write_text(
                json.dumps(baseline, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
            )
            print("baseline recorded")
            return 0
        regressions = report.gate(data, baseline, report.load_approvals())
        print(report.render_markdown(data, baseline, regressions))
        stopped = report.blocking(regressions)
        for r in stopped:
            print(f"BLOCKED: {r.delta.key} fell from {r.delta.baseline:.2f} to {r.delta.score:.2f}", file=sys.stderr)
        return 1 if stopped else 0

    import httpx

    from hishob.agentkit.client import make_client
    from hishob.evals import live
    from hishob.evals.run import Systems, run_sets
    from hishob.ledger import Loader

    which = tuple(args.sets or SETS)
    api_url = args.api or os.environ.get("HISHOB_API_URL")
    if {"questions", "refusals"} & set(which) and not api_url:
        print("set --against (or HISHOB_API_URL): the desks read through the query API", file=sys.stderr)
        return 2
    client = make_client()
    held = build_archive(settings) if "extraction" in which else None
    with httpx.Client(base_url=api_url or "http://unused", timeout=180) as http:

        def extract(items: list[datasets.ExtractionItem]) -> Any:
            assert held is not None
            return live.extract_all(
                client, held, Loader(held.registry.conn, held, held.data), items, cap_usd=args.cap_usd
            )

        systems = Systems(extract=extract, ask=live.make_asker(client, http, args.token), workers=args.workers)
        result = run_sets(systems, which, commit=args.commit)
    out = Path(args.report)
    out.mkdir(parents=True, exist_ok=True)
    (out / "report.json").write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    baseline = report.load_baseline()
    regressions = report.gate(result, baseline, report.load_approvals())
    markdown = report.render_markdown(result, baseline, regressions)
    (out / "report.md").write_text(markdown, encoding="utf-8")
    print(markdown)
    return 0


def _audit_token() -> str | None:
    """The audit desk's own reviewer-tier token, signed for the service account `audit-desk` (SPEC-011/R1)."""
    import os

    from hishob.api.tiers import sign

    secret = os.environ.get("HISHOB_TOKEN_SECRET")
    return sign("reviewer", "audit-desk", secret) if secret else None


def _audit(args: argparse.Namespace, settings: Settings) -> int:
    import os
    import uuid
    from dataclasses import asdict
    from datetime import UTC, datetime

    import httpx

    from hishob.agentkit.audit import run_audit
    from hishob.agentkit.client import make_client

    api_url = args.api or os.environ.get("HISHOB_API_URL")
    token = _audit_token()
    if not api_url or not token:
        print("set --api (or HISHOB_API_URL) and HISHOB_TOKEN_SECRET: the desk reads as a reviewer", file=sys.stderr)
        return 2
    store = build_archive(settings)
    run_id = args.run_id or f"audit-{datetime.now(UTC):%Y%m%d-%H%M%S}-{uuid.uuid4().hex[:6]}"
    with httpx.Client(base_url=api_url, timeout=120) as http:
        run = run_audit(make_client(), http, args.ward, store.data, run_id=run_id, token=token, cap_usd=args.cap_usd)
    print(json.dumps(asdict(run), ensure_ascii=False, indent=2))
    return 0 if run.status == "complete" else 1


def _ontology_build(*, check: bool) -> int:
    from hishob.schema import build

    files = build.generate()
    if check:
        out_of_date = build.stale(files)
        if out_of_date:
            print("generated artefacts out of date: " + ", ".join(out_of_date), file=sys.stderr)
            print("run: uv run hishob ontology build", file=sys.stderr)
            return 1
        print("generated artefacts are up to date")
        return 0
    build.write(files)
    print("wrote: " + ", ".join(files))
    return 0


if __name__ == "__main__":
    sys.exit(main())
