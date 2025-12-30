# Client Separation - Lazy-Bird v2.0

## Overview

This document guides the extraction of client implementations from the current integrated codebase into separate repositories that communicate with the core engine via REST API.

## Current Architecture (v1.1)

```
plane-lazy-bird/ (Single Repository)
├── apps/
│   ├── api/
│   │   └── plane/
│   │       ├── db/models/          # Plane models
│   │       └── lazy_bird/          # Lazy-Bird integration
│   │           ├── models.py       # Lazy-Bird models
│   │           ├── services/       # Business logic
│   │           ├── tasks.py        # Celery tasks
│   │           └── views.py        # API endpoints
│   └── web/
│       └── ce/components/
│           └── automations/        # React components
│               └── lazy-bird-toggle.tsx
```

**Problems**:
- Tight coupling between Plane and Lazy-Bird
- Can't use Lazy-Bird with other tools (Jira, Linear, GitHub Projects)
- Difficult to test Lazy-Bird independently
- Mixed database schemas

## Target Architecture (v2.0)

### Repository Structure

```
lazy-bird/              (Core Engine - This Repository)
├── lazy_bird/
│   ├── api/            # FastAPI application
│   ├── models/         # SQLAlchemy models
│   ├── services/       # Business logic
│   └── tasks/          # Celery tasks

lazy-bird-ui/           (New Repository - Web UI)
├── src/
│   ├── components/     # React components
│   ├── pages/          # Routes
│   ├── api/            # API client
│   └── hooks/          # React hooks

plane-lazy-bird-integration/  (New Repository - Plane Client)
├── plane_lazy_bird/
│   ├── client.py       # Lazy-Bird API client
│   ├── signals.py      # Django signals
│   ├── webhooks.py     # Webhook receiver
│   └── components/     # React components for Plane UI
```

## Migration Steps

### Phase 1: Extract Core Engine

#### 1.1 Create New Repository Structure

```bash
# In lazy-bird repository
mkdir -p lazy_bird/{api,models,schemas,services,tasks,core,tests}
touch lazy_bird/{__init__.py,api/__init__.py,models/__init__.py}
```

#### 1.2 Move Models

**From**: `plane-lazy-bird/apps/api/plane/lazy_bird/models.py`

**To**: `lazy_bird/models/` (Split into separate files)

```python
# lazy_bird/models/project.py
from sqlalchemy import Column, String, Boolean, Integer, DECIMAL, TIMESTAMP
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from lazy_bird.core.database import Base

class Project(Base):
    __tablename__ = "projects"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    name = Column(String(255), nullable=False)
    slug = Column(String(100), unique=True, nullable=False)
    # ... (see database schema doc)
```

**Changes Required**:
- Replace Django ORM with SQLAlchemy
- Remove Plane-specific foreign keys
- Add UUID primary keys (instead of integers)
- Update field types to PostgreSQL types

#### 1.3 Move Services

**From**: `plane-lazy-bird/apps/api/plane/lazy_bird/services/`

**To**: `lazy_bird/services/`

**Key Changes**:

```python
# OLD (Django-coupled)
from plane.db.models import Issue
from plane.lazy_bird.models import TaskRun

class PlaneService:
    def get_work_item_details(self, issue_id: str):
        issue = Issue.objects.get(id=issue_id)
        return {
            'id': issue.id,
            'title': issue.name,
            'description': issue.description_html
        }

# NEW (API-based)
class WorkItemClient:
    """Abstract client for work item systems"""

    def get_work_item_details(self, work_item_id: str) -> dict:
        """Get work item details from external system"""
        raise NotImplementedError
```

The Plane-specific implementation moves to `plane-lazy-bird-integration` repository.

#### 1.4 Move Celery Tasks

**From**: `plane-lazy-bird/apps/api/plane/lazy_bird/tasks.py`

**To**: `lazy_bird/tasks/queue_processor.py`

**Key Changes**:

```python
# OLD (Direct database access to Plane)
def process_work_item(task_run_id: str):
    task_run = TaskRun.objects.get(id=task_run_id)
    issue = Issue.objects.get(id=task_run.work_item_id)

    # Update issue state directly
    issue.state = State.objects.get(name='In Progress')
    issue.save()

# NEW (Webhook-based)
def process_task(task_run_id: str):
    task_run = db.query(TaskRun).get(task_run_id)

    # Publish webhook event instead
    webhook_service.publish_event(
        event_type='task.started',
        data={
            'task_run_id': task_run_id,
            'work_item_id': task_run.work_item_id,
            'project_id': task_run.project_id
        }
    )

    # Execute task...
```

#### 1.5 Create FastAPI Application

**New File**: `lazy_bird/api/main.py`

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from lazy_bird.api import routers
from lazy_bird.core.config import settings

app = FastAPI(
    title="Lazy-Bird API",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(routers.projects.router, prefix="/api/v1/projects", tags=["projects"])
app.include_router(routers.tasks.router, prefix="/api/v1/tasks", tags=["tasks"])
app.include_router(routers.accounts.router, prefix="/api/v1/accounts", tags=["accounts"])
app.include_router(routers.webhooks.router, prefix="/api/v1/webhooks", tags=["webhooks"])

@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "version": "2.0.0"
    }
```

---

### Phase 2: Extract Web UI Client

#### 2.1 Create New Repository

```bash
mkdir lazy-bird-ui
cd lazy-bird-ui
npm create vite@latest . -- --template react-ts
npm install @tanstack/react-query axios zustand
```

#### 2.2 Move Components

**From**: `plane-lazy-bird/apps/web/ce/components/automations/`

**To**: `lazy-bird-ui/src/components/`

**Example Component Migration**:

```tsx
// OLD (Plane-integrated)
import { useMutation } from '@tanstack/react-query';
import { AutomationService } from '@/services/automation.service';

export const LazyBirdToggle = ({ projectId }: { projectId: string }) => {
  const { mutate } = useMutation({
    mutationFn: (enabled: boolean) =>
      AutomationService.updateConfig(projectId, { enabled })
  });

  // Component uses Plane's state management...
};

// NEW (API-based)
import { useMutation, useQuery } from '@tanstack/react-query';
import { lazyBirdClient } from '@/api/client';

export const LazyBirdToggle = ({ projectId }: { projectId: string }) => {
  const { data: project } = useQuery({
    queryKey: ['projects', projectId],
    queryFn: () => lazyBirdClient.projects.get(projectId)
  });

  const { mutate } = useMutation({
    mutationFn: (enabled: boolean) =>
      lazyBirdClient.projects.update(projectId, {
        automation_enabled: enabled
      })
  });

  return (
    <Switch
      checked={project?.automation_enabled ?? false}
      onCheckedChange={mutate}
    />
  );
};
```

#### 2.3 Create API Client

**New File**: `lazy-bird-ui/src/api/client.ts`

```typescript
import axios, { AxiosInstance } from 'axios';

class LazyBirdClient {
  private client: AxiosInstance;

  constructor(baseURL: string, apiKey: string) {
    this.client = axios.create({
      baseURL,
      headers: {
        'Authorization': `Bearer ${apiKey}`,
        'Content-Type': 'application/json'
      }
    });
  }

  projects = {
    list: async (params?: { limit?: number; cursor?: string }) => {
      const { data } = await this.client.get('/api/v1/projects', { params });
      return data;
    },

    get: async (id: string) => {
      const { data } = await this.client.get(`/api/v1/projects/${id}`);
      return data;
    },

    create: async (project: CreateProjectInput) => {
      const { data } = await this.client.post('/api/v1/projects', project);
      return data;
    },

    update: async (id: string, updates: Partial<Project>) => {
      const { data } = await this.client.patch(`/api/v1/projects/${id}`, updates);
      return data;
    }
  };

  tasks = {
    list: async (params?: ListTasksParams) => {
      const { data } = await this.client.get('/api/v1/tasks', { params });
      return data;
    },

    queue: async (task: QueueTaskInput) => {
      const { data } = await this.client.post('/api/v1/tasks/queue', task);
      return data;
    },

    streamLogs: (taskRunId: string) => {
      return new EventSource(
        `${this.client.defaults.baseURL}/api/v1/tasks/${taskRunId}/logs/stream`,
        {
          headers: {
            'Authorization': this.client.defaults.headers.common['Authorization']
          }
        }
      );
    }
  };
}

export const lazyBirdClient = new LazyBirdClient(
  import.meta.env.VITE_LAZY_BIRD_API_URL,
  import.meta.env.VITE_LAZY_BIRD_API_KEY
);
```

#### 2.4 Update State Management

```typescript
// lazy-bird-ui/src/stores/tasks.ts
import create from 'zustand';
import { lazyBirdClient } from '@/api/client';

interface TasksState {
  tasks: Task[];
  activeTasks: Task[];
  fetchTasks: (projectId: string) => Promise<void>;
  queueTask: (task: QueueTaskInput) => Promise<void>;
}

export const useTasksStore = create<TasksState>((set) => ({
  tasks: [],
  activeTasks: [],

  fetchTasks: async (projectId: string) => {
    const { data } = await lazyBirdClient.tasks.list({
      project_id: projectId,
      status: 'running'
    });
    set({ activeTasks: data });
  },

  queueTask: async (task: QueueTaskInput) => {
    const newTask = await lazyBirdClient.tasks.queue(task);
    set((state) => ({
      tasks: [...state.tasks, newTask]
    }));
  }
}));
```

---

### Phase 3: Create Plane Integration Client

#### 3.1 Create New Repository

```bash
mkdir plane-lazy-bird-integration
cd plane-lazy-bird-integration
```

**Structure**:
```
plane-lazy-bird-integration/
├── plane_lazy_bird/
│   ├── __init__.py
│   ├── client.py          # Lazy-Bird API client
│   ├── signals.py         # Django signals for Plane
│   ├── webhooks.py        # Webhook receiver
│   ├── models.py          # Minimal models (just mapping)
│   ├── admin.py           # Django admin integration
│   └── components/        # React components for Plane UI
│       └── LazyBirdPanel.tsx
├── setup.py
├── README.md
└── pyproject.toml
```

#### 3.2 Create API Client

**File**: `plane_lazy_bird/client.py`

```python
import httpx
from typing import Optional, Dict, Any
from django.conf import settings

class LazyBirdClient:
    """Client for Lazy-Bird API"""

    def __init__(self, api_url: str, api_key: str):
        self.api_url = api_url.rstrip('/')
        self.api_key = api_key
        self.client = httpx.AsyncClient(
            headers={
                'Authorization': f'Bearer {api_key}',
                'Content-Type': 'application/json'
            }
        )

    async def queue_task(
        self,
        project_id: str,
        work_item_id: str,
        title: str,
        description: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Queue a new task"""
        response = await self.client.post(
            f'{self.api_url}/api/v1/tasks/queue',
            json={
                'project_id': project_id,
                'work_item_id': work_item_id,
                'work_item_title': title,
                'work_item_description': description,
                'task_type': 'feature',
                'metadata': metadata or {}
            }
        )
        response.raise_for_status()
        return response.json()

    async def get_task_status(self, task_run_id: str) -> Dict[str, Any]:
        """Get task status"""
        response = await self.client.get(
            f'{self.api_url}/api/v1/tasks/{task_run_id}'
        )
        response.raise_for_status()
        return response.json()

    async def cancel_task(self, task_run_id: str) -> Dict[str, Any]:
        """Cancel a running task"""
        response = await self.client.post(
            f'{self.api_url}/api/v1/tasks/{task_run_id}/cancel'
        )
        response.raise_for_status()
        return response.json()

# Global instance
lazy_bird_client = LazyBirdClient(
    api_url=settings.LAZY_BIRD_API_URL,
    api_key=settings.LAZY_BIRD_API_KEY
)
```

#### 3.3 Migrate Django Signals

**File**: `plane_lazy_bird/signals.py`

```python
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from plane.db.models import Issue
from .client import lazy_bird_client
from .models import TaskRunMapping
import asyncio

@receiver(post_save, sender=Issue)
def on_issue_state_change(sender, instance, created, **kwargs):
    """When issue moves to Ready state, queue in Lazy-Bird"""
    if created:
        return

    # Check if automation is enabled for this project
    config = AutomationConfig.objects.filter(
        project_id=instance.project_id,
        enabled=True
    ).first()

    if not config:
        return

    # Check if issue moved to Ready state
    if instance.state.name != config.ready_state_name:
        return

    # Check if already queued
    if TaskRunMapping.objects.filter(
        issue_id=instance.id,
        status__in=['queued', 'running']
    ).exists():
        return

    # Queue task in Lazy-Bird
    async def queue_task():
        result = await lazy_bird_client.queue_task(
            project_id=str(instance.project_id),
            work_item_id=str(instance.id),
            title=instance.name,
            description=instance.description_html or '',
            metadata={
                'source': 'plane',
                'priority': instance.priority,
                'labels': [label.name for label in instance.labels.all()]
            }
        )

        # Create mapping
        TaskRunMapping.objects.create(
            issue_id=instance.id,
            task_run_id=result['id'],
            status='queued'
        )

    # Run async task
    asyncio.create_task(queue_task())
```

#### 3.4 Create Webhook Receiver

**File**: `plane_lazy_bird/webhooks.py`

```python
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.conf import settings
from plane.db.models import Issue, State
from .models import TaskRunMapping
import hmac
import hashlib
import json

@csrf_exempt
@require_POST
def lazy_bird_webhook(request):
    """Receive webhook events from Lazy-Bird"""

    # Verify signature
    payload = request.body
    signature = request.headers.get('X-Lazy-Bird-Signature', '')
    secret = settings.LAZY_BIRD_WEBHOOK_SECRET

    expected_sig = f"sha256={hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()}"
    if not hmac.compare_digest(signature, expected_sig):
        return JsonResponse({'error': 'Invalid signature'}, status=401)

    # Parse event
    event = json.loads(payload)
    event_type = event['type']
    data = event['data']

    # Route to handler
    handlers = {
        'task.queued': handle_task_queued,
        'task.started': handle_task_started,
        'task.completed': handle_task_completed,
        'task.failed': handle_task_failed,
        'pr.created': handle_pr_created,
    }

    handler = handlers.get(event_type)
    if handler:
        handler(data)

    return JsonResponse({'received': True})


def handle_task_started(data):
    """Handle task started event"""
    mapping = TaskRunMapping.objects.get(task_run_id=data['task_run_id'])
    mapping.status = 'running'
    mapping.save()

    issue = Issue.objects.get(id=mapping.issue_id)
    issue.state = State.objects.get(project=issue.project, name='In Progress')
    issue.save()


def handle_task_completed(data):
    """Handle task completed event"""
    mapping = TaskRunMapping.objects.get(task_run_id=data['task_run_id'])
    mapping.status = 'completed'
    mapping.pr_url = data.get('pr_url')
    mapping.save()

    issue = Issue.objects.get(id=mapping.issue_id)

    # Add comment
    issue.comments.create(
        comment_html=f'''
            <p>✅ Task completed successfully!</p>
            <p>PR: <a href="{data['pr_url']}">#{data['pr_number']}</a></p>
            <p>Duration: {data['duration_seconds']}s | Cost: ${data['cost_usd']}</p>
        ''',
        actor_id=None  # System user
    )

    # Move to review state
    issue.state = State.objects.get(project=issue.project, name='In Review')
    issue.save()
```

#### 3.5 Minimal Models

**File**: `plane_lazy_bird/models.py`

```python
from django.db import models

class AutomationConfig(models.Model):
    """Stores which projects have Lazy-Bird enabled"""
    project = models.OneToOneField('db.Project', on_delete=models.CASCADE)
    lazy_bird_project_id = models.UUIDField()  # ID in Lazy-Bird system
    enabled = models.BooleanField(default=False)
    ready_state_name = models.CharField(max_length=100, default='Ready')

    class Meta:
        db_table = 'lazy_bird_automation_config'


class TaskRunMapping(models.Model):
    """Maps Plane issues to Lazy-Bird task runs"""
    issue = models.ForeignKey('db.Issue', on_delete=models.CASCADE)
    task_run_id = models.UUIDField()  # ID in Lazy-Bird system
    status = models.CharField(max_length=50)  # Cached status
    pr_url = models.URLField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'lazy_bird_task_mapping'
```

## Installation Guide

### For Core Engine

```bash
# Clone repository
git clone https://github.com/yusyus/lazy-bird.git
cd lazy-bird

# Install dependencies
pip install -e ".[dev]"

# Run migrations
alembic upgrade head

# Start services
docker-compose up -d
```

### For Web UI

```bash
# Clone repository
git clone https://github.com/yusyus/lazy-bird-ui.git
cd lazy-bird-ui

# Install dependencies
npm install

# Configure environment
cp .env.example .env
# Edit .env with API URL and key

# Start development server
npm run dev
```

### For Plane Integration

```bash
# In Plane repository
pip install plane-lazy-bird-integration

# Add to INSTALLED_APPS
# plane/settings/common.py
INSTALLED_APPS = [
    ...
    'plane_lazy_bird',
]

# Configure
# plane/settings/common.py
LAZY_BIRD_API_URL = env('LAZY_BIRD_API_URL')
LAZY_BIRD_API_KEY = env('LAZY_BIRD_API_KEY')
LAZY_BIRD_WEBHOOK_SECRET = env('LAZY_BIRD_WEBHOOK_SECRET')

# Run migrations
python manage.py migrate

# Register webhook in Lazy-Bird
python manage.py lazy_bird_setup_webhook
```

## Testing Strategy

### Core Engine Tests

```bash
pytest tests/
pytest tests/api/  # API endpoint tests
pytest tests/services/  # Business logic tests
pytest tests/tasks/  # Celery task tests
```

### Integration Tests

```bash
# Test Plane integration
pytest tests/integrations/plane/

# Test webhooks end-to-end
pytest tests/webhooks/
```

## Deployment

### Core Engine

```bash
# Production deployment
docker-compose -f docker-compose.prod.yml up -d

# Or Kubernetes
kubectl apply -f k8s/
```

### Web UI

```bash
# Build for production
npm run build

# Deploy to CDN/hosting
# (Vercel, Netlify, S3 + CloudFront, etc.)
```

### Plane Integration

Plane integration is installed as a Python package within Plane's deployment.

---

**Next**: [Implementation Timeline](06-implementation-timeline.md)
