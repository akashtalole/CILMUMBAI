# SPEC-013: AWS infrastructure, lean profile

| | |
|---|---|
| Status | Draft |
| Milestone | M2 |
| Owner role | Platform engineer |
| Depends on | SPEC-001 to SPEC-012 |
| ADRs | 0002, 0006, 0012, 0014, 0017, 0018, 0020, 0021, 0022 |
| Personas served | All |

## 1. Problem and outcome

M1 runs on a laptop. A public service needs to run in the cloud, cheaply when idle, securely, and so that it can be rebuilt from its record.

When done, the lean profile from the architecture design runs in AWS Mumbai, defined in Terraform, deployed by CI, with the graph and indexes rebuilt from the S3 record at least once.

## 2. User stories

- As the host organisation, I want the service to cost little when quiet.
- As an engineer, I want to recreate the whole environment from code and S3.
- As a reviewer, I want sign-in to the review tools without shared passwords.

## 3. Requirements

| Id | Requirement |
|---|---|
| R1 | All resources shall be defined in Terraform (OpenTofu compatible) with remote state, and created only by CI. |
| R2 | All stores and services shall be in ap-south-1. |
| R3 | The archive bucket shall have versioning and object lock; the data bucket versioning; both encrypted with KMS. |
| R4 | Services (`api`, `worker`, `loader`) shall run on ECS Fargate in private subnets, each with its own task role granting least privilege. |
| R5 | Only CloudFront and the load balancer shall accept traffic from the internet; the graph and database shall have no public address. |
| R6 | Services shall call Claude through Claude Platform on AWS using their task roles, with no stored API key. |
| R7 | A rebuild job shall recreate the graph, geo tables and alerts state from the S3 ledger into empty stores. |
| R8 | Sign-in for contributor, researcher, official and reviewer tiers shall use Cognito groups mapped to tiers. |

## 4. Acceptance criteria

| Id | Given | When | Then | Verifies |
|---|---|---|---|---|
| AC1 | A clean account | CI applies Terraform | The environment is created with no manual console steps | R1 |
| AC2 | The environment | Resources are listed across regions | All data and services are in ap-south-1 | R2 |
| AC3 | The buckets | Their configuration is read | Versioning on both, object lock on archive, KMS encryption on both | R3 |
| AC4 | Each task role | Its policy is evaluated | `api` cannot write the graph; `loader` cannot start agent sessions; `worker` cannot write the archive | R4 |
| AC5 | The graph and database endpoints | Probed from the internet | Unreachable | R5 |
| AC6 | A deployed worker | It starts a citizen desk session | The call is SigV4-signed with its role; no API key exists in the environment or Secrets Manager | R6 |
| AC7 | An empty graph and database | The rebuild job runs | View tests (SPEC-006) pass and counts match the ledger | R7 |
| AC8 | Users in each Cognito group | They call the API | The API resolves the matching tier | R8 |

## 5. Interfaces and data contracts

```
app/infra/terraform/
  modules/{network, buckets, aurora, graph_neo4j, ecs_service, cognito, cloudfront, queues, observability}
  envs/lean/
```

The graph in the lean profile is Neo4j Community on one instance with snapshots; the standard profile (SPEC-030) swaps in Neptune.

## 6. Non-functional requirements

- Idle cost measured in the first month and reported; budget alarms set.
- A full rebuild of one ward completes in under 30 minutes.

## 7. Constitution

| Article | How this spec upholds it |
|---|---|
| C7 | Encryption, private subnets, no keys in sandboxes |
| C8 | R8: tiers from identity |
| C9 | R3, R7: protected record; rebuild from it |
| C12 | Fargate and managed services only, per ADRs |

## 8. Out of scope

Standard profile (SPEC-030). WhatsApp channel resources (SPEC-019). Cross-region replication.

## 9. Design notes

- Follow the lean column of `design.md` section 8. Confirm Claude Platform on AWS availability for this account before T6.
- The rebuild job is the recovery plan for everything except the archive, ledger and Aurora's own data.

## 10. Tasks

| Id | Task | Size | Depends on | Verifies |
|---|---|---|---|---|
| T1 | State bucket, CI role, Terraform skeleton | M | | AC1 |
| T2 | Network module | M | T1 | AC5 |
| T3 | Buckets with lock and KMS | S | T1 | AC3 |
| T4 | Aurora with PostGIS and pgvector | M | T2 | |
| T5 | Neo4j instance with snapshots | M | T2 | AC5 |
| T6 | ECS services, roles, load balancer, CloudFront | L | T2 to T5 | AC2, AC4, AC6 |
| T7 | Cognito groups and API tier mapping | M | T6 | AC8 |
| T8 | Rebuild job and timed rehearsal | M | T6 | AC7 |
| T9 | Budgets and alarms | S | T6 | |

## 11. Open questions

| Question | Owner | Assumption until answered |
|---|---|---|
| Claude Platform on AWS availability for an account in Mumbai | Platform engineer | Available; else the Anthropic API with a key in Secrets Manager |
| Host organisation that owns the account | Product lead | Team lead's account until decided |
