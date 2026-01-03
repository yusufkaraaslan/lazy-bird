# Lazy-Bird v2.0 Deployment Guide

Complete guide for deploying Lazy-Bird in production environments.

## Table of Contents

- [System Requirements](#system-requirements)
- [Installation Methods](#installation-methods)
- [Configuration](#configuration)
- [Database Setup](#database-setup)
- [Redis Setup](#redis-setup)
- [Running the API](#running-the-api)
- [Running Workers](#running-workers)
- [Docker Deployment](#docker-deployment)
- [Production Checklist](#production-checklist)
- [Monitoring](#monitoring)
- [Troubleshooting](#troubleshooting)

---

## System Requirements

### Minimum Requirements (Phase 1)
- **OS**: Linux (Ubuntu 20.04+, Debian 11+), macOS, Windows 10/11 (via WSL2)
- **RAM**: 8GB
- **CPU**: 4 cores
- **Disk**: 20GB free space
- **Python**: 3.8+
- **Database**: PostgreSQL 12+ or SQLite 3.31+
- **Redis**: 6.0+

### Recommended (Production)
- **OS**: Linux (Ubuntu 22.04 LTS)
- **RAM**: 16GB
- **CPU**: 8 cores
- **Disk**: 50GB SSD
- **Python**: 3.10+
- **Database**: PostgreSQL 14+
- **Redis**: 7.0+

---

## Installation Methods

### Method 1: PyPI Installation (Recommended)

```bash
# 1. Install lazy-bird
pip install lazy-bird

# 2. Run setup wizard
lazy-bird setup

# 3. Start API server
lazy-bird server
```

### Method 2: From Source

```bash
# 1. Clone repository
git clone https://github.com/yusyus/lazy-bird.git
cd lazy-bird

# 2. Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -e ".[dev]"

# 4. Run setup wizard
python -m lazy_bird.cli setup

# 5. Start API server
python -m lazy_bird.cli server
```

### Method 3: Docker (Production)

```bash
# 1. Clone repository
git clone https://github.com/yusyus/lazy-bird.git
cd lazy-bird

# 2. Start all services with Docker Compose
docker-compose up -d

# Services will be available at:
# - API: http://localhost:8000
# - API Docs: http://localhost:8000/docs
# - PostgreSQL: localhost:5432
# - Redis: localhost:6379
```

---

## Configuration

### Environment Variables

Create a `.env` file in the project root:

```bash
# Environment
ENVIRONMENT=production
DEBUG=false

# API Server
HOST=0.0.0.0
PORT=8000
API_TITLE="Lazy-Bird API"
API_VERSION=2.0.0

# Database
DATABASE_URL=postgresql+asyncpg://lazy_bird:password@localhost:5432/lazy_bird
USE_ASYNC_DB=true

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=

# Security
JWT_SECRET_KEY=your-secret-key-here-change-this
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30
JWT_REFRESH_TOKEN_EXPIRE_MINUTES=10080

# Rate Limiting
RATE_LIMIT_PER_MINUTE=60

# CORS
CORS_ORIGINS=http://localhost:3000,https://yourdomain.com

# Logging
LOG_LEVEL=INFO
LOG_FORMAT=json

# Celery (Workers)
CELERY_BROKER_URL=redis://localhost:6379/1
CELERY_RESULT_BACKEND=redis://localhost:6379/2

# Claude API
CLAUDE_API_KEY=sk-ant-api03-...

# Monitoring (Optional)
SENTRY_DSN=https://...@sentry.io/...
PROMETHEUS_ENABLED=true
```

### Configuration File

Alternative to environment variables, create `~/.config/lazy_birtd/config.yml`:

```yaml
# Lazy-Bird Configuration

# Environment
environment: production
debug: false

# API Server
host: 0.0.0.0
port: 8000

# Database
database_url: postgresql+asyncpg://lazy_bird:password@localhost:5432/lazy_bird

# Redis
redis_host: localhost
redis_port: 6379

# Security
jwt_secret_key: your-secret-key
jwt_access_token_expire_minutes: 30

# Rate Limiting
rate_limit_per_minute: 60

# CORS
cors_origins:
  - http://localhost:3000
  - https://yourdomain.com

# Logging
log_level: INFO
log_format: json
```

---

## Database Setup

### PostgreSQL (Recommended)

```bash
# 1. Install PostgreSQL
sudo apt update
sudo apt install postgresql postgresql-contrib

# 2. Create database and user
sudo -u postgres psql <<EOF
CREATE DATABASE lazy_bird;
CREATE USER lazy_bird WITH PASSWORD 'your-password-here';
GRANT ALL PRIVILEGES ON DATABASE lazy_bird TO lazy_bird;
\q
EOF

# 3. Update DATABASE_URL in .env
DATABASE_URL=postgresql+asyncpg://lazy_bird:your-password@localhost:5432/lazy_bird

# 4. Initialize database schema
python -m lazy_bird.core.database init
```

### SQLite (Development Only)

```bash
# SQLite is configured automatically in development mode
# Database file: ~/.local/share/lazy_birtd/lazy_bird.db
```

---

## Redis Setup

### Linux

```bash
# 1. Install Redis
sudo apt update
sudo apt install redis-server

# 2. Configure Redis for production
sudo nano /etc/redis/redis.conf

# Set these values:
# bind 127.0.0.1  # Or specific IP
# protected-mode yes
# requirepass your-redis-password
# maxmemory 256mb
# maxmemory-policy allkeys-lru

# 3. Restart Redis
sudo systemctl restart redis-server
sudo systemctl enable redis-server

# 4. Test connection
redis-cli ping
# Expected: PONG
```

### Docker

```bash
# Run Redis in Docker
docker run -d \
  --name lazy-bird-redis \
  -p 6379:6379 \
  -v redis-data:/data \
  redis:7-alpine \
  redis-server --requirepass your-password
```

---

## Running the API

### Development

```bash
# Using lazy-bird command
lazy-bird server --debug

# Or using uvicorn directly
uvicorn lazy_bird.api.main:app --reload --host 127.0.0.1 --port 8000
```

### Production (systemd service)

Create `/etc/systemd/system/lazy-bird-api.service`:

```ini
[Unit]
Description=Lazy-Bird API Server
After=network.target postgresql.service redis.service

[Service]
Type=notify
User=lazy_bird
Group=lazy_bird
WorkingDirectory=/opt/lazy-bird
Environment="PATH=/opt/lazy-bird/venv/bin"
EnvironmentFile=/opt/lazy-bird/.env

ExecStart=/opt/lazy-bird/venv/bin/uvicorn lazy_bird.api.main:app \
    --host 0.0.0.0 \
    --port 8000 \
    --workers 4 \
    --loop uvloop \
    --log-config /opt/lazy-bird/logging.conf

Restart=always
RestartSec=5

# Security
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/opt/lazy-bird/logs

[Install]
WantedBy=multi-user.target
```

```bash
# Enable and start service
sudo systemctl daemon-reload
sudo systemctl enable lazy-bird-api
sudo systemctl start lazy-bird-api

# Check status
sudo systemctl status lazy-bird-api

# View logs
sudo journalctl -u lazy-bird-api -f
```

### Production (Gunicorn + Uvicorn workers)

```bash
# Install Gunicorn
pip install gunicorn

# Run with Gunicorn
gunicorn lazy_bird.api.main:app \
    --workers 4 \
    --worker-class uvicorn.workers.UvicornWorker \
    --bind 0.0.0.0:8000 \
    --access-logfile /var/log/lazy-bird/access.log \
    --error-logfile /var/log/lazy-bird/error.log \
    --log-level info
```

---

## Running Workers

Lazy-Bird uses Celery for asynchronous task processing.

### Celery Worker Service

Create `/etc/systemd/system/lazy-bird-worker.service`:

```ini
[Unit]
Description=Lazy-Bird Celery Worker
After=network.target redis.service

[Service]
Type=forking
User=lazy_bird
Group=lazy_bird
WorkingDirectory=/opt/lazy-bird
Environment="PATH=/opt/lazy-bird/venv/bin"
EnvironmentFile=/opt/lazy-bird/.env

ExecStart=/opt/lazy-bird/venv/bin/celery -A lazy_bird.tasks.celery_app worker \
    --loglevel=info \
    --concurrency=4 \
    --logfile=/var/log/lazy-bird/celery-worker.log

Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

```bash
# Enable and start worker
sudo systemctl daemon-reload
sudo systemctl enable lazy-bird-worker
sudo systemctl start lazy-bird-worker
```

### Celery Beat (Scheduler)

For periodic tasks:

Create `/etc/systemd/system/lazy-bird-beat.service`:

```ini
[Unit]
Description=Lazy-Bird Celery Beat Scheduler
After=network.target redis.service

[Service]
Type=simple
User=lazy_bird
Group=lazy_bird
WorkingDirectory=/opt/lazy-bird
Environment="PATH=/opt/lazy-bird/venv/bin"
EnvironmentFile=/opt/lazy-bird/.env

ExecStart=/opt/lazy-bird/venv/bin/celery -A lazy_bird.tasks.celery_app beat \
    --loglevel=info \
    --logfile=/var/log/lazy-bird/celery-beat.log

Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

---

## Docker Deployment

### Docker Compose (Recommended)

`docker-compose.yml`:

```yaml
version: '3.8'

services:
  api:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql+asyncpg://lazy_bird:password@db:5432/lazy_bird
      - REDIS_HOST=redis
      - ENVIRONMENT=production
    depends_on:
      - db
      - redis
    volumes:
      - ./logs:/app/logs
    restart: always

  worker:
    build: .
    command: celery -A lazy_bird.tasks.celery_app worker --loglevel=info
    environment:
      - DATABASE_URL=postgresql+asyncpg://lazy_bird:password@db:5432/lazy_bird
      - REDIS_HOST=redis
      - CELERY_BROKER_URL=redis://redis:6379/1
    depends_on:
      - db
      - redis
    restart: always

  db:
    image: postgres:14-alpine
    environment:
      - POSTGRES_DB=lazy_bird
      - POSTGRES_USER=lazy_bird
      - POSTGRES_PASSWORD=password
    volumes:
      - postgres-data:/var/lib/postgresql/data
    restart: always

  redis:
    image: redis:7-alpine
    command: redis-server --requirepass password
    volumes:
      - redis-data:/data
    restart: always

volumes:
  postgres-data:
  redis-data:
```

```bash
# Deploy
docker-compose up -d

# Scale workers
docker-compose up -d --scale worker=4

# View logs
docker-compose logs -f api

# Stop all services
docker-compose down
```

---

## Production Checklist

### Security

- [ ] Change all default passwords
- [ ] Generate strong JWT secret key
- [ ] Configure HTTPS/TLS (use Let's Encrypt)
- [ ] Set up firewall (ufw, firewalld)
- [ ] Enable rate limiting
- [ ] Configure CORS origins
- [ ] Review security baseline (Docs/Design/security-baseline.md)
- [ ] Rotate API keys every 90 days
- [ ] Set up API key scopes correctly
- [ ] Enable audit logging

### Performance

- [ ] Configure database connection pooling
- [ ] Set up Redis persistence
- [ ] Enable database query caching
- [ ] Configure CDN for static assets (if applicable)
- [ ] Set up load balancer (for multiple API instances)
- [ ] Tune Celery worker concurrency
- [ ] Configure database indexes
- [ ] Set up monitoring and alerting

### Reliability

- [ ] Configure automated backups (database + Redis)
- [ ] Set up health checks
- [ ] Configure log rotation
- [ ] Test disaster recovery plan
- [ ] Set up redundant database (replica)
- [ ] Configure service auto-restart
- [ ] Test rollback procedures

### Monitoring

- [ ] Set up application monitoring (Prometheus/Grafana)
- [ ] Configure error tracking (Sentry)
- [ ] Set up uptime monitoring
- [ ] Configure alerting (PagerDuty, email)
- [ ] Set up log aggregation (ELK, Loki)
- [ ] Monitor API response times
- [ ] Track task execution metrics

---

## Monitoring

### Prometheus + Grafana

```yaml
# docker-compose.yml addition
  prometheus:
    image: prom/prometheus:latest
    ports:
      - "9090:9090"
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus-data:/prometheus

  grafana:
    image: grafana/grafana:latest
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
    volumes:
      - grafana-data:/var/lib/grafana
```

### Health Check Endpoint

```bash
# Check API health
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

---

## Troubleshooting

### API Won't Start

```bash
# Check logs
sudo journalctl -u lazy-bird-api -n 100

# Common issues:
# 1. Database connection failed
#    - Check DATABASE_URL
#    - Ensure PostgreSQL is running
#    - Test connection: psql $DATABASE_URL

# 2. Redis connection failed
#    - Check REDIS_HOST and REDIS_PORT
#    - Test connection: redis-cli ping

# 3. Port already in use
#    - Check: sudo netstat -tlnp | grep 8000
#    - Kill process or change port
```

### Workers Not Processing Tasks

```bash
# Check worker status
sudo systemctl status lazy-bird-worker

# Check Celery logs
tail -f /var/log/lazy-bird/celery-worker.log

# List active workers
celery -A lazy_bird.tasks.celery_app inspect active

# Common issues:
# 1. Redis broker connection failed
# 2. Worker crashed (check logs)
# 3. Task queue full (purge old tasks)
```

### Database Migration Issues

```bash
# Check current migration version
alembic current

# Apply pending migrations
alembic upgrade head

# Rollback last migration
alembic downgrade -1
```

### Performance Issues

```bash
# Check database connections
psql -U lazy_bird -d lazy_bird -c "SELECT count(*) FROM pg_stat_activity;"

# Check Redis memory usage
redis-cli info memory

# Check API response times
curl -w "\nTime: %{time_total}s\n" http://localhost:8000/api/v1/health

# Enable query logging (temporarily)
# Set LOG_LEVEL=DEBUG in .env
```

---

## Additional Resources

- **API Documentation**: [Docs/API_GUIDE.md](API_GUIDE.md)
- **Security Baseline**: [Docs/Design/security-baseline.md](Design/security-baseline.md)
- **Performance Targets**: [Docs/Design/performance-targets.md](Design/performance-targets.md)
- **Contributing Guide**: [CONTRIBUTING.md](../CONTRIBUTING.md)
- **GitHub Issues**: https://github.com/yusyus/lazy-bird/issues

---

**Last Updated:** 2026-01-03
**Version:** 2.0.0
**Status:** Production Ready ✅
