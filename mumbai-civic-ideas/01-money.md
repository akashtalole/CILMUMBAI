# Money: where it is allocated and whether it is spent

Ideas 6 to 13. Idea 1, Paisa Trail, is in [../mumbai-civic-graph/01-paisa-trail.md](../mumbai-civic-graph/01-paisa-trail.md).

---

## 6. Unspent Money Watch

**Problem.** Each February the budget announces large allocations. Press reports on civic data showed more than half of the 2025-26 capital budget unspent late in that year. The gap between what is announced and what is spent is rarely visible by department or by ward.

**What residents get.** For each department and budget head: the budget estimate, the revised estimate and the actual spend, for the last five years, on one line. A plain sentence under it: "Storm water drains were given ₹X; ₹Y was spent; this has happened three years running."

**Data.** Budget books only. Each year's book prints the previous years' revised estimates and actuals beside the new estimates.

**How.** The intake desk parses budget tables into `Allocation` nodes with `amount_be`, `amount_re`, `amount_actual` per `FiscalYear`. The rest is arithmetic in code. An agent writes the plain-language line and flags heads that are under-spent every year.

**First version.** Days. One department, five years.

**Watch out.** Under-spending has innocent causes (court stays, land not handed over, monsoon). Show the number and ask the question; do not explain it without a source. Totals must reconcile with the printed department total before anything is shown.

---

## 7. Ward Budget in Plain Words

**Problem.** The budget is hundreds of pages of codes. A resident cannot tell what it means for their ward.

**What residents get.** A two-page summary per ward in Marathi, Hindi and English: the works named for the ward this year, what they cost, last year's list and what happened to it. Readable aloud at a residents' meeting. Shareable as an image.

**Data.** Budget books, ward-wise works lists where the budget prints them, and the tender graph for status.

**How.** Works are linked to wards in the graph. The drafter agent writes the summary from graph facts only; the rubric requires a source for every figure and bans jargon. A person fluent in Marathi reviews before release.

**First version.** Days, for one ward.

**Watch out.** Many budget lines are citywide and cannot honestly be split by ward. Say so and list them separately.

---

## 8. Corporator Fund Tracker

**Problem.** Each corporator has discretionary funds for small local works. Residents seldom know what their corporator chose to spend it on, or whether the benches, lights and paver blocks appeared.

**What residents get.** Per electoral ward: the fund available, each work sanctioned from it, its cost, and its location on a map. A button to confirm with a photo whether the work exists.

**Data.** Ward office sanction records. Probably not published in usable form; needs RTI to each ward office or cooperation from corporators who are willing to publish their own.

**How.** `(Work)-[:FUNDED_BY]->(Allocation {kind: 'corporator_fund'})` and `(Person)-[:SANCTIONED]->(Work)`. The RTI drafter produces one application per ward office. Replies come back as scans; the intake desk reads them.

**First version.** Weeks, because of the RTI wait. Start with two or three corporators who volunteer their lists.

**Watch out.** Starting with volunteers rewards the transparent ones; frame it that way.

---

## 9. MP and MLA Fund Tracker

**Problem.** Members of Parliament and of the state assembly also have local area development funds spent in Mumbai. Works funded this way are executed through district and civic agencies and are hard to tell apart from civic works.

**What residents get.** For each Mumbai constituency: works recommended, sanctioned and completed, with cost and location, alongside the civic works on the same map.

**Data.** The national MPLADS scheme publishes work-level data. State MLA fund data is less consistent. Confirm what is available for Mumbai's constituencies.

**How.** A second `Agency` and funding source in the same ontology. Constituency boundaries are overlaid on wards.

**First version.** Days for MPs if the published data is usable.

**Watch out.** Keep the three kinds of fund (civic, MLA, MP) visibly separate so nobody is credited or blamed for another's work.

---

## 10. Rate Card

**Problem.** Nobody outside the system knows what a kilometre of concrete road, a public toilet block or a metre of drain should cost, so nobody can tell whether a tender is unusual.

**What residents get.** A typical cost range per unit for common works, built from the city's own tenders, and a marker on any tender far outside the range, with the reasons a tender can legitimately differ.

**Data.** Tender values and quantities from Mahatenders detail pages and bill-of-quantity files; BMC's schedule of rates if obtainable.

**How.** The extractor pulls quantity and unit from each tender. Code computes cost per unit by work category and year. Outliers become case files that the Challenger reviews: wider road, utility shifting, night-only work and difficult sites all raise cost honestly.

**First version.** Weeks. Needs a few hundred tenders in one category to be meaningful.

**Watch out.** Comparing unlike works is the main risk. Publish the range and the method; treat an outlier as a question.

---

## 11. Mega Project Meter

**Problem.** A handful of projects take a large share of capital spending. Their costs and deadlines shift from one budget speech to the next and the earlier figures are forgotten.

**What residents get.** For each major project, a timeline of every stated cost and completion date, with the document each came from. One line at the top: "First announced at ₹X for completion in year A; now ₹Y for year B."

**Data.** Budget speeches across years, tender awards and news reports. All public text.

**How.** The same mechanism as the promise tracker: each statement is a dated `Promise` with `RESTATES` links, so drift is a query.

**First version.** Days, for five projects.

**Watch out.** Scope changes are real. Record them when a source states them.

---

## 12. Reserves and Borrowing Watch

**Problem.** The city has long held large deposits and now plans significant capital spending and new forms of borrowing. Whether that is sustainable is a question residents and their representatives rarely have figures for.

**What residents get.** A simple chart per year: deposits held, amount drawn for capital works, new borrowing, and committed future liabilities, each from the budget documents.

**Data.** Budget documents and the commissioner's speech.

**How.** A small set of `Indicator` observations per fiscal year. No agents needed beyond extraction.

**First version.** Days.

**Watch out.** This is finance, and easy to misread. Have someone with public finance experience review the definitions before publishing.

---

## 13. Dues Ledger

**Problem.** The city is owed large sums in property tax, water charges and other dues. Recovering them reduces the pressure on everyone else.

**What residents get.** Totals owed by category and ward, the trend, and, where the city itself has published a list of large defaulters, that list with its source.

**Data.** Budget documents for totals; the city's own published defaulter lists and press notes for names.

**How.** `Indicator` observations for totals; `Dues` nodes only for entries the city has officially published.

**First version.** Weeks.

**Watch out.** Republish only names the city has already made public, with the date, and remove them when dues are cleared. Many dues are under legal dispute; say so. Never list individual householders.
