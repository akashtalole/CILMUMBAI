# Idea 1: Paisa Trail

**Follow one rupee from the budget book to the street.**

Read [00-shared-foundation.md](00-shared-foundation.md) first. This plan covers only what is specific to this idea.

## The problem

The BMC budget is published by budget head. Works are tendered by tender number. Contracts are sanctioned by committee resolution number. Roads are known to citizens by name. None of these identifiers appear in each other's documents consistently, so nobody outside the system can connect "₹X crore for roads in the budget" to "this road outside my house".

## What the citizen gets

- **Search or tap a map:** pick a road, a ward or a budget head.
- **The trail:** budget head → allocation this year → work → tender → contractor → contract value → payments (where known) → current status. Each hop shows its source page.
- **Ask in plain language**, in English, Hindi or Marathi: "How much was allocated for storm water drains in K/West this year and what has started?"
- **The gaps are shown, not hidden.** Where a hop is missing ("tender found, no award found"), the trail says so. Those gaps are themselves the accountability finding.

## User stories

1. As a resident, I enter my road name and see what was sanctioned for it, who is doing the work and when it is due.
2. As a journalist, I pick a budget head and see every work funded under it, sorted by amount, with the unspent remainder.
3. As a corporator, I see all works in my electoral ward with status, to raise in committee.
4. As a BMC finance officer, I see allocations with no linked tender six months into the year.

## Graph slice

```
(FiscalYear)<-[:FOR_YEAR]-(Allocation)-[:UNDER]->(BudgetHead)-[:PARENT_OF*0..4]->(BudgetHead)
(Work)-[:FUNDED_BY]->(Allocation)
(Work)-[:IMPROVES]->(Asset)-[:LOCATED_IN]->(AdminWard)
(Tender)-[:FOR_WORK]->(Work)
(Award)-[:OF]->(Tender)
(Contract)-[:FROM_AWARD]->(Award)
(Contractor)-[:PARTY_TO]->(Contract)
(Payment)-[:UNDER_CONTRACT]->(Contract)
```

Key properties: `Allocation.amount_be`, `amount_re`, `amount_actual`; `Tender.estimated_cost`, `tender_no`, `published_on`; `Contract.value`, `signed_on`, `due_on`; `Work.status`, `category`.

## Example queries

Trail for a road:

```cypher
MATCH (a:Asset {id: $asset_id})<-[:IMPROVES]-(w:Work)
OPTIONAL MATCH (w)-[:FUNDED_BY]->(al:Allocation)-[:UNDER]->(bh:BudgetHead)
OPTIONAL MATCH (t:Tender)-[:FOR_WORK]->(w)
OPTIONAL MATCH (aw:Award)-[:OF]->(t)
OPTIONAL MATCH (c:Contract)-[:FROM_AWARD]->(aw)
OPTIONAL MATCH (k:Contractor)-[:PARTY_TO]->(c)
RETURN w, al, bh, t, c, k
ORDER BY t.published_on DESC
```

Allocations with nothing tendered against them:

```cypher
MATCH (al:Allocation)-[:FOR_YEAR]->(:FiscalYear {label: '2026-27'})
MATCH (al)-[:UNDER]->(bh:BudgetHead)
OPTIONAL MATCH (w:Work)-[:FUNDED_BY]->(al)
WITH bh, al, count(w) AS works
WHERE works = 0
RETURN bh.code, bh.name, al.amount_be
ORDER BY al.amount_be DESC
LIMIT 50
```

## The hard part: linking a work to its budget head

Tender notices rarely print the budget code cleanly. Use a three-step linker and record which step made each link:

1. **Explicit:** the budget code appears in the tender or resolution text. Trust tier `official`.
2. **Structural:** department + work category + ward narrows to one budget head. Tier `derived`, with the rule recorded.
3. **Semantic:** Claude ranks candidate budget heads from the description and explains the choice. Tier `derived`, confidence stored, shown to the user as "probable".

Never present a step 2 or 3 link as certain.

## Implementation plan

### Before the event (see [06-prep-and-day-plan.md](06-prep-and-day-plan.md))

| Step | Output |
|---|---|
| Pick the demo ward and department (roads) | A named scope |
| Collect the roads budget pages for 2026-27 and 2025-26 | 2 PDFs, archived with hashes |
| Collect 40 to 60 tender notices and any committee resolutions for that ward | Raw corpus |
| Draft `mco.ttl` and the extraction schema for BudgetHead, Allocation, Tender, Work, Contract, Contractor | Schema v0 |
| Stand up HydraDB and Neo4j; run the same five queries on both | Database decision |
| Hand-label 10 documents | Gold set for measuring extraction |

### Build phases

| Phase | Work | Done when |
|---|---|---|
| 1. Budget tree | Parse budget tables into BudgetHead hierarchy and Allocations; reconcile sub-totals to the printed totals | Sum of leaves equals printed department total |
| 2. Tender extraction | Claude extracts Tender and Work with quote and page; SHACL validation | 90% field accuracy on the gold set |
| 3. Asset matching | Match road names in tenders to OpenStreetMap ways within the ward; store geometry | 80% of works placed on the map |
| 4. Award and contract | Extract from committee resolutions and the concretisation dashboard; resolve contractor names | Contractor attached to at least half of the works |
| 5. Budget linker | Three-step linker above | Every work has a link or an explicit "unlinked" flag |
| 6. MCP tools | `find_entity`, `locate`, `trace_money`, `get_source` | Agent answers the 30 evaluation questions with citations |
| 7. UI | Map, trail view as a horizontal chain of cards, chat panel, source drawer | Demo script runs offline |

### Team split (4 to 5 people)

| Role | Owns |
|---|---|
| Data lead | Corpus, parsing, gold set |
| Graph lead | Ontology, loader, queries, database |
| AI lead | Extraction prompts, linker, agent, evaluation |
| Front end | Map, trail view, chat |
| Domain and pitch | Checks facts against reality, adoption story, demo script |

## Demo script (3 minutes)

1. "Here is a road in our ward everyone knows is dug up." Tap it on the map.
2. The trail appears: budget head, allocation, tender, contractor, due date. Open one source card to show the original page and highlighted quote.
3. Ask in Marathi: "या वॉर्डमध्ये रस्त्यांसाठी किती पैसे मंजूर झाले आणि किती कामे सुरू झाली?" The agent answers with figures and citations.
4. Show the "allocated but never tendered" list for the ward.
5. Close: "This used only documents BMC already publishes. Give us one ward office and we can keep it current."

## Success measures

- Coverage: share of the ward's road allocation that is traced to at least a tender.
- Accuracy: extraction accuracy on the gold set; zero uncited figures in agent answers.
- Usefulness: a person who lives in the ward finds their road and learns something they did not know.

## Risks specific to this idea

| Risk | Mitigation |
|---|---|
| Budget books are scanned images | OCR, then Claude vision on table pages; verify totals arithmetically |
| Payments data is not public | Show the trail up to contract value; mark payments "not published" and name the RTI that would obtain it |
| City-wide works do not map to one ward | Model them as `Work` with `scope: citywide`; exclude from ward totals and say so |
