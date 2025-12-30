# Plane Lazy-Bird Integration

Django package to integrate Lazy-Bird automation with Plane project management.

## Features

- 🎯 **Automatic Task Queuing** - When issues move to "Ready" state
- 🔔 **Webhook Integration** - Receive task completion events
- 💬 **Issue Updates** - Automatically update Plane issues with task status
- 🔗 **PR Linking** - Link created PRs to Plane issues
- 📊 **Admin Interface** - Manage automation via Django admin

## Installation

```bash
pip install plane-lazy-bird-integration
```

## Quick Setup

### 1. Add to INSTALLED_APPS

```python
# plane/settings/common.py
INSTALLED_APPS = [
    ...
    'plane_lazy_bird',
]
```

### 2. Configure Settings

```python
# plane/settings/common.py
LAZY_BIRD_API_URL = env('LAZY_BIRD_API_URL', 'http://localhost:8000')
LAZY_BIRD_API_KEY = env('LAZY_BIRD_API_KEY')
LAZY_BIRD_WEBHOOK_SECRET = env('LAZY_BIRD_WEBHOOK_SECRET')
```

### 3. Run Migrations

```bash
python manage.py migrate plane_lazy_bird
```

### 4. Register Webhook

```bash
python manage.py lazy_bird_setup_webhook
```

### 5. Add URL Routes

```python
# plane/urls.py
from django.urls import path, include

urlpatterns = [
    ...
    path('api/webhooks/', include('plane_lazy_bird.urls')),
]
```

## Usage

### Enable Automation for a Project

```python
from plane_lazy_bird.models import AutomationConfig
from plane.db.models import Project

project = Project.objects.get(slug='my-project')

AutomationConfig.objects.create(
    project=project,
    lazy_bird_project_id='proj_abc123',  # From Lazy-Bird
    enabled=True,
    ready_state_name='Ready'
)
```

### Automatic Task Queuing

When an issue moves to the "Ready" state, a task is automatically queued in Lazy-Bird:

```python
# User moves issue to "Ready" state in Plane UI
# → Signal fires
# → Task queued in Lazy-Bird
# → TaskRunMapping created
# → Issue state changed to "In Progress"
```

### Webhook Events

When Lazy-Bird completes a task, it sends a webhook to Plane:

```python
# Task completes in Lazy-Bird
# → Webhook sent to Plane
# → Issue updated with PR link
# → Issue state changed to "In Review"
# → Comment added to issue
```

## Configuration

### Environment Variables

```bash
# Lazy-Bird API configuration
LAZY_BIRD_API_URL=http://localhost:8000
LAZY_BIRD_API_KEY=lb_live_your_api_key_here
LAZY_BIRD_WEBHOOK_SECRET=whsec_your_webhook_secret
```

### Django Settings

```python
# plane/settings/common.py

# Lazy-Bird API URL
LAZY_BIRD_API_URL = env('LAZY_BIRD_API_URL')

# API key for authentication
LAZY_BIRD_API_KEY = env('LAZY_BIRD_API_KEY')

# Webhook secret for signature verification
LAZY_BIRD_WEBHOOK_SECRET = env('LAZY_BIRD_WEBHOOK_SECRET')

# Custom state names (optional)
LAZY_BIRD_READY_STATE = env('LAZY_BIRD_READY_STATE', 'Ready')
LAZY_BIRD_IN_PROGRESS_STATE = env('LAZY_BIRD_IN_PROGRESS_STATE', 'In Progress')
LAZY_BIRD_REVIEW_STATE = env('LAZY_BIRD_REVIEW_STATE', 'In Review')
```

## API Client Usage

```python
from plane_lazy_bird.client import lazy_bird_client

# Queue a task
task_run = await lazy_bird_client.queue_task(
    project_id='proj_123',
    work_item_id='issue-42',
    title='Add health system',
    description='Player needs health tracking with 100 max health...'
)

# Get task status
status = await lazy_bird_client.get_task_status(task_run['id'])
print(status['status'])  # 'queued', 'running', 'success', 'failed'

# Cancel a task
await lazy_bird_client.cancel_task(task_run['id'])
```

## Models

### AutomationConfig

Maps Plane projects to Lazy-Bird projects and configuration.

```python
class AutomationConfig(models.Model):
    project = models.OneToOneField('db.Project', on_delete=models.CASCADE)
    lazy_bird_project_id = models.UUIDField()
    enabled = models.BooleanField(default=False)
    ready_state_name = models.CharField(max_length=100, default='Ready')
```

### TaskRunMapping

Maps Plane issues to Lazy-Bird task runs.

```python
class TaskRunMapping(models.Model):
    issue = models.ForeignKey('db.Issue', on_delete=models.CASCADE)
    task_run_id = models.UUIDField()
    status = models.CharField(max_length=50)
    pr_url = models.URLField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
```

## Signals

### Issue State Change

Automatically queues tasks when issues move to Ready state:

```python
@receiver(post_save, sender=Issue)
def on_issue_state_change(sender, instance, **kwargs):
    # Check if automation enabled
    config = AutomationConfig.objects.filter(
        project=instance.project,
        enabled=True
    ).first()

    if config and instance.state.name == config.ready_state_name:
        # Queue task in Lazy-Bird
        task_run = await lazy_bird_client.queue_task(...)

        # Save mapping
        TaskRunMapping.objects.create(
            issue=instance,
            task_run_id=task_run['id']
        )
```

## Webhooks

### Events Handled

- `task.started` - Task execution began
- `task.completed` - Task completed successfully
- `task.failed` - Task failed
- `pr.created` - Pull request created

### Event Handlers

```python
def handle_task_completed(data):
    """Update Plane issue when task completes"""
    mapping = TaskRunMapping.objects.get(task_run_id=data['task_run_id'])
    issue = mapping.issue

    # Add comment with PR link
    issue.comments.create(
        comment_html=f'<p>✅ Task completed! PR: <a href="{data["pr_url"]}">#{data["pr_number"]}</a></p>',
        actor_id=None  # System user
    )

    # Move to review state
    review_state = State.objects.get(project=issue.project, name='In Review')
    issue.state = review_state
    issue.save()
```

## Admin Interface

Manage automation configuration via Django admin:

- View all project automations
- Enable/disable automation per project
- View task run mappings
- Monitor task statuses

## Development

```bash
# Install development dependencies
poetry install

# Run tests
pytest

# Run tests with coverage
pytest --cov=plane_lazy_bird

# Type checking
mypy plane_lazy_bird

# Code formatting
black plane_lazy_bird

# Linting
flake8 plane_lazy_bird
```

## Troubleshooting

### Tasks Not Queuing

1. Check automation is enabled:
   ```python
   AutomationConfig.objects.filter(project=project, enabled=True)
   ```

2. Verify state name matches:
   ```python
   config.ready_state_name == issue.state.name
   ```

3. Check API key is valid:
   ```bash
   curl -H "Authorization: Bearer $LAZY_BIRD_API_KEY" \
     http://localhost:8000/api/v1/status
   ```

### Webhooks Not Received

1. Verify webhook is registered:
   ```bash
   python manage.py lazy_bird_setup_webhook
   ```

2. Check webhook secret matches:
   ```python
   # In webhook handler
   logger.debug(f"Signature: {request.headers.get('X-Lazy-Bird-Signature')}")
   ```

3. Test webhook manually:
   ```bash
   curl -X POST http://localhost:8000/api/v1/webhooks/wh_xxx/test
   ```

## Contributing

See [IMPLEMENTATION.md](IMPLEMENTATION.md) for development roadmap.

## License

MIT

## Links

- [Lazy-Bird Core](https://github.com/yusufkaraaslan/lazy-bird)
- [Lazy-Bird Web UI](https://github.com/yusufkaraaslan/lazy-bird-ui)
- [Documentation](https://lazy-bird.dev/docs)
