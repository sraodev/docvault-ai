#!/bin/bash
# Script to deploy all Kubernetes resources

set -e

echo "🚀 Deploying DocVault AI to Kubernetes..."

# Create namespace
echo "📦 Creating namespace..."
kubectl apply -f namespace.yaml

# Create secrets (user must create this manually first)
echo "🔐 Checking secrets..."
if ! kubectl get secret docvault-secrets -n docvault &>/dev/null; then
    echo "⚠️  Warning: Secrets not found. Please create secrets first:"
    echo "   kubectl create secret generic docvault-secrets \\"
    echo "     --from-literal=openrouter_api_key=your-key \\"
    echo "     --namespace=docvault"
    exit 1
fi

# Apply ConfigMaps
echo "⚙️  Applying ConfigMaps..."
kubectl apply -f configmap.yaml
kubectl apply -f backend/configmap.yaml

# Create persistent volumes
echo "💾 Creating persistent volumes..."
kubectl apply -f persistent-volumes.yaml

# Deploy backend
echo "🔧 Deploying backend..."
kubectl apply -f backend/deployment.yaml
kubectl apply -f backend/service.yaml

# Deploy frontend
echo "🎨 Deploying frontend..."
kubectl apply -f frontend/deployment.yaml
kubectl apply -f frontend/service.yaml

# Deploy ingress
echo "🌐 Deploying ingress..."
kubectl apply -f ingress.yaml

# Deploy HPA
echo "📈 Deploying autoscaling..."
kubectl apply -f hpa.yaml

# Wait for deployments
echo "⏳ Waiting for deployments to be ready..."
kubectl wait --for=condition=available --timeout=300s deployment/docvault-backend -n docvault
kubectl wait --for=condition=available --timeout=300s deployment/docvault-frontend -n docvault

# Show status
echo "✅ Deployment complete!"
echo ""
echo "📊 Status:"
kubectl get pods -n docvault
kubectl get svc -n docvault
kubectl get ingress -n docvault
kubectl get hpa -n docvault

