# Architecture Design - Lazy-Bird v2.0

**Status:** ✅ **IMPLEMENTED** (v2.0 Complete - 2026-01-03)

## Overview

Lazy-Bird v2.0 adopts a microservice architecture with a core engine API and separate client implementations. This design enables multiple project management tools to leverage Lazy-Bird's automation capabilities.

## Architectural Principles

1. **Separation of Concerns**: Engine logic separate from client UI
2. **API-First Design**: All functionality exposed via REST API
3. **Event-Driven Communication**: Webhooks for async notifications
4. **Stateless Services**: Horizontal scaling capability
5. **Database Independence**: Core engine owns its data
6. **Technology Agnostic**: Clients can use any framework

## System Components

### Core Engine (lazy-bird)

**Technology Stack**:
- **Framework**: FastAPI (Python 3.10+)
- **Database**: PostgreSQL 14+
- **Queue**: Celery + Redis
- **ORM**: SQLAlchemy 2.0
- **Validation**: Pydantic v2
- **Authentication**: JWT tokens + API keys
- **Deployment**: Docker + Docker Compose

**Responsibilities**:
- Task queue management
- Claude Code execution
- Git worktree operations
- Test running and validation
- PR creation
- Webhook publishing
- Log storage and streaming
- Usage tracking and billing

**Directory Structure**:
```
lazy_bird/
├── api/                    # FastAPI application
│   ├── main.py            # Application entry point
│   ├── dependencies.py    # Shared dependencies
│   ├── middleware.py      # Auth, CORS, logging
│   └── routers/           # API route handlers
│       ├── projects.py
│       ├── tasks.py
│       ├── accounts.py
│       ├── webhooks.py
│       └── logs.py
├── models/                 # SQLAlchemy models
│   ├── project.py
│   ├── task_run.py
│   ├── claude_account.py
│   └── webhook.py
├── schemas/                # Pydantic schemas
│   ├── project.py
│   ├── task_run.py
│   └── webhook.py
├── services/               # Business logic
│   ├── claude_service.py
│   ├── git_service.py
│   ├── test_runner.py
│   ├── pr_service.py
│   └── webhook_service.py
├── tasks/                  # Celery tasks
│   ├── queue_processor.py
│   ├── task_executor.py
│   └── cleanup.py
├── core/                   # Core utilities
│   ├── config.py
│   ├── database.py
│   ├── security.py
│   └── logging.py
└── tests/                  # Test suite
```

### Web UI Client (lazy-bird-ui)

**Technology Stack**:
- **Framework**: React 18 + TypeScript
- **Build Tool**: Vite
- **State Management**: TanStack Query + Zustand
- **UI Library**: shadcn/ui + Tailwind CSS
- **Router**: React Router v6
- **API Client**: Axios with interceptors
- **Real-time**: EventSource (SSE)

**Responsibilities**:
- Project configuration UI
- Task queue visualization
- Real-time log streaming
- System health dashboard
- Usage and cost monitoring
- Account management
- Webhook configuration

**Routes**:
- `/` - Dashboard overview
- `/projects` - Project list and config
- `/projects/:id` - Project detail
- `/tasks` - Task queue and history
- `/tasks/:id` - Task detail with logs
- `/accounts` - Claude accounts
- `/settings` - System configuration
- `/webhooks` - Webhook management

### Plane Integration (plane-lazy-bird-integration)

**Technology Stack**:
- **Framework**: Django (Plane's framework)
- **Database**: Plane's PostgreSQL (for integration state only)
- **API Client**: httpx (async HTTP)
- **Background Tasks**: Django-Q or Celery

**Responsibilities**:
- Listen to Plane issue state changes
- Call Lazy-Bird API to queue tasks
- Receive webhook events from Lazy-Bird
- Update Plane issues with task status
- Add comments with PR links
- Display automation toggle in Plane UI

**Architecture Pattern** (Thin Client):
```python
# plane_lazy_bird_integration/services.py
class LazyBirdAPIClient:
    """Thin wrapper around Lazy-Bird API"""

    def queue_task(self, issue_id: str, project_id: str) -> str:
        """Queue a task in Lazy-Bird engine"""
        response = httpx.post(
            f"{LAZY_BIRD_API_URL}/api/v1/tasks/queue",
            json={
                "work_item_id": issue_id,
                "project_id": project_id,
                "source": "plane",
                "metadata": {...}
            },
            headers={"Authorization": f"Bearer {API_KEY}"}
        )
        return response.json()["task_run_id"]

    def get_task_status(self, task_run_id: str) -> dict:
        """Get task status from Lazy-Bird"""
        response = httpx.get(
            f"{LAZY_BIRD_API_URL}/api/v1/tasks/{task_run_id}",
            headers={"Authorization": f"Bearer {API_KEY}"}
        )
        return response.json()

# plane_lazy_bird_integration/signals.py
@receiver(post_save, sender=Issue)
def on_issue_state_change(sender, instance, **kwargs):
    """When issue moves to Ready state, queue in Lazy-Bird"""
    if instance.state.name == "Ready":
        client = LazyBirdAPIClient()
        task_run_id = client.queue_task(
            issue_id=str(instance.id),
            project_id=str(instance.project_id)
        )
        # Store mapping for later updates
        TaskRunMapping.objects.create(
            issue_id=instance.id,
            task_run_id=task_run_id
        )

# plane_lazy_bird_integration/webhooks.py
@csrf_exempt
def lazy_bird_webhook(request):
    """Receive webhook events from Lazy-Bird"""
    event = request.json()

    if event["type"] == "task.completed":
        # Find the Plane issue
        mapping = TaskRunMapping.objects.get(
            task_run_id=event["data"]["task_run_id"]
        )
        issue = Issue.objects.get(id=mapping.issue_id)

        # Add comment with PR link
        issue.comments.create(
            comment=f"PR created: {event['data']['pr_url']}",
            actor=system_user
        )

        # Move to "In Review" state
        review_state = State.objects.get(name="In Review")
        issue.state = review_state
        issue.save()
```

## Communication Patterns

### 1. Client → Engine (REST API)

**Request Flow**:
```
Client → API Gateway → Auth Middleware → Route Handler → Service Layer → Database
```

**Example**:
```typescript
// TypeScript client
const client = new LazyBirdClient({
  baseURL: "https://lazy-bird.example.com/api/v1",
  apiKey: "lb_live_abc123..."
});

// Queue a task
const taskRun = await client.tasks.queue({
  projectId: "proj_123",
  workItemId: "issue_456",
  description: "Add health system to player",
  metadata: {
    source: "plane",
    priority: "high"
  }
});

// Get task status
const status = await client.tasks.get(taskRun.id);

// Stream logs
const stream = client.tasks.streamLogs(taskRun.id);
stream.onMessage((log) => {
  console.log(log.message);
});
```

### 2. Engine → Client (Webhooks)

**Event Flow**:
```
Database Event → Webhook Publisher → HTTP POST → Client Webhook Endpoint → Handler
```

**Event Types**:
- `task.queued` - Task added to queue
- `task.started` - Task execution began
- `task.progress` - Progress update
- `task.log` - New log entry
- `task.completed` - Task finished successfully
- `task.failed` - Task failed
- `task.timeout` - Task exceeded time limit
- `pr.created` - Pull request created
- `pr.merged` - Pull request merged
- `usage.limit_reached` - Daily limit reached

**Payload Example**:
```json
{
  "id": "evt_abc123",
  "type": "task.completed",
  "timestamp": "2025-12-30T10:30:00Z",
  "data": {
    "task_run_id": "run_xyz789",
    "project_id": "proj_123",
    "work_item_id": "issue_456",
    "status": "success",
    "pr_url": "https://github.com/user/repo/pull/42",
    "branch_name": "feature-issue-456",
    "summary": "Added health system with 100 max health...",
    "tests_passed": true,
    "duration_seconds": 127,
    "cost_usd": 0.42
  }
}
```

### 3. Real-time Logs (Server-Sent Events)

**Stream Flow**:
```
Celery Task → Redis Pub/Sub → SSE Endpoint → EventSource → Client UI
```

**Client Implementation**:
```typescript
const eventSource = new EventSource(
  `${API_URL}/api/v1/tasks/${taskRunId}/logs/stream`,
  {
    headers: {
      Authorization: `Bearer ${apiKey}`
    }
  }
);

eventSource.onmessage = (event) => {
  const log = JSON.parse(event.data);
  appendLog(log);
};

eventSource.onerror = (error) => {
  console.error("SSE error:", error);
  eventSource.close();
};
```

## Database Architecture

### Core Engine Database

**PostgreSQL** with tables:
- `projects` - Project configurations
- `claude_accounts` - Claude API credentials
- `framework_presets` - Framework-specific settings
- `task_runs` - Task execution records
- `task_run_logs` - Detailed execution logs
- `webhook_subscriptions` - Client webhook endpoints
- `daily_usage` - Usage tracking and billing
- `api_keys` - Client authentication tokens

**Isolation**: Engine owns this database completely. Clients never access directly.

### Client Databases

**Plane Integration**:
- Uses Plane's existing database
- Only stores `TaskRunMapping` table for correlation
- All task data lives in Lazy-Bird engine

**Web UI**:
- No backend database (stateless)
- All state fetched from engine API
- Local storage for user preferences only

## Security Model

### Authentication

**API Keys**:
- Format: `lb_live_abc123...` (32 chars)
- Scoped to project or organization
- Can be read-only or read-write
- Revocable at any time

**JWT Tokens** (for Web UI):
- Short-lived (15 min)
- Refresh token rotation
- Claims: user_id, project_id, permissions

### Authorization

**Role-Based Access Control** (RBAC):
- `admin` - Full access to all resources
- `developer` - Create tasks, view logs, manage projects
- `viewer` - Read-only access

**Project-Level Permissions**:
- Users belong to projects
- API keys scoped to projects
- Tasks isolated by project

### Network Security

- HTTPS only (TLS 1.3)
- CORS configuration for trusted origins
- Rate limiting (100 req/min per API key)
- Request size limits (10 MB max)
- SQL injection protection (SQLAlchemy ORM)
- XSS protection (response sanitization)

## Deployment Architecture

### Docker Compose (Development)

```yaml
version: '3.8'

services:
  postgres:
    image: postgres:14-alpine
    environment:
      POSTGRES_DB: lazy_bird
      POSTGRES_USER: lazy_bird
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine
    command: redis-server --appendonly yes
    volumes:
      - redis_data:/data

  api:
    build: .
    command: uvicorn lazy_bird.api.main:app --host 0.0.0.0 --port 8000
    ports:
      - "8000:8000"
    environment:
      DATABASE_URL: postgresql://lazy_bird:${DB_PASSWORD}@postgres/lazy_bird
      REDIS_URL: redis://redis:6379/0
    depends_on:
      - postgres
      - redis
    volumes:
      - ./lazy_bird:/app/lazy_bird
      - git_repos:/var/lib/lazy_bird/repos

  worker:
    build: .
    command: celery -A lazy_bird.tasks worker --loglevel=info
    environment:
      DATABASE_URL: postgresql://lazy_bird:${DB_PASSWORD}@postgres/lazy_bird
      REDIS_URL: redis://redis:6379/0
    depends_on:
      - postgres
      - redis
    volumes:
      - git_repos:/var/lib/lazy_bird/repos

  beat:
    build: .
    command: celery -A lazy_bird.tasks beat --loglevel=info
    environment:
      DATABASE_URL: postgresql://lazy_bird:${DB_PASSWORD}@postgres/lazy_bird
      REDIS_URL: redis://redis:6379/0
    depends_on:
      - postgres
      - redis

volumes:
  postgres_data:
  redis_data:
  git_repos:
```

### Production (Kubernetes)

- **API**: Deployment with 3+ replicas, HPA
- **Worker**: StatefulSet with persistent volumes for git repos
- **Database**: Managed PostgreSQL (RDS, Cloud SQL)
- **Redis**: Managed Redis (ElastiCache, Memorystore)
- **Ingress**: NGINX with TLS termination
- **Monitoring**: Prometheus + Grafana
- **Logging**: ELK stack or Cloud Logging

## Scalability Considerations

### Horizontal Scaling

**API Service**:
- Stateless FastAPI instances
- Scale based on CPU/memory usage
- Load balancer distribution

**Celery Workers**:
- Independent worker pools
- Scale based on queue depth
- Task routing by priority

### Performance Optimization

- **Database**: Connection pooling (SQLAlchemy)
- **Caching**: Redis for frequently accessed data
- **Async I/O**: FastAPI async endpoints
- **Background Tasks**: Offload to Celery
- **CDN**: Static assets for Web UI

### Resource Limits

- Max concurrent tasks: Configurable per project
- Queue depth limit: 1000 tasks
- Log retention: 30 days (configurable)
- Task timeout: 30 minutes default

## Monitoring and Observability

### Metrics

- Request rate and latency (API endpoints)
- Task queue depth and processing time
- Success/failure rates
- Claude API costs
- Database query performance
- Worker resource usage

### Logging

- Structured JSON logs
- Request/response logging
- Task execution logs
- Error tracking with stack traces
- Audit logs for security events

### Alerting

- Failed task threshold exceeded
- API error rate spike
- Database connection issues
- Worker pool saturation
- Cost budget exceeded

## Disaster Recovery

### Backup Strategy

- **Database**: Daily snapshots, 30-day retention
- **Git Repos**: Mirrored to S3/GCS
- **Configuration**: Version controlled in git
- **Logs**: Archived to object storage

### Recovery Procedures

- Database restore from snapshot
- Worker pool rebuild from Docker images
- Configuration reapply from git
- Task queue replay from Redis persistence

---

**Next**: [Database Schema](02-database-schema.md)
