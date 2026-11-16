"""Command line: `hishob db migrate`, `hishob archive add|show`, `hishob ontology build [--check]`."""

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

    ontology = groups.add_parser("ontology").add_subparsers(dest="command", required=True)
    build = ontology.add_parser("build", help="generate the record schema, whitelist and reference page")
    build.add_argument("--check", action="store_true", help="fail if the committed files are out of date")

    args = parser.parse_args(argv)
    if args.group == "ontology":
        return _ontology_build(check=args.check)
    settings = Settings.from_env()

    if args.group == "db":
        applied = db.migrate(db.connect(settings.database_url))
        print("applied: " + (", ".join(applied) or "nothing new"))
        return 0

    store = build_archive(settings)
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
