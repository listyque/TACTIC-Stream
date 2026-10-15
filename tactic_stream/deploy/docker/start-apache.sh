#!/bin/sh
set -eu
umask 077

# Webmin-only root password; the container's Unix root account stays locked.
if [ ! -f /etc/webmin/.stream-initialized ]; then
    grep -q '^root:' /etc/webmin/miniserv.users
    hash=$(openssl passwd -6 -stdin < /run/secrets/webmin_password)
    awk -F: -v hash="$hash" 'BEGIN {OFS=":"} $1 == "root" {$2=hash} {print}' \
        /etc/webmin/miniserv.users > /etc/webmin/miniserv.users.new
    mv /etc/webmin/miniserv.users.new /etc/webmin/miniserv.users
    # Issue a private certificate per deployment, instead of sharing the image's key.
    generated=$(mktemp -d)
    trap 'rm -rf "$generated"' EXIT
    openssl req -x509 -newkey rsa:3072 -nodes -days 365 \
        -subj '/CN=localhost' -addext 'subjectAltName=DNS:localhost,IP:127.0.0.1' \
        -keyout "$generated/key.pem" -out "$generated/cert.pem" 2>/dev/null
    cat "$generated/key.pem" "$generated/cert.pem" > /etc/webmin/miniserv.pem
    rm -rf "$generated"
    touch /etc/webmin/.stream-initialized
fi

/etc/webmin/start
exec apache2ctl -D FOREGROUND
