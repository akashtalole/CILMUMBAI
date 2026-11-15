# Architecture on AWS

Design and decision records for hosting Mumbai Nagar Graph on AWS.

| File | Contents |
|---|---|
| [design.md](design.md) | The architecture: requirements, components, data flow, network, security, two deployment profiles, runtime sequences, open items |
| [adr/](adr/) | Twenty-two architecture decision records, each with the options considered from AWS and open source, the decision, its consequences and when to revisit it |

## Decisions at a glance

| # | Decision | Chosen | Main alternatives weighed |
|---|---|---|---|
| [0001](adr/0001-facts-ledger-as-system-of-record.md) | System of record | Document archive and validated facts on S3; graph and indexes are rebuildable projections | Graph database as the record |
| [0002](adr/0002-claude-access-on-aws.md) | Access to Claude | Claude Platform on AWS | Amazon Bedrock; Anthropic API direct |
| [0003](adr/0003-agent-runtime.md) | Agent runtime | Claude Managed Agents, cloud sandboxes | Bedrock AgentCore; self-hosted agent loop on Fargate; self-hosted sandboxes |
| [0004](adr/0004-graph-database.md) | Graph database | Neptune Database Serverless (standard profile); Neo4j Community (lean profile); HydraDB on trial | Neptune Analytics; Neo4j Aura; Memgraph; FalkorDB; Kuzu |
| [0005](adr/0005-ontology-and-rdf.md) | Ontology and linked data | Turtle and SHACL in the pipeline; RDF published as dumps | Neptune SPARQL; Jena Fuseki; Oxigraph as a live endpoint |
| [0006](adr/0006-relational-and-spatial-store.md) | Relational and spatial | Aurora PostgreSQL Serverless v2 with PostGIS | RDS PostgreSQL; DynamoDB; self-hosted Postgres |
| [0007](adr/0007-search.md) | Search | Hybrid text and vector in Postgres first; OpenSearch Service when measured need | OpenSearch Serverless; Bedrock Knowledge Bases; S3 Vectors; Kendra |
| [0008](adr/0008-embedding-model.md) | Embeddings | A managed multilingual model behind an interface, chosen by test on Marathi and Hindi | Self-hosted open models |
| [0009](adr/0009-document-parsing-and-ocr.md) | Parsing and OCR | Text layer first, Claude vision for scans, Tesseract to pre-screen | Amazon Textract |
| [0010](adr/0010-workflow-orchestration.md) | Workflows | LangGraph on Fargate with a Postgres checkpointer; EventBridge Scheduler for triggers | Step Functions; Airflow on MWAA; Managed Agents scheduled deployments |
| [0011](adr/0011-graph-tools-for-agents.md) | How agents reach the graph | Custom tools answered privately by the worker; MCP server only for the public data service | Public MCP server for agents; self-hosted sandboxes in the VPC |
| [0012](adr/0012-compute.md) | Compute | ECS Fargate and Lambda | EKS; EC2; App Runner |
| [0013](adr/0013-eventing.md) | Eventing | SQS and EventBridge | MSK (Kafka); SNS only |
| [0014](adr/0014-api-identity-and-access.md) | API and identity | Application Load Balancer and CloudFront; Cognito for sign-in; tiers enforced in the query layer | API Gateway; Keycloak |
| [0015](adr/0015-front-end-and-maps.md) | Front end and maps | Static site on S3 and CloudFront; MapLibre with PMTiles | Amplify Hosting; Amazon Location Service |
| [0016](adr/0016-resident-channels.md) | Resident channels | WhatsApp through AWS End User Messaging Social; Transcribe for voice notes | Meta Cloud API direct; Twilio; open speech models |
| [0017](adr/0017-region-and-data-residency.md) | Region | Mumbai (ap-south-1) for everything the platform stores | Other regions |
| [0018](adr/0018-security-and-privacy.md) | Security and privacy | Private data plane, least-privilege roles, encryption, redaction at intake | |
| [0019](adr/0019-observability-and-evaluation.md) | Observability | CloudWatch and OpenTelemetry; evaluation gate in CI | Langfuse; Grafana stack |
| [0020](adr/0020-infrastructure-as-code.md) | Infrastructure as code | Terraform or OpenTofu; three accounts | AWS CDK; CloudFormation |
| [0021](adr/0021-cost-posture.md) | Cost posture | Two profiles: lean for the pilot, standard for the service | One always-on profile |
| [0022](adr/0022-backup-and-rebuild.md) | Backup and recovery | Protect the archive and facts; rebuild everything else | Back up every store equally |

## What has and has not been verified

These records were written on 15 November 2026 without an AWS account to test in. Service facts come from AWS pages found by search and from general knowledge; each record lists what to confirm. In particular:

- **Confirmed by AWS pages found in search:** Neptune's openCypher endpoint works over Bolt and HTTPS; Neptune Analytics supports vector search; S3 Vectors is generally available; AWS End User Messaging Social has an endpoint in Mumbai; Amazon Transcribe lists Marathi for batch transcription.
- **Not confirmed:** Neptune Serverless's minimum capacity and whether it can pause; Aurora Serverless v2 pausing to zero in Mumbai; whether Textract reads Devanagari; whether Claude Platform on AWS is offered from the Mumbai region; any price.
- **From Anthropic's documentation as bundled with this tool:** Claude Platform on AWS has the same API as Anthropic's own, including Managed Agents in beta; Amazon Bedrock does not offer Managed Agents.

No prices are quoted. Price each option in the AWS calculator for Mumbai before committing.

## Sources

- [Amazon Neptune FAQs](https://aws.amazon.com/neptune/faqs/)
- [Migrating from Neo4j to Neptune](https://docs.amazonaws.cn/en_us/neptune/latest/userguide/migrating-from-neo4j-general.html)
- [Neptune Analytics smaller capacity units](https://aws.amazon.com/about-aws/whats-new/2024/07/amazon-neptune-analytics-smaller-capacity-units)
- [Introducing Amazon Neptune Analytics](https://aws.amazon.com/pt/blogs/aws/introducing-amazon-neptune-analytics-a-high-performance-graph-analytics/)
- [Amazon S3 Vectors generally available](https://aws.amazon.com/about-aws/whats-new/2025/12/amazon-s3-vectors-generally-available)
- [Amazon Transcribe supported languages](https://docs.aws.amazon.com/transcribe/latest/dg/supported-languages.html)
- [Amazon Polly available voices](https://docs.aws.amazon.com/polly/latest/dg/available-voices.html)
- [What is AWS End User Messaging Social](https://docs.aws.amazon.com/social-messaging/latest/userguide/what-is-service.html)
- [HydraDB README](https://raw.githubusercontent.com/hydra-db/hydradb/main/README.md)
