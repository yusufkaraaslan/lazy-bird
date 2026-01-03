# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.0.0] - 2026-01-03

### 🎉 v2.0 Complete - Production-Ready Microservice Architecture

**All 70 core v2.0 issues completed and closed!** This release represents a complete rewrite into a production-ready FastAPI microservice architecture with comprehensive testing and validation.

### Added

#### Core Engine
- **FastAPI REST API**: Async/await architecture with 30+ endpoints
- **PostgreSQL Database**: Complete JSONB support, 8 production-ready models
- **SQLAlchemy ORM**: Async support with asyncpg driver
- **Alembic Migrations**: Full database migration system
- **Celery Task Queue**: Distributed task processing with Redis backend
- **Intelligent Task Selection**: Cost-aware task prioritization (Issue #105)
- **Per-Project Concurrency**: Configurable concurrent task limits (Issue #105)
- **Daily Cost Limits**: Budget enforcement per project (Issue #105)

#### Database Schema (8 Models)
- **Project**: Multi-project configuration with cost controls
- **FrameworkPreset**: Framework-specific test/build/lint commands
- **Task**: Distributed task queue with priority and cost tracking
- **TestRun**: Test execution history and results
- **APIKey**: Scoped authentication with permissions
- **User**: User management with role-based access
- **AuditLog**: Complete audit trail for security
- **SystemMetric**: Resource monitoring (CPU, RAM, disk)

#### API Endpoints
- **Project Management**: CRUD operations, enable/disable, cost tracking
- **Framework Presets**: List, create, update builtin/custom presets
- **Task Queue**: Create, list, cancel, prioritize tasks
- **Test Runs**: Execution, results, history
- **Authentication**: API key management with scoped permissions
- **System Monitoring**: Health checks, metrics, resource usage
- **Webhooks**: GitHub/GitLab integration (12+ event types)

#### Testing & Validation
- **Comprehensive E2E Test Suite**: 612-line end-to-end workflow validation
- **PostgreSQL Schema Validation**: Complete JSONB support verified
- **Docker Test Environment**: Isolated PostgreSQL 15 container setup
- **E2E Test Coverage**: Database → Preset → Project → Task → Godot execution
- **Automated Cleanup**: Virtual environment isolation with complete cleanup

### Fixed

#### PostgreSQL Compatibility (5 Issues)
1. **ARRAY Default Syntax**: Fixed `server_default` to use PostgreSQL literal format `'{read}'`
2. **CHECK Constraint Types**: Fixed type mismatch between VARCHAR[] column and TEXT[] constraint
3. **Database Detection**: E2E test now auto-detects PostgreSQL vs SQLite from DATABASE_URL
4. **FrameworkPreset Fields**: Corrected field names (framework_type, display_name, language)
5. **Preset Name Case**: Fixed case sensitivity in preset lookup queries

### Changed
- **Architecture**: Complete rewrite from Phase 1.1 to FastAPI microservice
- **Database**: Migrated from SQLite to PostgreSQL with JSONB support
- **Task Queue**: Migrated from file-based queue to Celery with Redis
- **API Design**: RESTful API with async/await patterns
- **Testing**: Added comprehensive E2E test coverage

### Documentation
- **E2E_TEST_SUCCESS_SUMMARY.md**: Complete E2E test documentation (228 lines)
- **DOCS_AUDIT.md**: Comprehensive documentation audit (125 lines)
- **tests/e2e/README.md**: E2E testing guide with Docker setup
- **Updated README.md**: Reflects v2.0 completion status
- **Updated REFACTOR_PLAN.md**: Marked as complete

### Deployment
- **Docker Compose**: Multi-service deployment (API, Celery, Redis, PostgreSQL)
- **Systemd Services**: Production service definitions
- **Environment Configuration**: Comprehensive .env.example
- **Alembic Migrations**: Database version control

### Validation
- ✅ All 70 core v2.0 issues closed
- ✅ E2E test validates complete workflow
- ✅ PostgreSQL schema fully tested
- ✅ 5 compatibility issues discovered and fixed during testing
- ✅ Production-ready status confirmed

### Migration from v1.x
See `docs/refactor/07-migration-guide.md` for complete migration instructions from Phase 1.1 to v2.0.

## [0.1.0] - 2025-11-29

### 🎉 Published to PyPI
- **Package now available:** `pip install lazy-bird`
- **PyPI page:** https://pypi.org/project/lazy-bird/
- Global CLI command installation
- Automatic dependency management

### Added
- **Package Distribution**: pip and UV installation support via pyproject.toml
- **CLI Entry Points**: 5 command-line tools (lazy-bird, lazy-bird-server, lazy-bird-godot, lazy-bird-watcher, lazy-bird-project)
- **Phase 0 Web UI Complete**: Full React + TypeScript dashboard
  - Dashboard page with system monitoring (CPU, RAM, disk usage)
  - Projects page with CRUD operations (add, edit, remove, enable/disable)
  - Services page with systemd service management (start, stop, restart, enable, disable)
  - Queue page with task viewer and log display
  - Settings page for configuration management
  - Dark mode support (system-aware)
  - Route-based navigation (no modals for better UX)
  - Full TypeScript strict mode
  - TanStack Query for state management
  - Tailwind CSS v4.1 for styling
- **INSTALL.md**: Comprehensive installation guide (397 lines)
- **PHASE0_UI_SUMMARY.md**: Web UI completion documentation

### Changed
- **Architecture**: Converted from modal-based to route-based UI navigation
- **API Port**: Backend runs on port 5000 (was conflicting with 5001)
- **Project Forms**: Moved from modals to dedicated routes (`/projects/add`, `/projects/:id/edit`)
- **Service Forms**: Moved from modals to dedicated routes (`/services/add`, `/services/:name/edit`)

### Fixed
- Project edit form overlapping issues
- Queue UI showing stale completed tasks
- Unbound variable errors in logging (LOG_DIR, ISSUE_ID)
- gdUnit4 tests in worktrees by copying .godot directory
- Browser errors from process.env.USER references
- API client for ServicesPage HTTP methods

## [1.0.0] - 2025-11-02

### Added
- **Multi-Framework Support**: 18 framework presets
  - Game Engines: Godot, Unity, Unreal, Bevy
  - Backend: Django, Flask, FastAPI, Express, Rails
  - Frontend: React, Vue, Angular, Svelte
  - Languages: Python, Rust, Go, Node.js, C/C++, Java
  - Custom: Configurable template
- **Framework Presets**: config/framework-presets.yml (301 lines)
- **Phase 1.1 Complete**: Multi-project management
  - Project manager CLI tool (390 lines)
  - Multi-project issue watcher (760 lines)
  - Multi-project wizard support (360 lines)
  - Projects array configuration schema
  - Per-project test/build/lint commands
  - 26/26 tests passing
- **Phase 0 Validation Suite**: Comprehensive prerequisite testing
  - validate-all.sh master script (350+ lines)
  - validate-claude.sh for CLI testing (230+ lines)
  - validate-godot.sh for Godot testing (280+ lines)
  - test-worktree.sh for git worktree testing (325+ lines)
- **GitHub Issue #18**: Phase 2 implementation task created
- **Announcement Issue #15**: v1.0.0 release announcement

### Changed
- **Framework Count**: Updated from "15+" to 18 documented frameworks
- **Test Server**: Renamed from "Godot Server" to "Test Server" for multi-framework clarity
- **Documentation**: Updated all major docs to reflect multi-framework support

## [0.9.0] - 2025-10-XX (Pre-release)

### Added
- Initial project structure
- Core scripts (wizard.sh, godot-server.py, issue-watcher.py, agent-runner.sh)
- Docker configuration with security hardening
- systemd service definitions
- Comprehensive documentation (9,500+ lines across 13 design docs)
- CLAUDE.md project guide (700+ lines)
- README.md with examples (630 lines)

### Infrastructure
- Git worktree support for task isolation
- GitHub/GitLab issue integration
- Secret management in ~/.config/lazy_birtd/secrets/
- Resource limits and health checks
- Test retry logic (3 attempts max)

## Upcoming

### [Phase 2] - Multi-Agent Coordination (Planned)
- Parallel agent execution (2-3 agents)
- Enhanced test server with queuing
- Agent scheduler with resource awareness
- Worktree registry for conflict prevention

### [Phase 3] - Remote Access (Planned)
- WireGuard VPN setup
- Advanced web dashboard features
- Mobile notifications via ntfy.sh
- Remote monitoring capabilities

### [Phase 4+] - Enterprise Features (Planned)
- Full CI/CD pipeline integration
- GitLab CE self-hosting option
- Advanced orchestration
- Team collaboration features

---

## Version History Summary

| Version | Date | Key Features |
|---------|------|--------------|
| 2.0.0 | 2026-01-03 | **Production Ready!** FastAPI microservice, PostgreSQL, Celery, 70 issues complete, E2E tested |
| 0.1.0 | 2025-11-29 | Web UI Complete, pip/UV distribution |
| 1.0.0 | 2025-11-02 | Multi-framework (18), Phase 1.1 complete |
| 0.9.0 | 2025-10-XX | Initial release, core infrastructure |

---

**Note**: v2.0 represents a complete architectural rewrite into a production-ready microservice system. All 70 core issues have been completed and the system is fully tested with comprehensive E2E coverage.

For detailed technical specifications, see [Docs/Design/](Docs/Design/).
