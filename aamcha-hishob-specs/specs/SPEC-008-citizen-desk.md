# SPEC-008: Citizen desk

| | |
|---|---|
| Status | Draft |
| Milestone | M1 |
| Owner role | AI engineer |
| Depends on | SPEC-007 |
| ADRs | 0003, 0011 |
| Personas served | Sunita, Imran, Lata, Ramesh |

## 1. Problem and outcome

Residents ask in their own words and language. They need an answer they can act on: who is responsible, what the records show, and a letter to send. The answer must never invent a fact.

When done, one agent answers a resident's question using only the API's tools, in the resident's language, with citations that pass the check, and drafts a complaint on request. Residents' messages are redacted before the agent sees them.

## 2. User stories

- As Sunita, I want to ask in Marathi who will fix the drain in my lane and get a short answer and a letter.
- As Imran, I want to know when the work on my road is due and who is doing it.
- As Ramesh's community worker, I want to ask on his behalf and get something I can read aloud.

## 3. Requirements

| Id | Requirement |
|---|---|
| R1 | The desk shall answer only from tool results returned in the same session. |
| R2 | The desk shall reply in the language of the question: Marathi, Hindi or English. |
| R3 | If the question needs a location and none is given, then the desk shall ask for one and shall not infer it from an image. |
| R4 | Every answer shall pass the citation check (SPEC-007); if a draft fails twice, the desk shall reply that the records do not show it and give the nearest facts and how to find out. |
| R5 | The desk shall name offices and posts, and shall name a person only if they are an elected representative. |
| R6 | Where a work on the asset is within a defect liability period, the answer shall say so with the end date and source. |
| R7 | Before any text reaches the agent, the system shall remove phone numbers, email addresses, house numbers and personal names other than those of public office holders. |
| R8 | The desk shall have read-only tools only, no delegation, and read-only memory. |

## 4. Acceptance criteria

| Id | Given | When | Then | Verifies |
|---|---|---|---|---|
| AC1 | A question about a road in the graph | It is answered | Every figure in the answer appears in a tool result from the session | R1 |
| AC2 | The same question in Marathi, Hindi and English | Each is answered | Each reply is in the question's language | R2 |
| AC3 | "Who fixes the pothole outside my building?" with no place | It is answered | The desk asks for the location and states no office | R3 |
| AC4 | A question about something the graph does not hold | It is answered | The reply says the records do not show it and names a way to find out; no invented figures | R4 |
| AC5 | Any answer naming who is responsible | It is checked | It names a post and office; no official's personal name | R5 |
| AC6 | A road with a work still under liability | The resident asks about a defect | The reply states the liability end date with its source | R6 |
| AC7 | A message containing a phone number and the sender's name | It is processed | The agent's input contains neither | R7 |
| AC8 | The agent definition | CI lint runs | Only read-only custom tools; no multi-agent block; memory attached read-only | R8 |

## 5. Interfaces and data contracts

```python
def answer(question: str, *, language_hint: str | None, location: LatLon | None, tier: Tier) -> Answer: ...

@dataclass
class Answer:
    text: str
    language: Literal["mr", "hi", "en"]
    cited_fact_ids: list[str]
    check: CitationResult
    draft_letter: str | None
    gaps: list[Gap]
    session_id: str
```

Tools: `find_entity`, `locate`, `trace_money`, `who_is_responsible`, `get_source`, `gaps_for`, all answered by the worker through the API under the caller's tier.

## 6. Non-functional requirements

- Typical answer in under 30 seconds.
- Session spending cap per question set at creation.
- Routing (SPEC-017) will later send simple lookups to pages without the agent; this spec covers the agent path only.

## 7. Constitution

| Article | How this spec upholds it |
|---|---|
| C3 | R4: citation check, fallback reply |
| C4 | R8: read-only tools only |
| C5 | R5: posts, not people |
| C7 | R7: redaction before the model |
| C8 | Tools run under the caller's tier |
| C10 | AC2: tested in three languages |

## 8. Out of scope

WhatsApp and voice (SPEC-019). Filing complaints into government systems.

## 9. Design notes

- Start from `app/agents/citizen-desk.md` (moved from the starter code).
- Redaction: rules for phone, email and house numbers; names found against a list of public office holders are kept, other personal names are replaced with a placeholder. Tested on a fixture set in three languages.
- The two-attempt rule: the runner sends the unmatched items back once as a message to the session; on a second failure it returns the fallback reply built in code.

## 10. Tasks

| Id | Task | Size | Depends on | Verifies |
|---|---|---|---|---|
| T1 | Move agent file; lint rules for the desk | S | SPEC-005/T2 | AC8 |
| T2 | Tool answering through the API under tier | M | SPEC-007/T3 | AC1 |
| T3 | Citation check loop and fallback reply | M | SPEC-007/T5 | AC4 |
| T4 | Redaction with fixtures | M | | AC7 |
| T5 | Location prompt behaviour; fixture conversation | S | T2 | AC3 |
| T6 | Liability statement from `who_is_responsible` | S | T2 | AC6 |
| T7 | Language tests and post-only naming tests in the question set | M | SPEC-012/T3 | AC2, AC5 |
