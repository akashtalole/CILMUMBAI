#!/bin/bash
# Deploy or update the Aamcha Hishob demo profile from AWS CloudShell.
#
#   git clone <this repository> && cd <repo>/app/deploy/cloudshell
#   ./deploy.sh                    # create or update the stack, set the Claude key, install the app
#   ./deploy.sh --apply-agents     # also create the agents in the Claude account (asks first)
#   ./deploy.sh --set-key          # replace the stored Claude key
#
# Options: --stack NAME (default aamcha-hishob-demo), --region R (default ap-south-1),
#          --instance-type T (default t3.large), --no-key (use no Claude key: agent desks will not run).
set -euo pipefail
here=$(cd "$(dirname "$0")" && pwd)
# shellcheck source=lib.sh
. "$here/lib.sh"

instance_type=t3.large apply_agents=0 set_key=0 no_key=0
while [ $# -gt 0 ]; do
  case $1 in
    --stack) STACK=$2; shift 2 ;;
    --region) REGION=$2; shift 2 ;;
    --instance-type) instance_type=$2; shift 2 ;;
    --apply-agents) apply_agents=1; shift ;;
    --set-key) set_key=1; shift ;;
    --no-key) no_key=1; shift ;;
    -h | --help) sed -n '2,12p' "$0"; exit 0 ;;
    *) die "unknown option $1 (see --help)" ;;
  esac
done
need aws jq git curl python3

repo=$(git -C "$here" rev-parse --show-toplevel) || die "run this from a clone of the repository"
sha=$(git -C "$repo" rev-parse --short=12 HEAD)
if [ -n "$(git -C "$repo" status --porcelain -- app)" ]; then
  warn "app/ has uncommitted changes; the deployment uses the last commit, $sha"
fi
account=$(aws_ sts get-caller-identity --query Account --output text) || die "no AWS credentials"
say "account $account, region $REGION, stack $STACK, commit $sha"

# ---- 1. the stack ----------------------------------------------------------------------------------------------
prefix_list=$(aws_ ec2 describe-managed-prefix-lists \
  --filters Name=prefix-list-name,Values=com.amazonaws.global.cloudfront.origin-facing \
  --query 'PrefixLists[0].PrefixListId' --output text)
[ "$prefix_list" != None ] || die "no CloudFront origin-facing prefix list in $REGION"

case $(stack_status) in
  *ROLLBACK_COMPLETE | *_FAILED) die "stack $STACK is in state $(stack_status); run ./teardown.sh first" ;;
esac
say "creating or updating the stack (first time: about 10 minutes, mostly CloudFront)"
aws_ cloudformation deploy --stack-name "$STACK" --template-file "$here/template.yaml" \
  --capabilities CAPABILITY_IAM --no-fail-on-empty-changeset \
  --parameter-overrides "CloudFrontPrefixListId=$prefix_list" "InstanceType=$instance_type" \
  --tags project=aamcha-hishob profile=demo

instance=$(output InstanceId)
data_bucket=$(output DataBucket)
api_url=$(output ApiUrl)
key_arn=$(output ClaudeKeySecretArn)
token_arn=$(output TokenSecretArn)

# ---- 2. the Claude key: typed at a hidden prompt, never on a command line or in a file that stays -----------------
current=$(aws_ secretsmanager get-secret-value --secret-id "$key_arn" --query SecretString --output text)
if [ "$no_key" = 0 ] && { [ "$current" = unset ] || [ "$set_key" = 1 ]; }; then
  [ -t 0 ] || die "the Claude key is not set; run ./deploy.sh in an interactive shell to enter it"
  read -rsp "Claude API key (input hidden; Enter to skip): " key
  echo
  if [ -n "$key" ]; then
    tmp=$(umask 077 && mktemp)
    trap 'rm -f "$tmp"' EXIT
    printf '%s' "$key" > "$tmp"
    unset key
    aws_ secretsmanager put-secret-value --secret-id "$key_arn" --secret-string "file://$tmp" >/dev/null
    rm -f "$tmp"
    say "key stored in Secrets Manager"
  else
    warn "no key stored: the API works, the agent desks will not"
  fi
fi

# ---- 3. the app: a bundle of app/ at this commit, installed through Session Manager ------------------------------
bundle="deploy/app-$sha.tar.gz"
say "uploading the app bundle to s3://$data_bucket/$bundle"
git -C "$repo" archive --format=tar.gz "HEAD" app | aws_ s3 cp - "s3://$data_bucket/$bundle" --only-show-errors

say "waiting for the instance to finish its set-up (first time: about 5 minutes)"
wait_for_ssm "$instance"
for _ in $(seq 1 60); do
  ssm_run "$instance" "test -f /var/lib/hishob/bootstrapped" 60 >/dev/null 2>&1 && break
  sleep 15
done
ssm_run "$instance" "test -f /var/lib/hishob/bootstrapped" 60 >/dev/null \
  || die "set-up did not finish; see /var/log/hishob-bootstrap.log with: ./remote.sh sh 'tail -50 /var/log/hishob-bootstrap.log'"

say "installing $sha on $instance"
release="/opt/hishob/releases/$sha"
ssm_run "$instance" "set -euo pipefail
mkdir -p $release
aws s3 cp s3://$data_bucket/$bundle - --only-show-errors | tar xz -C $release
bash $release/app/deploy/cloudshell/remote/install.sh $release" 2400 || die "install failed (output above)"

if [ "$apply_agents" = 1 ]; then
  read -rp "Create or update the Hishob agents in the Claude account this key belongs to? [y/N] " yes
  if [ "$yes" = y ] || [ "$yes" = Y ]; then
    ssm_run "$instance" "/usr/local/bin/hishob agents apply" 600 || die "agents apply failed"
  fi
fi

# ---- 4. check from outside: HTTPS through CloudFront, and that the access tier reaches the API ------------------
say "checking $api_url (a new distribution can take 10 to 15 minutes to answer)"
ok=0
for _ in $(seq 1 60); do
  if curl -fsS -o /dev/null "$api_url/places?q=ward"; then ok=1; break; fi
  sleep 20
done
[ "$ok" = 1 ] || die "$api_url did not answer; try again in a few minutes: curl $api_url/places?q=ward"

secret=$(aws_ secretsmanager get-secret-value --secret-id "$token_arn" --query SecretString --output text)
token=$(SECRET=$secret python3 -c '
import hashlib, hmac, os
body = "reviewer.deploy-check"
print(body + "." + hmac.new(os.environ["SECRET"].encode(), body.encode(), hashlib.sha256).hexdigest())')
unset secret
curl -fsS -o /dev/null -H "Authorization: Bearer $token" "$api_url/places?q=deploy-check"
if ssm_run "$instance" "journalctl -u hishob-api --since '-5 min' --no-pager | grep -q '\"tier\": \"reviewer\"'" 60 \
  >/dev/null 2>&1; then
  say "access tiers work through CloudFront"
else
  warn "the API did not see the reviewer token: CloudFront may not be forwarding the Authorization header"
fi

cat <<DONE

Deployed $sha.

  API:        $api_url   (try $api_url/docs)
  Instance:   $instance  (no SSH; use ./remote.sh)
  Commands:   ./remote.sh hishob place find "S. V. Road"
              ./remote.sh hishob archive add <url> --publisher bmc --licence "<terms>"
              ./remote.sh sh 'journalctl -u hishob-api -n 50 --no-pager'
  Tokens:     ./remote.sh token reviewer <account>
  Tear down:  ./teardown.sh

The graph and database start empty. Load data as in app/README.md, running each command through ./remote.sh.
DONE
