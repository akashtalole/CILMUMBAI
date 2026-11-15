# Works: what is being built outside your door

Ideas 14 to 22. Idea 2, Jawabdar, is in [../mumbai-civic-graph/04-jawabdar.md](../mumbai-civic-graph/04-jawabdar.md).

---

## 14. Work Coming to Your Street

**Problem.** Residents learn about a road or drain work when the barricades arrive. They do not know how long it will last, who is doing it, or when to complain that it has overrun.

**What residents get.** They save their address or drop a pin. They get a message when a tender touching that area is published, when it is awarded and to whom, when the completion date passes, and when a corrigendum changes the scope or dates. Each message carries the tender number and a link to the notice.

**Data.** Mahatenders listings, corrigenda, status and award records, and BMC tender notices. Already mapped in [../mumbai-civic-graph/07-tender-portals.md](../mumbai-civic-graph/07-tender-portals.md).

**How.** The intake desk extracts road and locality names from each tender and matches them to map geometry. A subscription is a saved area. When a `Tender`, `Award` or `Corrigendum` node is added or changes within it, a message is drafted from the graph facts.

**First version.** Days, for one ward, by WhatsApp broadcast or email.

**Watch out.** Location matching from free-text tender titles will sometimes be wrong; show the title so the resident can judge. Collection must respect the portal's captcha, so freshness depends on how often someone collects.

---

## 15. Site Board QR

**Problem.** Work sites are meant to display a board with the work's name, cost, contractor and dates. Boards are often missing, faded or out of date.

**What residents get.** A QR code at the site. Scanning it shows the live record: what is being built, the cost, the contractor, the due date, the responsible engineer's post, how to report a problem, and whether the work is on time.

**Data.** The works graph. The code itself needs someone to put it up.

**How.** Each `Work` has a stable public page. Two routes to the street: residents' groups print and fix a notice themselves for works in their lane, or the ward office adds the code to official boards as a pilot.

**First version.** Weeks. The page is quick; getting codes onto sites takes people.

**Watch out.** A resident-posted notice must say clearly that it is unofficial and link to the official source.

---

## 16. Monsoon Readiness

**Problem.** Every year drains are desilted and vulnerable spots prepared before the rains, and every year parts of the city flood. Reported completion percentages are hard to check.

**What residents get.** From March to June, a countdown per drain and per known flooding spot: the work tendered, the contractor, the reported progress, and photos from residents nearby. After the first heavy rain, the same map with where water actually stood.

**Data.** Desilting tenders and awards; the city's published progress figures and lists of flooding spots; residents' photos.

**How.** Each drain stretch is an `Asset` with `Work` and `Milestone` nodes. Citizen reports attach as evidence. The audit desk runs on a date: on 1 May, which works are behind. The comparison of claimed progress with residents' evidence is a case file the Challenger reviews.

**First version.** Weeks. Timing matters: build before March to be useful that year.

**Watch out.** Flooding has causes beyond desilting, including tide and rainfall intensity. Report what was done and what happened; do not claim cause.

---

## 17. Dig Watch

**Problem.** A newly surfaced road is dug up for a cable or pipe and left patched badly. Residents cannot tell who dug, whether they had permission, or who must restore the surface.

**What residents get.** For a trench: the utility, the permission, the dates allowed, the restoration deadline and who is responsible for it.

**Data.** Trench permissions issued by the city. Not published in usable form as far as I know. Needs the roads department's cooperation or RTI.

**How.** `(Utility)-[:GRANTED]->(TrenchPermission)-[:ON]->(Asset)` with dates. Until permissions are available, residents' reports alone build a record of how often each road is dug and how long trenches stay open.

**First version.** Months for the full idea. The resident-report version is quick but answers less.

**Watch out.** Without permission data this can only say "this road was dug five times", not who was at fault.

---

## 18. Pothole Ledger

**Problem.** The same potholes return after every monsoon. Each is treated as a new complaint, so the pattern, and the contractor who built the road, never enter the picture.

**What residents get.** A history per road: every pothole reported, when it was fixed, how long the fix lasted. If the road is inside a contractor's defect liability period, a clear statement of that and a complaint that asks for repair at the contractor's cost.

**Data.** Residents' reports to start; the city's own pothole complaint data if it can be obtained; works and liability periods from the graph.

**How.** `Complaint` nodes attach to `Asset`. Repeat counts and time-to-fix are computed in code. The liability join is the same as Jawabdar's.

**First version.** Weeks. Useful once one monsoon's reports are in.

**Watch out.** Duplicate reports of the same pothole must be merged, by location and date, before counting.

---

## 19. Safety List

**Problem.** The city publishes a list of dangerously dilapidated buildings before each monsoon and has audited its bridges since the 2019 footbridge collapse. The lists exist as documents; few residents know whether their building or the bridge they cross is on one, or what was promised.

**What residents get.** A map and a search by address. For a listed building: its category, the date listed, what the notice requires. For a bridge: its last audit result, the repair or rebuild promised, the tender and the deadline.

**Data.** Published building lists and bridge audit summaries; bridge repair tenders.

**How.** `Asset` nodes of type building and bridge with `Inspection` results and linked `Work`. Year-on-year comparison shows buildings that stay on the list without action.

**First version.** Days, for the current year's list in one ward.

**Watch out.** A listing has consequences for residents' homes and can be disputed. Show the official record with its date and say how to check or contest it. Do not add anything the city has not published.

---

## 20. Hoarding Check

**Problem.** After the Ghatkopar hoarding collapse in 2024, the safety and legality of large hoardings became a public concern. A passer-by cannot tell whether a hoarding is licensed or who answers for it.

**What residents get.** Photograph a hoarding, give its location, and see whether a licence is on record, for what size, and which agency's land it stands on.

**Data.** The city's licence records, and those of other landowning agencies. Publication is uneven; likely needs RTI or cooperation.

**How.** `(Licence)-[:FOR]->(Hoarding)-[:ON_LAND_OF]->(Agency)`. Residents' photos build an inventory of what stands on the street to compare with what is licensed.

**First version.** Weeks, once any licence list is in hand.

**Watch out.** "No record found" is not "illegal"; the records may be incomplete. Word it as a question to the licensing office.

---

## 21. Toilet Audit

**Problem.** Public and community toilets matter most to those with least, especially women and slum residents. Many are built and then closed, charging more than allowed, or without water.

**What residents get.** A map of toilets with who operates each, what the city paid to build or maintain it, the approved charge, and its current state as rated by users.

**Data.** Construction and maintenance tenders; operator agreements, probably by RTI; ratings from users.

**How.** `Asset` of type toilet, linked to `Work`, `Contract` and operator. A short rating by voice note or three taps. A toilet with a maintenance contract and repeated "closed" reports becomes a case for the ward office.

**First version.** Weeks, with a community group doing the first survey of one area.

**Watch out.** Partner with an organisation already working in the area; ratings need local trust to be honest and safe to give.

---

## 22. Reserved Plots Tracker

**Problem.** The development plan reserves plots for schools, hospitals, markets and parks. Many reservations go unbuilt for decades or are quietly changed.

**What residents get.** Every reserved plot in their ward on a map: what it is reserved for, whether the land has been acquired, whether anything is budgeted or tendered, and any change to the reservation.

**Data.** Development plan maps and reservation lists; budget lines for land acquisition; change notices.

**How.** `(Reservation)-[:ON]->(Plot)` with purpose and status, linked to `Allocation` and `Work`. Changes are dated edges, so a deleted reservation leaves a visible history.

**First version.** Months. Digitising plan sheets for even one ward is real work.

**Watch out.** Land status is legally complex and often in litigation. Report the plan and the budget; avoid statements about ownership.
