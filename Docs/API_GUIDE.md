# Lazy-Bird v2.0 API Guide

Complete guide to using the Lazy-Bird REST API for development automation.

## Table of Contents

- [Getting Started](#getting-started)
- [Authentication](#authentication)
- [API Endpoints](#api-endpoints)
- [Code Examples](#code-examples)
- [Error Handling](#error-handling)
- [Rate Limiting](#rate-limiting)
- [Webhooks](#webhooks)

---

## Getting Started

### Base URL

```
http://localhost:8000/api/v1
```

### Interactive Documentation

Lazy-Bird provides auto-generated interactive API documentation:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **OpenAPI JSON**: http://localhost:8000/api/v1/openapi.json

### Quick Example

```bash
# Check API health
curl http://localhost:8000/api/v1/health

# Expected response
{
  "status": "healthy",
  "database": "connected",
  "redis": "connected",
  "celery": "running",
  "version": "2.0.0"
}
```

---

## Authentication

Lazy-Bird supports two authentication methods:

### 1. API Key Authentication (Recommended)

#### Creating an API Key

```python
import requests

# Create an API key
response = requests.post(
    "http://localhost:8000/api/v1/api-keys",
    headers={"X-API-Key": "<admin-key>"},
    json={
        "name": "My Development Key",
        "scopes": ["read", "write"],
        "expires_in_days": 90
    }
)

api_key = response.json()["key"]
# Save this key securely! It's only shown once.
```

#### Using an API Key

```python
import requests

headers = {
    "X-API-Key": "lb_abc123..."
}

response = requests.get(
    "http://localhost:8000/api/v1/projects",
    headers=headers
)
```

### 2. JWT Token Authentication

#### Login to Get Token

```python
import requests

response = requests.post(
    "http://localhost:8000/api/v1/auth/login",
    json={
        "username": "admin",
        "password": "your-password"
    }
)

token = response.json()["access_token"]
```

#### Using JWT Token

```python
import requests

headers = {
    "Authorization": f"Bearer {token}"
}

response = requests.get(
    "http://localhost:8000/api/v1/projects",
    headers=headers
)
```

### Scopes and Permissions

| Scope | Access |
|-------|--------|
| `read` | View projects, task runs, and status |
| `write` | Create/update projects and task runs |
| `admin` | Full access including API key management |

---

## API Endpoints

### Health Endpoints

#### GET `/api/v1/health`

Check system health status.

**Response:**
```json
{
  "status": "healthy",
  "database": "connected",
  "redis": "connected",
  "celery": "running",
  "version": "2.0.0",
  "uptime_seconds": 3600
}
```

---

### Project Endpoints

#### GET `/api/v1/projects`

List all projects.

**Query Parameters:**
- `skip` (int): Number of records to skip (default: 0)
- `limit` (int): Maximum records to return (default: 100, max: 1000)
- `is_active` (bool): Filter by active status

**Example:**
```python
import requests

response = requests.get(
    "http://localhost:8000/api/v1/projects",
    params={"is_active": True, "limit": 10},
    headers={"X-API-Key": "lb_..."}
)

projects = response.json()
```

#### POST `/api/v1/projects`

Create a new project.

**Request Body:**
```json
{
  "name": "My Godot Game",
  "description": "RPG game development",
  "repository_url": "https://github.com/user/game",
  "local_path": "/path/to/project",
  "framework": "godot",
  "test_command": "godot --headless -s res://addons/gdUnit4/bin/GdUnitCmdTool.gd",
  "build_command": "godot --export-release Linux /tmp/build",
  "lint_command": "gdlint .",
  "claude_account_id": "uuid-of-claude-account"
}
```

#### GET `/api/v1/projects/{project_id}`

Get project details.

#### PATCH `/api/v1/projects/{project_id}`

Update project settings.

#### DELETE `/api/v1/projects/{project_id}`

Delete a project.

---

### Task Run Endpoints

#### POST `/api/v1/task-runs`

Create and execute a new task.

**Request Body:**
```json
{
  "project_id": "uuid",
  "work_item_id": "GH-42",
  "work_item_title": "Add player health system",
  "work_item_url": "https://github.com/user/repo/issues/42",
  "task_type": "feature",
  "complexity": "medium",
  "instructions": "Implement health system with max_health=100, take_damage(), and heal() methods"
}
```

**Response:**
```json
{
  "id": "uuid",
  "project_id": "uuid",
  "work_item_id": "GH-42",
  "status": "queued",
  "created_at": "2026-01-02T10:30:00Z",
  "stream_url": "/api/v1/task-runs/{id}/logs/stream"
}
```

#### GET `/api/v1/task-runs/{task_run_id}`

Get task run status and results.

#### GET `/api/v1/task-runs/{task_run_id}/logs/stream`

Stream real-time logs via Server-Sent Events (SSE).

**Query Parameters:**
- `level` (str): Filter by log level (DEBUG, INFO, WARNING, ERROR)
- `search` (str): Filter logs containing text
- `since` (datetime): Only show logs after timestamp

**Example (Python):**
```python
import requests
import json

url = f"http://localhost:8000/api/v1/task-runs/{task_id}/logs/stream"
headers = {"X-API-Key": "lb_..."}

response = requests.get(url, headers=headers, stream=True)

for line in response.iter_lines():
    if line:
        # Parse SSE format
        if line.startswith(b"data: "):
            data = json.loads(line[6:])
            print(f"[{data['level']}] {data['message']}")
```

**Example (JavaScript):**
```javascript
const eventSource = new EventSource(
    `http://localhost:8000/api/v1/task-runs/${taskId}/logs/stream`,
    {
        headers: {
            'X-API-Key': 'lb_...'
        }
    }
);

eventSource.onmessage = (event) => {
    const log = JSON.parse(event.data);
    console.log(`[${log.level}] ${log.message}`);
};

eventSource.onerror = (error) => {
    console.error('SSE error:', error);
    eventSource.close();
};
```

#### POST `/api/v1/task-runs/{task_run_id}/retry`

Retry a failed task run.

---

### Claude Account Endpoints

#### GET `/api/v1/claude-accounts`

List Claude API accounts.

#### POST `/api/v1/claude-accounts`

Add a Claude API account.

**Request Body:**
```json
{
  "name": "Primary Claude Account",
  "account_type": "api",
  "api_key": "sk-ant-api03-...",
  "cost_limit_monthly": 100.00
}
```

---

### Framework Preset Endpoints

#### GET `/api/v1/framework-presets`

List available framework presets.

**Response:**
```json
[
  {
    "id": "godot",
    "name": "Godot",
    "description": "Godot game engine with gdUnit4",
    "test_command": "godot --headless -s res://addons/gdUnit4/bin/GdUnitCmdTool.gd",
    "supported_languages": ["gdscript", "c#"]
  },
  {
    "id": "django",
    "name": "Django",
    "description": "Django web framework",
    "test_command": "python manage.py test",
    "supported_languages": ["python"]
  }
]
```

---

### Webhook Endpoints

#### POST `/api/v1/webhooks`

Create a webhook subscription.

**Request Body:**
```json
{
  "url": "https://your-server.com/webhooks/lazy-bird",
  "events": ["task.started", "task.completed", "task.failed"],
  "secret": "your-webhook-secret"
}
```

#### GET `/api/v1/webhooks/{webhook_id}`

Get webhook details.

#### DELETE `/api/v1/webhooks/{webhook_id}`

Delete a webhook subscription.

---

## Code Examples

### Complete Workflow Example

```python
import requests
import time

API_URL = "http://localhost:8000/api/v1"
API_KEY = "lb_your_api_key_here"

headers = {"X-API-Key": API_KEY}

# 1. Create a project
project = requests.post(
    f"{API_URL}/projects",
    headers=headers,
    json={
        "name": "My Game",
        "repository_url": "https://github.com/user/my-game",
        "local_path": "/home/user/projects/my-game",
        "framework": "godot",
        "test_command": "godot --headless -s res://addons/gdUnit4/bin/GdUnitCmdTool.gd"
    }
).json()

project_id = project["id"]
print(f"Created project: {project_id}")

# 2. Create a task run
task = requests.post(
    f"{API_URL}/task-runs",
    headers=headers,
    json={
        "project_id": project_id,
        "work_item_id": "GH-42",
        "work_item_title": "Add health system",
        "task_type": "feature",
        "complexity": "medium",
        "instructions": "Add health system with 100 max health"
    }
).json()

task_id = task["id"]
print(f"Created task: {task_id}")

# 3. Monitor task progress
while True:
    status = requests.get(
        f"{API_URL}/task-runs/{task_id}",
        headers=headers
    ).json()

    print(f"Status: {status['status']}")

    if status["status"] in ["completed", "failed", "cancelled"]:
        break

    time.sleep(5)

# 4. Get final results
if status["status"] == "completed":
    print(f"✓ Task completed successfully!")
    print(f"PR URL: {status.get('pull_request_url')}")
    print(f"Tests passed: {status.get('tests_passed')}")
else:
    print(f"✗ Task failed: {status.get('error_message')}")
```

### Streaming Logs in Real-Time

```python
import requests
import json

def stream_task_logs(task_id: str, api_key: str):
    """Stream task logs in real-time using SSE."""
    url = f"http://localhost:8000/api/v1/task-runs/{task_id}/logs/stream"
    headers = {"X-API-Key": api_key}

    response = requests.get(url, headers=headers, stream=True)

    for line in response.iter_lines():
        if line:
            # SSE format: "data: {json}"
            if line.startswith(b"data: "):
                log_data = json.loads(line[6:])

                timestamp = log_data.get("timestamp", "")
                level = log_data.get("level", "INFO")
                message = log_data.get("message", "")

                # Color-code log levels
                colors = {
                    "DEBUG": "\033[36m",  # Cyan
                    "INFO": "\033[32m",   # Green
                    "WARNING": "\033[33m",  # Yellow
                    "ERROR": "\033[31m",  # Red
                }
                color = colors.get(level, "")
                reset = "\033[0m"

                print(f"{color}[{level}]{reset} {timestamp} {message}")

# Usage
stream_task_logs("task-uuid", "lb_your_key")
```

### Webhook Handler Example

```python
from flask import Flask, request, jsonify
import hmac
import hashlib

app = Flask(__name__)

WEBHOOK_SECRET = "your-webhook-secret"

@app.route("/webhooks/lazy-bird", methods=["POST"])
def lazy_bird_webhook():
    # Verify signature
    signature = request.headers.get("X-Lazy-Bird-Signature")
    body = request.get_data()

    expected_signature = hmac.new(
        WEBHOOK_SECRET.encode(),
        body,
        hashlib.sha256
    ).hexdigest()

    if not hmac.compare_digest(signature, expected_signature):
        return jsonify({"error": "Invalid signature"}), 401

    # Process event
    event = request.json
    event_type = event["event"]
    data = event["data"]

    if event_type == "task.completed":
        print(f"Task {data['task_id']} completed!")
        print(f"PR URL: {data.get('pr_url')}")

    elif event_type == "task.failed":
        print(f"Task {data['task_id']} failed!")
        print(f"Error: {data.get('error')}")

    return jsonify({"status": "received"}), 200

if __name__ == "__main__":
    app.run(port=5000)
```

---

## Error Handling

### Error Response Format

All errors return a consistent JSON structure:

```json
{
  "error": "ValidationError",
  "message": "Invalid project ID",
  "details": {
    "field": "project_id",
    "value": "invalid-uuid"
  },
  "request_id": "uuid"
}
```

### HTTP Status Codes

| Code | Meaning |
|------|---------|
| 200 | Success |
| 201 | Created |
| 204 | No Content (successful deletion) |
| 400 | Bad Request (validation error) |
| 401 | Unauthorized (missing/invalid auth) |
| 403 | Forbidden (insufficient permissions) |
| 404 | Not Found |
| 409 | Conflict (duplicate resource) |
| 422 | Unprocessable Entity (semantic error) |
| 429 | Too Many Requests (rate limited) |
| 500 | Internal Server Error |

### Retry Logic

```python
import requests
import time

def api_call_with_retry(url, headers, max_retries=3, backoff=2):
    """Make API call with exponential backoff retry."""
    for attempt in range(max_retries):
        try:
            response = requests.get(url, headers=headers, timeout=10)

            # Success
            if response.status_code == 200:
                return response.json()

            # Rate limited - respect Retry-After header
            if response.status_code == 429:
                retry_after = int(response.headers.get("Retry-After", backoff))
                print(f"Rate limited. Waiting {retry_after}s...")
                time.sleep(retry_after)
                continue

            # Client error - don't retry
            if 400 <= response.status_code < 500:
                response.raise_for_status()

            # Server error - retry with backoff
            if response.status_code >= 500:
                wait_time = backoff ** attempt
                print(f"Server error. Retrying in {wait_time}s...")
                time.sleep(wait_time)
                continue

        except requests.exceptions.RequestException as e:
            if attempt == max_retries - 1:
                raise
            wait_time = backoff ** attempt
            print(f"Request failed: {e}. Retrying in {wait_time}s...")
            time.sleep(wait_time)

    raise Exception(f"Max retries ({max_retries}) exceeded")
```

---

## Rate Limiting

Default rate limits (configurable):
- **60 requests per minute** per API key
- **1000 requests per hour** per API key

### Rate Limit Headers

All responses include rate limit information:

```
X-RateLimit-Limit: 60
X-RateLimit-Remaining: 45
X-RateLimit-Reset: 30
```

### Handling Rate Limits

```python
import requests
import time

def check_rate_limit(response):
    """Check rate limit headers and wait if needed."""
    remaining = int(response.headers.get("X-RateLimit-Remaining", 60))

    if remaining < 5:
        reset = int(response.headers.get("X-RateLimit-Reset", 60))
        print(f"Low rate limit. Waiting {reset}s...")
        time.sleep(reset)

    return remaining

# Usage
response = requests.get(url, headers=headers)
check_rate_limit(response)
```

---

## Webhooks

### Webhook Events

| Event | Description |
|-------|-------------|
| `task.created` | New task created |
| `task.started` | Task execution started |
| `task.progress` | Task progress update (every 10%) |
| `task.completed` | Task completed successfully |
| `task.failed` | Task execution failed |
| `task.cancelled` | Task was cancelled |
| `pr.created` | Pull request created |
| `pr.merged` | Pull request merged |
| `project.created` | New project added |
| `project.updated` | Project settings changed |

### Webhook Payload Example

```json
{
  "event": "task.completed",
  "timestamp": "2026-01-02T10:30:00Z",
  "data": {
    "task_id": "uuid",
    "project_id": "uuid",
    "work_item_id": "GH-42",
    "status": "completed",
    "tests_passed": true,
    "pr_url": "https://github.com/user/repo/pull/123",
    "duration_seconds": 120
  },
  "metadata": {
    "complexity": "medium",
    "framework": "godot"
  }
}
```

### Webhook Security

Webhooks include an HMAC-SHA256 signature for verification:

```python
import hmac
import hashlib

def verify_webhook(request_body: bytes, signature: str, secret: str) -> bool:
    """Verify webhook signature."""
    expected_signature = hmac.new(
        secret.encode(),
        request_body,
        hashlib.sha256
    ).hexdigest()

    return hmac.compare_digest(signature, expected_signature)
```

---

## Additional Resources

- **Interactive API Docs**: http://localhost:8000/docs
- **OpenAPI Spec**: http://localhost:8000/api/v1/openapi.json
- **GitHub Repository**: https://github.com/yusyus/lazy-bird
- **Issue Tracker**: https://github.com/yusyus/lazy-bird/issues
- **Security Documentation**: [Docs/Design/security-baseline.md](Design/security-baseline.md)
- **Performance Targets**: [Docs/Design/performance-targets.md](Design/performance-targets.md)

---

**Last Updated:** 2026-01-03
**API Version:** 2.0.0
**Status:** Production Ready ✅
