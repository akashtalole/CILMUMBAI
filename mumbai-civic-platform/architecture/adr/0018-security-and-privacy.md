# ADR 0018: Security and privacy baseline

**Status:** Accepted · 15 November 2026

## Decision

| Area | Rule |
|---|---|
| Network | Databases and services in private subnets; only CloudFront and the load balancer are public; security groups allow service-to-store paths only |
| Identity | One IAM role per service with least privilege; no long-lived keys; SigV4 to Claude; people sign in through IAM Identity Center |
| Secrets | Secrets Manager; nothing secret in agent sandboxes, memory stores, prompts or logs |
| Encryption | KMS at rest for S3, Aurora and the graph; TLS everywhere |
| Edge | WAF managed rules, rate limits per address and per key |
| Untrusted input | Documents and messages are data; agents that read them cannot write, publish or reach the network; outputs are validated in code |
| Personal data | No private individuals stored; officials by post; faces, number plates, phone numbers and addresses removed at intake; contributors can delete their data |
| Integrity | Archive bucket versioned with object lock; ledger append-only; releases and corrections logged with approver |
| Detection | CloudTrail, GuardDuty and Security Hub in every account; alarms on unusual query volume and on dead-letter queues |
| Supply chain | Pinned dependencies and image scanning in CI; agent definitions changed only through reviewed pull requests |

## Consequences

- Redaction runs before storage, so originals of residents' images are not kept.
- A security review is part of the move from the lean to the standard profile.
