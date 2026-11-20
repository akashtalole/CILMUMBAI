# SPEC-021: Review screen (release slice)

| | |
|---|---|
| Status | In progress: the release gate is built and tested end to end; queues for held facts, merges and rules are not |
| Milestone | M2 |
| Owner role | Full-stack engineer |
| Depends on | SPEC-007, SPEC-009, SPEC-011, SPEC-020 |
| ADRs | 0010, 0014 |
| Personas served | Advocate Nair, reviewers |

## 1. Problem and outcome

The workflow pauses at two human gates, and until now the only way to answer one was a command line with a signed token. A reviewer, who is a lawyer and not an engineer, needs to see what is about to be published and decide.

When this slice is done, a reviewer opens a link, sees each run waiting at a gate with the files it would publish and the cases held back, reads any of them, and releases or holds with a reason that is recorded.

## 2. User stories

- As Advocate Nair, I want to read each ward’s brief and cases before anything is public.
- As a reviewer, I want to release one ward and hold another in a single decision.
- As the product lead, I want every decision recorded with who made it, when and why.

## 3. Requirements

| Id | Requirement |
|---|---|
| R1 | Only the reviewer tier shall use the review endpoints; every other caller shall be refused, and the endpoints shall be off if access tiers are not configured. |
| R2 | The screen shall list runs, newest first, with where each waits, the question, the staged files and the held cases with their reasons by ward, the log, and the decisions so far. |
| R3 | A reviewer shall be able to read any staged output as text, and nothing outside the staging area. |
| R4 | A reviewer shall answer a gate with continue, stop, approve, hold, or a list of wards to release; a reason shall be required; the decision shall be recorded with the account and the time; a run that is not waiting shall refuse a decision. |
| R5 | Nothing shall be public before a release decision, only the wards released shall be published, and held cases shall never be offered or published, whatever is decided. |
| R6 | A process other than the one that started a run shall be able to answer its gates, and the process behind the screen shall never run the paid desks. |
| R7 | The web page shall show a Review tab only for a reviewer’s access code or a link ending in `#review`, let the reviewer read files, tick wards and give a reason, and disable the decision until a ward and a reason are given. |

## 4. Acceptance criteria

| Id | Given | When | Then | Verifies |
|---|---|---|---|---|
| AC1 | No code, and contributor, researcher and official codes | They call the three endpoints | Each is refused with 403; a reviewer is accepted; with no engine configured the answer is 503 | R1 |
| AC2 | A run waiting at the release gate with two wards | A reviewer lists runs | It shows the gate, both wards, the staged files without any held file, the held case with its reason, the log and no decisions | R2, R5 |
| AC3 | The same run | A reviewer reads a staged file, and then tries a key outside `staging/`, with `..`, with a backslash, or one that does not exist | The file’s text comes back; every other key is a 404 | R3 |
| AC4 | The same run | A contributor, an empty reason, no reason and a decision that is not an answer are tried; then one ward is released with a reason; then another decision | They are refused with 403, 422, 422 and 422; only the released ward is published and not its held case; the decision is listed with its account and reason; the next decision is a 409; holding publishes nothing | R4, R5 |
| AC5 | A run started by a worker engine | An engine with publish-only steps answers its gate through the API | The run finishes and publishes; the publish-only steps refuse to run an intake or an audit | R6 |
| AC6 | A browser against the real API, with a run waiting in Postgres | A visitor, a contributor and a reviewer use the page | The tab is hidden until `#review`; a contributor’s code is refused; the reviewer sees the run, reads a file, finds the decision disabled until a ward and a reason are given, releases one ward, and the run finishes with its decision recorded; the public folder holds only that ward, without its held case | R7, R5 |

AC1 to AC5 are `app/tests/integration/test_spec021_review_api.py`; AC6 is `app/web/e2e/review.mjs` against a run staged by `app/demo/seed_review.py`.

## 5. Interfaces and data contracts

```
GET  /review/threads                    runs: {thread, log, waiting: {gate, question, wards?, staged?, held?}, finished, published, decisions}
GET  /review/files?key=staging/…        {key, text, truncated}
POST /review/threads/{thread}/decision  {decision: continue|stop|approve|hold|[wards], reason}  -> the run; 403, 409, 422
```

Setting: `HISHOB_REVIEW_ENABLED` (default on when `HISHOB_TOKEN_SECRET` is set). The API process builds an engine with publish-only steps.

## 6. Non-functional requirements

- The list reads at most thirty runs; a file is cut at 200 KB.
- Decisions are never lost: they are written before the run resumes.

## 7. Constitution

| Article | How this spec upholds it |
|---|---|
| C4 | Publishing is a code step after a human decision |
| C5 | Held cases are never offered or published |
| C6 | The release gate is answered only by a reviewer, with a recorded reason |
| C8 | The endpoints read and act under the reviewer tier |

## 8. Out of scope

Queues for held facts, entity merges, findings and rules, and comments on a case (the rest of SPEC-021); editing a case in the screen; real sign-in (SPEC-013); a Marathi and Hindi interface for reviewers, who work in English.

## 9. Design notes

- Run state is in Postgres, so the API process can answer a gate the worker started, which is how production runs (R6).
- The review tab is hidden from residents by default rather than by trust: it appears for a reviewer’s code or a `#review` link, and the server decides what any code may do.

## 10. Tasks

| Id | Task | Size | Depends on | Verifies | State |
|---|---|---|---|---|---|
| T1 | Engine: list runs and decisions; publish-only steps | S | SPEC-009 | AC5 | Done |
| T2 | Review endpoints under the reviewer tier | M | T1 | AC1 to AC4 | Done |
| T3 | Review tab | M | T2 | AC6 | Done |
| T4 | Demo seed and browser test against the real stack | S | T3 | AC6 | Done |

## Change log

| Date | Change |
|---|---|
| 20 Nov 2026 | Implemented in `app/src/hishob/workflows/w1.py`, `app/src/hishob/api/app.py`, `app/web/src/components/Review.tsx` and `app/web/src/token.ts`; `app/demo/seed_review.py`. The access-code handling the Alerts tab used moved into the shared `token.ts`. |

### Not done yet

- The other queues in the spec’s scope (held facts, merges, findings, rules).
- Sign-in: the reviewer pastes a signed access code until Cognito (SPEC-013).
- A notification when a run starts waiting.
