# Webhooks - Lazy-Bird v2.0

**Status:** ✅ **IMPLEMENTED** (v2.0 Complete - 2026-01-03)

## Overview

Webhooks enable Lazy-Bird to send real-time event notifications to client applications. When specific events occur (task completion, PR creation, etc.), Lazy-Bird sends HTTP POST requests to registered webhook URLs.

This allows clients like Plane, Web UI, or custom integrations to react to events without polling the API.

## Architecture

```
┌─────────────────────────────────────────┐
│        Lazy-Bird Core Engine            │
│                                         │
│  ┌──────────────┐    ┌──────────────┐ │
│  │ Task Service │ ──▶│   Webhook    │ │
│  │  (Business)  │    │  Publisher   │ │
│  └──────────────┘    └──────────────┘ │
│                             │          │
└─────────────────────────────┼──────────┘
                              │
                              │ HTTP POST
                              │
         ┌────────────────────┼────────────────────┐
         │                    │                    │
         ▼                    ▼                    ▼
  ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
  │   Plane     │     │   Web UI    │     │   Custom    │
  │ Integration │     │  Backend    │     │   Client    │
  └─────────────┘     └─────────────┘     └─────────────┘
```

## Event Types

### Task Events

#### `task.queued`

Fired when a new task is added to the queue.

**Payload**:
```json
{
  "id": "evt_abc123",
  "type": "task.queued",
  "timestamp": "2025-12-30T10:14:30Z",
  "data": {
    "task_run_id": "run_xyz789",
    "project_id": "proj_abc123",
    "work_item_id": "issue-42",
    "work_item_title": "Add health system to player",
    "task_type": "feature",
    "complexity": "medium",
    "estimated_start_time": "2025-12-30T10:16:00Z"
  }
}
```

#### `task.started`

Fired when task execution begins.

**Payload**:
```json
{
  "id": "evt_abc124",
  "type": "task.started",
  "timestamp": "2025-12-30T10:15:00Z",
  "data": {
    "task_run_id": "run_xyz789",
    "project_id": "proj_abc123",
    "work_item_id": "issue-42",
    "branch_name": "feature-issue-42",
    "worktree_path": "/var/lib/lazy_bird/repos/proj_abc123/run_xyz789"
  }
}
```

#### `task.progress`

Fired periodically during task execution (every 30 seconds or on significant steps).

**Payload**:
```json
{
  "id": "evt_abc125",
  "type": "task.progress",
  "timestamp": "2025-12-30T10:16:00Z",
  "data": {
    "task_run_id": "run_xyz789",
    "project_id": "proj_abc123",
    "work_item_id": "issue-42",
    "step": "testing",
    "progress_percentage": 65,
    "message": "Running tests..."
  }
}
```

#### `task.completed`

Fired when task completes successfully.

**Payload**:
```json
{
  "id": "evt_abc126",
  "type": "task.completed",
  "timestamp": "2025-12-30T10:17:07Z",
  "data": {
    "task_run_id": "run_xyz789",
    "project_id": "proj_abc123",
    "work_item_id": "issue-42",
    "status": "success",
    "branch_name": "feature-issue-42",
    "commit_sha": "abc123def456...",
    "pr_url": "https://github.com/user/repo/pull/43",
    "pr_number": 43,
    "tests_passed": true,
    "duration_seconds": 127,
    "tokens_used": 5234,
    "cost_usd": 0.42,
    "summary": "Added health system with 100 max health, take_damage(amount) and heal(amount) methods. All tests passing."
  }
}
```

#### `task.failed`

Fired when task fails.

**Payload**:
```json
{
  "id": "evt_abc127",
  "type": "task.failed",
  "timestamp": "2025-12-30T10:20:00Z",
  "data": {
    "task_run_id": "run_xyz790",
    "project_id": "proj_abc123",
    "work_item_id": "issue-43",
    "status": "failed",
    "error_message": "Tests failed: 3 of 5 tests failing",
    "test_output": "FAILED test_player.gd::test_health_boundary - Expected 0, got -10",
    "duration_seconds": 95,
    "tokens_used": 3421,
    "cost_usd": 0.28,
    "retry_count": 3,
    "will_retry": false
  }
}
```

#### `task.timeout`

Fired when task exceeds time limit.

**Payload**:
```json
{
  "id": "evt_abc128",
  "type": "task.timeout",
  "timestamp": "2025-12-30T10:45:00Z",
  "data": {
    "task_run_id": "run_xyz791",
    "project_id": "proj_abc123",
    "work_item_id": "issue-44",
    "status": "timeout",
    "duration_seconds": 1800,
    "timeout_limit_seconds": 1800,
    "last_step": "testing",
    "tokens_used": 8943,
    "cost_usd": 0.73
  }
}
```

#### `task.cancelled`

Fired when task is manually cancelled.

**Payload**:
```json
{
  "id": "evt_abc129",
  "type": "task.cancelled",
  "timestamp": "2025-12-30T10:50:00Z",
  "data": {
    "task_run_id": "run_xyz792",
    "project_id": "proj_abc123",
    "work_item_id": "issue-45",
    "status": "cancelled",
    "cancelled_by": "user_123",
    "reason": "Duplicate task",
    "duration_seconds": 30
  }
}
```

### Pull Request Events

#### `pr.created`

Fired when a pull request is created.

**Payload**:
```json
{
  "id": "evt_abc130",
  "type": "pr.created",
  "timestamp": "2025-12-30T10:17:05Z",
  "data": {
    "task_run_id": "run_xyz789",
    "project_id": "proj_abc123",
    "work_item_id": "issue-42",
    "pr_url": "https://github.com/user/repo/pull/43",
    "pr_number": 43,
    "branch_name": "feature-issue-42",
    "title": "Add health system to player (#42)",
    "description": "Implements health tracking system...",
    "files_changed": 5,
    "additions": 127,
    "deletions": 3
  }
}
```

#### `pr.merged`

Fired when a pull request is merged.

**Payload**:
```json
{
  "id": "evt_abc131",
  "type": "pr.merged",
  "timestamp": "2025-12-30T11:00:00Z",
  "data": {
    "task_run_id": "run_xyz789",
    "project_id": "proj_abc123",
    "work_item_id": "issue-42",
    "pr_url": "https://github.com/user/repo/pull/43",
    "pr_number": 43,
    "merged_by": "user_456",
    "merged_at": "2025-12-30T11:00:00Z",
    "merge_commit_sha": "def456abc789..."
  }
}
```

### Usage Events

#### `usage.limit_warning`

Fired when approaching daily cost limit (80% threshold).

**Payload**:
```json
{
  "id": "evt_abc132",
  "type": "usage.limit_warning",
  "timestamp": "2025-12-30T14:30:00Z",
  "data": {
    "project_id": "proj_abc123",
    "date": "2025-12-30",
    "current_cost_usd": 40.00,
    "limit_usd": 50.00,
    "percentage_used": 0.80,
    "tasks_completed_today": 95
  }
}
```

#### `usage.limit_reached`

Fired when daily cost limit is reached.

**Payload**:
```json
{
  "id": "evt_abc133",
  "type": "usage.limit_reached",
  "timestamp": "2025-12-30T15:45:00Z",
  "data": {
    "project_id": "proj_abc123",
    "date": "2025-12-30",
    "current_cost_usd": 50.12,
    "limit_usd": 50.00,
    "tasks_completed_today": 119,
    "automation_paused": true
  }
}
```

## Webhook Subscription

### Creating a Subscription

**API Endpoint**: `POST /api/v1/webhooks`

```json
{
  "url": "https://plane.example.com/api/webhooks/lazy-bird",
  "secret": "whsec_abc123def456...",
  "project_id": "proj_abc123",
  "events": [
    "task.completed",
    "task.failed",
    "pr.created"
  ],
  "description": "Plane integration webhook"
}
```

### Event Filtering

Subscribe to specific events only:

```json
{
  "events": ["task.completed", "task.failed"]
}
```

Or subscribe to all events:

```json
{
  "events": ["*"]
}
```

Or event categories:

```json
{
  "events": ["task.*", "pr.*"]
}
```

## Webhook Delivery

### HTTP Request Format

**Method**: POST

**Headers**:
```http
POST /api/webhooks/lazy-bird HTTP/1.1
Host: plane.example.com
Content-Type: application/json
User-Agent: Lazy-Bird-Webhooks/2.0
X-Lazy-Bird-Event: task.completed
X-Lazy-Bird-Signature: sha256=abc123def456...
X-Lazy-Bird-Delivery: evt_abc126
X-Lazy-Bird-Timestamp: 1704024427
```

**Body**: Event payload (JSON)

### Signature Verification

Webhooks are signed using HMAC-SHA256. Verify the signature to ensure the request is from Lazy-Bird:

**Python Example**:
```python
import hmac
import hashlib

def verify_webhook_signature(payload: bytes, signature: str, secret: str) -> bool:
    """Verify webhook signature"""
    expected_signature = hmac.new(
        secret.encode(),
        payload,
        hashlib.sha256
    ).hexdigest()

    return hmac.compare_digest(
        signature,
        f"sha256={expected_signature}"
    )

# In your webhook endpoint
@app.post("/api/webhooks/lazy-bird")
async def lazy_bird_webhook(request: Request):
    payload = await request.body()
    signature = request.headers.get("X-Lazy-Bird-Signature")
    secret = "whsec_abc123..."  # From webhook subscription

    if not verify_webhook_signature(payload, signature, secret):
        raise HTTPException(status_code=401, detail="Invalid signature")

    event = await request.json()
    # Process event...
```

**JavaScript/TypeScript Example**:
```typescript
import crypto from 'crypto';

function verifyWebhookSignature(
  payload: string,
  signature: string,
  secret: string
): boolean {
  const expectedSignature = crypto
    .createHmac('sha256', secret)
    .update(payload)
    .digest('hex');

  return crypto.timingSafeEqual(
    Buffer.from(signature),
    Buffer.from(`sha256=${expectedSignature}`)
  );
}

// Express endpoint
app.post('/api/webhooks/lazy-bird', (req, res) => {
  const payload = JSON.stringify(req.body);
  const signature = req.headers['x-lazy-bird-signature'];
  const secret = 'whsec_abc123...';

  if (!verifyWebhookSignature(payload, signature, secret)) {
    return res.status(401).json({ error: 'Invalid signature' });
  }

  const event = req.body;
  // Process event...
  res.status(200).json({ received: true });
});
```

### Response Requirements

**Expected Response**:
- Status: `200 OK` or `204 No Content`
- Timeout: 10 seconds
- Body: Optional (not parsed)

**Example**:
```http
HTTP/1.1 200 OK
Content-Type: application/json

{"received": true}
```

### Retry Logic

If webhook delivery fails, Lazy-Bird will retry:

1. **Immediate retry** (after 5 seconds)
2. **Second retry** (after 30 seconds)
3. **Third retry** (after 5 minutes)
4. **Fourth retry** (after 30 minutes)
5. **Final retry** (after 2 hours)

**Failure conditions**:
- Non-2xx HTTP status code
- Network timeout (10 seconds)
- Connection error

**After 5 failed attempts**: Webhook is automatically disabled and admin is notified.

### Idempotency

Webhooks include `X-Lazy-Bird-Delivery` header with unique event ID. Clients should use this to prevent duplicate processing:

```python
# Track processed events
processed_events = set()

@app.post("/api/webhooks/lazy-bird")
async def lazy_bird_webhook(request: Request):
    event_id = request.headers.get("X-Lazy-Bird-Delivery")

    if event_id in processed_events:
        # Already processed, return success
        return {"received": true}

    # Process event...
    handle_event(await request.json())

    # Mark as processed
    processed_events.add(event_id)

    return {"received": true}
```

## Client Implementation Examples

### Plane Integration

```python
# plane_lazy_bird_integration/views.py
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
import hmac
import hashlib
import json

from plane.db.models import Issue, State
from .models import TaskRunMapping

@csrf_exempt
@require_POST
def lazy_bird_webhook(request):
    """Receive webhook events from Lazy-Bird"""

    # Verify signature
    payload = request.body
    signature = request.headers.get('X-Lazy-Bird-Signature')
    secret = settings.LAZY_BIRD_WEBHOOK_SECRET

    expected_sig = f"sha256={hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()}"
    if not hmac.compare_digest(signature, expected_sig):
        return JsonResponse({'error': 'Invalid signature'}, status=401)

    # Parse event
    event = json.loads(payload)
    event_type = event['type']
    data = event['data']

    # Handle different event types
    if event_type == 'task.completed':
        handle_task_completed(data)
    elif event_type == 'task.failed':
        handle_task_failed(data)
    elif event_type == 'pr.created':
        handle_pr_created(data)

    return JsonResponse({'received': True})


def handle_task_completed(data):
    """Handle task completion event"""
    # Find the Plane issue
    mapping = TaskRunMapping.objects.get(task_run_id=data['task_run_id'])
    issue = Issue.objects.get(id=mapping.issue_id)

    # Add comment with PR link
    issue.comments.create(
        comment_html=f'<p>✅ Task completed! PR: <a href="{data["pr_url"]}">#{data["pr_number"]}</a></p>',
        comment_json={
            'type': 'doc',
            'content': [{
                'type': 'paragraph',
                'content': [{'type': 'text', 'text': f'✅ Task completed! PR: {data["pr_url"]}'}]
            }]
        },
        actor_id=None  # System user
    )

    # Move to "In Review" state
    review_state = State.objects.get(
        project=issue.project,
        name='In Review'
    )
    issue.state = review_state
    issue.save()


def handle_task_failed(data):
    """Handle task failure event"""
    mapping = TaskRunMapping.objects.get(task_run_id=data['task_run_id'])
    issue = Issue.objects.get(id=mapping.issue_id)

    # Add comment with error details
    issue.comments.create(
        comment_html=f'<p>❌ Task failed: {data["error_message"]}</p>',
        actor_id=None
    )

    # Move back to "Ready" state for retry
    ready_state = State.objects.get(project=issue.project, name='Ready')
    issue.state = ready_state
    issue.save()


def handle_pr_created(data):
    """Handle PR creation event"""
    mapping = TaskRunMapping.objects.get(task_run_id=data['task_run_id'])
    issue = Issue.objects.get(id=mapping.issue_id)

    # Link PR to issue
    issue.issue_link.create(
        url=data['pr_url'],
        title=data['title'],
        metadata={
            'pr_number': data['pr_number'],
            'files_changed': data['files_changed']
        }
    )
```

### Web UI Backend (Node.js/Express)

```typescript
// server/webhooks/lazy-bird.ts
import express from 'express';
import crypto from 'crypto';
import { db } from '../db';

const router = express.Router();

router.post('/lazy-bird', async (req, res) => {
  // Verify signature
  const payload = JSON.stringify(req.body);
  const signature = req.headers['x-lazy-bird-signature'] as string;
  const secret = process.env.LAZY_BIRD_WEBHOOK_SECRET!;

  const expectedSignature = crypto
    .createHmac('sha256', secret)
    .update(payload)
    .digest('hex');

  if (!crypto.timingSafeEqual(
    Buffer.from(signature),
    Buffer.from(`sha256=${expectedSignature}`)
  )) {
    return res.status(401).json({ error: 'Invalid signature' });
  }

  const event = req.body;

  // Broadcast to connected WebSocket clients
  broadcastToWebSocketClients({
    type: 'lazy-bird-event',
    event: event
  });

  // Store event in database for history
  await db.webhookEvents.create({
    eventId: event.id,
    eventType: event.type,
    payload: event,
    receivedAt: new Date()
  });

  // Handle specific events
  switch (event.type) {
    case 'task.completed':
      await handleTaskCompleted(event.data);
      break;
    case 'task.progress':
      await handleTaskProgress(event.data);
      break;
  }

  res.status(200).json({ received: true });
});

async function handleTaskCompleted(data: any) {
  // Update task status in database
  await db.tasks.update({
    where: { taskRunId: data.task_run_id },
    data: {
      status: 'completed',
      prUrl: data.pr_url,
      completedAt: new Date(data.timestamp)
    }
  });

  // Send notification to user
  await sendNotification({
    userId: data.user_id,
    title: 'Task Completed',
    message: `Task "${data.work_item_title}" completed successfully!`,
    link: data.pr_url
  });
}

export default router;
```

## Monitoring and Debugging

### Webhook Dashboard

View webhook delivery status in Web UI:
- Recent deliveries
- Success/failure rates
- Response times
- Failed delivery details

### Webhook Logs

Each webhook delivery is logged:

```json
{
  "delivery_id": "del_abc123",
  "webhook_id": "wh_xyz789",
  "event_id": "evt_abc126",
  "event_type": "task.completed",
  "url": "https://plane.example.com/api/webhooks/lazy-bird",
  "attempt": 1,
  "status_code": 200,
  "response_time_ms": 125,
  "delivered_at": "2025-12-30T10:17:08Z"
}
```

### Testing Webhooks

Test webhook delivery without waiting for real events:

```bash
# Via API
curl -X POST https://api.lazy-bird.example.com/api/v1/webhooks/wh_xyz789/test \
  -H "Authorization: Bearer lb_live_abc123..."

# Via CLI
lazy-bird webhooks test wh_xyz789
```

### Debugging Failed Deliveries

```bash
# View failed deliveries
GET /api/v1/webhooks/wh_xyz789/deliveries?status=failed

# Retry specific delivery
POST /api/v1/webhooks/deliveries/del_abc123/retry
```

---

**Next**: [Client Separation](05-client-separation.md)
