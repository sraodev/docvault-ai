#!/bin/bash
# SSL Certificate Setup Script for Production Load Balancer

set -e

SSL_DIR="./ssl"
DOMAIN="${1:-localhost}"

echo "🔐 Setting up SSL certificates for domain: $DOMAIN"

# Create SSL directory
mkdir -p "$SSL_DIR"

# Check if Let's Encrypt certificates exist
if [ -d "/etc/letsencrypt/live/$DOMAIN" ]; then
    echo "✅ Found Let's Encrypt certificates"
    cp "/etc/letsencrypt/live/$DOMAIN/fullchain.pem" "$SSL_DIR/cert.pem"
    cp "/etc/letsencrypt/live/$DOMAIN/privkey.pem" "$SSL_DIR/key.pem"
    cp "/etc/letsencrypt/live/$DOMAIN/chain.pem" "$SSL_DIR/ca.pem"
    echo "✅ Certificates copied to $SSL_DIR"
elif [ -f "$SSL_DIR/cert.pem" ] && [ -f "$SSL_DIR/key.pem" ]; then
    echo "✅ SSL certificates already exist in $SSL_DIR"
else
    echo "⚠️  No SSL certificates found. Generating self-signed certificates for development..."
    
    # Generate self-signed certificate (development only)
    openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
        -keyout "$SSL_DIR/key.pem" \
        -out "$SSL_DIR/cert.pem" \
        -subj "/C=US/ST=State/L=City/O=Organization/CN=$DOMAIN"
    
    cp "$SSL_DIR/cert.pem" "$SSL_DIR/ca.pem"
    
    echo "⚠️  WARNING: Self-signed certificates generated. Use Let's Encrypt for production!"
    echo "   To get real certificates, run:"
    echo "   certbot certonly --standalone -d $DOMAIN"
fi

# Set proper permissions
chmod 600 "$SSL_DIR/key.pem"
chmod 644 "$SSL_DIR/cert.pem"
chmod 644 "$SSL_DIR/ca.pem"

echo "✅ SSL setup complete!"

