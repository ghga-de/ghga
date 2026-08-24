#!/usr/bin/env bash
# Create the self-signed certificate the dev server uses in the --with-oidc modes.
#
# OIDC forces the dev server to HTTPS on port 443 under the backend's own hostname (see
# run.js), so it needs a certificate for that name. A local CA signs it, and only the CA
# certificate has to be trusted by the browser — the leaf can then be reissued for another
# hostname without touching the browser again.
set -euo pipefail

cd "$(dirname "$0")"

CERT_DIR=.certs
CERT="$CERT_DIR/cert.pem"
KEY="$CERT_DIR/key.pem"
CA_CERT="$CERT_DIR/ca-cert.pem"
CA_KEY="$CERT_DIR/ca-key.pem"

DEFAULT_HOST=data.staging.ghga.dev

# The certified name is the host of base_url, i.e. whatever the browser will ask for.
# local.env is read the way run.js reads it, so both agree on the hostname.
url="${data_portal_base_url:-}"
if [ -z "$url" ] && [ -f local.env ]; then
  url=$(sed -n 's/^[[:space:]]*\(export[[:space:]]\{1,\}\)\{0,1\}data_portal_base_url[[:space:]]*=[[:space:]]*//p' local.env |
    tail -n 1 | tr -d "\"'")
fi
host=${url#*://}
host=${host%%[:/]*}
case "$host" in
  '' | localhost | 127.*) host=$DEFAULT_HOST ;;
esac

if [ -f "$CERT" ] && [ -f "$KEY" ] &&
  openssl x509 -in "$CERT" -noout -ext subjectAltName 2> /dev/null | grep -q "DNS:$host\$\|DNS:$host,"; then
  echo "Certificate for $host already exists in $CERT_DIR"
  exit 0
fi

mkdir -p "$CERT_DIR"

if [ ! -f "$CA_CERT" ] || [ ! -f "$CA_KEY" ]; then
  echo "Creating local CA..."
  openssl req -x509 -newkey rsa:4096 -nodes \
    -out "$CA_CERT" -keyout "$CA_KEY" \
    -subj "/CN=GHGA data portal development CA" -days 365
fi

echo "Creating certificate for $host..."
openssl req -newkey rsa:4096 -nodes \
  -out "$CERT_DIR/req.pem" -keyout "$KEY" \
  -subj "/CN=$host"
cat > "$CERT_DIR/ca.ext" << EOF
subjectAltName=DNS:$host,DNS:localhost
authorityKeyIdentifier=keyid,issuer
basicConstraints=CA:FALSE
keyUsage=digitalSignature,keyEncipherment
extendedKeyUsage=serverAuth
EOF
openssl x509 -req \
  -CA "$CA_CERT" -CAkey "$CA_KEY" \
  -in "$CERT_DIR/req.pem" -out "$CERT" \
  -CAcreateserial -days 365 \
  -extfile "$CERT_DIR/ca.ext"
rm -f "$CERT_DIR/req.pem" "$CERT_DIR/ca.ext" "$CERT_DIR/ca-cert.srl"

echo
echo "Add $PWD/$CA_CERT to the trusted certificates of your browser"
echo "or host computer to browse https://$host without warnings."
