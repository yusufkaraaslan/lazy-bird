# Lazy-Bird v2.0 Refactoring Plan

**Status:** ✅ **COMPLETE** - All 70 core v2.0 issues closed (2026-01-03)

This refactor has been successfully completed. See:
- [CHANGELOG.md](CHANGELOG.md) for v2.0 release details
- [E2E_TEST_SUCCESS_SUMMARY.md](../Testing/E2E_TEST_SUCCESS_SUMMARY.md) for validation results
- [docs/refactor/](docs/refactor/) for detailed implementation documentation

---

## Overview

This document outlines the comprehensive plan to refactor Lazy-Bird from a tightly-coupled Django integration to a microservice architecture with a core engine API and separate client implementations.

## Goals

1. **Separation of Concerns**: Core engine (API) separate from client implementations
2. **Framework Agnostic**: Support multiple project management tools (Plane, Jira, Linear, etc.)
3. **Scalability**: Independent scaling of engine and clients
4. **Maintainability**: Clear boundaries between components
5. **Feature Parity**: Match or exceed current functionality

## Current State (v1.1)

- Lazy-Bird tightly integrated into Plane Django app
- Direct database access between Lazy-Bird and Plane
- Django signals for bidirectional communication
- React components embedded in Plane UI
- Single repository with mixed concerns

## Target State (v2.0)

- **Core Engine**: FastAPI-based REST API service
- **Database**: Independent PostgreSQL database
- **Queue System**: Celery + Redis for background tasks
- **Clients**: Separate repositories for each viewport
  - `lazy-bird-ui` - Standalone web UI (React + TypeScript)
  - `plane-lazy-bird-integration` - Plane integration layer (Django)
  - Future: CLI client, VS Code extension, etc.
- **Communication**: Webhook-based event system + REST API

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Lazy-Bird Core Engine                    │
│                    (FastAPI + PostgreSQL)                    │
│                                                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │  REST API    │  │  Webhooks    │  │  SSE Logs    │     │
│  │  Endpoints   │  │  Publisher   │  │  Streaming   │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
│                                                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │  Celery      │  │  Git Service │  │  Claude      │     │
│  │  Queue       │  │  Worktrees   │  │  Service     │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
└─────────────────────────────────────────────────────────────┘
                              │
                              │ REST API + Webhooks
                              │
        ┌─────────────────────┼─────────────────────┐
        │                     │                     │
        ▼                     ▼                     ▼
┌──────────────┐      ┌──────────────┐     ┌──────────────┐
│  Lazy-Bird   │      │    Plane     │     │   Future     │
│   Web UI     │      │ Integration  │     │   Clients    │
│  (React TS)  │      │   (Django)   │     │ (CLI, etc.)  │
└──────────────┘      └──────────────┘     └──────────────┘
```

## Multi-Repository Architecture

The v2.0 refactor splits Lazy-Bird into **3 separate repositories**:

### 1. **lazy-bird** (Core Engine) - This Repository
- FastAPI REST API
- PostgreSQL database
- Celery task queue
- Webhook publisher
- **Implementation**: [docs/refactor/IMPLEMENTATION_CORE.md](docs/refactor/IMPLEMENTATION_CORE.md)

### 2. **lazy-bird-ui** (Web UI Client) - New Repository
- React + TypeScript
- Vite build system
- API client library
- **Setup**: [.github/repos-setup/lazy-bird-ui/](.github/repos-setup/lazy-bird-ui/)
- **Implementation**: [.github/repos-setup/lazy-bird-ui/IMPLEMENTATION.md](.github/repos-setup/lazy-bird-ui/IMPLEMENTATION.md)

### 3. **plane-lazy-bird-integration** (Plane Client) - New Repository
- Django package
- API client wrapper
- Signal handlers + webhooks
- **Setup**: [.github/repos-setup/plane-lazy-bird-integration/](.github/repos-setup/plane-lazy-bird-integration/)
- **Implementation**: [.github/repos-setup/plane-lazy-bird-integration/IMPLEMENTATION.md](.github/repos-setup/plane-lazy-bird-integration/IMPLEMENTATION.md)

## Repository Setup Guide

📋 **[REPOSITORY_SETUP.md](.github/repos-setup/REPOSITORY_SETUP.md)** - Complete guide for creating and configuring the 3 repositories with GitHub Projects and issues

## Documentation Structure

### Core Documentation (Applies to All Repos)

1. **[Architecture](docs/refactor/01-architecture.md)** - System design and component overview
2. **[Database Schema](docs/refactor/02-database-schema.md)** - PostgreSQL schema and migrations
3. **[API Endpoints](docs/refactor/03-api-endpoints.md)** - Complete REST API specification
4. **[Webhooks](docs/refactor/04-webhooks.md)** - Event system and webhook architecture
5. **[Client Separation](docs/refactor/05-client-separation.md)** - Guide to extracting clients
6. **[Implementation Timeline](docs/refactor/06-implementation-timeline.md)** - Week-by-week plan (unified view)
7. **[Migration Guide](docs/refactor/07-migration-guide.md)** - v1.1 to v2.0 upgrade path
8. **[Testing Strategy](docs/refactor/08-testing-strategy.md)** - Testing approach and coverage

### Repository-Specific Implementation Plans

- **[Core Engine Implementation](docs/refactor/IMPLEMENTATION_CORE.md)** - Week 1-3, lazy-bird repo (125+ issues)
- **[Web UI Implementation](.github/repos-setup/lazy-bird-ui/IMPLEMENTATION.md)** - Week 4, lazy-bird-ui repo (47+ issues)
- **[Plane Integration Implementation](.github/repos-setup/plane-lazy-bird-integration/IMPLEMENTATION.md)** - Week 4, plane-lazy-bird-integration repo (33+ issues)

## Quick Start

1. Read the [Architecture](docs/refactor/01-architecture.md) document first
2. Review the [Database Schema](docs/refactor/02-database-schema.md) to understand data model
3. Follow the [Implementation Timeline](docs/refactor/06-implementation-timeline.md) for execution
4. Use the [Migration Guide](docs/refactor/07-migration-guide.md) when upgrading existing installations

## Timeline

- **Week 1**: Repository setup, database schema, core models
- **Week 2**: REST API endpoints, authentication, basic CRUD
- **Week 3**: Webhook system, Celery tasks, background processing
- **Week 4**: Client extraction, integration testing, documentation

Total estimated time: **4 weeks** (1 developer, full-time)

## Success Criteria

- [ ] Core engine runs independently without Plane
- [ ] All current features work via REST API
- [ ] Web UI client connects and functions correctly
- [ ] Plane integration works via API calls
- [ ] Webhook events fire correctly
- [ ] Real-time logs stream via SSE
- [ ] All tests pass (unit, integration, e2e)
- [ ] Documentation complete and accurate
- [ ] Performance matches or exceeds v1.1
- [ ] Migration path tested and validated

## Benefits

1. **Multiple Viewports**: Use Lazy-Bird with Plane, Jira, Linear, GitHub Projects, etc.
2. **Independent Scaling**: Scale engine and clients separately
3. **Technology Freedom**: Clients can use any stack (React, Vue, CLI)
4. **Easier Testing**: Test engine without UI dependencies
5. **Better Security**: API authentication, rate limiting, CORS
6. **Deployment Flexibility**: Deploy engine once, connect many clients
7. **Open Source Growth**: Easy for community to build new clients

## Next Steps

1. **Review**: Team reviews this plan and provides feedback
2. **Approve**: Get sign-off from stakeholders
3. **Branch**: Create `refactor/v2.0` development branch
4. **Execute**: Follow implementation timeline
5. **Test**: Comprehensive testing at each phase
6. **Deploy**: Gradual rollout with v1.1 compatibility
7. **Deprecate**: Sunset v1.1 after v2.0 stabilizes

## Questions and Support

For questions about this refactoring plan:
- Open an issue with label `refactor-v2.0`
- Discussion: GitHub Discussions in "Architecture" category
- Documentation: See individual documents linked above

---

**Version**: 2.0.0-alpha
**Last Updated**: 2025-12-30
**Status**: Planning Phase
**Author**: Lazy-Bird Development Team
