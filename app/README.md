# Aamcha Hishob: application

The implementation of [Aamcha Hishob](../mumbai-civic-platform/README.md), built spec by spec from [../aamcha-hishob-specs/](../aamcha-hishob-specs/). Read the [constitution](../aamcha-hishob-specs/00-constitution.md) before changing anything.

## What is built

| Spec | Status | What works |
|---|---|---|
| [SPEC-001](../aamcha-hishob-specs/specs/SPEC-001-document-archive.md) Document archive and registry | All 7 acceptance criteria pass; awaiting review | Archive files, URLs and uploads by content hash; never overwrite or delete; registry in Postgres; page text extraction; events to a file or SQS; command line |

## Set up

Needs Python 3.12, [uv](https://docs.astral.sh/uv/) and Postgres 16.

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
export HISHOB_TEST_DATABASE_URL=postgresql://postgres:hishob@localhost:5432/hishob_test
uv run ruff check src tests && uv run ruff format --check src tests
uv run mypy
uv run pytest
```

Tests that need Postgres skip themselves if it is not reachable. Acceptance tests are named after the criteria they verify, for example `test_spec001_ac3_…`. S3 and SQS are tested against an in-process mock.

Fixtures in `tests/fixtures/` are invented documents marked as test data. `make_fixtures.py` regenerates them and needs a Devanagari font such as Noto Sans Devanagari.

## Layout

```
app/
  migrations/            SQL, applied in name order by `hishob db migrate`
  src/hishob/
    archive/             SPEC-001: media, pages, scripts, storage, registry, fetch, events, service
    cli.py  config.py  db.py
  tests/unit/            no database needed
  tests/integration/     acceptance tests; need Postgres
```
