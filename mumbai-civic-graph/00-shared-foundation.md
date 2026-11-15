# Shared foundation

Everything the five ideas have in common: the ontology, the graph database, the data, the pipeline and the rules for using Claude. Build this once.

## 1. The problem in numbers

- BMC's 2026-27 budget is ₹80,952.56 crore, of which about ₹48,164 crore is capital works (press reports of the budget presentation).
- Civic data reported in the press showed more than half of the 2025-26 capital allocation unspent late in that year.
- On road concretisation, press reports from 2025 put Phase 1 at 46 km complete out of 324 km, with contractors fined and blacklisted for delays and poor quality.

A citizen can read each of those facts in a newspaper. What they cannot do is start from *their* road and find the budget line, the contractor and the deadline. That is the gap.

## 2. Mumbai Civic Ontology (MCO)

A small ontology, written once in OWL/Turtle, that every idea shares. Reuse established vocabularies rather than inventing terms, so the result is recognisable to civic-tech people and exportable.

### Vocabularies to reuse

| Need | Vocabulary |
|---|---|
| Tenders, awards, contracts, payments | Open Contracting Data Standard (OCDS) concepts |
| Departments, posts, reporting lines | W3C Organization Ontology (`org:`) |
| People, posts, memberships of elected bodies | Popolo |
| Where every fact came from | W3C PROV-O (`prov:`) |
| Ward boundaries, road geometry | GeoSPARQL |
| Budget head hierarchy, work categories | SKOS |
| Validity periods, deadlines | OWL-Time |

### Core classes

```
Money        FiscalYear, BudgetHead, Allocation, Expenditure, Payment
Procurement  Tender, Bid, Award, Contract, WorkOrder, Penalty, Blacklisting
Work         Work (a project), Milestone, Inspection, DefectLiabilityPeriod
Asset        Road, Drain, Bridge, School, Hospital, Garden, Toilet
Place        AdminWard, ElectoralWard, Locality, Geometry
Actor        Agency (BMC, MMRDA, MSRDC, PWD, MHADA, Railways…),
             Department, Post, Person, Contractor, Company, Director
Voice        Promise, Complaint, RTIRequest, CitizenReport, NewsReport
Evidence     SourceDocument, Claim
```

### Core relationships

```
(BudgetHead)-[:PARENT_OF]->(BudgetHead)
(Allocation)-[:UNDER]->(BudgetHead)        (Allocation)-[:FOR_YEAR]->(FiscalYear)
(Work)-[:FUNDED_BY]->(Allocation)          (Work)-[:IMPROVES]->(Asset)
(Tender)-[:FOR_WORK]->(Work)               (Bid)-[:ON]->(Tender)
(Contractor)-[:SUBMITTED]->(Bid)           (Award)-[:OF]->(Tender)
(Contract)-[:FROM_AWARD]->(Award)          (Contractor)-[:PARTY_TO]->(Contract)
(Contract)-[:FOR_WORK]->(Work)             // shortcut, written at load time from Award → Tender → Work
(Payment)-[:UNDER_CONTRACT]->(Contract)    (Penalty)-[:IMPOSED_ON]->(Contractor)
(Asset)-[:LOCATED_IN]->(AdminWard)         (ElectoralWard)-[:WITHIN]->(AdminWard)
(Agency)-[:OWNS]->(Asset)                  (Department)-[:PART_OF]->(Agency)
(Post)-[:IN]->(Department)                 (Post)-[:RESPONSIBLE_FOR]->(Work|Asset|AdminWard)
(Person)-[:HOLDS {from,to}]->(Post)        (Person)-[:REPRESENTS]->(ElectoralWard)
(Promise)-[:MADE_BY]->(Person|Agency)      (Promise)-[:FULFILLED_BY]->(Work)
(Complaint)-[:ABOUT]->(Asset)              (Claim)-[:SUPPORTED_BY]->(SourceDocument)
```

### Three rules that make the graph trustworthy

1. **Every fact has a source.** Each node and relationship carries `source_id`, `page`, `quote`, `extracted_at`, `confidence`. No source, no edge. The UI shows the quote and links to the page.
2. **Every fact has a trust tier.** `official` (BMC document), `reported` (news), `citizen` (unverified upload), `derived` (computed by us). Answers say which tier they rest on.
3. **Facts are dated, not overwritten.** `valid_from` / `valid_to` on relationships. A revised deadline is a new edge, so slippage is visible as history.

### Keep the ontology in Turtle, compile it to the property graph

- `ontology/mco.ttl` is the source of truth: classes, properties, domains and ranges.
- `ontology/shapes.ttl` holds SHACL shapes (a Contract must have exactly one Award; an amount must be a positive decimal with a currency).
- A small script generates three things from those files: the JSON schema Claude must fill during extraction, the validation step in the pipeline (pySHACL over an rdflib graph of each batch), and the label and relationship whitelist for the property graph.

This gives ontology discipline without needing a reasoner inside the database.

## 3. Graph database choice

### HydraDB, as asked

From its README: HydraDB is a distributed graph database in Rust, built on SlateDB with S3-compatible object storage as the source of truth, with traversal on SuiteSparse GraphBLAS. It speaks a practical OpenCypher subset over **Neo4j-compatible Bolt 5.x** and an HTTP JSON API. Licence is Elastic License 2.0.

| For this project | Against |
|---|---|
| Bolt-compatible, so the standard `neo4j` Python and JS drivers work | v0.3; young, few independent evaluations |
| Object storage backend makes it cheap to host a public, read-heavy civic dataset | Cypher is a subset: check `MERGE`, `DETACH DELETE` and multi-row mutations against `cypher-compat.md` |
| Built-in path procedures (`algo.SPpaths`, `algo.SSpaths`) suit "follow the money" queries | README mentions no vector or full-text index, so those live elsewhere |
| Per-graph namespaces map well to "one graph per city or agency" | Needs building from source or a container image; allow setup time |

ELv2 permits self-hosting and modification. It forbids offering the database itself as a managed service, which does not affect a civic app built on top of it.

### Alternatives

| Database | Model | Why consider it | Caveat |
|---|---|---|---|
| **Neo4j Community** | Property graph, Cypher | Default choice; vector and full-text indexes built in; `neosemantics` imports RDF/OWL directly; Graph Data Science for community detection | JVM memory footprint; GPLv3 |
| **FalkorDB** | Property graph, Cypher, GraphBLAS | Fast; vector index; aimed at GraphRAG | Source-available licence; check terms |
| **Memgraph** | Property graph, Cypher | In-memory, Neo4j-driver compatible | BSL licence |
| **Kuzu** | Embedded property graph | Zero-ops, runs in-process; ideal for a laptop demo | Community-maintained now |
| **Apache Jena Fuseki / Oxigraph / Ontotext GraphDB** | RDF triple store, SPARQL | Native OWL and SHACL, real inference | Slower to build an app on; weaker path queries |

### Decision

- **Primary store: HydraDB**, accessed only through the Bolt driver and a thin repository layer.
- **Fallback: Neo4j Community in Docker**, same driver, same queries. Decide by the end of the pre-event spike. If HydraDB rejects a query shape the app needs, switch and lose nothing.
- **Ontology and validation: Turtle + SHACL in the pipeline** (rdflib, pySHACL), not in the database.
- **Text search and embeddings: Postgres with pgvector** (or SQLite with FTS5 for the demo), keyed by graph node id. Used to find the starting node; the graph does the reasoning.

Write all Cypher inside the subset HydraDB documents: typed relationships, bounded variable-length paths, `OPTIONAL MATCH`, aggregation, `UNWIND` batch writes. Avoid APOC and Neo4j-only procedures so the fallback works in both directions.

## 4. Data sources

Confirm each of these in the pre-event spike. Format and availability change without notice.

| Source | Gives | Format | Difficulty |
|---|---|---|---|
| BMC budget books (budget estimates, by department and budget code) | BudgetHead, Allocation | PDF, partly scanned | Medium |
| Budget speech of the Municipal Commissioner | Promises, headline allocations | PDF text | Low |
| BMC e-tender notices (`mcgm.gov.in` tender documents) and Mahatenders | Tender, Work, estimated cost, ward | PDF | Medium |
| Standing Committee and Improvements Committee agendas and resolutions | Award, Contractor, sanctioned cost | PDF, Marathi and English | High |
| BMC road concretisation dashboard (launched September 2025) | Work status, contractor, road, dates | Web | Medium |
| OpenCity.in | Cleaned budget and civic datasets, ward boundaries | CSV, GeoJSON | Low |
| Ward boundary files (administrative and 227 electoral wards) | AdminWard, ElectoralWard geometry | GeoJSON, KML | Low |
| OpenStreetMap | Road geometry and names | API | Low |
| Corporator list and committee memberships | Person, Post, REPRESENTS | Web | Low |
| News archives (English and Marathi) | Penalty, Blacklisting, delays, Promises | Web text | Low |
| Praja Foundation reports | Complaint statistics, ward indicators | PDF | Medium |
| RTI replies shared by activists | Payments, measurement details | Scans | High |
| Ministry of Corporate Affairs company data | Company, Director | Portal, partly paid | High |

MumbaiSpend (IndiaSpend, 2017) once published BMC vendor and purchase-order data. Check whether it is still live; if so it is the best single seed for Contractor and Payment nodes.

**Ask the organisers now** whether the problem briefing comes with data from BMC. If it does, most of the "High" rows become easy.

## 5. Architecture

```
            ┌───────────── Sources (PDF, web, CSV, photos) ─────────────┐
            ▼                                                            │
   1. Fetch and archive      raw file + hash + URL + fetched_at          │
            ▼                                                            │
   2. Parse                  PDF text / OCR / tables; Marathi kept as-is │
            ▼                                                            │
   3. Extract (Claude)       JSON constrained by the ontology schema,    │
                             with page and verbatim quote per fact       │
            ▼                                                            │
   4. Validate               SHACL shapes; reject or queue for review    │
            ▼                                                            │
   5. Resolve entities       same contractor, road, ward across sources  │
            ▼                                                            │
   6. Load                   UNWIND batches over Bolt → HydraDB          │
            ▼                                                            │
   7. Serve                  API + MCP server ── Claude agent ── Web/WhatsApp UI
```

Suggested stack: Python (FastAPI, `neo4j` driver, rdflib, pySHACL, PyMuPDF), Postgres with pgvector, a Next.js or plain React front end with MapLibre for maps.

### Serving through MCP

Expose the graph as a small MCP server rather than letting the model write free-form Cypher against a public dataset:

| Tool | Purpose |
|---|---|
| `find_entity(text, type?)` | Fuzzy and semantic lookup to a node id |
| `locate(lat, lon)` | Asset, ward and owning agency at a point |
| `trace_money(node_id)` | Budget head ↔ work ↔ contract ↔ payments path |
| `who_is_responsible(node_id)` | Agency, department, post, current holder, contractor under liability |
| `work_status(work_id)` | Milestones, deadlines, revisions, penalties |
| `cypher_read(query)` | Read-only escape hatch, with a label whitelist and row limit |
| `get_source(source_id, page)` | The quote and link behind any fact |

Every tool returns facts with their `source_id` and trust tier, so the agent can cite. The same server works from Claude Desktop, Claude Code or the web app, which is a useful point when pitching adoption: BMC staff and journalists can query it with tools they already have.

## 6. How Claude is used

| Job | Notes |
|---|---|
| Document extraction | One document at a time, schema-constrained output, quote and page mandatory. Use a larger model for committee resolutions and a small fast one for routine tender notices. |
| Marathi and Hindi | Extract directly from Marathi text; store the original name and an English transliteration on each node. |
| Entity resolution | Blocking by normalised name and ward, then Claude adjudicates candidate pairs with a reason. Never auto-merge people. |
| Question answering | Agent over the MCP tools. System prompt requires a citation for every figure and an explicit "the data does not show this" when the graph is silent. |
| Drafting | Complaints, RTI applications, plain-language summaries, in the citizen's language. |
| Vision | Classify a citizen photo (pothole, open drain, incomplete work) and read any contractor signboard in frame. |

Rules that keep it honest:

- The model never states an amount, date or name that is not in a tool result.
- Derived judgements ("delayed", "over budget") are computed by code from dated facts, then explained by the model.
- A human-review queue holds low-confidence extractions and all entity merges involving people.
- Keep an evaluation set: 30 questions with hand-checked answers for the demo ward. Run it after every pipeline change.

## 7. Risks

| Risk | Mitigation |
|---|---|
| Defamation: the graph links named contractors and officials to failures | Show sourced facts, not conclusions. Label red flags as "patterns worth checking". Refer to officials by post. Offer a right of reply. Get a lawyer on the team to review wording; the event invites them. |
| Wrong extraction published as fact | Quote and page on every fact; trust tiers; review queue; a "report an error" link on every card |
| Personal data (DPDP Act 2023) | Elected representatives and officials in their public role only. No home addresses or phone numbers. Blur faces and number plates in citizen photos. |
| Data is not available on the day | Pre-load one ward before the event; never demo from live scraping |
| HydraDB immaturity | Bolt-only access and Neo4j fallback, decided before the event |
| Scraping terms and load | Fetch politely, cache everything, prefer published files and OpenCity datasets |
| Adoption stalls after the event | Publish the ontology and the cleaned dataset openly; give BMC a version that runs on their own data and needs no new data entry |

## 8. What adoption looks like

The pitch to civic authorities is not "we will expose you". It is: *you already publish all of this; we make it legible, and it reduces your RTI and complaint load.* Concretely offer:

1. A one-ward pilot with the ward office, using only documents BMC already publishes.
2. The ontology as a proposed publishing format, so future tenders and work orders arrive as data.
3. A weekly digest for the ward officer: works at risk of missing deadlines, defects reported on roads still under contractor liability.
