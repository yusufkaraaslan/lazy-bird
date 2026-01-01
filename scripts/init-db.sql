-- Lazy-Bird v2.0 Database Initialization Script
-- This script runs automatically when the PostgreSQL container starts for the first time

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Enable full-text search
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- Set timezone
SET timezone = 'UTC';

-- Create custom types
DO $$ BEGIN
    CREATE TYPE task_status AS ENUM ('queued', 'running', 'success', 'failed', 'cancelled', 'timeout');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
    CREATE TYPE task_complexity AS ENUM ('simple', 'medium', 'complex');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
    CREATE TYPE account_type AS ENUM ('api', 'subscription');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

-- Grant permissions
GRANT ALL PRIVILEGES ON DATABASE lazy_bird TO lazy_bird;
GRANT ALL ON SCHEMA public TO lazy_bird;

-- Success message
DO $$
BEGIN
    RAISE NOTICE 'Lazy-Bird database initialized successfully!';
    RAISE NOTICE 'Database: lazy_bird';
    RAISE NOTICE 'User: lazy_bird';
    RAISE NOTICE 'Extensions: uuid-ossp, pg_trgm';
    RAISE NOTICE 'Ready for Alembic migrations';
END $$;
