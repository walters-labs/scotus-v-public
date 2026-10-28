#!/bin/bash
# Run on the VPS as root after staging and testing release 20261022-1.
set -euo pipefail
[ "$(id -u)" -eq 0 ] || { echo 'Run with sudo.' >&2; exit 1; }
source_dir=/home/jackson/scvpublic/releases/20261022-1
release=/opt/scvpublic/releases/20261022-1
[ ! -e "$release" ] || { echo "Release already exists: $release; inspect before retrying." >&2; exit 1; }
[ ! -e /etc/systemd/system/scvpublic.service ] || { echo 'Service already installed; inspect before replacing.' >&2; exit 1; }
cd "$source_dir"
sha256sum -c SHA256SUMS
install -d -m 755 "$release"
# Copy only the verified release files, excluding the preview's virtualenv.
while read -r digest name; do
    install -D -m 644 "$source_dir/$name" "$release/$name"
done < SHA256SUMS
install -m 644 SHA256SUMS "$release/SHA256SUMS"
cd "$release"
sha256sum -c SHA256SUMS
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
PYTHONPATH=. .venv/bin/python scripts/check_serving.py artifacts/search.sqlite
ln -s "$release" /opt/scvpublic/current.next
mv -Tf /opt/scvpublic/current.next /opt/scvpublic/current
install -m 644 deploy/scvpublic.service /etc/systemd/system/scvpublic.service
systemd-analyze verify /etc/systemd/system/scvpublic.service
systemctl daemon-reload
preview() { runuser -u jackson -- env XDG_RUNTIME_DIR=/run/user/1000 systemctl --user "$1" scvpublic-preview; }
preview stop
# Restore the working preview if activation fails.
trap 'systemctl stop scvpublic || true; preview start || true' ERR
systemctl enable --now scvpublic
for attempt in {1..15}; do
    if curl -fsS http://127.0.0.1:8010/healthz; then break; fi
    sleep 1
done
curl -fsS http://127.0.0.1:8010/healthz
systemctl is-enabled scvpublic
systemctl is-active scvpublic
trap - ERR
systemctl show scvpublic -p MemoryCurrent -p NRestarts
