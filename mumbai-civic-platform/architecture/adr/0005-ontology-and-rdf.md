# ADR 0005: Ontology in Turtle and SHACL, enforced in the pipeline; RDF published as files

**Status:** Accepted · 15 November 2026

## Context

The platform needs a formal ontology for consistency and for others to reuse, and wants to publish linked open data. The serving store is a property graph.

## Options

| Option | For | Against |
|---|---|---|
| RDF triple store as the primary store (Neptune SPARQL, Jena Fuseki, Oxigraph) | Native ontology, reasoning and validation | Path-heavy application queries are harder; fewer developers know SPARQL; two query languages in the application |
| Both models live in Neptune | One managed service | Neptune keeps RDF and property graph data separately, so everything is loaded and kept in step twice |
| **Ontology and shapes as files; validation in the loader; property graph for serving; RDF generated as an export** | Ontology discipline without a reasoner in the serving path; one query language in the application; linked data still published | No live inference; SPARQL users query dumps or a later endpoint |

## Decision

The ontology (OWL in Turtle), SHACL shapes and SKOS glossary live in git. A build step generates the extraction record schema and the loader's whitelist from them. The loader validates each batch with pySHACL before it reaches the ledger. Each release exports the official-tier graph as Turtle to S3 for download.

A live SPARQL endpoint (Oxigraph on Fargate, loaded from the export) is added only when someone asks for one.

## Consequences

- Anything that would be inferred is materialised by the loader as explicit facts marked `derived`.
- Ontology changes go through the evaluation gate and bump a version recorded on every fact.
