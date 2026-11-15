# ADR 0007: Hybrid search in Postgres first; OpenSearch when measurements call for it

**Status:** Accepted · 15 November 2026

## Context

Search must find exact identifiers and names (tender numbers, road names in two scripts), answer everyday-language questions across three languages, filter by ward and by access tier, and return passages linked to graph nodes so retrieval can move into the graph. Most residents' questions never reach open-ended retrieval; they are routed to named views.

## Options

| Option | For | Against |
|---|---|---|
| **Postgres: full-text, pgvector, PostGIS** | Already in the stack; one query can combine text rank, vector distance, geography and tier; no new service | Text relevance tuning and language analysis are basic; vector search slows at very large scale |
| Amazon OpenSearch Service, managed domain | Strong text relevance, language analysers, facets, hybrid text and vector scoring; proven at scale | A cluster to size and pay for continuously; another store to keep in step |
| OpenSearch Serverless | No cluster sizing | A capacity floor that is paid when idle; less control |
| Bedrock Knowledge Bases, optionally with graph retrieval on Neptune Analytics | Quick managed retrieval pipeline | Chunking, tier filtering and citation behaviour are harder to control; our chunks must carry graph node ids and page-level provenance; ties retrieval to Bedrock |
| Amazon S3 Vectors | Very low-cost vector storage at large scale | Vectors only; no text search; regional availability to confirm |
| Amazon Kendra | Managed enterprise search | Cost; limited control over ranking and languages |
| Self-hosted Qdrant, Weaviate or Elasticsearch | Capable, open | Another cluster for a small team |

## Decision

Start with hybrid search inside Aurora PostgreSQL: full-text over original script and transliteration, vector search with pgvector, merged by reciprocal rank, filtered by geography and tier in the same query. Put retrieval behind one interface.

Move text and vector search to an OpenSearch Service domain when any of these is measured: relevance on the Marathi evaluation set stays below target after tuning; query latency exceeds target; the vector table outgrows comfortable Postgres sizes. Consider S3 Vectors as the store for older, rarely queried vectors.

Bedrock Knowledge Bases is not used for the main path. It is acceptable for a throwaway demo.

## Consequences

- Marathi and Hindi tokenisation in Postgres is simple; transliteration and the glossary carry much of the load. This is the most likely reason to move.
- Chunking follows document structure and every chunk stores document, page and node ids.

## To confirm

Language analysis options in OpenSearch for Marathi; S3 Vectors availability in Mumbai.
