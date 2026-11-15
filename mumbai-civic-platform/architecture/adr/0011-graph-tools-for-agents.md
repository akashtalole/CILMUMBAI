# ADR 0011: Agents reach the graph through tools the worker answers; MCP only for the public data service

**Status:** Accepted · 15 November 2026

## Context

Agents need read access to the graph. Managed Agents cloud sandboxes run outside our VPC. The graph database should have no public address.

## Options

| Option | For | Against |
|---|---|---|
| Host an MCP server on a public address and attach it to agents | Sessions run with no client attached; standard protocol | A public, authenticated doorway into the query layer for our own agents; credentials in a vault; more attack surface |
| Self-hosted sandboxes inside the VPC | Tools run next to the data | More to operate; cannot attach memory stores on Claude Platform on AWS |
| **Custom tools: the session asks, the worker answers from inside the VPC** | Graph and query layer stay private; tier and rate limits enforced in our code; nothing new exposed | A worker must be attached for the life of each session; unattended scheduled deployments cannot be used |
| Give agents a database snapshot as files | No tools at all | Stale; large; no tier filtering |

## Decision

Agents get custom tools. The worker holds the session's event stream and answers each call by querying the api inside the VPC, with the tier of the user the session acts for. Intake agents get no graph tools at all; they receive an export of known entities as a file.

A separate, read-only MCP server is published for outside assistants and builders. It exposes only public-tier named views and is rate limited. Our own agents do not use it.

## Consequences

- Sessions are bound to a running worker, which fits [ADR 0010](0010-workflow-orchestration.md).
- Tool answers are logged with the session, the tier and the facts returned.
- If unattended sessions are ever needed, the public MCP path can be extended with authentication instead of redesigning.
