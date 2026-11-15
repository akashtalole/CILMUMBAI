# Data catalogue

Every dataset the platform needs, grouped by the graph it feeds.

**Read this first.** Only the two tender portals were examined directly (see [../mumbai-civic-graph/07-tender-portals.md](../mumbai-civic-graph/07-tender-portals.md)). Everything else is listed from general knowledge of what these bodies publish. Treat "Access" as a hypothesis to test in the data spike, and expect some rows to move.

- **Access:** *Open* (published), *Partly* (published in part or in poor form), *Ask* (RTI, partner or agency cooperation).
- **Priority:** *P0* needed for the hackathon slice · *P1* within 90 days · *P2* later.

## 0. The spine: identifiers that join everything

Collect these first. Without them the graphs do not connect.

| Identifier | Identifies | Where it appears |
|---|---|---|
| Administrative ward code | Ward | Almost every civic document |
| Electoral ward number | Corporator's ward | Election records, corporator lists |
| Budget code | Budget head | Budget books; sometimes tender notices and resolutions |
| Mahatenders tender id (`2026_MCGM_…`) | Tender | Mahatenders |
| BMC bid number (ten digits) | Tender | BMC tender notices |
| Committee resolution number and date | Award, sanction | Committee agendas |
| Contractor registration number; company identification number | Contractor, company | Tender documents; company registry |
| City survey number with village | Plot | Land records, approvals, RERA |
| RERA registration number | Housing project | RERA |
| Complaint number | Complaint | BMC complaint system |
| RTI registration number | RTI request | RTI portal, replies |
| Government resolution number and date | Direction | State resolutions portal |
| Case number and court | Court order | Court websites |
| OpenStreetMap way id, plus our own asset id | Road, drain, bridge | Map |

## 1. Place (used by every graph)

| Dataset | Source | Key fields | Access | Refresh | Priority |
|---|---|---|---|---|---|
| Administrative ward boundaries | BMC; OpenCity | Code, name, geometry | Open | Rare | P0 |
| Electoral ward boundaries (227) | State Election Commission; OpenCity | Number, geometry | Partly | Per delimitation | P0 |
| Roads, with names in English and Marathi | OpenStreetMap | Way id, name, geometry, length | Open | Continuous | P0 |
| Localities, landmarks, pincodes | OpenStreetMap; India Post | Name, aliases, point | Open | Rare | P0 |
| Population, households, slum population by ward | Census 2011; later official estimates | Counts by ward | Open | Decennial | P1 |
| Assembly and parliamentary constituency boundaries | Election Commission | Geometry | Open | Rare | P2 |

## 2. Money graph

| Dataset | Source | Key fields | Access | Refresh | Priority |
|---|---|---|---|---|---|
| Budget books (all parts), last five years | BMC | Budget code, head, department, budget estimate, revised estimate, actuals | Open, as PDF | Yearly | P0 |
| Commissioner's budget speech | BMC | Announcements, headline figures | Open | Yearly | P0 |
| Ward-wise works lists in the budget | BMC | Work, ward, amount | Partly | Yearly | P0 |
| Monthly or quarterly expenditure statements | BMC accounts | Head, spend to date | Ask | Monthly | P1 |
| Revenue: property tax, development charges, grants | Budget books | Head, amount | Open | Yearly | P1 |
| Deposits, borrowing, bonds | Budget documents | Balance, drawdown, issue | Open | Yearly | P1 |
| Corporator and area development funds | Ward offices | Corporator, work, amount | Ask | Yearly | P1 |
| MP local area fund works | National MPLADS data | Constituency, work, amount, status | Open | Continuous | P2 |
| MLA fund works | District planning office | Constituency, work, amount | Ask | Yearly | P2 |
| Payments to contractors | BMC accounts | Contract, bill, amount, date | Ask | Continuous | P1 |

## 3. Procurement graph

| Dataset | Source | Key fields | Access | Refresh | Priority |
|---|---|---|---|---|---|
| Active and archived tenders | Mahatenders | Tender id, reference, title, organisation chain, value, dates, location, period of work | Open, captcha on listings | Daily | P0 |
| Tender notices and conditions | BMC portal | Bid number, department, conditions, liability clause | Open, as PDF | Daily | P0 |
| Corrigenda | Mahatenders; BMC portal | Tender, field changed, old and new value | Open | Daily | P0 |
| Tender status and award of contract | Mahatenders | Stage, bidders if shown, selected bidder, awarded value, date | Open, to confirm | Daily | P0 |
| Cancelled and retendered | Mahatenders | Tender, reason, successor | Open | Daily | P1 |
| Committee agendas and resolutions | BMC municipal secretary | Resolution number, proposal, amount, contractor | Partly | Weekly | P0 |
| Goods purchases | GeM | Bid number, item, value, seller | Open | Daily | P2 |
| Debarment list | Mahatenders | Bidder, period | Open | Ad hoc | P1 |
| Penalties and blacklisting orders | BMC press notes; news | Contractor, amount, reason, date | Partly | Ad hoc | P1 |
| Registered contractor list | BMC | Name, class, registration number | Partly | Yearly | P1 |
| Company and director records | Ministry of Corporate Affairs | Company id, directors, address | Partly, some paid | Ad hoc | P2 |
| Other agencies' tenders in Mumbai (MMRDA, MSRDC, PWD, MHADA, BEST) | Mahatenders | As above | Open | Daily | P1 |

## 4. Works and Assets graph

| Dataset | Source | Key fields | Access | Refresh | Priority |
|---|---|---|---|---|---|
| Road concretisation status | BMC dashboard | Road, contractor, status, dates | Partly | Weekly | P0 |
| Work orders and completion certificates | Departments | Work, start, due, completed | Ask | Continuous | P1 |
| Defect liability periods | Tender conditions | Clause, period | Open, inside PDFs | Per tender | P0 |
| Bridges and audit results | BMC bridges department | Bridge, audit date, result, action | Partly | Yearly | P1 |
| Dilapidated building lists | BMC, pre-monsoon | Building, ward, category | Open | Yearly | P1 |
| Drains and desilting progress | BMC storm water drains | Drain, quantity, progress | Partly | Weekly in season | P1 |
| Known flooding spots | BMC disaster management | Location, status | Partly | Yearly | P1 |
| Public and community toilets | BMC; surveys | Location, operator, seats | Partly | Ad hoc | P2 |
| Gardens, open spaces, markets | BMC | Location, area, maintainer | Partly | Rare | P2 |
| Trench permissions | BMC roads | Utility, road, dates | Ask | Continuous | P2 |
| Hoarding licences | BMC licence department | Location, size, licensee | Ask | Yearly | P2 |
| Third-party quality audit reports | BMC | Road, findings | Ask | Per work | P2 |

## 5. Organisation and Jurisdiction graph

| Dataset | Source | Key fields | Access | Refresh | Priority |
|---|---|---|---|---|---|
| Departments, posts and reporting lines | BMC proactive disclosures under the RTI Act | Department, post, reports to | Partly | Yearly | P0 |
| Ward office structure and contacts by post | Ward office pages | Post, ward, office | Partly | Ad hoc | P0 |
| Complaint categories and service time limits | Citizen charter | Issue, department, days | Open | Rare | P0 |
| Road and asset ownership by agency | Agencies' project maps; local knowledge | Asset, owning agency | Partly | Ad hoc | P0 |
| Other agencies' structures | MMRDA, MSRDC, PWD, MHADA, SRA, BEST websites | Agency, department, grievance channel | Partly | Rare | P1 |
| Transfers and postings | Orders, press | Post, holder, dates | Partly | Ad hoc | P2 |

## 6. People and Representation graph

| Dataset | Source | Key fields | Access | Refresh | Priority |
|---|---|---|---|---|---|
| Corporators by electoral ward, with party | BMC; State Election Commission | Name, ward, party | Open | Per election | P0 |
| Committee memberships | Municipal secretary | Committee, member, role | Partly | Yearly | P1 |
| Meeting proceedings, attendance, questions | Municipal secretary | Meeting, attendance, question, reply | Ask | Per meeting | P1 |
| Election affidavits | State Election Commission; civil society digitisation | Declared assets, liabilities, cases | Open | Per election | P2 |
| MLAs and MPs for Mumbai | Election Commission | Name, constituency | Open | Per election | P2 |

## 7. Land and Planning graph

| Dataset | Source | Key fields | Access | Refresh | Priority |
|---|---|---|---|---|---|
| Development Plan 2034 sheets and reservations | BMC development plan department | Plot, reservation, zone | Open, as maps | Rare | P1 |
| Development control regulations and amendments | State urban development department | Regulation, clause, date | Open | Ad hoc | P1 |
| SRA schemes and letters of intent | SRA publications | Scheme, plots, developer, tenements | Partly | Monthly | P1 |
| Housing project registrations | MahaRERA | Project, promoter, survey numbers, planning authority, approvals | Open | Continuous | P1 |
| Building approvals and sign-offs | BMC building proposal system | Proposal, stage, date | Partly | Continuous | P1 |
| Slum declarations and mapping | SRA; collector | Plot, status, date | Partly | Ad hoc | P1 |
| Transit and project-affected tenements: owed, built, handed over | SRA; BMC estates | Scheme, count, date | Ask | Quarterly | P1 |
| Premiums assessed and paid | BMC; SRA | Scheme, premium type, amount | Ask | Continuous | P2 |
| Property cards | Land records | Survey number, holder, area | Partly | Ad hoc | P2 |

## 8. Services graph

| Dataset | Source | Key fields | Access | Refresh | Priority |
|---|---|---|---|---|---|
| Ward-level service indicators | BMC annual environment status report; civil society reports | Indicator, ward, value, year | Open, as PDF | Yearly | P1 |
| Hospitals and dispensaries: beds, posts, equipment | BMC health department | Facility, sanctioned, filled, equipment status | Ask | Quarterly | P2 |
| Schools: enrolment, teachers, supplies delivery | BMC education department | School, pupils, teachers, item, date | Ask | Yearly | P2 |
| Water: supply hours, cuts, quality complaints | BMC hydraulic engineer | Zone, hours, notices | Partly | Continuous | P2 |
| Solid waste: contracts, tonnage | BMC solid waste management | Ward, contractor, quantity | Ask | Monthly | P2 |
| Bus fleet, routes and subsidy | BEST; BMC budget | Fleet by type, subsidy | Partly | Yearly | P2 |
| Rainfall by station | BMC disaster management; India Meteorological Department | Station, time, millimetres | Open | Continuous | P2 |

## 9. Voice graph

| Dataset | Source | Key fields | Access | Refresh | Priority |
|---|---|---|---|---|---|
| Residents' reports with photo, place and time | The platform's own intake | Issue, location, time, image | Own | Continuous | P0 |
| Promises: speeches, manifestos, announcements | Budget speeches; party manifestos; news | Maker, deliverable, quantity, place, deadline | Open | Continuous | P0 |
| RTI replies | Residents and activists | Request, reply, date, office | Contributed | Continuous | P1 |
| Official complaint records | BMC complaint system | Number, category, ward, opened, closed | Ask | Daily | P1 |
| News archive, English and Marathi | Publishers | Article, date, entities | Open, subject to terms | Daily | P1 |
| Residents' association minutes and letters | Associations | Issue, date, reply | Contributed | Ad hoc | P2 |

## 10. Law and Oversight graph

| Dataset | Source | Key fields | Access | Refresh | Priority |
|---|---|---|---|---|---|
| Mumbai Municipal Corporation Act and rules | State law | Section, duty, authority | Open | Rare | P1 |
| Government resolutions and directions | State resolutions portal | Number, date, department, text | Open | Daily | P1 |
| BMC circulars | Departments | Number, date, subject | Partly | Ad hoc | P1 |
| National auditor's reports on BMC | Comptroller and Auditor General | Observation, amount, department | Open | Ad hoc | P1 |
| Municipal Chief Auditor's reports | BMC | Observation, department, reply | Partly | Yearly | P1 |
| High Court orders on civic matters | Bombay High Court | Case, date, direction, deadline | Open | Continuous | P1 |
| Information Commission orders | State Information Commission | Appeal, office, order | Open | Continuous | P2 |
| Lokayukta and vigilance outcomes | Respective bodies | Matter, outcome | Partly | Ad hoc | P2 |

## 11. Evidence graph

Not collected from outside; produced by the platform for every item above.

| Record | Fields |
|---|---|
| Source document | Id, title, publisher, URL, fetched at, hash, language, page count, licence |
| Claim | Fact id, document, page, quote, tier, confidence, extracted by (agent and version), checked by, quote check result |
| Run | Workflow, agents and versions, inputs, outputs, cost, reviewer, decision |
| Correction | What changed, why, requested by, approved by, date |
| Gap | Missing record, why it matters, holder, RTI drafted, status |

## Minimum data for each graph to be useful

| Graph | Smallest useful set |
|---|---|
| Place | Ward boundaries and named roads for one ward |
| Money | One department's budget pages for five years |
| Procurement | Fifty tenders for one ward with their notices and any awards |
| Works and Assets | The roads in those tenders, with liability clauses |
| Organisation and Jurisdiction | One ward office's posts and the complaint routing table |
| People and Representation | The ward's corporators |
| Land and Planning | Twenty schemes in one ward with their approval letters |
| Services | Three indicators for all wards from one published report |
| Voice | Two budget speeches and a hundred residents' reports |
| Law and Oversight | One audit report and the directions on one regulation |

## Collection rules

- Archive every document before parsing it, with URL, time and hash. The archive is never edited.
- Prefer a published file over a scraped page, and a request to the agency over both.
- Do not defeat captchas or logins. A person collects those pages in a browser session at a slow rate, or the data is requested.
- Check each publisher's terms before storing or republishing news text; store links and short quotes where terms require it.
- Record the licence of every source and carry it through to anything published.
- Remove personal details of private individuals at intake. The platform holds no patient, pupil, applicant or beneficiary names.
