#!/bin/bash
# Run on the VPS with sudo; uses the existing Certbot installation/account.
set -euo pipefail
[ "$(id -u)" -eq 0 ] || { echo 'Run with sudo.' >&2; exit 1; }
site=svp.walterslabs.dev
config=/etc/nginx/sites-available/$site
link=/etc/nginx/sites-enabled/$site
getent ahostsv4 "$site" | awk '{print $1}' | sort -u | grep -Fx 137.184.128.197 >/dev/null
systemctl is-active --quiet scvpublic
curl -fsS http://127.0.0.1:8010/healthz
# Preserve any existing site configuration, including Certbot's TLS additions.
if [ ! -e "$config" ]; then
    install -m 644 /opt/scvpublic/current/deploy/svp.walterslabs.dev.conf "$config"
fi
if [ ! -e "$link" ] && [ ! -L "$link" ]; then
    ln -s "$config" "$link"
fi
nginx -t
systemctl reload nginx
certbot --nginx -d "$site" --redirect
nginx -t
curl --fail --resolve "$site:443:127.0.0.1" "https://$site/healthz"
systemctl is-active scvpublic nginx
