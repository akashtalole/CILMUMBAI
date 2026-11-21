# SPEC-030: Photo report

| | |
|---|---|
| Status | In progress: all acceptance criteria pass with a scripted vision model; the plumbing is checked live, accuracy on real photos is not |
| Milestone | M2 |
| Owner role | AI engineer |
| Depends on | SPEC-007, SPEC-008, SPEC-020 |
| ADRs | 0003, 0011, 0018 |
| Personas served | Sunita, Imran, Lata, Ramesh |

## 1. Problem and outcome

A resident who sees a pothole does not know its name in the records, nor who owns the road. Typing a road name is the hard part; pointing a camera is easy (idea 2, Jawabdar).

When this is done, a resident photographs the problem on their phone and gets back what the photo shows, who is responsible for that road and who to complain to, whether a contractor must still repair it at its own cost, and a letter to send, each fact with its source.

## 2. User stories

- As Sunita, I want to take a photo of the pothole outside my building and be told who must fix it, in Marathi.
- As Lata, I want the letter written for me, ready to forward on WhatsApp.

## 3. Requirements

| Id | Requirement |
|---|---|
| R1 | The system shall accept a JPEG, PNG or WebP photo of up to 10 MB, refuse anything else with a reason, and reduce it to an upright JPEG of at most 1,568 pixels on its longest side with no metadata. |
| R2 | The system shall take the place from the device's position; failing that, from the photo's own GPS tag; and with neither, shall ask for it without calling the vision model. |
| R3 | A vision model shall name the problem from a fixed list (pothole, open manhole, waterlogging, incomplete work); anything outside the list, any malformed reply and any low confidence shall mean "unclear". |
| R4 | The citizen desk shall be asked a fixed question built in code from the problem and the resident's language, with the place, so that nothing written in the photo can steer the answer. |
| R5 | The photo and its metadata shall be held in memory for the request only, never stored or logged, and the place shall be logged by length only. |
| R6 | Photo reports shall be off unless the server has Claude credentials, limited per client per hour and in how many run at once, and a photo's upload size shall be capped while it is read. |
| R7 | The web page shall let a resident take or choose a photo, shrink it before it leaves the phone, show what was found, the sourced answer and the letter, and say plainly when the photo is unclear. |

## 4. Acceptance criteria

| Id | Given | When | Then | Verifies |
|---|---|---|---|---|
| AC1 | A 4000 by 3000 JPEG tilted by its orientation tag, with a GPS tag; PNG and WebP; and a GIF, text, an over-size file and an over-pixelled image | Each is read | The first becomes upright, at most 1,568 px, with no metadata left, and its place is read; PNG and WebP are accepted; the others are refused with a reason | R1 |
| AC2 | A photo with no place from the device or its tag | A report is made | The result is "no_location" and the vision model was never called | R2 |
| AC3 | A photo with a GPS tag, and a device position | A report is made with and without the device position | The device position wins; without it the tag is used; south and west read as negative and a tag of 0, 0 or one off the Earth is ignored | R2 |
| AC4 | A scripted model | It answers pothole, none, low confidence, a malformed reply, an issue off the list or text that tries to instruct | Only a valid issue with enough confidence reaches the desk, with the fixed question in the resident's language and the place; everything else is "unclear" and the desk is not asked | R3, R4 |
| AC5 | The API with scripted model and desk | A photo is posted and the job polled; then a non-image, a text file as an image, 10 MB and a byte over, a bad language, a position off the Earth, no credentials, and three photos from one client against a limit of two | The job returns the finding and a sourced answer; the bad uploads are refused with 415, 422, 413 and 422 before any model call; 503 without credentials; the third is 429 and polling is never limited | R1, R4, R6 |
| AC6 | A completed report | The request log and the job's result are read | The position appears in the log only by length, and neither the log nor the result holds any image content or the coordinates | R5 |
| AC7 | A browser at phone and desktop size, with the API mocked | A photo is chosen | The photo goes up as an image with the language and the device position, the finding, the sourced answer and the shareable letter are shown, and an unclear result says so | R7 |

AC1 to AC4 are `app/tests/unit/test_spec030_photo.py`; AC5 and AC6 `app/tests/integration/test_spec030_report_api.py`; AC7 `app/web/e2e/resident.mjs`.

## 5. Interfaces and data contracts

```
POST /report?language=mr|hi|en[&lat=…&lon=…]   body: the image, Content-Type image/*  -> 202 {id, status}
GET  /report/{id}   {status, elapsed_s, answer?: {status: answered|unclear|no_location, issue, confidence, location_from, answer?}}
```

Errors: 415 not an image type; 413 over 10 MB; 422 unreadable or unsupported photo, bad language or position; 429 limit; 503 off. Settings: `HISHOB_PHOTO_ENABLED` (default on with credentials), `HISHOB_PHOTO_PER_HOUR` (5).

## 6. Non-functional requirements

- A report ends in under a minute: one vision call of a few seconds, then one desk session.
- The page shrinks a photo on the phone before upload, which also drops its metadata.

## 7. Constitution

| Article | How this spec upholds it |
|---|---|
| C3 | The answer is the citizen desk's, checked in code against its cited facts |
| C5 | The model names a problem from a list and nothing else; it is told never to describe people or plates |
| C7 | Photos are not stored or logged, the place is logged by length only, and the page says the photo is sent for reading and not kept |
| C8 | The desk reads under the resident's own tier |

## 8. Out of scope

Storing photos as evidence, a gallery of reports, blurring faces and number plates for storage (nothing is stored), a resident's own correction of the issue and re-ask, reading a work-site board or a hoarding, and video.

## 9. Design notes

- The photo reaches the model as base64 inside one messages call to a vision model; it is the only place it leaves the server. The resident is told this on the page.
- The question put to the desk is a table in code, not text from the model, so a sign or a sticker in the photo cannot become an instruction.
- A job holds only its result in memory for an hour. The photo is not part of the result.

## 10. Tasks

| Id | Task | Size | Depends on | Verifies | State |
|---|---|---|---|---|---|
| T1 | Photo reading: formats, size, pixels, orientation, GPS, metadata | S | | AC1, AC3 | Done |
| T2 | Vision classification with fail-safe parsing | S | | AC4 | Done |
| T3 | Report orchestration and the fixed questions in three languages | M | SPEC-008 | AC2, AC3, AC4 | Done |
| T4 | Job endpoints, limits and logging | M | SPEC-020 | AC5, AC6 | Done |
| T5 | Web photo card | M | T4 | AC7 | Done |

## Change log

| Date | Change |
|---|---|
| 20 Nov 2026 | Implemented in `app/src/hishob/agentkit/photo.py`, `app/src/hishob/api/app.py` and `app/web/src/components/PhotoReport.tsx`. Adds the Pillow dependency. |

### Checked live

The vision call, the job endpoints and the location lookup ran against the demo server and the real model. A drawn stand-in image came back "unclear" (3.2 s, no desk session spent), which is the safe result. With the vision verdict scripted as "pothole" and the real desk behind it, the place near S. V. Road gave the road, ward K/W, the contractor under defect liability and the posts to complain to, with 13 sources and a letter, in Marathi and in English.

**Not checked:** how accurately the vision model names problems in real photos. No real photograph was available (the one public source tried rate-limited this environment). Before relying on it, run it on a set of real photos from several streets and add them, with the issue each shows, to the evaluation sets (SPEC-012).

### Found while building

- **Names ran across line breaks.** The desk's review took the end of a letter's address block and the next paragraph's first word as one name ("Western Suburbs", blank line, "Subject"), so English letters were rejected and replaced by the safe fallback: two of three English runs fell back. A name now runs along one line only.
- **A leading article became part of a name.** "To, The Executive Engineer" was checked as the name "The Executive Engineer", which no fact holds. A leading "The", "A", "An", "To" or "Dear" is dropped first. Four of four English runs now answered. Regression tests in `test_citations.py`.

### Not done yet

- Accuracy on real photos (above), and the Marathi and Hindi question wording needs the language reviewer.
- The page asks for the device's position only; a photo's own tag is used for API callers, since the page's shrinking drops it.
- A resident cannot correct what the model saw and ask again; "unclear" points to the other tab.
