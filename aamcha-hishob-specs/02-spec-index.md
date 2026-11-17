# Spec index

## 1. All specs

Status of every spec is **Draft** until reviewed. Milestones are defined in [03-milestones.md](03-milestones.md).

### Foundations and hackathon slice (written in full)

| Spec | Title | Milestone | Depends on | Owner role | ADRs |
|---|---|---|---|---|---|
| [SPEC-001](specs/SPEC-001-document-archive.md) | Document archive and registry | M0 | | Data engineer | 0001, 0022 |
| [SPEC-002](specs/SPEC-002-ontology-and-schema.md) | Ontology, shapes and generated schema | M0 | | Graph engineer | 0005 |
| [SPEC-003](specs/SPEC-003-facts-ledger-and-loader.md) | Facts ledger and loader | M0 | 001, 002 | Graph engineer | 0001, 0004 |
| [SPEC-004](specs/SPEC-004-place-spine.md) | Place spine | M0 | 002, 003 | Data engineer | 0006, 0015 |
| [SPEC-005](specs/SPEC-005-intake-desk.md) | Intake desk | M0 | 001, 002, 003 | AI engineer | 0002, 0003, 0009 |
| [SPEC-006](specs/SPEC-006-graph-projection-and-views.md) | Graph projection and named views | M1 | 003, 004 | Graph engineer | 0004 |
| [SPEC-007](specs/SPEC-007-query-api.md) | Query API, access tiers and citation check | M1 | 006 | Back-end engineer | 0014 |
| [SPEC-008](specs/SPEC-008-citizen-desk.md) | Citizen desk | M1 | 007 | AI engineer | 0003, 0011 |
| [SPEC-009](specs/SPEC-009-workflow-engine.md) | Workflow engine and human gates | M1 | 003, 005 | Back-end engineer | 0010 |
| [SPEC-010](specs/SPEC-010-street-alerts.md) | Street alerts | M1 | 004, 006, 007 | Full-stack engineer | 0013, 0015 |
| [SPEC-011](specs/SPEC-011-audit-desk-and-release.md) | Audit desk and release | M1 | 007, 009 | AI engineer | 0003, 0011 |
| [SPEC-012](specs/SPEC-012-evaluation-and-promotion-gate.md) | Evaluation harness and promotion gate | M1 | 005, 007, 008 | AI engineer | 0019 |
| [SPEC-020](specs/SPEC-020-web-application.md) | Web application (resident view written; rest later) | M1 / M2 | 004, 006, 007, 008 | Full-stack engineer | 0014, 0015, 0016 |
| [SPEC-013](specs/SPEC-013-aws-lean-infrastructure.md) | AWS infrastructure, lean profile | M2 | 001 to 012 | Platform engineer | 0012, 0017, 0018, 0020, 0021 |

### Later specs (scope only; written when their milestone approaches)

| Spec | Title | Milestone | Scope |
|---|---|---|---|
| SPEC-014 | Source watch | M2 | Scheduled collection per source, change detection, freshness monitor, captcha-respecting assisted collection |
| SPEC-015 | Money graph and budget parser | M2 | Budget books into budget heads and allocations, reconciled to printed totals; Unspent Money Watch |
| SPEC-016 | Procurement graph completion | M2 | Awards, corrigenda, retenders, debarments, committee resolutions; joining BMC and Mahatenders ids |
| SPEC-017 | Hybrid search | M2 | Passages, full text and vectors in Postgres, routing, graph expansion, reranking |
| SPEC-018 | Metrics engine | M2 | Declarative metric definitions compiled to queries, with caveats |
| SPEC-019 | Resident channels | M2 | WhatsApp text and voice notes, redaction, transcription, place read-back |
| SPEC-020 (rest) | Web application | M2 | Ward pages, alerts sign-up, pre-rendered pages, own map tiles; the resident view is written above |
| SPEC-021 | Review screen | M2 | Queues for held facts, merges, findings and rules; resume paused workflows |
| SPEC-022 | Correction and right of reply | M2 | Requests, checks against sources, decisions with history, replies published beside records |
| SPEC-023 | RTI loop | M2 | Gaps to drafted applications, thirty-day clock, appeal drafts, ingest of replies |
| SPEC-024 | Promise tracker | M3 | Promise extraction, restatement chains, status rules |
| SPEC-025 | Liability watch and pothole ledger | M3 | Defect liability periods joined to residents' reports and complaints |
| SPEC-026 | Regulation desk and jurisdiction rules | M3 | Clauses, positions, rules as data, lawyer approval, jurisdiction cards |
| SPEC-027 | Land and planning graph (Ek Plot Ek Record) | M3 | Schemes, plots, status claims, tenement ledger for one ward |
| SPEC-028 | Steward desk | M3 | Duplicates, orphans, stale sources, schema drift; proposed fixes |
| SPEC-029 | Public data service | M3 | Read-only API keys, public MCP server, bulk exports in JSON lines, Parquet and Turtle |
| SPEC-030 | Standard profile infrastructure | M3 | Neptune Serverless, multi-zone, three accounts, replication |
| SPEC-031 | Newsroom feed and committee digest | M3 | Weekly sourced brief across wards |
| SPEC-032 | Analyst desk | M4 | Research notes for registered researchers |
| SPEC-033 | Services graph | M4 | Indicators and facilities with partner data |
| SPEC-034 | Open publishing kit | M4 | Specification, validator and converter for BMC to publish at source |

## 2. Dependency graph

```
SPEC-001 archive ─────┬──────────────┬───────────────────────────────┐
SPEC-002 ontology ──┬─┤              │                               │
                    │ ▼              ▼                               │
                    │ SPEC-003 ledger + loader ◄── SPEC-005 intake desk
                    │   │       │                       │
                    ▼   ▼       │                       ▼
              SPEC-004 place    │                SPEC-009 workflow engine
                    │   │       ▼                       │
                    │   └──► SPEC-006 graph + views     │
                    │               │                   │
                    │               ▼                   │
                    │        SPEC-007 query API ────────┼──────────┐
                    │          │        │               │          │
                    ▼          ▼        ▼               ▼          │
              SPEC-010 street alerts  SPEC-008 citizen  SPEC-011 audit + release
                                        │                          │
                                        └──────► SPEC-012 evaluation gate ◄──┘
                                                         │
                                                         ▼
                                              SPEC-013 AWS lean profile
```

## 3. Target code layout

The implementation lives in a new top-level folder, `app/`, created by SPEC-001. The starter code in `mumbai-civic-graph/managed-agents/` moves into it under SPEC-005, SPEC-008, SPEC-009 and SPEC-011.

```
app/
  pyproject.toml              Python 3.12; uv; ruff; mypy; pytest
  ontology/                   mco-*.ttl, shapes/, glossary.ttl, rules/        SPEC-002
  src/hishob/
    archive/                  storage, registry, fetch                        SPEC-001
    schema/                   generated record schema and whitelist           SPEC-002
    ledger/                   append-only facts files                         SPEC-003
    loader/                   validation, quote check, projections            SPEC-003, 006
    place/                    wards, roads, geocoding                         SPEC-004
    graphstore/               Bolt repository layer, named views              SPEC-006
    api/                      FastAPI app, tiers, citation check              SPEC-007
    agentkit/                 session runner, tool answering, outputs         SPEC-005, 008, 011
    workflows/                LangGraph graphs and gates                      SPEC-009
    alerts/                   subscriptions and notifications                 SPEC-010
    evals/                    runners and reports                             SPEC-012
  agents/                     agent, environment, memory files; rubrics       SPEC-005, 008, 011
  evals/                      datasets: extraction, questions, refusals       SPEC-012
  tests/
    unit/  contract/  integration/  e2e/  constitution/
  infra/terraform/            lean profile                                    SPEC-013
  docker-compose.yml          Neo4j, Postgres with PostGIS and pgvector, MinIO for local S3
web/                          static site (SPEC-020); a minimal page in SPEC-010
```

## 4. Progress

| Spec | Status | Acceptance criteria | With passing tests |
|---|---|---|---|
| SPEC-001 | In progress | 7 | 7 |
| SPEC-002 | In progress | 6 | 6 |
| SPEC-003 | In progress | 9 | 9 |
| SPEC-004 | In progress | 6 | 5 |
| SPEC-005 | In progress | 8 | 8 |
| SPEC-006 | In progress | 7 | 6 |
| SPEC-007 | In progress | 9 | 9 |
| SPEC-008 | In progress | 8 | 8 |
| SPEC-009 | In progress | 7 | 7 |
| SPEC-010 | In progress | 6 | 6 |
| SPEC-011 | In progress | 8 | 8 |
| SPEC-012 | In progress | 7 | 7 |
| SPEC-013 | Draft | 8 | 0 |
| SPEC-020 | In progress | 9 | 9 |

Update this table in the same pull request that changes a spec's status.
