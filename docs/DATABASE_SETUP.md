# PostgreSQL Database Setup Guide

This document provides instructions for setting up PostgreSQL for Lazy-Bird v2.0.

## Prerequisites

- PostgreSQL 14+
- Or Docker with Docker Compose

---

## Option 1: Docker Compose (Recommended)

### Start Database

```bash
# Start PostgreSQL and Redis
docker-compose up -d postgres redis

# Verify services are running
docker-compose ps

# Check logs
docker-compose logs postgres
```

### Access Database

```bash
# Connect to database
docker-compose exec postgres psql -U lazy_bird -d lazy_bird

# Run SQL query
docker-compose exec postgres psql -U lazy_bird -d lazy_bird -c "SELECT version();"
```

### Stop Database

```bash
# Stop services
docker-compose stop

# Remove containers (keeps data)
docker-compose down

# Remove containers AND data
docker-compose down -v
```

---

## Option 2: Manual PostgreSQL Setup

### 1. Install PostgreSQL

**Ubuntu/Debian:**
```bash
sudo apt update
sudo apt install postgresql postgresql-contrib
```

**Fedora/RHEL:**
```bash
sudo dnf install postgresql-server postgresql-contrib
sudo postgresql-setup --initdb
sudo systemctl start postgresql
sudo systemctl enable postgresql
```

**macOS:**
```bash
brew install postgresql@14
brew services start postgresql@14
```

**Arch Linux:**
```bash
sudo pacman -S postgresql
sudo -u postgres initdb -D /var/lib/postgres/data
sudo systemctl start postgresql
sudo systemctl enable postgresql
```

### 2. Create Database and User

```bash
# Switch to postgres user
sudo -u postgres psql

# Run these commands in psql:
CREATE DATABASE lazy_bird;
CREATE USER lazy_bird WITH PASSWORD 'your_secure_password_here';
GRANT ALL PRIVILEGES ON DATABASE lazy_bird TO lazy_bird;

# Enable required extensions
\c lazy_bird
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

# Create custom types
CREATE TYPE task_status AS ENUM ('queued', 'running', 'success', 'failed', 'cancelled', 'timeout');
CREATE TYPE task_complexity AS ENUM ('simple', 'medium', 'complex');
CREATE TYPE account_type AS ENUM ('api', 'subscription');

# Exit
\q
```

### 3. Configure PostgreSQL Access

Edit `/etc/postgresql/14/main/pg_hba.conf` (path may vary):

```
# Add this line for local development
local   lazy_bird       lazy_bird                               md5
host    lazy_bird       lazy_bird       127.0.0.1/32            md5
host    lazy_bird       lazy_bird       ::1/128                 md5
```

Restart PostgreSQL:
```bash
sudo systemctl restart postgresql
```

### 4. Test Connection

```bash
# Test connection
psql -U lazy_bird -d lazy_bird -h localhost

# Or with connection string
psql postgresql://lazy_bird:your_password@localhost:5432/lazy_bird
```

---

## Option 3: Using Existing PostgreSQL Instance

If you already have PostgreSQL running:

```bash
# Connect as admin user
psql -U postgres

# Create database and user
CREATE DATABASE lazy_bird;
CREATE USER lazy_bird WITH PASSWORD 'your_password';
ALTER DATABASE lazy_bird OWNER TO lazy_bird;
GRANT ALL PRIVILEGES ON DATABASE lazy_bird TO lazy_bird;

# Switch to lazy_bird database
\c lazy_bird

# Enable extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

# Create custom types
CREATE TYPE task_status AS ENUM ('queued', 'running', 'success', 'failed', 'cancelled', 'timeout');
CREATE TYPE task_complexity AS ENUM ('simple', 'medium', 'complex');
CREATE TYPE account_type AS ENUM ('api', 'subscription');

\q
```

---

## Environment Configuration

Update your `.env` file with the database connection string:

```bash
# For Docker Compose (default)
DATABASE_URL=postgresql://lazy_bird:lazy_bird_dev_password_change_me@localhost:5432/lazy_bird

# For manual setup
DATABASE_URL=postgresql://lazy_bird:your_password@localhost:5432/lazy_bird

# For remote database
DATABASE_URL=postgresql://lazy_bird:your_password@your-host:5432/lazy_bird
```

---

## Verify Setup

```bash
# Test database connection with Python
python3 -c "
from sqlalchemy import create_engine
engine = create_engine('postgresql://lazy_bird:your_password@localhost:5432/lazy_bird')
with engine.connect() as conn:
    result = conn.execute('SELECT version();')
    print('✅ Database connection successful!')
    print(result.fetchone()[0])
"
```

---

## Troubleshooting

### Connection Refused

```bash
# Check if PostgreSQL is running
sudo systemctl status postgresql

# Check if port 5432 is listening
sudo netstat -tulpn | grep 5432

# Test connection
psql -U lazy_bird -d lazy_bird -h localhost
```

### Authentication Failed

```bash
# Reset password
sudo -u postgres psql -c "ALTER USER lazy_bird WITH PASSWORD 'new_password';"

# Update .env with new password
```

### Permission Denied

```bash
# Grant all privileges
sudo -u postgres psql -d lazy_bird -c "GRANT ALL PRIVILEGES ON DATABASE lazy_bird TO lazy_bird;"
sudo -u postgres psql -d lazy_bird -c "GRANT ALL ON SCHEMA public TO lazy_bird;"
```

---

## Next Steps

After database setup is complete:

1. ✅ Verify database connection
2. ➡️ Initialize Alembic (Issue #55)
3. ➡️ Create database migrations
4. ➡️ Apply migrations

---

## Useful Commands

```bash
# List databases
psql -U lazy_bird -l

# Connect to database
psql -U lazy_bird -d lazy_bird

# List tables
\dt

# Describe table
\d table_name

# View extensions
\dx

# Check database size
SELECT pg_size_pretty(pg_database_size('lazy_bird'));

# Backup database
pg_dump -U lazy_bird lazy_bird > backup.sql

# Restore database
psql -U lazy_bird lazy_bird < backup.sql
```

---

**Status**: Setup complete - ready for Alembic migrations
