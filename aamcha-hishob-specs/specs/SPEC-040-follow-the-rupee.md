# SPEC-040: Follow the Rupee

| | |
|---|---|
| Status | In progress: all acceptance criteria pass on the challenge dataset; Claude's notes are checked live; the judges' answer key is not out yet |
| Milestone | Claude Impact Lab Mumbai, 21 November 2026 |
| Owner role | AI engineer |
| Depends on | SPEC-007, SPEC-011 (the banned-word check), SPEC-020 |
| ADRs | 0003, 0011 |
| Personas served | Sunita (resident), the corporator, the ward officer, the journalist |

## 1. Problem and outcome

Every monsoon Mumbai spends crores repairing the same roads. Citizens complain, contractors repair, and nobody can easily say where the money went, whether the fix lasted, or where the next rupee should go. The challenge dataset (synthetic, all contractors fictional) has hidden problems in it: inflated bills, duplicate charges and repairs paid for while a road was still under the contractor's guarantee.

When this is done, anyone can open a ward and see its budget against its spend, what failed, what is in question and why, a fair grade for the ward and for every contractor, and a ranked, costed list of what to fix next; and a resident can type their complaint number and be told, in their language, what happened to it.

## 2. User stories

- As a corporator, I want a one-paragraph summary of my ward I can read out in a meeting, with every figure traceable.
- As a ward officer, I want the next fixes ranked by risk, with the method that lasts and what the remaining budget pays for.
- As a journalist, I want each questionable bill with a one-line reason and the rows behind it, so I can check it myself.
- As Sunita, I want to type my complaint number and hear in Marathi whether it was fixed, by whom, for how much, and whether it held.

## 3. Requirements

| Id | Requirement |
|---|---|
| R1 | The system shall link every complaint to the work order that fixed it where the data gives one, place complaints with no ward from the gazetteer (Latin and Devanagari aliases) or GPS, read the kind of problem from words in English, Hinglish, Marathi and Hindi, find the road from its name or position, and group open reports of one problem into one issue, recording how each choice was made. |
| R2 | The system shall flag, in code with written thresholds: bills above 1.5 times the rate card; a bill with no complaint behind it for the same road and work within 7 days and 15% of another; and any payment for a repair on a road under its Defect Liability Period. Each flag shall give the work order, a one-line reason, the money in question and the dataset rows it rests on. A fix that failed within 30 days and was paid for again to the same contractor shall be shown as a lead, not counted as money in question. |
| R3 | The system shall score each contractor and ward against what was expected for the same jobs (method and rain for durability; kind of work, flood-proneness and rain for speed), where 50 means as expected, so that context is accounted for and volume is never punished. A contractor's billing score shall count only its own bills; payments during the guarantee period count against the ward that approved them. |
| R4 | The system shall rank each ward's open issues by a risk score made of severity, flooding at that spot (last season's rain against its threshold, and big tides), traffic and bus routes, road-condition accidents, hospitals and schools that depend on the road, and how many people reported it; show the parts and the reasons; choose the method that fails least for that kind of problem; and fund issues in order from the ward's remaining budget, sending roads under DLP to the original contractor at no cost. |
| R5 | Claude shall write the plain-language scorecards and ward summaries from the computed figures only. Text with a banned word, a number that is not one of the figures, a cut-off reply or too many words shall be replaced by a written template, and the page shall say which wrote it. |
| R6 | `hishob rupee build` shall write the flags, linked complaints, plan and scorecards as CSV files and one JSON bundle; the same data shall always give the same flags, scores and ranking. |
| R7 | Given a complaint number, the system shall say in Marathi, Hindi or English what happened to it: the work order, contractor, date, cost, whether it met the SLA, whether it held and any flag on the bill; or that it is still open, and past its SLA, and where to follow it up. |
| R8 | The API shall serve the bundle read-only under /rupee (summary, ward, contractor, flags, work order, complaint, plan, ward shapes), say 503 when nothing has been built, and be off when not configured; the web app shall show it with every figure linking to its row in the dataset. |

## 4. Acceptance criteria

| Id | Given | When | Then | Verifies |
|---|---|---|---|---|
| AC1 | The challenge dataset | The auditor runs | It flags 109 over-billed jobs, 45 duplicates and 493 payments under DLP; every flag cites its work order's line, and each can be re-derived from the CSV by hand; nothing within the normal 30% band is flagged; money in question counts each job once | R2 |
| AC2 | The 6,501 complaints | They are linked | Every complaint the data links is tied to its work order, the rest have a state; issues are fewer than complaints; open reports of one road and problem are one issue; almost every complaint has a ward; problems are read correctly in four languages, and "petrol pump" is not waterlogging | R1 |
| AC3 | The scorecards | They are computed, and again with every job duplicated | 50 means as expected and the scale is bounded; doubling the same work leaves the scores unchanged; all 8 contractors and 24 wards are scored; contractor billing counts only over-billing and duplicates; the contractor with the most over-billing ranks last | R3 |
| AC4 | The plan | It is built for every ward | Items are in risk order with reasons and evidence; funded cost never exceeds the remaining budget; DLP roads cost BMC nothing; the method chosen fails least for that kind of problem, and for potholes it is not cold mix | R4 |
| AC5 | A scripted model | It returns a good note, an accusation, an invented number and a cut-off reply | Only the good note is kept; the others are replaced by the template with the problem recorded; with no model the template is used; the templates pass the same checks | R5 |
| AC6 | A fixed complaint, an open one and an unknown number | Each is looked up in English, Marathi and Hindi | The fixed one names its work order, contractor and cost in the chosen language; the open one says so with no work order; the unknown one is not found | R7 |
| AC7 | A built bundle | The files are written and the endpoints called | Five files are written and the flags CSV cites rows; each endpoint answers from the bundle, ward codes with a slash work, unknown ids are 404, no bundle is 503 and an unconfigured server has no /rupee | R6, R8 |

AC1 to AC7 are `app/tests/unit/test_spec040_rupee.py`.

## 5. Interfaces and data contracts

- Input: `app/datasets/follow-the-rupee/data/*.csv` and `*.geojson`, copied unchanged from the challenge repository (CC BY 4.0; see `SOURCE.md`).
- Evidence: `file.csv#L<line>`, line 1 the header. The web app opens it on GitHub at that line.
- CLI: `hishob rupee build [--data DIR] [--out var/rupee] [--claude]`.
- Outputs: `bundle.json`, `flags.csv`, `complaints_linked.csv`, `next_rupee.csv`, `scorecards.csv`.
- API: `GET /rupee/summary`, `/rupee/ward?code=`, `/rupee/contractor?id=`, `/rupee/flags?rule=&ward=&contractor=`, `/rupee/workorder?id=`, `/rupee/complaint?id=&lang=`, `/rupee/plan`, `/rupee/wards.geojson`. `HISHOB_RUPEE_DIR` sets where the bundle is (default `var/rupee`).

## 6. Non-functional requirements

- The whole build runs in about five seconds without Claude, and a minute or two with it.
- Findings never depend on a model: Claude only writes the text around them.

## 7. Constitution

- C3 (no conclusions): the text says what the records show, never fraud or intent; the banned-word check from SPEC-011 enforces it.
- C5 (every figure sourced): every flag, plan item and complaint carries the rows it came from.

## 8. Out of scope

- The social posts. They are noisy and unverified; they could later raise the demand part of risk.
- Judging the rules against the answer key: it is published after the event. When it is, it becomes an evaluation set (SPEC-012).

## 9. Design notes

- The thresholds come from the data dictionary: normal jobs vary 20 to 30% around the rate card, so 1.5 times is well outside it. In the data the ratios cluster between 0.8 and 1.3, with a clear gap before the over-billed ones.
- The fairness strata were tested before being used. Rain in the week after a repair did not change how often it failed (24% either way); the repair method did (cold mix 32%, hot mix 23%); low-lying wards met fewer SLAs (47% against 55%). Contractors' reopen rates run from 9% to 39%, which the method mix does not explain.
- About 18% of reported categories are wrong. For a complaint with a work order we take the kind of work from the work order; for the rest, from the words.
- Contractors' listed active wards do not match where they worked (most jobs are outside them, for every contractor alike). We read that as noise in the generator, not a finding, and do not flag it.

## Change log

- 2026-11-21: written and built on the day the dataset was released.
