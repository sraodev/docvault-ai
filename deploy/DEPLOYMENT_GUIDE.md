# Production Deployment Guide

## Overview

This guide covers deploying DocVault AI in production using Docker containers with scalable orchestration.

## Architecture

```
┌─────────────────────────────────────────────────┐
│              Load Balancer (Nginx)              │
│              Port 80/443                        │
└─────────────────────────────────────────────────┘
                    │
        ┌───────────┴───────────┐
        │                       │
┌───────▼────────┐    ┌────────▼────────┐
│   Frontend     │    │    Backend      │
│   (Nginx)      │    │   (FastAPI)     │
│   Replicas: 2  │    │   Replicas: 3+  │
└────────────────┘    └─────────────────┘
                              │
                    ┌─────────┴─────────┐
                    │                   │
            ┌───────▼──────┐   ┌────────▼────────┐
            │   Database   │   │    Storage      │
            │  (JSON/DB)   │   │  (Local/S3)     │
            └──────────────┘   └─────────────────┘
```

## Prerequisites

- Docker & Docker Compose (for local/testing)
- Kubernetes cluster (for production)
- kubectl configured
- Domain name and SSL certificates (for production)

## Quick Start (Docker Compose)

### 1. Build and Start Services

```bash
# Build images
docker-compose build

# Start services (with scaling)
docker-compose up -d --scale backend=2 --scale frontend=2

# Check status
docker-compose ps

# View logs
docker-compose logs -f backend
```

### 2. Access Application

- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs
- Health Check: http://localhost:8000/health

### 3. Scale Services

```bash
# Scale backend to 4 replicas
docker-compose up -d --scale backend=4

# Scale frontend to 3 replicas
docker-compose up -d --scale frontend=3
```

## Production Deployment (Kubernetes)

### 1. Build and Push Images

```bash
# Build backend image
cd backend
docker build -t your-registry/docvault-backend:latest .
docker push your-registry/docvault-backend:latest

# Build frontend image
cd ../frontend
docker build -t your-registry/docvault-frontend:latest .
docker push your-registry/docvault-frontend:latest
```

### 2. Create Secrets

```bash
# Create secrets from file
kubectl create secret generic docvault-secrets \
  --from-literal=openrouter_api_key=your-key \
  --from-literal=anthropic_api_key=your-key \
  --from-literal=aws_access_key_id=your-key \
  --from-literal=aws_secret_access_key=your-key

# Or from file (update secrets.yaml.example first)
kubectl apply -f deploy/k8s/secrets.yaml
```

### 3. Deploy ConfigMap

```bash
kubectl apply -f deploy/k8s/configmap.yaml
```

### 4. Deploy Persistent Volumes

```bash
kubectl apply -f deploy/k8s/persistent-volumes.yaml
```

### 5. Deploy Backend

```bash
# Update image in deployment.yaml if using custom registry
kubectl apply -f deploy/k8s/backend/deployment.yaml
kubectl apply -f deploy/k8s/backend/service.yaml
```

### 6. Deploy Frontend

```bash
kubectl apply -f deploy/k8s/frontend/deployment.yaml
kubectl apply -f deploy/k8s/frontend/service.yaml
```

### 7. Deploy Ingress

```bash
# Update domain name in ingress.yaml
kubectl apply -f deploy/k8s/ingress.yaml
```

### 8. Deploy Autoscaling

```bash
kubectl apply -f deploy/k8s/hpa.yaml
```

### 9. Verify Deployment

```bash
# Check pods
kubectl get pods -l app=docvault-backend
kubectl get pods -l app=docvault-frontend

# Check services
kubectl get svc

# Check ingress
kubectl get ingress

# Check HPA
kubectl get hpa

# View logs
kubectl logs -f deployment/docvault-backend
```

## Scaling

### Manual Scaling

```bash
# Scale backend
kubectl scale deployment docvault-backend --replicas=5

# Scale frontend
kubectl scale deployment docvault-frontend --replicas=3
```

### Automatic Scaling (HPA)

The HorizontalPodAutoscaler automatically scales based on:
- CPU utilization (target: 70%)
- Memory utilization (target: 80%)

Backend scales between 3-10 replicas
Frontend scales between 2-5 replicas

## Health Checks

### Endpoints

- `/health` - Liveness probe (is container running?)
- `/ready` - Readiness probe (can handle traffic?)

### Monitoring

```bash
# Check health
curl http://localhost:8000/health

# Check readiness
curl http://localhost:8000/ready
```

## Environment Variables

### Backend

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_TYPE` | Database type (json/scalable_json/memory) | scalable_json |
| `STORAGE_TYPE` | Storage type (local/s3/supabase) | local |
| `OPENROUTER_API_KEY` | OpenRouter API key | - |
| `ANTHROPIC_API_KEY` | Anthropic API key | - |
| `AWS_ACCESS_KEY_ID` | AWS access key (for S3) | - |
| `AWS_SECRET_ACCESS_KEY` | AWS secret key (for S3) | - |
| `S3_BUCKET_NAME` | S3 bucket name | - |

### Frontend

Configured via nginx.conf (no environment variables needed)

## Storage

### Local Storage (Development)

Files stored in:
- Uploads: `./backend/uploads`
- Database: `./backend/data`

### Production Storage

Use Persistent Volumes:
- Uploads PVC: 100Gi
- Data PVC: 50Gi

Or use S3/Supabase for cloud storage (configure via environment variables)

## Security

### Container Security

- ✅ Non-root user in containers
- ✅ Read-only filesystem where possible
- ✅ Security headers in Nginx
- ✅ Secrets management via Kubernetes Secrets

### Network Security

- ✅ Internal service communication only
- ✅ Ingress for external access
- ✅ SSL/TLS termination at ingress

## Monitoring

### Logs

```bash
# Docker Compose
docker-compose logs -f backend

# Kubernetes
kubectl logs -f deployment/docvault-backend
```

### Metrics

Kubernetes provides built-in metrics:
- CPU usage
- Memory usage
- Pod count
- Request rate

## Troubleshooting

### Pods Not Starting

```bash
# Check pod status
kubectl describe pod <pod-name>

# Check logs
kubectl logs <pod-name>

# Check events
kubectl get events --sort-by=.metadata.creationTimestamp
```

### Health Check Failures

```bash
# Test health endpoint manually
kubectl exec -it <pod-name> -- curl http://localhost:8000/health

# Check probe configuration
kubectl describe pod <pod-name> | grep -A 5 "Liveness\|Readiness"
```

### Scaling Issues

```bash
# Check HPA status
kubectl describe hpa docvault-backend-hpa

# Check resource usage
kubectl top pods
```

## Production Checklist

- [ ] Images built and pushed to registry
- [ ] Secrets created and secured
- [ ] ConfigMap configured
- [ ] Persistent volumes created
- [ ] Deployments created with proper replicas
- [ ] Services exposed correctly
- [ ] Ingress configured with SSL
- [ ] HPA configured for autoscaling
- [ ] Health checks working
- [ ] Monitoring set up
- [ ] Backup strategy in place
- [ ] Disaster recovery plan ready

## Performance Tuning

### Backend

- Adjust worker count in Dockerfile CMD
- Tune resource limits in deployment.yaml
- Configure connection pooling
- Enable caching where appropriate

### Frontend

- Enable CDN for static assets
- Configure caching headers
- Optimize bundle size
- Use compression

## Backup & Recovery

### Database Backup

```bash
# Backup JSON database
kubectl exec -it <pod-name> -- tar czf /tmp/backup.tar.gz /app/data
kubectl cp <pod-name>:/tmp/backup.tar.gz ./backup.tar.gz
```

### Restore

```bash
# Restore database
kubectl cp ./backup.tar.gz <pod-name>:/tmp/backup.tar.gz
kubectl exec -it <pod-name> -- tar xzf /tmp/backup.tar.gz -C /
```

## Updates & Rollouts

### Rolling Update

```bash
# Update image
kubectl set image deployment/docvault-backend backend=your-registry/docvault-backend:v2

# Monitor rollout
kubectl rollout status deployment/docvault-backend

# Rollback if needed
kubectl rollout undo deployment/docvault-backend
```

## Support

For issues or questions:
1. Check logs: `kubectl logs -f deployment/docvault-backend`
2. Check health: `curl http://localhost:8000/health`
3. Review deployment guide
4. Check Kubernetes events

