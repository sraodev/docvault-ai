# Production Load Balancer

Production-ready nginx load balancer configuration for DocVault AI.

## Quick Start

```bash
# 1. Setup SSL certificates
./setup-ssl.sh your-domain.com

# 2. Start load balancer stack
./start-loadbalancer.sh
```

## Features

✅ **Load Balancing**: Multiple backend instances with least-connections algorithm  
✅ **Health Checks**: Automatic failover on backend failure  
✅ **Rate Limiting**: Per-endpoint rate limits (API, upload, general)  
✅ **SSL/TLS**: Full HTTPS support with modern ciphers  
✅ **Security Headers**: HSTS, CSP, XSS protection  
✅ **Monitoring**: Nginx status endpoint and JSON logs  
✅ **High Performance**: Optimized for high traffic  

## Architecture

```
Internet → Nginx LB → Backend-1
                    → Backend-2
                    → Backend-3
                    → Frontend-1
                    → Frontend-2
```

## Configuration Files

- `nginx.conf` - Main nginx configuration
- `docker-compose.loadbalancer.yml` - Docker Compose stack
- `setup-ssl.sh` - SSL certificate setup script
- `start-loadbalancer.sh` - Startup script

## Documentation

See [LOAD_BALANCER_GUIDE.md](./LOAD_BALANCER_GUIDE.md) for detailed documentation.

