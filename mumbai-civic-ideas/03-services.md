# Services: what the money is supposed to buy

Ideas 23 to 28. Idea 5, Ward Lens, is in [../mumbai-civic-graph/05-ward-lens.md](../mumbai-civic-graph/05-ward-lens.md).

Service ideas are the most valuable to residents and the hardest to build, because the data sits inside hospitals, schools and depots and is rarely published. Each one needs a partner inside or close to the service. None is a hackathon-day build.

---

## 23. Hospital Watch

**Problem.** The city runs major hospitals and a network of smaller ones, with a large health budget. Patients meet long queues, unfilled posts, and scanners that are out of order for months.

**What residents get.** Per hospital: the budget, sanctioned and filled posts by category, beds, and the status of major equipment, with procurement and repair tenders linked. A notice when a machine a patient needs is reported out of service, and where the nearest working one is.

**Data.** Budget documents and equipment tenders are public. Vacancies and equipment status need RTI, questions raised in the corporation, or a partner such as a patients' group or resident doctors' association.

**How.** `Asset` of type hospital with `Equipment`, `Post` and `Indicator` nodes. The promise tracker covers announced beds and machines. Reports from patients and staff are citizen-tier evidence.

**First version.** Months. A narrow start is possible: track only announced new beds and machines against tenders, from public documents.

**Watch out.** No patient data, ever. Reports about staff must be about posts and vacancies, not individuals.

---

## 24. School Delivery Tracker

**Problem.** The city supplies its school pupils with uniforms, books, bags and devices. Deliveries have often arrived months into the school year.

**What residents get.** Per item and per year: when the tender was issued, when it was awarded, the promised delivery date, and when parents and teachers say the items actually arrived.

**Data.** Tenders and awards are public. Delivery dates need parents, teachers or school management committees to report.

**How.** Each item is a `Work` with milestones. A simple report from a parent ("received", "not yet") attaches to the school. The audit desk compares tender dates across years to show whether the process starts early enough to deliver by the first day of term.

**First version.** Weeks for the tender timeline; a school term for delivery reports.

**Watch out.** Work with a parents' or teachers' network. Reports should name the school, never the child.

---

## 25. Water Ledger

**Problem.** Supply hours vary sharply across the city, leaks run for days, and contamination complaints recur in the same lanes.

**What residents get.** Per locality: announced supply cuts, leak and contamination reports with time to repair, and the water works tendered for the area. A history that shows whether a lane's problem is new or chronic.

**Data.** Cut announcements and tenders are public. Leak, pressure and contamination records are internal; start with residents' reports.

**How.** Pipelines and reservoirs as `Asset`, complaints attached by location, works linked. Chronic clusters are found by counting in code.

**First version.** Months.

**Watch out.** Contamination reports are health claims. Label them as reported, encourage testing, and route them to the responsible office quickly.

---

## 26. Waste Contract Watch

**Problem.** Collection, transport and dump-site clearing are large recurring contracts, typically paid by weight or trips. Residents see only whether their bin was emptied.

**What residents get.** Per ward: who holds the collection contract, its value and terms, and residents' record of missed collections. For dump-site clearing: the contracted quantity, the reported progress and the deadline.

**Data.** Contracts via tenders and committee approvals. Weighbridge and trip data are internal.

**How.** `Contract` nodes with payment basis; `Complaint` nodes for missed collections; `Milestone` for clearing targets.

**First version.** Months. The contract map alone is quicker and already informative.

**Watch out.** Without weighbridge data, do not imply payments are wrong; show what is contracted and what residents report.

---

## 27. BEST Fleet Meter

**Problem.** Bus numbers are announced regularly: new electric buses, leased buses, fleet targets. Commuters experience longer waits. The city also pays a substantial subsidy to the undertaking each year.

**What residents get.** A timeline of every fleet announcement with its date and target, against the fleet size reported at later dates, and the annual subsidy from the civic budget.

**Data.** Budget documents, the undertaking's own statements and tenders, and news reports. BEST also tenders on Mahatenders.

**How.** The promise tracker's mechanism, with fleet size as a dated `Indicator`.

**First version.** Days.

**Watch out.** Distinguish owned from leased buses and buses on the books from buses in service, as the sources do.

---

## 28. Stalled Rehab Tracker

**Problem.** Families moved out for redevelopment are promised a new home and rent in the meantime. Projects stall for years and rent stops. This affects a very large number of households.

**What residents get.** For a project: the developer, the approvals and dates on record, the stated completion date, and reports from residents on rent arrears. A drafted complaint to the right authority.

**Data.** The slum rehabilitation and housing authorities publish some project information. Rent arrears come from residents.

**How.** A further `Agency` in the ontology; `Project`, `Developer`, `Approval` nodes; resident reports as evidence.

**First version.** Months.

**Watch out.** This sits outside the civic budget and largely outside BMC, so it stretches the challenge. It is also contested and often in court. Work with a housing rights group, publish only records and residents' own statements, and take legal advice.
