# SPEC-002: Ontology, shapes and generated schema

| | |
|---|---|
| Status | Draft |
| Milestone | M0 |
| Owner role | Graph engineer |
| Depends on | |
| ADRs | 0005 |
| Personas served | Researchers; all, indirectly |

## 1. Problem and outcome

The extractor agents, the loader, the graph and the documentation must agree on what kinds of things and relationships exist. Today the starter code parses a Markdown file for labels.

When done, the Mumbai Civic Ontology for the first four graphs (Place, Money, Procurement, Works and Assets, plus Organisation and Evidence) lives as Turtle and SHACL files, and a build step generates the extraction schema, the loader whitelist and the documentation from them.

## 2. User stories

- As an AI engineer, I want the extraction schema generated from the ontology, so that agents can only emit types that exist.
- As a graph engineer, I want one place to add a class or property, so that every component picks it up.
- As a researcher, I want published, versioned definitions, so that I can interpret the data.

## 3. Requirements

| Id | Requirement |
|---|---|
| R1 | The ontology shall define classes and properties for Place, Money, Procurement, Works and Assets, Organisation and Evidence, as listed in the platform's ontology document, with English and Marathi labels. |
| R2 | The ontology shall reuse or declare equivalence to OCDS, W3C Organization, PROV-O, SKOS, OWL-Time and GeoSPARQL terms where they exist. |
| R3 | SHACL shapes shall require on every fact the provenance fields: source document, page, quote, tier, confidence. |
| R4 | The build shall generate a JSON Schema for extracted records, a label and relationship whitelist with allowed domains and ranges, and a Markdown reference page. |
| R5 | The ontology shall carry a semantic version; the build shall embed that version in every generated artefact. |
| R6 | If the Turtle files are not valid, or a generated artefact differs from the committed one, then CI shall fail. |

## 4. Acceptance criteria

| Id | Given | When | Then | Verifies |
|---|---|---|---|---|
| AC1 | The ontology files | They are parsed with rdflib | No errors; every class and property has `rdfs:label` in `en` and `mr`; every class with a counterpart in OCDS, W3C Organization, PROV-O, SKOS, OWL-Time or GeoSPARQL declares it | R1, R2 |
| AC2 | A valid tender record with all provenance fields | It is validated against the shapes | It conforms | R3 |
| AC3 | A tender record missing `quote` | It is validated | It fails with a message naming `quote` | R3 |
| AC4 | The ontology | The build runs | `schema/records.json`, `schema/whitelist.json` and `docs/ontology.md` are produced, each stamped with the ontology version | R4, R5 |
| AC5 | An edge `FOR_WORK` from a `Contractor` | It is checked against the whitelist | It is rejected because the domain must be `Tender` or `Contract` | R4 |
| AC6 | A pull request that edits a `.ttl` file but not the generated files | CI runs | CI fails with "generated artefacts out of date" | R6 |

## 5. Interfaces and data contracts

```
app/ontology/
  mco-core.ttl  mco-place.ttl  mco-money.ttl  mco-procurement.ttl
  mco-works.ttl  mco-org.ttl  mco-evidence.ttl
  shapes/*.ttl   glossary.ttl   VERSION
app/src/hishob/schema/
  records.json      JSON Schema for one extracted record (node | edge | note)
  whitelist.json    {"labels": {...}, "edges": {"FOR_WORK": {"from": ["Tender","Contract"], "to": ["Work"]}}}
```

Command: `hishob ontology build [--check]`.

## 6. Non-functional requirements

- Build completes in under 10 seconds.
- Generated files are deterministic (sorted keys) so diffs are meaningful.

## 7. Constitution

| Article | How this spec upholds it |
|---|---|
| C1 | R3: provenance fields required by shape |
| C10 | R1: Marathi labels required |
| C12 | One source of truth for types; no hand-maintained duplicates |

## 8. Out of scope

Land and Planning, People, Services, Voice and Law modules (later specs add them). A live SPARQL endpoint.

## 9. Design notes

- Start from the classes in `mumbai-civic-graph/00-shared-foundation.md` and `mumbai-civic-platform/02-ontology-and-graphs.md`.
- Use pySHACL in tests and in the loader.
- Ontology version: minor bump for additions, major for removals or renames. The loader refuses records stamped with an unknown major version.

## 10. Tasks

| Id | Task | Size | Depends on | Verifies |
|---|---|---|---|---|
| T1 | Core, Place and Evidence modules with labels | M | | AC1 |
| T2 | Money, Procurement, Works, Organisation modules | L | T1 | AC1 |
| T3 | Provenance shapes and per-class shapes | M | T1 | AC2, AC3 |
| T4 | Generator for JSON Schema and whitelist | M | T2 | AC4, AC5 |
| T5 | Generator for the reference page | S | T2 | AC4 |
| T6 | `--check` mode and CI job | S | T4, T5 | AC6 |

## 11. Open questions

| Question | Owner | Assumption until answered |
|---|---|---|
| Who reviews Marathi labels | Language reviewer | Product lead drafts; reviewer approves before M2 |
