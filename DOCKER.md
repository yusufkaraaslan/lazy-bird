# Docker Deployment Guide

Complete guide for deploying Lazy-Bird using Docker and Docker Compose.

## Quick Start

### Development Setup

```bash
# 1. Clone repository
git clone https://github.com/yusyus/lazy-bird.git
cd lazy-bird

# 2. Create environment file
cp .env.example .env

# 3. Update .env with your values (at minimum, set passwords)
nano .env

# 4. Start all services
docker-compose up -d

# 5. Check service health
docker-compose ps

# 6. View logs
docker-compose logs -f api

# 7. Access API
curl http://localhost:8000/api/v1/health
```

**Services will be available at:**
- API: http://localhost:8000
- API Docs: http://localhost:8000/docs
- PostgreSQL: localhost:5432
- Redis: localhost:6379

### Production Setup

```bash
# 1. Clone repository
git clone https://github.com/yusyus/lazy-bird.git
cd lazy-bird

# 2. Create production environment file
cp .env.example .env.prod

# 3. Update ALL security values in .env.prod
# CRITICAL: Change ALL passwords, secret keys, and JWT keys!
nano .env.prod

# 4. Generate SSL certificates (see SSL Setup section below)
./scripts/generate-ssl-certs.sh

# 5. Start production services
docker-compose -f docker-compose.prod.yml --env-file .env.prod up -d

# 6. Check service health
docker-compose -f docker-compose.prod.yml ps

# 7. View logs
docker-compose -f docker-compose.prod.yml logs -f

# 8. Access API through nginx
curl https://localhost/api/v1/health
```

## Architecture

### Development Stack (`docker-compose.yml`)

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  API Server │────▶│ PostgreSQL  │     │    Redis    │
│ (FastAPI)   │     │  (Database) │     │  (Cache/    │
│             │     │             │     │   Broker)   │
└─────────────┘     └─────────────┘     └─────────────┘
       │                                        │
       │                                        │
       ▼                                        ▼
┌─────────────┐                         ┌─────────────┐
│   Celery    │                         │   Celery    │
│   Worker    │◀────────────────────────│    Beat     │
│ (Tasks)     │                         │ (Scheduler) │
└─────────────┘                         └─────────────┘
```

### Production Stack (`docker-compose.prod.yml`)

```
                    ┌─────────────┐
         Internet ──│    Nginx    │── HTTPS/SSL
                    │   (Proxy)   │
                    └─────────────┘
                           │
                           ▼
              ┌────────────────────────┐
              │   Internal Network     │
              │  (No Internet Access)  │
              │                        │
    ┌─────────┼────────────┬───────────┼──────────┐
    │         │            │           │          │
    ▼         ▼            ▼           ▼          ▼
┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐
│  API   │ │Worker 1│ │Worker 2│ │Postgres│ │ Redis  │
│ (x4    │ │(Celery)│ │(Celery)│ │        │ │        │
│workers)│ │        │ │        │ │        │ │        │
└────────┘ └────────┘ └────────┘ └────────┘ └────────┘
```

**Key Production Features:**
- **Nginx Reverse Proxy**: SSL/TLS termination, rate limiting, caching
- **Network Isolation**: Database and Redis on internal network only
- **Resource Limits**: CPU and memory constraints
- **Worker Scaling**: 2 worker instances for parallel task processing
- **Gunicorn**: Production WSGI server with multiple workers
- **Health Checks**: Automatic service restart on failure
- **Security Hardening**: Non-root containers, read-only filesystems

## Services

### API Server

**Development:**
- Command: `uvicorn lazy_bird.api.main:app --reload`
- Port: 8000
- Workers: 1 (auto-reload enabled)

**Production:**
- Command: `gunicorn lazy_bird.api.main:app --workers 4 --worker-class uvicorn.workers.UvicornWorker`
- Port: 8000 (internal)
- Workers: 4
- Resource Limits: 4 CPU cores, 4GB RAM

### PostgreSQL Database

**Development:**
- Image: `postgres:14-alpine`
- Port: 5432 (exposed)
- Data: Volume `postgres_data`

**Production:**
- Image: `postgres:14-alpine`
- Port: Not exposed (internal network only)
- Resource Limits: 2 CPU cores, 2GB RAM
- Health Check: `pg_isready`

### Redis

**Development:**
- Image: `redis:7-alpine`
- Port: 6379 (exposed)
- Persistence: AOF enabled

**Production:**
- Image: `redis:7-alpine`
- Port: Not exposed (internal network only)
- Password protected
- Resource Limits: 1 CPU core, 512MB RAM
- Maxmemory Policy: `allkeys-lru`

### Celery Worker

**Development:**
- Workers: 1
- Concurrency: 4

**Production:**
- Instances: 2 (scaled)
- Concurrency: 4 per instance
- Resource Limits: 2 CPU cores, 2GB RAM per instance
- Task Limits: 100 tasks per worker (auto-restart)
- Time Limits: 3600s hard, 3000s soft

### Celery Beat (Scheduler)

**Both Environments:**
- Single instance (cannot be scaled)
- Schedules periodic tasks
- Resource Limits (prod): 0.5 CPU, 512MB RAM

### Nginx (Production Only)

- Ports: 80 (HTTP), 443 (HTTPS)
- SSL/TLS termination
- Rate limiting: 10 req/s
- Gzip compression
- Static file caching
- SSE support (no buffering)

## Environment Variables

### Required for All Environments

```bash
# Security
SECRET_KEY=<generate-with-openssl-rand-hex-32>
JWT_SECRET_KEY=<generate-with-openssl-rand-hex-32>
DB_PASSWORD=<strong-database-password>

# Database
DATABASE_URL=postgresql://lazy_bird:${DB_PASSWORD}@postgres:5432/lazy_bird

# Redis
REDIS_URL=redis://redis:6379/0
```

### Production-Specific

```bash
# Version
VERSION=2.0.0  # or latest

# Environment
ENVIRONMENT=production
DEBUG=false

# Redis Password
REDIS_PASSWORD=<strong-redis-password>

# CORS
CORS_ORIGINS=https://yourdomain.com,https://api.yourdomain.com

# Logging
LOG_LEVEL=INFO
LOG_FORMAT=json
```

### Optional

```bash
# Claude API (for AI features)
CLAUDE_API_KEY=sk-ant-api03-...

# GitHub/GitLab Integration
GITHUB_TOKEN=ghp_...
GITLAB_TOKEN=glpat_...

# Monitoring
SENTRY_DSN=https://...@sentry.io/...
PROMETHEUS_ENABLED=true
```

## SSL Setup

### Development (Self-Signed Certificate)

```bash
# Create SSL directory
mkdir -p nginx/ssl

# Generate self-signed certificate
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout nginx/ssl/key.pem \
  -out nginx/ssl/cert.pem \
  -subj "/C=US/ST=State/L=City/O=Organization/CN=localhost"
```

### Production (Let's Encrypt)

```bash
# Install certbot
sudo apt install certbot

# Generate certificate (requires domain and port 80 open)
sudo certbot certonly --standalone -d yourdomain.com -d api.yourdomain.com

# Copy certificates to nginx directory
sudo cp /etc/letsencrypt/live/yourdomain.com/fullchain.pem nginx/ssl/cert.pem
sudo cp /etc/letsencrypt/live/yourdomain.com/privkey.pem nginx/ssl/key.pem

# Set permissions
sudo chown $USER:$USER nginx/ssl/*.pem
chmod 644 nginx/ssl/cert.pem
chmod 600 nginx/ssl/key.pem
```

**Auto-renewal:**
```bash
# Add to crontab
0 0 1 * * certbot renew --quiet && docker-compose -f docker-compose.prod.yml restart nginx
```

## Docker Commands

### Basic Operations

```bash
# Start services
docker-compose up -d

# Stop services
docker-compose down

# Restart specific service
docker-compose restart api

# View logs
docker-compose logs -f api
docker-compose logs -f worker
docker-compose logs --tail=100 postgres

# Check service status
docker-compose ps

# Execute command in container
docker-compose exec api bash
docker-compose exec postgres psql -U lazy_bird -d lazy_bird
```

### Database Operations

```bash
# Run migrations
docker-compose exec api alembic upgrade head

# Create new migration
docker-compose exec api alembic revision --autogenerate -m "Description"

# Database backup
docker-compose exec postgres pg_dump -U lazy_bird lazy_bird > backup.sql

# Database restore
cat backup.sql | docker-compose exec -T postgres psql -U lazy_bird -d lazy_bird

# Connect to database
docker-compose exec postgres psql -U lazy_bird -d lazy_bird
```

### Scaling Workers

```bash
# Scale to 4 workers
docker-compose up -d --scale worker=4

# Production (already scaled to 2 in config)
docker-compose -f docker-compose.prod.yml up -d
```

### Resource Monitoring

```bash
# View resource usage
docker stats

# Container details
docker inspect lazy-bird-api-prod

# Disk usage
docker system df
```

## Troubleshooting

### Services Won't Start

```bash
# Check logs
docker-compose logs

# Check specific service
docker-compose logs postgres
docker-compose logs redis

# Verify configuration
docker-compose config

# Remove volumes and restart (CAUTION: deletes data)
docker-compose down -v
docker-compose up -d
```

### Database Connection Failed

```bash
# Check PostgreSQL is running
docker-compose ps postgres

# Check PostgreSQL logs
docker-compose logs postgres

# Verify DATABASE_URL in .env
cat .env | grep DATABASE_URL

# Test connection
docker-compose exec postgres pg_isready -U lazy_bird
```

### API Returns 500 Errors

```bash
# Check API logs
docker-compose logs -f api

# Verify migrations ran
docker-compose exec api alembic current

# Run migrations
docker-compose exec api alembic upgrade head

# Check database connectivity
docker-compose exec api python -c "from lazy_bird.core.database import engine; print('OK')"
```

### Workers Not Processing Tasks

```bash
# Check worker logs
docker-compose logs -f worker

# Check Redis connection
docker-compose exec worker redis-cli -h redis ping

# Check Celery status
docker-compose exec worker celery -A lazy_bird.tasks.celery_app inspect active

# Restart workers
docker-compose restart worker
```

### High Memory Usage

```bash
# Check current usage
docker stats

# Adjust resource limits in docker-compose.prod.yml
services:
  api:
    deploy:
      resources:
        limits:
          memory: 2G  # Reduce if needed

# Restart with new limits
docker-compose -f docker-compose.prod.yml up -d
```

### SSL Certificate Issues

```bash
# Verify certificate files exist
ls -la nginx/ssl/

# Check certificate expiration
openssl x509 -in nginx/ssl/cert.pem -noout -dates

# Test SSL connection
curl -vI https://localhost/health

# Regenerate self-signed certificate
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout nginx/ssl/key.pem \
  -out nginx/ssl/cert.pem
```

## Performance Tuning

### Database

```bash
# Increase connection pool (in .env)
DB_POOL_SIZE=50
DB_MAX_OVERFLOW=20

# PostgreSQL tuning (add to docker-compose.yml)
services:
  postgres:
    command: postgres -c shared_buffers=256MB -c max_connections=200
```

### Redis

```bash
# Increase maxmemory (in docker-compose.prod.yml)
services:
  redis:
    command: redis-server --maxmemory 1gb --maxmemory-policy allkeys-lru
```

### API Workers

```bash
# Increase Gunicorn workers (in docker-compose.prod.yml)
services:
  api:
    command: >
      gunicorn lazy_bird.api.main:app
      --workers 8  # 2x CPU cores
      --worker-class uvicorn.workers.UvicornWorker
```

### Celery Workers

```bash
# Increase concurrency
services:
  worker:
    command: >
      celery -A lazy_bird.tasks.celery_app worker
      --concurrency=8
```

## Security Checklist

Before deploying to production:

- [ ] Change ALL default passwords in `.env.prod`
- [ ] Generate new `SECRET_KEY` and `JWT_SECRET_KEY`
- [ ] Use strong `DB_PASSWORD` and `REDIS_PASSWORD`
- [ ] Configure valid SSL certificate (Let's Encrypt)
- [ ] Set `DEBUG=false` and `ENVIRONMENT=production`
- [ ] Configure correct `CORS_ORIGINS` for your domain
- [ ] Review `nginx/conf.d/lazy-bird.conf` rate limits
- [ ] Enable firewall (only ports 80, 443 open)
- [ ] Set up log rotation
- [ ] Configure automated backups
- [ ] Review `Docs/Design/security-baseline.md`
- [ ] Enable monitoring and alerting
- [ ] Test disaster recovery plan

## Backup & Recovery

### Automated Backups

```bash
# Create backup script
cat > backup.sh <<'EOF'
#!/bin/bash
BACKUP_DIR=/backups
DATE=$(date +%Y%m%d_%H%M%S)

# Database backup
docker-compose exec -T postgres pg_dump -U lazy_bird lazy_bird \
  | gzip > $BACKUP_DIR/db_$DATE.sql.gz

# Redis backup
docker-compose exec -T redis redis-cli --rdb /data/dump.rdb
docker cp lazy-bird-redis:/data/dump.rdb $BACKUP_DIR/redis_$DATE.rdb

# Cleanup old backups (keep 30 days)
find $BACKUP_DIR -name "*.sql.gz" -mtime +30 -delete
find $BACKUP_DIR -name "*.rdb" -mtime +30 -delete
EOF

chmod +x backup.sh

# Add to crontab (daily at 2 AM)
0 2 * * * /path/to/backup.sh
```

### Restore from Backup

```bash
# Restore database
gunzip -c backup.sql.gz | docker-compose exec -T postgres psql -U lazy_bird -d lazy_bird

# Restore Redis
docker cp backup.rdb lazy-bird-redis:/data/dump.rdb
docker-compose restart redis
```

## Migration from v1.1

If upgrading from Lazy-Bird v1.1:

```bash
# 1. Export v1.1 data
python3 scripts/export-v1-data.py > v1-data.json

# 2. Start v2.0 services
docker-compose up -d

# 3. Run migrations
docker-compose exec api alembic upgrade head

# 4. Import v1.1 data
cat v1-data.json | docker-compose exec -T api python3 scripts/import-v1-data.py

# 5. Verify migration
docker-compose exec api python3 -c "from lazy_bird.models import Project; print(Project.query.count())"
```

## Monitoring

### Health Checks

```bash
# API health
curl http://localhost:8000/api/v1/health

# Expected response:
{
  "status": "healthy",
  "database": "connected",
  "redis": "connected",
  "celery": "running",
  "version": "2.0.0"
}
```

### Logs

```bash
# Follow all logs
docker-compose logs -f

# API logs only
docker-compose logs -f api

# Worker logs
docker-compose logs -f worker

# Last 100 lines
docker-compose logs --tail=100
```

### Metrics

Production deployment includes Prometheus metrics:

```bash
# Access metrics
curl http://localhost:9090/metrics
```

## Additional Resources

- **API Documentation**: http://localhost:8000/docs
- **API Guide**: [Docs/API_GUIDE.md](Docs/API_GUIDE.md)
- **Deployment Guide**: [Docs/DEPLOYMENT.md](Docs/DEPLOYMENT.md)
- **Security Baseline**: [Docs/Design/security-baseline.md](Docs/Design/security-baseline.md)
- **GitHub Issues**: https://github.com/yusyus/lazy-bird/issues

---

**Last Updated:** 2026-01-03
**Version:** 2.0.0
**Docker Compose Version:** 3.8
