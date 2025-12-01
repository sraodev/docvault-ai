# Kubernetes Scaling Guide - Million+ Users

## Quick Scaling Commands

### Scale Backend
```bash
# Manual scaling
kubectl scale deployment docvault-backend --replicas=20 -n docvault

# Check HPA (auto-scaling)
kubectl get hpa -n docvault
kubectl describe hpa docvault-backend-hpa -n docvault
```

### Scale Frontend
```bash
kubectl scale deployment docvault-frontend --replicas=10 -n docvault
```

### Scale Celery Workers
```bash
kubectl scale deployment celery-worker --replicas=20 -n docvault
```

### Scale Redis (if needed)
```bash
kubectl scale deployment redis --replicas=5 -n docvault
```

## Auto-Scaling Configuration

### Backend HPA
- **Min Replicas**: 5
- **Max Replicas**: 50
- **CPU Target**: 70%
- **Memory Target**: 80%

### Frontend HPA
- **Min Replicas**: 3
- **Max Replicas**: 20
- **CPU Target**: 70%
- **Memory Target**: 80%

## Resource Limits

### Backend Pod
- **Requests**: 2 CPU, 2Gi memory
- **Limits**: 4 CPU, 4Gi memory
- **Workers**: 8 per pod

### Frontend Pod
- **Requests**: 250m CPU, 256Mi memory
- **Limits**: 500m CPU, 512Mi memory

### Celery Worker
- **Requests**: 1 CPU, 1Gi memory
- **Limits**: 2 CPU, 2Gi memory
- **Concurrency**: 4 per worker

## Scaling Scenarios

### Scenario 1: Gradual Growth (100k → 1M users)

**Actions**:
1. Increase backend replicas to 10
2. Add 5 more Celery workers
3. Enable Redis cluster mode
4. Monitor metrics

**Expected**:
- Backend: 10-20 replicas
- Workers: 10-15 workers
- Redis: 3 nodes

### Scenario 2: Sudden Spike (10x traffic)

**Actions**:
1. HPA auto-scales backend to 50
2. HPA auto-scales frontend to 20
3. Scale workers to 30
4. Monitor for bottlenecks

**Expected**:
- Backend: 20-50 replicas
- Frontend: 10-20 replicas
- Workers: 20-30 workers

### Scenario 3: Sustained High Load (1M+ users)

**Actions**:
1. Increase HPA max replicas to 100
2. Add more Redis nodes
3. Consider database migration
4. Implement CDN
5. Multi-region deployment

**Expected**:
- Backend: 50-100 replicas
- Frontend: 20-50 replicas
- Workers: 50+ workers
- Redis: 5+ nodes

## Monitoring Scaling

### Key Metrics to Watch

```bash
# Pod count
kubectl get pods -n docvault | wc -l

# Resource usage
kubectl top pods -n docvault

# HPA status
kubectl get hpa -n docvault

# Queue depth (Celery)
kubectl exec -it <celery-pod> -n docvault -- celery -A app.services.message_queue inspect active

# Redis memory
kubectl exec -it <redis-pod> -n docvault -- redis-cli info memory
```

## Performance Tuning

### Increase Workers Per Pod

Edit `backend/Dockerfile`:
```dockerfile
CMD ["uvicorn", "app.main:app", "--workers", "16", ...]
```

### Increase Resource Limits

Edit `deploy/k8s/backend/deployment.yaml`:
```yaml
resources:
  limits:
    memory: "8Gi"
    cpu: "8000m"
```

### Adjust HPA Thresholds

Edit `deploy/k8s/hpa.yaml`:
```yaml
targetCPUUtilization: 60  # More aggressive scaling
targetMemoryUtilization: 70
```

## Cost Optimization

### Use Spot Instances

Add node selector for spot instances:
```yaml
nodeSelector:
  kubernetes.io/instance-type: spot
```

### Right-Size Resources

Monitor actual usage and adjust:
```bash
kubectl top pods -n docvault --containers
```

### Scale Down During Low Traffic

```bash
# Scale down at night
kubectl scale deployment docvault-backend --replicas=5 -n docvault
```

## Troubleshooting Scaling Issues

### Pods Not Scaling Up

```bash
# Check HPA status
kubectl describe hpa docvault-backend-hpa -n docvault

# Check metrics
kubectl get --raw /apis/metrics.k8s.io/v1beta1/namespaces/docvault/pods
```

### High Resource Usage

```bash
# Check top pods
kubectl top pods -n docvault

# Check node resources
kubectl top nodes

# Review resource limits
kubectl describe pod <pod-name> -n docvault
```

### Slow Response Times

```bash
# Check queue depth
kubectl exec -it <celery-pod> -n docvault -- celery inspect stats

# Check Redis
kubectl exec -it <redis-pod> -n docvault -- redis-cli info stats

# Check database connections
kubectl logs <backend-pod> -n docvault | grep "connection"
```

