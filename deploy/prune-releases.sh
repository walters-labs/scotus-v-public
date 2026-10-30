#!/bin/bash
# Remove superseded installed releases; retain only the verified live release.
# Usage: sudo bash deploy/prune-releases.sh [--apply]
set -euo pipefail
[[ $# -le 1 && ( $# -eq 0 || "$1" == --apply ) ]] || exit 2
root=/opt/scvpublic/releases
active=$(readlink -f /opt/scvpublic/current)
[[ -d "$active" && "$(dirname "$active")" == "$root" ]] || { echo 'Unexpected active release' >&2; exit 1; }
systemctl is-active --quiet scvpublic
curl -fsS http://127.0.0.1:8010/healthz >/dev/null
[[ $(systemctl show scvpublic -p WorkingDirectory --value) == /opt/scvpublic/current ]] || exit 1
for path in "$root"/*; do
    [[ -d "$path" && ! -L "$path" && "$path" != "$active" ]] || continue
    [[ $(basename "$path") =~ ^[0-9]{8}-[a-zA-Z0-9_-]+$ ]] || { echo "Unexpected release: $path" >&2; exit 1; }
done
for path in "$root"/*; do
    [[ -d "$path" && ! -L "$path" && "$path" != "$active" ]] || continue
    echo "Remove: $path"
    if [[ ${1:-} == --apply ]]; then
        [[ $(readlink -f /opt/scvpublic/current) == "$active" ]] || exit 1
        rm -rf -- "$path"
    fi
done
echo "Retained live release: $active"
df -h "$root"
