#!/bin/bash
# Start Production Load Balancer Stack

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "🚀 Starting DocVault AI Load Balancer Stack..."

# Check if SSL certificates exist
if [ ! -f "./ssl/cert.pem" ] || [ ! -f "./ssl/key.pem" ]; then
    echo "⚠️  SSL certificates not found. Running setup..."
    ./setup-ssl.sh "${DOMAIN:-localhost}"
fi

# Validate nginx configuration
echo "🔍 Validating nginx configuration..."
docker run --rm -v "$(pwd)/nginx.conf:/etc/nginx/nginx.conf:ro" nginx:alpine nginx -t

if [ $? -eq 0 ]; then
    echo "✅ Nginx configuration is valid"
else
    echo "❌ Nginx configuration has errors. Please fix before starting."
    exit 1
fi

# Start services
echo "📦 Starting Docker Compose services..."
docker-compose -f docker-compose.loadbalancer.yml up -d

# Wait for services to be healthy
echo "⏳ Waiting for services to be healthy..."
sleep 10

# Check health
echo "🏥 Checking service health..."
for i in {1..30}; do
    if curl -f -s http://localhost/health > /dev/null 2>&1; then
        echo "✅ Load balancer is healthy"
        break
    fi
    if [ $i -eq 30 ]; then
        echo "❌ Load balancer health check failed"
        exit 1
    fi
    sleep 2
done

# Display status
echo ""
echo "📊 Service Status:"
docker-compose -f docker-compose.loadbalancer.yml ps

echo ""
echo "✅ Load balancer stack started successfully!"
echo ""
echo "🌐 Access points:"
echo "   - HTTP:  http://localhost"
echo "   - HTTPS: https://localhost"
echo "   - API:   http://localhost/api"
echo "   - Health: http://localhost/health"
echo ""
echo "📝 Useful commands:"
echo "   - View logs: docker-compose -f docker-compose.loadbalancer.yml logs -f"
echo "   - Stop:     docker-compose -f docker-compose.loadbalancer.yml down"
echo "   - Restart:  docker-compose -f docker-compose.loadbalancer.yml restart"

