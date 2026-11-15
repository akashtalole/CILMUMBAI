# ADR 0021: Two profiles, lean and standard

**Status:** Accepted · 15 November 2026

## Context

Funding is uncertain. The service must be able to idle cheaply for months and still be correct, and to grow when a pilot succeeds. No prices are quoted here; price both profiles for Mumbai before choosing.

## Decision

Maintain two profiles from the same code ([design.md](../design.md), section 8). Start lean. Move to standard when a public launch or a formal pilot requires availability across zones.

Cost rules for both:

| Driver | Control |
|---|---|
| Extraction tokens | Smallest capable model for reading; batch API for backlogs; each document read once per extractor version |
| Audit and brief tokens | Session budgets; schedules weekly, not daily, unless a source changed |
| Answer tokens | Routing serves most questions from named views with no agent; pages pre-rendered |
| Always-on capacity | Prefer services that scale down or pause; in the lean profile, one small graph instance |
| Data transfer | Static content and tiles from CloudFront; exports as files |
| Fixed network cost | In the lean profile, one NAT path and gateway endpoints for S3 |

Measure spend by desk and by workflow in the first month, then set budgets and alarms.

## Revisit when

Idle cost of the lean profile exceeds what the host can sustain, or traffic makes pay-per-use dearer than fixed capacity.
