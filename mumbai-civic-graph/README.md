# Mumbai Civic Graph

Plans for the Claude Impact Lab Mumbai hackathon, 21 November 2026.

**Challenge:** help citizens see where public money is spent, track whether civic promises are delivered, and hold the right systems and people accountable.

**Thesis:** Mumbai's accountability problem is a *join* problem. The budget book, the tender notice, the work order, the contractor, the road, the ward and the complaint all exist, but in separate PDFs and portals with no shared identifiers. A knowledge graph with an explicit ontology is the natural fix: Claude reads the documents and extracts entities, the ontology says what may connect to what, and the graph answers multi-hop questions ("which budget head paid for this road, who built it, and is it still under warranty?") that no single source can.

## Files

| File | Contents |
|---|---|
| [00-shared-foundation.md](00-shared-foundation.md) | Ontology, graph database choice (HydraDB and alternatives), data sources, architecture, how Claude is used, risks. All five ideas build on this. |
| [01-paisa-trail.md](01-paisa-trail.md) | Follow one rupee from budget head to the street. |
| [02-vachan-tracker.md](02-vachan-tracker.md) | Promise tracker: every civic promise linked to evidence of delivery. |
| [03-thekedar-graph.md](03-thekedar-graph.md) | Contractor and procurement red-flag graph. |
| [04-jawabdar.md](04-jawabdar.md) | "Who is responsible for this?" Photo to responsible agency, officer post, contractor and a drafted complaint or RTI. |
| [05-ward-lens.md](05-ward-lens.md) | Ward scorecards: spend against outcomes, with citizen-verified ground truth. |
| [06-prep-and-day-plan.md](06-prep-and-day-plan.md) | What to do between now and the 21st, and an hour-by-hour plan for the day. |
| [07-tender-portals.md](07-tender-portals.md) | What the BMC tender portal and Mahatenders publish, their identifiers, how they map to the graph, and how to collect from them. |

## The five ideas, ranked

| # | Idea | Challenge pillar | Demo strength | Data risk | Adoption path |
|---|---|---|---|---|---|
| 1 | **Paisa Trail** | See where money is spent | High | Medium: needs budget and tender PDFs parsed | BMC finance and IT; newsrooms |
| 2 | **Jawabdar** | Hold the right people accountable | Very high: photo in, answer out | Medium: needs road-to-agency mapping | Ward offices; 1916 helpline |
| 3 | **Vachan Tracker** | Track promises | High | Low: budget speech and news are public text | Corporators; civil society |
| 4 | **Thekedar Graph** | Accountability | High, but legally sensitive | High: entity resolution, company data | Vigilance department; journalists |
| 5 | **Ward Lens** | See spending and outcomes | Medium | High: outcome data is patchy | Ward committees; citizen groups |

## Recommendation

Build **Paisa Trail as the spine, with Jawabdar as the front door.**

- Paisa Trail produces the graph every other idea needs (budget head → work → contract → contractor → asset → ward).
- Jawabdar is the most persuasive two-minute demo: a citizen photographs a broken road and gets back who built it, what it cost, whether the contractor still owes repairs, and a ready-to-file complaint.
- Scope it to **one ward and one department (roads)**. A complete, sourced graph of one ward beats a thin graph of the whole city, and judges from civic bodies will test it on roads they know.
- Vachan Tracker is the natural third layer if the team has spare hands, since it reuses the same work nodes.

Thekedar Graph and Ward Lens are worth pitching as the roadmap, not building on the day: the first needs legal review before anything is published, the second needs outcome data that takes weeks to assemble.

## What is verified and what is not

Facts in these plans were checked on 15 November 2026 where possible. Items to confirm before relying on them:

- **HydraDB details** come from its GitHub README. It is a young project (v0.3) and the Cypher subset it accepts must be checked against its `cypher-compat.md` before committing. Every plan here keeps Neo4j as a drop-in fallback over the same Bolt driver.
- **Tender portals** were examined directly; see [07-tender-portals.md](07-tender-portals.md). Listing pages on Mahatenders sit behind a captcha, so tender detail and award pages were not opened.
- **Other data source availability** was not tested end to end. [06-prep-and-day-plan.md](06-prep-and-day-plan.md) starts with a data spike for exactly this reason.
- **Budget figures** are from press coverage of the 2026-27 BMC budget, not from the budget books themselves.

## Sources

- [HydraDB README](https://raw.githubusercontent.com/hydra-db/hydradb/main/README.md) and [repository](https://github.com/hydra-db/hydradb)
- [HydraDB OSS on Product Hunt](https://www.producthunt.com/products/hydradb-oss)
- [BMC presents ₹80,952.56 crore budget for 2026-27, Business Standard](https://www.business-standard.com/budget/news/bmc-presents-rs-80952-crore-budget-for-2026-27-up-8-7-pc-126022500692_1.html)
- [Over 50% of 2025-26 capital budget unutilised, Free Press Journal](https://www.freepressjournal.in/mumbai/mumbai-news-bmc-data-shows-over-50-per-cent-of-202526-capital-budget-unutilised-even-as-major-infrastructure-projects-progress)
- [Analysing the BMC Budget for 2026-27, OpenCity](https://opencity.in/analysing-the-bmc-budget-for-2026-27/)
- [Road concretisation fines and blacklisting, Free Press Journal](https://www.freepressjournal.in/mumbai/mumbai-road-concretisation-bmc-imposes-20-lakh-fines-blacklists-contractors-and-rmc-plants-for-substandard-work)
- [Only 46 km of 324 km done in Phase 1, Free Press Journal](https://www.freepressjournal.in/amp/mumbai/mumbai-bmc-struggles-to-complete-road-concretisation-only-46-km-done-out-of-324-km-in-phase-1)
- [BMC road concretisation dashboard, Mumbai Live](https://www.mumbailive.com/en/infrastructure/bmc-must-upgrade-dashboard-allow-citizens-to-put-complaints-urges-bjp-minister-ashish-shelar-90143)
- [MumbaiSpend, IndiaSpend (2017)](https://www.indiaspend.com/mumbaispend-now-you-can-track-how-mumbai-spends-its-money-31981)
- [Graph database benchmark, AIMultiple](https://aimultiple.com/graph-databases)
- [Mahatenders](https://mahatenders.gov.in/nicgep/app) and [BMC tender notices](https://www.mcgm.gov.in/irj/go/km/docs/documents/Tenders-New/ETH/ETH_8000113000_110826.pdf); full list in [07-tender-portals.md](07-tender-portals.md)
