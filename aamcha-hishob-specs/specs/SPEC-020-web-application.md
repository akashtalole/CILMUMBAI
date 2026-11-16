# SPEC-020: Web application, resident view (demo slice)

| | |
|---|---|
| Status | In progress: all acceptance criteria pass for the resident view; the ward pages and alerts sign-up are later slices |
| Milestone | M1 (demo slice), M2 (the rest) |
| Owner role | Full-stack engineer |
| Depends on | SPEC-004, SPEC-006, SPEC-007, SPEC-008 |
| ADRs | 0015, 0016, 0014 |
| Personas served | Sunita, Imran, Lata, Ramesh (residents); Farah and Kavita in part |

## 1. Problem and outcome

Everything built so far is reached through a command line or the API. A resident needs a page on a phone that answers three questions in their language: who must fix this, where did the money go, and what should I ask.

When this slice is done, a resident can find their road by name in either script or by location; see who is responsible, whether a contractor must still repair it at its own cost, and where to complain next; follow the money from tender to payment; and ask the citizen desk a question and get a sourced answer with a letter to send. Every fact on the page opens to the document line it came from.

## 2. User stories

- As Sunita, I want to stand on my road, press one button and learn who must fix the pothole, in Marathi.
- As Imran, I want to see what was paid for my road and to whom, with the documents behind it.
- As Lata, I want a complaint letter I can forward on WhatsApp.
- As Kavita, I want to see which records are missing and who holds them, so I can file an RTI.

## 3. Requirements

| Id | Requirement |
|---|---|
| R1 | A resident shall find a road or ward by name, in Latin or Devanagari script, or from the device's location. |
| R2 | For a chosen place and issue, the page shall show any contractor still liable with the end date, the post to complain to, the escalation chain, and the owner, department and ward, each with its source. |
| R3 | The page shall show the money trail for a road, with amounts in rupees in the Indian format with lakh or crore, dates in the chosen language, works past due marked, and each missing record with the office that holds it. |
| R4 | The interface shall be available in Marathi, Hindi and English, open in Marathi unless the device prefers Hindi or English, and remember the choice. |
| R5 | A resident shall be able to ask the citizen desk a question; the answer shall come back with its sources (each passage once) and any draft letter, which can be copied, shared on WhatsApp or downloaded. The desk shall read through the API under the resident's own tier. |
| R6 | Because each question costs money, asking shall be off unless the server has Claude credentials, limited per client per hour, and limited in how many run at once; the desk's own tool calls and polling for an answer shall not use up the resident's per-minute limit. |
| R7 | A map shall show the chosen road or ward, and shall still show it if the basemap cannot be reached. |
| R8 | The API shall serve the built page from the same origin; the page shall work on a phone with no sideways scrolling. |
| R9 | No text in an answer shall be able to inject markup into the page. |

## 4. Acceptance criteria

| Id | Given | When | Then | Verifies |
|---|---|---|---|---|
| AC1 | The demo seed | A resident presses "Near me" at S. V. Road, or types "एस. व्ही" | S. V. Road is chosen, or offered | R1 |
| AC2 | S. V. Road and "Pothole" | The tab loads | The contractor and 31 May 2031, the Assistant Engineer (Roads), K/West, and the Executive Engineer are shown; a source opens to its quote | R2 |
| AC3 | S. V. Road | The money tab loads | ₹4,20,00,000 (₹4.2 crore) is shown, and the missing budget head with the BMC Chief Accountant (Finance) | R3 |
| AC4 | A browser set to Marathi | The page opens, English is chosen and the page reloads | It opens in Marathi; after reload it is in English; Hindi labels appear when Hindi is chosen | R4 |
| AC5 | A scripted desk behind the real API | A contributor asks with a location | The job finishes with the answer body, its sources, and the desk called with the contributor's token and location | R5 |
| AC6 | No credentials; a limit of 2 an hour; a per-minute limit lower than the desk's tool calls | Questions are asked | 503 without credentials; the third question in an hour is refused; the desk's calls succeed while an outside caller is still limited | R6 |
| AC7 | A ward with a boundary | Its shape is requested; the page shows the road | GeoJSON comes back (404 for an unknown place); the map draws the road | R7 |
| AC8 | A build in the web directory; a phone viewport | `/` and an API route are requested; the page is measured | The page and the API both answer; the page is no wider than the screen | R8 |
| AC9 | An answer containing a script tag, bold text, bullets and a repeated source | It is shown | Bold and bullets render, no script element exists, the repeated source appears once | R9, R5 |

AC1 to AC4 and AC7 to AC9 are checked in a browser by `app/web/e2e/resident.mjs` at phone and desktop sizes; AC5 to AC8 by `app/tests/integration/test_spec020_resident_api.py`.

## 5. Interfaces and data contracts

```
GET  /places/{node_id}/shape   GeoJSON Feature: a ward's boundary (simplified) or every segment of a road's name
POST /ask                      {question, language?, lat?, lon?} -> 202 {id, status}; 503 off; 429 limited
GET  /ask/{id}                 {id, status: running|done|failed, elapsed_s, answer?: {body, text, sources, draft_letter, gaps, status, language}}
GET  /                         the built web app (app/web/dist, or HISHOB_WEB_DIR)
```

Settings: `HISHOB_ASK_ENABLED` (default on when Claude credentials are present), `HISHOB_ASK_PER_HOUR` (10), `HISHOB_WEB_DIR`. Build-time: `VITE_DATA_NOTICE` (a banner, used for demo data), `VITE_MAP_STYLE`.

## 6. Non-functional requirements

- Usable on a mid-range phone on a slow connection: the page shell is static, and the map is the only large download.
- Text in three scripts with Noto fonts where installed.
- Keyboard and screen-reader usable: real buttons, radio groups for issues, live regions for results.

## 7. Constitution

| Article | How this slice upholds it |
|---|---|
| C3 | Every fact shown has a source chip that opens to the quote, page and document |
| C5 | Records, not verdicts: the footer says so, and gaps are shown as records not held |
| C7 | The question text is not logged; the desk redacts names and numbers before the model reads it |
| C8 | The desk reads under the resident's own tier |

## 8. Out of scope

Ward pages, alerts sign-up (SPEC-010), sign-in (SPEC-013, Cognito), pre-rendered pages and own PMTiles (ADR 0015), photo upload, conversation follow-ups with the desk (each question is one session), and the views for officials, reporters and reviewers (SPEC-021 and later).

## 9. Design notes

- Vite, React and TypeScript, built to static files. In the demo profile the API serves them; in production they move to S3 and CloudFront (ADR 0015).
- Basemap: OpenFreeMap (OpenStreetMap data, no key) until our own PMTiles exist. If it cannot load within six seconds, the map switches to a plain background and still draws the place.
- Asking is a job, because an answer takes 20 to 90 seconds. Jobs live in the API process's memory for an hour, which fits one process (the demo profile); behind several API tasks they move to Postgres.
- The desk's tool calls go back into the same app in-process (Starlette's test client), with the resident's token and a per-process key that exempts them from the per-minute limit. This avoids a network hop and a second credential; it is a demo-profile choice to revisit for production.
- The desk writes light Markdown. The page renders paragraphs, bullets and bold as React elements, never as HTML.
- `app/demo/seed.py` loads the synthetic S. V. Road scenario on the fixture shapes into an empty database, for trying the page. Its documents say on every page that they are invented, and the page shows a banner.

## 10. Tasks

| Id | Task | Size | Depends on | Verifies | State |
|---|---|---|---|---|---|
| T1 | Shape endpoint | S | SPEC-004 | AC7 | Done |
| T2 | Ask endpoint as a job, with limits | M | SPEC-008 | AC5, AC6 | Done |
| T3 | Page shell, three languages, place search, near me | M | | AC1, AC4, AC8 | Done |
| T4 | Who is responsible and money trail views with sources | M | T3 | AC2, AC3 | Done |
| T5 | Ask view with letter sharing and safe rendering | M | T2, T3 | AC5, AC9 | Done |
| T6 | Map with fallback | S | T1 | AC7 | Done |
| T7 | Demo seed and browser test | S | | AC1 to AC9 | Done |

## Change log

| Date | Change |
|---|---|
| 16 Nov 2026 | Resident view built: `app/web/` (React), API additions in `app/src/hishob/api/{app,ask}.py` and `place/geo.py`, demo seed `app/demo/seed.py`, tests `app/tests/integration/test_spec020_resident_api.py` and `app/web/e2e/resident.mjs`. One live question in Marathi through the page: answered correctly from the records in 20 seconds. |

### Found while building

- **MapLibre's `isStyleLoaded()` is false while basemap tiles download**, so a shape that arrived then was never drawn. Readiness is now taken from the style's own load event.
- **Polling counted against the resident's per-minute limit**, which could lock someone out mid-answer. Polling by job id is exempt.
- **The desk replies in Markdown**, which showed as raw `**` and `-`; it is now rendered safely.
- **Several facts cite one line**, so the same passage was listed four times; sources are now shown once each.
- **The test suite and the demo share one Neo4j** on a development machine; running the tests empties the demo graph. Rebuild it with `hishob graph rebuild` against the demo database.

### Not done yet

- The Marathi and Hindi interface text needs the language reviewer.
- Missing-record text from the API (gaps) is in English only.
- The demo road is the fixture's invented straight line, so it does not sit exactly on S. V. Road in the basemap.
- The page is about 970 kB of JavaScript, almost all of it the map library; loading the map on demand would halve the first load.
