# ADR 0020: Terraform or OpenTofu; three accounts

**Status:** Accepted · 15 November 2026

## Options

| Option | For | Against |
|---|---|---|
| **Terraform or OpenTofu** | Widely known among volunteers; open; explicit plans to review | State to manage; more verbose |
| AWS CDK | Real programming languages; high-level constructs | Ties the infrastructure code to AWS and to one language |
| CloudFormation directly | Native | Verbose; slower to write |

## Decision

Infrastructure in Terraform, compatible with OpenTofu, with remote state in S3. Three accounts under one organisation for the standard profile: development, staging, production. The lean profile uses one account with two stages. Agent, environment and memory definitions are applied by the `ant` CLI from the same pipeline, with a dry-run plan on pull requests and apply on merge.

## Consequences

- Anyone joining can read a plan before it runs.
- The host organisation owns the accounts and the state bucket.
