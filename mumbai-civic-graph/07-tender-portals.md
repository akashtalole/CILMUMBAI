# Tender portals: BMC and Mahatenders

What the two official tender sites publish, how their identifiers work, and how to turn them into graph data. Checked on 15 November 2026. Items marked **confirm** were not seen directly.

## 1. Where BMC tenders live

BMC procurement is spread over three channels. A tender notice's header says which one applies.

| Channel | Address | Role |
|---|---|---|
| **BMC portal** | `portal.mcgm.gov.in` / `www.mcgm.gov.in`, under *For Partners → Tenders* | Publishes tender notices and corrigenda as PDFs. Viewing only. |
| **Mahatenders** | `mahatenders.gov.in` | Maharashtra's e-procurement system (NIC GePNIC). Bids are submitted and opened here; awards are recorded here. |
| **GeM** | `gem.gov.in` | Used for some goods and equipment purchases. Bid numbers look like `GEM/2026/B/7825407`. |

History that matters for older data: BMC ran its own SAP SRM bidding system until the end of December 2023. BMC notices state that tenders moved to Mahatenders from 21 December 2023 and that SRM was closed to users after 30 December 2023. Works tendered before that date will not be on Mahatenders; only the BMC PDFs exist for them.

## 2. BMC portal

### What is there

- Tender notices as PDFs, in a predictable location and naming pattern:

  ```
  https://www.mcgm.gov.in/irj/go/km/docs/documents/Tenders-New/ETH/ETH_8000113000_110826.pdf
  https://portal.mcgm.gov.in/irj/go/km/docs/documents/Tenders/ETH/ETH_7000023382_041022.pdf
                                                              └┬┘ └────┬────┘ └─┬──┘
                                                        folder   bid number   date ddmmyy
  ```

- The same files are served from several hosts: `www`, `portal`, `r3app` and `crmapp` under `mcgm.gov.in`.
- Folders seen: `Tenders/ETH` (older) and `Tenders-New/ETH` (2026). Some files are named `..._Tender Notice.pdf` or `..._Draft Tender.pdf` instead of carrying a date.
- Bid numbers are ten digits starting `7000…`, `7200…` or `8000…`.
- Vendor manuals and instructions under `Tenders/Tender Manuals/`.

### What a notice contains

One 2026 notice was opened (a Disaster Management Department equipment purchase routed through GeM). Its index lists: e-tender notice, header data, preamble, instructions, general conditions of contract, technical specifications, bill of quantity, and annexures including an integrity pact, litigation history and pending criminal cases.

For works tenders, expect the header data to give department, ward or zone, description, estimated cost, earnest money, contract period and key dates, and the general conditions to hold the defect liability clause. **Confirm** on a roads notice from the demo ward.

### Constraints

- The tender listing page (`/irj/portal/anonymous/qlTenders`) is a SAP portal view that returned "not compatible with your browser" to a plain HTTP fetch. Open it in a real browser, or drive one with Playwright, to read the listing.
- The PDFs themselves download directly once the URL is known.
- Documents are long (the sample was 1.7 MB) and some are scanned. Send only the notice, header data and relevant conditions pages to Claude, not the whole file.
- No award or payment information is published here.

## 3. Mahatenders

### Public pages

All under `https://mahatenders.gov.in/nicgep/app?page=<name>&service=page`.

| Page name | Shows | Use |
|---|---|---|
| `FrontEndTendersByOrganisation` | Every organisation with its count of active tenders | Entry point per agency |
| `FrontEndLatestActiveTenders` | Active tenders | Current pipeline |
| `FrontEndAdvancedSearch` | Search by id, title, reference, organisation, dates | Targeted lookup |
| `FrontEndTendersByLocation` | Tenders by place | Ward-level filtering, if location is filled in |
| `FrontEndTendersByClassification` | By product or work category | Roads, drains and so on |
| `FrontEndLatestActiveCorrigendums` | Corrigenda | Deadline and scope changes |
| `WebTenderStatusLists` | Stage of each tender after closing | Bid opening, evaluation, award |
| `ResultOfTenders` | Award of contract (AOC) records | Award and contractor |
| `WebCancelledTenderLists` | Cancelled and retendered | Stalled works |
| `FrontEndTendersInArchive` | Closed tenders | History |
| `FrontEndDebarmentList` | Debarred bidders | Blacklisting |

There is also an MIS reports site at `gepnicreports.gov.in/eprocreports/maha/`. It returned a server error when checked; try again, as it may offer aggregate reports without page-by-page browsing.

### What was observed

- **Organisation list:** columns are S.No, Organisation Name, Tender Count. BMC appears as **"Municipal Corporation of Greater Mumbai"** with 158 active tenders.
- **Other Mumbai agencies on the same portal** (active tender counts): BEST 59, Public Works Department Mantralaya 38, MSRDC 24, MMRDA 12, CIDCO 12, MHADA 9, Public Works Special Projects Mumbai 3. This matters for Jawabdar: the same pipeline covers roads that are not BMC's.
- **Tender listings:** Tender Title, Reference No, Closing Date, Bid Opening Date.
- **Results of Tenders:** search by Tender ID or keyword; result columns are S.No, AOC Date, e-Published Date, Title and Ref.No./Tender ID, Organisation Chain, AOC.
- **Debarment list:** columns are S.No, Bidder Name, Login ID, Product Category, Start Date, End Date; searchable by login id or PAN. The default view showed no records.
- **Captcha:** the organisation list and the results search both require a captcha before showing data.

### Tender ID

Mahatenders ids follow the pattern seen in public document links:

```
2026_MCGM_1303610_1
 │     │      │    └ version (increments on retender)
 │     │      └ running number
 │     └ organisation code
 └ year
```

This is the best primary key for a `Tender` node from 2024 onward.

### Tender detail and award pages

GePNIC portals normally show, on each tender's detail page: organisation chain, tender reference number, tender id, tender category (works, goods, services), form of contract, tender value, earnest money, location and pincode, period of work in days, publication and closing dates, the inviting authority, and downloadable notice and bill-of-quantity files. The status and AOC pages normally list the bidders, the evaluation stages, the selected bidder and the awarded value.

These were not opened in this session because they sit behind the captcha. **Confirm** on five BMC tenders in the data spike. If the status pages do list all bidders, the bid-level red flags in [03-thekedar-graph.md](03-thekedar-graph.md) become feasible.

## 4. Mapping to the ontology

| Portal field | Graph |
|---|---|
| Tender ID (`2026_MCGM_…`) | `Tender.id` |
| Tender reference number / BMC bid number | `Tender.ref_no`, `Tender.bmc_bid_no` |
| Organisation chain (organisation → department → division) | `Agency`, `Department`, and `(Tender)-[:ISSUED_BY]->(Department)` |
| Title, work description | `Work.title`; road and ward names extracted by Claude into `(Work)-[:IMPROVES]->(Asset)` |
| Tender category, form of contract | `Tender.category`, `Tender.contract_form` |
| Tender value, EMD | `Tender.estimated_cost`, `Tender.emd` |
| Location, pincode | Candidate `AdminWard` |
| Period of work | `Contract.duration_days`, used to compute `due_on` |
| Published, closing, opening dates | `Tender.published_on`, `closes_on`, `opened_on` |
| Corrigendum | `(Corrigendum)-[:AMENDS]->(Tender)` with the changed field and both values |
| Tender status stage | `Tender.stage`, dated |
| AOC date, selected bidder, awarded value | `Award`, `(Award)-[:TO]->(Contractor)`, `Contract.value` |
| Bidder list | `Bid`, `(Contractor)-[:SUBMITTED]->(Bid)` |
| Cancelled / retendered | `Tender.status`; `(Tender)-[:RETENDER_OF]->(Tender)` using the version suffix |
| Debarment entry | `Blacklisting {from, to}` on `Contractor` |
| Defect liability clause in BMC notice | `DefectLiabilityPeriod` |

### Joining the two portals

A work appears on both sites under different numbers. Link them in this order and record which rule matched:

1. The BMC bid number printed as the reference number on Mahatenders, or the Mahatenders id printed in the BMC PDF.
2. Same department, same closing date, and same estimated cost.
3. Claude compares titles for the remaining candidates and gives a reason; stored as a probable match.

## 5. Collection plan

The captcha is the site's access control for listings. Do not try to defeat it. Work with it:

| Method | How | When |
|---|---|---|
| **Ask for the data** | Request a bulk export of BMC tenders and awards from the organisers or BMC's IT department | First; the event has civic authorities in the room |
| **Assisted browsing** | A person opens the site in a Playwright-driven browser, solves the captcha once, and the script saves the listing and detail pages for the chosen organisation during that session at a slow, polite rate | Pre-event corpus for one ward |
| **MIS reports** | Check whether the GePNIC reports site gives organisation-level tables | If it is back up |
| **BMC PDFs** | Direct download once bid numbers are known from the BMC listing | Notice text, conditions, liability clause |
| **Third-party mirrors** | Sites such as Public Services Map and InfraLens republish Mahatenders notices | Discovery only; always cite the official page |

Store every saved page with its URL, time and hash. The demo runs from that archive.

### Scope for the hackathon

- BMC, Roads and Traffic department, one ward, tenders from January 2024 onward.
- Target: 40 to 60 tenders with detail pages, their AOC records where they exist, and the matching BMC notice PDFs.
- Add 5 to 10 tenders from MMRDA, MSRDC or PWD touching the same ward, for the multi-agency case.

## 6. Effect on the five ideas

| Idea | What the portals add |
|---|---|
| Paisa Trail | A stable tender id, estimated cost, award value and contractor from an official source. Budget code is still the missing hop. |
| Vachan Tracker | Tender stage and corrigenda give dated, official evidence of progress or slippage. Cancelled and retendered lists reveal stalled promises. |
| Thekedar Graph | AOC records for awards; debarment list for blacklisting; bidder lists if status pages show them. |
| Jawabdar | Period of work gives completion dates; BMC notice gives the liability clause; other agencies' tenders on the same portal settle whose road it is. |
| Ward Lens | Tender value by ward and category, where location is filled in. |

## 7. Still not available from either portal

- The budget head a tender is charged to.
- Payments made and measurement records.
- Completion certificates and inspection reports.
- Penalties imposed.

These need committee resolutions, press notes, the concretisation dashboard or RTI. The trail should show them as named gaps.

## Sources

- [Mahatenders home](https://mahatenders.gov.in/nicgep/app)
- [Mahatenders: tenders by organisation](https://mahatenders.gov.in/nicgep/app?page=FrontEndTendersByOrganisation&service=page)
- [Mahatenders: results of tenders](https://mahatenders.gov.in/nicgep/app?page=ResultOfTenders&service=page)
- [Mahatenders: debarment list](https://mahatenders.gov.in/nicgep/app?page=FrontEndDebarmentList&service=page)
- [BMC tender notice, bid 8000113000](https://www.mcgm.gov.in/irj/go/km/docs/documents/Tenders-New/ETH/ETH_8000113000_110826.pdf)
- [BMC e-tendering FAQ](https://www.mcgm.gov.in/com.mcgm.atenders_overview/docs/FAQ_Tenders.html)
- [BMC instructions to vendors](https://www.mcgm.gov.in/irj/go/km/docs/documents/Tenders/Tender%20Manuals/Instructions_to_Vendors.pdf)
- [BMC tender notice, bid 8000087897](https://r3app.mcgm.gov.in/irj/go/km/docs/documents/Tenders/ETH/ETH_8000087897_150725.pdf)
