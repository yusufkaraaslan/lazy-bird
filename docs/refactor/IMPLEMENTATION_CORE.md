# lazy-bird Core Engine - Implementation Plan

**Status:** ✅ **IMPLEMENTED** (v2.0 Complete - 2026-01-03)

## Repository: yusufkaraaslan/lazy-bird

This is the **core engine** implementation plan, extracted from the main v2.0 refactoring plan.

## Timeline: Week 1-3 (15 working days)

### Prerequisites
- PostgreSQL 14+ installed
- Redis installed
- Python 3.10+ installed
- Git configured

---

## Week 1: Foundation & Database

### Day 1: Repository Setup ✅ (Already Done)
- [x] Branch created: `refactor/v2.0`
- [x] Documentation complete

**New Tasks**:
- [ ] Set up new directory structure
- [ ] Initialize Python package with Poetry
- [ ] Configure development environment (.env.example)
- [ ] Set up PostgreSQL database
- [ ] Initialize Alembic

**Issues**: #50, #51, #52

---

### Day 2: Database Schema & Models

**Tasks**:
- [ ] Create SQLAlchemy Base class
- [ ] Implement Project model
- [ ] Implement ClaudeAccount model
- [ ] Implement FrameworkPreset model
- [ ] Implement TaskRun model
- [ ] Implement TaskRunLog model
- [ ] Implement WebhookSubscription model
- [ ] Implement DailyUsage model
- [ ] Implement ApiKey model
- [ ] Create Alembic migrations
- [ ] Apply migrations and test

**Issues**: #53, #54, #55, #56, #57, #58, #59, #60, #61, #62

**Deliverable**: All database tables created and tested

---

### Day 3: Pydantic Schemas

**Tasks**:
- [ ] Create schemas for Project (Create, Update, Response)
- [ ] Create schemas for ClaudeAccount
- [ ] Create schemas for FrameworkPreset
- [ ] Create schemas for TaskRun
- [ ] Create schemas for TaskRunLog
- [ ] Create schemas for Webhook
- [ ] Create schemas for ApiKey
- [ ] Add validation rules
- [ ] Write schema tests

**Issues**: #63, #64, #65, #66, #67, #68, #69, #70

**Deliverable**: Complete Pydantic schema layer with validation

---

### Day 4: Core Configuration

**Tasks**:
- [ ] Create settings management (Pydantic Settings)
- [ ] Implement logging configuration
- [ ] Create authentication utilities (JWT, API keys)
- [ ] Set up CORS and middleware
- [ ] Create database utilities (connection pooling)
- [ ] Configure Redis connection
- [ ] Write configuration tests

**Issues**: #71, #72, #73, #74, #75

**Deliverable**: Complete configuration layer

---

### Day 5: Basic FastAPI Application

**Tasks**:
- [ ] Create FastAPI app instance
- [ ] Implement health check endpoint
- [ ] Set up dependency injection
- [ ] Configure authentication middleware
- [ ] Add request logging middleware
- [ ] Create error handlers (RFC 7807 format)
- [ ] Set up OpenAPI/Swagger docs
- [ ] Test basic endpoints

**Issues**: #76, #77, #78, #79, #80

**Deliverable**: Running FastAPI application with /health endpoint

---

## Week 2: API Endpoints & Services

### Day 6: Projects API

**Tasks**:
- [ ] Implement GET /api/v1/projects (list with pagination)
- [ ] Implement POST /api/v1/projects (create)
- [ ] Implement GET /api/v1/projects/:id (get)
- [ ] Implement PATCH /api/v1/projects/:id (update)
- [ ] Implement DELETE /api/v1/projects/:id (soft delete)
- [ ] Add filtering and search
- [ ] Write API tests
- [ ] Update OpenAPI docs

**Issues**: #81, #82, #83, #84, #85, #86

**Deliverable**: Complete Projects API

---

### Day 7: Tasks API (Part 1)

**Tasks**:
- [ ] Implement GET /api/v1/tasks (list with filters)
- [ ] Implement POST /api/v1/tasks/queue (queue task)
- [ ] Implement GET /api/v1/tasks/:id (get details)
- [ ] Add pagination and filtering
- [ ] Write API tests

**Issues**: #87, #88, #89, #90

**Deliverable**: Basic Tasks API (read + queue)

---

### Day 8: Tasks API (Part 2)

**Tasks**:
- [ ] Implement POST /api/v1/tasks/:id/cancel (cancel task)
- [ ] Implement POST /api/v1/tasks/:id/retry (retry failed task)
- [ ] Implement GET /api/v1/tasks/:id/logs (get logs)
- [ ] Implement GET /api/v1/tasks/:id/logs/stream (SSE streaming)
- [ ] Write streaming tests

**Issues**: #91, #92, #93, #94

**Deliverable**: Complete Tasks API with streaming

---

### Day 9: Accounts & Presets APIs

**Tasks**:
- [ ] Implement ClaudeAccounts CRUD (5 endpoints)
- [ ] Implement FrameworkPresets CRUD (5 endpoints)
- [ ] Add seed data for built-in presets
- [ ] Encrypt sensitive fields (API keys)
- [ ] Write tests

**Issues**: #95, #96, #97, #98

**Deliverable**: Accounts and Presets APIs complete

---

### Day 10: Webhooks API

**Tasks**:
- [ ] Implement webhook subscription CRUD
- [ ] Create webhook publisher service
- [ ] Implement HMAC signature generation
- [ ] Add retry logic for failed deliveries
- [ ] Implement webhook testing endpoint
- [ ] Write integration tests

**Issues**: #99, #100, #101, #102, #103

**Deliverable**: Complete Webhooks system

---

## Week 3: Background Tasks & Services

### Day 11: Celery Setup

**Tasks**:
- [ ] Set up Celery application
- [ ] Configure Celery Beat scheduler
- [ ] Create celeryconfig.py
- [ ] Set up task routing
- [ ] Configure Redis as broker
- [ ] Write basic task tests

**Issues**: #104, #105, #106

**Deliverable**: Celery infrastructure ready

---

### Day 12: Queue Processor

**Tasks**:
- [ ] Migrate queue_processor task from v1.1
- [ ] Implement task selection logic
- [ ] Add concurrency limits
- [ ] Implement task prioritization
- [ ] Add monitoring and metrics
- [ ] Write processor tests

**Issues**: #107, #108, #109, #110

**Deliverable**: Queue processor working

---

### Day 13: Task Executor & Services

**Tasks**:
- [ ] Migrate GitService (worktree management)
- [ ] Migrate ClaudeService (CLI execution)
- [ ] Migrate TestRunner service
- [ ] Migrate PRService (GitHub/GitLab PR creation)
- [ ] Update services for v2.0 architecture
- [ ] Write service integration tests

**Issues**: #111, #112, #113, #114, #115

**Deliverable**: All core services working

---

### Day 14: Real-time Logging (SSE)

**Tasks**:
- [ ] Implement Redis Pub/Sub for logs
- [ ] Create SSE endpoint implementation
- [ ] Update task executor to publish logs
- [ ] Add log filtering and formatting
- [ ] Test real-time streaming
- [ ] Add reconnection handling

**Issues**: #116, #117, #118, #119

**Deliverable**: Real-time log streaming working

---

### Day 15: Polish & Testing

**Tasks**:
- [ ] End-to-end integration tests
- [ ] Performance testing
- [ ] Security audit
- [ ] Fix bugs found in testing
- [ ] Update documentation
- [ ] Create Docker Compose setup
- [ ] Prepare for client development

**Issues**: #120, #121, #122, #123, #124

**Deliverable**: Core engine ready for client integration

---

## Success Criteria

- [ ] All API endpoints working and tested
- [ ] Database migrations applied
- [ ] Celery tasks executing correctly
- [ ] Webhooks publishing events
- [ ] Real-time logs streaming via SSE
- [ ] 80%+ test coverage
- [ ] API documentation complete
- [ ] Docker Compose working
- [ ] Health checks passing
- [ ] Performance targets met (<200ms API response time)

---

## GitHub Project Board Structure

### Columns

1. **📋 Backlog** - All issues not yet started
2. **🎯 Ready** - Issues ready to work on
3. **🚧 In Progress** - Currently being worked on
4. **👀 In Review** - PR created, awaiting review
5. **✅ Done** - Completed and merged

### Labels

- `week-1` - Week 1 tasks
- `week-2` - Week 2 tasks
- `week-3` - Week 3 tasks
- `priority:critical` - Must complete for milestone
- `priority:high` - Important but not blocking
- `priority:medium` - Nice to have
- `type:database` - Database related
- `type:api` - API endpoint
- `type:service` - Business logic service
- `type:celery` - Background task
- `type:testing` - Test related
- `blocked` - Blocked by another issue
- `blocking` - Blocking other issues
- `api-breaking` - Breaking API change

---

## Next Steps

1. Create GitHub issues from this plan (run: `.github/scripts/create_core_issues.py`)
2. Set up GitHub Project board
3. Create `refactor/v2.0` branch
4. Start Week 1, Day 1 tasks

**Dependencies**: None (this is the base repository)

**Blocks**: lazy-bird-ui and plane-lazy-bird-integration (they need the API ready)
