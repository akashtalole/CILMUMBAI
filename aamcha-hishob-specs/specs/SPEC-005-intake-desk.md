# SPEC-005: Intake desk

| | |
|---|---|
| Status | In progress: all acceptance criteria pass (AC5 in the live test only); awaiting second review and demo |
| Milestone | M0 |
| Owner role | AI engineer |
| Depends on | SPEC-001, SPEC-002, SPEC-003 |
| ADRs | 0002, 0003, 0009 |
| Personas served | All, indirectly; reviewers directly |

## 1. Problem and outcome

Reading hundreds of civic documents in two languages is the bulk of the work. The starter code defines an ingest lead with extractor, verifier and resolver agents on Claude Managed Agents, but it is untested and not wired to the archive or the ledger.

When done, a batch of archived documents is read by the intake desk, every document is extracted and independently verified, entity matches are proposed, and the outputs are handed to the loader (SPEC-003). The run is reproducible: agent versions, inputs and cost are recorded.

## 2. User stories

- As a data engineer, I want to submit a list of archived documents and get back a facts file, a review file and a report.
- As a reviewer, I want unsure entity matches and low-confidence facts listed, so that I decide them.
- As the product lead, I want each run's cost and agent versions recorded.

## 3. Requirements

| Id | Requirement |
|---|---|
| R1 | The desk shall accept a batch of archive hashes and mount each document, the generated record schema and a known-entities export as read-only files in the session. |
| R2 | The desk shall extract facts from every document using the record schema and shall have every document's facts checked by a separate verifier agent. |
| R3 | The session's sandbox shall have no outbound network access and no web tools; no agent in the desk shall have a tool that writes outside the sandbox. |
| R4 | The desk shall produce `facts.jsonl`, `review.jsonl` and `report.md`, where the report lists every input as covered or not covered with a reason. |
| R5 | The entity resolver shall merge organisations only on a hard identifier and shall never merge people without an official identifier; other candidates shall go to `review.jsonl` as `unsure`. |
| R6 | Where a page has no text layer, the extractor shall read the page image and mark facts from it with the page's scan status. |
| R7 | The runner shall record session id, agent ids and versions, input hashes, output file hashes, duration and cost, and shall hand `facts.jsonl` to the loader. |
| R8 | The session shall have a spending cap set at creation, and if it is reached the runner shall record the batch as incomplete rather than retry without limit. |

## 4. Acceptance criteria

| Id | Given | When | Then | Verifies |
|---|---|---|---|---|
| AC1 | Ten archived tender PDFs | A batch is run | The session mounts ten documents, the schema and the entities file; all three outputs are downloaded | R1, R4 |
| AC2 | A completed run | Session events are inspected | Each document has an extractor thread and a verifier thread | R2 |
| AC3 | The agent definition files | The CI lint runs | No agent has web tools enabled, the environment allows no hosts, and no custom tool can write | R3 |
| AC4 | A batch in which one PDF is corrupt | It is run | The report lists that file as not covered with a reason; the others are covered | R4 |
| AC5 | Two contractor names differing only in "M/s" and "Pvt Ltd", no registration number | Resolved | They appear in `review.jsonl` as `unsure`, not merged | R5 |
| AC6 | A scanned Marathi page | It is extracted | Its facts carry the page and arrive at the loader, which marks them `scan_unchecked` | R6 |
| AC7 | A completed run | The run record is read | It has every R7 field and the loader's batch report is linked | R7 |
| AC8 | A spending cap set very low | A batch is run | The run ends paused at the cap and is recorded as incomplete | R8 |

## 5. Interfaces and data contracts

```python
def run_intake(hashes: list[str], *, ward: str | None, cap_usd: int) -> IntakeRun: ...

@dataclass
class IntakeRun:
    session_id: str
    agents: dict[str, str]          # name -> "agent_id@version"
    inputs: list[str]               # sha256
    outputs: dict[str, str]         # filename -> sha256
    status: Literal["complete", "incomplete", "failed"]
    cost_usd: float
    duration_s: int
    load_report: str | None         # path to SPEC-003 report
```

Agent files: `app/agents/{ingest-lead,doc-extractor,fact-verifier,entity-resolver}.md`, environment `app/agents/environments/civic-cloud.yaml`, rubric `app/agents/rubrics/ingest.md`. They are applied with `hishob agents apply`, which uses the SDK and a local, uncommitted lock file (`app/agents/.lock.json`) of ids, versions and content hashes. This replaces `ant apply`, which was not available in the build environment; the file format is the same, so `ant apply` can take over later.

Mounts: each document at `/mnt/session/uploads/corpus/<sha256>.<ext>` so extracted facts cite their source by hash; the generated `records.json` and the ontology reference at `/mnt/session/uploads/schema/`; known entities at `/mnt/session/uploads/entities.jsonl`. Run records live in `agentkit.runs` (migration `003_agent_runs.sql`).

## 6. Non-functional requirements

- Field accuracy of at least 90% on the ten-document labelled set (SPEC-012 extraction set at M0 size).
- A batch of fifty documents completes within the session's unattended time limit; larger batches are split by the workflow.
- Readers use the smallest capable model; the lead uses the default model.

## 7. Constitution

| Article | How this spec upholds it |
|---|---|
| C1 | Schema requires page and quote on every record |
| C2 | Loader checks every quote after the run |
| C4 | R3: no write, web or publish tools; lint in CI |
| C7 | Only public documents are mounted |
| C11 | Agent changes go through the promotion gate (SPEC-012) |

## 8. Out of scope

Scheduling and source watch (SPEC-014). Graph tools for intake agents (they get an entities file instead).

## 9. Design notes

- Move `civic_client.py`'s `ingest`, `upload`, `download_outputs` and session loop into `hishob.agentkit`, with typed results and tests using recorded session event fixtures.
- Integration tests against the real API run in a nightly job with a small cap, not on every pull request.
- The workflow engine (SPEC-009) calls `run_intake`; this spec does not decide when to run.

## 10. Tasks

| Id | Task | Size | Depends on | Verifies | State |
|---|---|---|---|---|---|
| T1 | Move agent files to `app/agents/`; apply to a development workspace | S | | | Done |
| T2 | Agent definition lint (tools, network, models) in CI | S | T1 | AC3 | Done |
| T3 | `agentkit` session runner with recorded-event fixtures | M | | AC2 | Done |
| T4 | Mount archive documents, schema and entities file | S | T3, SPEC-001/T3 | AC1 | Done |
| T5 | Outputs download and run record | M | T3 | AC1, AC7 | Done |
| T6 | Hand-off to loader | S | T5, SPEC-003/T6 | AC7 | Done |
| T7 | Corrupt file handling and coverage report check | S | T5 | AC4 | Done |
| T8 | Resolver rules in prompt and rubric; fixture test | S | T1 | AC5 | Done |
| T9 | Scanned page path test | S | T6 | AC6 | Done |
| T10 | Spending cap and incomplete status | S | T3 | AC8 | Done |

## 11. Open questions

| Question | Owner | Assumption until answered |
|---|---|---|
| Organisation has the current multi-agent type | AI engineer | Yes; fall back to the older coordinator type without workflows if not |

## Change log

| Date | Change |
|---|---|
| 16 Nov 2026 | Implemented in `app/src/hishob/agentkit/` and `app/agents/`. Offline tests use a scripted client (`app/tests/fakes.py`); `app/tests/live/test_spec005_live.py` runs a real session when `HISHOB_LIVE=1`. Damaged PDFs are now archived with zero pages (SPEC-001 behaviour extended) so they can be reported as not covered. |

## First live run (16 November 2026)

Four fixture documents: an English tender, a Marathi and English tender with a scanned page, an award notice naming one contractor two ways, and a damaged PDF. Session capped at $5.

| Measure | Result |
|---|---|
| Status | complete |
| Cost and time | $1.63 list cost; 351 seconds |
| Threads | 3 Document extractor, 3 Fact verifier, 1 Entity resolver |
| Coverage | 3 covered; the damaged PDF reported as not covered, with the reason |
| Facts | 39 records: 26 loaded, 2 held, 11 notes |
| Quotes | All 26 loaded facts matched their pages exactly |
| Verifier | Rejected an invented tender built from a resolution number, and the three edges that depended on it |
| Contractor names | "M/s Shree Ganesh Infra Pvt. Ltd." and "Shree Ganesh Infrastructure" kept apart and sent to review (AC5) |

Findings to act on, each through the evaluation gate (SPEC-012) before any prompt changes:

1. **The extractor splits one entity into several records**, one quote each. This exposed a loader bug: whole-record supersession dropped properties. SPEC-003/R7 now supersedes property by property; replaying this run's facts gives each tender both its reference number and its cost.
2. **The resolver is too cautious with public bodies.** The rule written for contractors (merge only on a registration number) left three separate nodes for BMC. Public bodies and wards should match against a reference list: the place spine (SPEC-004) for wards, and a list of agencies.
3. **Wards without codes are held.** The extractor named wards ("K/West Ward", "के पश्चिम विभाग") without the code the shapes require. With the place spine mounted as known entities, it can use the official codes.
4. **Nothing was extracted from the scanned page.** The report says so. Reading page images is the next step for scans (ADR 0009).
