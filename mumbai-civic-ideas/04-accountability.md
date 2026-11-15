# Accountability: making the system answer

Ideas 29 to 36. Idea 3, Vachan Tracker, and idea 4, Thekedar Graph, are in [../mumbai-civic-graph/](../mumbai-civic-graph/).

---

## 29. Committee Digest

**Problem.** Most spending decisions are approved in committee meetings, chiefly the Standing Committee. Agendas are long, formal and partly in Marathi. Few people outside read them.

**What residents get.** A weekly digest: each proposal approved, the amount, the contractor, the ward, and anything unusual such as a cost revision or an award to a sole bidder. Filterable by ward. Sent to subscribers and reporters.

**Data.** Committee agendas and resolutions. Availability online varies; confirm how to obtain them each week.

**How.** The intake desk reads each agenda item into `Award` and `Contract` facts, linking to tenders already in the graph. The drafter writes the digest. This is also the missing source of award data for the money trail.

**First version.** Days, for one meeting's agenda.

**Watch out.** A proposal on the agenda is not yet approved. Record the stage precisely.

---

## 30. RTI Commons

**Problem.** Thousands of right-to-information requests are filed about the same things. Each reply reaches one person and is lost. Many applications are rejected for being vague, and few people file a first appeal.

**What residents get.** A searchable library of RTI replies others have received. A drafting helper that asks for specific records in the form offices cannot easily refuse. A tracker for the thirty-day reply period, with a first appeal drafted automatically when it lapses.

**Data.** Replies contributed by residents and activists. No agency's permission is needed.

**How.** Each reply is a `SourceDocument` read by the intake desk, with personal details of the applicant removed. Facts from replies enter the graph at official tier. The gaps file from the audit desk supplies ready questions.

**First version.** Days. Seed it with replies that local activists already hold.

**Watch out.** Remove applicants' names and addresses before publishing. Check replies for third-party personal data.

---

## 31. Complaint Closure Audit

**Problem.** A complaint is marked resolved while the problem remains. The city's figures then show a high resolution rate.

**What residents get.** After a complaint is closed, a prompt: is it fixed? If not, a photo reopens it with evidence and adds it to a public count per ward and department of closures that residents dispute.

**Data.** Residents' own complaint numbers and photos. Official complaint data would improve it but is not required.

**How.** `Complaint` nodes with the official status and the resident's status side by side. The disputed share is computed per ward office and department.

**First version.** Days.

**Watch out.** Photos need location and time to count. Guard against one person filing many disputes by weighting per reporter.

---

## 32. Audit Para Tracker

**Problem.** The city's own auditor and the national auditor write reports listing specific irregularities. The national auditor's special audit of BMC works was tabled in 2023. After the headlines, nobody records what happened to each finding.

**What residents get.** Each audit observation as a card: what the auditor found, the amount involved, the department, the reply on record, and its status: answered, action taken, or silent. Counted by department.

**Data.** Published audit reports and any action-taken replies. RTI for the rest.

**How.** `(AuditObservation)-[:ABOUT]->(Work|Contract|Department)`, linked to works in the graph where they can be matched. Each silent observation generates a drafted RTI and a question for the relevant committee.

**First version.** Days, for one report.

**Watch out.** An audit observation is the auditor's view, sometimes contested by the department. Quote it as such.

---

## 33. Court Order Compliance

**Problem.** The High Court has repeatedly directed the city on potholes, open manholes, footpaths, hoardings and air quality. Compliance is reviewed only when the case next comes up.

**What residents get.** Each direction as a plain statement with its date and deadline, the city's stated compliance, and residents' evidence for or against. Lawyers appearing in these matters get an organised record.

**Data.** Court orders are public. Compliance affidavits are filed in court and are harder to obtain.

**How.** `(Direction)-[:FROM]->(Order)` with deadline and responsible agency, linked to assets and works. The promise tracker's status rules apply.

**First version.** Weeks. Needs a lawyer to select and read the orders correctly.

**Watch out.** Do not comment on pending matters beyond what the orders say. Have a lawyer review every summary.

---

## 34. Corporator Report Card

**Problem.** Residents vote for a corporator and then have little way to see what they did: attendance, questions raised, proposals moved, funds used.

**What residents get.** A page per corporator from official records, updated as meetings happen, comparable across wards.

**Data.** Meeting proceedings and attendance records, likely by RTI or from civil society groups that already compile annual report cards. Fund use from idea 8.

**How.** `Person`, `Post`, `Meeting`, `Question` nodes. Counting only; no scores invented.

**First version.** Weeks.

**Watch out.** Apply identical measures to every corporator and publish the method. Offer each a right to correct their record.

---

## 35. Affidavit Explorer

**Problem.** Candidates file sworn declarations of assets, liabilities and pending cases at election time. They are public but scattered as scanned forms.

**What residents get.** Each representative's own declarations, searchable and comparable between elections.

**Data.** Election affidavits published by the election authorities; civil society groups already digitise many.

**How.** Extracted as `Declaration` facts attached to `Person`, each quoted from the affidavit.

**First version.** Days, for the corporators of one ward.

**Watch out.** Present declarations exactly as sworn, with no inference. Linking a representative to a contractor is a different, sensitive exercise that belongs under the review rules of the contractor graph and needs legal sign-off.

---

## 36. Ward Participatory Budget

**Problem.** Residents are consulted, if at all, after decisions are made. Small local works are chosen without them.

**What residents get.** Before the budget, residents of a ward propose small works, see rough costs from the rate card, and rank them. The ranked list goes to the corporator and ward committee. Afterwards, each chosen work is tracked to completion.

**Data.** Residents' proposals; costs from tender history.

**How.** `Proposal` nodes with support counts, linked to a `Work` if adopted. The city's existing residents' groups are natural organisers.

**First version.** Months, and only with a corporator or ward office willing to commit a share of discretionary funds.

**Watch out.** Online voting favours those already online and organised. Pair it with meetings in the ward, and verify that participants live there.
