# ADR 0019: CloudWatch and OpenTelemetry for operations; an evaluation gate for behaviour

**Status:** Accepted · 15 November 2026

## Options

| Concern | Option | For | Against |
|---|---|---|---|
| Metrics, logs, traces | **CloudWatch with the AWS OpenTelemetry distribution** | Managed, in-account, enough for four services | Dashboards are plain |
| | Self-run Grafana, Prometheus, Loki | Rich, open | More to operate |
| Model and agent traces | **Console session viewer, plus session and run records in our registry** | No setup; every thread and tool call visible | Lives outside our dashboards |
| | Langfuse, self-hosted | Open; prompt and cost analytics | Another service and database |
| | OpenTelemetry export of API spans | Standard; joins with service traces | Beta on Claude Platform on AWS |

## Decision

CloudWatch for service metrics, logs and alarms, with OpenTelemetry traces from the services. For agents, record each session's id, agent versions, cost and outcome in the registry and link to the Console trace. Add Langfuse only if prompt-level analytics become a daily need.

Behaviour is guarded by the evaluation gate: every change to an agent, prompt, rule, ontology or retrieval setting runs the extraction, question and refusal sets in CI against staging, reported by route and by language, and needs an owner's approval to reach production.

Dashboards to build first: source freshness; quote-check pass rate; held-queue size; answers failing the citation check; cost per desk per day; evaluation trend.
