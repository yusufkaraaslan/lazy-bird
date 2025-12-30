# Database Schema - Lazy-Bird v2.0

## Overview

Lazy-Bird v2.0 uses PostgreSQL 14+ as the primary database. The schema is designed for:
- **Data integrity**: Foreign keys, constraints, indexes
- **Performance**: Optimized queries, efficient joins
- **Scalability**: Partitioning ready for high-volume tables
- **Auditability**: Created/updated timestamps, soft deletes

## Schema Diagram

```
┌─────────────────┐         ┌─────────────────┐
│    projects     │────┐    │ claude_accounts │
└─────────────────┘    │    └─────────────────┘
        │              │             │
        │              │             │
        │              ▼             ▼
        │         ┌─────────────────────┐
        └────────▶│    task_runs        │
                  └─────────────────────┘
                           │
                           │
                           ▼
                  ┌─────────────────────┐
                  │   task_run_logs     │
                  └─────────────────────┘

┌─────────────────┐         ┌─────────────────┐
│framework_presets│         │  daily_usage    │
└─────────────────┘         └─────────────────┘

┌─────────────────┐         ┌─────────────────┐
│webhook_subscript│         │    api_keys     │
└─────────────────┘         └─────────────────┘
```

## Table Definitions

### 1. projects

**Description**: Project configurations and settings

```sql
CREATE TABLE projects (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    slug VARCHAR(100) UNIQUE NOT NULL,

    -- Git configuration
    repo_url VARCHAR(500) NOT NULL,
    default_branch VARCHAR(100) DEFAULT 'main',

    -- Framework configuration
    framework_preset_id UUID REFERENCES framework_presets(id),
    project_type VARCHAR(50) NOT NULL,  -- 'python', 'nodejs', 'rust', 'godot', etc.

    -- Custom commands (override preset)
    test_command VARCHAR(500),
    build_command VARCHAR(500),
    lint_command VARCHAR(500),
    format_command VARCHAR(500),

    -- Automation settings
    automation_enabled BOOLEAN DEFAULT false,
    ready_state_name VARCHAR(100),  -- e.g., "Ready", "To Do"
    in_progress_state_name VARCHAR(100) DEFAULT 'In Progress',
    review_state_name VARCHAR(100) DEFAULT 'In Review',
    done_state_name VARCHAR(100) DEFAULT 'Done',

    -- Resource limits
    max_concurrent_tasks INTEGER DEFAULT 3,
    task_timeout_seconds INTEGER DEFAULT 1800,  -- 30 minutes
    max_cost_per_task_usd DECIMAL(10, 2) DEFAULT 5.00,
    daily_cost_limit_usd DECIMAL(10, 2) DEFAULT 50.00,

    -- Integration settings
    github_installation_id BIGINT,
    gitlab_project_id BIGINT,
    source_platform VARCHAR(50),  -- 'github', 'gitlab', 'plane', etc.
    source_platform_url VARCHAR(500),

    -- Claude account
    claude_account_id UUID REFERENCES claude_accounts(id),

    -- Metadata
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    deleted_at TIMESTAMP WITH TIME ZONE,  -- Soft delete

    -- Full-text search
    search_vector TSVECTOR GENERATED ALWAYS AS (
        to_tsvector('english', name || ' ' || COALESCE(repo_url, ''))
    ) STORED
);

CREATE INDEX idx_projects_slug ON projects(slug);
CREATE INDEX idx_projects_source_platform ON projects(source_platform);
CREATE INDEX idx_projects_automation_enabled ON projects(automation_enabled);
CREATE INDEX idx_projects_search ON projects USING gin(search_vector);
CREATE INDEX idx_projects_deleted_at ON projects(deleted_at) WHERE deleted_at IS NULL;
```

**Sample Data**:
```sql
INSERT INTO projects (name, slug, repo_url, project_type, automation_enabled) VALUES
('My Game', 'my-game', 'https://github.com/user/my-game', 'godot', true),
('Backend API', 'backend-api', 'https://github.com/user/backend', 'python', true);
```

### 2. claude_accounts

**Description**: Claude API credentials and settings

```sql
CREATE TABLE claude_accounts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    account_type VARCHAR(50) NOT NULL,  -- 'api', 'subscription'

    -- API mode
    api_key VARCHAR(500),  -- Encrypted at application layer

    -- Subscription mode
    config_directory VARCHAR(500),
    session_token VARCHAR(500),  -- Encrypted at application layer

    -- Settings
    model VARCHAR(100) DEFAULT 'claude-sonnet-4-5',
    max_tokens INTEGER DEFAULT 8000,
    temperature DECIMAL(3, 2) DEFAULT 0.7,

    -- Usage limits
    monthly_budget_usd DECIMAL(10, 2),
    is_active BOOLEAN DEFAULT true,

    -- Metadata
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    last_used_at TIMESTAMP WITH TIME ZONE,

    CONSTRAINT check_account_type CHECK (account_type IN ('api', 'subscription')),
    CONSTRAINT check_api_key_required CHECK (
        (account_type = 'api' AND api_key IS NOT NULL) OR
        (account_type = 'subscription' AND config_directory IS NOT NULL)
    )
);

CREATE INDEX idx_claude_accounts_active ON claude_accounts(is_active);
CREATE INDEX idx_claude_accounts_type ON claude_accounts(account_type);
```

**Sample Data**:
```sql
INSERT INTO claude_accounts (name, account_type, api_key, model) VALUES
('Production API', 'api', 'sk-ant-...encrypted...', 'claude-sonnet-4-5');
```

### 3. framework_presets

**Description**: Framework-specific command presets

```sql
CREATE TABLE framework_presets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) UNIQUE NOT NULL,
    display_name VARCHAR(255) NOT NULL,
    description TEXT,

    -- Framework details
    framework_type VARCHAR(50) NOT NULL,  -- 'game_engine', 'backend', 'frontend', 'language'
    language VARCHAR(50),  -- 'gdscript', 'python', 'javascript', 'rust', etc.

    -- Default commands
    test_command VARCHAR(500) NOT NULL,
    build_command VARCHAR(500),
    lint_command VARCHAR(500),
    format_command VARCHAR(500),

    -- Additional configuration
    config_files JSONB,  -- e.g., {"godot": "project.godot", "python": "pyproject.toml"}

    -- Metadata
    is_builtin BOOLEAN DEFAULT false,  -- Built-in presets vs user-created
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_framework_presets_type ON framework_presets(framework_type);
CREATE INDEX idx_framework_presets_builtin ON framework_presets(is_builtin);
```

**Sample Data**:
```sql
INSERT INTO framework_presets (name, display_name, framework_type, language, test_command, build_command) VALUES
('godot', 'Godot Engine 4.x', 'game_engine', 'gdscript',
 'godot --headless -s addons/gdUnit4/bin/GdUnitCmdTool.gd --test-suite all',
 'godot --headless --export-release "Linux/X11" build/game.x86_64'),

('django', 'Django', 'backend', 'python',
 'pytest',
 'python manage.py collectstatic --noinput'),

('react', 'React + Vite', 'frontend', 'javascript',
 'npm test',
 'npm run build');
```

### 4. task_runs

**Description**: Task execution records

```sql
CREATE TABLE task_runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Relations
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    claude_account_id UUID REFERENCES claude_accounts(id),

    -- Work item identification
    work_item_id VARCHAR(255) NOT NULL,  -- External ID (e.g., GitHub issue #42)
    work_item_url VARCHAR(500),
    work_item_title VARCHAR(500),
    work_item_description TEXT,

    -- Task details
    task_type VARCHAR(50) DEFAULT 'feature',  -- 'feature', 'bugfix', 'refactor'
    complexity VARCHAR(20),  -- 'simple', 'medium', 'complex'
    prompt TEXT NOT NULL,

    -- Execution status
    status VARCHAR(50) NOT NULL DEFAULT 'queued',
    -- Possible statuses: queued, running, success, failed, cancelled, timeout

    -- Progress tracking
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    duration_seconds INTEGER,
    retry_count INTEGER DEFAULT 0,
    max_retries INTEGER DEFAULT 3,

    -- Git details
    branch_name VARCHAR(255),
    worktree_path VARCHAR(500),
    commit_sha VARCHAR(40),

    -- Results
    pr_url VARCHAR(500),
    pr_number INTEGER,
    tests_passed BOOLEAN,
    test_output TEXT,
    error_message TEXT,

    -- Resource usage
    tokens_used INTEGER,
    cost_usd DECIMAL(10, 4),

    -- Metadata
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT check_status CHECK (
        status IN ('queued', 'running', 'success', 'failed', 'cancelled', 'timeout')
    ),
    CONSTRAINT check_complexity CHECK (
        complexity IS NULL OR complexity IN ('simple', 'medium', 'complex')
    )
);

-- Indexes
CREATE INDEX idx_task_runs_project ON task_runs(project_id);
CREATE INDEX idx_task_runs_status ON task_runs(status);
CREATE INDEX idx_task_runs_work_item ON task_runs(work_item_id);
CREATE INDEX idx_task_runs_created_at ON task_runs(created_at DESC);
CREATE INDEX idx_task_runs_project_status ON task_runs(project_id, status);

-- Partition by created_at (monthly) for high-volume scenarios
-- ALTER TABLE task_runs PARTITION BY RANGE (created_at);
```

**Sample Data**:
```sql
INSERT INTO task_runs (
    project_id, work_item_id, work_item_title, prompt, status
) VALUES (
    '123e4567-e89b-12d3-a456-426614174000',
    'issue-42',
    'Add health system to player',
    'Implement a health system with 100 max health, take_damage and heal methods',
    'queued'
);
```

### 5. task_run_logs

**Description**: Detailed execution logs

```sql
CREATE TABLE task_run_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    task_run_id UUID NOT NULL REFERENCES task_runs(id) ON DELETE CASCADE,

    -- Log details
    level VARCHAR(20) NOT NULL,  -- 'debug', 'info', 'warning', 'error'
    message TEXT NOT NULL,

    -- Context
    step VARCHAR(100),  -- 'init', 'planning', 'implementation', 'testing', etc.
    tool_name VARCHAR(50),  -- 'Read', 'Write', 'Bash', etc.

    -- Additional data
    metadata JSONB DEFAULT '{}',

    -- Timestamp
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT check_level CHECK (
        level IN ('debug', 'info', 'warning', 'error', 'critical')
    )
);

-- Indexes
CREATE INDEX idx_task_run_logs_task_run ON task_run_logs(task_run_id);
CREATE INDEX idx_task_run_logs_created_at ON task_run_logs(created_at);
CREATE INDEX idx_task_run_logs_level ON task_run_logs(level);
CREATE INDEX idx_task_run_logs_task_run_created ON task_run_logs(task_run_id, created_at);

-- Partition by created_at (daily) for very high-volume logging
-- ALTER TABLE task_run_logs PARTITION BY RANGE (created_at);
```

**Sample Data**:
```sql
INSERT INTO task_run_logs (task_run_id, level, message, step) VALUES
('abc-123', 'info', 'Starting task execution', 'init'),
('abc-123', 'info', 'Created git worktree at /tmp/agent-abc', 'init'),
('abc-123', 'info', 'Running Claude Code CLI', 'implementation');
```

### 6. webhook_subscriptions

**Description**: Client webhook endpoint registrations

```sql
CREATE TABLE webhook_subscriptions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Subscription details
    url VARCHAR(500) NOT NULL,
    secret VARCHAR(255) NOT NULL,  -- For HMAC signature verification

    -- Scope
    project_id UUID REFERENCES projects(id) ON DELETE CASCADE,
    -- NULL project_id means global subscription

    -- Event filtering
    events TEXT[] NOT NULL,  -- Array of event types to subscribe to
    -- e.g., {'task.completed', 'task.failed', 'pr.created'}

    -- Status
    is_active BOOLEAN DEFAULT true,
    last_triggered_at TIMESTAMP WITH TIME ZONE,
    failure_count INTEGER DEFAULT 0,
    last_failure_at TIMESTAMP WITH TIME ZONE,

    -- Metadata
    description TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT check_url_format CHECK (url ~ '^https?://')
);

CREATE INDEX idx_webhook_subscriptions_project ON webhook_subscriptions(project_id);
CREATE INDEX idx_webhook_subscriptions_active ON webhook_subscriptions(is_active);
CREATE INDEX idx_webhook_subscriptions_events ON webhook_subscriptions USING gin(events);
```

**Sample Data**:
```sql
INSERT INTO webhook_subscriptions (url, secret, project_id, events) VALUES
('https://plane.example.com/api/webhooks/lazy-bird',
 'whsec_abc123...',
 '123e4567-e89b-12d3-a456-426614174000',
 ARRAY['task.completed', 'task.failed', 'pr.created']);
```

### 7. daily_usage

**Description**: Daily usage tracking and billing

```sql
CREATE TABLE daily_usage (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Scope
    project_id UUID REFERENCES projects(id) ON DELETE CASCADE,
    date DATE NOT NULL,

    -- Usage metrics
    tasks_queued INTEGER DEFAULT 0,
    tasks_completed INTEGER DEFAULT 0,
    tasks_failed INTEGER DEFAULT 0,

    -- Resource consumption
    total_tokens_used BIGINT DEFAULT 0,
    total_cost_usd DECIMAL(10, 4) DEFAULT 0,
    total_duration_seconds BIGINT DEFAULT 0,

    -- Metadata
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,

    UNIQUE(project_id, date)
);

CREATE INDEX idx_daily_usage_project_date ON daily_usage(project_id, date DESC);
CREATE INDEX idx_daily_usage_date ON daily_usage(date DESC);
```

**Sample Data**:
```sql
INSERT INTO daily_usage (project_id, date, tasks_completed, total_cost_usd) VALUES
('123e4567-e89b-12d3-a456-426614174000', '2025-12-30', 5, 2.35);
```

### 8. api_keys

**Description**: API authentication tokens

```sql
CREATE TABLE api_keys (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Key details
    key_hash VARCHAR(64) NOT NULL UNIQUE,  -- SHA-256 hash of actual key
    key_prefix VARCHAR(10) NOT NULL,  -- First 8 chars for identification (e.g., "lb_live_")
    name VARCHAR(255) NOT NULL,

    -- Scope
    project_id UUID REFERENCES projects(id) ON DELETE CASCADE,
    -- NULL project_id means organization-level key

    -- Permissions
    scopes TEXT[] NOT NULL DEFAULT ARRAY['read'],
    -- Possible scopes: 'read', 'write', 'admin'

    -- Status
    is_active BOOLEAN DEFAULT true,
    expires_at TIMESTAMP WITH TIME ZONE,
    last_used_at TIMESTAMP WITH TIME ZONE,

    -- Metadata
    created_by VARCHAR(255),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    revoked_at TIMESTAMP WITH TIME ZONE,

    CONSTRAINT check_scopes CHECK (
        scopes <@ ARRAY['read', 'write', 'admin']::TEXT[]
    )
);

CREATE INDEX idx_api_keys_hash ON api_keys(key_hash);
CREATE INDEX idx_api_keys_prefix ON api_keys(key_prefix);
CREATE INDEX idx_api_keys_project ON api_keys(project_id);
CREATE INDEX idx_api_keys_active ON api_keys(is_active);
```

**Sample Data**:
```sql
INSERT INTO api_keys (key_hash, key_prefix, name, scopes) VALUES
('abc123...hashed...', 'lb_live_a', 'Production API Key', ARRAY['read', 'write']);
```

## Migrations

### Alembic Configuration

```python
# alembic/env.py
from lazy_bird.core.database import Base
from lazy_bird.models import *  # Import all models

target_metadata = Base.metadata

def run_migrations_online():
    """Run migrations in 'online' mode."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            compare_server_default=True
        )

        with context.begin_transaction():
            context.run_migrations()
```

### Migration Commands

```bash
# Create a new migration
alembic revision --autogenerate -m "Add projects table"

# Apply migrations
alembic upgrade head

# Rollback one migration
alembic downgrade -1

# Show current version
alembic current

# Show migration history
alembic history
```

## Data Integrity

### Foreign Key Constraints

All foreign keys use `ON DELETE CASCADE` or `ON DELETE SET NULL` appropriately:
- `task_runs.project_id` → CASCADE (delete tasks when project deleted)
- `task_run_logs.task_run_id` → CASCADE (delete logs when task deleted)
- `projects.claude_account_id` → SET NULL (keep project if account deleted)

### Check Constraints

- Status values validated against enum-like checks
- Account types validated
- URL formats validated
- Cost values must be >= 0

### Triggers

```sql
-- Auto-update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_projects_updated_at BEFORE UPDATE ON projects
FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_task_runs_updated_at BEFORE UPDATE ON task_runs
FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Calculate task duration on completion
CREATE OR REPLACE FUNCTION calculate_task_duration()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.status IN ('success', 'failed', 'timeout', 'cancelled') AND NEW.started_at IS NOT NULL THEN
        NEW.duration_seconds = EXTRACT(EPOCH FROM (NEW.completed_at - NEW.started_at))::INTEGER;
    END IF;
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER calculate_task_run_duration BEFORE UPDATE ON task_runs
FOR EACH ROW EXECUTE FUNCTION calculate_task_duration();
```

## Performance Optimization

### Indexing Strategy

- **B-tree indexes** for equality and range queries (status, created_at)
- **GIN indexes** for full-text search and array containment (events, scopes)
- **Partial indexes** for soft deletes (WHERE deleted_at IS NULL)
- **Composite indexes** for common query patterns (project_id + status)

### Query Optimization

```sql
-- Efficient task queue query
SELECT * FROM task_runs
WHERE status = 'queued'
  AND project_id = $1
ORDER BY created_at ASC
LIMIT 10;
-- Uses: idx_task_runs_project_status

-- Recent logs for a task
SELECT * FROM task_run_logs
WHERE task_run_id = $1
  AND created_at > NOW() - INTERVAL '1 hour'
ORDER BY created_at ASC;
-- Uses: idx_task_run_logs_task_run_created

-- Daily usage summary
SELECT
    date,
    SUM(tasks_completed) as total_tasks,
    SUM(total_cost_usd) as total_cost
FROM daily_usage
WHERE project_id = $1
  AND date >= CURRENT_DATE - INTERVAL '30 days'
GROUP BY date
ORDER BY date DESC;
-- Uses: idx_daily_usage_project_date
```

### Connection Pooling

```python
# lazy_bird/core/database.py
from sqlalchemy import create_engine
from sqlalchemy.pool import QueuePool

engine = create_engine(
    DATABASE_URL,
    poolclass=QueuePool,
    pool_size=20,          # Max connections
    max_overflow=10,       # Extra connections if needed
    pool_pre_ping=True,    # Check connection health
    pool_recycle=3600,     # Recycle connections every hour
)
```

## Backup and Recovery

### Backup Strategy

```bash
# Daily full backup
pg_dump -Fc lazy_bird > backups/lazy_bird_$(date +%Y%m%d).dump

# Point-in-time recovery setup
wal_level = replica
archive_mode = on
archive_command = 'cp %p /var/lib/postgresql/archive/%f'
```

### Recovery

```bash
# Restore from dump
pg_restore -d lazy_bird backups/lazy_bird_20251230.dump

# Point-in-time recovery
pg_restore -d lazy_bird_restore backups/base_backup.dump
# Then replay WAL logs to specific timestamp
```

---

**Next**: [API Endpoints](03-api-endpoints.md)
