#!/bin/bash
# Activate the GSS/bigram candidate tested under the VPS memory cap.
set -euo pipefail
[ "$(id -u)" -eq 0 ] || { echo 'Run with sudo.' >&2; exit 1; }
source_dir=/home/jackson/scvpublic/bigram-memory-test
release=/opt/scvpublic/releases/20261022-gss-bigrams
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
    trap - ERR
    ln -s "$previous" /opt/scvpublic/rollback.next
    mv -Tf /opt/scvpublic/rollback.next /opt/scvpublic/current
    systemctl restart scvpublic
    echo "Activation failed; restored $previous" >&2
}
trap rollback ERR
ln -s "$release" /opt/scvpublic/current.next
mv -Tf /opt/scvpublic/current.next /opt/scvpublic/current
systemctl restart scvpublic
.venv/bin/python - <<'PY'
import time, urllib.request
for attempt in range(20):
    try:
        with urllib.request.urlopen('http://127.0.0.1:8010/healthz', timeout=5) as response:
            assert response.status == 200
        break
    except Exception:
        if attempt == 19: raise
        time.sleep(1)
for query, required, excluded in [
    ('civil+rights', b'96 scored cases', b'No matching opinions.'),
    ('gun+control', b'GUNLAW', b'PILLOK'),
    ('marijuana', b'GRASS', b'No matching GSS questions.')]:
    with urllib.request.urlopen('http://127.0.0.1:8010/?q1='+query, timeout=30) as response:
        page = response.read()
        assert required in page and excluded not in page, query
PY
systemctl is-active scvpublic
trap - ERR
echo "Activated $release"
echo "Previous release retained at $previous"
