# Intelligence layer

Claude models do the reading, judging and writing. Managed Agents runs them as standing desks. LangGraph decides the order of work and where people must sign off. Plain code does everything that must be exact.

The first four desks and the pipeline already exist as files in [../mumbai-civic-graph/managed-agents/](../mumbai-civic-graph/managed-agents/). This document extends them to the whole platform. Nothing here has been run against the API.

## 1. Division of labour

| Layer | Decides | Never does |
|---|---|---|
| Plain code | Quote checks, schema validation, graph writes, metric values, jurisdiction cards, citation checks, access control | Interpret language |
| LangGraph | Which step runs next, fan-out, retries, pauses for people, saved state | Reason about content |
| Managed Agents | How to split and carry out an agentic task inside one step | Write to the graph or publish |
| People | Whether rules, merges, findings and briefs are released | Bulk reading |

## 2. Models

| Use | Model | Why |
|---|---|---|
| Desk leads; citizen answers; legal reading | Claude Opus 5.5 | Planning, judgement, accuracy |
| Bulk document reading | Claude Haiku 5.5 | Most tokens are here; the task is narrow |
| Verification, entity resolution, challenge, drafting | Claude Sonnet 5.5 | More judgement than reading, less than leading |
| Question routing and entity spotting | Claude Haiku 5.5 through the Messages API | A single fast call, no agent needed |

Overnight extraction of large backlogs can go through the Message Batches API at lower cost, since nothing is waiting on it. Model choices should be revisited against the evaluation sets; they are a starting allocation, not a measured optimum.

## 3. The desks

Six desks. Each is a Managed Agents coordinator with a small roster, except the Citizen desk, which is a single agent by design.

| Desk | Lead and roster | Input | Output | Exists as files |
|---|---|---|---|---|
| **Intake** | Ingest lead; document extractor, fact verifier, entity resolver | Archived documents | Verified facts file, review file | Yes |
| **Regulation** | Regulation lead; rule drafter, two equal-brief advocates | Legal texts, directions, letters, orders | Clauses, positions, candidate rules, dual-reading brief | Planned |
| **Audit** | Audit lead; challenger, drafter | The graph, for one ward or theme | Brief, case files, drafts, gaps | Yes |
| **Steward** | Steward lead; copies of itself | The graph and the review queues | Data-quality report: duplicates, orphans, stale sources, failed quote checks, schema drift; proposed fixes for a reviewer | Planned |
| **Analyst** | Analyst lead; copies of itself for sub-questions | A researcher's question | A sourced research note | Planned |
| **Citizen** | One agent | One resident's question | A sourced answer and a drafted letter | Yes |

Why the Steward desk matters: a civic graph decays. Portals change format, a contractor's name gains a suffix, a ward is split. One desk whose only job is to look for decay, and to propose rather than make corrections, is what keeps year two as trustworthy as week one.

Dynamic workflows are on for the Intake, Audit, Regulation and Analyst leads, so a large job runs as many agents in phases in the background. Every agent in a run uses tokens, so every session has a budget. To turn them off for a lead, set `workflows: {type: disabled}` in its file and apply again. The Citizen desk has no delegation at all.

## 4. Tools

For the hackathon, graph tools are custom tools answered by the client on a laptop. For the service, the same tools are hosted as an MCP server in front of the query layer, with credentials in a vault, so sessions run unattended.

| Tool | Returns | Used by |
|---|---|---|
| `find_entity` | Nodes by name in any of three languages | All |
| `locate` | Asset, ward, owning agency at a point | Citizen, Audit |
| `trace_money` | Budget head to payment chain for a work or asset | Citizen, Audit, Analyst |
| `who_is_responsible` | Agency, post, escalation, representative, contractor under liability | Citizen |
| `which_authority` | Jurisdiction card for a plot or scheme | Citizen, Regulation |
| `metric` | A metric's value with grain, sources and caveats | Audit, Analyst, Citizen |
| `search` | Passages and summaries with fact ids, by the retrieval path in the search layer | Analyst, Audit |
| `cypher_read` | Rows from one read-only query, tier-limited | Audit, Analyst, Steward |
| `get_source` | Document reference and quote for a fact | All |
| `gaps_for` | Missing records for a node, with the holder | Audit, Citizen |

No agent has a write tool. Outputs are files; code validates and loads them.

## 5. Memory

| Store | Holds | Who writes |
|---|---|---|
| Playbook | Numbering conventions, abbreviations, extraction rules | Intake and Steward leads; reviewed |
| Ward notes | Aliases, non-BMC roads, confirmed corrections, per ward | Intake and Audit leads |
| Legal notes | How each regulation and direction has been read so far, with dates | Regulation lead |
| Source notes | Each portal's quirks and format changes | Steward lead |

The Citizen desk mounts these read-only. Memory is versioned, so a wrong note can be traced and rolled back. No secrets and no personal data go into memory.

## 6. Workflows

Each is a LangGraph state graph with saved state. Steps in capitals pause for a person. The first exists as code; the rest follow the same pattern.

| # | Workflow | Steps |
|---|---|---|
| W1 | **Ingest and audit** (exists) | intake → quote check and load → REVIEW FACTS if many held → audit each ward in parallel → RELEASE → publish |
| W2 | **Source watch** | for each source on its schedule: fetch or receive → detect new or changed documents → archive → hand to W1 or W4 → update freshness |
| W3 | **Resident request** | route question → citizen desk → citation check → reply; if it is a report: locate → attach to asset → acknowledge → offer complaint draft |
| W4 | **Legal change** | classify → regulation desk extracts clauses and positions → draft rules → LAWYER APPROVES RULES → recompute cards in code → notify affected subscribers → brief → RELEASE |
| W5 | **RTI loop** | gap identified → drafter writes application → resident files and records the number → clock starts → at thirty days: draft first appeal → reply uploaded → intake → gap closed → audit re-run for affected ward |
| W6 | **Correction and right of reply** | request received → steward desk checks against sources → REVIEWER DECIDES → correct with history kept, or attach the party's reply → notify requester |
| W7 | **Stewardship** | weekly: steward desk scans → proposals queued → REVIEWER APPROVES MERGES AND FIXES → apply in code |
| W8 | **Promotion gate** | any change to an agent, prompt, rule, ontology or retrieval → run the three evaluation sets → compare with the last release → OWNER APPROVES → apply new version |

W2 and the scheduled parts of W1, W5 and W7 run as Managed Agents scheduled deployments once the graph tools are hosted. Each firing starts a fresh session; the LangGraph state carries what must persist between firings.

W8 is what makes changes safe. Agents are versioned, stored configurations, so a regression can be rolled back by pinning the previous version, and every fact records the version that extracted it.

## 7. Safeguards

| Risk | Control |
|---|---|
| Instructions hidden in documents or residents' messages | Readers have no web, graph or publishing tools; outputs are validated in code; the citizen desk treats messages as requests, not rule changes |
| Wrong fact | Second reader; quote check at load; held queue; corrections workflow |
| Wrong answer | Tool-only answering; citation check in code; "not known" as a first-class reply |
| Defamation | Records, not verdicts; challenger on every finding; banned conclusion words in rubrics; officials by post; human release |
| Bias toward one authority or party | Equal-brief advocates; identical measures for all; published method; right of reply |
| Privacy | No private individuals; images blurred; contributor data deletable |
| Runaway cost | Session budgets; cheap models for bulk; routing keeps most questions off agents with delegation |
| Model or platform change | Evaluation gate; pinned agent versions; all prompts and rules in version control |
| Over-reliance | Every answer names its sources and gaps; the platform says it is not legal advice and not an official record |

## 8. What a resident's question costs, in steps

To show that the common case is simple: "Who is responsible for the potholes on this road?"

1. One fast call routes it as a trail question and finds the road.
2. The citizen desk calls `locate`, `who_is_responsible` and `trace_money`: three graph queries.
3. It writes a short answer and a complaint draft.
4. Code checks the citations.

No delegation, no workflow run, no open-ended retrieval. The multi-agent machinery is for building and maintaining the graph, not for answering from it.
