# Implementation Timeline - Lazy-Bird v2.0

## Overview

This document provides a detailed week-by-week implementation plan for refactoring Lazy-Bird from v1.1 (Django-integrated) to v2.0 (microservice architecture).

**Timeline**: 4 weeks (1 developer, full-time)

**Approach**: Incremental refactoring with parallel v1.1 operation

## Week 1: Foundation and Core Models

### Day 1: Repository Setup

**Tasks**:
- [ ] Create `refactor/v2.0` branch in lazy-bird repository
- [ ] Set up new directory structure
- [ ] Initialize Python package (`pyproject.toml`, `setup.py`)
- [ ] Configure development environment
- [ ] Set up PostgreSQL database for v2.0
- [ ] Initialize Alembic for migrations

**Deliverables**:
```
lazy-bird/
├── lazy_bird/
│   ├── __init__.py
│   ├── api/
│   ├── models/
│   ├── schemas/
│   ├── services/
│   ├── tasks/
│   ├── core/
│   └── tests/
├── alembic/
├── docker-compose.yml
├── pyproject.toml
└── README.md
```

**Commands**:
```bash
# Create branch
git checkout -b refactor/v2.0

# Initialize package
poetry init
poetry add fastapi uvicorn sqlalchemy alembic psycopg2-binary pydantic celery redis

# Initialize Alembic
alembic init alembic

# Create database
docker-compose up -d postgres redis
```

---

### Day 2: Database Schema and Models

**Tasks**:
- [ ] Design PostgreSQL schema (see database-schema.md)
- [ ] Create SQLAlchemy Base class
- [ ] Implement Project model
- [ ] Implement ClaudeAccount model
- [ ] Implement FrameworkPreset model
- [ ] Implement TaskRun model
- [ ] Implement TaskRunLog model
- [ ] Create Alembic migration scripts

**Deliverables**:

**File**: `lazy_bird/core/database.py`
```python
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from lazy_bird.core.config import settings

engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    pool_size=20,
    max_overflow=10
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

**File**: `lazy_bird/models/project.py`
```python
from sqlalchemy import Column, String, Boolean, Integer, DECIMAL, TIMESTAMP, Text
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from sqlalchemy.sql import func, text
from lazy_bird.core.database import Base

class Project(Base):
    __tablename__ = "projects"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    name = Column(String(255), nullable=False)
    slug = Column(String(100), unique=True, nullable=False)
    repo_url = Column(String(500), nullable=False)
    # ... (see database schema doc for complete definition)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())
```

**Commands**:
```bash
# Create migration
alembic revision --autogenerate -m "Initial schema"

# Apply migration
alembic upgrade head

# Verify
psql lazy_bird -c "\dt"
```

---

### Day 3: Pydantic Schemas and Validation

**Tasks**:
- [ ] Create Pydantic schemas for all models
- [ ] Implement input validation
- [ ] Create response models
- [ ] Add API documentation strings

**Deliverables**:

**File**: `lazy_bird/schemas/project.py`
```python
from pydantic import BaseModel, HttpUrl, validator
from typing import Optional, Literal
from datetime import datetime
from uuid import UUID

class ProjectBase(BaseModel):
    name: str
    slug: str
    repo_url: HttpUrl
    project_type: str
    automation_enabled: bool = False

class ProjectCreate(ProjectBase):
    framework_preset_id: Optional[UUID] = None
    claude_account_id: Optional[UUID] = None
    ready_state_name: str = "Ready"
    max_concurrent_tasks: int = 3
    daily_cost_limit_usd: float = 50.00

    @validator('slug')
    def validate_slug(cls, v):
        if not v.replace('-', '').isalnum():
            raise ValueError('Slug must be alphanumeric with hyphens')
        return v.lower()

class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    automation_enabled: Optional[bool] = None
    max_concurrent_tasks: Optional[int] = None
    daily_cost_limit_usd: Optional[float] = None

class ProjectResponse(ProjectBase):
    id: UUID
    created_at: datetime
    updated_at: datetime
    framework_preset: Optional[dict] = None
    claude_account: Optional[dict] = None
    stats: Optional[dict] = None

    class Config:
        orm_mode = True
```

---

### Day 4: Core Configuration and Utilities

**Tasks**:
- [ ] Create settings management (using Pydantic Settings)
- [ ] Implement logging configuration
- [ ] Create authentication utilities (JWT, API keys)
- [ ] Set up CORS and middleware
- [ ] Create database utilities (connection pooling, session management)

**Deliverables**:

**File**: `lazy_bird/core/config.py`
```python
from pydantic_settings import BaseSettings
from typing import List

class Settings(BaseSettings):
    # Database
    DATABASE_URL: str
    DB_POOL_SIZE: int = 20
    DB_MAX_OVERFLOW: int = 10

    # Redis
    REDIS_URL: str

    # Celery
    CELERY_BROKER_URL: str
    CELERY_RESULT_BACKEND: str

    # API
    API_TITLE: str = "Lazy-Bird API"
    API_VERSION: str = "2.0.0"
    ALLOWED_ORIGINS: List[str] = ["http://localhost:5173"]

    # Security
    SECRET_KEY: str
    API_KEY_SALT: str
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRATION_MINUTES: int = 15

    # Claude
    CLAUDE_DEFAULT_MODEL: str = "claude-sonnet-4-5"

    class Config:
        env_file = ".env"

settings = Settings()
```

**File**: `lazy_bird/core/security.py`
```python
import secrets
import hashlib
from datetime import datetime, timedelta
from jose import jwt
from lazy_bird.core.config import settings

def generate_api_key() -> tuple[str, str]:
    """Generate API key and its hash"""
    key = f"lb_live_{secrets.token_urlsafe(24)}"
    key_hash = hashlib.sha256(key.encode()).hexdigest()
    return key, key_hash

def verify_api_key(key: str, key_hash: str) -> bool:
    """Verify API key against hash"""
    computed_hash = hashlib.sha256(key.encode()).hexdigest()
    return secrets.compare_digest(computed_hash, key_hash)

def create_access_token(data: dict) -> str:
    """Create JWT access token"""
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=settings.JWT_EXPIRATION_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
```

---

### Day 5: Basic FastAPI Application

**Tasks**:
- [ ] Create FastAPI app instance
- [ ] Implement health check endpoint
- [ ] Set up dependency injection
- [ ] Configure authentication middleware
- [ ] Add request logging middleware
- [ ] Create error handlers

**Deliverables**:

**File**: `lazy_bird/api/main.py`
```python
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from lazy_bird.core.config import settings
from lazy_bird.api import dependencies
import logging

logger = logging.getLogger(__name__)

app = FastAPI(
    title=settings.API_TITLE,
    version=settings.API_VERSION,
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Exception handlers
@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "type": "https://lazy-bird.dev/errors/internal-error",
            "title": "Internal Server Error",
            "status": 500,
            "detail": str(exc)
        }
    )

@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "version": settings.API_VERSION
    }
```

**Commands**:
```bash
# Start development server
uvicorn lazy_bird.api.main:app --reload --port 8000

# Test
curl http://localhost:8000/health
```

---

## Week 2: API Endpoints and Services

### Day 6: Projects API

**Tasks**:
- [ ] Implement GET /api/v1/projects (list)
- [ ] Implement POST /api/v1/projects (create)
- [ ] Implement GET /api/v1/projects/:id (get)
- [ ] Implement PATCH /api/v1/projects/:id (update)
- [ ] Implement DELETE /api/v1/projects/:id (delete)
- [ ] Add pagination support
- [ ] Write unit tests

**Deliverables**:

**File**: `lazy_bird/api/routers/projects.py`
```python
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from uuid import UUID

from lazy_bird.core.database import get_db
from lazy_bird.models.project import Project
from lazy_bird.schemas.project import ProjectCreate, ProjectUpdate, ProjectResponse
from lazy_bird.api.dependencies import get_current_api_key

router = APIRouter()

@router.get("/", response_model=dict)
async def list_projects(
    limit: int = 20,
    cursor: Optional[str] = None,
    automation_enabled: Optional[bool] = None,
    db: Session = Depends(get_db),
    api_key = Depends(get_current_api_key)
):
    query = db.query(Project)

    if automation_enabled is not None:
        query = query.filter(Project.automation_enabled == automation_enabled)

    # Apply cursor pagination
    # ... implementation

    projects = query.limit(limit).all()

    return {
        "data": projects,
        "pagination": {
            "next_cursor": "...",
            "has_more": len(projects) == limit
        }
    }

@router.post("/", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_project(
    project: ProjectCreate,
    db: Session = Depends(get_db),
    api_key = Depends(get_current_api_key)
):
    # Check slug uniqueness
    if db.query(Project).filter(Project.slug == project.slug).first():
        raise HTTPException(status_code=400, detail="Slug already exists")

    db_project = Project(**project.dict())
    db.add(db_project)
    db.commit()
    db.refresh(db_project)

    return db_project
```

**Tests**: `tests/api/test_projects.py`
```python
from fastapi.testclient import TestClient
from lazy_bird.api.main import app

client = TestClient(app)

def test_create_project():
    response = client.post(
        "/api/v1/projects",
        json={
            "name": "Test Project",
            "slug": "test-project",
            "repo_url": "https://github.com/user/repo",
            "project_type": "python"
        },
        headers={"Authorization": "Bearer test_api_key"}
    )
    assert response.status_code == 201
    assert response.json()["slug"] == "test-project"
```

---

### Day 7-8: Tasks API

**Tasks**:
- [ ] Implement GET /api/v1/tasks (list)
- [ ] Implement POST /api/v1/tasks/queue (queue task)
- [ ] Implement GET /api/v1/tasks/:id (get details)
- [ ] Implement POST /api/v1/tasks/:id/cancel (cancel)
- [ ] Implement POST /api/v1/tasks/:id/retry (retry)
- [ ] Implement GET /api/v1/tasks/:id/logs (get logs)
- [ ] Implement GET /api/v1/tasks/:id/logs/stream (SSE)
- [ ] Write unit tests

**Deliverables**: Similar structure to projects API

---

### Day 9: Claude Accounts & Framework Presets APIs

**Tasks**:
- [ ] Implement Claude Accounts CRUD endpoints
- [ ] Implement Framework Presets CRUD endpoints
- [ ] Add seed data for built-in presets
- [ ] Write tests

---

### Day 10: Webhooks API

**Tasks**:
- [ ] Implement webhook subscription CRUD
- [ ] Create webhook publisher service
- [ ] Implement signature generation
- [ ] Add retry logic
- [ ] Write tests

**File**: `lazy_bird/services/webhook_service.py`
```python
import hmac
import hashlib
import httpx
from typing import Dict, Any
from sqlalchemy.orm import Session
from lazy_bird.models.webhook import WebhookSubscription

class WebhookService:
    async def publish_event(
        self,
        db: Session,
        event_type: str,
        data: Dict[str, Any],
        project_id: Optional[str] = None
    ):
        """Publish event to all matching webhooks"""
        query = db.query(WebhookSubscription).filter(
            WebhookSubscription.is_active == True
        )

        if project_id:
            query = query.filter(
                (WebhookSubscription.project_id == project_id) |
                (WebhookSubscription.project_id == None)
            )

        webhooks = query.all()

        for webhook in webhooks:
            if self._event_matches(event_type, webhook.events):
                await self._send_webhook(webhook, event_type, data)

    async def _send_webhook(
        self,
        webhook: WebhookSubscription,
        event_type: str,
        data: Dict[str, Any]
    ):
        """Send webhook with retry logic"""
        payload = {
            "id": f"evt_{secrets.token_hex(8)}",
            "type": event_type,
            "timestamp": datetime.utcnow().isoformat(),
            "data": data
        }

        payload_json = json.dumps(payload)
        signature = self._generate_signature(payload_json, webhook.secret)

        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                response = await client.post(
                    webhook.url,
                    json=payload,
                    headers={
                        "X-Lazy-Bird-Signature": signature,
                        "X-Lazy-Bird-Event": event_type
                    }
                )
                response.raise_for_status()
                # Update last_triggered_at
            except Exception as e:
                logger.error(f"Webhook delivery failed: {e}")
                # Increment failure count, schedule retry
```

---

## Week 3: Background Tasks and Celery

### Day 11-12: Celery Task Migration

**Tasks**:
- [ ] Set up Celery application
- [ ] Migrate queue processor task
- [ ] Migrate task executor
- [ ] Implement cleanup tasks
- [ ] Configure Celery Beat scheduler
- [ ] Write tests for background tasks

**File**: `lazy_bird/tasks/__init__.py`
```python
from celery import Celery
from lazy_bird.core.config import settings

app = Celery('lazy_bird')
app.config_from_object('lazy_bird.tasks.celeryconfig')

# Auto-discover tasks
app.autodiscover_tasks(['lazy_bird.tasks'])
```

**File**: `lazy_bird/tasks/queue_processor.py`
```python
from lazy_bird.tasks import app
from lazy_bird.core.database import SessionLocal
from lazy_bird.models.task_run import TaskRun
from lazy_bird.services.task_executor import TaskExecutor

@app.task
def process_queue():
    """Process queued tasks"""
    db = SessionLocal()
    try:
        queued_tasks = db.query(TaskRun).filter(
            TaskRun.status == 'queued'
        ).limit(10).all()

        for task in queued_tasks:
            execute_task.delay(str(task.id))
    finally:
        db.close()

@app.task
def execute_task(task_run_id: str):
    """Execute a single task"""
    db = SessionLocal()
    try:
        executor = TaskExecutor(db)
        executor.execute(task_run_id)
    finally:
        db.close()
```

---

### Day 13: Git and Claude Services

**Tasks**:
- [ ] Migrate GitService (worktree management)
- [ ] Migrate ClaudeService (CLI execution)
- [ ] Migrate TestRunner
- [ ] Migrate PRService
- [ ] Write integration tests

---

### Day 14: Real-time Logging (SSE)

**Tasks**:
- [ ] Implement Redis Pub/Sub for logs
- [ ] Create SSE endpoint for log streaming
- [ ] Update task executor to publish logs
- [ ] Test real-time streaming
- [ ] Add WebSocket alternative (optional)

**File**: `lazy_bird/api/routers/logs.py`
```python
from fastapi import APIRouter
from sse_starlette.sse import EventSourceResponse
import asyncio
from lazy_bird.core.redis import redis_client

router = APIRouter()

@router.get("/tasks/{task_run_id}/logs/stream")
async def stream_logs(task_run_id: str):
    async def event_generator():
        pubsub = redis_client.pubsub()
        await pubsub.subscribe(f"task_logs:{task_run_id}")

        try:
            async for message in pubsub.listen():
                if message['type'] == 'message':
                    yield {
                        "data": message['data'].decode()
                    }
        finally:
            await pubsub.unsubscribe(f"task_logs:{task_run_id}")

    return EventSourceResponse(event_generator())
```

---

## Week 4: Client Extraction and Testing

### Day 15-16: Web UI Extraction

**Tasks**:
- [ ] Create lazy-bird-ui repository
- [ ] Set up Vite + React + TypeScript
- [ ] Create API client library
- [ ] Migrate React components
- [ ] Set up TanStack Query for state management
- [ ] Implement real-time log viewer
- [ ] Build and test

---

### Day 17: Plane Integration Client

**Tasks**:
- [ ] Create plane-lazy-bird-integration repository
- [ ] Create LazyBirdClient Python class
- [ ] Migrate Django signals
- [ ] Implement webhook receiver
- [ ] Create minimal models (mapping only)
- [ ] Write integration tests
- [ ] Package for PyPI

---

### Day 18-19: Integration Testing

**Tasks**:
- [ ] End-to-end tests (Core → UI)
- [ ] End-to-end tests (Core → Plane)
- [ ] Webhook delivery tests
- [ ] Performance testing
- [ ] Load testing (concurrent tasks)
- [ ] Security testing (auth, CORS, injection)

**Test Plan**:
```python
# tests/integration/test_full_workflow.py
async def test_complete_task_flow():
    """Test: Queue task → Execute → Create PR → Webhook delivery"""

    # 1. Queue task via API
    response = await client.post("/api/v1/tasks/queue", json={...})
    task_run_id = response.json()["id"]

    # 2. Wait for task to start
    await wait_for_status(task_run_id, "running")

    # 3. Stream logs and verify progress
    async for log in stream_logs(task_run_id):
        assert log["level"] in ["info", "debug", "error"]

    # 4. Wait for completion
    task = await wait_for_status(task_run_id, "success")
    assert task["pr_url"] is not None

    # 5. Verify webhook was sent
    webhook_event = await get_webhook_delivery(task_run_id)
    assert webhook_event["type"] == "task.completed"
```

---

### Day 20: Documentation and Deployment

**Tasks**:
- [ ] Update README.md
- [ ] Write API documentation (OpenAPI/Swagger)
- [ ] Create deployment guide
- [ ] Update CLAUDE.md
- [ ] Write migration guide (v1.1 → v2.0)
- [ ] Create Docker Compose files
- [ ] Create Kubernetes manifests (optional)
- [ ] Deploy to staging environment
- [ ] Run smoke tests

**Documentation**:
- API Reference (auto-generated from OpenAPI)
- Getting Started guide
- Migration guide
- Deployment guide
- Architecture overview

---

## Post-Implementation Tasks

### Week 5: Beta Testing and Refinement

**Tasks**:
- [ ] Deploy to beta environment
- [ ] Invite beta testers
- [ ] Collect feedback
- [ ] Fix bugs
- [ ] Performance optimization
- [ ] Security audit

### Week 6: Production Release

**Tasks**:
- [ ] Final testing
- [ ] Deploy to production
- [ ] Monitor metrics
- [ ] Create v2.0.0 release
- [ ] Announce release
- [ ] Update documentation site

---

## Rollout Strategy

### Phase 1: Parallel Operation (Week 1-4)

- v1.1 continues to run
- v2.0 deployed to separate environment
- No production traffic

### Phase 2: Beta Release (Week 5)

- Select beta users
- Gradual traffic shift (10% → 50% → 100%)
- Monitor error rates
- Rollback plan ready

### Phase 3: General Availability (Week 6)

- Full production deployment
- v1.1 deprecated but supported for 30 days
- Migration assistance available

### Phase 4: v1.1 Sunset (Week 10)

- Remove v1.1 code
- Archive old repository
- Update all documentation

---

## Success Metrics

- [ ] All v1.1 features working in v2.0
- [ ] API response time < 200ms (p95)
- [ ] Task execution time unchanged
- [ ] Zero data loss during migration
- [ ] 100% test coverage for core services
- [ ] API documentation complete
- [ ] 3 clients successfully integrated (UI, Plane, CLI)

---

**Next**: [Migration Guide](07-migration-guide.md)
