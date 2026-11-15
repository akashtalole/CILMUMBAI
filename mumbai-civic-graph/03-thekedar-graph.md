# Idea 3: Thekedar Graph

**A contractor and procurement graph that surfaces patterns worth checking.**

Read [00-shared-foundation.md](00-shared-foundation.md) first.

## The problem

Press reports describe contractors fined or blacklisted for poor road work, and penalties that go unrecovered for months. What the public cannot see is the pattern across contracts: who keeps winning, whether a blacklisted firm's directors reappear under another name, whether the same few bidders rotate, whether penalised firms still receive new awards.

These are graph questions. They are also the questions where a wrong answer does the most damage, so this idea needs the most care.

## What the user gets

Primary users are journalists, auditors, vigilance staff and civil society researchers, not the general public.

- **Contractor profile:** all contracts, total value, wards, on-time record, penalties, blacklisting periods, related entities.
- **Red flags**, each a named, documented pattern with the underlying records attached.
- **Network view:** contractors, companies, directors and addresses, with shared links highlighted.
- **Ask:** "Which contractors penalised in 2025 received new awards within twelve months?"

## Red flag catalogue

Based on widely used open-contracting red flag indicators. Each is a deterministic query; the model only explains results.

| Flag | Pattern |
|---|---|
| Award after penalty | New `Award` dated inside or shortly after a `Penalty` or `Blacklisting` period |
| Reappearing directors | A director of a blacklisted company is a director of another company that then wins |
| Shared identity | Two bidders on the same tender share an address, phone, email or director |
| Single bidder | Tender with one valid bid |
| Concentration | One contractor holds more than a set share of a ward's or department's contract value |
| Bid rotation | A small set of bidders repeatedly co-bid and take turns winning |
| Cost escalation | Contract value revised upward beyond a threshold after award |
| Just under threshold | Clusters of contract values just below an approval limit |
| Short tender window | Days between publication and closing below the norm |
| Chronic delay | Share of a contractor's works past due date |

## Graph slice

```
(Contractor)-[:IS]->(Company)
(Director)-[:DIRECTOR_OF {from,to}]->(Company)
(Company)-[:REGISTERED_AT]->(Address)
(Contractor)-[:SUBMITTED]->(Bid)-[:ON]->(Tender)
(Award)-[:OF]->(Tender)    (Award)-[:TO]->(Contractor)
(Penalty)-[:IMPOSED_ON]->(Contractor)    (Penalty)-[:FOR_WORK]->(Work)
(Blacklisting {from,to})-[:OF]->(Contractor)
(Contractor)-[:JOINT_VENTURE_WITH]->(Contractor)
```

## Example queries

Awards after a penalty:

```cypher
MATCH (p:Penalty)-[:IMPOSED_ON]->(k:Contractor)<-[:TO]-(a:Award)
WHERE a.date > p.date AND a.date < p.date + duration({months: 12})
RETURN k.name, p.date, p.amount, a.date, a.value
ORDER BY a.value DESC
```

If the chosen database does not support `duration` arithmetic, precompute `p.window_end` at load time and compare dates directly.

Co-bidders sharing a director:

```cypher
MATCH (k1:Contractor)-[:SUBMITTED]->(:Bid)-[:ON]->(t:Tender)<-[:ON]-(:Bid)<-[:SUBMITTED]-(k2:Contractor)
WHERE k1.id < k2.id
MATCH (k1)-[:IS]->(:Company)<-[:DIRECTOR_OF]-(d:Director)-[:DIRECTOR_OF]->(:Company)<-[:IS]-(k2)
RETURN t.tender_no, k1.name, k2.name, d.name
```

Paths between a blacklisted firm and a recent winner, using a bounded traversal:

```cypher
MATCH (b:Contractor {id: $blacklisted}), (w:Contractor {id: $winner})
MATCH path = (b)-[:IS|DIRECTOR_OF|REGISTERED_AT*1..4]-(w)
RETURN path LIMIT 10
```

Rotation and concentration need community detection. HydraDB's README lists path and degree procedures only, so compute communities offline in Python (NetworkX, Louvain) and write `community_id` back onto nodes.

## Entity resolution, the core difficulty

The same firm appears as "M/s ABC Infra Pvt Ltd", "ABC Infrastructure" and "A.B.C. Infra (JV)".

1. Normalise: strip "M/s", legal suffixes, punctuation; transliterate Marathi.
2. Block: candidates sharing a normalised token set, a registration number, or an address.
3. Adjudicate: Claude compares each candidate pair with all known attributes and returns same, different or unsure, with a reason.
4. **Merge only on "same" with a hard identifier** (registration number, tax id) or after human approval. "Unsure" pairs get a `POSSIBLY_SAME_AS` edge that is displayed as such and never used to raise a flag on its own.
5. Never merge natural persons on name alone. Two directors called "R. Shah" stay separate until a director identification number matches.

## Implementation plan

| Phase | Work | Done when |
|---|---|---|
| 1. Award corpus | Extract Awards, Contractors and values from committee resolutions and the concretisation dashboard | 200+ awards loaded |
| 2. Penalty corpus | Extract Penalty and Blacklisting events from BMC press notes and news, with dates and amounts | Each event has an official or reported source |
| 3. Entity resolution | Pipeline above with a review screen | Reviewed contractor list for the demo scope |
| 4. Company layer | Add Company, Director, Address for the top 30 contractors by value, from public company records | Manual for the hackathon; automate later |
| 5. Flag engine | One query per flag, results stored as `RedFlag` nodes linked to their evidence | Flags reproducible; each has an evidence bundle |
| 6. UI | Profile page, flag list with filters, network view | Demo script runs |
| 7. Legal pass | Lawyer reviews every label and sentence on screen | Sign-off before anything public |

Bid-level data (who bid and lost) is often not public. If it is unavailable, drop the flags that need it (shared identity among co-bidders, single bidder, rotation) and say so. The award-after-penalty and reappearing-director flags need only award and penalty data.

## Publication rules

These are requirements, not suggestions.

- The interface says "pattern worth checking", never "fraud", "corrupt" or "cartel".
- Every flag opens to the records behind it. No flag without at least one official-tier source.
- Before public release, a named contractor is given the chance to respond, and the response is shown beside the flag.
- Access to the network view is limited to registered researchers and journalists at first; the public sees contractor profiles and penalties from official sources.
- Officials appear by post, not by name, unless named in an official order.

## Demo script

1. Open a contractor profile: contracts, wards, penalties, all sourced.
2. Show the "award after penalty" list. Open one and walk through the two source documents.
3. Network view: two firms linked through a shared director, one of them barred from tendering.
4. State plainly what the tool does not claim, and show the right-of-reply field.

For the hackathon demo, consider anonymising contractor names on screen (Contractor A, B, C) unless every displayed fact has been checked by the team's lawyer.

## Success measures

- Entity resolution precision on a hand-checked sample (target above 95%; a false merge is the worst failure).
- Share of flags a domain expert judges worth a follow-up question.
- One finding a journalist or official on the judging panel did not already know.

## Why this is roadmap, not day-one

High data difficulty, high legal exposure, and its users are specialists. It becomes much stronger once Paisa Trail has built the award data it depends on. Pitch it as phase two.
