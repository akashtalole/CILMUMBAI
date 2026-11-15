# ADR 0006: Aurora PostgreSQL Serverless v2 for relational, spatial and operational data

**Status:** Accepted · 15 November 2026

## Context

Besides the graph, the platform needs geometry (wards, roads, plots), workflow checkpoints, review queues, accounts and subscriptions, computed metrics, a document registry, and, at first, search ([ADR 0007](0007-search.md)).

## Options

| Option | For | Against |
|---|---|---|
| **Aurora PostgreSQL Serverless v2** | PostGIS, full-text and pgvector in one managed database; scales with load and, where supported, pauses when idle; multi-zone; LangGraph has a Postgres checkpointer | Costs more per unit than plain RDS when busy; cold start after a pause |
| RDS for PostgreSQL | Simple, predictable price, same extensions | Fixed instance size; no pause |
| Postgres on an instance or in a container | Cheapest | We run backups, patching and failover |
| DynamoDB for operational data, separate spatial store | Truly serverless | No spatial or text search; more moving parts; awkward for review queues and joins |

## Decision

One Aurora PostgreSQL Serverless v2 cluster with PostGIS and pgvector, separate schemas per concern. The lean profile runs it at the lowest setting; the standard profile adds a reader.

## Consequences

- One database to secure, back up and monitor.
- Search and workflow state share a cluster at first; split them if either starves the other.

## To confirm

Pausing to zero capacity and extension versions in Mumbai.
