# ADR 0017: Store everything in Mumbai (ap-south-1)

**Status:** Accepted; one legal question open · 15 November 2026

## Context

Users are in Mumbai. Most data is published civic documents. Some is residents' contributions, which are personal data under the Digital Personal Data Protection Act. Model inference may run outside India.

## Decision

All stores and services run in ap-south-1. Residents' messages and images are redacted before storage and before any model call, so that what leaves the region for inference is the question and public facts, not identity. Contributors' account data never goes to a model.

## Consequences

- Latency to users is low.
- Some AWS features arrive later in Mumbai than elsewhere; each ADR lists what to confirm.
- Model inference location is set by the Claude offering, not by this platform.

## To confirm

- With a lawyer: whether sending redacted residents' text for processing outside India needs notice or consent wording.
- Which region serves Claude Platform on AWS requests and what inference geography options apply.
