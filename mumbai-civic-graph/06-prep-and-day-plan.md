# Preparation and day plan

For the recommended build: **Paisa Trail as the spine, Jawabdar as the front door, one ward, roads only.**

## Before the event (16 to 20 November)

The single biggest risk is arriving without data. Everything this week reduces that risk.

| Day | Task | Output |
|---|---|---|
| Mon 16 | **Data spike.** Open every source in [00-shared-foundation.md](00-shared-foundation.md) section 4 and record what is actually downloadable and in what format. On Mahatenders, open five BMC road tenders and note exactly what the detail, status and AOC pages show ([07-tender-portals.md](07-tender-portals.md) lists what to confirm). Email the organisers to ask what data the problem briefing will provide. | A one-page source log: works / broken / needs login |
| Mon 16 | **Choose the ward.** Pick one a team member lives in, with visible road works and at least one non-BMC road. | Named ward |
| Tue 17 | **Database spike.** Run HydraDB locally and Neo4j Community in Docker. Load 100 dummy nodes over Bolt with the `neo4j` Python driver. Run the queries from the idea files on both. Read HydraDB's `cypher-compat.md` for `MERGE`, date arithmetic and variable-length paths. | Decision: HydraDB or Neo4j, written down with the reason |
| Tue 17 | **Ontology v0.** Write `mco.ttl` and SHACL shapes for the roads slice only. Generate the extraction JSON schema from it. | Schema that validates one hand-written example |
| Wed 18 | **Corpus.** Download the roads budget pages, 40 to 60 tenders for the ward from Mahatenders with their BMC notice PDFs, any committee resolutions, the concretisation dashboard entries, ward boundaries, OpenStreetMap roads. Archive with hashes. | `data/raw/` with a manifest |
| Wed 18 | **Gold set.** Hand-label 10 documents. Write 30 evaluation questions with correct answers. | `eval/` folder |
| Thu 19 | **Extraction v0.** Run Claude over the corpus with the schema. Measure against the gold set. Fix the prompt, not the output. | Accuracy number; loaded graph |
| Thu 19 | **Org graph.** Hand-build agencies, departments, posts and the issue routing table for the ward. | "Who is responsible" query works |
| Fri 20 | **Walk the ward.** Photograph five roads in the graph. Note which facts the graph got right. Take the demo photos. | Reality check and demo assets |
| Thu 19 | **Agents.** Run `ant apply` in `managed-agents/`, then `civic_client.py ingest` on ten documents. Fix what the first real run shows; tune the rubric. See [08-multi-agent-system.md](08-multi-agent-system.md). | Agents created; one clean intake batch |
| Fri 20 | **Skeleton app.** Map, one trail view, and a chat panel backed by the Citizen desk agent. | Something that runs end to end, however rough |
| Fri 20 | **Freeze.** Snapshot the database. Write the demo script. Prepare a one-page brief for teammates who join on the day. | A build that works with no network |

Check the event rules on pre-built work. If only work done on the day counts, treat the above as data preparation and research (normally allowed) and rebuild the app on the day from the plan. The data, ontology and gold set are the parts that cannot be made in eight hours.

## Team

Aim for four or five people. The event invites non-coders; use them.

| Role | On the day |
|---|---|
| Graph and back end | Loader, queries, graph tools in `civic_client.py` |
| AI | Agent files and rubrics, intake runs, evaluation |
| Front end | Map, trail cards, chat, mobile view |
| Domain (policy person, journalist or resident) | Verifies facts, finds the story, writes the complaint templates |
| Lawyer, if available | Reviews wording of anything naming a contractor; checks RTI and complaint drafts |

## Day plan (21 November)

Adjust to the published schedule. Assumes roughly eight build hours.

| Time | Activity |
|---|---|
| Briefing | Listen for two things: what data the authorities can share, and what they say hurts most. Change scope to match. If they hand over data, one person starts ingesting it immediately. |
| Hour 0 to 1 | Team formation. Share the one-page brief. Agree the demo script first, then work backwards from it. Assign owners. |
| Hour 1 to 3 | **Vertical slice.** One road, end to end: map tap → trail → source page. Photo → responsible post → draft complaint. Ugly is fine. |
| Hour 3 to 5 | **Widen.** Load the full ward. Run the evaluation set. Fix the worst extraction errors. Add the liability period and the second-agency case. |
| Hour 5 to 6 | **Languages and polish.** Marathi and Hindi answers. Source drawer with highlighted quotes. "Allocated but not tendered" list. |
| Hour 6 to 7 | **Feature freeze.** Rehearse the demo three times. Record a backup video. Domain lead checks every figure that will appear on screen. |
| Hour 7 to 8 | Pitch deck: five slides (below). Buffer. |

### Rules for the day

- Demo from the frozen local snapshot, not from live sources or venue wifi.
- Any figure shown on screen must open to its source in one click.
- If a feature is not working by the freeze, cut it from the demo and put it on the roadmap slide.
- Keep the Neo4j container ready even if HydraDB is primary.

## Pitch (five slides, three minutes plus demo)

1. **The question.** A photo of a broken road in the ward. "Who built this, what did it cost, and who has to fix it?" Today that takes an RTI and thirty days.
2. **Demo.** Photo to answer to drafted complaint. Then the money trail.
3. **How.** One ontology, one graph, built only from documents BMC already publishes. Every fact cites its page.
4. **What the city gains.** Fewer misrouted complaints; defects repaired at contractor cost while roads are under liability; an early-warning list of allocations not yet tendered.
5. **The ask.** One ward office for a 90-day pilot, and tender and work-order data as files instead of PDFs. Roadmap: promise tracking, contractor red flags, ward scorecards.

## After the event

| When | Step |
|---|---|
| Week 1 | Publish the ontology and the cleaned one-ward dataset under an open licence. Write up what was easy and what was not. |
| Weeks 2 to 4 | Expand to three wards. Automate weekly refresh. Add Vachan Tracker on the same graph. |
| Month 2 | Pilot Jawabdar with one ward office and one residents' association. Measure routing accuracy and time to resolution. |
| Month 3 | Legal review, then a limited release of Thekedar Graph to journalists and auditors. Begin Ward Lens indicators. |

## Checklist to bring

- Laptop with the database snapshot, both database containers and the corpus stored locally
- Claude credits activated; API key tested; agents applied and `claude-lock.json` committed
- Demo photos with location metadata
- Backup demo video
- Printed one-page brief and the source log
- Phone hotspot
