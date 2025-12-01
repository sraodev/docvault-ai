# Kubernetes Deployment

Complete Kubernetes deployment configuration for DocVault AI with production-ready scaling and high availability.

## Structure

```
deploy/k8s/
├── backend/
│   ├── deployment.yaml      # Backend deployment (3+ replicas)
│   └── service.yaml         # Backend service (ClusterIP)
├── frontend/
│   ├── deployment.yaml      # Frontend deployment (2+ replicas)
│   └── service.yaml         # Frontend service (ClusterIP)
├── configmap.yaml           # Configuration (non-sensitive)
├── secrets.yaml.example     # Secrets template (sensitive)
├── persistent-volumes.yaml  # Storage volumes
├── ingress.yaml             # External access & SSL
├── hpa.yaml                 # Auto-scaling configuration
└── README.md                # This file
```

## Quick Start

### 1. Create Secrets

```bash
kubectl create secret generic docvault-secrets \
  --from-literal=openrouter_api_key=your-key \
  --from-literal=anthropic_api_key=your-key
```

### 2. Deploy Everything

```bash
# Deploy in order
kubectl apply -f configmap.yaml
kubectl apply -f persistent-volumes.yaml
kubectl apply -f backend/
kubectl apply -f frontend/
kubectl apply -f ingress.yaml
kubectl apply -f hpa.yaml
```

### 3. Verify

```bash
kubectl get pods
kubectl get svc
kubectl get ingress
kubectl get hpa
```

## Features

### High Availability
- ✅ Backend: 3+ replicas with rolling updates
- ✅ Frontend: 2+ replicas
- ✅ Health checks (liveness, readiness, startup)
- ✅ Pod disruption budgets

### Auto-Scaling
- ✅ Horizontal Pod Autoscaler (HPA)
- ✅ CPU-based scaling (70% target)
- ✅ Memory-based scaling (80% target)
- ✅ Backend: 3-10 replicas
- ✅ Frontend: 2-5 replicas

### Production Ready
- ✅ Persistent storage for uploads and data
- ✅ SSL/TLS termination at ingress
- ✅ Resource limits and requests
- ✅ Security contexts (non-root)
- ✅ Secrets management

### Monitoring
- ✅ Health check endpoints
- ✅ Readiness probes
- ✅ Liveness probes
- ✅ Startup probes

## Configuration

### Environment Variables

Set in `configmap.yaml`:
- `DATABASE_TYPE`: Database type (scalable_json recommended)
- `STORAGE_TYPE`: Storage backend (local/s3/supabase)
- `CORS_ORIGINS`: Allowed CORS origins

Set in `secrets.yaml`:
- `OPENROUTER_API_KEY`: AI service API key
- `ANTHROPIC_API_KEY`: Alternative AI service key
- `AWS_ACCESS_KEY_ID`: For S3 storage
- `AWS_SECRET_ACCESS_KEY`: For S3 storage

### Resource Limits

Backend:
- Requests: 1 CPU, 1Gi memory
- Limits: 2 CPU, 2Gi memory

Frontend:
- Requests: 250m CPU, 256Mi memory
- Limits: 500m CPU, 512Mi memory

### Storage

- Uploads: 100Gi persistent volume
- Data: 50Gi persistent volume
- Access mode: ReadWriteMany (shared across pods)

## Scaling

### Manual Scaling

```bash
# Scale backend
kubectl scale deployment docvault-backend --replicas=5

# Scale frontend
kubectl scale deployment docvault-frontend --replicas=3
```

### Automatic Scaling

HPA automatically scales based on:
- CPU utilization (target: 70%)
- Memory utilization (target: 80%)

View HPA status:
```bash
kubectl get hpa
kubectl describe hpa docvault-backend-hpa
```

## Health Checks

### Endpoints

- `/health` - Liveness probe
- `/ready` - Readiness probe

### Probe Configuration

Backend:
- Liveness: `/health` every 30s
- Readiness: `/ready` every 10s
- Startup: `/health` every 10s (max 2min)

Frontend:
- Liveness: `/health` every 30s
- Readiness: `/health` every 10s

## Updates

### Rolling Update

```bash
# Update image
kubectl set image deployment/docvault-backend backend=your-registry/docvault-backend:v2

# Monitor
kubectl rollout status deployment/docvault-backend

# Rollback if needed
kubectl rollout undo deployment/docvault-backend
```

## Troubleshooting

### Check Pod Status

```bash
kubectl get pods -l app=docvault-backend
kubectl describe pod <pod-name>
```

### View Logs

```bash
kubectl logs -f deployment/docvault-backend
kubectl logs -f <pod-name>
```

### Check Events

```bash
kubectl get events --sort-by=.metadata.creationTimestamp
```

### Test Health Endpoints

```bash
kubectl exec -it <pod-name> -- curl http://localhost:8000/health
```

## Security

- ✅ Non-root containers
- ✅ Secrets stored securely
- ✅ Network policies (if configured)
- ✅ SSL/TLS at ingress
- ✅ Security contexts

## Performance

### Optimizations

1. **Connection Pooling**: Backend uses connection pooling
2. **Caching**: Nginx caching for static assets
3. **Compression**: Gzip enabled
4. **Resource Limits**: Prevent resource exhaustion
5. **Auto-scaling**: Scale based on demand

### Monitoring

```bash
# Resource usage
kubectl top pods

# HPA metrics
kubectl describe hpa docvault-backend-hpa
```

## Backup

### Database Backup

```bash
# Backup
kubectl exec -it <pod-name> -- tar czf /tmp/backup.tar.gz /app/data
kubectl cp <pod-name>:/tmp/backup.tar.gz ./backup.tar.gz

# Restore
kubectl cp ./backup.tar.gz <pod-name>:/tmp/backup.tar.gz
kubectl exec -it <pod-name> -- tar xzf /tmp/backup.tar.gz -C /
```

## Production Checklist

- [ ] Secrets created and secured
- [ ] ConfigMap configured
- [ ] Persistent volumes created
- [ ] Images pushed to registry
- [ ] Deployments created
- [ ] Services exposed
- [ ] Ingress configured with SSL
- [ ] HPA configured
- [ ] Health checks working
- [ ] Monitoring set up
- [ ] Backup strategy in place

## Support

See `deploy/DEPLOYMENT_GUIDE.md` for detailed deployment instructions.
