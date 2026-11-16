# SPEC-011: Audit desk and release

| | |
|---|---|
| Status | In progress: all acceptance criteria pass with scripted agents, plus a live run; awaiting review |
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
def run_audit(client, http, ward, data, *, run_id, token, cap_usd=10) -> AuditRun: ...  # staging/<run_id>/
def check_outputs(files, http, *, token, private_names, contractor_names, keep_names) -> OutputCheck: ...
def arrange(raw_files) -> Arranged: ...   # places files by name and by the Challenger's verdict
```

```
hishob audit run K/W --api http://127.0.0.1:8000 [--run-id …] [--cap-usd 10]
```

Staging layout: `ward-brief.md`, `gaps.jsonl`, `cases/case-NN-*.md` with `case-NN-*.challenge.md`, `held/` (each held case with its review and a `.held.md` reason written by code), `drafts/{rti-NN,complaint-NN,questions}.md`, `manifest.json` (the run record). Only files outside `held/` and the manifest are offered for release.

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

| Id | Task | Size | Depends on | Verifies | State |
|---|---|---|---|---|---|
| T1 | Move agent files and rubric; lint | S | SPEC-005/T2 | AC1 | Done |
| T2 | `run_audit` on `agentkit`, tools under reviewer tier | M | SPEC-007/T3 | AC2, AC7 | Done |
| T3 | Output layout check | S | T2 | AC2, AC3, AC4 | Done |
| T4 | Banned words and post-only check in three languages | M | | AC5 | Done in code; the Marathi and Hindi lists still need the language reviewer and the lawyer |
| T5 | Reference resolver and value comparison | M | SPEC-007/T5 | AC6 | Done |
| T6 | Wire to release gate in W1 | S | SPEC-009/T5 | AC8 | Done |

## Change log

| Date | Change |
|---|---|
| 16 Nov 2026 | Implemented in `app/src/hishob/agentkit/` (`audit.py`, `outputs.py`; `ward_summary` tool in `tools.py`; `honorific_names` in `redact.py`), `app/agents/{audit-lead,challenger,drafter}.md` and `app/agents/rubrics/ward-audit.md`; wired into W1 through `workflows/live.py`. Tests in `app/tests/unit/test_spec011_parts.py` and `app/tests/integration/test_spec011_audit.py`. Command: `hishob audit run`. |

### Decisions made while building

- **Code decides where files go.** A case stays in `cases/` only if a review beside it ends in `Verdict: publish` or `Verdict: publish with changes`. A held verdict, a missing review or a review with no verdict sends the case and its review to `held/`, with the reason written by code. The folder the agent used does not matter; files are placed by name.
- **References are fact ids in brackets**, as in the citizen desk. They are checked per paragraph and per table row: every amount, date and identifier in the brief and the case files must be found in the facts cited in that same block, through `POST /answers/check` under the reviewer tier. Contractors seen in tool results must be cited wherever they are named. In drafts, every fact id must resolve; their dates are requests ("for 1 April 2026 to date"), not claims, so values are not compared.
- **No computed figures.** The lead is told to state only values a record states and to describe totals and durations in words or counts, because a computed total has no fact to cite.
- **Banned words by stem**, in English and in Devanagari (so case endings such as घोटाळ्याचा are caught). People are caught two ways: anyone named after an honorific (Shri, Smt, Mr, श्री …), using the same landmark rules as the citizen desk's redaction, and any Person node seen in tool results. Elected representatives can be passed as names to keep.
- **One fix round, then hold.** If the check finds problems, the lead is sent the list once. Whatever still fails is held with the reasons; a problem in the brief or a missing required file marks the run incomplete. Held files are not checked again: they are never offered for release.
- **The Challenger does not repeat banned words or names** in its review, because the review is published beside the case.
- **The desk reads as a service account.** The command line and the W1 worker sign a reviewer-tier token for `audit-desk` with `HISHOB_TOKEN_SECRET`.
- **Repeat-safe.** A finished run is found by its manifest and returned without a new session. A run interrupted while writing gets a new run id (`…-r2`) instead of overwriting.
- **The release gate shows** each ward's staged files and what is held, so the reviewer sees both before deciding (AC8).

### Not done yet

- **Changes asked for by the Challenger are not checked in code.** A `publish with changes` verdict passes once the review exists; whether each change was made is left to the rubric grader and the reviewer at the release gate.
- **Language and legal review** of the Marathi and Hindi banned-word lists.
- **Officials named without an honorific** and not present as Person nodes are not caught by code; the Challenger is told to flag them.

## First live run (16 November 2026)

Ward K/W, on the facts from the first live intake (SPEC-005), which come from the synthetic test-fixture tender documents and the DataMeet ward boundaries. Command: `hishob audit run K/W --cap-usd 8`.

| Measure | Result |
|---|---|
| Agents that ran | Audit lead; Challenger and Drafter as sub-agents |
| Rubric grading | `needs_revision`, then `satisfied` |
| Outputs | Ward brief, 1 case file with its review (`publish with changes`, 10 changes listed), 8 RTI applications, meeting questions, 8 gaps |
| Cost and time | $2.54, 17 minutes |
| What the brief said | The graph holds the ward and one partial award sentence ("The work of desilting nullahs in K/West ward is awarded to", which stops there); each of the five checks found nothing, stated as missing records rather than as nothing wrong; two ward nodes (K/W and K/West) that the records do not link |
| Code check, as run | Failed the brief, so the run was marked incomplete: the brief points to its own files (`drafts/rti-01.md`, `cases/case-01-…`) and the identifier rule took those paths for unsourced work numbers. The fix request did not help, because the problem was in the check |
| Fix | References to the run's own files and backticked graph node ids are removed before the value check; tender and work numbers written as text are still checked (regression test from this run) |
| Code check, after the fix | All 13 outputs pass: no banned words, no people named, every fact id resolves and every cited value matches |

What it showed beyond the acceptance tests: the desk says plainly when the records are thin instead of filling gaps; the RTI drafts ask for named records and leave the resident's details blank; and the intake left two nodes for one ward (K/W from the boundary file, K/West from a tender), which entity resolution in SPEC-005 should merge.
