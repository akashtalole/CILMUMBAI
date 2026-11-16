# Deploy from AWS CloudShell (demo profile)

Scripts to put Aamcha Hishob on AWS from the browser, with nothing installed locally, and to take it down again. They are for the hackathon demo and for trying the platform. The production profile is [SPEC-013](../../../aamcha-hishob-specs/specs/SPEC-013-aws-lean-infrastructure.md): Terraform, Fargate and Aurora, deployed by CI.

| File | What it does |
|---|---|
| `deploy.sh` | Creates or updates the stack, stores the Claude key, installs the app at the current commit, and checks it from outside |
| `remote.sh` | Runs `hishob` or shell commands on the instance, signs access tokens, shows service status |
| `teardown.sh` | Deletes the stack; with `--delete-data`, also empties and deletes the buckets |
| `template.yaml` | The CloudFormation stack |
| `remote/` | What runs on the instance: install script, secrets loader, systemd services, `hishob` wrapper |

## What gets created

```
Internet ──HTTPS──▶ CloudFront ──HTTP, port 80, CloudFront addresses only──▶ EC2 instance (Ubuntu 24.04, t3.large)
                                                                               ├─ API (uvicorn) and workflow worker
                                                                               ├─ Postgres 16 + PostGIS   (127.0.0.1)
                                                                               └─ Neo4j 5 Community       (127.0.0.1)
                    S3: archive (versioning, object lock), data, released outputs   ◀── instance role
                    SQS: events, workflow (with dead-letter queue)                  ◀── instance role
                    Secrets Manager: token-signing secret, Claude key               ◀── instance role
```

All in `ap-south-1` (ADR 0017), whatever region the console shows. There is no SSH: the instance is reached through Session Manager, which is how the scripts install and run things on it.

| Choice | Why, for a demo |
|---|---|
| One instance, not Fargate | CloudShell cannot build container images. One instance holds both stores and the app, and is quick to create and delete |
| CloudFront in front | HTTPS without a domain or certificate; the instance accepts traffic only from CloudFront |
| Fixed Elastic IP | The CloudFront origin does not change if the instance is stopped and started |
| Claude key in Secrets Manager | ADR 0002 allows a key for the hackathon. Claude Platform on AWS with IAM roles needs its IAM actions confirmed first |
| Buckets kept on teardown | The archive is the system of record (ADR 0001); deleting it takes a separate, explicit step |
| Postgres and Neo4j on the instance's disk | Both can be rebuilt from the ledger in S3 (ADR 0022) |

## Before you start

- An AWS account and a user that can create CloudFormation stacks, IAM roles, EC2, S3, SQS, Secrets Manager, CloudFront and Systems Manager resources. An administrator role is simplest.
- A Claude API key, unless you only want the API without the agent desks.
- The repository in CloudShell. If it is private, clone it with a GitHub personal access token, or upload a zip through CloudShell's **Actions → Upload file**.

## Deploy

Open CloudShell from the AWS console (the `>_` icon), then:

```sh
git clone https://github.com/akashtalole/cilmumbai.git
cd cilmumbai/app/deploy/cloudshell
./deploy.sh
```

The first run takes about 20 minutes. Most of that time goes to CloudFront and installing packages. The script:

1. Creates the stack, or updates it.
2. Asks for the Claude key at a hidden prompt and stores it in Secrets Manager. The key is never written to a command line or left in a file.
3. Packs `app/` at the current commit (`git archive HEAD`) and uploads it to the data bucket.
4. Waits for the instance's set-up, then installs that release through Session Manager. The install migrates the database and starts the services.
5. Calls the API through CloudFront, once without a token and once with a signed reviewer token. It confirms in the API's log that the token's tier arrived.

Uncommitted changes are not deployed. Commit first, then run `./deploy.sh` again. Each run installs the new commit and keeps the last three releases on the instance.

| Option | Effect |
|---|---|
| `--apply-agents` | Also creates or updates the Hishob agents in the Claude account the key belongs to. Asks before doing it |
| `--set-key` | Replace the stored Claude key |
| `--no-key` | Do not ask for a key; the API works, the agent desks do not |
| `--instance-type t3.xlarge` | A bigger instance |
| `--stack NAME`, `--region R` | Another stack name or region |

## Use it

```sh
./remote.sh status                                        # services and recent log lines
./remote.sh hishob archive add <url> --publisher bmc --licence "<terms>"
./remote.sh hishob place import-wards <file-on-instance> --kind admin --name-property name --publisher datameet --licence "<terms>"
./remote.sh hishob graph apply
./remote.sh hishob audit run K/W --api http://127.0.0.1:80 --cap-usd 10
./remote.sh token reviewer acct_nair                      # a signed token for the API's Authorization header
./remote.sh sh 'journalctl -u hishob-worker -n 50 --no-pager'
./remote.sh session                                       # interactive shell, if the Session Manager plugin is present
```

The API is at the `ApiUrl` that `deploy.sh` prints. Its interactive documentation is at `/docs`. To start a workflow run, send a message to the workflow queue; the worker picks it up:

```sh
aws --region ap-south-1 sqs send-message --queue-url "$(aws --region ap-south-1 cloudformation describe-stacks \
  --stack-name aamcha-hishob-demo --query "Stacks[0].Outputs[?OutputKey=='WorkflowQueueUrl'].OutputValue" --output text)" \
  --message-body '{"workflow": "W1", "thread": "t1", "hashes": ["<sha256>"], "wards": ["K/W"]}'
./remote.sh hishob workflow status t1
./remote.sh hishob workflow resume t1 approve --reason "checked every case" --token "$(./remote.sh token reviewer acct_nair)"
```

## Tear down

```sh
./teardown.sh                 # delete the stack; keep the buckets
./teardown.sh --delete-data   # also delete the buckets and every object version in them
```

`teardown.sh` lists what it will delete and what it will keep, then asks you to type the stack name. `--delete-data` asks a second time and removes every version, including the archive's locked ones. That needs permission to bypass governance-mode retention (`s3:BypassGovernanceRetention`), which administrators have. It finds buckets left by an earlier teardown through their stack tag.

Teardown does not remove the agents created in the Claude account. Remove those in the Claude console. If the key was ever shared, revoke it there too.

## Cost

You pay while it exists, even when nobody uses it: instance hours, the 40 GiB disk, the public IPv4 address and Secrets Manager. You also pay by use for CloudFront, S3, SQS and Session Manager. Check the [AWS pricing calculator](https://calculator.aws/) for `ap-south-1` before leaving it running. Claude usage is billed separately, and each agent run has its own spending cap (`--cap-usd`). Run `./teardown.sh` when the demo is over.

## Not yet verified

These scripts have **not been run against a real AWS account**. Here is what has been checked:

- `cfn-lint` passes on the template and `shellcheck` passes on every script.
- `deploy.sh`, `remote.sh` and `teardown.sh` were run end to end against a stand-in for the AWS CLI. That covered the stack, key, bundle, install, smoke-check and teardown paths, including emptying a 1,500-version locked bucket in batches.
- The bundle installs with `uv sync --locked --no-dev`.
- Tokens signed by the scripts are accepted by the app.

Still to check on a real account:

- **CloudFront and the `Authorization` header.** The managed policies used (CachingDisabled, AllViewerExceptHostHeader) are expected to pass it to the API, and `deploy.sh` checks that they do. If it warns, access tiers do not work through CloudFront and the cache behaviour needs changing.
- **Ubuntu package names.** `postgresql-16-postgis-3` and `openjdk-21-jre-headless` on 24.04, and the Neo4j 5.26.0 download. If set-up fails, read `/var/log/hishob-bootstrap.log` with `./remote.sh sh 'tail -80 /var/log/hishob-bootstrap.log'`.
- **Instance size.** Neo4j, Postgres and the app fit in 8 GiB for the demo data; the heap and page cache are set to 1 GiB each.
- **Secrets on teardown.** CloudFormation may schedule the secrets for deletion with a recovery window rather than delete them at once. Their names are generated, so a new deployment does not collide with them.
