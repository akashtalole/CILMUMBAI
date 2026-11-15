# ADR 0004: Graph database

**Status:** Accepted for the two profiles; HydraDB on trial · 15 November 2026
**Changes:** the earlier plan named HydraDB as primary. For hosting on AWS this record makes it a trial candidate.

## Context

The graph serves multi-hop reads over a few million nodes and edges. Writes come only from the loader, in batches. Because of [ADR 0001](0001-facts-ledger-as-system-of-record.md) the graph is a rebuildable projection, so durability features matter less than usual and operating effort and fixed cost matter more. All access goes through one repository layer over Bolt, using a common openCypher subset with no vendor procedures.

## Options

| Option | Model and query | For | Against |
|---|---|---|---|
| **Amazon Neptune Database, Serverless** | Property graph (openCypher, Gremlin) and RDF (SPARQL) | Managed, multi-zone, IAM, backups; openCypher over Bolt works with standard drivers; scales with load | A capacity floor that is paid when idle; openCypher is a subset without APOC; no built-in vector index; text search through a separate OpenSearch integration; property graph and RDF data are separate stores |
| Amazon Neptune Analytics | Property graph, openCypher, in memory | Vector search and graph algorithms built in; pairs with Bedrock's graph retrieval | Provisioned capacity; aimed at analysis, not as the serving store |
| **Neo4j Community, self-managed on one instance** | Property graph, full Cypher | Richest Cypher; vector and full-text indexes; RDF import plugin; lowest fixed cost at small scale; identical to the laptop setup | Single node, no clustering or online backup in the community edition; GPLv3; we patch and monitor it |
| Neo4j Aura through AWS Marketplace | As above, managed | No operations | Cost; data sits in the vendor's account |
| HydraDB on S3 with stateless nodes on Fargate | Property graph, openCypher subset, Bolt | Object storage is the source of truth, which suits S3 and low idle cost; open core | Version 0.3; few independent evaluations; Cypher coverage must be checked query by query; Elastic License 2.0; no text or vector index |
| Memgraph, FalkorDB | Property graph, Cypher, in memory | Fast | Source-available licences; memory-bound; self-managed |
| Kuzu, embedded | Property graph | No server at all; could sit inside the api task | Community-maintained; single writer; less suited to a shared service |

## Decision

- **Standard profile:** Neptune Database Serverless. A two-person team should not run a database cluster, and Bolt support keeps the code unchanged.
- **Lean profile and local development:** Neo4j Community on one instance, rebuilt from the ledger if lost.
- **HydraDB:** trial. Deploy beside the chosen engine, load from the same ledger, and run the competency queries and a soak test. Adopt it for the lean profile if it passes; its storage model is the best fit for a low-traffic public dataset on S3.
- **Neptune Analytics:** not now. Add it later, loaded from the same ledger, if graph algorithms (community detection for the contractor graph) are needed at scale.

Vector and text search stay outside the graph in every case ([ADR 0007](0007-search.md)), so the graph engines are compared on traversal alone.

## Consequences

- Queries must stay within the subset all three engines accept. A test suite runs the named views against each.
- Date arithmetic, `MERGE` behaviour and variable-length paths are the known places engines differ; the loader precomputes derived dates so queries compare plain values.
- Community detection runs offline in Python and writes results back, whichever engine is used.

## To confirm

- Neptune Serverless's minimum capacity and whether it can pause when idle; price both profiles.
- Which of the ten competency queries each engine rejects.

## Revisit when

HydraDB passes its trial, or the Neptune floor proves too costly for the traffic.
