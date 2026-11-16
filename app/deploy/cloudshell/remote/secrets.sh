#!/bin/bash
# Fetch secrets into /run (memory only) for the services. Run by hishob-secrets.service as root.
set -euo pipefail
set -a
# shellcheck disable=SC1091
. /etc/hishob/hishob.env
set +a
install -d -m 750 -o root -g hishob /run/hishob
umask 027
token=$(aws secretsmanager get-secret-value --secret-id "$HISHOB_TOKEN_SECRET_ARN" --query SecretString --output text)
key=$(aws secretsmanager get-secret-value --secret-id "$HISHOB_CLAUDE_KEY_SECRET_ARN" --query SecretString --output text)
{
  printf 'HISHOB_TOKEN_SECRET=%s\n' "$token"
  if [ "$key" != "unset" ]; then printf 'ANTHROPIC_API_KEY=%s\n' "$key"; fi
} > /run/hishob/secrets.env.new
chgrp hishob /run/hishob/secrets.env.new
mv /run/hishob/secrets.env.new /run/hishob/secrets.env
