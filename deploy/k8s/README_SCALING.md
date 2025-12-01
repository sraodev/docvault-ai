# Kubernetes Scaling Guide - Million+ Users

## Quick Reference

### Current Configuration
- **Backend**: 5-50 replicas (auto-scale)
- **Frontend**: 3-20 replicas (auto-scale)
- **Celery Workers**: 10+ replicas
- **Redis**: 3-node cluster
- **Storage**: S3 (production)

### Scale Commands

```bash
# Scale backend manually
kubectl scale deployment docvault-backend --replicas=20 -n docvault

# Scale frontend
kubectl scale deployment docvault-frontend --replicas=10 -n docvault

# Scale workers
kubectl scale deployment celery-worker --replicas=30 -n docvault

# Check auto-scaling
kubectl get hpa -n docvault
kubectl describe hpa docvault-backend-hpa -n docvault
```

## Scaling Tiers

### Tier 1: 100k Users
- Backend: 5-10 replicas
- Frontend: 3-5 replicas
- Workers: 10 replicas
- Redis: 3 nodes

### Tier 2: 1M Users
- Backend: 10-30 replicas
- Frontend: 5-10 replicas
- Workers: 20 replicas
- Redis: 5 nodes

### Tier 3: 10M Users
- Backend: 30-100 replicas
- Frontend: 10-30 replicas
- Workers: 50+ replicas
- Redis: 7+ nodes
- Database: Consider migration

## Monitoring

```bash
# Resource usage
kubectl top pods -n docvault

# HPA status
kubectl get hpa -n docvault

# Pod count
kubectl get pods -n docvault | wc -l
```

