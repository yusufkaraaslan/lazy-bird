# plane-lazy-bird-integration - Implementation Plan

## Repository: yusufkaraaslan/plane-lazy-bird-integration

Django package for integrating Lazy-Bird with Plane project management.

## Timeline: Week 4 (3 working days)

**Prerequisites**:
- lazy-bird core API functional (Week 3 complete)
- Plane instance available for testing
- Understanding of Plane's data model

---

## Day 1: Package Setup & API Client

### Morning: Django Package Setup

**Tasks**:
- [ ] Initialize Python package with Poetry
- [ ] Create Django app structure
- [ ] Set up package metadata (setup.py, pyproject.toml)
- [ ] Create README with installation instructions
- [ ] Add LICENSE file
- [ ] Configure development environment
- [ ] Create .env.example for settings

**Issues**: #1, #2, #3

**Deliverable**: Installable Django package

---

### Afternoon: Lazy-Bird API Client

**Tasks**:
- [ ] Create `LazyBirdClient` class
- [ ] Implement async HTTP client (httpx)
- [ ] Add authentication (Bearer token)
- [ ] Implement `queue_task()` method
- [ ] Implement `get_task_status()` method
- [ ] Implement `cancel_task()` method
- [ ] Implement `get_task_logs()` method
- [ ] Add error handling and retries
- [ ] Write client tests

**Issues**: #4, #5, #6, #7, #8

**Deliverable**: Complete API client library

---

## Day 2: Django Integration

### Morning: Models & Configuration

**Tasks**:
- [ ] Create `AutomationConfig` model
- [ ] Create `TaskRunMapping` model
- [ ] Create database migrations
- [ ] Implement model managers
- [ ] Add model methods
- [ ] Create admin interface
- [ ] Add model tests

**Issues**: #9, #10, #11, #12

**Deliverable**: Database models ready

---

### Afternoon: Django Signals

**Tasks**:
- [ ] Implement `pre_save` signal to capture state changes
- [ ] Implement `post_save` signal for issue state changes
- [ ] Add logic to detect "Ready" state transitions
- [ ] Implement task queuing when issue moves to Ready
- [ ] Add duplicate detection (prevent double-queuing)
- [ ] Handle signal errors gracefully
- [ ] Write signal tests

**Issues**: #13, #14, #15, #16

**Deliverable**: Automatic task queuing working

---

## Day 3: Webhooks & Final Integration

### Morning: Webhook Receiver

**Tasks**:
- [ ] Create webhook endpoint view
- [ ] Implement HMAC signature verification
- [ ] Add event routing (task.completed, task.failed, etc.)
- [ ] Implement `handle_task_started()` handler
- [ ] Implement `handle_task_completed()` handler
- [ ] Implement `handle_task_failed()` handler
- [ ] Implement `handle_pr_created()` handler
- [ ] Add idempotency handling
- [ ] Write webhook tests

**Issues**: #17, #18, #19, #20, #21, #22

**Deliverable**: Webhook receiver working

---

### Afternoon: Plane Updates & Polish

**Tasks**:
- [ ] Implement issue state updates
- [ ] Add comments to Plane issues
- [ ] Link PRs to issues
- [ ] Add error logging
- [ ] Create management command for setup
- [ ] Write integration tests
- [ ] Update documentation
- [ ] Package for PyPI

**Issues**: #23, #24, #25, #26, #27

**Deliverable**: Complete Plane integration package

---

## Additional Features (If Time Permits)

### React Components for Plane UI

**Tasks**:
- [ ] Create LazyBirdPanel component
- [ ] Show task status in Plane issue view
- [ ] Add manual task trigger button
- [ ] Display task logs in modal
- [ ] Show PR links

**Issues**: #28, #29, #30

---

### Advanced Features

**Tasks**:
- [ ] Multiple project support
- [ ] Custom state mapping per project
- [ ] Task priority handling
- [ ] Retry failed tasks from Plane UI
- [ ] Cost tracking in Plane

**Issues**: #31, #32, #33

---

## Technology Stack

### Core
- **Django 4.2+** - Web framework
- **httpx** - Async HTTP client
- **python-dotenv** - Environment configuration

### Testing
- **pytest** - Test framework
- **pytest-django** - Django testing
- **pytest-asyncio** - Async testing
- **factory_boy** - Test fixtures

### Development
- **Poetry** - Dependency management
- **black** - Code formatting
- **flake8** - Linting
- **mypy** - Type checking

---

## Package Structure

```
plane-lazy-bird-integration/
├── plane_lazy_bird/
│   ├── __init__.py
│   ├── apps.py                    # Django app config
│   ├── client.py                  # Lazy-Bird API client
│   ├── models.py                  # Django models
│   ├── signals.py                 # Signal handlers
│   ├── webhooks.py                # Webhook receiver
│   ├── admin.py                   # Admin interface
│   ├── urls.py                    # URL routing
│   ├── management/
│   │   └── commands/
│   │       └── lazy_bird_setup_webhook.py
│   ├── migrations/
│   │   └── 0001_initial.py
│   └── tests/
│       ├── test_client.py
│       ├── test_signals.py
│       └── test_webhooks.py
├── docs/
│   ├── installation.md
│   ├── configuration.md
│   └── usage.md
├── .env.example
├── setup.py
├── pyproject.toml
├── README.md
├── LICENSE
└── CHANGELOG.md
```

---

## Installation & Configuration

### Installation

```bash
# In Plane project
pip install plane-lazy-bird-integration

# Add to INSTALLED_APPS
INSTALLED_APPS = [
    ...
    'plane_lazy_bird',
]

# Run migrations
python manage.py migrate plane_lazy_bird
```

### Configuration

```python
# settings.py
LAZY_BIRD_API_URL = env('LAZY_BIRD_API_URL', 'http://localhost:8000')
LAZY_BIRD_API_KEY = env('LAZY_BIRD_API_KEY')
LAZY_BIRD_WEBHOOK_SECRET = env('LAZY_BIRD_WEBHOOK_SECRET')
```

### Setup Webhook

```bash
python manage.py lazy_bird_setup_webhook
```

---

## Code Examples

### API Client Usage

```python
from plane_lazy_bird.client import lazy_bird_client

# Queue a task
task_run = await lazy_bird_client.queue_task(
    project_id='proj_123',
    work_item_id='issue-42',
    title='Add health system',
    description='Player needs health tracking...'
)

# Get task status
status = await lazy_bird_client.get_task_status(task_run['id'])
```

### Signal Handler

```python
from django.db.models.signals import post_save
from django.dispatch import receiver
from plane.db.models import Issue

@receiver(post_save, sender=Issue)
def on_issue_state_change(sender, instance, **kwargs):
    if instance.state.name == 'Ready':
        # Queue task in Lazy-Bird
        task_run_id = await lazy_bird_client.queue_task(...)
        # Save mapping
        TaskRunMapping.objects.create(
            issue_id=instance.id,
            task_run_id=task_run_id
        )
```

### Webhook Handler

```python
@csrf_exempt
@require_POST
def lazy_bird_webhook(request):
    # Verify signature
    if not verify_signature(request):
        return JsonResponse({'error': 'Invalid signature'}, status=401)

    event = json.loads(request.body)

    if event['type'] == 'task.completed':
        # Update Plane issue
        issue.state = State.objects.get(name='In Review')
        issue.save()

        # Add comment with PR link
        issue.comments.create(
            comment=f"PR created: {event['data']['pr_url']}"
        )

    return JsonResponse({'received': True})
```

---

## Success Criteria

- [ ] Package installs in Plane without errors
- [ ] Signals detect issue state changes
- [ ] Tasks queue automatically in Lazy-Bird
- [ ] Webhooks receive and process events
- [ ] Plane issues update correctly
- [ ] PR links added to issues
- [ ] No database errors
- [ ] 80%+ test coverage
- [ ] Documentation complete
- [ ] Published to PyPI

---

## GitHub Project Board

### Columns

1. **📋 Backlog** - Future features
2. **🎯 Ready** - Ready to implement
3. **🚧 In Progress** - Currently working on
4. **👀 In Review** - PR created
5. **✅ Done** - Merged and published

### Labels

- `day-1` - Day 1 tasks
- `day-2` - Day 2 tasks
- `day-3` - Day 3 tasks
- `priority:critical` - Must have for v1.0
- `priority:high` - Important
- `priority:low` - Nice to have
- `type:setup` - Package setup
- `type:api-client` - API client
- `type:models` - Django models
- `type:signals` - Signal handlers
- `type:webhooks` - Webhook integration
- `type:testing` - Tests
- `blocked` - Blocked by core API

---

## Dependencies

**Blocks**: Nothing (this is a client)

**Blocked by**:
- yusufkaraaslan/lazy-bird#120 (Core API must be ready)

---

## Publishing to PyPI

```bash
# Build package
poetry build

# Publish to PyPI
poetry publish

# Install from PyPI
pip install plane-lazy-bird-integration
```

---

## Testing Strategy

### Unit Tests

```bash
pytest plane_lazy_bird/tests/
```

### Integration Tests (with Plane)

```bash
pytest plane_lazy_bird/tests/integration/
```

### Coverage

```bash
pytest --cov=plane_lazy_bird --cov-report=html
```

---

## Next Steps

1. Wait for lazy-bird core API (Week 3 end)
2. Create GitHub repository: `yusufkaraaslan/plane-lazy-bird-integration`
3. Initialize Python package
4. Create GitHub issues from this plan
5. Set up project board
6. Start Day 1 development
7. Test with Plane instance
8. Publish to PyPI
