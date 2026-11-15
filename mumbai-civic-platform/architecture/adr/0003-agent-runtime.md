# ADR 0003: Run agents on Claude Managed Agents with cloud sandboxes

**Status:** Accepted · 15 November 2026

## Context

Six desks of agents read documents, verify, audit, challenge and draft. They need a sandbox with a filesystem, delegation between agents, rubric-graded outcomes, persistent memory, and versioned configurations.

## Options

| Option | For | Against |
|---|---|---|
| **Claude Managed Agents, cloud sandboxes** | Anthropic runs the loop and the sandbox; rosters, background workflow runs, outcomes, memory stores, versioned agents and session budgets are built in; agent definitions already written | Beta; sandbox runs outside our VPC; platform dependency |
| Managed Agents with self-hosted sandboxes in our VPC | Tools execute inside our network | More to operate; on Claude Platform on AWS such sessions cannot attach memory stores |
| Amazon Bedrock AgentCore | AWS-native runtime, identity and memory | A different agent model and API; the existing agent files, outcomes and roster design would not carry over; depends on Bedrock's Claude feature set |
| Own agent loop on Fargate (Messages API with tools, or the Claude Agent SDK) | Full control; no beta dependency | We would build and maintain delegation, grading, memory, sandboxing and versioning ourselves |
| LangGraph agents calling the Messages API | One framework for everything | Same build burden for sandbox and delegation; mixes deterministic orchestration with agentic work |

## Decision

Managed Agents with cloud sandboxes. Sandboxes have no outbound hosts and the web tools are off. Documents enter as mounted files and results leave as output files. Agent, environment and memory definitions live as files in git and are applied with the `ant` CLI from CI.

## Consequences

- The sandbox never needs to reach our network, which is what allows the graph to stay private ([ADR 0011](0011-graph-tools-for-agents.md)).
- Only public documents and redacted text are mounted into sandboxes.
- A fallback exists in principle (own loop on Fargate) but is not built. The agent prompts, rubrics and tool definitions are plain files and would carry over.

## Revisit when

A requirement arises to process material that may not leave the VPC, or the beta terms change.
