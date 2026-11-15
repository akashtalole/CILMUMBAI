# Semantic and search layer

The graph holds facts. This layer makes them findable, comparable and safe to show. It sits between the stores and the agents, and it is mostly ordinary software: the model is used where language is needed and nowhere else.

## 1. The semantic layer

Three things, each defined once and used by every application and agent.

### 1.1 Glossary

A SKOS vocabulary of civic terms with labels in Marathi, Hindi and English, synonyms, abbreviations and the ontology class or property each maps to.

| Term | Also written as | Maps to |
|---|---|---|
| Standing Committee | स्थायी समिती, SC | `Committee` |
| Defect liability period | DLP, दोष दायित्व कालावधी, warranty | `DefectLiabilityPeriod` |
| K/West ward | K/W, के पश्चिम, Andheri West ward | `AdminWard {code: 'K/W'}` |
| Storm water drain | SWD, nullah, नाला | `Asset {type: 'drain'}` |
| Budget estimate | BE, अर्थसंकल्पीय अंदाज | `Allocation.amount_be` |

The glossary drives query expansion, entity lookup, extraction prompts and the labels in every interface. Road and locality aliases confirmed by reviewers are added to it from the ward memory store.

### 1.2 Metrics

Each indicator is a small declarative definition compiled to a query. The scorecard, the agent and the export therefore return the same number.

```yaml
metric: capital_utilisation
label: {en: "Share of capital budget spent", mr: "भांडवली खर्चाचे प्रमाण"}
numerator:   sum(Allocation.amount_actual) where BudgetHead.kind = 'capital'
denominator: sum(Allocation.amount_be)     where BudgetHead.kind = 'capital'
grain: [Department, FiscalYear]
unit: percent
tiers: [official]
caveats: "Actuals for the latest year are provisional until the next budget book."
```

Starter set: capital utilisation; share of allocation tendered; median days from tender to award; share of works past due; works under liability with open defects; tenements owed against handed over; complaints disputed after closure; audit observations unanswered.

Every metric carries its caveats, and an answer that uses a metric must repeat them.

### 1.3 Named views

Common traversals with fixed, tested queries, exposed as tools: `trace_money`, `who_is_responsible`, `work_status`, `scheme_card`, `ward_summary`, `contractor_record`, `promise_history`, `gaps_for`. Agents call these first and write free-form queries only when no view fits.

## 2. Storage for search

| Index | Holds | Used for |
|---|---|---|
| Full-text | Every archived page, in its original script, with transliteration; node names and aliases | Exact numbers and names: tender ids, road names, contractor names |
| Vector | Passages of documents and one generated summary per ward, department, contractor, scheme and major work | Questions phrased in everyday language, across languages |
| Graph | The ten graphs | Multi-hop questions and anything about relationships |
| Spatial | Geometry of wards, roads, plots, assets | "Near me", "in this ward", point lookups |
| Metric tables | Pre-computed metric values | Comparisons and trends |

A practical choice that keeps operations small: Postgres with its full-text search, the pgvector extension and PostGIS covers the text, vector, spatial and metric rows in one database. OpenSearch is the step up if volume demands it. The embedding model must handle Marathi and Hindi well; choose it by testing on real queries, not by reputation.

Passages are chunked by document structure (a tender's header data, a committee item, a budget table row) and each chunk keeps its document, page and the ids of the graph nodes extracted from it. That link is what lets retrieval move from a passage to the graph and back.

## 3. How a question is answered

```
question (any of three languages, text or transcribed voice)
   │
   ▼
1. Understand     normalise script, expand with glossary, find entities and places
   │
   ▼
2. Route          lookup · trail · metric · rule · exploratory
   │
   ├─ lookup        entity search ► node card
   ├─ trail         named view ► ordered facts
   ├─ metric        metric engine ► numbers with caveats
   ├─ rule          rules engine ► card with basis and contest
   └─ exploratory   text + vector retrieval ► expand through the graph from the
                    nodes those passages mention ► rerank
   │
   ▼
3. Compose        the agent writes the answer from the retrieved facts only
   │
   ▼
4. Check          code verifies every figure, date and name in the answer appears
                  in a retrieved fact, and attaches source, page and tier
   │
   ▼
5. Respond        answer, sources, what is not known, and how to find out
```

Routing is a cheap classification. Most residents' questions are lookups and trails, which never need open-ended retrieval; that keeps answers fast, cheap and reproducible. The exploratory path is for reporters and researchers.

### The exploratory path in more detail

1. Retrieve passages by text and by vector, and merge the two rankings.
2. Collect the graph nodes those passages were extracted into.
3. Expand one or two hops along relationships that matter for the question type (a tender's award and contractor; a work's asset and ward).
4. Add the pre-written summaries of the wards, departments or contractors involved.
5. Rerank and trim to what fits, keeping every item's source.

The summaries are the part often called graph-based retrieval: they let a question like "what is going wrong with drain works in the eastern suburbs" be answered from a few vetted paragraphs and then drilled into, instead of from hundreds of raw passages. They are written by the audit desk, reviewed like any other output, and stored as nodes with their own provenance and date.

## 4. Citations are enforced, not requested

- Every tool result carries fact ids. The answer must cite them.
- After the agent composes an answer, a deterministic checker extracts each amount, date, identifier and proper name and confirms it occurs in a cited fact. A failure sends the answer back once with the unmatched items listed; a second failure returns a plain "the records we hold do not show this" with the nearest facts.
- Every answer ends with what was not found and which office or request could supply it.
- Each fact shows its tier and its date. A fact older than its source's normal refresh period shows a staleness mark.

## 5. Access tiers

| Tier | Who | Sees |
|---|---|---|
| Public | Anyone | Official and reviewed facts; residents' reports in aggregate; published briefs |
| Contributor | Signed-in residents | Their own reports and subscriptions |
| Researcher | Registered journalists, academics, auditors | Contractor network views, unreviewed flags marked as such, bulk queries |
| Official | Ward and department staff | Their unit's work lists, pending items, correction requests |
| Reviewer | The platform's editors and lawyers | Review queues, held items, everything above |

Access is enforced in the query layer, by tier labels on nodes and relationships, so an agent acting for a public user cannot retrieve researcher-tier data however it is asked. Every query is logged with the tier it ran under.

## 6. What "enterprise grade" means here

| Property | How it is met |
|---|---|
| Correctness | Quote check at load; citation check at answer; evaluation set run on every change |
| Traceability | Each fact records document, page, quote, extractor and version; each answer records the facts used |
| Freshness | Each source has an expected refresh period; a monitor flags sources that are late |
| Availability | Read paths use replicas and caches; the archive and graph are backed up; the public site degrades to cached pages |
| Security | Tiered access in the query layer; no secrets in agent sandboxes; residents' images stripped of faces and plates |
| Privacy | No private individuals' names stored; officials by post; deletion on request for contributors |
| Multilingual | Glossary, transliteration and a tested multilingual embedding model; answers in the asker's language |
| Auditability | Query and release logs; corrections recorded with reason and approver |
| Cost control | Routing keeps most questions off the expensive path; caching of views and summaries; budgets on agent sessions |

## 7. Evaluation

Three sets, kept in the repository and run before any change to prompts, rules, ontology or retrieval goes live.

| Set | Size to start | Measures |
|---|---|---|
| Extraction | 50 hand-labelled documents across types and both languages | Field accuracy; share of quotes that match |
| Questions | 150 questions with verified answers, a third each in Marathi, Hindi and English, across all five routes | Correct, cited, and "not known" said when true |
| Refusals | 40 questions the platform must not answer as asked (accusations, personal data, legal advice) | Declines appropriately and offers what it can |

Report results by route and by language. A change that improves English and worsens Marathi is not an improvement.
