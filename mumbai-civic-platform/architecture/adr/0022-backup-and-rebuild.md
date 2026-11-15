# ADR 0022: Protect the archive and the ledger; rebuild everything else

**Status:** Accepted · 15 November 2026

## Decision

| Data | Protection |
|---|---|
| Document archive | S3 versioning and object lock; replication to a second region in the standard profile |
| Facts ledger | S3 versioning; replication in the standard profile |
| Accounts, subscriptions, reviews, workflow state | Aurora automated backups and point-in-time recovery |
| Graph, text index, vector index, metric tables | Not backed up as primary protection; rebuilt from the ledger by a scripted job. Snapshots kept only to speed recovery. |
| Ontology, rules, agents, prompts, rubrics, infrastructure | Git |

A full rebuild into an empty environment is rehearsed before launch and after any change of engine. Its duration is the recovery time for the projections and is recorded.

## Consequences

- Losing the graph database is an inconvenience, not a loss of knowledge.
- The data the platform cannot regenerate is small: accounts, review decisions and residents' contributions. That is where backup attention goes.
