# Solution design

## 1. Principles

- **Neutral.** The register records what each authority did and said. It does not rule on who has jurisdiction. Where the law is contested, it shows both readings and the direction currently in force.
- **Plot first.** Everything hangs off the plot, identified by its city survey number, because that is the one thing both authorities, the land records and the homebuyers' regulator all share.
- **Sourced and dated.** Every status, approval and figure carries its document, page, quote and date. A plot's slum status in particular is recorded as "declared by X on date Y", never as a bare fact.
- **Not legal advice.** The jurisdiction card tells a resident where their file is and which office to approach. It says plainly that it is a summary of published directions.

## 2. Modules

### 2.1 Scheme Register

Every scheme under Regulation 33(11), and the neighbouring routes it is confused with (33(10) slum rehabilitation, 33(20)(B)), with:

- the plots it covers and each plot's status;
- whether plots were pooled, and which are slum and which are not;
- the developer;
- each approval in order (letter of intent, intimation of approval, commencement certificate, occupation certificate), with the issuing authority and date;
- floor space sanctioned, by component.

This alone answers a question nobody can answer today: of the roughly 300 schemes BMC flagged and the 522 SRA counts, which are which, where are they, and what stage are they at.

### 2.2 Jurisdiction Card

For any plot or scheme, a short card:

```
Plot CTS 123, Village X, Ward K/W
Status:        Non-slum (no declaration on record; source: … , as of …)
Scheme:        33(11), pooled with CTS 456 (declared slum, …)
Directed to:   SRA   under UDD directions of 15 Oct 2024, reiterated 2 Nov 2026
Contested by:  BMC   (Commissioner's letter of 22 Jul 2026)
Approvals:     LOI by SRA (date) · IOA by SRA (date) · water NOC by BMC pending since (date)
Approach:      SRA, [office], for the scheme · BMC ward office for water, sewer, road
```

The card is produced by rules, described in section 4. When a new direction or court order arrives, the rule changes and every card updates, with the old answer kept in history.

### 2.3 Tenement Ledger

For each scheme: transit and project-affected tenements owed, built, handed over, and to whom. Rolled up by ward, developer and year.

This is the module with the most direct value to residents. The reported gap between tenements generated (32,337) and handed over (6,604) becomes a list of named schemes, each with its due date and current stage. A displaced family, or the agency responsible for housing them, can see which schemes near them owe homes.

### 2.4 Concession Meter

For each scheme: each premium or charge, the basis clause, the amount assessed, the amount paid, any concession and the clause that grants it.

BMC says premium revenue is being lost. SRA says premiums are payable at standard rates. The meter does not take a side. It shows, scheme by scheme, what was assessed and paid, and the total. If data from one authority is missing, the meter says so and names the record that would fill it.

### 2.5 Ward Load Sheet

Per ward: additional built-up area approved, by authority and by regulation, against published figures for open space, water supply and sewer capacity where they exist. Shows whether approvals from two authorities are being added together by anyone.

### 2.6 Handoff Tracker

Even where SRA is the planning authority, schemes need BMC sign-offs for water, sewerage, storm drains, roads and fire safety. Each is recorded with the date requested and the date issued. Median waiting time by department and ward shows where files actually stall, which is useful to both authorities and to the state.

### 2.7 Resident's Front Door

Through the existing citizen desk: "Which authority has my building's file? What stage is it at? Who do I approach about transit rent, about water, about the occupation certificate?" Answered from the register, with sources, in Marathi, Hindi or English, with a drafted letter to the right office.

### 2.8 Dual-Reading Brief

A neutral document for the state, the press and the public: the text of the regulation and each direction, BMC's reading and SRA's reading side by side with the exact words each relies on, the points where they differ, and what the register's data shows on each disputed factual claim. Produced by agents, reviewed by a lawyer. See [02-agents-and-pipeline.md](02-agents-and-pipeline.md).

## 3. Ontology extension

Added to the Mumbai Civic Ontology in [../../mumbai-civic-graph/00-shared-foundation.md](../../mumbai-civic-graph/00-shared-foundation.md).

### Classes

```
Land         Plot, PlotStatusClaim, Reservation
Scheme       Scheme, SchemeComponent, Developer, Society
Approval     Approval (LOI, IOA, CC, OC), NOC, Authority (BMC, SRA, UDD, MHADA…)
Law          Regulation, Clause, Direction (government resolution, letter, circular),
             CourtOrder, Position, JurisdictionRule
Obligation   TenementObligation, Handover, Premium, Concession
People       ProjectAffectedGroup (never individuals)
```

### Relationships

```
(Scheme)-[:COVERS]->(Plot)                    (Scheme)-[:UNDER]->(Regulation)
(Scheme)-[:POOLED_WITH]->(Scheme)             (Developer)-[:PROMOTES]->(Scheme)
(PlotStatusClaim {status, as_of})-[:ABOUT]->(Plot)
(PlotStatusClaim)-[:MADE_BY]->(Authority)
(Approval {kind, date})-[:FOR]->(Scheme)      (Authority)-[:ISSUED]->(Approval)
(NOC {dept, requested_on, issued_on})-[:FOR]->(Scheme)
(Direction {date})-[:INTERPRETS]->(Clause)    (Authority)-[:ISSUED]->(Direction)
(Direction)-[:REITERATES|SUPERSEDES]->(Direction)
(Position {date, summary})-[:TAKEN_BY]->(Authority)
(Position)-[:ON]->(Clause)                    (Position)-[:STATED_IN]->(SourceDocument)
(JurisdictionRule)-[:BASED_ON]->(Direction|CourtOrder)
(JurisdictionRule)-[:ASSIGNS]->(Authority)
(Scheme)-[:OWES]->(TenementObligation {count, kind, due_on})
(Handover {count, date})-[:AGAINST]->(TenementObligation)
(Premium {kind, assessed, paid})-[:FOR]->(Scheme)
(Premium)-[:PAYABLE_TO]->(Authority)
(Concession {amount})-[:ON]->(Premium)        (Concession)-[:GRANTED_UNDER]->(Clause)
```

`PlotStatusClaim` is deliberately a claim and not a property. Whether a plot is a slum is the heart of the dispute, and two authorities may say different things about the same plot at different times.

## 4. Jurisdiction rules

Rules are data, not code. Each has conditions, an outcome, a basis and a validity period.

```yaml
- id: rule-33-11-udd-2024
  when:
    scheme.regulation: "33(11)"
  assigns: SRA
  basis: direction:udd-2024-10-15
  valid_from: 2024-10-15
  status: in_force
  reiterated_by: direction:udd-2026-11-02
  contested_by:
    - position: position:bmc-2026-07-22
      applies_when: "scheme covers a plot with no slum status claim"
```

Resolution is done in code:

1. Collect the scheme's regulation and every plot's status claims.
2. Select rules whose conditions match and whose validity covers today.
3. Among directions, prefer the latest that has not been superseded; a court order outranks a direction.
4. Return the assigned authority, the basis, and any position that contests it for this fact pattern.

The output always separates three things: what is directed, who contests it, and what is simply unknown. A lawyer on the team reviews every rule before it is used. The exact wording of each condition must come from the direction's text, which this plan has not seen.

## 5. Data sources

None of these was tested for this plan. Confirm each in a data spike.

| Source | Gives | Likely access |
|---|---|---|
| SRA website publications, including letters of intent issued under 33(11) | Scheme, plots, developer, approvals, tenement counts | Published lists and PDFs |
| MahaRERA public project search | Projects, promoter, survey numbers, planning authority named, approvals and dates | Public website |
| BMC online building proposal system | Approvals and NOCs issued by BMC | Public status lookup, if available; otherwise RTI |
| DCPR 2034 text and amendments | Regulation and clauses | Published |
| UDD directions and government resolutions | Directions | State resolutions portal; the letters themselves may need RTI |
| Commissioner's and SRA's letters | Positions | Press reports now; RTI for the text |
| Slum declarations and SRA slum mapping, including the SRA GIS portal at umd.nic.in/sra (slum areas by ward, cluster and hut id) | Plot status claims, with the map layer as evidence | Partly published; the GIS portal is interactive and needs SRA's agreement for a data export |
| Development Plan 2034 sheets | Reservations, open space | Published maps |
| Bombay High Court orders | Court orders on jurisdiction and individual schemes | Public |
| BMC budget documents | Premium and development charge revenue | Published |
| Residents' associations and housing rights groups | Handover and transit rent status on the ground | Partnership |

Premium payments and NOC dates per scheme are the hardest to obtain and will probably need RTI to both authorities. The register should show these as named gaps from the first day, and the RTI drafter should produce the applications.

## 6. Example queries

Schemes that include a plot with no slum status claim, by ward:

```cypher
MATCH (s:Scheme)-[:UNDER]->(:Regulation {code: '33(11)'})
MATCH (s)-[:COVERS]->(p:Plot)-[:LOCATED_IN]->(w:AdminWard)
OPTIONAL MATCH (c:PlotStatusClaim {status: 'slum'})-[:ABOUT]->(p)
WITH s, w, p, count(c) AS slum_claims
WHERE slum_claims = 0
RETURN w.code, count(DISTINCT s) AS schemes, count(DISTINCT p) AS plots
ORDER BY schemes DESC
```

Tenements owed and not yet handed over, largest first:

```cypher
MATCH (s:Scheme)-[:OWES]->(o:TenementObligation)
OPTIONAL MATCH (h:Handover)-[:AGAINST]->(o)
WITH s, o, sum(h.count) AS handed
RETURN s.name, o.count AS owed, handed, o.count - handed AS outstanding, o.due_on
ORDER BY outstanding DESC
LIMIT 50
```

Where sign-offs wait longest:

```cypher
MATCH (n:NOC)-[:FOR]->(:Scheme)-[:COVERS]->(:Plot)-[:LOCATED_IN]->(w:AdminWard)
WHERE n.issued_on IS NULL
RETURN w.code, n.dept, count(n) AS pending, min(n.requested_on) AS oldest
ORDER BY pending DESC
```

Premiums assessed against paid, by receiving authority:

```cypher
MATCH (pr:Premium)-[:FOR]->(s:Scheme)
MATCH (pr)-[:PAYABLE_TO]->(a:Authority)
OPTIONAL MATCH (c:Concession)-[:ON]->(pr)
RETURN a.name, sum(pr.assessed) AS assessed, sum(pr.paid) AS paid, sum(c.amount) AS concessions
```

`sum` over an empty optional match should be checked on the chosen database; compute the difference in code if it returns null.
