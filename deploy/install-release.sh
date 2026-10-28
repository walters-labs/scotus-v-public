#!/bin/bash
# Usage: sudo bash deploy/install-release.sh /absolute/staging/path release-name
set -euo pipefail
[ "$(id -u)" -eq 0 ] || { echo 'Run with sudo.' >&2; exit 1; }
source_dir=$(realpath "${1:?staging directory required}")
name=${2:?release name required}
[[ "$name" =~ ^[a-zA-Z0-9_-]+$ ]] || exit 1
release=/opt/scvpublic/releases/$name
previous=$(readlink -f /opt/scvpublic/current)
[ ! -e "$release" ] || { echo "Release exists: $release"; exit 1; }
cd "$source_dir"
sha256sum -c SHA256SUMS
install -d -m 755 "$release"
while read -r digest file; do
    [[ "$file" != /* && "$file" != *..* ]] || exit 1
    install -D -m 644 "$source_dir/$file" "$release/$file"
done < SHA256SUMS
install -m 644 SHA256SUMS "$release/SHA256SUMS"
cd "$release"
python3 -m venv .venv
.venv/bin/pip install -r requirements-hybrid.txt
cp /etc/systemd/system/scvpublic.service "$release/previous.service"
rollback() {
    trap - ERR
    ln -sfn "$previous" /opt/scvpublic/current.next
    mv -Tf /opt/scvpublic/current.next /opt/scvpublic/current
    cp "$release/previous.service" /etc/systemd/system/scvpublic.service
    systemctl daemon-reload
    systemctl restart scvpublic
    echo "Restored $previous" >&2
}
trap rollback ERR
install -m 644 deploy/scvpublic.service /etc/systemd/system/scvpublic.service
systemd-analyze verify /etc/systemd/system/scvpublic.service
ln -sfn "$release" /opt/scvpublic/current.next
mv -Tf /opt/scvpublic/current.next /opt/scvpublic/current
systemctl daemon-reload
systemctl restart scvpublic
for attempt in {1..30}; do
    if curl -fsS http://127.0.0.1:8010/healthz; then break; fi
    sleep 1
done
.venv/bin/python scripts/check_hybrid_http.py --url http://127.0.0.1:8010
systemctl is-active scvpublic
systemctl show scvpublic -p MemoryCurrent -p MemoryPeak -p NRestarts
trap - ERR
echo "Activated $release; rollback release: $previous"
