# Idea 2: Vachan Tracker

**Every civic promise, linked to evidence of whether it was kept.**

Read [00-shared-foundation.md](00-shared-foundation.md) first.

## The problem

Promises are made in budget speeches, manifestos, press conferences and committee meetings. Delivery, if it happens, is recorded in tender portals and work dashboards. Nobody connects the two, so a promise quietly expires and reappears in next year's speech.

## What the citizen gets

- A list of promises for their ward or for the city, each with a status: **Kept, In progress, Delayed, Stalled, No evidence, Dropped**.
- The status is not an opinion. It is computed from linked evidence, and each promise shows that evidence: the tender, the work order, the completion note, the news report, the citizen photo.
- A history view: the same promise across years, with deadline changes shown ("promised for May 2025, then May 2026, then December 2026").
- Follow a promise and get notified when its evidence changes.

## What counts as a promise

A statement is a `Promise` only if it has: a **maker** (person or agency), a **deliverable** (what will exist), and ideally a **quantity, place and deadline**. "We are committed to better roads" is not a promise. "All roads in the island city will be concretised by May 2027" is.

Claude classifies each candidate sentence and extracts those fields. Vague statements are stored as `Statement` and not tracked.

## Graph slice

```
(Promise)-[:MADE_BY]->(Person|Agency)
(Promise)-[:MADE_IN]->(SourceDocument)        // speech, manifesto, press report
(Promise)-[:ABOUT]->(Asset|AdminWard|BudgetHead)
(Promise)-[:RESTATES]->(Promise)              // same promise in a later year
(Promise)-[:FULFILLED_BY]->(Work)
(Promise)-[:FUNDED_BY]->(Allocation)
(Evidence)-[:BEARS_ON {direction: 'supports'|'contradicts'}]->(Promise)
```

`Promise` properties: `text_original`, `text_en`, `deliverable`, `quantity`, `unit`, `deadline`, `made_on`, `specificity_score`.

## Status rules

Computed in code, re-run nightly. The model explains the result; it does not decide it.

| Status | Rule |
|---|---|
| Kept | Linked work has a completion record at or above the promised quantity |
| In progress | Linked work has a contract and no missed milestone |
| Delayed | Deadline passed, or a later promise `RESTATES` it with a later deadline |
| Stalled | Contract exists; no evidence of activity in the last 180 days |
| No evidence | No allocation, tender or work could be linked |
| Dropped | Official statement cancelling it, or allocation removed in the next budget |

## Example queries

Promises restated with a slipping deadline:

```cypher
MATCH (p2:Promise)-[:RESTATES]->(p1:Promise)
WHERE p2.deadline > p1.deadline
RETURN p1.text_en, p1.deadline AS first_deadline, p2.deadline AS new_deadline, p2.made_on
ORDER BY p2.made_on DESC
```

Promises about a ward with no money behind them:

```cypher
MATCH (p:Promise)-[:ABOUT]->(:AdminWard {code: $ward})
OPTIONAL MATCH (p)-[:FUNDED_BY]->(al:Allocation)
OPTIONAL MATCH (p)-[:FULFILLED_BY]->(w:Work)
WITH p, count(al) AS funded, count(w) AS works
WHERE funded = 0 AND works = 0
RETURN p.text_en, p.made_on, p.deadline
```

## Implementation plan

### Sources, in order of ease

1. Commissioner's budget speeches for 2025-26 and 2026-27 (two speeches make `RESTATES` detection possible).
2. Party manifestos from the most recent BMC election.
3. News reports of announcements, English and Marathi.
4. Standing Committee resolutions.

### Build phases

| Phase | Work | Done when |
|---|---|---|
| 1. Promise extraction | Split speeches into statements; Claude classifies and extracts fields with quote and page | 100+ promises from two budget speeches, spot-checked |
| 2. Deduplicate and chain | Embed promises; Claude adjudicates near-duplicates across years into `RESTATES` chains | Chains reviewed by a human for the demo ward |
| 3. Link to delivery | Match promise to Works and Allocations (shares the Paisa Trail graph); candidates by ward, category and embedding, then Claude picks with a reason | Each promise has links or an explicit "no evidence" |
| 4. Status engine | Rules above as a Python module with unit tests | Status reproducible from the graph alone |
| 5. Evidence intake | News monitoring for the tracked promises; citizen photo upload with location | New evidence changes a status in the demo |
| 6. UI | Promise cards, timeline per promise, ward filter, share-as-image card for WhatsApp | Demo script runs |

### If building standalone, without Paisa Trail

Skip phase 3's tender linkage and rely on news and citizen evidence. The tracker is still useful, but statuses will mostly be "reported" tier rather than "official".

## Demo script

1. Open the 2026-27 budget speech. Show 60 promises extracted, each with its sentence highlighted in the original.
2. Filter to the demo ward. Show one **Kept**, one **Delayed** with its deadline history across two speeches, one **No evidence**.
3. Upload a photo of an unfinished site; the linked promise gains a citizen-tier evidence item.
4. Generate the shareable card: promise, status, three sources.

## Success measures

- Precision of promise extraction: of items shown as promises, how many a human agrees are concrete commitments (target above 90%).
- Share of promises with at least one official-tier evidence link.
- Number of multi-year chains found; these are the most newsworthy output.

## Risks specific to this idea

| Risk | Mitigation |
|---|---|
| Seen as partisan | Track every maker by the same rules; publish the rules; show kept promises as prominently as broken ones |
| Wrong link makes a kept promise look broken | "No evidence" is worded as "we found no evidence", with a button for the maker's office to submit some |
| Vague promises resist tracking | Publish a specificity score; that itself nudges better promises |
