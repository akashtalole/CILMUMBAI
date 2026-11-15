# Idea 4: Jawabdar

**"Who is responsible for this?" A photo in, the accountable agency, post and contractor out, with a complaint ready to file.**

Read [00-shared-foundation.md](00-shared-foundation.md) first.

## The problem

In Mumbai, the road outside your building may belong to BMC, MMRDA, MSRDC, the state PWD, MHADA, the railways or the port authority. Inside BMC it may fall to the ward office or to a central department. The trench in it may have been dug by a utility. Citizens complain to the wrong body, the complaint is closed as "not ours", and nothing happens.

There is a second, less known lever: works are usually covered by a **defect liability period**, during which the contractor must repair defects at their own cost. If a newly built road cracks inside that period, the right demand is not "please fix it" but "make the contractor fix it, as the contract requires". Citizens almost never know a road is under liability.

## What the citizen gets

1. Take a photo or drop a pin. On WhatsApp or the web.
2. Get back, in their language:
   - **Whose it is:** the owning agency and department.
   - **Who is accountable:** the post responsible (for example the ward's Assistant Engineer, Roads), and the escalation chain above it.
   - **The work history:** last work on this asset, contractor, cost, completion date.
   - **Liability status:** "This road was completed in March 2025 and is under contractor liability until March 2030" (dates from the contract, where known).
   - **The elected representative** for that electoral ward.
3. **A drafted complaint** addressed to the right office, citing the work order and the liability clause, plus an optional RTI application asking for the inspection reports.
4. A tracking link. If the complaint is not resolved in the service-level time, a drafted escalation to the next post up.

## Why a graph

The answer is a traversal across four different hierarchies that meet at a point on the map:

```
(point) → Asset → OWNED_BY → Agency → Department → Post → HOLDS ← Person
                → LOCATED_IN → AdminWard → ElectoralWard ← REPRESENTS ← Person
                ← IMPROVES ← Work ← Contract ← PARTY_TO ← Contractor
                                  → DefectLiabilityPeriod {from, to}
          Post → REPORTS_TO* → Post         (escalation chain)
```

## Graph slice

```
(Agency)-[:OWNS]->(Asset)
(Department)-[:PART_OF]->(Agency)
(Department)-[:MAINTAINS {category}]->(AssetType)
(Post)-[:IN]->(Department)
(Post)-[:COVERS]->(AdminWard)
(Post)-[:REPORTS_TO]->(Post)
(Person)-[:HOLDS {from,to}]->(Post)
(Work)-[:HAS_DLP]->(DefectLiabilityPeriod)
(IssueType)-[:HANDLED_BY]->(Department)           // pothole → Roads; open manhole → Sewerage
(IssueType)-[:HAS_SLA {days}]->(ServiceStandard)
(Complaint)-[:ABOUT]->(Asset)   (Complaint)-[:ROUTED_TO]->(Post)   (Complaint)-[:ESCALATED_TO]->(Post)
```

The `IssueType` → `Department` routing table is small (about 40 issue types) and can be written by hand from BMC's published complaint categories.

## Example queries

Who is responsible, given an asset and an issue type:

```cypher
MATCH (a:Asset {id: $asset_id})-[:LOCATED_IN]->(w:AdminWard)
MATCH (ag:Agency)-[:OWNS]->(a)
MATCH (it:IssueType {code: $issue})-[:HANDLED_BY]->(d:Department)-[:PART_OF]->(ag)
MATCH (p:Post)-[:IN]->(d)
MATCH (p)-[:COVERS]->(w)
OPTIONAL MATCH (per:Person)-[h:HOLDS]->(p) WHERE h.to IS NULL
RETURN ag.name, d.name, p.title, per.name
```

Escalation chain:

```cypher
MATCH (p:Post {id: $post_id})-[:REPORTS_TO*1..4]->(up:Post)
RETURN up.title, up.office
```

Is the asset under contractor liability today:

```cypher
MATCH (a:Asset {id: $asset_id})<-[:IMPROVES]-(w:Work)-[:HAS_DLP]->(d:DefectLiabilityPeriod)
WHERE d.from <= $today AND d.to >= $today
MATCH (k:Contractor)-[:PARTY_TO]->(:Contract)-[:FOR_WORK]->(w)
RETURN w.title, k.name, d.to
```

## Implementation plan

### Data to assemble

| Data | Source | Effort |
|---|---|---|
| Road geometry and names for the demo ward | OpenStreetMap | Low |
| Ward boundaries, administrative and electoral | OpenCity or BMC files | Low |
| Road ownership (which roads are not BMC's) | Agency project maps, news, local knowledge; start with a short list of known non-BMC roads in the ward | Medium, manual |
| BMC ward office structure: posts and reporting lines | BMC website, proactive disclosures under RTI Act section 4 | Medium |
| Issue type to department routing | BMC complaint categories | Low, manual |
| Recent works and contractors on each road | Paisa Trail graph, or the concretisation dashboard directly | Medium |
| Works by other agencies in the ward | Mahatenders lists MMRDA, MSRDC, PWD, MHADA and BEST tenders alongside BMC's | Medium |
| Defect liability terms | General conditions in the BMC tender notice PDF for each work | Medium; Claude extracts the clause and period |
| Corporators by electoral ward | Public lists | Low |

### Build phases

| Phase | Work | Done when |
|---|---|---|
| 1. Locate | Point → nearest road segment → ward → electoral ward, using PostGIS or Shapely | Correct for 20 test points |
| 2. Org graph | Agencies, departments, posts, reporting lines, routing table for the demo ward | "Who is responsible" query returns a post for every issue type |
| 3. Work and liability | Link works to road segments; extract liability period from tender conditions; compute `from` and `to` | 15+ roads in the ward with liability dates |
| 4. Photo understanding | Claude vision: issue type, severity, any signboard text; ask one clarifying question if unsure | 9 of 10 test photos classified correctly |
| 5. Drafting | Complaint and RTI templates filled from graph facts; English, Hindi, Marathi | A lawyer on the team approves the templates |
| 6. Channel | Web app first; WhatsApp through a business API sandbox if time allows | Photo to answer in under 20 seconds |
| 7. Tracking | Store complaint, due date from the service standard, drafted escalation | Escalation draft appears when the clock is advanced |

### Agent design

One agent with the MCP tools `locate`, `who_is_responsible`, `work_status`, `trace_money`, `get_source`. Instructions:

- Ask for location if the photo has none. Never guess a location from the image.
- State ownership with its trust tier. If ownership is uncertain, say "probably BMC; if they say it is not theirs, here is who else it could be".
- Name posts, not people, in the drafted complaint, unless the person is an elected representative.
- Cite the work order and liability clause only when they are in the graph.

### Filing

Do not automate submission into government portals at the hackathon. Give the citizen the draft, the right channel (BMC's helpline, app or ward office; the state RTI portal) and a one-tap copy. Automated filing is something to negotiate with BMC as part of adoption.

## Demo script (2 minutes)

1. On a phone, photograph a cracked concrete road (a prepared image with location).
2. The reply appears: BMC, Roads department of the ward, the responsible post, the contractor, completed on a given date, **under contractor liability until a given date**, with a link to the contract clause.
3. Tap "Draft complaint". It appears in Marathi, citing the work and the clause.
4. Second pin, on a road owned by another agency: the answer changes to that agency and its grievance channel. This is the moment the audience understands the routing problem.
5. Show the ward officer's view: open defects on roads still under liability, grouped by contractor. "This is money the city does not need to spend."

## Why authorities might adopt it

- Fewer misrouted complaints reaching the wrong desk.
- Defects on roads under liability get fixed at the contractor's cost, not the city's.
- It can sit in front of the existing complaint system as a routing layer. It does not replace anything.

## Success measures

- Routing accuracy on test points checked by someone who knows the ward.
- Share of the ward's recently built roads with known liability dates.
- Time from photo to a correct, sourced answer.

## Risks specific to this idea

| Risk | Mitigation |
|---|---|
| Wrong agency named | Show confidence and the alternative; let users correct it; corrections go to review, then into the graph |
| Liability dates wrong | Show only when extracted from a contract document, with the clause quoted |
| Officer names out of date | Route to the post; show the holder only with a "last verified" date |
| Harassment of individual officers | Post-based addressing; no personal phone numbers; rate-limit complaints per asset and merge duplicates |
