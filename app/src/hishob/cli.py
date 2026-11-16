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

    agents = groups.add_parser("agents").add_subparsers(dest="command", required=True)
    agents.add_parser("apply", help="create or update the agents and environment in the Claude account")
    intake = groups.add_parser("intake").add_subparsers(dest="command", required=True)
    run_cmd = intake.add_parser("run", help="read archived documents with the intake desk (SPEC-005)")
    run_cmd.add_argument("sha256", nargs="+")
    run_cmd.add_argument("--cap-usd", type=int, default=5, help="hard spending cap for the session, in dollars")

    ontology = groups.add_parser("ontology").add_subparsers(dest="command", required=True)
    build = ontology.add_parser("build", help="generate the record schema, whitelist and reference page")
    build.add_argument("--check", action="store_true", help="fail if the committed files are out of date")

    args = parser.parse_args(argv)
    if args.group == "ontology":
        return _ontology_build(check=args.check)
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
            print(json.dumps(asdict(result)))
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
