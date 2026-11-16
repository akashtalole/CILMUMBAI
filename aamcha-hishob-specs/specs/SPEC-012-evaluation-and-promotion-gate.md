# SPEC-012: Evaluation harness and promotion gate

| | |
|---|---|
| Status | Draft |
| Milestone | M1 |
| Owner role | AI engineer |
| Depends on | SPEC-005, SPEC-007, SPEC-008 |
| ADRs | 0019 |
| Personas served | All, indirectly |

## 1. Problem and outcome

A changed prompt, rule or model can quietly make answers worse, often in one language. Without measurement, nobody notices until a resident is misled.

When done, three evaluation sets live in the repository, a harness runs them and reports by route and language, and CI blocks any behaviour change that regresses until an owner approves.

## 2. User stories

- As an AI engineer, I want to know whether my prompt change helped, by language.
- As the product lead, I want no release that makes Marathi answers worse.

## 3. Requirements

| Id | Requirement |
|---|---|
| R1 | The repository shall hold an extraction set (labelled documents with expected records), a question set (questions with verified answers and expected cited facts) and a refusal set (questions that must be declined or redirected), each item tagged with language and route. |
| R2 | The harness shall score extraction by field accuracy and quote-match rate; questions by correctness of key values, citation-check pass and correct "not known" replies; refusals by appropriate decline. |
| R3 | The harness shall report every score overall, by language and by route, and compare it with the last released baseline. |
| R4 | When a pull request changes files under `app/agents/`, `app/ontology/`, prompts, rules or retrieval settings, CI shall run the harness against staging. |
| R5 | If any score falls below the baseline by more than the configured tolerance in any language, then CI shall fail until an owner records an approval with a reason. |
| R6 | The harness shall record the cost and duration of each run. |
| R7 | Evaluation items shall contain no personal data of private individuals. |

## 4. Acceptance criteria

| Id | Given | When | Then | Verifies |
|---|---|---|---|---|
| AC1 | The repository | The datasets are validated | Each item has language and route; M1 sizes are at least 10 documents, 30 questions (10 per language) and 10 refusals | R1 |
| AC2 | A stub system returning known outputs | The harness runs | Scores equal hand-computed values | R2 |
| AC3 | A completed run | The report is read | It shows scores by language and route and the difference from baseline | R3 |
| AC4 | A pull request touching `app/agents/citizen-desk.md` | CI runs | The evaluation job runs | R4 |
| AC5 | A change that lowers Marathi question accuracy beyond tolerance but raises English | CI runs | The job fails and names Marathi | R5 |
| AC6 | A completed run | The report is read | Cost and duration are present | R6 |
| AC7 | The datasets | The personal-data scan runs | No phone numbers, emails or private names are found | R7 |

## 5. Interfaces and data contracts

```
app/evals/
  extraction/<id>/{document.pdf → archive hash, expected.jsonl}
  questions.jsonl     {id, language, route, question, location?, expected: {values, fact_ids, not_known}}
  refusals.jsonl      {id, language, question, expected_behaviour}
  baseline.json       scores of the last release
hishob eval run [--set extraction|questions|refusals] [--against staging] --report out/
```

## 6. Non-functional requirements

- The question set at M1 size runs in under 15 minutes.
- Integration runs use a capped budget per run.

## 7. Constitution

| Article | How this spec upholds it |
|---|---|
| C3 | Citation pass rate is a scored metric |
| C7 | R7: scan datasets for personal data |
| C10 | R3, R5: by-language reporting and blocking |
| C11 | R4, R5: the promotion gate |

## 8. Out of scope

Growing the sets to full size (M2). Model-graded scoring of free text beyond key values (later, if needed).

## 9. Design notes

- Key-value scoring reuses the citation checker's normalisers, so "₹4.2 crore" and "४.२ कोटी" compare equal.
- Write questions from real residents' phrasing gathered in persona interviews where possible.

## 10. Tasks

| Id | Task | Size | Depends on | Verifies |
|---|---|---|---|---|
| T1 | Dataset formats and validator | S | | AC1 |
| T2 | Ten labelled documents | L | SPEC-001 | AC1 |
| T3 | Thirty questions, ten refusals, three languages | L | SPEC-006 | AC1 |
| T4 | Scorers with stub tests | M | SPEC-007/T4 | AC2 |
| T5 | Report with baseline comparison, cost and duration | M | T4 | AC3, AC6 |
| T6 | CI job, path triggers, approval override | M | T5 | AC4, AC5 |
| T7 | Personal-data scan | S | T1 | AC7 |
