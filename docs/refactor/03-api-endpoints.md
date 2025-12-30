# API Endpoints - Lazy-Bird v2.0

## Overview

The Lazy-Bird REST API follows RESTful principles with consistent conventions:
- **Base URL**: `https://api.lazy-bird.example.com/api/v1`
- **Authentication**: Bearer token (`Authorization: Bearer <api_key>`)
- **Content-Type**: `application/json`
- **Pagination**: Cursor-based with `cursor` and `limit` parameters
- **Error Format**: RFC 7807 Problem Details
- **Rate Limiting**: 100 requests/minute per API key

## Authentication

### API Key Format

```
lb_live_abc123def456...  (32 characters after prefix)
```

### Request Headers

```http
GET /api/v1/projects HTTP/1.1
Host: api.lazy-bird.example.com
Authorization: Bearer lb_live_abc123def456...
Content-Type: application/json
Accept: application/json
```

### Error Responses

```json
{
  "type": "https://lazy-bird.dev/errors/authentication-failed",
  "title": "Authentication Failed",
  "status": 401,
  "detail": "Invalid or expired API key",
  "instance": "/api/v1/projects"
}
```

## Endpoints

### Health & Status

#### `GET /health`

Health check endpoint (no auth required)

**Response 200**:
```json
{
  "status": "healthy",
  "version": "2.0.0",
  "timestamp": "2025-12-30T10:30:00Z",
  "services": {
    "database": "healthy",
    "redis": "healthy",
    "celery": "healthy"
  }
}
```

#### `GET /api/v1/status`

System status and metrics (requires auth)

**Response 200**:
```json
{
  "queue_depth": 5,
  "active_tasks": 3,
  "workers_online": 2,
  "avg_task_duration_seconds": 127,
  "success_rate_24h": 0.95
}
```

---

### Projects

#### `GET /api/v1/projects`

List all projects

**Query Parameters**:
- `limit` (integer, default 20, max 100)
- `cursor` (string, pagination cursor)
- `automation_enabled` (boolean, filter)

**Response 200**:
```json
{
  "data": [
    {
      "id": "proj_abc123",
      "name": "My Game Project",
      "slug": "my-game",
      "repo_url": "https://github.com/user/my-game",
      "project_type": "godot",
      "automation_enabled": true,
      "framework_preset": {
        "id": "preset_123",
        "name": "godot",
        "display_name": "Godot Engine 4.x"
      },
      "claude_account": {
        "id": "acct_456",
        "name": "Production API"
      },
      "stats": {
        "total_tasks": 42,
        "tasks_this_month": 12,
        "success_rate": 0.92
      },
      "created_at": "2025-12-01T00:00:00Z",
      "updated_at": "2025-12-30T10:00:00Z"
    }
  ],
  "pagination": {
    "next_cursor": "crs_xyz789",
    "has_more": true
  }
}
```

#### `POST /api/v1/projects`

Create a new project

**Request Body**:
```json
{
  "name": "My New Project",
  "slug": "my-new-project",
  "repo_url": "https://github.com/user/my-new-project",
  "project_type": "python",
  "framework_preset_id": "preset_django",
  "automation_enabled": false,
  "ready_state_name": "Ready",
  "claude_account_id": "acct_456",
  "max_concurrent_tasks": 3,
  "daily_cost_limit_usd": 50.00
}
```

**Response 201**:
```json
{
  "id": "proj_new123",
  "name": "My New Project",
  "slug": "my-new-project",
  ...
}
```

#### `GET /api/v1/projects/:id`

Get project details

**Response 200**:
```json
{
  "id": "proj_abc123",
  "name": "My Game Project",
  "slug": "my-game",
  "repo_url": "https://github.com/user/my-game",
  "project_type": "godot",
  "automation_enabled": true,
  "ready_state_name": "Ready",
  "in_progress_state_name": "In Progress",
  "review_state_name": "In Review",
  "done_state_name": "Done",
  "test_command": "godot --headless -s addons/gdUnit4/bin/GdUnitCmdTool.gd --test-suite all",
  "build_command": null,
  "max_concurrent_tasks": 3,
  "task_timeout_seconds": 1800,
  "max_cost_per_task_usd": 5.00,
  "daily_cost_limit_usd": 50.00,
  "framework_preset": { ... },
  "claude_account": { ... },
  "created_at": "2025-12-01T00:00:00Z",
  "updated_at": "2025-12-30T10:00:00Z"
}
```

#### `PATCH /api/v1/projects/:id`

Update project

**Request Body**:
```json
{
  "automation_enabled": true,
  "max_concurrent_tasks": 5
}
```

**Response 200**: Updated project object

#### `DELETE /api/v1/projects/:id`

Delete project (soft delete)

**Response 204**: No content

---

### Tasks

#### `GET /api/v1/tasks`

List task runs

**Query Parameters**:
- `project_id` (string, filter by project)
- `status` (string, filter by status: queued, running, success, failed)
- `work_item_id` (string, filter by work item)
- `limit` (integer, default 20)
- `cursor` (string, pagination)

**Response 200**:
```json
{
  "data": [
    {
      "id": "run_xyz789",
      "project_id": "proj_abc123",
      "work_item_id": "issue-42",
      "work_item_title": "Add health system to player",
      "work_item_url": "https://github.com/user/repo/issues/42",
      "status": "success",
      "task_type": "feature",
      "complexity": "medium",
      "branch_name": "feature-issue-42",
      "pr_url": "https://github.com/user/repo/pull/43",
      "pr_number": 43,
      "tests_passed": true,
      "started_at": "2025-12-30T10:15:00Z",
      "completed_at": "2025-12-30T10:17:07Z",
      "duration_seconds": 127,
      "tokens_used": 5234,
      "cost_usd": 0.42,
      "retry_count": 0,
      "created_at": "2025-12-30T10:14:30Z"
    }
  ],
  "pagination": {
    "next_cursor": "crs_abc123",
    "has_more": false
  }
}
```

#### `POST /api/v1/tasks/queue`

Queue a new task

**Request Body**:
```json
{
  "project_id": "proj_abc123",
  "work_item_id": "issue-45",
  "work_item_url": "https://github.com/user/repo/issues/45",
  "work_item_title": "Fix jump physics bug",
  "work_item_description": "Player can double jump when they shouldn't",
  "task_type": "bugfix",
  "complexity": "simple",
  "prompt": "Fix the jump physics in player.gd. Player should only be able to jump when on ground.",
  "metadata": {
    "source": "plane",
    "priority": "high",
    "labels": ["bug", "physics"]
  }
}
```

**Response 201**:
```json
{
  "id": "run_new123",
  "status": "queued",
  "project_id": "proj_abc123",
  "work_item_id": "issue-45",
  "created_at": "2025-12-30T10:30:00Z",
  "estimated_start_time": "2025-12-30T10:32:00Z"
}
```

#### `GET /api/v1/tasks/:id`

Get task details

**Response 200**:
```json
{
  "id": "run_xyz789",
  "project": {
    "id": "proj_abc123",
    "name": "My Game Project",
    "slug": "my-game"
  },
  "work_item_id": "issue-42",
  "work_item_title": "Add health system to player",
  "work_item_description": "Player needs health tracking...",
  "work_item_url": "https://github.com/user/repo/issues/42",
  "status": "success",
  "task_type": "feature",
  "complexity": "medium",
  "prompt": "Add health system with 100 max health...",
  "branch_name": "feature-issue-42",
  "worktree_path": "/var/lib/lazy_bird/repos/proj_abc123/worktrees/run_xyz789",
  "commit_sha": "abc123def456...",
  "pr_url": "https://github.com/user/repo/pull/43",
  "pr_number": 43,
  "tests_passed": true,
  "test_output": "Ran 5 tests, all passed",
  "started_at": "2025-12-30T10:15:00Z",
  "completed_at": "2025-12-30T10:17:07Z",
  "duration_seconds": 127,
  "tokens_used": 5234,
  "cost_usd": 0.42,
  "retry_count": 0,
  "claude_account": {
    "id": "acct_456",
    "name": "Production API"
  },
  "metadata": {
    "source": "plane",
    "priority": "high"
  },
  "created_at": "2025-12-30T10:14:30Z",
  "updated_at": "2025-12-30T10:17:07Z"
}
```

#### `POST /api/v1/tasks/:id/cancel`

Cancel a queued or running task

**Response 200**:
```json
{
  "id": "run_xyz789",
  "status": "cancelled",
  "cancelled_at": "2025-12-30T10:30:00Z"
}
```

#### `POST /api/v1/tasks/:id/retry`

Retry a failed task

**Response 201**: New task run object

#### `GET /api/v1/tasks/:id/logs`

Get task execution logs

**Query Parameters**:
- `level` (string, filter: debug, info, warning, error)
- `limit` (integer, default 100)
- `cursor` (string)

**Response 200**:
```json
{
  "data": [
    {
      "id": "log_abc123",
      "task_run_id": "run_xyz789",
      "level": "info",
      "message": "Starting task execution",
      "step": "init",
      "tool_name": null,
      "metadata": {},
      "created_at": "2025-12-30T10:15:00Z"
    },
    {
      "id": "log_abc124",
      "level": "info",
      "message": "Created git worktree at /tmp/agent-xyz",
      "step": "init",
      "created_at": "2025-12-30T10:15:02Z"
    }
  ],
  "pagination": {
    "next_cursor": "crs_logs123",
    "has_more": true
  }
}
```

#### `GET /api/v1/tasks/:id/logs/stream`

Stream task logs in real-time (Server-Sent Events)

**Headers**:
```
Accept: text/event-stream
```

**Response 200**:
```
data: {"id":"log_abc125","level":"info","message":"Running tests...","created_at":"2025-12-30T10:16:30Z"}

data: {"id":"log_abc126","level":"info","message":"Tests passed!","created_at":"2025-12-30T10:16:45Z"}

data: {"id":"log_abc127","level":"info","message":"Creating PR...","created_at":"2025-12-30T10:17:00Z"}
```

---

### Claude Accounts

#### `GET /api/v1/accounts`

List Claude accounts

**Response 200**:
```json
{
  "data": [
    {
      "id": "acct_456",
      "name": "Production API",
      "account_type": "api",
      "model": "claude-sonnet-4-5",
      "is_active": true,
      "monthly_budget_usd": 1000.00,
      "usage_this_month_usd": 342.50,
      "last_used_at": "2025-12-30T10:17:00Z",
      "created_at": "2025-12-01T00:00:00Z"
    }
  ]
}
```

#### `POST /api/v1/accounts`

Create Claude account

**Request Body**:
```json
{
  "name": "Dev Account",
  "account_type": "api",
  "api_key": "sk-ant-...",
  "model": "claude-sonnet-4-5",
  "monthly_budget_usd": 500.00
}
```

**Response 201**: Created account object (api_key not returned)

#### `GET /api/v1/accounts/:id`

Get account details

**Response 200**: Account object

#### `PATCH /api/v1/accounts/:id`

Update account

**Request Body**:
```json
{
  "is_active": false,
  "monthly_budget_usd": 1500.00
}
```

**Response 200**: Updated account object

#### `DELETE /api/v1/accounts/:id`

Delete account

**Response 204**: No content

---

### Webhooks

#### `GET /api/v1/webhooks`

List webhook subscriptions

**Query Parameters**:
- `project_id` (string, filter by project)

**Response 200**:
```json
{
  "data": [
    {
      "id": "wh_abc123",
      "url": "https://plane.example.com/api/webhooks/lazy-bird",
      "project_id": "proj_abc123",
      "events": ["task.completed", "task.failed", "pr.created"],
      "is_active": true,
      "last_triggered_at": "2025-12-30T10:17:07Z",
      "failure_count": 0,
      "created_at": "2025-12-15T00:00:00Z"
    }
  ]
}
```

#### `POST /api/v1/webhooks`

Create webhook subscription

**Request Body**:
```json
{
  "url": "https://myapp.example.com/webhooks/lazy-bird",
  "secret": "whsec_abc123...",
  "project_id": "proj_abc123",
  "events": ["task.completed", "task.failed"],
  "description": "Plane integration webhook"
}
```

**Response 201**: Created webhook object

#### `GET /api/v1/webhooks/:id`

Get webhook details

**Response 200**: Webhook object

#### `PATCH /api/v1/webhooks/:id`

Update webhook

**Request Body**:
```json
{
  "is_active": false,
  "events": ["task.completed"]
}
```

**Response 200**: Updated webhook object

#### `DELETE /api/v1/webhooks/:id`

Delete webhook

**Response 204**: No content

#### `POST /api/v1/webhooks/:id/test`

Send test webhook event

**Response 200**:
```json
{
  "success": true,
  "status_code": 200,
  "response_time_ms": 125
}
```

---

### Framework Presets

#### `GET /api/v1/presets`

List framework presets

**Response 200**:
```json
{
  "data": [
    {
      "id": "preset_godot",
      "name": "godot",
      "display_name": "Godot Engine 4.x",
      "description": "Godot game engine with gdUnit4 test framework",
      "framework_type": "game_engine",
      "language": "gdscript",
      "test_command": "godot --headless -s addons/gdUnit4/bin/GdUnitCmdTool.gd --test-suite all",
      "build_command": "godot --headless --export-release \"Linux/X11\" build/game.x86_64",
      "is_builtin": true
    }
  ]
}
```

#### `GET /api/v1/presets/:id`

Get preset details

**Response 200**: Preset object

#### `POST /api/v1/presets`

Create custom preset (admin only)

**Request Body**:
```json
{
  "name": "custom-python",
  "display_name": "My Python Setup",
  "framework_type": "language",
  "language": "python",
  "test_command": "poetry run pytest",
  "build_command": "poetry build"
}
```

**Response 201**: Created preset object

---

### Usage & Analytics

#### `GET /api/v1/usage/daily`

Get daily usage statistics

**Query Parameters**:
- `project_id` (string, optional filter)
- `start_date` (date, format YYYY-MM-DD)
- `end_date` (date, format YYYY-MM-DD)

**Response 200**:
```json
{
  "data": [
    {
      "date": "2025-12-30",
      "project_id": "proj_abc123",
      "tasks_queued": 8,
      "tasks_completed": 7,
      "tasks_failed": 1,
      "total_tokens_used": 35421,
      "total_cost_usd": 2.87,
      "total_duration_seconds": 892
    }
  ],
  "summary": {
    "total_tasks": 8,
    "total_cost_usd": 2.87,
    "avg_cost_per_task": 0.36,
    "success_rate": 0.875
  }
}
```

#### `GET /api/v1/usage/summary`

Get usage summary

**Query Parameters**:
- `period` (string: today, week, month, year)

**Response 200**:
```json
{
  "period": "month",
  "start_date": "2025-12-01",
  "end_date": "2025-12-30",
  "tasks_completed": 142,
  "tasks_failed": 8,
  "success_rate": 0.947,
  "total_cost_usd": 58.32,
  "total_tokens_used": 720543,
  "avg_duration_seconds": 134,
  "by_project": [
    {
      "project_id": "proj_abc123",
      "project_name": "My Game Project",
      "tasks_completed": 95,
      "total_cost_usd": 38.50
    }
  ]
}
```

---

### API Keys

#### `GET /api/v1/api-keys`

List API keys for current user

**Response 200**:
```json
{
  "data": [
    {
      "id": "key_abc123",
      "key_prefix": "lb_live_a",
      "name": "Production Key",
      "scopes": ["read", "write"],
      "project_id": "proj_abc123",
      "is_active": true,
      "last_used_at": "2025-12-30T10:17:00Z",
      "created_at": "2025-12-01T00:00:00Z"
    }
  ]
}
```

#### `POST /api/v1/api-keys`

Create new API key

**Request Body**:
```json
{
  "name": "Development Key",
  "scopes": ["read"],
  "project_id": "proj_abc123",
  "expires_at": "2026-12-30T00:00:00Z"
}
```

**Response 201**:
```json
{
  "id": "key_new123",
  "api_key": "lb_live_abc123def456...",
  "name": "Development Key",
  "scopes": ["read"],
  "project_id": "proj_abc123",
  "created_at": "2025-12-30T10:30:00Z"
}
```

**Important**: The `api_key` field is only returned once during creation.

#### `DELETE /api/v1/api-keys/:id`

Revoke API key

**Response 204**: No content

---

## Error Handling

### Error Response Format

All errors follow RFC 7807 Problem Details:

```json
{
  "type": "https://lazy-bird.dev/errors/validation-failed",
  "title": "Validation Failed",
  "status": 422,
  "detail": "The request body contains invalid data",
  "instance": "/api/v1/projects",
  "errors": [
    {
      "field": "repo_url",
      "message": "Must be a valid URL"
    }
  ]
}
```

### HTTP Status Codes

- `200 OK` - Request succeeded
- `201 Created` - Resource created
- `204 No Content` - Success with no response body
- `400 Bad Request` - Invalid request format
- `401 Unauthorized` - Missing or invalid authentication
- `403 Forbidden` - Authenticated but not authorized
- `404 Not Found` - Resource not found
- `422 Unprocessable Entity` - Validation failed
- `429 Too Many Requests` - Rate limit exceeded
- `500 Internal Server Error` - Server error
- `503 Service Unavailable` - Service temporarily down

## Rate Limiting

**Limits**:
- 100 requests per minute per API key
- 1000 requests per hour per API key

**Response Headers**:
```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1704024000
```

**Error Response (429)**:
```json
{
  "type": "https://lazy-bird.dev/errors/rate-limit-exceeded",
  "title": "Rate Limit Exceeded",
  "status": 429,
  "detail": "You have exceeded the rate limit of 100 requests per minute",
  "retry_after": 42
}
```

## Pagination

All list endpoints use cursor-based pagination:

**Request**:
```
GET /api/v1/tasks?limit=20&cursor=crs_abc123
```

**Response**:
```json
{
  "data": [...],
  "pagination": {
    "next_cursor": "crs_xyz789",
    "has_more": true
  }
}
```

## Versioning

API versions are specified in the URL path:
- `/api/v1/...` - Version 1 (current)
- `/api/v2/...` - Version 2 (future)

Version 1 will be supported for minimum 12 months after v2 release.

---

**Next**: [Webhooks](04-webhooks.md)
