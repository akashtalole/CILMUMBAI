# SPEC-003: Facts ledger and loader

| | |
|---|---|
| Status | Draft |
| Milestone | M0 |
| Owner role | Graph engineer |
| Depends on | SPEC-001, SPEC-002 |
| ADRs | 0001, 0004 |
| Personas served | Reviewers; all, indirectly |

## 1. Problem and outcome

Agents produce facts; nothing they produce may reach the graph unchecked. The starter loader checks quotes and writes straight to the graph, with no durable record of what was accepted.

When done, every batch of extracted facts passes schema validation and a quote check in code. Accepted facts are appended to an immutable ledger on S3; rejected ones go to a held file with a reason. Projections (SPEC-006) are built only from the ledger.

## 2. User stories

- As a reviewer, I want every held fact with its reason, so that I can fix or discard it.
- As a graph engineer, I want to rebuild the graph from the ledger, so that I can change engines or recover.
- As a researcher, I want to know which extractor version produced a fact, so that I can judge it.

## 3. Requirements

| Id | Requirement |
|---|---|
| R1 | The loader shall validate each record against the generated JSON Schema and the whitelist (SPEC-002). |
| R2 | For each record whose source page has a text layer, the loader shall confirm the quote occurs in the page text after normalising whitespace and Unicode (NFC). |
| R3 | Where the source page has no text layer, the loader shall accept the record with `quote_check = scan_unchecked`. |
| R4 | When a record fails validation or the quote check, the loader shall write it to the batch's held file with a machine-readable reason. |
| R5 | The loader shall append accepted records to the ledger as a new file and shall never modify an existing ledger file. |
| R6 | Each ledger record shall carry: fact id, kind, label or type, ids, properties, source sha256, page, quote, tier, confidence, `quote_check`, extractor id and version, ontology version, batch id, loaded time. |
| R7 | When a new record has the same identity as an existing fact but different properties, the loader shall append it with `supersedes` set to the earlier fact id. |
| R8 | If a batch references an edge endpoint that exists neither in the batch nor in the ledger, then the loader shall hold that edge with reason `dangling_endpoint`. |
| R9 | The loader shall produce a batch report with counts accepted, held by reason, and superseded. |

## 4. Acceptance criteria

| Id | Given | When | Then | Verifies |
|---|---|---|---|---|
| AC1 | A record with a label not in the whitelist | It is loaded | It is held with reason `unknown_label` | R1, R4 |
| AC2 | A record whose quote appears on its page with different line breaks | It is loaded | It is accepted with `quote_check = matched` | R2 |
| AC3 | A record whose quote does not appear on its page | It is loaded | It is held with reason `quote_not_found` | R2, R4 |
| AC4 | A record citing a page with no text layer | It is loaded | It is accepted with `quote_check = scan_unchecked` | R3 |
| AC5 | An existing ledger | A second batch is loaded | Earlier ledger files are byte-identical to before | R5 |
| AC6 | An accepted record | It is written | All R6 fields are present | R6 |
| AC7 | A fact already in the ledger | A record with the same id and a changed amount is loaded | It is appended with `supersedes` pointing to the earlier fact | R7 |
| AC8 | An edge to a node id not present anywhere | It is loaded | It is held with reason `dangling_endpoint` | R8 |
| AC9 | A batch of 100 records with 5 bad quotes and 2 unknown labels | It is loaded | The report shows 93 accepted, 5 `quote_not_found`, 2 `unknown_label` | R9 |

## 5. Interfaces and data contracts

```
hishob load <facts.jsonl> --batch <id> --extractor <agent_id>@<version>

s3://…/facts/<graph>/<yyyy-mm-dd>/<batch>.jsonl      accepted, append-only
s3://…/staging/<batch>/held.jsonl                     {record, reason, detail}
s3://…/staging/<batch>/report.json                    counts
```

Held reasons: `schema_invalid`, `unknown_label`, `unknown_edge`, `domain_range`, `quote_not_found`, `page_out_of_range`, `dangling_endpoint`, `unknown_ontology_major`.

## 6. Non-functional requirements

- Loads 10,000 records in under a minute locally.
- Deterministic: the same input produces the same ledger content apart from timestamps and batch id.

## 7. Constitution

| Article | How this spec upholds it |
|---|---|
| C1 | R1, R6: provenance required and recorded |
| C2 | R2, R3: quote check, scan mark |
| C4 | The loader, not an agent, writes the ledger |
| C9 | R5: append-only; projections built from ledger |

## 8. Out of scope

Writing to the graph and indexes (SPEC-006). Review screen for held facts (SPEC-021). Fuzzy quote matching.

## 9. Design notes

- Reuse and harden `load()` and `quote_on_page()` from `civic_client.py`; read page text from SPEC-001 rather than reopening PDFs.
- Normalise quotes and page text the same way: NFC, collapse whitespace, unify Devanagari nukta forms. Do not lowercase or strip punctuation: amounts and identifiers must match exactly.
- Fact id: hash of kind, label or type, node ids and source sha256 and page.

## 10. Tasks

| Id | Task | Size | Depends on | Verifies |
|---|---|---|---|---|
| T1 | Ledger writer and record model | M | SPEC-002/T4 | AC5, AC6 |
| T2 | Schema and whitelist validation | S | T1 | AC1 |
| T3 | Quote normaliser and check, with Marathi test fixtures | M | SPEC-001/T8 | AC2, AC3, AC4 |
| T4 | Supersession | S | T1 | AC7 |
| T5 | Dangling endpoint check against batch and ledger index | M | T1 | AC8 |
| T6 | Batch report and command line | S | T2, T3 | AC9 |

## 11. Open questions

| Question | Owner | Assumption until answered |
|---|---|---|
| Should a near-match quote (one character off) be held or flagged | Product lead | Held |
| Devanagari that a PDF draws with full shaping can extract as garbled text (seen while building SPEC-001's fixtures). How common is this in real BMC PDFs, and should such pages be treated like scans? | AI engineer | Measure on twenty real Marathi PDFs in M0; until then, a page whose text has Devanagari letters mixed with stray Latin-1 characters is treated as `scan_unchecked` |
