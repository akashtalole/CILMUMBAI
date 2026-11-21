# SPEC-010: Street alerts

| | |
|---|---|
| Status | In progress: all acceptance criteria pass; delivery by email is not built, alerts are read in the web app |
| Milestone | M1 |
| Owner role | Full-stack engineer |
| Depends on | SPEC-004, SPEC-006, SPEC-007 |
| ADRs | 0013, 0015 |
| Personas served | Imran, Lata, Farah |

## 1. Problem and outcome

Residents learn about a road work when the barricades arrive. This is the platform's first application and the easiest for anyone to understand (idea 14).

When done, a resident saves an area and receives a message when a tender in it is published, awarded, changed by a corrigendum, or passes its completion date, each with the tender number and source.

## 2. User stories

- As Imran, I want to know when work on my road is tendered, awarded and due.
- As Lata, I want to know about anything tendered within 300 metres of our building.

## 3. Requirements

| Id | Requirement |
|---|---|
| R1 | A contributor shall be able to save an area as a point with a radius between 100 and 1,000 metres, or as named roads. |
| R2 | When a tender, award or corrigendum fact is projected whose work is linked to an asset within a saved area, the system shall queue one alert per subscriber per event. |
| R3 | When a work's current due date passes with no completion fact, the system shall queue an overdue alert once. |
| R4 | Each alert shall state what changed, the tender number, the date and a link to the source page, in the subscriber's language. |
| R5 | The system shall not send the same alert to the same subscriber twice. |
| R6 | Where a work's location was matched from free text with confidence below a threshold, the alert shall show the tender title so the resident can judge. |

## 4. Acceptance criteria

| Id | Given | When | Then | Verifies |
|---|---|---|---|---|
| AC1 | A contributor | They save a point with radius 300 m | The subscription is stored; 50 m or 2 km are rejected | R1 |
| AC2 | A subscription around a road | A new tender for that road is projected | One alert is queued | R2 |
| AC3 | A work due yesterday with no completion fact | The daily check runs twice | One overdue alert is queued | R3, R5 |
| AC4 | An alert for a Marathi-speaking subscriber | It is rendered | It is in Marathi with tender number, date and source link | R4 |
| AC5 | The projector replays the same ledger file | Alerts are evaluated | No duplicate alerts | R5 |
| AC6 | A tender matched to a road with low confidence | An alert is rendered | It includes the tender title | R6 |

## 5. Interfaces and data contracts

`account.subscriptions(id, account_id, kind, geom, radius_m, road_ids, language, created_at)`;
`alerts.outbox(id, subscription_id, event_key UNIQUE, payload, created_at, sent_at)`.

Delivery at M1: a page listing a subscriber's alerts (the Alerts tab). Email delivery needs an email service and the account store's contact details; it is not built. WhatsApp delivery comes with SPEC-019.

```
POST   /subscriptions     {kind: point|roads, language, lat?, lon?, radius_m?, road_ids?} -> 201; 422 bad radius or unknown road; 401 not signed in
GET    /subscriptions     the caller's saved areas
DELETE /subscriptions/{id}   204; 404 if not the caller's
GET    /alerts            the caller's alerts, newest first, rendered in each area's language, with source links
hishob alerts run         queue alerts for new tenders, awards and corrigenda (also run by `hishob graph apply`)
hishob alerts overdue     the daily overdue check
```

## 6. Non-functional requirements

- Alerts queued within 15 minutes of projection.
- Subscriber contact details stored only in the account store, never in alert payloads or logs.

## 7. Constitution

| Article | How this spec upholds it |
|---|---|
| C1 | R4: every alert links its source |
| C7 | Contact details isolated |
| C10 | R4: rendered in three languages |

## 8. Out of scope

WhatsApp delivery (SPEC-019). Full web app (SPEC-020); a minimal sign-up page is enough for M1.

## 9. Design notes

- Evaluate on projector watermark changes: query new tender, award and corrigendum facts, join to assets with PostGIS within each subscription.
- `event_key` = subscription id + fact id + kind, which makes R5 a unique constraint.

## 10. Tasks

| Id | Task | Size | Depends on | Verifies | State |
|---|---|---|---|---|---|
| T1 | Subscription model and validation | S | SPEC-004/T3 | AC1 | Done |
| T2 | Event matcher on projector watermark | M | SPEC-006/T2 | AC2, AC5 | Done |
| T3 | Daily overdue check | S | T2 | AC3 | Done |
| T4 | Alert templates in three languages | M | | AC4, AC6 | Done (Marathi and Hindi wording to be reviewed) |
| T5 | Minimal sign-up page and email delivery | M | T1, T4 | | Page done (Alerts tab); email not built |

## Change log

| Date | Change |
|---|---|
| 17 Nov 2026 | Implemented in `app/src/hishob/alerts/` (`subscriptions.py`, `matcher.py`, `render.py`), migration `008_alerts.sql`, endpoints in `api/app.py`, the Alerts tab in `app/web/`, and `hishob alerts`. Tests in `app/tests/integration/test_spec010_alerts.py` and `app/web/e2e/resident.mjs`. |

### Decisions made while building

- **Matching runs on the ledger index and PostGIS, not the graph.** An event is a Tender, Award or Corrigendum node linked to a work that improves a road. A saved point matches any segment of that road's name within the radius; a road subscription matches the road by name, so the several segments of one street count as one.
- **One alert per subscriber per event, not per fact.** The key is the subscription and the event's node, so a later corrected cost on the same tender does not alert again. An overdue alert's key includes the due date, so an extended date that passes again is a new event.
- **No back-alerts.** An event counts only if its node was first loaded after the area was saved, so a new subscriber is not sent a street's history. The overdue check is the exception.
- **`hishob graph apply` queues alerts** after projecting, which keeps alerts within minutes of new facts (non-functional requirement). The output stays one JSON object, with `alerts_queued` added.
- **The saved area holds an account id and a place, nothing else.** Alert payloads hold facts only; the subscriber's language lives on the area. Rendering happens when the alert is read.
- **Until sign-in (SPEC-013), the web app asks for the signed access code** it was given, kept in the browser, or taken from a `#token=` link fragment, which is never sent to a server.

### Not done yet

- Email delivery, and contact details in the account store.
- A daily scheduler for `hishob alerts overdue` (the deployment runs it from cron or a scheduled task; not wired).
- The overdue check scans every work each day; fine for one city's works, to be indexed when it is not.
- A work's location confidence comes from the `IMPROVES` edge's confidence. Alerts for assets other than roads, and for works matched to a ward only, are not yet generated.
