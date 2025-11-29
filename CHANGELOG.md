# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
| 0.1.0 | 2025-11-12 | Web UI Complete, pip/UV distribution |
| 1.0.0 | 2025-11-02 | Multi-framework (18), Phase 1.1 complete |
| 0.9.0 | 2025-10-XX | Initial release, core infrastructure |

---

**Note**: This project follows a progressive development model. Each phase adds capabilities while maintaining backward compatibility. Phase 1.1 is currently production-ready.

For detailed technical specifications, see [Docs/Design/](Docs/Design/).
