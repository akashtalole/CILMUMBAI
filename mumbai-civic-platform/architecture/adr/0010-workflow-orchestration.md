# ADR 0010: LangGraph on Fargate for workflows; EventBridge Scheduler for triggers

**Status:** Accepted · 15 November 2026

## Context

Eight workflows order the work between agent sessions, code steps and human sign-offs. Runs may wait days for a reviewer. One workflow already exists as a LangGraph state graph.

## Options

| Option | For | Against |
|---|---|---|
| **LangGraph in a worker service, Postgres checkpointer** | Already written; pauses and resumes are first-class; fan-out per ward; plain Python next to the agent client; open source | We host the worker; less visual tooling than a managed service |
| AWS Step Functions | Managed, durable, visual, strong retries; waits for callbacks cost nothing | Workflow logic moves into a separate definition language; long agent sessions need callback plumbing; a second place for logic |
| Airflow on MWAA, or Dagster | Good for scheduled data pipelines | Heavy and always-on; poor fit for human pauses and per-request flows |
| Managed Agents scheduled deployments | No scheduler to run | Starts sessions only; cannot run code steps or gates; no one answers custom tool calls |
| Temporal | Durable execution, strong guarantees | A cluster or a paid service; more than this needs |

## Decision

LangGraph runs in the `worker` service on Fargate with checkpoints in Aurora PostgreSQL. EventBridge Scheduler and S3 events put messages on SQS; the worker starts or resumes workflows from them. Agent sessions are started by the worker, not by Managed Agents deployments, so every run is launched, logged and authorised from our account and the worker is present to answer tool calls.

Step Functions is not used for workflow logic. It may be used later as a thin wrapper if an auditor wants a managed execution history.

## Consequences

- The worker must survive restarts mid-run: workflows resume from the checkpoint, and nodes with side effects are written to be safe to repeat.
- Human gates are rows in a review table; the review screen resumes the run.
- The SQLite checkpointer in the starter code is replaced by the Postgres one in deployment.
