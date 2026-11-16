#!/bin/bash
# Remove the Aamcha Hishob demo profile from AWS, from CloudShell.
#
#   ./teardown.sh                 delete the stack; keep the three buckets (the archive is the system of record)
#   ./teardown.sh --delete-data   also empty and delete the buckets, every version, after a second confirmation
#
# Options: --stack NAME, --region R, --yes (skip the first confirmation; --delete-data always asks).
set -euo pipefail
here=$(cd "$(dirname "$0")" && pwd)
# shellcheck source=lib.sh
. "$here/lib.sh"

delete_data=0 yes=0
while [ $# -gt 0 ]; do
  case $1 in
    --stack) STACK=$2; shift 2 ;;
    --region) REGION=$2; shift 2 ;;
    --delete-data) delete_data=1; shift ;;
    --yes) yes=1; shift ;;
    -h | --help) sed -n '2,8p' "$0"; exit 0 ;;
    *) die "unknown option $1 (see --help)" ;;
  esac
done
need aws jq

status=$(stack_status)
buckets=()
if [ "$status" != NONE ]; then
  for key in ArchiveBucket DataBucket ReleasedBucket; do
    name=$(output "$key" 2>/dev/null || true)
    [ -n "$name" ] && [ "$name" != None ] && buckets+=("$name")
  done
fi
if [ ${#buckets[@]} -eq 0 ]; then
  # The stack may be gone already; find buckets it left behind by their tags.
  while read -r name; do
    [ -n "$name" ] || continue
    # shellcheck disable=SC2016  # backticks are JMESPath literals, not shell
    tags=$(aws_ s3api get-bucket-tagging --bucket "$name" --query 'TagSet[?Key==`aws:cloudformation:stack-name`].Value' \
      --output text 2>/dev/null || true)
    [ "$tags" = "$STACK" ] && buckets+=("$name")
  done < <(aws_ s3api list-buckets --query 'Buckets[].Name' --output text | tr '\t' '\n')
fi

say "region $REGION, stack $STACK ($status)"
if [ "$status" != NONE ]; then
  echo "Will delete: the instance and its disk (Postgres and Neo4j data, rebuildable from the ledger), the network,"
  echo "             the Elastic IP, CloudFront, the queues, the secrets and the instance role."
fi
if [ ${#buckets[@]} -gt 0 ]; then
  if [ "$delete_data" = 1 ]; then echo "Will delete:  buckets ${buckets[*]}"; else echo "Will keep:    buckets ${buckets[*]}"; fi
fi
echo "Not touched:  agents created in the Claude account (remove them there, and revoke the key if it was shared)."

if [ "$status" != NONE ]; then
  if [ "$yes" = 0 ]; then
    read -rp "Type the stack name to delete it: " answer
    [ "$answer" = "$STACK" ] || die "not confirmed; nothing deleted"
  fi
  say "deleting the stack (CloudFront takes 10 to 20 minutes to disable)"
  aws_ cloudformation delete-stack --stack-name "$STACK"
  aws_ cloudformation wait stack-delete-complete --stack-name "$STACK" \
    || die "stack deletion did not complete; see the stack's events in the CloudFormation console"
  say "stack deleted"
fi

[ ${#buckets[@]} -gt 0 ] || exit 0
if [ "$delete_data" = 0 ]; then
  echo
  echo "Buckets kept. They cost little but not nothing; to delete them later: ./teardown.sh --delete-data"
  exit 0
fi

archive=$(printf '%s\n' "${buckets[@]}" | grep -i archive | head -1 || true)
echo
warn "this permanently deletes every version of every object in: ${buckets[*]}"
read -rp "Type 'delete ${archive:-${buckets[0]}}' to confirm: " answer
[ "$answer" = "delete ${archive:-${buckets[0]}}" ] || die "not confirmed; buckets kept"

empty_bucket() {
  local bucket=$1 bypass=() batch count result failed
  # The archive uses object lock in governance mode; removing locked versions needs s3:BypassGovernanceRetention.
  [ "$bucket" = "$archive" ] && bypass=(--bypass-governance-retention)
  while :; do
    batch=$(aws_ s3api list-object-versions --bucket "$bucket" --max-items 1000 --output json \
      | jq -c '{Objects: ([.Versions[]?, .DeleteMarkers[]?] | map({Key, VersionId})), Quiet: true}')
    count=$(jq '.Objects | length' <<<"$batch")
    [ "$count" -gt 0 ] || break
    result=$(aws_ s3api delete-objects --bucket "$bucket" "${bypass[@]}" --delete "$batch" --output json)
    failed=$(jq '[.Errors[]?] | length' <<<"$result")
    jq -r '.Errors[]? | "  could not delete \(.Key): \(.Message)"' <<<"$result" | head -5
    if [ "$failed" -ge "$count" ]; then
      warn "nothing more can be deleted from $bucket (locked objects need s3:BypassGovernanceRetention)"
      return 1
    fi
    echo "  removed $((count - failed)) versions from $bucket"
  done
}
for bucket in "${buckets[@]}"; do
  if ! aws_ s3api head-bucket --bucket "$bucket" 2>/dev/null; then continue; fi
  if empty_bucket "$bucket" && aws_ s3api delete-bucket --bucket "$bucket"; then
    say "deleted $bucket"
  else
    warn "could not delete $bucket"
  fi
done
