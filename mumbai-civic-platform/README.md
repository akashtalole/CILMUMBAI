# Aamcha Hishob: the final recommendation

**One knowledge graph of how Mumbai is governed, paid for and built, with an intelligence layer on top, so that every idea in this repository becomes a small application on a shared base and not a separate project.**

**Aamcha Hishob** (आमचा हिशोब, "our account") is the public name. Hishob is the word a Mumbaikar uses when asking for an account of money: *hishob dya*, give the account. The name says whose money it is and what is being asked for. The technical name for the data layer underneath stays the civic knowledge graph.

Before using the name publicly, check that it is free as a trademark and as a domain; a quick web search on 15 November 2026 found no civic platform using it.

## The recommendation in brief

Stop choosing between ideas. The forty-one ideas in [../mumbai-civic-ideas/](../mumbai-civic-ideas/) ask the same few questions of the same few kinds of record: money, contracts, works, places, offices, people, rules and evidence. Build that record once, properly, and each idea is a query, a view or an agent on top of it.

The platform has five layers.

```
 ┌──────────────────────────────────────────────────────────────────────────────┐
 │ 5  APPLICATIONS    alerts · money trail · who is responsible · ward brief ·  │
 │                    promise tracker · tenement ledger · newsroom feed · API   │
 ├──────────────────────────────────────────────────────────────────────────────┤
 │ 4  INTELLIGENCE    Claude models · Managed Agents desks · LangGraph workflows│
 │                    intake · regulation · audit · steward · analyst · citizen │
 ├──────────────────────────────────────────────────────────────────────────────┤
 │ 3  SEMANTIC AND    glossary (Marathi, Hindi, English) · metric definitions · │
 │    SEARCH          question routing · text + vector + graph retrieval ·      │
 │                    citations checked in code · access tiers                  │
 ├──────────────────────────────────────────────────────────────────────────────┤
 │ 2  KNOWLEDGE       ten linked graphs under one ontology · every fact sourced,│
 │                    dated and tiered · rules as data                          │
 ├──────────────────────────────────────────────────────────────────────────────┤
 │ 1  DATA            immutable archive of every source document · parsed text ·│
 │                    geometry · residents' reports · RTI replies               │
 └──────────────────────────────────────────────────────────────────────────────┘
```

## Why this is the right final idea

- **It matches the shape of the problem.** Accountability fails at the joins between records, not inside any one of them. A graph is a store of joins.
- **It compounds.** Each new source improves every application. Tender data collected for street alerts also feeds the money trail, the contractor record and the ward brief.
- **It can start small and stay honest.** One ward, four graphs and three applications is a real product. Coverage grows by source and by ward, and the platform always states what it does not hold.
- **It is adoptable.** The same base serves residents, reporters, corporators, ward officers and the state. Officers gain from it, which is what makes a civic body take it up.
- **It survives the team.** An open ontology, an open archive and an open API let others build on it.

## What it answers

Each line is a question the platform should answer with sources, in Marathi, Hindi or English.

| Question | Graphs used |
|---|---|
| Where did the money for my road come from, who built it, and is it still under warranty? | Money, Procurement, Works and Assets |
| Who is responsible for this drain, and who is above them? | Organisation and Jurisdiction, Works and Assets |
| What was promised for my ward this year and what has started? | Voice, Money, Procurement |
| Which office has my building's redevelopment file? | Land and Planning, Law and Oversight |
| How much of the health budget was spent in each of the last five years? | Money |
| Which audit findings has nobody answered? | Law and Oversight |
| What has my corporator's fund been spent on? | People and Representation, Money, Works and Assets |
| Which works due before the monsoon are behind? | Works and Assets, Procurement |
| Which records do we not have, and who holds them? | Evidence (gaps) |

## Files

| File | Contents |
|---|---|
| [01-data-catalogue.md](01-data-catalogue.md) | Every dataset needed, by graph: source, key fields, access, refresh, priority |
| [02-ontology-and-graphs.md](02-ontology-and-graphs.md) | The ontology, the ten graphs, identifiers, provenance and time, validation |
| [03-semantic-and-search-layer.md](03-semantic-and-search-layer.md) | Glossary, metrics, storage, retrieval, citations, access tiers, evaluation |
| [04-intelligence-layer.md](04-intelligence-layer.md) | Claude models, Managed Agents desks, LangGraph workflows, tools, safeguards |
| [06-user-personas.md](06-user-personas.md) | Who the platform serves: twelve personas, their jobs, channels, access tier and the features mapped to each |
| [../aamcha-hishob-specs/](../aamcha-hishob-specs/) | The spec-driven development plan to build the platform |
| [architecture/](architecture/) | Design and architecture for hosting on AWS, with 22 decision records comparing AWS and open-source options |
| [05-implementation-plan.md](05-implementation-plan.md) | Phases from the hackathon day to a year out, team, infrastructure, governance, risks |

## How the earlier work fits

| Earlier folder | Role in the platform |
|---|---|
| [../mumbai-civic-graph/](../mumbai-civic-graph/) | The first slice: core ontology, tender portal pipeline, four agent desks, working client and LangGraph pipeline |
| [../mumbai-civic-ideas/](../mumbai-civic-ideas/) | The application backlog: forty-one ideas, each now a view on the platform |
| [../mumbai-civic-ideas/bmc-sra-jurisdiction/](../mumbai-civic-ideas/bmc-sra-jurisdiction/) | The Land and Planning graph and the Regulation desk |

## Status

This is a design. The agent client and pipeline in `mumbai-civic-graph/managed-agents/` were syntax-checked and the pipeline was dry-run; nothing has run against the Claude API or a real database. Most data sources in the catalogue have not been opened. The plan's first step is to change that.
