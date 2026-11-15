# ADR 0002: Reach Claude through Claude Platform on AWS

**Status:** Accepted, subject to one confirmation · 15 November 2026

## Context

The platform uses Claude models, the Message Batches API for overnight extraction, the Files API, and Managed Agents with multi-agent rosters, outcomes and memory stores. Hosting is on AWS, and the host organisation will want one bill and IAM-based access control.

## Options

| Option | For | Against |
|---|---|---|
| Amazon Bedrock | AWS-operated; familiar to AWS teams; own batch and guardrail features | Per Anthropic's documentation it does not offer Managed Agents, the Message Batches API or the Files API; feature releases follow AWS's schedule; model ids carry a prefix |
| Anthropic API direct | Full feature set; simplest to start | Separate billing and credentials; a long-lived API key to manage |
| **Claude Platform on AWS** | Operated by Anthropic with the same API as its own platform, including Managed Agents (beta), batches and files; SigV4 and IAM; billing through AWS Marketplace | Newer offering; an unattended session must be re-authenticated after six hours; sessions on self-hosted sandboxes cannot attach memory stores |

## Decision

Use Claude Platform on AWS. Services authenticate with their IAM task roles; no API key is stored. The client code selects the AWS client when `ANTHROPIC_AWS_WORKSPACE_ID` is set and the standard client otherwise, so a laptop with an ordinary key and a Fargate task with a role run the same code.

For the hackathon day, the Anthropic API with event credits is fine; nothing in the code changes.

## Consequences

- Agent sessions must finish, or receive an event, within six hours. Intake batches are sized accordingly and long jobs are split by the workflow.
- Cloud sandboxes are used so memory stores remain available ([ADR 0003](0003-agent-runtime.md)).
- If the platform ever had to move to Bedrock, the agent layer would need rebuilding on a different runtime. The facts ledger, graph and search would be unaffected.

## To confirm

- That the offering can be subscribed to and called from an account whose workloads run in Mumbai, and which region the endpoint is in.
- IAM actions needed by each service.
