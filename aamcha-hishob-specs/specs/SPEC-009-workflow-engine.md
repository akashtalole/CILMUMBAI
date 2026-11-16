# SPEC-009: Workflow engine and human gates

| | |
|---|---|
| Status | Draft |
| Milestone | M1 |
| Owner role | Back-end engineer |
| Depends on | SPEC-003, SPEC-005 |
| ADRs | 0010 |
| Personas served | Reviewers, Advocate Nair |

## 1. Problem and outcome

Work flows from intake to loading to audit to release, with people deciding at two points. Runs may wait days. The starter pipeline proves the shape in dry-run mode with a SQLite checkpoint.

When done, LangGraph workflows run in a worker, checkpointed to Postgres, started from queue messages, with human gates that cannot be bypassed and that survive restarts.

## 2. User stories

- As a reviewer, I want a run to wait for my decision without losing its state.
- As an engineer, I want to restart the worker without breaking runs in progress.
- As the product lead, I want to see every run, where it is and what it waits for.

## 3. Requirements

| Id | Requirement |
|---|---|
| R1 | The engine shall run workflow W1 (ingest, load, review if many held, audit each ward, release, publish) as a LangGraph graph. |
| R2 | The engine shall checkpoint state to Postgres after every step and resume from the last checkpoint after a restart. |
| R3 | The engine shall start runs from queue messages and from the command line, each with a thread id. |
| R4 | When the share of held facts in a batch exceeds a configured threshold, the run shall pause for review before audit. |
| R5 | While a run is paused at the release gate, the engine shall not copy any output to a public location. |
| R6 | Only an account with the reviewer tier shall be able to resume a run from a gate, and each decision shall be recorded with account id, time and reason. |
| R7 | Steps with side effects (starting a session, loading, publishing) shall be safe to repeat after a restart without duplicating their effect. |

## 4. Acceptance criteria

| Id | Given | When | Then | Verifies |
|---|---|---|---|---|
| AC1 | A run of W1 with stubbed desks | It runs to the release gate | It pauses there with the expected state | R1 |
| AC2 | A run paused at a gate | The worker process is killed and restarted, then the run is resumed | It continues from the gate with its state intact | R2 |
| AC3 | A queue message `{workflow: W1, thread: t1, ...}` | The worker receives it | A run with thread `t1` starts | R3 |
| AC4 | A batch with 30% held and threshold 20% | Loading finishes | The run pauses at review; at 10% it proceeds to audit | R4 |
| AC5 | A run at the release gate | The public prefix is listed | It contains nothing from that run | R5 |
| AC6 | A run at a gate | A contributor-tier account tries to resume it | Refused; a reviewer can resume, and the decision row is written | R6 |
| AC7 | A run killed just after the publish step started | It is resumed | Each output exists once in the public prefix | R7 |

## 5. Interfaces and data contracts

```
hishob workflow run W1 --thread <id> --ward <code> [--ward …] <hashes…>
hishob workflow status --thread <id>
hishob workflow resume --thread <id> --decision continue|stop|approve|hold|<wards> --reason "…"
```

Postgres: LangGraph checkpointer tables; `flow.decisions(thread_id, gate, decision, reason, account_id, decided_at)`.

## 6. Non-functional requirements

- Restart to resumed in under one minute.
- A paused run costs nothing while waiting.

## 7. Constitution

| Article | How this spec upholds it |
|---|---|
| C6 | R5, R6: release gate, reviewer-only resume |
| C4 | Publishing is a code step after a human decision |
| C12 | One engine for all workflows |

## 8. Out of scope

Other workflows W2 to W8 (their specs add them on this engine). The review screen (SPEC-021); until then, the command line resumes runs.

## 9. Design notes

- Port `orchestrator.py`; replace the SQLite saver with the Postgres saver; replace dry-run stubs with `run_intake`, `load` and `run_audit` behind interfaces so tests stub them.
- Idempotency: a session start records its session id before streaming; a resumed step reattaches instead of starting another. Publishing writes with a content hash key so a repeat is a no-op.

## 10. Tasks

| Id | Task | Size | Depends on | Verifies |
|---|---|---|---|---|
| T1 | Port graph; step interfaces; stubbed tests | M | | AC1 |
| T2 | Postgres checkpointer; restart test | M | T1 | AC2 |
| T3 | Queue consumer and command line | S | T1 | AC3 |
| T4 | Review threshold gate | S | T1 | AC4 |
| T5 | Release gate, decision records, tier check | M | T1, SPEC-007/T1 | AC5, AC6 |
| T6 | Idempotent session start and publish | M | T2 | AC7 |
