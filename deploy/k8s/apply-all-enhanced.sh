#!/bin/bash
# Enhanced deployment script for million+ user scale

set -e

echo "🚀 Deploying DocVault AI for Million+ User Scale..."

# Create namespace
echo "📦 Creating namespace..."
kubectl apply -f namespace.yaml

# Create secrets
echo "🔐 Checking secrets..."
if ! kubectl get secret docvault-secrets -n docvault &>/dev/null; then
    echo "⚠️  Warning: Secrets not found. Please create secrets first."
    exit 1
fi

# Apply ConfigMaps
echo "⚙️  Applying ConfigMaps..."
kubectl apply -f configmap.yaml
kubectl apply -f backend/configmap.yaml
kubectl apply -f database-optimization.yaml

# Deploy Redis Cluster
echo "💾 Deploying Redis cluster..."
kubectl apply -f redis/persistent-volume.yaml
kubectl apply -f redis/configmap.yaml
kubectl apply -f redis/deployment.yaml
kubectl apply -f redis/service.yaml

# Wait for Redis
echo "⏳ Waiting for Redis..."
kubectl wait --for=condition=available --timeout=120s deployment/redis -n docvault || true

# Create persistent volumes
echo "💾 Creating persistent volumes..."
kubectl apply -f persistent-volumes.yaml

# Deploy backend
echo "🔧 Deploying backend (5 replicas)..."
kubectl apply -f backend/deployment.yaml
kubectl apply -f backend/service.yaml

# Deploy Celery workers
echo "⚙️  Deploying Celery workers (10 replicas)..."
kubectl apply -f celery/deployment.yaml

# Deploy frontend
echo "🎨 Deploying frontend (3 replicas)..."
kubectl apply -f frontend/deployment.yaml
kubectl apply -f frontend/service.yaml

# Deploy ingress
echo "🌐 Deploying ingress..."
kubectl apply -f ingress.yaml

# Deploy HPA (auto-scaling)
echo "📈 Deploying autoscaling (5-50 backend, 3-20 frontend)..."
kubectl apply -f hpa.yaml

# Deploy monitoring (optional)
if [ "$1" == "--with-monitoring" ]; then
    echo "📊 Deploying monitoring..."
    kubectl apply -f monitoring/
fi

# Wait for deployments
echo "⏳ Waiting for deployments to be ready..."
kubectl wait --for=condition=available --timeout=300s deployment/docvault-backend -n docvault
kubectl wait --for=condition=available --timeout=300s deployment/docvault-frontend -n docvault
kubectl wait --for=condition=available --timeout=300s deployment/celery-worker -n docvault

# Show status
echo "✅ Deployment complete!"
echo ""
echo "📊 Status:"
kubectl get pods -n docvault
echo ""
kubectl get svc -n docvault
echo ""
kubectl get ingress -n docvault
echo ""
kubectl get hpa -n docvault
echo ""
echo "💡 Scaling tips:"
echo "  - Backend auto-scales: 5-50 replicas"
echo "  - Frontend auto-scales: 3-20 replicas"
echo "  - Scale workers: kubectl scale deployment celery-worker --replicas=20 -n docvault"
echo "  - Monitor: kubectl get hpa -n docvault"

