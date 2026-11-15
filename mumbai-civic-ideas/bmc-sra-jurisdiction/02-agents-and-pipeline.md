# Agents and pipeline

This idea reuses the three desks in [../../mumbai-civic-graph/08-multi-agent-system.md](../../mumbai-civic-graph/08-multi-agent-system.md) and adds one: a Regulation desk. Nothing here has been built or run.

## 1. What each desk does for this idea

| Desk | Existing role | Added for this idea |
|---|---|---|
| Intake | Reads documents into verified facts | Reads letters of intent, approval letters, RERA project pages and handover records into `Scheme`, `Plot`, `Approval`, `TenementObligation`, `Premium` facts |
| **Regulation (new)** | | Reads regulations, directions and letters into `Clause`, `Direction`, `Position` facts and drafts jurisdiction rules; writes the dual-reading brief |
| Audit | Finds overdue works and gaps | Finds overdue tenement handovers, schemes with a non-slum plot and no stated basis, sign-offs pending longest, missing premium records |
| Citizen | Answers residents from the graph | Gains a `which_authority` tool that returns the jurisdiction card |

## 2. The Regulation desk

Four agents. The lead coordinates; two advocates each argue one authority's reading; a rule drafter turns the texts into candidate rules.

| Agent | Model | Job | Tools |
|---|---|---|---|
| **Regulation lead** | Claude Opus 5.5 | Plans the reading, delegates, writes the neutral brief, reconciles the advocates' points | Files; read-only graph tools |
| Rule drafter | Claude Sonnet 5.5 | From each regulation and direction, extracts conditions and outcomes as candidate `JurisdictionRule` records, each with the clause and quote it rests on | Files only |
| BMC-reading advocate | Claude Sonnet 5.5 | Makes the strongest case for the corporation's reading, from the texts only | Files only |
| SRA-reading advocate | Claude Sonnet 5.5 | Makes the strongest case for the authority's reading, from the texts only | Files only |

The two advocates use the same agent definition with a different brief, so neither is favoured by its instructions. The definition would be added to `managed-agents/agents/` in the same file format as the existing agents, and the lead would list the drafter and the advocate in its roster.

### Instructions that matter

For the advocates:

> Argue only from the documents you are given. Quote the exact words you rely on, with document and page. Do not characterise the other side's motives. Where the text is silent or ambiguous, say so; that is a finding, not a weakness. End with the three factual questions which, if answered by data, would most help or hurt this reading.

For the lead:

> You do not decide who is right. Set out the text, then each reading with its quotes, then where they differ and why. For each disputed factual claim, state what the register's data shows and what it cannot show. Use the same length and tone for both readings. Do not use words that imply bad faith. A lawyer will review this before anyone else sees it.

For the rule drafter:

> A rule may contain only conditions the text states. If a condition needs interpretation, write it as a contested condition and name the position that contests it. Never write a rule from a press report.

### Why two advocates and not one summary

A single summary of a legal dispute tends to drift toward whichever side's documents are longer or more recent. Two agents with equal briefs and equal sources, followed by a lead held to equal length and tone, is a cheap structural guard against that. The advocates' closing lists of factual questions also become the audit desk's work list.

This adds three agents' worth of tokens per brief. A brief is written once per new direction or order, not per resident's question, so the cost is small and bounded by the session budget.

## 3. Outcome rubric for the brief (starter)

- The brief quotes the operative text of Regulation 33(11) and of each direction, with document and page.
- Each reading is stated in its own section of comparable length, and every assertion in it is tied to a quote.
- A table lists each point of difference with the words each side relies on.
- Each disputed factual claim (premium loss, schemes on vacant plots, tenements delivered) is followed by what the register shows, with counts and sources, or the statement that the register holds no data on it.
- The brief does not state or imply which reading is correct.
- No sentence attributes motive or bad faith to an authority, an officer or a developer.
- A final section lists the records that would settle each factual claim and which authority holds them.

## 4. Pipeline

Added to the LangGraph pipeline in `managed-agents/orchestrator.py` as a second entry point.

```
new document (direction, letter, court order, LOI list)
        │
        ▼
   classify ── scheme document ──► intake ──► quote check and load ──► audit (tenements, sign-offs)
        │                                                                   │
        └── legal text ──► regulation desk: extract clauses and positions   │
                                   │                                        │
                                   ▼                                        │
                         draft rules ──► LAWYER REVIEWS RULES (pause)       │
                                   │                                        │
                                   ▼                                        │
                         recompute jurisdiction cards (code)                │
                                   │                                        │
                                   ├──► cards that changed ──► notify subscribers
                                   ▼                                        ▼
                         dual-reading brief ──────────────► EDITOR OR LAWYER RELEASES (pause)
                                                                            │
                                                                            ▼
                                                                         publish
```

Two points are fixed in code and not left to a model:

- **Rules do not take effect until a lawyer approves them.** The pipeline pauses with the candidate rules and their quotes. Until then, cards show the previous answer with a banner that a new direction is under review.
- **Cards are computed by code from approved rules.** No agent writes a jurisdiction answer.

When a new direction arrives, as on 2 November 2026, the visible result is: every affected card shows the new basis and date, subscribers are told what changed for their plot, and the brief gains a section.

## 5. The `which_authority` tool

Added to the citizen desk's tools.

| Input | Output |
|---|---|
| A plot's survey number, or a location, or a scheme or society name | Plot status claims with sources; scheme and regulation; authority currently directed to process it and the basis; any position contesting that; approvals and pending sign-offs; which office to approach for which matter |

The citizen desk is told to present the directed authority and the contest as two separate facts, and to add that this summarises published directions and is not legal advice.

## 6. Safeguards specific to this idea

| Risk | Control |
|---|---|
| The tool is seen as taking a side | Equal-brief advocates; rubric on balance; both authorities offered a right to correct the record before release |
| A wrong jurisdiction answer misdirects a resident | Rules approved by a lawyer; every card shows its basis and date; "under review" banner when the law moves |
| A plot is wrongly shown as slum or non-slum | Status is always a dated claim attributed to its maker; conflicting claims are shown together |
| Displaced families are identified | Tenement records are counts per scheme. No names, no allotment lists. |
| A developer is implied to be at fault for a delay | Record stages and dates only; the Challenger reviews any case file naming a developer |
| The matter is before a court | Report orders as issued; no comment on pending proceedings |
