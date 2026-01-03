# Testing Strategy - Lazy-Bird v2.0

**Status:** ✅ **IMPLEMENTED** (v2.0 Complete - 2026-01-03)

## Overview

Comprehensive testing strategy for Lazy-Bird v2.0 refactoring, covering unit tests, integration tests, end-to-end tests, and performance testing.

**Test Coverage Goal**: 80%+ for production code

**Test Framework**: pytest + pytest-asyncio + FastAPI TestClient

## Testing Pyramid

```
                    ┌─────────────┐
                    │  E2E Tests  │  ← 10% (Critical paths)
                    └─────────────┘
                  ┌───────────────────┐
                  │ Integration Tests │  ← 30% (API + Services)
                  └───────────────────┘
              ┌─────────────────────────────┐
              │       Unit Tests            │  ← 60% (Models + Utils)
              └─────────────────────────────┘
```

## Test Structure

```
lazy-bird/
└── tests/
    ├── conftest.py              # Shared fixtures
    ├── unit/                    # Unit tests
    │   ├── test_models.py
    │   ├── test_schemas.py
    │   ├── test_security.py
    │   └── test_services/
    │       ├── test_claude_service.py
    │       ├── test_git_service.py
    │       └── test_webhook_service.py
    ├── integration/             # Integration tests
    │   ├── test_api/
    │   │   ├── test_projects.py
    │   │   ├── test_tasks.py
    │   │   ├── test_accounts.py
    │   │   └── test_webhooks.py
    │   ├── test_celery_tasks.py
    │   └── test_database.py
    ├── e2e/                     # End-to-end tests
    │   ├── test_full_workflow.py
    │   ├── test_plane_integration.py
    │   └── test_web_ui.py
    └── performance/             # Performance tests
        ├── test_load.py
        └── test_concurrent_tasks.py
```

## Unit Tests

### Models

**File**: `tests/unit/test_models.py`

```python
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from lazy_bird.core.database import Base
from lazy_bird.models.project import Project
from lazy_bird.models.task_run import TaskRun

@pytest.fixture
def db_session():
    """Create in-memory SQLite database for testing"""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()

def test_project_creation(db_session):
    """Test creating a project"""
    project = Project(
        name="Test Project",
        slug="test-project",
        repo_url="https://github.com/user/repo",
        project_type="python"
    )
    db_session.add(project)
    db_session.commit()

    assert project.id is not None
    assert project.slug == "test-project"
    assert project.automation_enabled is False  # Default

def test_project_slug_uniqueness(db_session):
    """Test slug must be unique"""
    project1 = Project(
        name="Project 1",
        slug="test-project",
        repo_url="https://github.com/user/repo1",
        project_type="python"
    )
    db_session.add(project1)
    db_session.commit()

    project2 = Project(
        name="Project 2",
        slug="test-project",
        repo_url="https://github.com/user/repo2",
        project_type="python"
    )
    db_session.add(project2)

    with pytest.raises(Exception):  # IntegrityError
        db_session.commit()

def test_task_run_duration_calculation(db_session):
    """Test duration is calculated correctly"""
    from datetime import datetime, timedelta

    project = Project(name="Test", slug="test", repo_url="https://github.com/user/repo", project_type="python")
    db_session.add(project)
    db_session.commit()

    task_run = TaskRun(
        project_id=project.id,
        work_item_id="issue-1",
        prompt="Test task",
        status="running",
        started_at=datetime.utcnow()
    )
    db_session.add(task_run)
    db_session.commit()

    # Complete task
    task_run.status = "success"
    task_run.completed_at = task_run.started_at + timedelta(seconds=127)
    db_session.commit()

    # Duration should be calculated by trigger
    assert task_run.duration_seconds == 127
```

### Schemas (Pydantic Validation)

**File**: `tests/unit/test_schemas.py`

```python
import pytest
from pydantic import ValidationError
from lazy_bird.schemas.project import ProjectCreate, ProjectUpdate

def test_project_create_valid():
    """Test valid project creation schema"""
    data = {
        "name": "Test Project",
        "slug": "test-project",
        "repo_url": "https://github.com/user/repo",
        "project_type": "python"
    }
    project = ProjectCreate(**data)
    assert project.slug == "test-project"
    assert project.automation_enabled is False

def test_project_create_invalid_slug():
    """Test slug validation"""
    data = {
        "name": "Test Project",
        "slug": "Test Project!",  # Invalid: spaces and special chars
        "repo_url": "https://github.com/user/repo",
        "project_type": "python"
    }
    with pytest.raises(ValidationError) as exc_info:
        ProjectCreate(**data)

    assert "slug" in str(exc_info.value)

def test_project_create_invalid_url():
    """Test URL validation"""
    data = {
        "name": "Test Project",
        "slug": "test-project",
        "repo_url": "not-a-url",
        "project_type": "python"
    }
    with pytest.raises(ValidationError) as exc_info:
        ProjectCreate(**data)

    assert "repo_url" in str(exc_info.value)
```

### Security

**File**: `tests/unit/test_security.py`

```python
import pytest
from lazy_bird.core.security import generate_api_key, verify_api_key, create_access_token
from jose import jwt
from lazy_bird.core.config import settings

def test_generate_api_key():
    """Test API key generation"""
    key, key_hash = generate_api_key()

    assert key.startswith("lb_live_")
    assert len(key) > 20
    assert len(key_hash) == 64  # SHA-256 hash

def test_verify_api_key():
    """Test API key verification"""
    key, key_hash = generate_api_key()

    assert verify_api_key(key, key_hash) is True
    assert verify_api_key("wrong_key", key_hash) is False

def test_create_access_token():
    """Test JWT token creation"""
    data = {"user_id": "123", "scopes": ["read", "write"]}
    token = create_access_token(data)

    # Decode and verify
    decoded = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
    assert decoded["user_id"] == "123"
    assert "exp" in decoded  # Expiration time
```

### Services

**File**: `tests/unit/test_services/test_webhook_service.py`

```python
import pytest
from unittest.mock import Mock, AsyncMock, patch
from lazy_bird.services.webhook_service import WebhookService
from lazy_bird.models.webhook import WebhookSubscription

@pytest.fixture
def webhook_service():
    return WebhookService()

@pytest.fixture
def mock_webhook():
    webhook = Mock(spec=WebhookSubscription)
    webhook.id = "wh_123"
    webhook.url = "https://example.com/webhook"
    webhook.secret = "test_secret"
    webhook.events = ["task.completed", "task.failed"]
    webhook.is_active = True
    return webhook

@pytest.mark.asyncio
async def test_publish_event_matching_subscription(webhook_service, mock_webhook):
    """Test event is published to matching webhooks"""
    with patch.object(webhook_service, '_send_webhook', new=AsyncMock()) as mock_send:
        with patch('lazy_bird.services.webhook_service.db') as mock_db:
            mock_db.query.return_value.filter.return_value.all.return_value = [mock_webhook]

            await webhook_service.publish_event(
                db=mock_db,
                event_type="task.completed",
                data={"task_id": "run_123"}
            )

            mock_send.assert_called_once()

@pytest.mark.asyncio
async def test_webhook_signature_generation(webhook_service, mock_webhook):
    """Test webhook signature is correctly generated"""
    payload = '{"type": "task.completed"}'
    signature = webhook_service._generate_signature(payload, "test_secret")

    assert signature.startswith("sha256=")
    assert len(signature) > 10

@pytest.mark.asyncio
async def test_event_filtering(webhook_service, mock_webhook):
    """Test events are filtered correctly"""
    # Webhook subscribed to task.* events
    assert webhook_service._event_matches("task.completed", ["task.*"]) is True
    assert webhook_service._event_matches("task.failed", ["task.*"]) is True
    assert webhook_service._event_matches("pr.created", ["task.*"]) is False

    # Wildcard subscription
    assert webhook_service._event_matches("task.completed", ["*"]) is True
```

---

## Integration Tests

### API Endpoints

**File**: `tests/integration/test_api/test_projects.py`

```python
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from lazy_bird.api.main import app
from lazy_bird.core.database import Base, get_db
from lazy_bird.core.security import generate_api_key
from lazy_bird.models.api_key import ApiKey

# Test database
TEST_DATABASE_URL = "postgresql://test:test@localhost/lazy_bird_test"
engine = create_engine(TEST_DATABASE_URL)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(scope="function")
def db():
    """Create test database"""
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    yield db
    db.close()
    Base.metadata.drop_all(bind=engine)

@pytest.fixture(scope="function")
def client(db):
    """Create test client"""
    def override_get_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    return TestClient(app)

@pytest.fixture
def api_key(db):
    """Create test API key"""
    key, key_hash = generate_api_key()
    api_key = ApiKey(
        key_hash=key_hash,
        key_prefix=key[:10],
        name="Test Key",
        scopes=["read", "write"]
    )
    db.add(api_key)
    db.commit()
    return key

def test_create_project(client, api_key):
    """Test POST /api/v1/projects"""
    response = client.post(
        "/api/v1/projects",
        json={
            "name": "Test Project",
            "slug": "test-project",
            "repo_url": "https://github.com/user/repo",
            "project_type": "python",
            "automation_enabled": False
        },
        headers={"Authorization": f"Bearer {api_key}"}
    )

    assert response.status_code == 201
    data = response.json()
    assert data["slug"] == "test-project"
    assert data["id"] is not None

def test_list_projects(client, api_key, db):
    """Test GET /api/v1/projects"""
    # Create test projects
    from lazy_bird.models.project import Project
    for i in range(5):
        project = Project(
            name=f"Project {i}",
            slug=f"project-{i}",
            repo_url=f"https://github.com/user/repo{i}",
            project_type="python"
        )
        db.add(project)
    db.commit()

    response = client.get(
        "/api/v1/projects",
        headers={"Authorization": f"Bearer {api_key}"}
    )

    assert response.status_code == 200
    data = response.json()
    assert len(data["data"]) == 5
    assert "pagination" in data

def test_get_project(client, api_key, db):
    """Test GET /api/v1/projects/:id"""
    from lazy_bird.models.project import Project
    project = Project(
        name="Test Project",
        slug="test-project",
        repo_url="https://github.com/user/repo",
        project_type="python"
    )
    db.add(project)
    db.commit()

    response = client.get(
        f"/api/v1/projects/{project.id}",
        headers={"Authorization": f"Bearer {api_key}"}
    )

    assert response.status_code == 200
    data = response.json()
    assert data["slug"] == "test-project"

def test_update_project(client, api_key, db):
    """Test PATCH /api/v1/projects/:id"""
    from lazy_bird.models.project import Project
    project = Project(
        name="Test Project",
        slug="test-project",
        repo_url="https://github.com/user/repo",
        project_type="python",
        automation_enabled=False
    )
    db.add(project)
    db.commit()

    response = client.patch(
        f"/api/v1/projects/{project.id}",
        json={"automation_enabled": True},
        headers={"Authorization": f"Bearer {api_key}"}
    )

    assert response.status_code == 200
    data = response.json()
    assert data["automation_enabled"] is True
```

### Celery Tasks

**File**: `tests/integration/test_celery_tasks.py`

```python
import pytest
from lazy_bird.tasks.queue_processor import process_queue, execute_task
from lazy_bird.models.task_run import TaskRun
from lazy_bird.models.project import Project

@pytest.mark.celery
def test_process_queue(db, celery_worker):
    """Test queue processor task"""
    # Create project
    project = Project(
        name="Test Project",
        slug="test-project",
        repo_url="https://github.com/user/repo",
        project_type="python"
    )
    db.add(project)
    db.commit()

    # Create queued task
    task_run = TaskRun(
        project_id=project.id,
        work_item_id="issue-1",
        prompt="Test task",
        status="queued"
    )
    db.add(task_run)
    db.commit()

    # Process queue
    result = process_queue.delay()
    result.get(timeout=10)

    # Verify task was picked up
    db.refresh(task_run)
    assert task_run.status in ["running", "success", "failed"]

@pytest.mark.celery
@pytest.mark.slow
def test_execute_task_end_to_end(db, celery_worker, tmp_path):
    """Test full task execution"""
    # This test requires actual Claude CLI and git repo
    # Mark as slow/integration test

    project = Project(
        name="Test Project",
        slug="test-project",
        repo_url="https://github.com/user/test-repo",
        project_type="python",
        test_command="pytest"
    )
    db.add(project)
    db.commit()

    task_run = TaskRun(
        project_id=project.id,
        work_item_id="issue-1",
        prompt="Add a function that returns Hello World",
        status="queued"
    )
    db.add(task_run)
    db.commit()

    # Execute task
    result = execute_task.delay(str(task_run.id))
    result.get(timeout=600)  # 10 minutes

    # Verify results
    db.refresh(task_run)
    assert task_run.status in ["success", "failed"]
    assert task_run.duration_seconds is not None
```

---

## End-to-End Tests

### Full Workflow

**File**: `tests/e2e/test_full_workflow.py`

```python
import pytest
import asyncio
from fastapi.testclient import TestClient
from lazy_bird.api.main import app

@pytest.mark.e2e
@pytest.mark.asyncio
async def test_complete_task_workflow(client, api_key, db):
    """Test: Queue task → Execute → Create PR → Webhook"""

    # 1. Create project
    project_response = client.post(
        "/api/v1/projects",
        json={
            "name": "E2E Test Project",
            "slug": "e2e-test",
            "repo_url": "https://github.com/user/test-repo",
            "project_type": "python",
            "test_command": "pytest",
            "automation_enabled": True
        },
        headers={"Authorization": f"Bearer {api_key}"}
    )
    assert project_response.status_code == 201
    project_id = project_response.json()["id"]

    # 2. Queue task
    task_response = client.post(
        "/api/v1/tasks/queue",
        json={
            "project_id": project_id,
            "work_item_id": "issue-42",
            "work_item_title": "Add hello world function",
            "prompt": "Create a function hello_world() that returns 'Hello World'"
        },
        headers={"Authorization": f"Bearer {api_key}"}
    )
    assert task_response.status_code == 201
    task_run_id = task_response.json()["id"]

    # 3. Wait for task to start
    max_wait = 60  # seconds
    waited = 0
    while waited < max_wait:
        status_response = client.get(
            f"/api/v1/tasks/{task_run_id}",
            headers={"Authorization": f"Bearer {api_key}"}
        )
        status = status_response.json()["status"]

        if status == "running":
            break

        await asyncio.sleep(2)
        waited += 2

    assert status == "running", "Task should have started"

    # 4. Stream logs
    logs_response = client.get(
        f"/api/v1/tasks/{task_run_id}/logs",
        headers={"Authorization": f"Bearer {api_key}"}
    )
    assert logs_response.status_code == 200
    logs = logs_response.json()["data"]
    assert len(logs) > 0

    # 5. Wait for completion (or timeout)
    max_wait = 600  # 10 minutes
    waited = 0
    final_status = None

    while waited < max_wait:
        status_response = client.get(
            f"/api/v1/tasks/{task_run_id}",
            headers={"Authorization": f"Bearer {api_key}"}
        )
        final_status = status_response.json()["status"]

        if final_status in ["success", "failed", "timeout"]:
            break

        await asyncio.sleep(5)
        waited += 5

    # 6. Verify completion
    task_data = status_response.json()
    assert final_status == "success", f"Task should succeed, got {final_status}"
    assert task_data["pr_url"] is not None
    assert task_data["tests_passed"] is True
    assert task_data["duration_seconds"] > 0
```

### Plane Integration

**File**: `tests/e2e/test_plane_integration.py`

```python
import pytest
from unittest.mock import Mock, patch
import httpx

@pytest.mark.e2e
@pytest.mark.asyncio
async def test_plane_webhook_integration():
    """Test webhook delivery to Plane"""

    # Mock Plane webhook endpoint
    webhook_received = []

    async def mock_webhook_handler(request: httpx.Request):
        webhook_received.append({
            "headers": dict(request.headers),
            "body": request.content.decode()
        })
        return httpx.Response(200, json={"received": True})

    # Set up mock HTTP server for Plane
    with patch('httpx.AsyncClient.post', side_effect=mock_webhook_handler):
        # Trigger task completion
        # ... (queue and execute task)

        # Wait for webhook delivery
        await asyncio.sleep(2)

        # Verify webhook was sent
        assert len(webhook_received) == 1
        webhook = webhook_received[0]

        # Verify signature
        assert "X-Lazy-Bird-Signature" in webhook["headers"]
        assert "X-Lazy-Bird-Event" in webhook["headers"]

        # Verify payload
        import json
        payload = json.loads(webhook["body"])
        assert payload["type"] == "task.completed"
        assert "task_run_id" in payload["data"]
```

---

## Performance Tests

**File**: `tests/performance/test_load.py`

```python
import pytest
import asyncio
from concurrent.futures import ThreadPoolExecutor
from fastapi.testclient import TestClient

@pytest.mark.performance
def test_api_response_time(client, api_key):
    """Test API response time under load"""
    import time

    response_times = []

    def make_request():
        start = time.time()
        response = client.get(
            "/api/v1/projects",
            headers={"Authorization": f"Bearer {api_key}"}
        )
        duration = time.time() - start
        response_times.append(duration)
        return response.status_code

    # Make 100 concurrent requests
    with ThreadPoolExecutor(max_workers=10) as executor:
        results = list(executor.map(lambda _: make_request(), range(100)))

    # Calculate statistics
    avg_time = sum(response_times) / len(response_times)
    p95_time = sorted(response_times)[int(len(response_times) * 0.95)]
    p99_time = sorted(response_times)[int(len(response_times) * 0.99)]

    print(f"Average: {avg_time:.3f}s")
    print(f"P95: {p95_time:.3f}s")
    print(f"P99: {p99_time:.3f}s")

    # Assertions
    assert avg_time < 0.2, "Average response time should be < 200ms"
    assert p95_time < 0.5, "P95 response time should be < 500ms"
    assert all(r == 200 for r in results), "All requests should succeed"

@pytest.mark.performance
@pytest.mark.slow
def test_concurrent_task_execution(db):
    """Test multiple tasks executing concurrently"""
    # Queue 10 tasks simultaneously
    # Verify they all complete
    # Measure total time
    # Ensure resource limits are respected
    pass
```

---

## Test Configuration

**File**: `pytest.ini`

```ini
[pytest]
markers =
    unit: Unit tests
    integration: Integration tests
    e2e: End-to-end tests
    performance: Performance tests
    slow: Slow tests (> 30 seconds)
    celery: Tests requiring Celery worker

testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*

# Asyncio configuration
asyncio_mode = auto

# Coverage
addopts =
    --cov=lazy_bird
    --cov-report=html
    --cov-report=term-missing
    --cov-fail-under=80
```

**File**: `conftest.py`

```python
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from lazy_bird.core.database import Base

@pytest.fixture(scope="session")
def test_db_engine():
    """Create test database engine"""
    engine = create_engine("postgresql://test:test@localhost/lazy_bird_test")
    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)

@pytest.fixture(scope="function")
def db(test_db_engine):
    """Create database session for each test"""
    Session = sessionmaker(bind=test_db_engine)
    session = Session()
    yield session
    session.rollback()
    session.close()

@pytest.fixture(scope="session")
def celery_config():
    """Celery configuration for testing"""
    return {
        'broker_url': 'redis://localhost:6379/15',
        'result_backend': 'redis://localhost:6379/15',
        'task_always_eager': True  # Execute tasks synchronously in tests
    }
```

---

## Running Tests

```bash
# All tests
pytest

# Unit tests only
pytest -m unit

# Integration tests
pytest -m integration

# E2E tests
pytest -m e2e

# Exclude slow tests
pytest -m "not slow"

# With coverage
pytest --cov=lazy_bird --cov-report=html

# Verbose output
pytest -v

# Specific file
pytest tests/unit/test_models.py

# Specific test
pytest tests/unit/test_models.py::test_project_creation
```

## Continuous Integration

**File**: `.github/workflows/test.yml`

```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest

    services:
      postgres:
        image: postgres:14
        env:
          POSTGRES_DB: lazy_bird_test
          POSTGRES_USER: test
          POSTGRES_PASSWORD: test
        ports:
          - 5432:5432

      redis:
        image: redis:7
        ports:
          - 6379:6379

    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.10'

      - name: Install dependencies
        run: |
          pip install -e ".[dev]"

      - name: Run unit tests
        run: pytest -m unit --cov=lazy_bird

      - name: Run integration tests
        run: pytest -m integration --cov=lazy_bird --cov-append

      - name: Upload coverage
        uses: codecov/codecov-action@v3
```

---

## Success Criteria

- [ ] 80%+ code coverage
- [ ] All unit tests passing
- [ ] All integration tests passing
- [ ] E2E tests passing for critical workflows
- [ ] API response time < 200ms (p95)
- [ ] No memory leaks detected
- [ ] Performance metrics meet targets
- [ ] Security tests passing (no vulnerabilities)

---

**End of Refactoring Plan Documentation**
