<div align="center">

```
    🦜                                                      🦜
       _           _     ________  __     __
      | |         / \    |___  /   \ \   / /
      | |        / _ \      / /     \ \_/ /
      | |___    / ___ \    / /__     \   /
      |_____|  /_/   \_\  /_____|     |_|

       ____    ___   ____    ____
      | __ )  |_ _| |  _ \  |  _ \
      |  _ \   | |  | |_) | | | | |
      | |_) |  | |  |  _ <  | |_| |
      |____/  |___| |_| \_\ |____/
    💤                                                      💤
```

### Automate ANY development project while you sleep 🦜💤

### Your AI-powered development assistant that works 24/7

**Works with: Godot, Unity, Python, Rust, Node.js, Django, React, and more!**

[![PyPI version](https://badge.fury.io/py/lazy-bird.svg)](https://pypi.org/project/lazy-bird/)
[![Python Versions](https://img.shields.io/pypi/pyversions/lazy-bird.svg)](https://pypi.org/project/lazy-bird/)
[![Downloads](https://static.pepy.tech/badge/lazy-bird/month)](https://pepy.tech/project/lazy-bird)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Multi-Framework](https://img.shields.io/badge/Frameworks-18-blue.svg)](#-supported-frameworks)
[![Claude](https://img.shields.io/badge/Claude-Code-purple.svg)](https://claude.ai/code)

[![Tests](https://github.com/yusufkaraaslan/lazy-bird/actions/workflows/test.yml/badge.svg)](https://github.com/yusufkaraaslan/lazy-bird/actions/workflows/test.yml)
[![Code Quality](https://github.com/yusufkaraaslan/lazy-bird/actions/workflows/lint.yml/badge.svg)](https://github.com/yusufkaraaslan/lazy-bird/actions/workflows/lint.yml)
[![codecov](https://codecov.io/gh/yusufkaraaslan/lazy-bird/branch/main/graph/badge.svg)](https://codecov.io/gh/yusufkaraaslan/lazy-bird)
[![Status](https://img.shields.io/badge/Status-v2.0%20Complete-brightgreen.svg)]()
[![Production Ready](https://img.shields.io/badge/Production-Ready-success.svg)]()

[Quick Start](#-quick-start) • [Features](#-features) • [Installation](#-installation) • [Docs](CLAUDE.md) • [Architecture](Docs/Design/)

---

</div>

## 🎯 What is Lazy_Bird?

Lazy_Bird is a **progressive automation system** that lets Claude Code work on your development projects autonomously—game engines, backends, frontends, or any codebase. Create GitHub Issues in the morning, review Pull Requests at lunch, and merge completed features in the evening—all while you focus on creative work or simply relax.

```
Morning (7 AM)          Work Hours                 Lunch (12 PM)         Evening (6 PM)
──────────────          ──────────────             ─────────────         ─────────────
Create Issues      →    Claude implements     →    Review PRs       →    Merge & Ship
Add "ready" label       Runs tests automatically   Approve changes       Plan tomorrow
Go to work             Creates PRs if passing      Back to work          Enjoy life
```

**The result?** You save 20-100 hours per month on repetitive development tasks.

---

## 📦 Supported Frameworks

Lazy_Bird works with **any project type** through framework presets. During setup, simply select your framework and the system configures the right test commands automatically.

### Game Engines
- **Godot** - GDScript/C#, gdUnit4 testing
- **Unity** - C#, NUnit/Unity Test Framework
- **Unreal** - C++/Blueprint, automation tests
- **Bevy** - Rust game engine, cargo test

### Backend Frameworks
- **Django** - Python web framework, `python manage.py test`
- **Flask** - Python micro-framework, pytest
- **FastAPI** - Modern Python API, pytest
- **Express** - Node.js web framework, Jest/Mocha
- **Rails** - Ruby web framework, RSpec

### Frontend Frameworks
- **React** - JavaScript/TypeScript, Jest/RTL
- **Vue** - JavaScript/TypeScript, Vitest
- **Angular** - TypeScript, Jasmine/Karma
- **Svelte** - JavaScript/TypeScript, Vitest

### Programming Languages (General)
- **Python** - pytest, unittest, any test framework
- **Rust** - cargo test, cargo-nextest
- **Node.js** - npm test, Jest, Mocha, Vitest
- **Go** - go test, testify
- **C/C++** - make test, CTest, CMake
- **Java** - JUnit, Maven, Gradle

### Custom Projects
**Don't see your framework?** Choose "Custom" during setup and specify your test commands manually. Lazy_Bird supports any framework with a command-line test runner!

---

## 🚀 Quick Start

```bash
# 1. Install via pip (recommended)
pip install lazy-bird

# 2. Run setup wizard
lazy-bird setup

# 3. Create your first automated task
gh issue create --template task \
  --title "[Task]: Add player health system" \
  --label "ready"

# 4. Monitor progress
lazy-bird status
```

**That's it!** The system will pick up your issue, implement the feature, run tests, and create a PR—all automatically.

## 🎉 v2.0 Highlights

Lazy_Bird v2.0 represents a complete rewrite into a production-ready microservice architecture:

**✅ All 70 Core Issues Completed**
- FastAPI microservice architecture with async/await
- PostgreSQL database with complete JSONB support
- Celery distributed task queue with Redis
- 8 production-ready database models
- 30+ REST API endpoints
- Comprehensive E2E test coverage

**🧪 Fully Tested & Validated**
- End-to-end test validates complete workflow
- PostgreSQL schema fully validated
- 5 PostgreSQL compatibility issues discovered and fixed during testing
- Unit and integration test coverage
- Production-ready status confirmed

**🚀 Ready for Deployment**
- Docker and Docker Compose support
- Systemd service integration
- Multi-framework support (18+ frameworks)
- Intelligent task selection with cost controls
- Per-project concurrency limits
- Real-time web dashboard

## ✨ Features

- 🤖 **Autonomous Development** - Claude Code works while you're away
- 🎯 **Multi-Framework Support** - Works with 18 frameworks out-of-the-box
- 🗂️ **Multi-Project Management** - Monitor 2-20+ projects from a single server
- 🖥️ **Web Dashboard** - React + TypeScript UI for monitoring and management (Phase 0 complete!)
- 📦 **Easy Installation** - Available via pip/UV, ready in 5 minutes
- 🧪 **Automated Testing** - Runs framework tests, retries on failure
- 🌿 **Safe Git Workflow** - Isolated worktrees, automatic PRs
- 📊 **Progress Monitoring** - Real-time system stats, task queue viewer
- 🔐 **Security First** - Secret management, containerized execution
- 📈 **Progressive Scaling** - Start simple (1 agent), scale to multiple

## How It Works

```
Morning (7-8am)          Work Hours                Lunch (12pm)        Evening (6pm)
─────────────────       ──────────────            ─────────────       ──────────────
Create GitHub Issues → Claude processes tasks  →  Review PRs      →  Merge & test
Add "ready" label       Runs tests automatically   Approve/comment     Deploy builds
Go to work              Creates PRs if passing     Back to work        Plan tomorrow
```

## Architecture

**v2.0 - Complete Microservice Architecture** (✅ Production Ready!)

Lazy_Bird v2.0 is a full-featured FastAPI microservice architecture with:

**Core Engine:**
- FastAPI REST API with async/await
- PostgreSQL database with JSONB support
- SQLAlchemy ORM with Alembic migrations
- Celery distributed task queue with Redis
- Intelligent task selection with cost controls
- Per-project concurrency limits
- Daily cost limit enforcement

**Web Dashboard:**
- React + TypeScript single-page application
- Real-time system monitoring (CPU, RAM, disk)
- Project management (CRUD operations)
- Task queue viewer with execution logs
- Service control (start/stop/restart systemd services)
- Dark mode support
- Responsive design

**Multi-Framework Support:**
- 18+ frameworks out-of-the-box (Godot, Unity, Python, Rust, React, Django, etc.)
- Framework presets with auto-configuration
- Custom framework support
- Per-project test/build/lint commands

**Database Schema:**
- 8 production-ready tables (Projects, FrameworkPresets, Tasks, APIKeys, etc.)
- Complete PostgreSQL JSONB support
- Alembic migration system
- Full E2E test coverage

**Testing & Validation:**
- Comprehensive E2E test suite
- PostgreSQL schema validation
- Complete workflow testing (database → execution → PRs)
- Unit and integration test coverage

**Deployment:**
- Docker and Docker Compose support
- Systemd service integration
- Multi-project monitoring from single server
- Production-ready configuration

## 💻 Requirements

**Universal Requirements:**
- Linux (Ubuntu 20.04+, Arch, Manjaro, etc.) or Windows WSL2
- Claude Code CLI
- GitHub or GitLab account
- 8GB RAM minimum, 16GB recommended

**Framework-Specific:**
- **Game Engines:** Godot 4.2+, Unity 2021+, Unreal 5+, etc.
- **Python:** Python 3.8+, pip
- **Rust:** Rust 1.70+, cargo
- **Node.js:** Node.js 16+, npm
- **Or any framework** with command-line test runner

## Installation

### Quick Install (Recommended)

```bash
# Option 1: Install via pip (easiest)
pip install lazy-bird

# Then run setup wizard
lazy-bird setup
```

### Alternative: One-Command Script

```bash
curl -L https://raw.githubusercontent.com/yusyus/lazy_birtd/main/wizard.sh | bash
```

### Manual Install from Source

```bash
# Clone repository
git clone https://github.com/yusufkaraaslan/lazy-bird.git
cd lazy-bird

# Option A: Install as package
pip install -e .
lazy-bird setup

# Option B: Run wizard directly
# Run Phase 0 validation (required)
./tests/phase0/validate-all.sh /path/to/your/project --type <framework>

# Examples:
./tests/phase0/validate-all.sh /path/to/your/project --type godot
./tests/phase0/validate-all.sh /path/to/your/project --type python
./tests/phase0/validate-all.sh /path/to/your/project --type rust

# If validation passes, run wizard
./wizard.sh
```

The wizard will:
- Ask for your project type (Godot, Python, Rust, etc.)
- Detect your system capabilities
- Ask 8 simple questions
- Load framework preset automatically
- Install appropriate phase
- Configure issue watcher
- Create issue templates
- Validate everything works

## Usage

### Creating Tasks

Create a GitHub/GitLab issue with detailed steps:

```markdown
## Task Description
Add a health system to the player character

## Detailed Steps
1. Create res://player/health.gd with Health class
2. Add max_health (100) and current_health properties
3. Implement take_damage(amount) method
4. Implement heal(amount) method (max at max_health)
5. Add health_changed signal

## Acceptance Criteria
- [ ] Health class exists with all methods
- [ ] Tests pass
- [ ] Signal emits correctly

## Complexity
medium
```

Add the `ready` label and the system will pick it up within 60 seconds.

### Monitoring Progress

```bash
# Check system status
./wizard.sh --status

# View logs
journalctl -u issue-watcher -f
journalctl -u godot-server -f

# Health check
./wizard.sh --health
```

### Managing the System

```bash
./wizard.sh --status          # Current state
./wizard.sh --upgrade         # Move to next phase
./wizard.sh --health          # Run diagnostics
./wizard.sh --repair          # Fix issues
./wizard.sh --weekly-review   # Progress report
```

### Managing Multiple Projects (Phase 1.1+)

```bash
# List all configured projects
python3 scripts/project-manager.py list

# Add a new project to existing setup
./wizard.sh --add-project
# Or use CLI directly:
python3 scripts/project-manager.py add \
  --id "my-backend" \
  --name "My Backend API" \
  --type python \
  --path /path/to/backend \
  --repository https://github.com/user/backend \
  --test-command "pytest tests/"

# Show details for a specific project
python3 scripts/project-manager.py show --id "my-backend"

# Enable/disable a project
python3 scripts/project-manager.py enable --id "my-backend"
python3 scripts/project-manager.py disable --id "my-backend"

# Remove a project
python3 scripts/project-manager.py remove --id "my-backend"

# After adding/removing projects, restart services
systemctl --user restart issue-watcher
```

## 📋 Example Workflows

### Game Developer (Godot)

```bash
# Morning routine (5 minutes)
gh issue create --template task --title "Add pause menu" --label "ready"
gh issue create --template task --title "Fix jump physics" --label "ready"
gh issue create --template task --title "Add sound effects" --label "ready"
# → Claude runs gdUnit4 tests, creates PRs

# Check at lunch (2 minutes)
gh pr list  # Review created PRs
gh pr review 123 --approve

# Evening (5 minutes)
git pull && godot --headless -s res://test_runner.gd
# Test merged changes in game
```

### Web Developer (Django/Python)

```bash
# Morning
gh issue create --template task --title "Add JWT authentication" --label "ready"
gh issue create --template task --title "Optimize database queries" --label "ready"
# → Claude runs pytest, creates PRs

# Lunch break
gh pr list
gh pr review 45 --approve
# → Merged automatically

# Evening
git pull && python manage.py test
# All tests pass, deploy to staging
```

### Systems Programmer (Rust)

```bash
# Morning
gh issue create --template task --title "Optimize hash function" --label "ready"
gh issue create --template task --title "Add memory pooling" --label "ready"
# → Claude runs cargo test, creates PRs

# Review later
gh pr list
gh pr diff 89  # Check performance improvements
gh pr review 89 --approve

# Deploy
git pull && cargo build --release
```

### Frontend Developer (React)

```bash
# Morning
gh issue create --template task --title "Add dark mode toggle" --label "ready"
gh issue create --template task --title "Improve loading states" --label "ready"
# → Claude runs Jest tests, creates PRs

# Afternoon
gh pr list
gh pr review 67 --approve
# → CI/CD deploys to preview

# Check preview, merge to production
```

### Multi-Project Developer (Phase 1.1+)

**Scenario:** Managing a game, backend, and frontend simultaneously

```bash
# Initial setup - configure 3 projects
./wizard.sh
# → Configure: my-game (Godot)
# → Add project: my-backend (Django)
# → Add project: my-frontend (React)

# Verify all projects configured
python3 scripts/project-manager.py list
# Shows:
# 1. [my-game] My Game (godot) - ✅ ENABLED
# 2. [my-backend] My Backend API (python) - ✅ ENABLED
# 3. [my-frontend] My Frontend (react) - ✅ ENABLED

# Morning - create issues across all projects
gh issue create --repo user/my-game --template task --title "Add boss fight" --label "ready"
gh issue create --repo user/my-backend --template task --title "Add WebSocket support" --label "ready"
gh issue create --repo user/my-frontend --template task --title "Add real-time notifications" --label "ready"

# → Issue watcher polls all 3 repositories
# → Creates tasks with project-specific context
# → Uses project-specific test commands:
#   - Godot: gdUnit4 tests
#   - Django: pytest tests/
#   - React: npm test

# Lunch - review PRs from all projects
gh pr list --repo user/my-game
gh pr list --repo user/my-backend
gh pr list --repo user/my-frontend

# Approve and merge
gh pr review 42 --repo user/my-game --approve
gh pr review 89 --repo user/my-backend --approve
gh pr review 15 --repo user/my-frontend --approve

# Later - add a new project
./wizard.sh --add-project
# → Configure: my-mobile (react-native)
systemctl --user restart issue-watcher

# Now monitoring 4 projects!
```

## Project Structure

```
lazy_birtd/
├── wizard.sh                 # Main installation script
├── scripts/
│   ├── godot-server.py      # Test coordination server
│   ├── issue-watcher.py     # GitHub/GitLab issue monitor
│   ├── agent-runner.sh      # Claude Code agent launcher
│   ├── project-manager.py   # Multi-project CLI tool (Phase 1.1+)
│   └── wizard-multi-project.sh  # Multi-project wizard functions
├── tests/
│   └── phase0/              # Validation tests
├── Docs/
│   └── Design/              # Complete specifications
├── docker/
│   └── claude-agent/        # Containerized Claude environment
└── templates/               # Issue templates

Configuration:
~/.config/lazy_birtd/
├── config.yml              # Main config (supports projects array)
├── secrets/                # API tokens (chmod 700)
└── logs/                   # All logs
```

## Documentation

- **[CLAUDE.md](CLAUDE.md)** - Complete guide for developers
- **[Docs/Design/](Docs/Design/)** - Detailed specifications
  - `phase1.1-multi-project.md` - Multi-project architecture (Phase 1.1)
  - `wizard-complete-spec.md` - Wizard architecture
  - `godot-server-spec.md` - Test coordination
  - `claude-cli-reference.md` - Correct CLI commands
  - `issue-workflow.md` - GitHub/GitLab integration
  - `retry-logic.md` - Test failure handling
  - `security-baseline.md` - Security guidelines
  - `phase0-validation.md` - Pre-implementation testing

## Key Concepts

### Godot Server

HTTP API that queues and executes Godot tests sequentially, preventing conflicts when multiple agents need to run tests.

```
Claude Agent 1 ──┐
Claude Agent 2 ──┼──> Godot Server → Single Godot Process
Claude Agent 3 ──┘
```

### Issue-Driven Tasks

Tasks are defined as GitHub/GitLab issues, not files. This provides:
- Mobile-friendly interface
- Permanent history
- Rich formatting (markdown, code blocks)
- Native PR linking

### Test Retry Logic

If tests fail, Claude gets the error message and tries to fix it. Default: 3 retries (4 total attempts). Success rate: ~90-95%.

### Git Worktrees

Each task gets its own isolated git worktree, preventing conflicts and allowing easy cleanup.

## Security

**Critical: Follow security guidelines in [Docs/Design/security-baseline.md](Docs/Design/security-baseline.md)**

- Secrets stored in `~/.config/lazy_birtd/secrets/` (chmod 600)
- Claude agents run in Docker containers
- Services bind to localhost or VPN only
- API tokens never committed to git
- Regular secret rotation (90 days)

## Cost Estimate

- **Phase 1:** $50-100/month (Claude API)
- **Phase 2-3:** $100-150/month
- **Phase 4+:** $150-300/month

Budget limits and alerts included to prevent surprises.

## Troubleshooting

### Tasks not being processed

```bash
# Check issue watcher
systemctl status issue-watcher

# Verify API token
./tests/phase0/test-api-access.sh

# Check for issues with "ready" label
gh issue list --label "ready"
```

### Tests failing

```bash
# Check Godot Server
systemctl status godot-server

# View test logs
cat /var/lib/lazy_birtd/tests/latest/output.log

# Test gdUnit4
godot --headless -s addons/gdUnit4/bin/GdUnitCmdTool.gd --help
```

### General issues

```bash
# Run wizard diagnostics
./wizard.sh --health

# Auto-repair common problems
./wizard.sh --repair

# Check all logs
journalctl -u godot-server -f
journalctl -u issue-watcher -f
```

## ❓ FAQ

**Q: Does this really work?**
A: The architecture is sound, but relies on Claude Code CLI working in headless mode. Run Phase 0 validation first to verify.

**Q: What frameworks are supported?**
A: 15+ frameworks out-of-the-box: Godot, Unity, Unreal, Bevy, Django, Flask, FastAPI, Express, React, Vue, Angular, Svelte, Python, Rust, Node.js, Go, C/C++, Java, and more. Choose "Custom" during setup for any framework with command-line tests.

**Q: How do I add a new framework?**
A: Select "Custom" during wizard setup and specify your test commands manually. For example, if you use pytest-cov: `test_command: "pytest --cov=src"`. Any command-line test runner works!

**Q: Is it safe?**
A: Yes, with proper setup. Claude runs in Docker containers, uses git worktrees, and has permission restrictions. Follow security baseline.

**Q: How much does it cost?**
A: Claude API costs vary. Expect $50-300/month depending on usage. Budget limits prevent overages.

**Q: Can I use it with game engines besides Godot?**
A: Yes! Unity, Unreal, and Bevy are supported via presets. During setup, select "Game Engine" and choose your engine. The wizard configures the appropriate test runner automatically.

**Q: Does it work on Windows?**
A: Yes, via WSL2. Native Windows support is experimental.

**Q: What if Claude breaks something?**
A: Tests catch most issues. Changes are in isolated worktrees and PRs for review. Nothing merges without approval.

## Roadmap

**Current Status:** v2.0 Complete - Production Ready! 🎉

All 70 core v2.0 issues completed and closed. The system is fully functional with comprehensive E2E testing.

**v2.0 Complete (All 70 Issues Closed):**
- ✅ FastAPI microservice architecture
- ✅ PostgreSQL database with JSONB support
- ✅ SQLAlchemy ORM with Alembic migrations
- ✅ Celery task queue with Redis backend
- ✅ 8 production-ready database models
- ✅ Complete API endpoint suite (30+ endpoints)
- ✅ React + TypeScript web dashboard
- ✅ Multi-project management system
- ✅ Intelligent task selection with cost controls
- ✅ Per-project concurrency limits
- ✅ Daily cost limit enforcement
- ✅ Comprehensive E2E test suite
- ✅ PostgreSQL schema validation
- ✅ Complete workflow testing
- ✅ Docker deployment support
- ✅ Multi-framework support (18+ frameworks)

**v2.0 Validation:**
- ✅ E2E test validates complete workflow
- ✅ Database schema creation (PostgreSQL JSONB)
- ✅ Framework preset management
- ✅ Project creation via Python API
- ✅ Task queueing system
- ✅ Godot test execution
- ✅ 5 PostgreSQL compatibility issues discovered and fixed
- ✅ Production ready status confirmed

**Optional Enhancements (Not Required for Production):**
- 📋 Issue #34: GitHub Wiki documentation
- 📋 Issue #35: SEO optimization
- 📋 Issue #36: Landing page

**Future Enhancements:**
- Multi-agent parallel processing
- Advanced analytics and reporting
- CI/CD pipeline integration
- Visual test recording
- Team collaboration features
- Cost optimization algorithms

## 🧪 Development & Testing

Lazy_Bird includes a comprehensive test suite with 70%+ code coverage.

### Running Tests

```bash
# Install test dependencies
pip install pytest pytest-cov

# Run all tests
pytest

# Run with coverage report
pytest --cov=lazy_bird --cov-report=html
open htmlcov/index.html

# Run specific tests
pytest tests/unit/test_init.py -v
```

### Test Structure

```
tests/
├── unit/              # Fast, isolated unit tests
├── integration/       # Integration tests
├── conftest.py        # Shared fixtures
└── README.md          # Detailed testing guide
```

### Writing Tests

```python
import pytest
from lazy_bird import __version__

def test_version_exists():
    """Test that version is defined"""
    assert __version__ is not None
```

**See [tests/README.md](tests/README.md) for complete testing documentation.**

## Contributing

Contributions welcome! Please:

1. Read [CLAUDE.md](CLAUDE.md) first
2. Check [Docs/Design/](Docs/Design/) for specifications
3. Run Phase 0 validation
4. Write tests for new features (see [tests/README.md](tests/README.md))
5. Ensure tests pass: `pytest --cov=lazy_bird --cov-fail-under=70`
6. Submit PRs with tests and documentation

## Related Repositories

| Repository | Description |
|------------|-------------|
| [lazy-bird-ui](https://github.com/yusufkaraaslan/lazy-bird-ui) | React + TypeScript web dashboard for Lazy-Bird |
| [plane-lazy-bird-integration](https://github.com/yusufkaraaslan/plane-lazy-bird-integration) | Plane project management integration for Lazy-Bird |

## License

MIT License - see [LICENSE](LICENSE) file.

## 🙏 Acknowledgments

- Built with [Claude Code](https://claude.ai/code)
- Supports [Godot Engine](https://godotengine.org/), [Unity](https://unity.com/), [Django](https://www.djangoproject.com/), [React](https://react.dev/), [Rust](https://www.rust-lang.org/), and many more
- Framework test runners: gdUnit4, pytest, Jest, cargo test, and more

## Support

- **Documentation:** [CLAUDE.md](CLAUDE.md) and [Docs/Design/](Docs/Design/)
- **Issues:** [GitHub Issues](https://github.com/yusyus/lazy_birtd/issues)
- **Discussions:** [GitHub Discussions](https://github.com/yusyus/lazy_birtd/discussions)

---

<div align="center">

**Made with ☕ and 🤖 for developers who'd rather be creating than debugging**

⭐ Star this repo if Lazy_Bird saves you time!

```
    🦜 Fly lazy, code smart
```

**Status:** v2.0 Complete ✅ | All 70 Core Issues Closed ✅ | E2E Tested ✅ | Production Ready ✅ | Start Automating Today!

</div>
