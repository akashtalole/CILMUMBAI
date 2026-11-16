# Milestones

Dates assume the event on 21 November 2026. Durations after the event are estimates and depend most on how quickly data can be obtained.

## M0: Foundations (16 to 20 November)

**Goal.** A corpus for one ward is archived, read by agents, checked in code and held as a facts ledger.

| Specs | 001, 002, 003, 004, 005 |
|---|---|
| Runs on | A laptop: Docker Compose with Neo4j, Postgres and MinIO; Claude API with event credits |
| Data | One ward: fifty tenders with notices, roads budget pages for five years, ward and road geometry, the ward office's posts |

**Exit criteria**

- Every document in the corpus is in the archive with hash and metadata.
- One intake run produces a facts file; the loader accepts or holds every record with a stated reason.
- At least 90% of extracted fields correct on ten hand-labelled documents.
- The ledger can be replayed into an empty graph and produces the same node and edge counts.

**Demo.** Drop a new tender PDF in; watch it archived, read, checked and appear as facts with their quotes.

## M1: Hackathon slice (21 November)

**Goal.** Residents and judges can use three things on one ward, with correct, cited answers.

| Specs | 006, 007, 008, 009, 010, 011, 012 (minimum parts) |
|---|---|
| Runs on | The same laptop; a tunnel or a small host for judges' phones if allowed |

**Exit criteria**

- A judge picks a road in the ward and gets its works, contractor, cost and responsible post, each with a source.
- A question in Marathi and one in English are answered with citations that pass the citation check.
- One audit run produces a ward brief and one case file with its challenge review, paused for release.
- A street alert fires for a new tender in a saved area.
- The question evaluation set (thirty questions at this stage) passes at the agreed threshold.

**Demo.** The script in [../mumbai-civic-graph/06-prep-and-day-plan.md](../mumbai-civic-graph/06-prep-and-day-plan.md), using only these features.

**Cut line.** If time runs short, drop SPEC-010 before SPEC-011, and SPEC-011 before SPEC-008. Never drop the citation check.

## M2: First service (to about 20 December)

**Goal.** A public, cloud-hosted service for all wards' procurement and five years of budgets, kept current.

| Specs | 013 to 023 |
|---|---|

**Exit criteria**

- Lean profile running on AWS in Mumbai, rebuilt from S3 at least once.
- All wards' tenders since January 2024 loaded; source freshness monitored.
- Hybrid search live; evaluation sets at full starting size (50 documents, 150 questions, 40 refusals), reported by language.
- WhatsApp text and voice notes in Marathi and Hindi working end to end with redaction.
- Review screen in use; corrections handled within a published time.
- Ontology and one ward's data published under an open licence.

## M3: Pilot (to about February 2027)

**Goal.** A 90-day pilot with one ward office, and the redevelopment register for one ward.

| Specs | 024 to 031 |
|---|---|

**Exit criteria**

- Ward office uses the liability watch weekly; repairs at contractor cost recorded.
- Promise tracker covers two budget speeches.
- Jurisdiction cards for one ward's schemes, rules approved by a lawyer.
- Public API and MCP server live with rate limits.
- Standard profile ready, even if not yet switched on.

## M4: Institution (to November 2027)

**Goal.** A hosted, funded, governed service with partners.

| Specs | 032 to 034, and new specs from what M2 and M3 teach |
|---|---|

**Exit criteria**

- Host organisation, editorial board and governance charter in place.
- One BMC department publishing through the open publishing kit, or a written reason why not.
- Services graph with at least one partner's data.

## Burn-down rules

- A milestone ends on its date with what is Done. Unfinished specs move to the next milestone; they are not half-released.
- Exit criteria may not be lowered to meet a date. Scope is cut instead.
