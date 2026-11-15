# Idea 41: Ek Plot, Ek Record

**One plot, one record: a shared, neutral register of redevelopment approvals across BMC and SRA, built around the people both authorities are meant to serve.**

Written 15 November 2026 in response to the BMC and SRA dispute over who approves redevelopment schemes on non-slum plots.

## The news, as reported

Facts below are from two press reports dated early November 2026. I could not open the underlying letters or the regulation text, so treat every item as "reported" until checked against the documents.

| Date | Event |
|---|---|
| August 2024 | The then municipal commissioner raises concerns about SRA approving schemes on plots without slums. |
| 15 October 2024 | The state Urban Development Department (UDD) issues directions on Regulation 33(11). BMC reads them as limiting the regulation to slum rehabilitation schemes. |
| 22 July 2026 | The BMC Commissioner writes to UDD, flags about 300 SRA-approved schemes, and asks that planning authority for these rest with the corporation. |
| 2 September 2026 | SRA replies, defending its use of the regulation. |
| 2 November 2026 | UDD writes to SRA reiterating that 33(11) proposals are to be processed by SRA under the October 2024 directions. It does not give BMC the planning powers it asked for. |

**What the regulation is for.** Regulation 33(11) of the Development Control and Promotion Regulations 2034 lets schemes create permanent transit camp (PTC) tenements: homes for people displaced by infrastructure and redevelopment works. A newer provision, 33(20)(B), is reported as the route BMC would handle.

**The two positions.**

| | BMC | SRA |
|---|---|---|
| Reading | 33(11) is for slum rehabilitation; it should not be used on vacant plots with no slum | 33(11) exists to produce transit tenements and allows eligible plots to be pooled |
| Concern | Concessions meant for slums reach non-slum plots; premium revenue is lost; open space in prime areas shrinks | Premiums are payable at standard rates under BMC policy; pooling reduces dependence on government land |
| Asks | Planning authority for these schemes | Continue as directed by the state |

**The numbers in play** (SRA figures as reported): 522 approved schemes; 32,337 tenements for project-affected people generated; 6,604 handed over; about 50,000 needed now and 2.2 lakh under the Development Plan. BMC's development charges were reported at nearly ₹12,000 crore in 2025-26, its second-largest revenue source.

The latest reports describe the disagreement as continuing. Developers quoted in them welcome the clarification but speak of hope, not of a settled process.

## Why this is a citizens' problem, not only a turf war

The dispute is argued in terms of powers and premiums. Four groups of residents carry the cost.

1. **Displaced families waiting for a home.** By the reported figures, about 25,700 tenements have been generated on paper but not handed over. Nobody outside can see which schemes owe them or why they are late.
2. **Residents of buildings and slums under redevelopment.** When two authorities contest a file, it slows. Families living on transit rent pay for every month of delay.
3. **Every taxpayer.** If premiums are being forgone, that is public money. If they are not, the claim should be put to rest. Today neither side's figures can be checked.
4. **Neighbours.** One authority approves the floor space; the other must supply the water, sewers, roads and open space. Nobody adds up what has been approved in a ward against what the ward can carry.

A fifth cost falls on everyone: when something goes wrong in such a building, a resident does not know which authority to approach, and each can point to the other.

## The solution in one paragraph

Do not try to decide who is right. Build the record that both authorities, the state and residents are missing: for every plot in a contested scheme, one page showing its status (slum or not, and on whose word), the scheme and regulation, which authority issued each approval, the tenements owed and delivered, the premiums assessed and paid, and the infrastructure sign-offs. Add a jurisdiction card that states which authority is currently directed to process the plot, under which dated direction, and who contests it. Then let agents keep the record current, prepare a neutral brief that sets the two readings side by side with the exact text each relies on, and answer residents' questions.

The register turns an argument about powers into three questions that data can answer: how many transit homes have these schemes actually delivered, how much premium has been paid or waived, and how much extra load has each ward been given.

## Files

| File | Contents |
|---|---|
| [01-solution-design.md](01-solution-design.md) | Modules, ontology extension, jurisdiction rules, data sources, example queries |
| [02-agents-and-pipeline.md](02-agents-and-pipeline.md) | The agents, how they fit the existing desks, and the LangGraph steps |
| [03-implementation-plan.md](03-implementation-plan.md) | Phases, hackathon slice, team, demo, risks, adoption |

This builds on the foundation in [../../mumbai-civic-graph/](../../mumbai-civic-graph/): the same graph, the same agent desks and the same rule that every fact carries its source.

## Sources

- [Maha Urban Development Dept clarifies DCR 33(11), Free Press Journal, 6 November 2026](https://www.freepressjournal.in/mumbai/maha-urban-development-dept-clarifies-dcr-3311-real-estate-stakeholders-hope-move-will-end-jurisdictional-disputes)
- [BMC, SRA dispute over redevelopment approvals on non-slum plots, Realty Today](https://therealtytoday.com/news/news/bmc-sra-dispute-over-redevelopment-approvals-on-non-slum-plots-in-mumbai)
- [UDD reiterates directions on Regulation 33(11), Free Press Journal](https://www.freepressjournal.in/mumbai/maharashtra-urban-development-department-reiterates-directions-on-regulation-3311-developers-hope-move-will-end-uncertainty)
- [BMC challenges SRA authority over non-slum land development, MSN](https://www.msn.com/en-in/news/other/bmc-challenges-sra-authority-over-non-slum-land-development/ar-AA2gWURs) (found in search; page did not load)
- [SRA publications: letters of intent under Regulation 33(11)](https://www.sra.gov.in/publication/index/1095) (found in search; not opened)
