# SPEC-011: Audit desk and release

| | |
|---|---|
| Status | Draft |
| Milestone | M1 |
| Owner role | AI engineer |
| Depends on | SPEC-007, SPEC-009 |
| ADRs | 0003, 0011 |
| Personas served | Farah, Arjun, Corporator Pawar, Assistant Engineer, Advocate Nair |

## 1. Problem and outcome

The graph holds records; people need findings they can act on, and findings that name parties carry legal risk. The starter code defines an audit lead with a Challenger and a Drafter.

When done, an audit run for a ward produces a one-page brief, case files that have each been challenged, drafted complaints, RTI applications and meeting questions, and a gaps file. Nothing leaves the run until a reviewer releases it.

## 2. User stories

- As Farah, I want three questions for Saturday's ward meeting, each with its source.
- As the Assistant Engineer, I want the defects on roads still under contractor liability.
- As Advocate Nair, I want each finding with its evidence and its challenge, so that I can release or hold it quickly.

## 3. Requirements

| Id | Requirement |
|---|---|
| R1 | The audit lead shall read the graph only through read-only tools under the reviewer tier. |
| R2 | The run shall produce `ward-brief.md`, `cases/`, `held/`, `drafts/` and `gaps.jsonl` as specified in the audit rubric. |
| R3 | Every case file shall be reviewed by a Challenger agent, whose review is stored beside it with a verdict of publish, publish with changes, or hold. |
| R4 | Case files with verdict hold shall be placed in `held/` with the reason and not in `cases/`. |
| R5 | No output shall contain the words fraud, scam, corrupt, cartel, nexus or siphoned, or their Marathi and Hindi equivalents, or name an official other than by post. |
| R6 | Every amount, date, contractor and tender number in the brief and case files shall be followed by a source reference that resolves to a fact. |
| R7 | The run shall be graded against the ward-audit rubric and revised until it passes or reaches the iteration limit. |
| R8 | The outputs shall reach the public location only after a reviewer approves them at the release gate (SPEC-009). |

## 4. Acceptance criteria

| Id | Given | When | Then | Verifies |
|---|---|---|---|---|
| AC1 | The audit agent definitions | CI lint runs | The lead's tools are read-only; Challenger and Drafter have file tools only | R1 |
| AC2 | A completed run for the demo ward | Outputs are listed | All R2 files and folders exist | R2 |
| AC3 | Any file in `cases/` | Its folder is listed | A `.challenge.md` with a verdict of publish or publish with changes is beside it | R3 |
| AC4 | A case the Challenger held | Outputs are listed | It is in `held/` with a reason and absent from `cases/` | R4 |
| AC5 | All outputs | The banned-word and post-only check runs in code | No violations | R5 |
| AC6 | All outputs | Source references are resolved through the API | Every reference resolves to a fact, and the cited values match | R6 |
| AC7 | A run whose first draft misses a rubric criterion | The run continues | Grader events show revision until satisfied or the limit | R7 |
| AC8 | A completed run | Before release | Nothing from it is in the public location; after approval, the approved files are | R8 |

## 5. Interfaces and data contracts

```python
def run_audit(ward: str, *, cap_usd: int) -> AuditRun: ...   # outputs in staging/<run>/
def check_outputs(path: Path) -> OutputCheck: ...            # banned words, posts, references
```

Agent files: `app/agents/{audit-lead,challenger,drafter}.md`; rubric `app/agents/rubrics/ward-audit.md`.

## 6. Non-functional requirements

- A ward audit completes within the session's unattended time limit.
- Spending cap per run set at creation.

## 7. Constitution

| Article | How this spec upholds it |
|---|---|
| C3 | R6, AC6: references resolve and values match |
| C4 | Lead and specialists cannot write stores or publish |
| C5 | R3, R5: Challenger review; banned words and post-only check in code |
| C6 | R8: release gate |
| C8 | R1: reads under a defined tier |

## 8. Out of scope

Regulation desk and jurisdiction cards (SPEC-026). Contractor network views (later). Newsroom distribution (SPEC-031).

## 9. Design notes

- The output check in code runs after the session and before the release gate; a violation sends the run back to the lead once, then holds the file.
- Marathi and Hindi banned-word lists are drafted with the language reviewer and the lawyer.

## 10. Tasks

| Id | Task | Size | Depends on | Verifies |
|---|---|---|---|---|
| T1 | Move agent files and rubric; lint | S | SPEC-005/T2 | AC1 |
| T2 | `run_audit` on `agentkit`, tools under reviewer tier | M | SPEC-007/T3 | AC2, AC7 |
| T3 | Output layout check | S | T2 | AC2, AC3, AC4 |
| T4 | Banned words and post-only check in three languages | M | | AC5 |
| T5 | Reference resolver and value comparison | M | SPEC-007/T5 | AC6 |
| T6 | Wire to release gate in W1 | S | SPEC-009/T5 | AC8 |
