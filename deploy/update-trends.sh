#!/bin/bash
set -euo pipefail
[ "$(id -u)" -eq 0 ] || { echo 'Run with sudo.' >&2; exit 1; }
release=$(readlink -f /opt/scvpublic/current)
backup="$release/trends-backup-$(date +%s).tar.gz"
files=(scvpublic/store.py scvpublic/web.py scvpublic/chart.py scvpublic/templates/index.html scvpublic/static/style.css)
tar -czf "$backup" -C "$release" "${files[@]}"
trap 'tar -xzf "$backup" -C "$release"; systemctl restart scvpublic' ERR
for file in "${files[@]}"; do
    install -m 644 "/home/jackson/scvpublic/trends-update/$file" "$release/$file"
done
cd "$release"
PYTHONPATH=. .venv/bin/python scripts/check_serving.py artifacts/search.sqlite
systemctl restart scvpublic
sleep 2
curl -fsS 'http://127.0.0.1:8010/?q1=abortion&rolling=1' -o /dev/null
curl -fsS http://127.0.0.1:8010/healthz
trap - ERR
echo "Previous files saved to $backup"
