#!/bin/sh
set -eu
umask 022
test "$(id -u)" -eq 0
test -f /opt/footballknow/public/index.html
test -f /opt/footballknow/public/app.js
test -f /opt/footballknow/server.py
test -f /opt/footballknow/public/data.json
apt-get update -qq
DEBIAN_FRONTEND=noninteractive apt-get install -y -qq caddy python3-venv ca-certificates curl
if ! id footballknow >/dev/null 2>&1; then
    useradd --system --user-group --home-dir /var/lib/footballknow --shell /usr/sbin/nologin footballknow
fi
install -d -m 700 -o footballknow -g footballknow /var/lib/footballknow
install -d -m 755 -o footballknow -g footballknow /opt/footballknow/public/match-details /opt/footballknow/public/laliga/match-details /opt/footballknow/public/ucl/match-details /opt/footballknow/public/seriea/match-details /opt/footballknow/public/bundesliga/match-details /opt/footballknow/public/finance/history
if ! test -f /var/lib/footballknow/admin.sqlite3 && ! test -f /var/lib/footballknow/admin-seed.json; then
    test -f /opt/footballknow/deploy/private/admin-seed.json
    install -m 600 -o footballknow -g footballknow /opt/footballknow/deploy/private/admin-seed.json /var/lib/footballknow/admin-seed.json
fi
python3 -m venv /opt/footballknow/.venv
/opt/footballknow/.venv/bin/python -m pip install --disable-pip-version-check -r /opt/footballknow/requirements.txt
chmod 755 /opt/footballknow /opt/footballknow/public
find /opt/footballknow/football -type d -exec chmod 755 {} +
find /opt/footballknow/football -type f -exec chmod 644 {} +
find /opt/footballknow -maxdepth 1 -type f -name '*.py' -exec chmod 644 {} +
chmod 644 /opt/footballknow/analysis-rules.txt
chown -R footballknow:footballknow /opt/footballknow/public
find /opt/footballknow/public -type d -exec chmod 755 {} +
find /opt/footballknow/public -type f -exec chmod 644 {} +
if test -d /opt/footballknow/deploy/private; then
    chmod 700 /opt/footballknow/deploy/private
    chmod 600 /opt/footballknow/deploy/private/admin-seed.json
fi
cd /opt/footballknow
runuser -u footballknow -- env FOOTBALL_STATE_DIR=/var/lib/footballknow PYTHONDONTWRITEBYTECODE=1 /opt/footballknow/.venv/bin/python -c 'from football.auth import initialize_database; initialize_database()'
if test -f /etc/caddy/Caddyfile && ! test -f /etc/caddy/Caddyfile.before-footballknow; then
    cp -p /etc/caddy/Caddyfile /etc/caddy/Caddyfile.before-footballknow
fi
install -m 644 /opt/footballknow/deploy/Caddyfile /etc/caddy/Caddyfile
install -m 644 /opt/footballknow/deploy/footballknow-web.service /etc/systemd/system/footballknow-web.service
install -m 644 /opt/footballknow/deploy/footballknow-worker.service /etc/systemd/system/footballknow-worker.service
if test -f /etc/systemd/system/footballknow-sync.timer; then
    systemctl disable --now footballknow-sync.timer
fi
systemctl daemon-reload
caddy validate --config /etc/caddy/Caddyfile --adapter caddyfile
systemctl enable footballknow-web footballknow-worker caddy
systemctl restart footballknow-web footballknow-worker
attempt=0
until curl --fail --silent http://127.0.0.1:8765/api/auth/me >/dev/null; do
    attempt=$((attempt + 1))
    test "$attempt" -lt 20
    sleep 1
done
systemctl restart caddy
systemctl is-active footballknow-web footballknow-worker caddy
curl --fail --silent http://127.0.0.1:8765/api/auth/me
