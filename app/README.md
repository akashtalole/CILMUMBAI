# Aamcha Hishob: application

The implementation of [Aamcha Hishob](../mumbai-civic-platform/README.md), built spec by spec from [../aamcha-hishob-specs/](../aamcha-hishob-specs/). Read the [constitution](../aamcha-hishob-specs/00-constitution.md) before changing anything.

## What is built

| Spec | Status | What works |
|---|---|---|
| [SPEC-001](../aamcha-hishob-specs/specs/SPEC-001-document-archive.md) Document archive and registry | All 7 acceptance criteria pass; awaiting review | Archive files, URLs and uploads by content hash; never overwrite or delete; registry in Postgres; page text extraction; events to a file or SQS; command line |
| [SPEC-003](../aamcha-hishob-specs/specs/SPEC-003-facts-ledger-and-loader.md) Facts ledger and loader | All 9 acceptance criteria pass; awaiting review | Validates extracted facts (schema, properties, SHACL per batch, source and page, quote check, edge endpoints), appends accepted facts to an append-only ledger, holds the rest with reasons, handles supersession and corroboration, and rebuilds its index from the ledger alone |
| [SPEC-004](../aamcha-hishob-specs/specs/SPEC-004-place-spine.md) Place spine | AC1 to AC5 pass; field test and K/West roads pending | Ward and road importers that archive each file and load checked facts; geo tables in PostGIS rebuilt from the ledger; `find_place` across Marathi and English; `at_point` for road and wards. Real BMC ward boundaries load and resolve correctly. See [the loading guide](src/hishob/place/README.md) |
| [SPEC-006](../aamcha-hishob-specs/specs/SPEC-006-graph-projection-and-views.md) Graph projection and named views | 6 of 7 acceptance criteria pass; the Neptune run waits for an instance | Projects the ledger into Neo4j over Bolt with per-property provenance and fact history; five named views (`trace_money`, `who_is_responsible`, `work_status`, `ward_summary`, `gaps_for`) that list missing records as gaps |
| [SPEC-007](../aamcha-hishob-specs/specs/SPEC-007-query-api.md) Query API, access tiers and citation check | All 9 acceptance criteria pass; awaiting review | HTTP API for places, points, named views, facts, source pages and answer checking; every request under one tier; results filtered by tier and given quotes and fetch dates; citation check for amounts, dates, identifiers and names in English, Marathi and Hindi; request log without personal data; rate limit for the public. [OpenAPI document](api/openapi.json) |
| [SPEC-008](../aamcha-hishob-specs/specs/SPEC-008-citizen-desk.md) Citizen desk | All 8 acceptance criteria pass, plus a live run; awaiting review | One agent answers a resident in Marathi, Hindi or English through the API: redaction first, read-only tools, every reply checked in code (citations, language, no private names, liability date), one rewrite, then a fallback built in code. First live answer in Marathi cost $0.05 |
| [SPEC-009](../aamcha-hishob-specs/specs/SPEC-009-workflow-engine.md) Workflow engine | All 7 acceptance criteria pass with stubbed desks; no live run of the whole workflow yet | LangGraph W1 checkpointed to Postgres: intake, a review gate when too many facts are held, one audit per ward in parallel, a release gate only a reviewer can answer (with a recorded reason), then publishing that is safe to repeat. Started from the command line or a queue. The audit step is the SPEC-011 desk |
| [SPEC-011](../aamcha-hishob-specs/specs/SPEC-011-audit-desk-and-release.md) Audit desk | All 8 acceptance criteria pass, plus a live run; awaiting review | The audit lead reads the graph as a reviewer and writes a ward brief, case files, drafts and a gaps file. A Challenger reviews every case; code places cases by its verdict, checks every figure against the cited fact, bans conclusion words in three languages and names other than posts, asks the lead to fix problems once, then holds what still fails. First live run on K/W: $2.54, an honest brief on thin records, 8 RTI drafts |
| [SPEC-005](../aamcha-hishob-specs/specs/SPEC-005-intake-desk.md) Intake desk | All 8 acceptance criteria pass (one only in the live test); awaiting review | Agent definitions in `agents/`, applied to a Claude account; intake sessions that read archived documents with extractor, verifier and resolver agents, then hand the facts to the loader and record the run. First live run: 3 documents read for $1.63 |
| [SPEC-002](../aamcha-hishob-specs/specs/SPEC-002-ontology-and-schema.md) Ontology, shapes and generated schema | All 6 acceptance criteria pass; awaiting review | Mumbai Civic Ontology in Turtle (39 node labels, 32 relationship types, English and draft Marathi labels); SHACL shapes; generated record schema, whitelist and [reference page](ontology/REFERENCE.md); validators the loader will use |

## Set up

Needs Python 3.12, [uv](https://docs.astral.sh/uv/), Neo4j 5 (Community is enough; `docker compose up -d neo4j`, or the tarball from neo4j.com with Java 21), and Postgres 16 with PostGIS 3 (the place spine, SPEC-004, needs it). On Ubuntu: `apt-get install postgresql-16-postgis-3`. In the project's Claude Code cloud environment a setup script installs it; if Postgres is not running in a session, start it with `service postgresql start`.

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
uv run hishob place import-wards BMC_Wards.geojson --kind admin --name-property name --publisher datameet \
  --licence "..." --batch wards-1        # see src/hishob/place/README.md
uv run hishob place find "SV road"
uv run hishob place at 19.0988 72.8267
uv run hishob graph apply               # project new ledger facts into the graph
uv run hishob graph view trace_money road:sv
uv run hishob graph view who_is_responsible road:sv --issue pothole
uv run uvicorn hishob.api.app:serve --factory --port 8000   # the query API; set HISHOB_TOKEN_SECRET for tiers
uv run hishob api openapi               # regenerate api/openapi.json after changing the API
uv run hishob ask "एस. व्ही. रोडवरील खड्डा कोण दुरुस्त करणार?" --api http://127.0.0.1:8000
uv run hishob agents apply              # create or update the agents in the Claude account
uv run hishob intake run <sha256> [<sha256> ...] --cap-usd 5
uv run hishob audit run K/W --api http://127.0.0.1:8000 --cap-usd 10   # needs HISHOB_TOKEN_SECRET
uv run hishob workflow run t1 --hash <sha256> --ward K/W   # W1 to the release gate; set HISHOB_API_URL
uv run hishob workflow status t1
uv run hishob workflow resume t1 approve --reason "checked the brief" --token <reviewer token>
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
| `HISHOB_TOKEN_SECRET` | Secret that signs access-tier tokens (API and `workflow resume`) | none: everyone is public |
| `HISHOB_API_URL` | Query API the workflow's audit step reads through | none |
| `HISHOB_PUBLIC_BUCKET` | Where released outputs are published when `HISHOB_STORAGE=s3` (locally: `var/public/`) | none |

The archive bucket must have versioning and object lock. Production buckets come from Terraform (SPEC-013); `hishob.archive.storage.create_archive_bucket` does the same for tests.

## Web app: resident view (SPEC-020)

```sh
createdb hishob_demo && psql -d hishob_demo -c 'CREATE EXTENSION postgis' -c 'CREATE EXTENSION pg_trgm'
export HISHOB_DATABASE_URL=postgresql://postgres:hishob@localhost:5432/hishob_demo HISHOB_LOCAL_ROOT=var/demo
uv run python demo/seed.py                              # the synthetic S. V. Road scenario
(cd web && npm ci && VITE_DATA_NOTICE="Demo data: invented test documents" npm run build)
uv run uvicorn hishob.api.app:serve --factory --port 8000  # page at http://127.0.0.1:8000/
node web/e2e/resident.mjs                               # browser check, phone and desktop
```

Set `ANTHROPIC_API_KEY` (and apply the agents) to switch on the Ask tab. For live reloading while editing the page, run `npm run dev` in `web/`; it proxies the API. The test suite empties the shared graph, so run `uv run hishob graph rebuild` with the demo settings afterwards.

## Deploy to AWS (demo)

From AWS CloudShell: `cd app/deploy/cloudshell && ./deploy.sh`, and `./teardown.sh` to remove it. One CloudFormation stack in Mumbai: an instance running the API, worker, Postgres and Neo4j behind CloudFront, with S3, SQS and Secrets Manager. Not yet run against a real account; see [deploy/cloudshell/README.md](deploy/cloudshell/README.md). The production profile is SPEC-013.

## Test

```sh
createdb hishob_test   # once
psql -d hishob_test -c 'CREATE EXTENSION IF NOT EXISTS postgis' -c 'CREATE EXTENSION IF NOT EXISTS pg_trgm'
export HISHOB_TEST_DATABASE_URL=postgresql://postgres:hishob@localhost:5432/hishob_test
uv run ruff check src tests && uv run ruff format --check src tests
uv run mypy
uv run pytest
```

Tests that need Postgres skip themselves if it is not reachable; so do graph tests without Neo4j (`HISHOB_TEST_GRAPH_URI`, default `neo4j://127.0.0.1:7687`). **Graph tests delete everything in that database**: point them at a test instance only. Live tests call the Claude API and cost money; they run only with `HISHOB_LIVE=1` and a credential (`ANTHROPIC_API_KEY`, or Claude Platform on AWS with `ANTHROPIC_AWS_WORKSPACE_ID`). Acceptance tests are named after the criteria they verify, for example `test_spec001_ac3_…`. S3 and SQS are tested against an in-process mock.

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
    place/               SPEC-004: name normalising, importers, geo tables and lookups
    graphstore/          SPEC-006: projection into the graph, named views, Bolt driver
    api/                 SPEC-007: FastAPI app, tiers, access rules, citation check, rate limit
  api/openapi.json       generated; CI fails if stale
    agentkit/            SPEC-005: client, agent definitions, provisioning, session loop, intake runner
  agents/                agent definitions (Markdown with YAML front matter), environment, rubrics
    cli.py  config.py  db.py
  tests/unit/            no database needed
  tests/integration/     acceptance tests; need Postgres
```
