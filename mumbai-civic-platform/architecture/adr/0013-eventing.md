# ADR 0013: SQS and EventBridge for events and schedules

**Status:** Accepted · 15 November 2026

## Options

| Option | For | Against |
|---|---|---|
| **SQS queues with dead-letter queues; EventBridge Scheduler and rules** | Serverless, cheap, simple back-pressure and retries | No replay of history beyond retention |
| Amazon MSK or self-run Kafka | Replayable log, high throughput | A cluster for a workload of a few thousand events a day |
| SNS only | Simple fan-out | No back-pressure |

## Decision

One queue per kind of work: new documents, scheduled runs, residents' messages, rebuild jobs. Each has a dead-letter queue with an alarm. EventBridge Scheduler creates the scheduled messages. Replay is not needed from the bus because the ledger on S3 is the replayable history ([ADR 0001](0001-facts-ledger-as-system-of-record.md)).
