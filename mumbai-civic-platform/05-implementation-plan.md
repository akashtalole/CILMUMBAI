# Implementation plan

Dates assume the event on 21 November 2026. Durations after that are planning estimates, not commitments, and depend most on how quickly data can be obtained.

## 1. Phases

### Phase 0: before the event (16 to 20 November)

| Goal | Tasks |
|---|---|
| Know what data is real | Open every P0 source in the catalogue; record format and access. Open five BMC road tenders on Mahatenders and note what detail, status and award pages show. |
| Choose the stores | Run HydraDB and Neo4j side by side with the competency queries; decide. Stand up Postgres with full-text, vector and spatial extensions. |
| Have a spine | Ward boundaries, named roads, corporators and the ward office's posts for one ward. |
| Have a corpus | Fifty tenders with notices and any awards; the roads budget pages for five years; two budget speeches. Archived with hashes. |
| Have agents | API key in hand; `ant apply`; one clean intake batch; rubrics tuned on real output. |
| Have a yardstick | Ten labelled documents and thirty verified questions. |

Detail: [../mumbai-civic-graph/06-prep-and-day-plan.md](../mumbai-civic-graph/06-prep-and-day-plan.md).

### Phase 1: the day (21 November)

One ward. Graphs: Place, Money, Procurement, Works and Assets, Organisation and Jurisdiction, Evidence. Three applications on them.

| Application | Shows |
|---|---|
| Work Coming to Your Street | The platform is useful to a resident today |
| Money trail with "who is responsible" | The joins work: budget to tender to contractor to road to office |
| Ward brief with one challenged case file and the gaps list | The intelligence layer, and honesty about what is missing |

Success on the day is a judge from the ward testing a road they know and getting a correct, sourced answer.

### Phase 2: first 30 days

| Track | Deliver |
|---|---|
| Coverage | All wards for procurement from January 2024; all departments' budgets for five years |
| Sources | Committee agendas weekly; penalties and debarments; other agencies' tenders |
| Search | Text, vector and spatial indexes; the five routes; citation checker; evaluation sets at starting size |
| Applications | Unspent Money Watch, Committee Digest, RTI Commons, Complaint Closure Audit |
| Operations | Source watch workflow; freshness monitor; review queue with a simple screen |
| Openness | Ontology and one ward's data published under an open licence |

### Phase 3: days 30 to 90

| Track | Deliver |
|---|---|
| Graphs | People and Representation; Law and Oversight; Voice at scale; Land and Planning for one ward |
| Desks | Regulation and Steward desks; legal-change and correction workflows |
| Service | Graph tools hosted behind the query layer; scheduled deployments; public API with rate limits |
| Applications | Promise tracker, Audit Para Tracker, Safety List, Pothole Ledger with liability watch, Ek Plot Ek Record pilot |
| Adoption | A 90-day pilot with one ward office; a weekly brief to local newsrooms |
| Access | WhatsApp text and voice notes in Marathi and Hindi |

### Phase 4: months 3 to 12

| Track | Deliver |
|---|---|
| Graphs | Services, with partner organisations in health, education and water |
| Standards | Open Publishing Kit piloted with one BMC department; linked open data endpoint |
| Applications | Rate Card, Monsoon Readiness (ready before March), Corporator Fund Tracker, Ward Participatory Budget pilot |
| Institution | A host organisation, an editorial board, funding, and a published governance charter |
| Reach | Other agencies in the metropolitan region on the same ontology |

## 2. Build order within the platform

Each row depends on those above it.

1. Archive and document registry
2. Place spine and glossary
3. Ontology core, shapes and the generated record schema
4. Intake desk, quote check, loader
5. Money and Procurement graphs
6. Works and Assets; Organisation and Jurisdiction
7. Named views and graph tools; Citizen desk
8. Audit desk; challenger; release step
9. Text, vector and spatial indexes; routing; citation checker
10. Metrics engine
11. Remaining graphs, one source at a time
12. Hosted tools, schedules, public API

## 3. Team

| Role | Day | Later |
|---|---|---|
| Product and domain lead | Decides scope; checks facts against reality | Owns the roadmap and partnerships |
| Data engineer | Corpus, parsing, archive | Source watch, pipelines |
| Graph and ontology engineer | Ontology, loader, queries | Ontology governance, linked data |
| AI engineer | Agent files, rubrics, runs | Evaluation, promotion gate, cost |
| Search engineer | Not needed on the day | Indexes, routing, citation checker |
| Front end | Map, trail, chat | Applications, review screen |
| Lawyer | Wording review | Rules approval, right of reply, publication sign-off |
| Editor or journalist | Finds the story | Release decisions, newsroom feed |
| Community organiser | Ground truth in the ward | Residents' groups, voice access, pilots |
| Marathi and Hindi reviewer | Checks every public sentence | Glossary, evaluation in both languages |

Four or five people cover the day by doubling up. The lawyer and the language reviewer are the two roles that cannot be skipped once anything is public.

## 4. Infrastructure

| Component | Day | Service |
|---|---|---|
| Graph | One container on a laptop | HydraDB on object storage, or Neo4j, with backups |
| Relational, spatial, text, vector | One Postgres container | Managed Postgres; OpenSearch if volume requires |
| Archive | A folder with a manifest | S3-compatible bucket with versioning |
| Agents | Managed Agents, sessions started from a laptop | Managed Agents with hosted tools and scheduled deployments |
| Orchestration | LangGraph with a SQLite checkpoint file | LangGraph with a Postgres checkpointer |
| Application and API | A local web server | A small container service behind a content delivery network |
| Observability | Console session traces | Tracing, cost and freshness dashboards, alerts |

Running costs are driven by three things: tokens for bulk extraction (one-off per document, lowest on the smallest model and in batches), tokens for audits and briefs (bounded by session budgets and schedule), and tokens for residents' questions (kept low by routing). Measure each in the first month before forecasting; this plan does not estimate them.

## 5. Governance

| Matter | Rule |
|---|---|
| Ownership | A neutral host: a university centre or an established civic organisation, not a vendor and not a party |
| Editorial | A small board including a lawyer and a journalist approves anything naming a party; decisions are logged |
| Method | Ontology, rules, rubrics and metric definitions are public |
| Corrections | Anyone can request one; each is answered; history is kept |
| Right of reply | Any named party's response is published beside the record |
| Data licence | Open licence for official-tier data; residents' contributions under clear consent |
| Privacy | Compliance with the Digital Personal Data Protection Act; no private individuals; deletion on request |
| Independence | No funding from contractors or developers with civic contracts; funders listed publicly |
| Relationship with BMC | Offered as a partner tool; the platform never presents itself as an official record |

## 6. Adoption path

1. **A ward office.** The liability watch and the complaint routing reduce their load. Ask for nothing but a meeting and feedback.
2. **Corporators and residents' associations.** Ward briefs and meeting questions; fund tracking for those who volunteer.
3. **Newsrooms.** The weekly feed, on equal terms.
4. **BMC's IT and finance departments.** The Open Publishing Kit: data published at source replaces reading PDFs after the fact.
5. **The state Urban Development Department.** The shared redevelopment register for disputes between authorities.

Each step produces evidence of use that makes the next conversation easier.

## 7. Measures

| Area | Measure |
|---|---|
| Coverage | Share of wards, departments and years in each graph; share of capital budget traced to at least a tender |
| Quality | Extraction accuracy; quote-match rate; evaluation scores by route and language; corrections per thousand facts |
| Freshness | Share of sources updated within their expected period |
| Use | Residents asking; subscriptions; complaints and RTIs drafted and filed; newsroom stories citing the platform |
| Effect | Defects repaired under liability; RTI gaps closed; audit observations answered; promises with evidence |
| Trust | Corrections resolved; replies published; officials using the work lists |

## 8. Risks

| Risk | Mitigation |
|---|---|
| Data cannot be obtained at the pace planned | Start where data is open; show gaps and file RTIs; partner for the rest; cut scope, never quality |
| Portals change or block collection | Source watch detects it; fall back to requests and assisted collection; never defeat access controls |
| A wrong fact about a named party is published | The layered checks above; fast, visible correction; legal review before release |
| Seen as partisan | Identical treatment, public method, mixed editorial board |
| HydraDB proves immature | Bolt-only access and a tested Neo4j fallback |
| Dependence on one model provider or beta features | Prompts, rules and evaluations in version control; agents behind a thin client; the graph and archive are independent of any model |
| Cost grows with use | Routing, caching, budgets, batches; measure before scaling |
| Team disperses after the event | Open everything; find the host organisation early; keep the first slice small enough for two people to run |
| Marathi quality lags English | A named reviewer; evaluation reported by language; no release that regresses either |

## 9. The first ten things to do

1. Get an API key working and run the dry-run pipeline, then one real intake batch.
2. Open five BMC road tenders on Mahatenders and write down exactly what each page shows.
3. Choose the ward.
4. Run both graph databases against the ten competency questions.
5. Download the roads budget pages for five years and check that leaf totals reconcile.
6. Build the place spine for the ward.
7. Hand-label ten documents and write thirty questions.
8. Ask the organisers what data the authorities will bring.
9. Recruit a lawyer and a Marathi reviewer.
10. Write the three-minute demo script, then cut everything not needed for it.
