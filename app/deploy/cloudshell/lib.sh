#!/bin/bash
# Shared by deploy.sh, teardown.sh and remote.sh. Sourced, not run.

STACK=${HISHOB_STACK:-aamcha-hishob-demo}
REGION=${HISHOB_REGION:-ap-south-1} # ADR 0017: Mumbai, whatever region the console is showing

say() { printf '\033[1m==\033[0m %s\n' "$*"; }
warn() { printf '\033[33mwarning:\033[0m %s\n' "$*" >&2; }
die() { printf '\033[31merror:\033[0m %s\n' "$*" >&2; exit 1; }

need() {
  for tool in "$@"; do command -v "$tool" >/dev/null || die "$tool is not installed (AWS CloudShell has it)"; done
}

aws_() { aws --region "$REGION" "$@"; }

stack_status() {
  aws_ cloudformation describe-stacks --stack-name "$STACK" --query 'Stacks[0].StackStatus' --output text 2>/dev/null \
    || echo NONE
}

# output <Key>: one stack output value
output() {
  aws_ cloudformation describe-stacks --stack-name "$STACK" \
    --query "Stacks[0].Outputs[?OutputKey=='$1'].OutputValue" --output text
}

# ssm_run <instance-id> <shell script text> [timeout seconds]: run as root on the instance, print its output,
# and return non-zero if it failed. The script text is passed as JSON, so no shell quoting is involved.
ssm_run() {
  local instance=$1 script=$2 timeout=${3:-1800} id status
  id=$(aws_ ssm send-command --instance-ids "$instance" --document-name AWS-RunShellScript \
    --timeout-seconds 600 --comment "aamcha-hishob" \
    --parameters "$(jq -n --arg s "$script" --arg t "$timeout" '{commands: [$s], executionTimeout: [$t]}')" \
    --query Command.CommandId --output text) || return 1
  while :; do
    sleep 4
    status=$(aws_ ssm get-command-invocation --command-id "$id" --instance-id "$instance" \
      --query Status --output text 2>/dev/null || echo Pending)
    case $status in Pending | InProgress | Delayed) ;; *) break ;; esac
  done
  aws_ ssm get-command-invocation --command-id "$id" --instance-id "$instance" \
    --query '[StandardOutputContent, StandardErrorContent]' --output json | jq -r '.[] | select(. != null and . != "")'
  [ "$status" = Success ]
}

# Wait until Session Manager can reach the instance.
wait_for_ssm() {
  local instance=$1 tries=0
  until [ "$(aws_ ssm describe-instance-information --filters "Key=InstanceIds,Values=$instance" \
    --query 'length(InstanceInformationList)' --output text 2>/dev/null)" = 1 ]; do
    tries=$((tries + 1))
    [ "$tries" -le 90 ] || die "the instance did not register with Session Manager within 15 minutes"
    sleep 10
  done
}
