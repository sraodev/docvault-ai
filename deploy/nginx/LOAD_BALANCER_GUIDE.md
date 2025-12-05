# Production Load Balancer Setup Guide

## Overview

This guide explains how to set up and configure the production load balancer for DocVault AI with multiple backend instances.

## Architecture

```
                    ┌─────────────────┐
                    │   Nginx LB      │
                    │  (Port 80/443)  │
                    └────────┬────────┘
                             │
                ┌────────────┼────────────┐
                │            │            │
         ┌──────▼───┐  ┌─────▼─────┐  ┌──▼──────┐
         │ Backend 1│  │ Backend 2  │  │Backend 3│
         │  :8000   │  │  :8000     │  │ :8000   │
         └──────┬───┘  └─────┬─────┘  └──┬──────┘
                │            │            │
                └────────────┼────────────┘
                             │
                    ┌────────▼────────┐
                    │     Redis       │
                    │   (Shared)      │
                    └─────────────────┘
```

## Features

### Load Balancing
- **Algorithm**: Least Connections (least_conn)
- **Health Checks**: Automatic failover on backend failure
- **Backup Servers**: Automatic promotion when primary fails

### Rate Limiting
- **API Endpoints**: 100 requests/second (burst: 20)
- **Upload Endpoints**: 10 requests/second (burst: 5)
- **General Traffic**: 200 requests/second (burst: 50)
- **Connection Limits**: 50 concurrent connections per IP

### SSL/TLS
- **Protocols**: TLSv1.2, TLSv1.3
- **Ciphers**: Modern, secure cipher suites
- **OCSP Stapling**: Enabled for performance
- **HSTS**: Strict Transport Security headers

### Health Checks
- **Backend Health**: `/health` endpoint
- **Nginx Status**: `/nginx_status` (internal)
- **Automatic Failover**: 3 failures = 30s timeout

## Quick Start

### 1. Generate SSL Certificates (for HTTPS)

```bash
# Using Let's Encrypt (recommended)
certbot certonly --standalone -d your-domain.com

# Copy certificates to nginx/ssl directory
cp /etc/letsencrypt/live/your-domain.com/fullchain.pem deploy/nginx/ssl/cert.pem
cp /etc/letsencrypt/live/your-domain.com/privkey.pem deploy/nginx/ssl/key.pem
```

### 2. Start Load Balancer Stack

```bash
cd deploy/nginx
docker-compose -f docker-compose.loadbalancer.yml up -d
```

### 3. Verify Setup

```bash
# Check nginx status
curl http://localhost/nginx_status

# Check backend health
curl http://localhost/api/health

# Check load balancing (should rotate between backends)
for i in {1..10}; do curl -H "X-Request-ID: test-$i" http://localhost/api/health; done
```

## Configuration

### Scaling Backends

Edit `docker-compose.loadbalancer.yml`:

```yaml
services:
  backend-4:
    # Copy backend-1 configuration
    # Update container_name
```

Update `nginx.conf` upstream:

```nginx
upstream backend {
    server backend-1:8000;
    server backend-2:8000;
    server backend-3:8000;
    server backend-4:8000;  # Add new instance
}
```

### Rate Limiting

Adjust rate limits in `nginx.conf`:

```nginx
# API rate limit: 100 req/s
limit_req_zone $binary_remote_addr zone=api_limit:10m rate=100r/s;

# Upload rate limit: 10 req/s
limit_req_zone $binary_remote_addr zone=upload_limit:10m rate=10r/s;
```

### SSL Configuration

1. Place certificates in `deploy/nginx/ssl/`:
   - `cert.pem` - SSL certificate
   - `key.pem` - Private key
   - `ca.pem` - CA certificate (for OCSP)

2. Uncomment HTTPS server block in `nginx.conf`

3. Enable HTTPS redirect in HTTP server block:
```nginx
server {
    listen 80;
    return 301 https://$host$request_uri;
}
```

## Monitoring

### Nginx Status

```bash
# Access nginx status (internal network only)
curl http://localhost/nginx_status
```

Output:
```
Active connections: 10
server accepts handled requests
 100 100 1000
Reading: 2 Writing: 3 Waiting: 5
```

### Logs

```bash
# Access logs
docker exec docvault-nginx-lb tail -f /var/log/nginx/access.log

# Error logs
docker exec docvault-nginx-lb tail -f /var/log/nginx/error.log

# JSON logs (for log aggregation)
docker exec docvault-nginx-lb tail -f /var/log/nginx/access.json.log
```

### Health Checks

```bash
# Backend health
curl http://localhost/api/health

# Load balancer health
curl http://localhost/health

# Individual backend health (from within network)
curl http://backend-1:8000/health
curl http://backend-2:8000/health
curl http://backend-3:8000/health
```

## Load Balancing Algorithms

### Current: Least Connections

```nginx
upstream backend {
    least_conn;  # Routes to backend with fewest active connections
    server backend-1:8000;
    server backend-2:8000;
    server backend-3:8000;
}
```

### Alternative: Round Robin (default)

```nginx
upstream backend {
    # Round robin (default)
    server backend-1:8000;
    server backend-2:8000;
    server backend-3:8000;
}
```

### Alternative: IP Hash (sticky sessions)

```nginx
upstream backend {
    ip_hash;  # Routes same IP to same backend
    server backend-1:8000;
    server backend-2:8000;
    server backend-3:8000;
}
```

### Alternative: Weighted

```nginx
upstream backend {
    server backend-1:8000 weight=3;  # 3x traffic
    server backend-2:8000 weight=2;  # 2x traffic
    server backend-3:8000 weight=1;  # 1x traffic
}
```

## Performance Tuning

### Worker Processes

```nginx
worker_processes auto;  # Auto-detect CPU cores
```

### Worker Connections

```nginx
events {
    worker_connections 4096;  # Increase for high traffic
}
```

### Keepalive

```nginx
keepalive_timeout 65;
keepalive_requests 1000;
```

### Buffering

```nginx
proxy_buffering on;
proxy_buffer_size 4k;
proxy_buffers 8 4k;
proxy_busy_buffers_size 8k;
```

## Security

### Rate Limiting

Prevents DDoS and abuse:
- API: 100 req/s per IP
- Upload: 10 req/s per IP
- General: 200 req/s per IP

### Connection Limits

```nginx
limit_conn conn_limit 50;  # Max 50 concurrent connections per IP
```

### Security Headers

- `Strict-Transport-Security`: Force HTTPS
- `X-Frame-Options`: Prevent clickjacking
- `X-Content-Type-Options`: Prevent MIME sniffing
- `X-XSS-Protection`: XSS protection
- `Content-Security-Policy`: XSS and injection protection

## Troubleshooting

### Backend Not Receiving Requests

1. Check backend health:
```bash
docker exec docvault-backend-1 curl http://localhost:8000/health
```

2. Check nginx upstream status:
```bash
docker exec docvault-nginx-lb curl http://localhost/nginx_status
```

3. Check nginx error logs:
```bash
docker exec docvault-nginx-lb tail -f /var/log/nginx/error.log
```

### Rate Limiting Issues

If legitimate users are rate limited:

1. Increase rate limits in `nginx.conf`
2. Whitelist specific IPs:
```nginx
geo $limit {
    default 1;
    10.0.0.0/8 0;  # Internal network
    192.168.0.0/16 0;  # Private network
}

map $limit $limit_key {
    0 "";
    1 $binary_remote_addr;
}

limit_req_zone $limit_key zone=api_limit:10m rate=100r/s;
```

### SSL Certificate Issues

1. Verify certificate files exist:
```bash
ls -la deploy/nginx/ssl/
```

2. Check certificate validity:
```bash
openssl x509 -in deploy/nginx/ssl/cert.pem -text -noout
```

3. Test SSL configuration:
```bash
nginx -t -c deploy/nginx/nginx.conf
```

## Production Checklist

- [ ] SSL certificates configured
- [ ] HTTPS redirect enabled
- [ ] Rate limiting configured
- [ ] Health checks working
- [ ] Multiple backend instances running
- [ ] Monitoring/logging configured
- [ ] Security headers enabled
- [ ] Backup servers configured
- [ ] Load testing completed
- [ ] Failover tested

## Scaling

### Horizontal Scaling

Add more backend instances:

```bash
docker-compose -f docker-compose.loadbalancer.yml up -d --scale backend-1=3
```

### Vertical Scaling

Increase resources in `docker-compose.loadbalancer.yml`:

```yaml
deploy:
  resources:
    limits:
      cpus: '4'  # Increase from 2
      memory: 4G  # Increase from 2G
```

## Best Practices

1. **Always use HTTPS in production**
2. **Monitor backend health regularly**
3. **Set up log aggregation** (ELK, Loki, etc.)
4. **Use sticky sessions** only if necessary
5. **Test failover scenarios**
6. **Keep nginx updated**
7. **Monitor rate limit metrics**
8. **Set up alerts** for backend failures

