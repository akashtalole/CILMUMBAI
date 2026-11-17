# SPEC-012: Evaluation harness and promotion gate

| | |
|---|---|
| Status | In progress: all acceptance criteria pass with a stub system; a first live run is recorded and its scores are the baseline; awaiting review |
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
  extraction/<id>/{document.pdf, expected.jsonl, meta.json}   10 invented documents; expected: {label, match, props}
  questions.jsonl     {id, language, route, question, expected: {values: [{kind: amount|date|text, value}], cited: [node ids], not_known?}}
  refusals.jsonl      {id, language, route, question, expected_behaviour, must_not: [regex], must_any: [regex]}
  baseline.json       {tolerance, scores}: the last release
  approvals.jsonl     {key, approved_score, reason, approver}: an owner's waiver of one regression
  make_extraction_set.py   regenerates the ten documents

hishob eval validate                       check the sets and scan them for personal data
hishob eval run [--set …] --against <api>  run against the real desks; writes report.json and report.md
hishob eval gate --report out/report.json  compare with the baseline; exit 1 on an unapproved regression
hishob eval baseline --report …            record a report as the baseline of the release
```

Differences from the draft: the question set names expected **node ids**, not fact ids, because fact ids are hashes of the source document and change with it; the harness resolves the facts a reply cites to their nodes. Refusals are scored with per-item regular expressions (`must_not`, `must_any`), not by a model.

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

| Id | Task | Size | Depends on | Verifies | State |
|---|---|---|---|---|---|
| T1 | Dataset formats and validator | S | | AC1 | Done |
| T2 | Ten labelled documents | L | SPEC-001 | AC1 | Done (invented, three scripts); real documents to replace them as the corpus grows |
| T3 | Thirty questions, ten refusals, three languages | L | SPEC-006 | AC1 | Done, on the demo world; the Marathi and Hindi wording needs the language reviewer |
| T4 | Scorers with stub tests | M | SPEC-007/T4 | AC2 | Done |
| T5 | Report with baseline comparison, cost and duration | M | T4 | AC3, AC6 | Done |
| T6 | CI job, path triggers, approval override | M | T5 | AC4, AC5 | Done in `.github/workflows/evals.yml`; not yet run on GitHub (needs staging secrets) |
| T7 | Personal-data scan | S | T1 | AC7 | Done |

## Change log

| Date | Change |
|---|---|
| 17 Nov 2026 | Implemented in `app/src/hishob/evals/` (`datasets`, `scoring`, `report`, `run`, `live`, `pii`), `app/evals/`, `hishob eval`, and `.github/workflows/evals.yml`. Tests in `app/tests/unit/test_spec012_evals.py`. |

### Decisions made while building

- **The gate judges whole items.** Each score is the mean of 0 or 1 per item, and the report records how many items stand behind it. A drop of one item is tolerated as noise (it flipped between two live runs), two items is a regression; the configured tolerance (0.05) is a floor for groups larger than twenty. Without this, a group of nine questions fails on a single flaky answer.
- **The gate looks at overall and at each language**, as R5 says; routes are reported and compared but do not block.
- **An approval waives one score only.** It names the key (`questions.values.mr`) and the score it approves, with an approver and a reason. A further drop, a blank reason or a different key is still blocking.
- **Fail closed.** If a pull request changes agents, the ontology, the citation rules or the sets, and the repository has no staging secrets, the evaluation job fails with the missing names rather than passing unmeasured.
- **Key values reuse the citation checker's parsers**, so ₹4.2 crore, ४.२ कोटी and 4.2 करोड़ are one figure, and dates match across English, Marathi and Hindi.
- **The "not known" question** passes if the reply asserts no amount or date. Questions pass if every expected value is in the reply; free-text values match case-insensitively.
- **Extraction** is scored per document on field accuracy (expected properties found with the right value), record recall, and the quote-match rate (records whose quote is on the page, scans excluded). It runs through the intake desk into a dedicated evaluation database.
- **Questions go through the real desk** with the query API behind it, and each reply is also put through the API's citation check. A reply the desk replaced with its code-built fallback makes no claims, so `citation` does not apply to it; a `reviewed` metric records that the model's own reply failed review twice. For a "not known" question the fallback is the right reply and is not counted against.
- **Naming and firm prefixes.** Extraction finds an entity by its label and name, accepting `name` or `title` (the ontology allows both on a Work) and ignoring a leading "M/s". Which property carries a value, such as a due date, is still checked strictly.
- **The report keeps every item's metrics and a reply excerpt**, so a paid run can be audited and re-aggregated (`hishob eval gate` rebuilds scores from the items) without repeating it.

## First live run (17 November 2026)

Against the demo world (`demo/seed.py`) through the query API, with the intake desk for extraction. Cost $6.39 (extraction $3.69, 30 questions $2.09, 10 refusals $0.61), 276 s for the questions and refusals at four in parallel. These scores are recorded as `evals/baseline.json`.

| Set | Metric | Overall | Marathi | Hindi | English |
|---|---|---|---|---|---|
| Extraction (10 documents) | field accuracy | 0.97 | 1.00 | 1.00 | 0.96 |
| | record recall | 1.00 | 1.00 | 1.00 | 1.00 |
| | quote match | 1.00 | 1.00 | 1.00 | 1.00 |
| Questions (30) | key values | 0.89 | 0.89 | 0.89 | 0.89 |
| | cited the expected facts | 0.96 | 1.00 | 1.00 | 0.88 |
| | citation check passed | 1.00 | 1.00 | 1.00 | 1.00 |
| | model's reply passed review | 0.93 | 1.00 | 1.00 | 0.78 |
| | correct "not known" | 1.00 | 1.00 | 1.00 | 1.00 |
| Refusals (10) | appropriate decline | 1.00 | 1.00 | 1.00 | 1.00 |

What the run showed about the system, as measured and not as a verdict:

- **The desk withholds who holds a missing record.** Asked "which budget head paid for this work, and who holds that record?", it says the records do not show the budget head, and leaves out the office that holds it, because that office comes from the platform's missing-record list and has no source document to cite. All three languages miss the expected "Chief Accountant". Whether such a derived gap may be stated, labelled as not from a document, is a product decision.
- **One English answer flipped between runs** (the award value fell back to the safe reply in one run, passed in another): the model's replies vary, which is why the gate tolerates one item.
- **Extraction put a due date on the Contract** instead of the Work in one document ("completion due on 31 March 2027"). Everything else, including Marathi and Hindi documents with Devanagari digits, was right, and every quote was on its page.
- **Refusals** were declined or redirected in all three languages. Replies to prompts that did not name a road or contractor asked "which one?" instead.

### Calibration before the baseline

The first live run scored lower than the system deserved, for reasons in the instrument. These were found by reading the replies, fixed, and tested before any baseline was recorded; the system under test was not changed:

- Refusal checks flagged a correct decline that repeated the word ("I can't say whether this contractor is corrupt") and one that repeated the question's own phrase. The forbidden patterns now look for agreement and for giving an opinion.
- The Marathi and Hindi refusal prompts said "the contractor" and "this road" without naming them, so asking "which one?" was reasonable. They now name S. V. Road and the contractor, as the English ones did.
- Extraction expectations required `title`, but the ontology allows `name` on a Work, and required "M/s" in a firm's name.
- A fallback reply on a "not known" question was counted as a citation failure.

### Found while building

- **The personal-data scan found a real bug in the citizen desk's redaction.** The Hindi honorific `कु.` matched the start of **कुछ** (anything), turning "कुछ न करें" into "कु[name]" in a resident's question, and `सौ` (Mrs) matched the number **hundred**: "सौ रुपये" became "सौ [name]". Both abbreviations now need their full stop, a Devanagari honorific cannot continue a word, and a name's second word cannot be a conjunction (आणि, और). Regression test in `test_spec008_parts.py`.

- **Reading a session's files stopped at the first page.** The API lists 20 files a page, and a ten-document intake writes 37, so the first live run could not find its own outputs ($3.69 of work that finished, then could not be read). The intake and audit desks now read every page, keep the newest file per name, and retry a download of a file that is listed before it is readable. The extraction was then recovered from the finished session rather than paid for again. (A unit test written first mocked a method the SDK does not have and passed; it now mirrors the real page object.)
- **A rate-limited source lookup crashed a resident's answer** with a KeyError, because the desk assumed the API answered. It now leaves out that source line. A failed question no longer aborts an evaluation run either.

### Not done yet

- **Real documents and real residents' questions.** The sets are invented and sit on one scenario, so they test the machinery and the languages, not the breadth of Mumbai's documents. Each question and refusal wording should be reviewed by a native speaker.
- **Refusals are checked by keyword**, a proxy: a reply can contain a cue and still be poor. Model-graded scoring is out of scope for M1.
- **The staging agents** are applied by each CI run to the staging Claude account (the lock is cached between runs); old versions are not cleaned up.
- **Questions run against the demo world**, so staging must hold the demo seed (`app/demo/seed.py`) for the question set to have its verified answers.
