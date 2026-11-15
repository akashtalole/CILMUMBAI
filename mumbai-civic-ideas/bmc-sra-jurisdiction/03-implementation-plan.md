# Implementation plan

## 1. Phases

| Phase | Work | Done when |
|---|---|---|
| 0. Read the texts | Obtain Regulation 33(11), 33(10) and 33(20)(B), the directions of 15 October 2024 and 2 November 2026, and, by RTI if needed, the two authorities' letters | A lawyer on the team has read them and written a one-page note on what each actually says |
| 1. Scheme Register | Collect SRA's published 33(11) letters of intent and matching RERA project pages for one ward; extract schemes, plots, developers and approvals | 20 to 30 schemes loaded, each fact quoted from its source |
| 2. Plot status | Attach slum declarations and survey references as status claims | Every plot in the register has at least one claim or an explicit "no claim found" |
| 3. Tenement Ledger | Extract tenements owed from letters of intent; handovers from SRA publications and RTI | Owed and handed-over counts reconcile, in total, with SRA's published figures for the schemes covered |
| 4. Jurisdiction rules and cards | Encode rules from the directions; lawyer review; card generator | A card for every scheme, each with its basis |
| 5. Regulation desk | Advocates, rule drafter, lead; first dual-reading brief | Brief passes its rubric and a lawyer's review |
| 6. Resident's front door | `which_authority` tool on the citizen desk; subscriptions for changes | A resident's question about a real scheme is answered correctly, as checked by someone who knows the scheme |
| 7. Concession Meter and Handoff Tracker | RTI applications to both authorities for premium and sign-off records; ingest replies | First replies loaded; gaps listed for the rest |
| 8. Ward Load Sheet | Sum approved floor space by ward and authority; add open space and service figures | One ward complete |

Phases 1 to 4 need only published documents. Phases 7 and 8 depend on records the authorities hold.

## 2. Hackathon slice

Aim for one ward and three things that work end to end.

| Build | Shows |
|---|---|
| Scheme Register for 20 to 30 schemes, on a map | "Here are the schemes behind the headline, in this ward" |
| Tenement Ledger for those schemes | "This many transit homes are owed here; this many have been handed over" |
| Jurisdiction card for each, plus one dual-reading brief | "Here is who is directed to handle each, on what basis, and what each side says" |

Leave premiums, sign-offs and ward load as named gaps with drafted RTI applications. Showing the gap and the application that would fill it is part of the demo.

### Before the event

| Task | Output |
|---|---|
| Open the SRA publications page for 33(11) letters of intent and record what it actually contains | Source note |
| Look up five of those schemes on the RERA public search and note which fields are shown | Field list |
| Obtain the regulation text and both directions | Documents in the archive |
| Ask a lawyer to join the team | A name |
| Pick the ward | One with several 33(11) schemes |

### On the day

| Hours | Work |
|---|---|
| 0 to 1 | Agree the demo. Lawyer reads the texts and writes the one-page note. |
| 1 to 3 | Intake of letters of intent and RERA pages for the ward. First ten schemes on a map. |
| 3 to 5 | Tenement counts. Jurisdiction rules encoded and reviewed. Cards generated. |
| 5 to 6 | Regulation desk produces the brief. Lawyer edits it. |
| 6 to 7 | Citizen desk answers three prepared questions in Marathi and English. Rehearse. |
| 7 to 8 | Pitch. Backup recording. |

## 3. Team

| Role | Why essential |
|---|---|
| Lawyer with development control experience | Reads the regulation and directions correctly; approves rules and the brief |
| Planner or architect who files proposals | Knows what a letter of intent contains and how approvals sequence |
| Data and graph engineer | Register, rules engine, queries |
| AI engineer | Intake and Regulation desk agents, rubrics |
| Front end | Map, card, ledger |
| Housing rights or residents' group contact | Ground truth on handovers and transit rent |

Without the lawyer, build only the Scheme Register and Tenement Ledger and leave the jurisdiction card out.

## 4. Demo script

1. Show the headline. "Two authorities, one regulation, about 300 schemes in question. Which ones? Where?"
2. Open the map of one ward. Each scheme is a pin. Tap one: plots, status claims, regulation, approvals, each with its document.
3. Show its jurisdiction card: directed to SRA under the state's directions, contested by BMC, with both dates.
4. Open the Tenement Ledger for the ward: owed, handed over, outstanding, by scheme. "These are the transit homes the argument is supposed to be about."
5. Open the dual-reading brief: both readings, same length, each with the words it relies on, then what the data shows.
6. Ask the citizen desk, in Marathi: "Our building's redevelopment file is with which office, and whom do we ask about transit rent?"
7. Show the gaps list and one drafted RTI application for premium records.
8. Close: "We have not decided who is right. We have built the record that lets the state decide on evidence, and lets residents stop waiting in the dark."

## 5. Adoption

The natural owner is the state Urban Development Department, which both authorities answer to and which has now written twice on the same question.

| Audience | What they gain |
|---|---|
| UDD | One view of every scheme, both authorities' actions on it, and delivery against the regulation's purpose. Evidence for any future direction. |
| SRA | A public record of transit tenements delivered, which is its case for the regulation |
| BMC | Visibility of what has been approved in each ward by another authority, and of premiums due to it |
| Displaced families and their representatives | Which schemes owe homes, and when |
| Residents in redevelopment | Where their file is and who to approach |
| Developers | A predictable statement of which authority and which sign-offs apply |

Offer it first as a joint pilot for one ward, with both authorities invited to correct their own records before anything is public. A register both have checked is worth more than one that either can dismiss.

## 6. Measures of success

- Share of the reported 522 schemes in the register with at least a letter of intent on file.
- Share of tenement obligations with a known handover status.
- Number of jurisdiction cards whose basis a lawyer has confirmed.
- Median days a BMC sign-off has been pending, once that data exists.
- Residents' questions answered with a source, and how many were corrected afterwards.
- Whether either authority, or the department, asks for access.

## 7. Risks

| Risk | Mitigation |
|---|---|
| The texts say something different from the press reports | Phase 0 comes first; nothing in the rules is taken from news |
| Published SRA data is too thin to build the register | Fall back to RERA project pages, which name the planning authority and approvals; state coverage honestly |
| Survey numbers do not match across sources | Keep each source's identifier and link them as claims; a planner reviews doubtful matches |
| The state issues a new direction or a court rules mid-build | The rules are data; add the document, review, and every card updates. This is the design working as intended. |
| The project is used by one side against the other | Equal treatment in the brief; right of correction for both; publish the method |
| Legal exposure from naming developers | Stages and dates only; Challenger and lawyer review; no characterisation |
| Scope: this is partly outside the civic budget | The link to the challenge is direct: premium revenue is public money, and transit homes are a public promise. Keep those two at the centre. |

## 8. What this plan has not established

- The exact wording of Regulation 33(11), 33(20)(B) and the two directions.
- Whether "generated" in SRA's tenement figures means sanctioned, under construction or built.
- What SRA's publications page and the RERA search actually expose, and in what form.
- Whether BMC publishes approval and sign-off status in a usable way.

Each of these is a task in "Before the event". The design holds whichever way they turn out, but the hackathon slice should be cut to fit what the data spike finds.
