# SPEC-009: Workflow engine and human gates

| | |
|---|---|
| Status | In progress: all acceptance criteria pass with stubbed desks; no live run yet (the audit desk is SPEC-011) |
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
hishob workflow run <thread> --hash <sha256> [--hash …] --ward <code> [--ward …]
hishob workflow status <thread>
hishob workflow resume <thread> continue|stop|approve|hold|<ward,ward> --reason "…" --token <reviewer token>
hishob workflow retry <thread>
hishob workflow consume --queue-url <url> [--max N]
```

Queue message: `{"workflow": "W1", "thread": "t1", "hashes": ["…"], "wards": ["K/W"]}`.

Postgres, schema `flow`: LangGraph checkpointer tables; `flow.decisions(thread_id, gate, decision, reason, account_id, decided_at)`; `flow.steps(thread_id, step, result, finished_at)` for completed side-effect steps.

Published outputs: `published/<ward-slug>/<run_id>/<file>` in the public store.

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

| Id | Task | Size | Depends on | Verifies | State |
|---|---|---|---|---|---|
| T1 | Port graph; step interfaces; stubbed tests | M | | AC1 | Done |
| T2 | Postgres checkpointer; restart test | M | T1 | AC2 | Done |
| T3 | Queue consumer and command line | S | T1 | AC3 | Done |
| T4 | Review threshold gate | S | T1 | AC4 | Done |
| T5 | Release gate, decision records, tier check | M | T1, SPEC-007/T1 | AC5, AC6 | Done |
| T6 | Idempotent session start and publish | M | T2 | AC7 | Partly: publish and completed steps are idempotent; reattaching to a running session is not built |

## Change log

| Date | Change |
|---|---|
| 16 Nov 2026 | Implemented in `app/src/hishob/workflows/` (`w1.py`, `live.py`) and migration `app/migrations/007_flow.sql`; tests in `app/tests/integration/test_spec009_workflow.py`. Command: `hishob workflow`. |

### Decisions made while building

- **Steps behind a protocol.** `Steps` has `intake`, `audit` and `publish`. Tests use stubs; `LiveSteps` uses the intake desk and real publishing. Its `audit` raises until SPEC-011 provides the audit desk, so W1 cannot yet run end to end on real documents.
- **Audits run in parallel**, one LangGraph `Send` per ward, and wait together at one release gate.
- **The release gate takes** `approve` (every ward), `hold` (none) or a list of wards. Holding ends the run with nothing published.
- **Two checks on resume.** The command line refuses any token that is not a valid reviewer token before it connects to anything; `Engine.resume` checks the tier again and requires a non-empty reason, so no other caller can skip it. Every decision is written to `flow.decisions`.
- **Completed steps are recorded** in `flow.steps`. When a run is retried, a finished intake or audit returns its saved result and is not called again.
- **Publishing is content-idempotent.** Each file is copied with a write-if-absent. Copying the same bytes again does nothing; different bytes under the same key are an error, never an overwrite. A publish interrupted part way through finishes on `retry` with each file present once (AC7).
- **Thread ids are used once.** Starting a thread that already exists is refused.

### Not done yet

- **Reattaching to a running session.** If the worker dies while the intake desk's session is still running, a retry starts a new session. The cost is repeated work, not duplicated facts, because the ledger refuses duplicates (SPEC-003). Recording the session id before streaming and reattaching to it is still to do.
- **Restart test is in-process.** AC2 resumes with a new engine and new database connections, with nothing kept in memory. It does not kill an operating-system process, and the one-minute restart target is not measured.
- **No live run.** That waits for the audit desk.
