# Ontology and graphs

## 1. One ontology, ten graphs

The Mumbai Civic Ontology (MCO) is a single vocabulary. The ten graphs are modules of it that share places, organisations, time and evidence. A node belongs to one module; relationships cross modules freely, and those crossings are where the value is.

```
                         ┌───────────────┐
                         │   EVIDENCE    │  every node and edge points here
                         └───────┬───────┘
   ┌──────────┐  funds   ┌───────┴───────┐  executed as  ┌────────────────┐
   │  MONEY   ├─────────►│  PROCUREMENT  ├──────────────►│ WORKS & ASSETS │
   └────┬─────┘          └───────┬───────┘               └───────┬────────┘
        │ voted by               │ approved by                   │ located in / owned by
   ┌────┴─────────────┐  ┌───────┴────────┐              ┌───────┴────────┐
   │ PEOPLE &         │  │ ORGANISATION & │◄─────────────┤     PLACE      │
   │ REPRESENTATION   │  │ JURISDICTION   │  responsible └───────┬────────┘
   └────┬─────────────┘  └───────┬────────┘                      │
        │ promises               │ bound by                      │ on
   ┌────┴─────┐          ┌───────┴────────┐              ┌───────┴────────┐
   │  VOICE   │─────────►│ LAW & OVERSIGHT│◄─────────────┤ LAND & PLANNING│
   └────┬─────┘  about   └────────────────┘   governs    └────────────────┘
        │ reports on
   ┌────┴─────┐
   │ SERVICES │
   └──────────┘
```

## 2. Vocabularies reused

| Need | Standard |
|---|---|
| Tenders, awards, contracts | Open Contracting Data Standard concepts |
| Organisations, posts, reporting | W3C Organization Ontology |
| People, memberships, elected bodies | Popolo |
| Provenance | W3C PROV-O |
| Geometry | GeoSPARQL |
| Hierarchies and glossaries | SKOS |
| Time | OWL-Time |
| Statistical observations | RDF Data Cube |
| Legal texts and their parts | ELI-style identifiers for acts, regulations and clauses |
| Datasets and licences | DCAT |

Where a standard has a term, MCO uses it or declares an equivalence. MCO adds only what Mumbai needs and the standards lack: wards, budget heads, defect liability, tenement obligations, jurisdiction rules.

## 3. The modules

### 3.1 Place

`AdminWard`, `ElectoralWard`, `Locality`, `Constituency`, `Geometry`.
`(ElectoralWard)-[:WITHIN]->(AdminWard)` · `(Locality)-[:WITHIN]->(AdminWard)` · `(x)-[:HAS_GEOMETRY]->(Geometry)`

### 3.2 Money

`FiscalYear`, `BudgetHead`, `Allocation`, `Expenditure`, `RevenueHead`, `Receipt`, `Fund`, `Borrowing`, `Payment`.
`(BudgetHead)-[:PARENT_OF]->(BudgetHead)` · `(Allocation)-[:UNDER]->(BudgetHead)` · `(Allocation)-[:FOR_YEAR]->(FiscalYear)` · `(Fund)-[:CONTROLLED_BY]->(Person|Post)` · `(Payment)-[:UNDER_CONTRACT]->(Contract)`

### 3.3 Procurement

`Tender`, `Corrigendum`, `Bid`, `Award`, `Contract`, `Contractor`, `Company`, `Director`, `Penalty`, `Blacklisting`.
`(Tender)-[:FOR_WORK]->(Work)` · `(Tender)-[:ISSUED_BY]->(Department)` · `(Bid)-[:ON]->(Tender)` · `(Award)-[:OF]->(Tender)` · `(Award)-[:TO]->(Contractor)` · `(Contract)-[:FROM_AWARD]->(Award)` · `(Penalty)-[:IMPOSED_ON]->(Contractor)` · `(Tender)-[:RETENDER_OF]->(Tender)`

### 3.4 Works and Assets

`Work`, `Milestone`, `Inspection`, `DefectLiabilityPeriod`, `Asset` (road, drain, bridge, building, toilet, garden, school, hospital, pipeline), `Utility`, `Permission`.
`(Work)-[:IMPROVES]->(Asset)` · `(Work)-[:FUNDED_BY]->(Allocation)` · `(Work)-[:HAS_DLP]->(DefectLiabilityPeriod)` · `(Asset)-[:LOCATED_IN]->(AdminWard)` · `(Inspection)-[:OF]->(Asset)`

### 3.5 Organisation and Jurisdiction

`Agency`, `Department`, `Post`, `IssueType`, `ServiceStandard`, `JurisdictionRule`.
`(Department)-[:PART_OF]->(Agency)` · `(Post)-[:IN]->(Department)` · `(Post)-[:COVERS]->(AdminWard)` · `(Post)-[:REPORTS_TO]->(Post)` · `(Agency)-[:OWNS]->(Asset)` · `(IssueType)-[:HANDLED_BY]->(Department)` · `(JurisdictionRule)-[:ASSIGNS]->(Agency)`

### 3.6 People and Representation

`Person` (public role only), `Party`, `Committee`, `Meeting`, `Question`, `Declaration`.
`(Person)-[:HOLDS {from,to}]->(Post)` · `(Person)-[:REPRESENTS]->(ElectoralWard)` · `(Person)-[:MEMBER_OF]->(Committee)` · `(Meeting)-[:OF]->(Committee)` · `(Meeting)-[:APPROVED]->(Award)` · `(Question)-[:ASKED_BY]->(Person)`

### 3.7 Land and Planning

`Plot`, `PlotStatusClaim`, `Reservation`, `Scheme`, `Developer`, `Approval`, `NOC`, `TenementObligation`, `Handover`, `Premium`, `Concession`.
Detailed in [../mumbai-civic-ideas/bmc-sra-jurisdiction/01-solution-design.md](../mumbai-civic-ideas/bmc-sra-jurisdiction/01-solution-design.md).

### 3.8 Services

`Facility`, `Indicator`, `Observation`, `Sector`, `Equipment`.
`(Observation)-[:OF]->(Indicator)` · `(Observation)-[:FOR]->(AdminWard|Facility)` · `(Indicator)-[:MEASURES]->(Sector)` · `(BudgetHead)-[:SERVES]->(Sector)`

### 3.9 Voice

`Promise`, `Complaint`, `CitizenReport`, `RTIRequest`, `RTIReply`, `NewsReport`, `Proposal`.
`(Promise)-[:MADE_BY]->(Person|Agency)` · `(Promise)-[:RESTATES]->(Promise)` · `(Promise)-[:FULFILLED_BY]->(Work)` · `(Complaint)-[:ABOUT]->(Asset)` · `(Complaint)-[:ROUTED_TO]->(Post)` · `(RTIReply)-[:ANSWERS]->(RTIRequest)` · `(RTIRequest)-[:SEEKS]->(Gap)`

### 3.10 Law and Oversight

`Act`, `Regulation`, `Clause`, `Direction`, `Circular`, `CourtOrder`, `AuditReport`, `AuditObservation`, `Position`.
`(Direction)-[:INTERPRETS]->(Clause)` · `(Direction)-[:SUPERSEDES|REITERATES]->(Direction)` · `(CourtOrder)-[:DIRECTS]->(Agency)` · `(AuditObservation)-[:ABOUT]->(Work|Contract|Department)` · `(Position)-[:TAKEN_BY]->(Agency)`

### 3.11 Evidence

`SourceDocument`, `Claim`, `Run`, `Correction`, `Gap`.
Every node and relationship in every other module carries `source_id`, `page`, `quote`, `tier`, `confidence`, `valid_from`, `valid_to`, `extracted_by`.

## 4. Four rules that hold everywhere

1. **No source, no fact.** A record without a document, page and quote is rejected at load.
2. **Tiers.** `official`, `reported`, `citizen`, `derived`. Answers say which they rest on. Bulk downloads contain only official and reviewed data.
3. **Time.** Nothing is overwritten. A changed deadline is a new dated edge; the old one keeps its `valid_to`. History is a query.
4. **Claims where facts are contested.** Slum status, road ownership and jurisdiction are stored as dated claims attributed to whoever made them, never as bare properties.

## 5. Identity and entity resolution

| Entity | Primary key | Fallback |
|---|---|---|
| Tender | Mahatenders id | BMC bid number |
| Budget head | Budget code plus budget part | Normalised name under its parent |
| Contractor | Registration number; company id | Normalised name plus address, held as `POSSIBLY_SAME_AS` until reviewed |
| Asset | Own id linked to OpenStreetMap way id | Name plus ward plus nearest landmark |
| Plot | Survey number plus village | Geometry |
| Person | Office held plus term | Never merged on name alone |
| Document | Content hash | URL plus fetch time |

Merges of organisations need a hard identifier or a reviewer's approval. Merges of people need an official identifier. Unsure pairs are linked, shown as unsure, and never used to raise a finding.

## 6. Authoring and validation

```
ontology/
  mco-core.ttl          classes and properties shared by all modules
  mco-money.ttl  mco-procurement.ttl  mco-works.ttl  mco-org.ttl  mco-people.ttl
  mco-land.ttl   mco-services.ttl     mco-voice.ttl  mco-law.ttl  mco-evidence.ttl
  shapes/               SHACL shapes, one file per module
  glossary.ttl          SKOS terms in Marathi, Hindi and English
  rules/                jurisdiction and status rules as YAML
```

A short example of the style:

```turtle
mco:Tender a owl:Class ;
    rdfs:label "Tender"@en, "निविदा"@mr ;
    rdfs:comment "An invitation to bid for a work, supply or service."@en ;
    skos:closeMatch ocds:Tender .

mco:forWork a owl:ObjectProperty ;
    rdfs:domain mco:Tender ; rdfs:range mco:Work .

mco:TenderShape a sh:NodeShape ;
    sh:targetClass mco:Tender ;
    sh:property [ sh:path mco:tenderId ; sh:minCount 1 ; sh:maxCount 1 ] ;
    sh:property [ sh:path mco:estimatedCost ; sh:datatype xsd:integer ; sh:minInclusive 0 ] ;
    sh:property [ sh:path prov:wasDerivedFrom ; sh:minCount 1 ] .
```

From these files a build step generates: the record schema the extractor agents fill, the label and relationship whitelist the loader enforces, the validation run on every batch, and the public documentation. The ontology is versioned; each fact records the ontology version it was loaded under.

## 7. Physical stores

| Store | Holds | Choice |
|---|---|---|
| Property graph | All ten graphs, for traversal | On AWS: Neptune Database Serverless or Neo4j Community by profile, with HydraDB on trial; see [architecture/adr/0004-graph-database.md](architecture/adr/0004-graph-database.md) |
| Triple store | The same data as linked open data, for publishing and SPARQL | Apache Jena Fuseki or Oxigraph, fed by export |
| Relational and spatial | Geometry, subscriptions, review queues, metric tables | Postgres with PostGIS |
| Text and vector index | Document passages and node summaries | See [03-semantic-and-search-layer.md](03-semantic-and-search-layer.md) |
| Object storage | The immutable document archive | Any S3-compatible store |

HydraDB's README describes an OpenCypher subset with no built-in text or vector index, so search lives outside it, and every query the platform depends on must be checked against its compatibility notes. The triple store is not needed on the day; it becomes useful when the data is published for others.

## 8. Competency questions

The ontology is correct when these can be answered by a query. Use them as acceptance tests.

1. For a given road, list every work in the last five years with contractor, cost, due date and liability end date.
2. For a budget head and year, list works funded, tenders issued and the unspent remainder.
3. For a point on the map, return the owning agency, responsible post and escalation chain.
4. List contractors awarded a contract within twelve months after a recorded penalty.
5. For a promise, list every restatement with its deadline, and the linked works.
6. For a ward, list schemes that owe transit tenements, with owed and handed-over counts.
7. For a plot, return every status claim with its maker and date.
8. For an audit observation, return the work it concerns and any reply on record.
9. For any fact shown to a user, return the document, page and quote.
10. List every gap, the record that would close it, and the office that holds that record.
