#!/usr/bin/env bash
# One-time (sudo): issue the TLS certificate and enable the nginx site.
#   sudo ./deploy/install-nginx.sh
set -euo pipefail
DOMAIN=obelytics.bitstreamhq.com
SITE=/etc/nginx/sites-available/$DOMAIN
cd "$(dirname "$0")"

mkdir -p /var/www/certbot

if [ ! -d "/etc/letsencrypt/live/$DOMAIN" ]; then
  # Port-80-only site first so certbot's webroot challenge can be served
  sed -n '/^server {$/{:a;N;/\n}$/!ba;h};${x;p}' nginx/obelytics.conf > "$SITE"
  ln -sf "$SITE" /etc/nginx/sites-enabled/$DOMAIN
  nginx -t && systemctl reload nginx
  certbot certonly --webroot -w /var/www/certbot -d "$DOMAIN" \
    --non-interactive --agree-tos --register-unsafely-without-email
fi

install -m 644 nginx/obelytics.conf "$SITE"
ln -sf "$SITE" /etc/nginx/sites-enabled/$DOMAIN
nginx -t && systemctl reload nginx
echo "nginx site for $DOMAIN enabled"
