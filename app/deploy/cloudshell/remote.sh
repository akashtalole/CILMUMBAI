#!/bin/bash
# Run things on the demo instance through Session Manager, from CloudShell.
#
#   ./remote.sh hishob <args…>          run the hishob command line on the instance
#   ./remote.sh sh '<shell commands>'    run shell commands as root
#   ./remote.sh token <tier> <account>   print a signed access token (public, contributor, researcher, official, reviewer)
#   ./remote.sh session                  open an interactive shell (needs the Session Manager plugin)
#   ./remote.sh status                   service status and the last log lines
#
# Options before the command: --stack NAME, --region R.
set -euo pipefail
here=$(cd "$(dirname "$0")" && pwd)
# shellcheck source=lib.sh
. "$here/lib.sh"
while [ $# -gt 0 ]; do
  case $1 in
    --stack) STACK=$2; shift 2 ;;
    --region) REGION=$2; shift 2 ;;
    *) break ;;
  esac
done
[ $# -gt 0 ] || { sed -n '2,11p' "$0"; exit 1; }
need aws jq
instance=$(output InstanceId) || die "stack $STACK not found in $REGION"

case $1 in
  hishob)
    shift
    printf -v args ' %q' "$@"
    ssm_run "$instance" "/usr/local/bin/hishob$args" 3600
    ;;
  sh)
    shift
    ssm_run "$instance" "$*" 3600
    ;;
  token)
    [ $# -eq 3 ] || die "usage: ./remote.sh token <tier> <account>"
    secret=$(aws_ secretsmanager get-secret-value --secret-id "$(output TokenSecretArn)" --query SecretString --output text)
    SECRET=$secret TIER=$2 ACCOUNT=$3 python3 -c '
import hashlib, hmac, os, re, sys
tier, account = os.environ["TIER"], os.environ["ACCOUNT"]
if tier not in {"public", "contributor", "researcher", "official", "reviewer"} or not re.fullmatch(r"[A-Za-z0-9_-]{3,64}", account):
    sys.exit("bad tier or account")
body = f"{tier}.{account}"
print(body + "." + hmac.new(os.environ["SECRET"].encode(), body.encode(), hashlib.sha256).hexdigest())'
    ;;
  session)
    command -v session-manager-plugin >/dev/null || die "the Session Manager plugin is not installed here"
    aws_ ssm start-session --target "$instance"
    ;;
  status)
    ssm_run "$instance" "systemctl --no-pager --lines=0 status neo4j postgresql hishob-api hishob-worker | grep -E '●|Active:'
journalctl -u hishob-api -u hishob-worker -n 20 --no-pager" 120
    ;;
  *) die "unknown command $1 (see ./remote.sh with no arguments)" ;;
esac
