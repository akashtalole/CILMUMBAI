# Aamcha Hishob: application

The implementation of [Aamcha Hishob](../mumbai-civic-platform/README.md), built spec by spec from [../aamcha-hishob-specs/](../aamcha-hishob-specs/). Read the [constitution](../aamcha-hishob-specs/00-constitution.md) before changing anything.

## What is built

| Spec | Status | What works |
|---|---|---|
| [SPEC-001](../aamcha-hishob-specs/specs/SPEC-001-document-archive.md) Document archive and registry | All 7 acceptance criteria pass; awaiting review | Archive files, URLs and uploads by content hash; never overwrite or delete; registry in Postgres; page text extraction; events to a file or SQS; command line |
| [SPEC-003](../aamcha-hishob-specs/specs/SPEC-003-facts-ledger-and-loader.md) Facts ledger and loader | All 9 acceptance criteria pass; awaiting review | Validates extracted facts (schema, properties, SHACL per batch, source and page, quote check, edge endpoints), appends accepted facts to an append-only ledger, holds the rest with reasons, handles supersession and corroboration, and rebuilds its index from the ledger alone |
| [SPEC-005](../aamcha-hishob-specs/specs/SPEC-005-intake-desk.md) Intake desk | All 8 acceptance criteria pass (one only in the live test); awaiting review | Agent definitions in `agents/`, applied to a Claude account; intake sessions that read archived documents with extractor, verifier and resolver agents, then hand the facts to the loader and record the run. First live run: 3 documents read for $1.63 |
| [SPEC-002](../aamcha-hishob-specs/specs/SPEC-002-ontology-and-schema.md) Ontology, shapes and generated schema | All 6 acceptance criteria pass; awaiting review | Mumbai Civic Ontology in Turtle (39 node labels, 32 relationship types, English and draft Marathi labels); SHACL shapes; generated record schema, whitelist and [reference page](ontology/REFERENCE.md); validators the loader will use |

## Set up

Needs Python 3.12, [uv](https://docs.astral.sh/uv/), and Postgres 16 with PostGIS 3 (the place spine, SPEC-004, needs it). On Ubuntu: `apt-get install postgresql-16-postgis-3`. In the project's Claude Code cloud environment a setup script installs it; if Postgres is not running in a session, start it with `service postgresql start`.

```sh
cd app
uv sync
docker compose up -d postgres          # or any local Postgres
export HISHOB_DATABASE_URL=postgresql://postgres:hishob@localhost:5432/hishob
uv run hishob db migrate
```

## Use

```sh
uv run hishob archive add ./tender.pdf --publisher bmc --licence "BMC public notice"
uv run hishob archive add https://example.gov.in/notice.pdf --publisher bmc --licence "BMC public notice"
uv run hishob archive show <sha256>
uv run hishob load facts.jsonl --batch b-001 --extractor doc-extractor@1
uv run hishob agents apply              # create or update the agents in the Claude account
uv run hishob intake run <sha256> [<sha256> ...] --cap-usd 5
uv run hishob ontology build            # after editing ontology/*.ttl
uv run hishob ontology build --check    # CI fails if generated files are stale
```

By default documents are stored under `./var/` and events appended to `./var/events.jsonl`. For S3 and SQS:

| Variable | Meaning | Default |
|---|---|---|
| `HISHOB_DATABASE_URL` | Postgres connection | `postgresql://postgres:hishob@localhost:5432/hishob` |
| `HISHOB_STORAGE` | `local` or `s3` | `local` |
| `HISHOB_LOCAL_ROOT` | Folder for local storage and events | `var` |
| `HISHOB_ARCHIVE_BUCKET`, `HISHOB_DATA_BUCKET` | Buckets when `HISHOB_STORAGE=s3` | `hishob-archive`, `hishob-data` |
| `HISHOB_EVENTS`, `HISHOB_EVENTS_QUEUE_URL` | `log` or `sqs`, and the queue | `log` |
| `HISHOB_FETCH_DELAY_S` | Seconds between requests to one host | `5` |

The archive bucket must have versioning and object lock. Production buckets come from Terraform (SPEC-013); `hishob.archive.storage.create_archive_bucket` does the same for tests.

## Test

```sh
createdb hishob_test   # once
psql -d hishob_test -c 'CREATE EXTENSION IF NOT EXISTS postgis' -c 'CREATE EXTENSION IF NOT EXISTS pg_trgm'
export HISHOB_TEST_DATABASE_URL=postgresql://postgres:hishob@localhost:5432/hishob_test
uv run ruff check src tests && uv run ruff format --check src tests
uv run mypy
uv run pytest
```

Tests that need Postgres skip themselves if it is not reachable. Live tests call the Claude API and cost money; they run only with `HISHOB_LIVE=1` and a credential (`ANTHROPIC_API_KEY`, or Claude Platform on AWS with `ANTHROPIC_AWS_WORKSPACE_ID`). Acceptance tests are named after the criteria they verify, for example `test_spec001_ac3_…`. S3 and SQS are tested against an in-process mock.

Fixtures in `tests/fixtures/` are invented documents marked as test data. `make_fixtures.py` regenerates them and needs a Devanagari font such as Noto Sans Devanagari.

## Layout

```
app/
  migrations/            SQL, applied in name order by `hishob db migrate`
  src/hishob/
  ontology/              SPEC-002: mco-*.ttl, shapes/, VERSION, generated REFERENCE.md
    archive/             SPEC-001: media, pages, scripts, storage, registry, fetch, events, service
    schema/              SPEC-002: model, build, whitelist, validate; generated records.json and whitelist.json
    ledger/              SPEC-003: quote check, loader, ledger index
    agentkit/            SPEC-005: client, agent definitions, provisioning, session loop, intake runner
  agents/                agent definitions (Markdown with YAML front matter), environment, rubrics
    cli.py  config.py  db.py
  tests/unit/            no database needed
  tests/integration/     acceptance tests; need Postgres
```
