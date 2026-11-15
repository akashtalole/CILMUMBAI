# ADR 0012: ECS Fargate and Lambda; no Kubernetes

**Status:** Accepted · 15 November 2026

## Options

| Option | For | Against |
|---|---|---|
| **ECS on Fargate** | No servers or cluster to manage; per-task IAM roles; runs long-lived workers and streams; Spot for interruptible work | Dearer per unit than instances; slower cold start than Lambda |
| AWS Lambda | Scales to zero; ideal for small event handlers | Fifteen-minute limit; unsuited to holding agent event streams or long workflows |
| Amazon EKS | Portable; rich ecosystem | A control plane and add-ons to run; more than a small team should carry |
| EC2 instances | Cheapest at steady load | Patching and scaling by hand |
| App Runner | Simplest for a web service | Less control over networking and background workers |

## Decision

Four Fargate services: `api`, `worker`, `loader`, `public-mcp`. Lambda for small glue: S3 event handlers, WhatsApp webhook intake, scheduled checks. Bulk parsing and re-embedding run as Fargate tasks on Spot, started from a queue.

## Consequences

- The worker holds long connections, so it is deployed with graceful draining and resumes from checkpoints.
- Container images are the unit of release for everything except the static site.
