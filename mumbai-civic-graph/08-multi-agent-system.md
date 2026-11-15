# Multi-agent system on Claude Managed Agents

The five ideas so far describe what citizens see. This file describes what does the work behind them: a standing team of agents, built on Claude Managed Agents, that reads the documents, checks its own findings, and produces things people can act on.

The agent definitions and the client that runs them are in [managed-agents/](managed-agents/). They have been syntax-checked against the current Python SDK but **not run**: no Claude API credential was visible in the session that wrote them, and creating agents in your account needs your go-ahead.

## 1. Why agents, and why more than one

A dashboard shows data someone else prepared. The hard part of civic accountability is the preparation: reading thousands of pages in two languages, checking each fact, noticing what is missing, and turning a finding into a letter the right office must answer. That is continuous work, and it is the work a small audit office or newsroom desk does.

So the design is an office with three desks, not a chatbot:

```
                        ┌──────────────────────── INTAKE DESK ───────────────────────┐
 tender PDFs, awards,   │  Ingest lead ──► Document extractor  (one per document)     │
 resolutions, budget ──►│      │      ──► Fact verifier       (second reader, every   │──► facts.jsonl
 pages, RTI replies     │      │                                document)             │    review.jsonl
                        │      └──────► Entity resolver                               │
                        └─────────────────────────────────────────────────────────────┘
                                                   │  quote check + schema check in code, then load
                                                   ▼
                                        ┌──────────────────────┐
                                        │   CIVIC GRAPH        │   HydraDB / Neo4j over Bolt
                                        │   every fact sourced │
                                        └──────────────────────┘
                                          ▲ read-only tools  ▲
                        ┌─────────────────┴──────┐   ┌───────┴──────────────────────────────┐
   resident, on web  ──►│  CITIZEN DESK          │   │  AUDIT DESK                          │
   or WhatsApp          │  one agent, one answer │   │  Audit lead ──► Challenger (argues   │──► ward brief
                        │  with sources and a    │   │      │           the other side)     │    case files
                        │  drafted complaint     │   │      └──────► Drafter (complaints,   │    RTI drafts
                        └────────────────────────┘   │               RTIs, meeting questions)│   gaps.jsonl
                                                     └──────────────────────────────────────┘
                                                                     │
                                                          a person reviews, then publishes
```

Splitting the work across agents is justified here for three reasons, and only these:

- **Volume.** A ward's corpus is hundreds of documents. One agent reading them all fills its context; one cheap reader per document, run in parallel, does not.
- **Independence.** The agent that checks a fact should not be the one that extracted it, and the agent that attacks a finding should not be the one that wrote it.
- **Least privilege.** The agents that read untrusted documents have no web access and no graph access. The agent that talks to the public cannot write anything.

The Citizen desk is deliberately a single agent. Answering one resident's question does not split into independent pieces, and adding checker agents to every answer would multiply its cost without making it more correct. Its accuracy comes from the graph tools, a strict "answer only from tool results" rule, and higher reasoning effort.

## 2. The roster

| Agent | Model | Can do | Cannot do |
|---|---|---|---|
| **Ingest lead** | Claude Opus 5.5 | Plan a batch, delegate, merge results, write the facts file | Reach the web or the graph |
| Document extractor | Claude Haiku 5.5 | Read one document, write facts with page and quote | Anything outside the sandbox files |
| Fact verifier | Claude Sonnet 5.5 | Re-read the source, pass, fix or reject each fact, add missed ones | Same |
| Entity resolver | Claude Sonnet 5.5 | Match names to known entities, with a reason | Merge people on name alone (by instruction) |
| **Audit lead** | Claude Opus 5.5 | Query the graph read-only, write case files and the ward brief | Write to the graph, publish |
| Challenger | Claude Sonnet 5.5 | Review a case file, argue innocent explanations, flag wording | See the graph; it judges only the evidence in the file |
| Drafter | Claude Sonnet 5.5 | Write complaints, RTI applications, meeting questions in three languages | Add facts it was not given |
| **Citizen desk** | Claude Opus 5.5, high effort | Look up a place, trace money, name the responsible office, draft a complaint | Write memory, run code, reach the web |

The leads run on the most capable default model because they plan and judge. The readers run on smaller current models because their work is mostly reading; that is where most of the tokens go.

## 3. What this makes possible

These are the parts that go beyond showing data.

### 3.1 The graph knows what it does not know

Every trail has gaps: a tender with no budget head, a contract with no payment record, a "completed" work with no completion certificate. Most tools hide gaps. Here each one becomes a line in `gaps.jsonl`, naming the missing record and the office that holds it, and the Drafter turns it into an RTI application asking for exactly that record.

When a resident files it and uploads the reply, the Intake desk reads the reply and the gap closes. The graph grows through citizens exercising a right they already have, and the list of unanswered RTIs becomes its own accountability measure.

### 3.2 Every finding is attacked before anyone sees it

The Challenger reads each case file as the contractor's or the officer's advocate: does the evidence support each claim, what is the innocent explanation (a retender, a court stay, the monsoon work ban, a different firm with a similar name), what single record would settle it. It also strikes words that state conclusions. A finding it holds does not leave the session.

This addresses the largest risk in the whole project, which is publishing something wrong about a named party. It also produces the right-of-reply text in advance.

### 3.3 Liability watch: repairs the city does not have to pay for

Tender conditions carry a defect liability period during which the contractor must repair defects at their own cost. The Audit lead joins three things nobody joins today: completion dates, liability periods and citizen-reported defects. The output is a list per ward of defects on roads still under liability, grouped by contractor.

That list is the adoption case. It is useful to the ward officer on Monday morning, it costs the city nothing, and its value can be stated in rupees.

### 3.4 Meeting packs

Accountability mostly happens in rooms: ward committee meetings, the Standing Committee, a residents' association meeting with the ward officer. For each, the Drafter writes a short list of questions that can be answered with a fact, each with its source. A corporator or a resident can read them out.

### 3.5 Ward memory

Two memory stores persist across sessions. The playbook holds conventions (how tenders are numbered, department abbreviations, Marathi and English name pairs). Ward notes hold what has been learned about each ward: local road names, which roads belong to MMRDA or PWD, corrections a reviewer confirmed. Each batch makes the next one better, and every change is versioned, so a wrong note can be traced and rolled back.

### 3.6 Seasonal watches

The same audit run, pointed at a deadline, answers questions the city asks every year: which drain and road works due before the monsoon are behind schedule on 1 May; which promises in February's budget speech have a tender by September.

## 4. How the five ideas map onto the desks

| Idea | Intake | Audit | Citizen desk |
|---|---|---|---|
| Paisa Trail | Builds the trail | Finds allocations with nothing tendered | Shows the trail for a road |
| Jawabdar | Extracts liability clauses and org structure | Liability watch | Photo or pin to responsible office and drafted complaint |
| Vachan Tracker | Extracts promises from speeches | Computes status, finds slipped deadlines | "What was promised for my ward?" |
| Thekedar Graph | Awards, penalties, debarments; entity resolution | Red-flag case files, each challenged | Not exposed to the public |
| Ward Lens | Indicator tables | Ward brief | Ward scorecard questions |

## 5. Which Managed Agents features are used

| Feature | Used for |
|---|---|
| Agents as versioned, stored configs | One file per agent in `managed-agents/agents/`. The agent version that produced a fact can be recorded with it, so a bad prompt change can be traced to the facts it touched. |
| Multiagent roster | Each lead delegates to its specialists; each specialist runs in its own thread with its own model, prompt and tools. Only the listed agents can be used. |
| Dynamic workflows | **On** for both leads. For a large batch the lead starts a background run: one extractor per document, then one verifier per document, with rejected documents redone once. |
| Outcomes | Intake and audit sessions are graded against a rubric (`managed-agents/rubrics/`) and revised until they pass or reach three iterations. |
| Shared sandbox filesystem | Agents hand work to each other as files. The final files are downloaded from the session's outputs. |
| Memory stores | Playbook (read-only) and ward notes (read-write for the desks, read-only for the Citizen desk). |
| Custom tools | Graph queries are answered by `civic_client.py` on your machine, so the database needs no public address for the hackathon. |
| Session budgets | Hard cap per session: $25 for an intake batch, $15 for a ward audit, $2 for one citizen question. |
| Limited networking | The sandbox has no outbound hosts and the web tools are off on every agent. |
| Scheduled deployments | Production only; see section 8. |

### About dynamic workflows

Workflows are turned on for the Ingest lead and the Audit lead. With them, the lead can run many agents in phases in the background, which is what finishes a few hundred documents without batching them by hand. Every agent in a run uses tokens, which is why each session has a budget. To turn them off, set `workflows: {type: disabled}` in the lead's file and apply again; the lead will then delegate only through its roster, a few at a time.

## 6. Safeguards

| Risk | Control |
|---|---|
| A document contains text that tries to instruct the agent | Readers are told documents are data; they have no web, no graph and no publishing tool, so there is nothing for an injected instruction to reach. Their output is checked in code before use. |
| An extracted fact is wrong | Second reader on every document; then `civic_client.py load` confirms each quote appears on the cited page of the source PDF before writing anything. Facts that fail go to `held.jsonl`. Scanned pages with no text layer are loaded but marked `scan_unchecked`. |
| Agents corrupt the graph | No agent has a write tool. Only the loader writes, from validated files, against a whitelist of labels and relationship types. |
| A finding defames someone | Challenger review on every case file; banned conclusion words in the rubric; officials by post; nothing is published by an agent. A person, ideally the team's lawyer, releases it. |
| A resident's message manipulates the Citizen desk | It has read-only tools, cannot write memory, and is told the message is a request, not a change to its rules. |
| Runaway cost | Session budgets; cheap models for bulk reading; the Citizen desk has no delegation. |
| Captcha on Mahatenders | Agents do not browse the portal. A person collects pages as described in [07-tender-portals.md](07-tender-portals.md); agents read the archive. |

The second-reader and Challenger passes each add roughly one more agent per item. That is a deliberate cost for work where a miss is expensive. If the budget is tight on the day, drop the verifier from the workflow and rely on the quote check in code, and say so in the demo.

## 7. Running it

Prerequisites: an Anthropic API key with Managed Agents access, the `ant` CLI (1.40 or later), Python with `pip install -r requirements.txt`, and a graph database on Bolt.

```sh
cd mumbai-civic-graph/managed-agents

# 1. Create the agents, environment and memory stores (shows a plan first)
ant apply --dry-run -v agents environments memory_stores
ant apply agents environments memory_stores          # writes claude-lock.json; commit it

# 2. Read a batch of documents, then check quotes and load the graph
python civic_client.py ingest ../data/raw/*.pdf
python civic_client.py load ../data/extracted/<session id>/facts.jsonl

# 3. Audit a ward
python civic_client.py audit "K/West"

# 4. Answer a resident
python civic_client.py ask "एस.व्ही. रोडवरील खड्ड्यांसाठी कोण जबाबदार आहे?"
```

Each session prints a link to its trace in the Claude Console, where every thread, tool call and cost is visible. That view is worth showing in the demo.

To change an agent, edit its file and run `ant apply` again. Running sessions keep the version they started with.

### Things to confirm on first run

- Your organisation has the current multiagent type. If creating a lead fails on the `multiagent` field, the organisation does not have it yet; the fallback is the older `coordinator` type, which delegates to a roster but cannot start workflow runs.
- `MERGE` in the loader is accepted by Neo4j. On HydraDB, check `cypher-compat.md` first.
- The graph queries inside `civic_client.py` assume the property names in [00-shared-foundation.md](00-shared-foundation.md). Adjust them to the data you actually load.
- The rubrics are starters. Tune them after the first real batch.

## 8. Hackathon slice and what comes after

**On the day**, build the Intake desk and the Citizen desk first. That gives the demo: documents go in, a sourced graph comes out, a resident's question is answered with a drafted complaint. Add the Audit desk if time allows, for one ward, and show one case file with its challenge review.

**After the event**, three changes turn it into a service:

1. **Host the graph tools as an MCP server** in front of the database and replace the custom tools with an `mcp_toolset`, with the credential in a vault. Sessions then run with nobody's laptop attached.
2. **Schedule the desks.** With the graph reachable, a deployment runs the audit unattended:

   ```python
   client.beta.deployments.create(
       name="Weekly ward audit, K/West",
       agent=AUDIT_LEAD_ID,
       environment_id=ENVIRONMENT_ID,
       resources=[...],  # schema file and the two memory stores
       initial_events=[{
           "type": "user.define_outcome",
           "description": "Audit public works in ward K/West and write the ward brief, case files, drafts and gaps file.",
           "rubric": {"type": "text", "content": WARD_AUDIT_RUBRIC},
       }],
       schedule={"type": "cron", "expression": "30 6 * * 1", "timezone": "Asia/Kolkata"},
   )
   ```

   A nightly intake run over newly archived documents works the same way.
3. **Put a person in the publishing path.** A small review screen where an editor or lawyer approves each case file, with the Challenger's review beside it, and where the named party's reply is attached.

## 9. Sources

- Claude Managed Agents documentation: [multiagent orchestration](https://platform.claude.com/docs/en/managed-agents/multiagent-orchestration.md), [define outcomes](https://platform.claude.com/docs/en/managed-agents/define-outcomes.md)
