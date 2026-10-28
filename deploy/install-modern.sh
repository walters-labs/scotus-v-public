#!/bin/bash
# Activate the separately tested modern corpus; retain the previous release.
set -euo pipefail
[ "$(id -u)" -eq 0 ] || { echo 'Run with sudo.' >&2; exit 1; }
source_dir=/home/jackson/scvpublic/modern-release
release=/opt/scvpublic/releases/20261023-modern
previous=$(readlink -f /opt/scvpublic/current)
[ ! -e "$release" ] || { echo "Release exists: $release; inspect before retrying." >&2; exit 1; }
cd "$source_dir"
sha256sum -c SHA256SUMS
install -d -m 755 "$release"
while read -r digest name; do
    install -D -m 644 "$source_dir/$name" "$release/$name"
done < SHA256SUMS
install -m 644 SHA256SUMS "$release/SHA256SUMS"
cd "$release"
sha256sum -c SHA256SUMS
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
PYTHONPATH=. .venv/bin/python scripts/check_serving.py artifacts/search.sqlite
rollback() {
    ln -s "$previous" /opt/scvpublic/rollback.next
    mv -Tf /opt/scvpublic/rollback.next /opt/scvpublic/current
    systemctl restart scvpublic
}
trap rollback ERR
ln -s "$release" /opt/scvpublic/current.next
mv -Tf /opt/scvpublic/current.next /opt/scvpublic/current
systemctl restart scvpublic
for attempt in {1..15}; do
    if curl -fsS http://127.0.0.1:8010/healthz; then break; fi
    sleep 1
done
curl -fsS 'http://127.0.0.1:8010/?q1=abortion' -o /dev/null
systemctl is-active scvpublic
trap - ERR
echo "Previous release retained at $previous"
