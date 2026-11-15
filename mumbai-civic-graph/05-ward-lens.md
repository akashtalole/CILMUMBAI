# Idea 5: Ward Lens

**Ward scorecards that set spending against outcomes, checked by citizens on the ground.**

Read [00-shared-foundation.md](00-shared-foundation.md) first.

## The problem

Money spent is an input. What residents care about is whether the drain floods, whether the school has teachers, whether the dispensary is open. Spending and outcomes are reported by different bodies in different units for different geographies, so nobody can say whether a ward that received more got more.

There is also no ground truth. A work is "completed" when the paperwork says so.

## What the user gets

- **Ward scorecard:** per sector (roads, drains, water, health, education, solid waste), the allocation, the spend, the works completed, and two or three outcome indicators, with the trend over years.
- **Fair comparison:** per resident, per kilometre of road, per slum household, so dense and poor wards are not compared unfairly with rich ones.
- **Citizen verification:** residents confirm or dispute a work's status with a geotagged photo. "Official status: complete. 14 citizen reports: 11 say incomplete."
- **Ask:** "Which wards have the highest drain spending per kilometre and the most waterlogging complaints?"

## The semantic model

The graph holds the facts. A thin **metric layer** on top defines each indicator once, so the scorecard, the chat agent and any export compute it identically.

```yaml
metric: road_spend_per_km
label: Road spending per km of road
numerator:   sum(Contract.value) where Work.category = 'roads' and FiscalYear = $fy
denominator: sum(Road.length_km)
grain: [AdminWard, FiscalYear]
unit: INR lakh per km
sources: [official]
caveats: "Excludes citywide projects such as the Coastal Road."
```

In the ontology, indicators are first-class:

```
(Indicator {code, label, unit, direction})          // direction: higher_is_better | lower_is_better
(Observation {value, period})-[:OF]->(Indicator)
(Observation)-[:FOR]->(AdminWard)
(Observation)-[:FROM]->(SourceDocument)
(Indicator)-[:MEASURES]->(Sector)
(BudgetHead)-[:SERVES]->(Sector)
(Work)-[:IN_SECTOR]->(Sector)
(CitizenReport {status_claimed, photo, at})-[:ABOUT]->(Work)
(CitizenReport)-[:BY]->(Reporter {reputation})
```

`Sector` is the bridge: budget heads and works roll up to sectors on the money side; indicators roll up to sectors on the outcome side. This is modelled on the RDF Data Cube idea of observations with dimensions, kept simple.

## Indicators to start with

Choose only those with a public source at ward level. Candidates:

| Sector | Money | Outcome |
|---|---|---|
| Roads | Spend per km | Pothole complaints per km; share of works past deadline |
| Storm water drains | Spend per km of drain | Waterlogging complaints; flooding spots reported |
| Solid waste | Spend per resident | Garbage complaints per 1,000 residents |
| Health | Spend per resident | Dispensaries per 100,000 residents; reported dengue and malaria cases |
| Education | Spend per enrolled pupil | Enrolment trend; pupil to teacher ratio |
| Water | Spend per connection | Contamination and shortage complaints |

Praja Foundation's annual reports and BMC's own published statistics are the likely sources for complaints and service indicators. Confirm coverage before promising any row of this table.

## Example queries

Money and outcome side by side for one sector:

```cypher
MATCH (w:AdminWard)
OPTIONAL MATCH (w)<-[:LOCATED_IN]-(:Asset)<-[:IMPROVES]-(wk:Work)-[:IN_SECTOR]->(:Sector {code: 'drains'})
OPTIONAL MATCH (c:Contract)-[:FOR_WORK]->(wk)
WITH w, sum(c.value) AS spend
OPTIONAL MATCH (o:Observation)-[:FOR]->(w)
OPTIONAL MATCH (o)-[:OF]->(i:Indicator {code: 'waterlogging_complaints'})
RETURN w.code, spend, sum(o.value) AS complaints
ORDER BY spend DESC
```

Works where official status and citizens disagree:

```cypher
MATCH (wk:Work {status: 'complete'})<-[:ABOUT]-(r:CitizenReport {status_claimed: 'incomplete'})
WITH wk, count(r) AS disputes
WHERE disputes >= 3
RETURN wk.title, wk.completed_on, disputes
ORDER BY disputes DESC
```

## Citizen verification design

- A report needs a photo taken in-app, with GPS within 50 metres of the work and a timestamp. No gallery uploads.
- Claude vision checks the photo plausibly shows the work type and blurs faces and number plates before storage.
- Reports are citizen-tier evidence. They never change the official status; they sit beside it.
- A reporter's reputation rises when their reports agree with later official or majority evidence. Weight reports by reputation to resist brigading.
- Three or more independent disputes on a "complete" work generate an item in the ward officer's digest.

## Implementation plan

| Phase | Work | Done when |
|---|---|---|
| 1. Ward base | Wards with population, area, road length, slum population share (Census and OpenStreetMap) | Denominators for every ward |
| 2. Money rollup | Ward-level allocation and contract value by sector, from the Paisa Trail graph or from OpenCity's budget data | Totals reconcile with the source |
| 3. Outcome ingest | Extract indicator tables from reports into Observations with source and period | 6+ indicators across all wards |
| 4. Metric layer | YAML definitions and a small engine that compiles each to a query | Scorecard and agent return identical numbers |
| 5. Scorecard UI | Ward page, city map shaded by a chosen metric, scatter of spend against outcome | Demo script runs |
| 6. Verification | Photo report flow, checks, dispute query | A live report appears on a work during the demo |
| 7. Agent | Chat over metrics with the caveats attached to each answer | Evaluation questions pass |

## Interpreting the numbers honestly

Spending and outcomes move together for many reasons. A ward may get more drain money *because* it floods. The interface must:

- Never label a ward "inefficient" from one ratio.
- Show trends over at least three years next to any comparison.
- Attach the metric's caveats to every chart and every agent answer.
- Describe patterns as questions ("spending rose 40% while complaints did not fall; what was built?") and link to the works so the question can be answered.

## Demo script

1. City map shaded by road spend per km. Pick the demo ward.
2. Scorecard: money on the left, outcomes on the right, three-year trend.
3. Ask: "Which three wards spent the most on drains per km and what happened to waterlogging complaints?" The answer includes caveats and sources.
4. Open a work marked complete with several citizen disputes; show the photos.
5. Submit a live report from a phone in the room (mock location).

## Success measures

- Number of indicators with full ward coverage and a cited source.
- Agreement between the scorecard and hand calculations for three wards.
- Number of verified citizen reports per work in a pilot ward.

## Why this is roadmap, not day-one

Outcome data at ward level is the scarcest input and takes weeks to assemble and reconcile. Citizen verification only becomes meaningful with real users over time. The piece worth building on the day, if there is capacity, is the citizen verification flow on top of Paisa Trail's works, since it needs no new data.
