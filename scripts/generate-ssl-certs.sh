#!/bin/bash
# Generate self-signed SSL certificates for development
# For production, use Let's Encrypt instead

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
SSL_DIR="$PROJECT_ROOT/nginx/ssl"

echo "=== Lazy-Bird SSL Certificate Generator ==="
echo

# Create SSL directory
mkdir -p "$SSL_DIR"

# Check if certificates already exist
if [ -f "$SSL_DIR/cert.pem" ] && [ -f "$SSL_DIR/key.pem" ]; then
    echo "⚠️  Certificates already exist at $SSL_DIR"
    echo
    read -p "Regenerate certificates? This will overwrite existing ones. (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Aborted."
        exit 0
    fi
fi

echo "Generating self-signed SSL certificate..."
echo

# Generate certificate
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
    -keyout "$SSL_DIR/key.pem" \
    -out "$SSL_DIR/cert.pem" \
    -subj "/C=US/ST=Development/L=Local/O=Lazy-Bird/CN=localhost" \
    2>/dev/null

if [ $? -eq 0 ]; then
    echo "✅ SSL certificates generated successfully!"
    echo
    echo "Certificate: $SSL_DIR/cert.pem"
    echo "Private Key: $SSL_DIR/key.pem"
    echo
    echo "Certificate Details:"
    openssl x509 -in "$SSL_DIR/cert.pem" -noout -subject -dates
    echo
    echo "⚠️  WARNING: This is a self-signed certificate for DEVELOPMENT ONLY!"
    echo "   Browsers will show security warnings."
    echo "   For production, use Let's Encrypt:"
    echo "   sudo certbot certonly --standalone -d yourdomain.com"
    echo
else
    echo "❌ Failed to generate SSL certificates"
    exit 1
fi
