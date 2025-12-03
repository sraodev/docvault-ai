# Deployment Guide

Complete deployment guide for DocVault AI in production environments.

## Quick Links

- [Docker Compose Deployment](#docker-compose-deployment) - Local development and testing
- [Kubernetes Deployment](#kubernetes-deployment) - Production deployment
- [Production Checklist](./PRODUCTION_CHECKLIST.md) - Pre-deployment checklist

## Docker Compose Deployment

### Prerequisites
- Docker 20.10+
- Docker Compose 2.0+

### Quick Start

```bash
# 1. Copy environment file
cp .env.example .env

# 2. Update .env with your configuration

# 3. Build and start
docker-compose build
docker-compose up -d

# 4. Scale services
docker-compose up -d --scale backend=2 --scale frontend=2

# 5. Check status
docker-compose ps
docker-compose logs -f backend
```

### Access Points
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs
- Health: http://localhost:8000/health

## Kubernetes Deployment

### Prerequisites
- Kubernetes 1.24+
- kubectl configured
- Container registry access

### Quick Start

```bash
# 1. Create namespace
kubectl apply -f deploy/k8s/namespace.yaml

# 2. Create secrets
kubectl create secret generic docvault-secrets \
  --from-literal=openrouter_api_key=your-key \
  --namespace=docvault

# 3. Deploy resources
kubectl apply -f deploy/k8s/

# 4. Verify
kubectl get pods -n docvault
kubectl get svc -n docvault
```

See [deploy/k8s/README.md](./k8s/README.md) for detailed Kubernetes deployment guide.

## Architecture

```
┌─────────────────────────────────────┐
│         Load Balancer               │
│         (Nginx/Ingress)             │
└─────────────────────────────────────┘
              │
    ┌─────────┴─────────┐
    │                   │
┌───▼────┐        ┌─────▼────┐
│Frontend│        │ Backend  │
│(Nginx) │        │(FastAPI) │
│  2+    │        │   3+     │
└────────┘        └──────────┘
                          │
                  ┌───────┴───────┐
                  │               │
            ┌─────▼────┐    ┌─────▼────┐
            │ Database │    │ Storage  │
            │  (JSON)  │    │(Local/S3)│
            └──────────┘    └──────────┘
```

## Features

### High Availability
- Multiple replicas for backend and frontend
- Rolling updates with zero downtime
- Health checks and auto-recovery

### Auto-Scaling
- Horizontal Pod Autoscaler (HPA)
- CPU and memory-based scaling
- Configurable min/max replicas

### Production Ready
- Health check endpoints
- Readiness and liveness probes
- Resource limits and requests
- Security contexts
- Persistent storage

## Makefile Commands

```bash
# Docker Compose
make build          # Build images
make up            # Start services
make down          # Stop services
make logs          # View logs
make scale-backend N=3  # Scale backend
make health        # Check health

# Kubernetes
make k8s-deploy    # Deploy to Kubernetes
make k8s-logs      # View logs
make k8s-scale DEPLOYMENT=docvault-backend REPLICAS=5
```

## Environment Variables

See `.env.example` for all available environment variables.

Key variables:
- `DATABASE_TYPE`: Database backend (scalable_json recommended)
- `STORAGE_TYPE`: Storage backend (local/s3/supabase)
- `OPENROUTER_API_KEY`: AI service API key
- `ENVIRONMENT`: Environment (development/production)

## Troubleshooting

### Pods Not Starting
```bash
kubectl describe pod <pod-name>
kubectl logs <pod-name>
```

### Health Check Failures
```bash
curl http://localhost:8000/health
curl http://localhost:8000/ready
```

### Scaling Issues
```bash
kubectl get hpa
  kubectl describe hpa docvault-backend-hpa
  ```

## Support

- [Deployment Guide](./DEPLOYMENT_GUIDE.md) - Detailed deployment instructions
- [Production Checklist](./PRODUCTION_CHECKLIST.md) - Pre-deployment checklist
- [Kubernetes README](./k8s/README.md) - Kubernetes-specific guide

