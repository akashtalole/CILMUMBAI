# User personas

Who Aamcha Hishob serves, what each of them is trying to get done, and which parts of the platform do it for them.

These personas are composites drawn from the challenge brief and the kinds of people it invites. They are not research. Before building, test each one with two or three real people who fit it, and rewrite what does not hold.

## 1. Summary

| # | Persona | Group | Main question | Channel | Tier |
|---|---|---|---|---|---|
| 1 | Sunita, resident of a chawl | Residents | "Who will fix this, and how do I make them?" | WhatsApp voice note, Marathi | Public |
| 2 | Imran, salaried commuter | Residents | "When will this road work end?" | Web on phone, alerts | Contributor |
| 3 | Lata, housing society secretary | Residents | "What is planned for our lane, and is our building on any list?" | Web, WhatsApp | Contributor |
| 4 | Ramesh, family awaiting a transit home | Residents | "When do we get our home, and who is holding it up?" | WhatsApp, community worker | Public |
| 5 | Farah, residents' association volunteer | Organisers | "What do we ask at the ward meeting, with proof?" | Web, printed briefs | Contributor |
| 6 | Kavita, RTI activist | Organisers | "Which record is missing, and how do I get it?" | Web | Contributor |
| 7 | Arjun, civic reporter at a Marathi daily | Watchdogs | "What is the story this week, and can I stand behind it?" | Weekly feed, web | Researcher |
| 8 | Dr Meera, urban policy researcher | Watchdogs | "Can I query the whole thing and cite it?" | API, bulk downloads | Researcher |
| 9 | Corporator Pawar | Representatives | "What is happening in my ward that I should raise?" | Web, ward brief | Official |
| 10 | Assistant Engineer, ward office | Officials | "Which defects can the contractor be made to fix, and which complaints are mine?" | Web work list | Official |
| 11 | Deputy Secretary, state Urban Development Department | Officials | "What do both authorities' records actually show?" | Briefs, register | Official |
| 12 | Advocate Nair, the platform's reviewing lawyer | Platform team | "Is this safe and fair to publish?" | Review screen | Reviewer |

Two further groups use the platform without being its audience: **contractors and developers**, who appear in the records and need a way to correct them and reply; and **other builders**, who use the public API. Both are covered in section 4.

## 2. Personas

### 2.1 Sunita, 46, resident of a chawl in a dense ward

**Situation.** Lives with her family in one room. Reads Marathi slowly, does not use English. Uses WhatsApp daily, mostly by voice. Her lane's drain overflows every monsoon and the open manhole near the tap has been reported twice.

**Jobs to be done.**
- Find out who is responsible for the drain and the manhole.
- Send a complaint that is not ignored, and know when to push again.

**Pains today.** Complaints are closed without the work being done. She is sent between offices. She does not know the names of departments or posts.

**What she needs from the platform.**
- Send a voice note and a photo; get a short spoken or written reply in Marathi.
- Be asked where it is if the location is missing, and have the place read back to her.
- A complaint she can forward or have printed, addressed to the right office.
- A reminder when the complaint's time limit passes, with the next step.

**Features.** Voice line (idea 37), Jawabdar (idea 2), Complaint Closure Audit (idea 31), citizen desk.

**Design notes.** No sign-in. Short replies. No jargon or abbreviations. Never ask her for more than one thing at a time. Faces and number plates removed from her photos; her phone number never stored with her report.

**Success looks like.** The manhole is covered, and she knows which office to call next time.

### 2.2 Imran, 31, salaried commuter

**Situation.** Rents a flat in the western suburbs. Comfortable with apps in English and Hindi. His road has been dug up for months.

**Jobs to be done.**
- Know what is being built on his route, by whom, and by when.
- Know when a deadline has passed.

**Features.** Work Coming to Your Street (idea 14), Site Board QR (idea 15), Paisa Trail (idea 1), Pothole Ledger (idea 18).

**Design notes.** Save a route or an area once; alerts arrive without asking. Every alert shows the tender number and a link to the source.

**Success looks like.** He can say, with the tender in hand, that the work is three months late, and to whom.

### 2.3 Lata, 58, secretary of a cooperative housing society

**Situation.** Handles the society's dealings with the ward office. The building is old. Redevelopment is being discussed.

**Jobs to be done.**
- Know whether the building is on the dangerous-buildings list, and what that requires.
- Know what is planned for the lane and the nearby reserved plot.
- If redevelopment proceeds, know which authority has the file and at what stage.

**Features.** Safety List (idea 19), Reserved Plots Tracker (idea 22), Ek Plot Ek Record (idea 41), ward budget summary (idea 7).

**Design notes.** Pages she can print for a society meeting. Plain statements of what is official and what is not. Clear "this is not legal advice" wording on anything about approvals.

**Success looks like.** The society's meeting decides with the same facts in front of everyone.

### 2.4 Ramesh, 52, head of a family displaced by a road project

**Situation.** Moved out for a project, promised a permanent transit home. Rent was paid for a while, then stopped. Does not know which scheme his home is supposed to come from.

**Jobs to be done.**
- Know which schemes owe transit homes near him, and how many have been handed over.
- Know whom to approach, and with what.

**Features.** Tenement Ledger and resident's front door in Ek Plot Ek Record (idea 41), Stalled Rehab Tracker (idea 28), drafted letters.

**Design notes.** Reached most often through a community worker or housing rights group, so the platform must work well when someone else is operating it for him. Records are counts per scheme; the platform never holds allotment lists or names.

**Success looks like.** He knows the scheme, its due date and the office, and his group can raise it with numbers.

### 2.5 Farah, 39, residents' association volunteer

**Situation.** Organises a residents' group in her ward. Attends ward committee meetings. Writes letters on behalf of neighbours.

**Jobs to be done.**
- Arrive at a meeting with a few questions that cannot be brushed aside.
- Track what was promised for the ward, and whether it started.
- Collect neighbours' reports into evidence.

**Features.** Ward brief and meeting questions (audit desk), Vachan Tracker (idea 3), Unspent Money Watch (idea 6), Committee Digest (idea 29), Complaint Closure Audit (idea 31).

**Design notes.** One-page outputs, each fact with its source in brackets. A way to share a page as an image on WhatsApp groups.

**Success looks like.** A question she asks gets a dated answer in the minutes.

### 2.6 Kavita, 44, RTI activist

**Situation.** Files dozens of right-to-information requests a year. Holds boxes of replies. Spends much of her time drafting and appealing.

**Jobs to be done.**
- Ask for exactly the record that fills a gap.
- Track the thirty-day clock and file appeals on time.
- Make replies useful beyond one person.

**Features.** RTI Commons (idea 30), the gaps list from the audit desk, RTI loop workflow (W5), intake of replies.

**Design notes.** Applications drafted to ask for named records by period; appeal drafts ready on day thirty-one. Her name and address removed from any reply she shares.

**Success looks like.** Her replies close gaps in the graph and are reused by others.

### 2.7 Arjun, 29, civic reporter at a Marathi daily

**Situation.** Covers the corporation alone. Short of time. Cannot run a story on a hunch.

**Jobs to be done.**
- Find the week's story in the committee agenda, tender awards and audit reports.
- Check a claim fast, with the document behind it.

**Features.** Newsroom Feed (idea 38), Committee Digest (idea 29), Audit Para Tracker (idea 32), Mega Project Meter (idea 11), contractor record (idea 4, researcher tier).

**Design notes.** Every item carries its documents and the Challenger's counter-argument, so the other side's response is anticipated. The same feed goes to every outlet on the same terms. Clear marking of official record versus residents' report.

**Success looks like.** A published story that cites the platform and survives the corporation's reply.

### 2.8 Dr Meera, 41, urban policy researcher

**Situation.** Studies municipal finance and planning. Comfortable with data tools.

**Jobs to be done.**
- Query across years, wards and departments.
- Cite data with its provenance in published work.

**Features.** Public Data Service and API (idea 40), bulk exports in JSON lines, Parquet and Turtle, analyst desk, metric definitions.

**Design notes.** Stable identifiers, documented ontology, release versions she can cite, and a statement of coverage and gaps with each release.

**Success looks like.** Her paper's numbers can be reproduced from a named release.

### 2.9 Corporator Pawar, elected representative

**Situation.** Represents an electoral ward. Hears residents' complaints daily. Has a discretionary fund.

**Jobs to be done.**
- Know what is late or stuck in the ward before residents tell him.
- Raise questions in committee with evidence.
- Show residents what his fund paid for.

**Features.** Ward brief, Corporator Fund Tracker (idea 8), Corporator Report Card (idea 34), Ward Participatory Budget (idea 36).

**Design notes.** Identical measures for every corporator, regardless of party. A route to publish his own fund records. A right to correct his record.

**Success looks like.** He uses the brief in committee, and volunteers his fund data.

### 2.10 Assistant Engineer (Roads), ward office

**Situation.** Responsible for roads in one ward. Many complaints, some about roads that are not the corporation's. Contractors on recently built roads owe repairs under their defect liability periods.

**Jobs to be done.**
- See which complaints are genuinely his and which belong to another agency.
- See which defects are on roads still under contractor liability, grouped by contractor.
- Correct the record where it is wrong.

**Features.** Liability watch (audit desk), Pothole Ledger (idea 18), complaint routing in Jawabdar (idea 2), correction workflow (W6).

**Design notes.** Addressed by post, never by name. A work list, not a scorecard. A correction button that is answered.

**Success looks like.** Repairs done at the contractor's cost that would otherwise have been paid from the ward's budget. This persona is the platform's best route to adoption.

### 2.11 Deputy Secretary, state Urban Development Department

**Situation.** Fields letters from both BMC and SRA on the same regulation. Needs to decide on evidence, not on correspondence.

**Jobs to be done.**
- See every scheme in question, both authorities' actions on it, and delivery against the regulation's purpose.
- Read both positions set out fairly, with the texts each relies on.

**Features.** Ek Plot Ek Record (idea 41): Scheme Register, Tenement Ledger, Concession Meter, dual-reading brief.

**Design notes.** Neutral language, equal treatment, every claim sourced. Both authorities invited to correct their own records before anything is public.

**Success looks like.** The next direction cites figures from the register.

### 2.12 Advocate Nair, reviewing lawyer for the platform

**Situation.** Volunteers part of her week. Signs off anything that names a party.

**Jobs to be done.**
- Review findings, rules and briefs quickly, with the evidence and the challenge alongside.
- Hold anything unsafe or unfair.

**Features.** Review screen at the release and rule-approval steps of the LangGraph workflows; Challenger reviews; correction and right-of-reply workflow.

**Design notes.** Each item shows the claim, the evidence table, the Challenger's review and the banned-word check. One-click hold with a reason that goes back to the audit desk.

**Success looks like.** Nothing published needs to be withdrawn.

## 3. Mapping personas to the platform

### 3.1 Features by persona

| Feature | Sunita | Imran | Lata | Ramesh | Farah | Kavita | Arjun | Meera | Corporator | Engineer | UDD | Lawyer |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Who is responsible (Jawabdar) | ● | ● | ○ | | ● | | | | ○ | ● | | |
| Street alerts | | ● | ● | | ○ | | | | ○ | | | |
| Money trail (Paisa Trail) | | ● | ○ | | ● | ● | ● | ● | ● | ○ | | |
| Promise tracker | | ○ | | | ● | | ● | ● | ● | | | |
| Ward brief and meeting questions | | | ○ | | ● | | ● | | ● | ● | | ● |
| Complaint closure and pothole ledger | ● | ● | ○ | | ● | | ○ | | ○ | ● | | |
| Liability watch | | | | | ○ | | ○ | | ○ | ● | | ● |
| Safety list | ○ | | ● | | ● | | ● | | ○ | ○ | | |
| Ek Plot Ek Record | | | ● | ● | ○ | ○ | ● | ● | ○ | | ● | ● |
| RTI Commons and gaps | | | | ○ | ● | ● | ○ | ○ | | | | |
| Committee digest and audit paras | | | | | ● | ● | ● | ● | ● | | ○ | |
| Contractor record | | | | | | ○ | ● | ● | | | | ● |
| API and bulk data | | | | | | | ○ | ● | | | ○ | |
| Review and correction | | | | | | | | | ○ | ● | ○ | ● |

● primary use · ○ occasional use

### 3.2 Channels and access

| Channel | Personas | Notes |
|---|---|---|
| WhatsApp text and voice notes | Sunita, Ramesh, Lata, Farah | Marathi and Hindi first; voice transcribed and the place read back |
| Mobile web | Imran, Lata, Farah, Kavita, Arjun, Corporator | Phone-first; pages work on slow connections |
| Printed and shareable pages | Lata, Farah, Corporator | One page, sources in brackets, shareable as an image |
| Weekly feed | Arjun, Farah, Corporator | Same terms for every outlet |
| API, MCP tools and downloads | Meera, other builders | Public tier only in bulk |
| Work list and review screen | Engineer, UDD, Lawyer | Approved accounts only |

| Access tier ([03-semantic-and-search-layer.md](03-semantic-and-search-layer.md)) | Personas |
|---|---|
| Public | Sunita, Ramesh, and anyone without an account |
| Contributor | Imran, Lata, Farah, Kavita |
| Researcher | Arjun, Meera |
| Official | Corporator, Engineer, UDD |
| Reviewer | Lawyer and the editorial board |

### 3.3 Personas by agent desk and workflow

| Desk or workflow | Serves |
|---|---|
| Citizen desk; resident request workflow (W3) | Sunita, Imran, Lata, Ramesh |
| Audit desk; ingest and audit workflow (W1) | Farah, Arjun, Corporator, Engineer |
| Regulation desk; legal change workflow (W4) | UDD, Lata, Ramesh |
| RTI loop (W5) | Kavita, Farah, Ramesh's group |
| Correction and right of reply (W6) | Engineer, Corporator, contractors, developers |
| Analyst desk | Arjun, Meera |
| Steward desk (W7) | Every persona, indirectly: it keeps the data true |
| Release and promotion gates (W1, W8) | Lawyer |

### 3.4 Language and literacy

| Need | Personas | Platform response |
|---|---|---|
| Marathi, spoken | Sunita, Ramesh | Voice notes in, text replies now; spoken Marathi replies once a voice is tested |
| Marathi or Hindi, written | Lata, Farah, Arjun, Corporator | Every page and reply in the reader's language; glossary for official terms |
| English | Imran, Meera, UDD | Same content, same sources |
| Assisted use | Ramesh, often Sunita | Works when a community worker operates it; drafts are easy to read aloud |

## 4. People who appear in the records

| Group | Need | How the platform meets it |
|---|---|---|
| Contractors and developers | Accuracy; a right to respond | Records shown as stages and dates, not verdicts; correction requests answered; replies published beside the record |
| Officials | Not to be singled out personally | Named by post only; work lists rather than rankings |
| Elected representatives | Equal treatment | Identical measures for all; right to correct |
| BMC, SRA and other agencies | Fair representation | Invited to correct their own records before release; positions set out in their own words |

## 5. Anti-personas

The platform is deliberately not built for these uses.

| Use | Why not, and what happens instead |
|---|---|
| Someone seeking to target an individual official or resident | No private individuals in the data; officials by post; harassment-shaped requests declined |
| A campaign wanting one-sided material against a party or authority | Same rules and measures for all; counter-arguments shown with every finding |
| Someone wanting legal advice on their own case | Plain statement that the platform summarises published records; pointed to the right office or to legal aid |
| Someone wanting an official certificate or record | The platform is not an official record; pointed to the issuing office |

## 6. Priorities for the first slice

For the hackathon day and the first 30 days, design for three personas first and let the others follow:

1. **Sunita**, because if it works for her by voice in Marathi it works for nearly everyone.
2. **Farah**, because she turns the platform's output into action in a room where decisions are made.
3. **The Assistant Engineer**, because an officer who gains from it is how the city adopts it.

**Arjun** is the fourth: one published story reaches more residents than any feature.

## 7. Validating the personas

| Step | How |
|---|---|
| Interview | Two or three people per persona before the 30-day mark; ask what they did the last time they had this problem |
| Test the first slice | Watch Sunita-type and Farah-type users complete one task each, in their language, without help |
| Measure | Task completed, time taken, whether the answer was correct, whether they would use it again |
| Update | Rewrite this file from what is learned; record what changed and why |
