#!/bin/bash
# Runs on the instance, as root, through Session Manager (deploy.sh). Installs one release of the app from the
# bundle already unpacked at $1, migrates the database and (re)starts the services. Safe to run again.
set -euo pipefail
release=${1:?usage: install.sh <release-dir>}
app="$release/app"
here="$app/deploy/cloudshell/remote"

[ -f /var/lib/hishob/bootstrapped ] || { echo "instance set-up has not finished yet" >&2; exit 3; }
chown -R hishob:hishob "$release"

echo "== dependencies"
runuser -u hishob -- env HOME=/home/hishob UV_PYTHON_INSTALL_DIR=/home/hishob/.local/share/uv/python \
  /usr/local/bin/uv sync --locked --no-dev --project "$app"

# The agent lock records which agents exist in the Claude account; it must outlive releases (provision.py).
touch /var/lib/hishob/agents.lock.json
[ -s /var/lib/hishob/agents.lock.json ] || echo '{"agents": {}, "environments": {}}' > /var/lib/hishob/agents.lock.json
chown hishob:hishob /var/lib/hishob/agents.lock.json
ln -sfn /var/lib/hishob/agents.lock.json "$app/agents/.lock.json"

echo "== services"
install -m 755 "$here/hishob" /usr/local/bin/hishob
install -m 750 "$here/secrets.sh" /usr/local/sbin/hishob-secrets
install -m 644 "$here"/hishob-*.service /etc/systemd/system/
ln -sfn "$release" /opt/hishob/current
systemctl daemon-reload
systemctl restart hishob-secrets

echo "== database"
/usr/local/bin/hishob db migrate

systemctl enable hishob-secrets hishob-api hishob-worker >/dev/null
systemctl restart hishob-api hishob-worker

echo "== health"
for _ in $(seq 1 30); do
  if curl -fsS -o /dev/null "http://127.0.0.1/places?q=ward"; then
    echo "api answering on port 80"
    break
  fi
  sleep 2
done
curl -fsS -o /dev/null "http://127.0.0.1/places?q=ward" || { journalctl -u hishob-api -n 40 --no-pager; exit 4; }

# Keep the three newest releases (names are commit hashes; the newest is the one just installed).
# shellcheck disable=SC2012
ls -1dt /opt/hishob/releases/*/ | tail -n +4 | xargs -r rm -rf
echo "installed $(basename "$release")"
