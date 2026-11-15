# ADR 0001: The document archive and facts ledger on S3 are the system of record

**Status:** Accepted · 15 November 2026

## Context

The platform holds the same knowledge in several stores: a graph, a text index, a vector index, metric tables. Any of them may need to be replaced as the project grows or as a product proves unsuitable. Extraction prompts will also improve, and old documents will need re-reading.

## Options

| Option | For | Against |
|---|---|---|
| Graph database is the record | One place to look | Engine choice becomes irreversible; backups and migrations are critical; re-extraction means editing live data |
| Relational database is the record, graph derived | Mature tooling | Still couples truth to one engine; awkward for document-shaped facts |
| **Immutable archive plus append-only facts files on S3; every store is a projection** | Any store can be rebuilt or swapped; cheap, durable; full history for free; re-extraction is a new batch | A rebuild step is needed; consistency across projections is eventual |

## Decision

Two S3 datasets are the record. The archive holds every source document unchanged, addressed by content hash, with versioning and object lock. The facts ledger holds validated facts as append-only JSON lines, partitioned by graph and date, each carrying source, page, quote, tier, extractor version and ontology version. The graph, the search indexes and the metric tables are built from the ledger by the loader and can be dropped and rebuilt.

## Consequences

- The graph engine in [ADR 0004](0004-graph-database.md) can change without data loss.
- Corrections are new ledger entries that supersede old ones; nothing is edited in place.
- A full rebuild must be scripted, timed and rehearsed ([ADR 0022](0022-backup-and-rebuild.md)).
- Readers may briefly see a projection that lags the ledger; the loader records the last batch applied to each store.

## Revisit when

A rebuild takes longer than the service can tolerate being stale.
