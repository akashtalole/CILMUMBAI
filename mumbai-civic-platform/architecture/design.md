# Design and architecture

Aamcha Hishob on AWS. Read with the platform documents one level up; this file covers how it is built and run, and points to the decision record behind each choice.

## 1. Purpose and scope

A public service that answers, with sources, questions about how Mumbai's civic bodies allocate money, award contracts, carry out works and assign responsibility. It ingests published documents and residents' contributions, builds a knowledge graph, and serves residents, reporters, officials and other builders.

Out of scope: acting as an official record; filing complaints into government systems automatically; storing data about private individuals.

## 2. Requirements that shape the design

| Quality | Requirement | Design response |
|---|---|---|
| Correctness | No fact without a source; no answer without citations | Quote check at load, citation check at answer, both in code |
| Rebuildability | Any store can be lost and rebuilt | Archive and facts ledger on S3 are the record ([ADR 0001](adr/0001-facts-ledger-as-system-of-record.md)) |
| Low fixed cost | A civic project with little money must survive quiet months | Serverless and scale-down choices; two profiles ([ADR 0021](adr/0021-cost-posture.md)) |
| Small team | Two people must be able to run it | Managed services over self-run clusters; no Kubernetes ([ADR 0012](adr/0012-compute.md)) |
| Portability | No single vendor can end the project | Open formats on S3, Bolt for the graph, Postgres, prompts and rules in git |
| Safety | Untrusted documents and messages must not steer the system | Agents have no write or publish tools; graph is private ([ADR 0011](adr/0011-graph-tools-for-agents.md)) |
| Languages | Marathi, Hindi and English as equals | Glossary, tested embedding model, evaluation by language |
| Accountability of the platform itself | Every release and correction is traceable | Run, release and correction records; versioned agents |

Planning assumptions, to replace with measurements: tens of thousands of documents in the first year; a graph of a few million nodes and edges; residents' questions in the low thousands per day at most; intake in batches, not real time.

## 3. System context

```
  Residents ─ web, WhatsApp, voice ─┐                         ┌─ BMC portal, Mahatenders
  Reporters and researchers ────────┤                         ├─ Budget books, committee papers
  Ward and department officers ─────┼──►  MUMBAI NAGAR GRAPH ◄┼─ Other agencies, state directions
  Other builders ─ API, bulk data ──┤          on AWS         ├─ Courts, auditors
  Editors and lawyers ─ review ─────┘             │           └─ RTI replies, residents' reports
                                                  ▼
                                   Claude models and Managed Agents
                                   (Claude Platform on AWS)
```

## 4. Components on AWS

```
                               Internet
                                  │
                    ┌─────────────┴──────────────┐
                    │  CloudFront  +  WAF        │
                    └──────┬───────────────┬─────┘
                 static site│               │/api, /mcp
              ┌─────────────┴───┐   ┌───────┴────────────────────────────────────────┐
              │ S3: web assets, │   │ VPC (ap-south-1), private subnets              │
              │ map tiles,      │   │                                                │
              │ public exports  │   │  ALB ──► ECS Fargate services                  │
              └─────────────────┘   │           ├─ api          query layer, tiers   │
                                    │           ├─ public-mcp   read-only data tools │
   WhatsApp ──► End User Messaging  │           ├─ worker       LangGraph workflows, │
                 ──► SNS ──► SQS ───┼──────────►│               agent sessions,      │
                                    │           │               tool answering       │
   EventBridge Scheduler ──► SQS ───┼──────────►│                                    │
                                    │           └─ loader       validate, quote      │
   S3 event (new document) ─► SQS ──┼──────────►                check, write         │
                                    │                                                │
                                    │  ┌──────────────┐ ┌──────────────────────────┐ │
                                    │  │ Graph        │ │ Aurora PostgreSQL        │ │
                                    │  │ Neptune or   │ │ PostGIS · full text ·    │ │
                                    │  │ Neo4j (Bolt) │ │ pgvector · checkpoints · │ │
                                    │  └──────────────┘ │ queues · metrics · users │ │
                                    │                   └──────────────────────────┘ │
                                    │  ┌──────────────────────────────────────────┐  │
                                    │  │ S3: archive (versioned, locked) ·        │  │
                                    │  │     parsed text · facts ledger · exports │  │
                                    │  └──────────────────────────────────────────┘  │
                                    │                                                │
                                    │  NAT / VPC endpoints ──► Claude Platform on AWS│
                                    │                          (Messages, Batches,   │
                                    │                           Managed Agents)      │
                                    └────────────────────────────────────────────────┘
        Cognito (sign-in, tiers) · Secrets Manager · KMS · CloudWatch · OpenTelemetry
```

| Component | Role | Record |
|---|---|---|
| S3 archive | Every source document, immutable, with hash and fetch metadata | [0001](adr/0001-facts-ledger-as-system-of-record.md) |
| S3 facts ledger | Validated facts as append-only files, the input to every projection | [0001](adr/0001-facts-ledger-as-system-of-record.md) |
| Graph database | The ten graphs, for traversal | [0004](adr/0004-graph-database.md) |
| Aurora PostgreSQL | Geometry, text and vector search, workflow state, review queues, metrics, accounts | [0006](adr/0006-relational-and-spatial-store.md), [0007](adr/0007-search.md) |
| `worker` service | Runs LangGraph workflows, starts agent sessions, answers their graph tool calls | [0010](adr/0010-workflow-orchestration.md), [0011](adr/0011-graph-tools-for-agents.md) |
| `loader` service | Schema validation, quote check, writes to graph and indexes | [0001](adr/0001-facts-ledger-as-system-of-record.md) |
| `api` service | Query layer: routing, named views, metrics, access tiers, citation check | [0014](adr/0014-api-identity-and-access.md) |
| `public-mcp` service | The same read-only tools for outside assistants and builders | [0011](adr/0011-graph-tools-for-agents.md) |
| Claude Platform on AWS | Models, batches and Managed Agents | [0002](adr/0002-claude-access-on-aws.md), [0003](adr/0003-agent-runtime.md) |
| Queues and scheduler | Triggers and back-pressure | [0013](adr/0013-eventing.md) |
| Static site and tiles | Web application and maps | [0015](adr/0015-front-end-and-maps.md) |
| WhatsApp and speech | Resident channels | [0016](adr/0016-resident-channels.md) |

## 5. Data flow

### 5.1 Ingest

```
source ─► fetch or upload ─► S3 archive (hash, metadata) ─► S3 event ─► queue
      ─► worker: parse (text layer, else vision) ─► S3 parsed text
      ─► worker: W1 workflow ─► Managed Agents intake session
                                 (documents mounted as files; no network)
      ─► session outputs: facts, review, report ─► S3 staging
      ─► loader: schema check ─► quote check against parsed page ─► held queue or
         S3 facts ledger (append) ─► graph upsert ─► text and vector index ─► metrics refresh
```

The facts ledger is the hinge. Everything before it is extraction and can be redone with a better prompt; everything after it is projection and can be rebuilt with a different engine.

### 5.2 Answer

```
question ─► api: normalise, glossary, entities (one fast model call)
         ─► route: lookup · trail · metric · rule · exploratory
         ─► named view / metric engine / rules engine / hybrid retrieval, tier-filtered
         ─► citizen desk composes from tool results (Managed Agents session via worker)
         ─► api: citation check in code ─► reply with sources, tier, gaps
```

Lookups, trails, metrics and rule cards can also be served with no agent at all, as plain pages. The agent is used when the resident asks in free language or wants a letter drafted.

### 5.3 Audit and release

```
schedule ─► queue ─► worker: W1 from the audit step, one branch per ward
         ─► audit session (lead, challenger, drafter) ─► outputs to S3 staging
         ─► workflow pauses ─► reviewer decides in the review screen
         ─► approved outputs copied to public S3 prefix ─► site and feeds update
```

## 6. Storage layout

```
s3://nagar-archive/      source/<publisher>/<yyyy>/<sha256>.<ext>   + .meta.json     (versioned, object lock)
s3://nagar-data/         parsed/<sha256>/page-<n>.txt
                         facts/<graph>/<yyyy-mm-dd>/<batch>.jsonl                   (append-only)
                         staging/<session>/…                                         (expires)
                         exports/<release>/{jsonl,parquet,ttl}/…
s3://nagar-public/       site/ · tiles/ · published/<ward>/ · downloads/
```

Postgres schemas: `geo` (wards, roads, plots), `search` (passages, vectors, summaries), `flow` (LangGraph checkpoints, queues, reviews), `metric` (computed values), `account` (users, tiers, subscriptions), `registry` (documents, sources, freshness, runs).

## 7. Network and security

- One VPC in Mumbai across two availability zones. Databases and services sit in private subnets. Only CloudFront and the load balancer face the internet.
- The graph database has no public address. Agents never connect to it; they call tools that the worker answers ([ADR 0011](adr/0011-graph-tools-for-agents.md)).
- Managed Agents sandboxes run on Anthropic's side with no outbound hosts allowed and the web tools off. Documents reach them as mounted files; results leave as output files.
- Outbound calls to Claude go through a NAT gateway or a private endpoint if one is offered. Requests are signed with the task's IAM role; there is no long-lived API key.
- Each service has its own task role with the least access it needs: the loader can write the graph, the api can only read, the worker can start sessions and read and write staging.
- Encryption with KMS at rest; TLS in transit. Secrets in Secrets Manager.
- WAF rate limits and bot rules in front of the api and the public tools.
- Residents' images are stripped of faces and number plates, and messages of phone numbers, before storage or any model call ([ADR 0018](adr/0018-security-and-privacy.md)).

## 8. Deployment profiles

| | Lean (pilot, lowest fixed cost) | Standard (public service) |
|---|---|---|
| Graph | Neo4j Community, one Graviton instance, volume snapshots | Neptune Database Serverless, two zones |
| Postgres | Aurora Serverless v2, lowest setting, pausing if available | Aurora Serverless v2 with a reader |
| Search | Inside Postgres | Postgres, or OpenSearch Service if measurements call for it |
| Services | One task each on Fargate Spot where safe | Two tasks each across zones, autoscaling |
| Networking | One NAT instance or gateway | NAT gateways per zone, VPC endpoints |
| Environments | One account, two stages | Three accounts: development, staging, production |
| Recovery | Rebuild from S3 | Rebuild from S3, plus database snapshots for speed |

Both profiles use the same code and the same S3 record. Moving from lean to standard is a rebuild of projections, not a migration of truth.

## 9. Runtime sequences

### A resident asks on WhatsApp

1. WhatsApp message arrives through End User Messaging and lands on a queue.
2. The worker redacts personal details, transcribes a voice note if there is one, and passes the text to the api.
3. The api routes the question. For a trail, it runs named views directly.
4. If free-language composition is needed, the worker opens a citizen desk session, answers its tool calls from the api, and collects the reply.
5. The api checks citations and returns the answer; the worker sends it to WhatsApp.

### A new state direction is published

1. Source watch archives the document and classifies it as legal text.
2. The legal-change workflow starts a Regulation desk session; outputs are candidate rules with quotes.
3. The workflow pauses. A lawyer approves or edits the rules in the review screen.
4. Code recomputes jurisdiction cards, writes changed cards to the ledger, and notifies subscribers of affected plots.

### An agent definition changes

1. A pull request edits an agent file, rubric or rule.
2. CI applies it to the staging workspace and runs the three evaluation sets.
3. Results are compared with the last release by route and by language.
4. An owner approves; the change is applied to production. The earlier agent version stays available for rollback.

## 10. Failure and degradation

| Failure | Behaviour |
|---|---|
| Claude service unavailable or rate limited | Lookups, trails, metrics and cards still work as pages; free-language answers show a notice; intake queues wait |
| Graph database down | Site serves cached pages and published briefs from S3; api returns a clear notice; rebuild or failover |
| A portal changes format | Source watch flags the source as late; nothing wrong is loaded because the quote check fails closed |
| A bad prompt change slips through | Roll back to the pinned agent version; re-extract affected documents, identified by the version recorded on each fact |
| Wrong fact published | Correction workflow; history kept; affected answers identified through the facts they cited |

## 11. Open items

1. Confirm Claude Platform on AWS can be used from an account whose workloads are in Mumbai, and what a session's six-hour unattended limit means for long intake runs.
2. Run the ten competency queries on Neptune, Neo4j and HydraDB and record what each rejects.
3. Price both profiles in Mumbai.
4. Test two or three embedding models on a hundred real Marathi and Hindi questions.
5. Test scanned Marathi committee papers through each parsing route.
6. Ask a lawyer about cross-border processing of residents' messages under the Digital Personal Data Protection Act.
7. Decide the host organisation; it owns the AWS accounts.
