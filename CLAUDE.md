# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Lazy_Bird** is a progressive development automation system that enables Claude Code instances to work on software development tasks autonomously while developers are away. The system supports 15+ frameworks (Godot, Unity, Python, Rust, React, Django, and more) and scales from simple task automation to enterprise-level orchestration.

## Quick Reference for Developers

**Most Common Commands:**

```bash
# Testing & Quality
pytest                          # Run all tests
pytest --cov=lazy_bird --cov-report=html  # With coverage
black lazy_bird/ tests/         # Format code
flake8 lazy_bird/ tests/        # Lint code

# Development
lazy-bird setup                 # Setup wizard
lazy-bird server                # Start web backend
cd web && ./start.sh            # Start both frontend & backend
cd web/frontend && npm run dev  # Frontend only

# Services
systemctl --user status issue-watcher
systemctl --user status queue-processor
journalctl --user -u issue-watcher -f

# Project Management
lazy-bird project list          # List projects
lazy-bird project add           # Add project

# Key Files to Know
lazy_bird/cli.py               # CLI entry point
scripts/agent-runner.sh        # Task executor
scripts/issue-watcher.py       # Issue monitor
web/backend/app.py             # Web API
web/frontend/src/App.tsx       # Frontend router
```

**Architecture at a Glance:**
- **Python package** (`lazy_bird/`) - CLI tool and package structure
- **Bash scripts** (`scripts/`) - Core automation logic
- **Web UI** (`web/`) - Flask backend + React frontend
- **Config** (`~/.config/lazy_birtd/`) - Runtime configuration
- **Tests** (`tests/`) - pytest test suite

## Core Philosophy

**Start simple, add complexity only when needed.** Each phase must deliver immediate value.

## CRITICAL: Core Assumptions Validated

⚠️ **The original plan assumed fictional Claude Code CLI flags.** This version uses **actual working commands**.

**Correct CLI Usage:**
- Use `-p "prompt"` flag (not `--task`)
- No `--auto-commit` flag exists (handle git separately)
- Use `--dangerously-skip-permissions` for full automation (containerized only)
- Use `--allowedTools` to restrict capabilities safely

**See:** `Docs/Design/claude-cli-reference.md` for complete command reference.

## Framework Selection

**Lazy_Bird supports 15+ frameworks out-of-the-box.** During wizard setup (Q1), select your project type and framework. The system automatically configures test/build/lint commands via presets.

### Supported Frameworks

**Game Engines:** Godot, Unity, Unreal, Bevy
**Backend:** Django, Flask, FastAPI, Express, Rails
**Frontend:** React, Vue, Angular, Svelte
**Languages:** Python, Rust, Node.js, Go, C/C++, Java
**Custom:** Any framework with CLI test runner

### How to Choose

1. **Use a preset if available** - Automatic configuration, tested presets
2. **Choose "Custom" for unsupported frameworks** - Specify test commands manually
3. **Defaults to Godot** - Backward compatibility with original design

### Framework Configuration

Framework presets live in `config/framework-presets.yml` and include:
- `test_command` - Required, runs tests
- `build_command` - Optional, compiles project
- `lint_command` - Optional, code quality checks
- `format_command` - Optional, code formatting

**Example:** Django preset includes `pytest` for tests, `pylint` for linting, `black` for formatting.

**See:** `Docs/Design/multi-framework-support.md` for complete details.

##Phase 0: Validation (REQUIRED FIRST STEP)

**Before implementing any automation, run Phase 0 validation:**

```bash
# Godot project (default)
./tests/phase0/validate-all.sh /path/to/your/project

# Other frameworks - specify --type
./tests/phase0/validate-all.sh /path/to/your/project --type python
./tests/phase0/validate-all.sh /path/to/your/project --type rust
./tests/phase0/validate-all.sh /path/to/your/project --type nodejs
```

**Phase 0 validates:**
- Claude Code CLI capabilities (headless mode, flags)
- Framework-specific tools (based on --type)
- Git worktree functionality
- GitHub/GitLab API access
- System resources (RAM, disk, CPU)

**See:** `Docs/Design/phase0-validation.md`

**Do NOT proceed to Phase 1 until Phase 0 passes.**

## Architecture

The system follows a 6-phase progressive development model:

### Phase 0: Validation & Prerequisites (1-2 days)
**REQUIRED FIRST**
- Test all assumptions
- Validate Claude Code CLI
- Verify Godot headless mode
- Test git worktrees
- Confirm API access
- **Output:** Go/No-Go decision

### Phase 1: Single Agent Sequential (Week 1)
- Issue watcher monitors GitHub/GitLab for tasks
- Creates git worktree per task
- Runs Claude Code in Docker container
- Submits tests to Godot Server
- Creates PR if tests pass (with retry logic)
- Setup: 2-3 hours via wizard, 4-6GB RAM

### Phase 1.1: Multi-Project Support (✅ IMPLEMENTED)
**Extends Phase 1 to manage multiple projects from a single server.**

- **Single server** monitors 2-20+ projects simultaneously
- **Projects array** configuration with unique IDs per project
- **Project-aware** issue watcher with per-project monitoring
- **Project-specific** commands (test/build/lint) per project
- **Isolated worktrees** named `feature-project-id-issue-number`
- **CLI tool** for project management (`project-manager.py`)
- **Wizard enhancement** with `--add-project` command
- Setup: Add to existing Phase 1 installation, 6-8GB RAM
- Use cases: Solo devs with multiple projects, small teams, polyglot development

**Key Benefits:**
- Manage Godot game + Django backend + Rust CLI from one server
- Add/remove projects without reconfiguration
- Per-project issue tracking and state management
- Full backward compatibility with single-project Phase 1

**See:** `Docs/Design/phase1.1-multi-project.md` for complete specification

### Phase 2: Multi-Agent with Coordination (Week 2)
- 2-3 Claude agents run simultaneously
- Godot Server queues test requests
- Agent scheduler manages resources
- Worktree registry tracks ownership
- Setup: 1 week, 12-16GB RAM (note: original estimate of 8GB was too low)

### Phase 3: Remote Access + Monitoring (Week 3)
- WireGuard VPN for remote access
- Web dashboard (Flask-based)
- Mobile notifications via ntfy.sh
- Setup: 1 weekend, 10-12GB RAM

### Phase 4-6: As Original Plan
- Phase 4: Advanced multi-agent (not needed for solo dev initially)
- Phase 5: CI/CD Pipeline (16GB+ RAM, 24GB recommended)
- Phase 6: Enterprise Orchestration (32GB+ RAM)

## Key Components

### 1. Agent Runner (Core Execution Engine)

**Location:** `scripts/agent-runner.sh`

The agent runner is the heart of task execution. It orchestrates the entire workflow for a single task.

**What it does:**
1. Creates isolated git worktree for the task
2. Runs Claude Code with task-specific prompts (11 steps)
3. Executes tests and validates results
4. Creates draft PR on success
5. Posts detailed implementation comment to GitHub issue
6. Cleans up worktree after completion

**Exit Codes:**
- `0` - Task completed successfully, PR created
- `1` - Task failed (Claude error, test failure, etc.)
- `2` - Invalid arguments or configuration
- `3` - Git/worktree error
- `4` - Cleanup failed (worktree may need manual removal)

**Usage:**
```bash
# Run manually (usually called by queue-processor)
./scripts/agent-runner.sh ~/.config/lazy_birtd/queue/task-PROJECT-ISSUE.json

# View logs
tail -f ~/.config/lazy_birtd/logs/task-PROJECT-ISSUE.log
```

**11-Step Execution Process:**
1. Parse task details from queue file
2. Create git worktree and branch
3. Generate implementation plan
4. Implement changes (Claude Code)
5. Run tests
6. Fix any test failures (with retries)
7. Commit changes with detailed message
8. Push to GitHub
9. Wait for GitHub API sync (polling)
10. Create draft PR
11. Post implementation comment to issue

### 1.1 Web Dashboard (Phase 0 - Implemented)

**Location:** `web/` directory

Modern React + TypeScript web interface for monitoring and managing Lazy_Bird.

**Architecture:**
```
web/
├── backend/              # Flask REST API
│   ├── app.py           # Main Flask application
│   ├── api/             # API endpoints
│   │   ├── projects.py  # Project CRUD
│   │   ├── system.py    # System status & control
│   │   └── queue.py     # Task queue management
│   └── services/        # Business logic
│       ├── config_service.py    # Config.yml reader/writer
│       ├── systemd_service.py   # Service control
│       └── queue_service.py     # Queue reader
│
└── frontend/            # React SPA
    ├── src/
    │   ├── App.tsx      # Main app with React Router
    │   ├── pages/       # Route-based pages
    │   │   ├── DashboardPage.tsx    # System overview
    │   │   ├── ProjectsPage.tsx     # Project list
    │   │   ├── ProjectFormPage.tsx  # Add/edit project
    │   │   ├── ServicesPage.tsx     # Service management
    │   │   ├── QueuePage.tsx        # Task queue viewer
    │   │   └── SettingsPage.tsx     # Configuration
    │   ├── components/  # Reusable components
    │   ├── hooks/       # Custom React hooks
    │   │   ├── useProjects.ts
    │   │   └── useSystem.ts
    │   ├── lib/         # API client & utilities
    │   └── types/       # TypeScript interfaces
    └── package.json
```

**Key Backend API Endpoints:**
```
GET    /api/projects              # List all projects
POST   /api/projects              # Create project
GET    /api/projects/:id          # Get project details
PUT    /api/projects/:id          # Update project
DELETE /api/projects/:id          # Delete project

GET    /api/system/status         # System health (CPU, RAM, services)
POST   /api/system/services/:name/start
POST   /api/system/services/:name/stop
POST   /api/system/services/:name/restart

GET    /api/queue                 # List queued tasks
GET    /api/queue/:id             # Get task details
DELETE /api/queue/:id             # Cancel task
```

**Frontend Tech Stack:**
- **React 18+** with TypeScript for type safety
- **Vite** for fast builds and hot module replacement
- **TanStack Query** (React Query) for server state management
- **React Router** for client-side routing
- **Shadcn/ui** components built on Radix UI
- **Tailwind CSS** for styling

**Development Workflow:**
1. Backend changes: Edit `web/backend/api/*.py` or `web/backend/services/*.py`
2. Frontend changes: Edit `web/frontend/src/**/*.tsx`
3. Both servers auto-reload on file changes
4. API changes require backend restart
5. Frontend changes hot-reload instantly

### 2. Setup Wizard (Primary Installation Method)

The wizard is the **recommended way** to install and manage the system.

```bash
# One-command installation
curl -L https://raw.githubusercontent.com/yusyus/lazy_birtd/main/wizard.sh | bash

# Or manual
git clone https://github.com/yusyus/lazy_birtd.git
cd lazy_birtd
./wizard.sh
```

**Wizard Capabilities:**
- Detects system capabilities (RAM, Godot, Claude Code, Docker)
- Runs Phase 0 validation automatically
- Asks 8 configuration questions
- Installs appropriate phase
- Sets up Godot Server
- Installs gdUnit4 test framework
- Configures issue watcher
- Creates issue templates
- Sets up secrets securely
- Validates everything works

**Management Commands:**
```bash
./wizard.sh --status           # Check system status
./wizard.sh --upgrade          # Upgrade to next phase
./wizard.sh --health           # Run health checks
./wizard.sh --weekly-review    # Progress report
./wizard.sh --repair           # Fix broken components
./wizard.sh --add <feature>    # Add specific feature
./wizard.sh --export           # Backup configuration
```

**See:** `Docs/Design/wizard-complete-spec.md`

### 2. Godot Server (Test Coordination)

**Problem Solved:** Multiple Claude agents cannot run Godot tests simultaneously without conflicts.

**Solution:** HTTP API server that queues and executes tests sequentially.

**Architecture:**
```
Claude Agent 1 ──┐
Claude Agent 2 ──┼──> Godot Server (HTTP API) ──> Single Godot Process
Claude Agent 3 ──┘         (Queue)                    (Sequential Execution)
```

**API Endpoints:**
- `POST /test/submit` - Submit test job
- `GET /test/status/{job_id}` - Check status
- `GET /test/results/{job_id}` - Get results
- `GET /health` - Health check
- `GET /queue` - View queue

**Deployment:**
```bash
# systemd service (recommended)
sudo systemctl start godot-server

# Or Docker
docker-compose up godot-server
```

**See:** `Docs/Design/godot-server-spec.md`

### 3. GitHub/GitLab Issues Workflow

**Task Source:** Issues (not tasks.md files)

**Daily Workflow:**
1. **Morning:** Create GitHub/GitLab issues with detailed steps, add `ready` label
2. **Work Hours:** System processes tasks, runs tests, creates PRs
3. **Lunch Break:** Review PRs on GitHub/GitLab, approve or request changes
4. **Evening:** Merge approved PRs, test in main branch

**Issue Structure:**
```markdown
## Task Description
[What needs to be done]

## Detailed Steps
1. [Specific step with files and code]
2. [Another step]
3. [Final step]

## Acceptance Criteria
- [ ] Criterion 1
- [ ] Tests pass

## Complexity
[simple|medium|complex]
```

**Issue Watcher Service:**
- Polls API every 60 seconds for issues with `ready` label
- Parses issue body
- Creates task in queue
- Removes `ready` label, adds `processing` label

**See:** `Docs/Design/issue-workflow.md`

### 4. Test Retry Logic

**Default:** 3 retries max (4 total attempts)

**Retry Strategy:**
- Parse test errors
- Pass error context to Claude
- Let Claude fix issues
- Retry tests
- Exponential backoff between retries

**Cost Control:**
- Max cost per task: $5 (configurable)
- Daily budget limit: $50 (configurable)
- Alert at 80% of budget

**See:** `Docs/Design/retry-logic.md`

### 5. Task Complexity System

Tasks are categorized by complexity (affects resource allocation):

| Complexity | RAM | Max Parallel | Examples |
|------------|-----|--------------|----------|
| Simple | 2GB | 3 agents | UI, dialogue, config changes |
| Medium | 3GB | 2 agents | Gameplay features, AI, refactoring |
| Complex | 5GB | 1 agent | Physics systems, rendering, optimization |

## Correct Claude Code Usage

### ❌ WRONG (Fictional Flags):
```bash
# These commands DO NOT EXIST:
claude-code --task "Add feature" --auto-commit
claude --project ./godot-project --task "Fix bug"
```

### ✅ CORRECT (Actual Commands):

**Basic Headless:**
```bash
claude -p "Add health system to player with 100 max health, take_damage and heal methods"
```

**With Tool Restrictions (Safe):**
```bash
claude -p "Fix jump physics in player.gd" --allowedTools "Read,Write,Edit,Bash(git:*)"
```

**Full Automation (Containerized):**
```bash
# ONLY in Docker containers, NEVER on host
docker run --rm -v /workspace:/workspace lazy-birtd/claude-agent \
  claude -p "Implement feature" --dangerously-skip-permissions
```

**Output Formats:**
```bash
# JSON output for parsing
claude -p "task" --output-format json

# Streaming JSON for real-time monitoring
claude -p "task" --output-format stream-json
```

**See:** `Docs/Design/claude-cli-reference.md` for complete reference.

## Development Guidelines

### When Working on Core Scripts

**Bash Scripts:**
- Include `set -euo pipefail` for safety
- Use resource limits: `systemd-run -p MemoryLimit=2G`
- Always include error handling and logging
- Scripts must be idempotent (safe to run multiple times)
- Never use git operations on main branch (use worktrees)

**Python Scripts:**
- Use type hints
- Include docstrings
- Handle exceptions gracefully
- Log security-relevant events
- Load secrets from `~/.config/lazy_birtd/secrets/`

### When Working on Godot Integration

**Test Framework:** gdUnit4 (not GUT as originally planned)

**Test Execution:**
```bash
godot --headless \\
  -s res://addons/gdUnit4/bin/GdUnitCmdTool.gd \\
  --test-suite res://test/test_player.gd
```

**Test Runner Location:** Managed by Godot Server (not res://test_runner.gd)

**Always:**
- Use `--headless` flag for automation
- Parse JUnit XML output
- Handle test timeouts (default: 300s)
- Capture full test output for debugging

### When Working on the Wizard

**Wizard is non-negotiable** - it's the primary way users will install the system.

**Requirements:**
- Non-interactive mode with config file
- Validates all prerequisites (Phase 0)
- Idempotent installations
- Rollback on failure
- Clear error messages
- Dry-run mode available

**Wizard Flow:**
1. System detection
2. Phase 0 validation (automatic)
3. User questions (8 questions)
4. Installation plan preview
5. Automated installation
6. Post-install validation
7. First task demo (optional)

## Security Baseline

**CRITICAL: Follow security guidelines in `Docs/Design/security-baseline.md`**

### Secret Management

**Storage Location:** `~/.config/lazy_birtd/secrets/` (chmod 700)

**Secrets:**
- `api_token` - GitHub/GitLab token (chmod 600)
- `claude_key` - Claude API key (chmod 600)
- `vpn_key` - WireGuard private key (chmod 600)

**Never:**
- ❌ Commit secrets to git
- ❌ Log secrets
- ❌ Pass secrets as command-line arguments
- ❌ Store secrets in plain config files

**Always:**
- ✅ Load from secure files or environment
- ✅ Use file permissions (600/700)
- ✅ Rotate every 90 days
- ✅ Encrypt at rest (future enhancement)

### Service Authentication

**Godot Server:**
- Bind to localhost only (`127.0.0.1:5000`)
- Or use API key authentication
- Or restrict via firewall to VPN network only

**Dashboard:**
- HTTP Basic Auth minimum
- OAuth2 recommended (GitHub/GitLab)
- HTTPS with valid certificate (Phase 3+)

### Docker Security

- Run containers as non-root user
- Use official base images only
- Pin image versions (no `:latest`)
- Scan images with `trivy`
- Apply resource limits
- Use read-only filesystems where possible

**See:** `Docs/Design/security-baseline.md`

## Commands Reference

### Python Package CLI (Recommended)

After installing via pip (`pip install lazy-bird`), use the `lazy-bird` command:

```bash
# Setup and management
lazy-bird setup              # Run setup wizard
lazy-bird status             # Show system status (same as ./wizard.sh --status)

# Web dashboard
lazy-bird server             # Start web backend on http://localhost:5000
lazy-bird server --host 0.0.0.0 --port 8080  # Custom host/port

# Services
lazy-bird watch              # Run issue watcher (foreground)
lazy-bird godot              # Run Godot test server (foreground)
lazy-bird project list       # List all projects
lazy-bird project add        # Add new project

# Version
lazy-bird --version          # Show version
```

### Wizard Commands (Alternative - Direct Script)

```bash
./wizard.sh                    # Install/configure system
./wizard.sh --status           # System health and status
./wizard.sh --upgrade          # Upgrade to next phase
./wizard.sh --health           # Run diagnostics
./wizard.sh --repair           # Fix common issues
./wizard.sh --weekly-review    # Progress report
./wizard.sh --add-project      # Add new project (Phase 1.1+)
```

### Core Services (systemd user services - preferred)

```bash
# Issue Watcher - detects new GitHub issues
systemctl --user start issue-watcher
systemctl --user status issue-watcher
journalctl --user -u issue-watcher -f

# Queue Processor - executes tasks from queue
systemctl --user start queue-processor
systemctl --user status queue-processor
journalctl --user -u queue-processor -f

# Enable services to start on boot (requires user lingering)
systemctl --user enable issue-watcher queue-processor
sudo loginctl enable-linger $USER
```

### Web Dashboard Development

**Quick Start (One Command):**
```bash
cd web
./start.sh                   # Starts both backend (5000) and frontend (5173)
./stop.sh                    # Stops both servers
```

**Manual Development:**
```bash
# Backend (Terminal 1)
cd web/backend
source venv/bin/activate     # Activate virtual environment
python3 app.py               # Start Flask server on :5000
python3 app.py --debug       # Dev mode with auto-reload

# Frontend (Terminal 2)
cd web/frontend
npm install                  # First time only
npm run dev                  # Start Vite dev server on :5173
npm run build                # Production build
npm run preview              # Preview production build
npm run lint                 # Lint TypeScript/React code
```

**Dashboard URLs:**
- Frontend: http://localhost:5173 (dev)
- Backend API: http://localhost:5000/api
- API Docs: http://localhost:5000/

**Dashboard Features:**
- Real-time queue monitoring
- Task execution logs viewer
- PR creation status
- Multi-project overview (CRUD operations)
- System health metrics (CPU, RAM, disk)
- Service control (start/stop/restart systemd services)
- Settings (GitHub token configuration)

### Testing Commands

**Python/Backend Tests:**
```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=lazy_bird --cov-report=term
pytest --cov=lazy_bird --cov-report=html  # Generate HTML report

# Run specific test types
pytest -m unit               # Unit tests only
pytest -m integration        # Integration tests only
pytest -m "not slow"         # Skip slow tests

# Run specific test files
pytest tests/unit/test_init.py
pytest tests/integration/ -v

# Coverage threshold check
pytest --cov=lazy_bird --cov-fail-under=10
```

**Code Quality Checks:**
```bash
# Format code (auto-fix)
black lazy_bird/ tests/

# Check formatting (no changes)
black --check --diff lazy_bird/ tests/

# Lint code
flake8 lazy_bird/ tests/

# Type checking
mypy lazy_bird/ --ignore-missing-imports

# Security scan
bandit -r lazy_bird/
```

### Manual Testing

```bash
# Test Claude Code (Phase 0)
./tests/phase0/validate-claude-all.sh

# Test Godot Server
curl http://localhost:5000/health

# Test issue creation
gh issue create --template task --title "Test" --label "ready"

# Test web backend API
curl http://localhost:5000/api/projects
curl http://localhost:5000/api/system/status
curl http://localhost:5000/api/queue
```

### Project Management (Phase 1.1+)

```bash
# Using Python package CLI
lazy-bird project list                    # List all projects
lazy-bird project add                     # Interactive add
lazy-bird project show my-project         # Show project details
lazy-bird project enable my-project       # Enable project
lazy-bird project disable my-project      # Disable project
lazy-bird project remove my-project       # Remove project

# Using direct script
python3 scripts/project-manager.py list
python3 scripts/project-manager.py add \
  --id "my-backend" \
  --name "My Backend API" \
  --type python \
  --path /path/to/backend \
  --repository https://github.com/user/backend \
  --test-command "pytest tests/"
```

## Target Environment

### Supported Operating Systems

**Linux** (Recommended):
- Ubuntu 20.04+, Debian 11+, Fedora 35+, Arch-based (Manjaro, EndeavourOS)
- Full feature support for all phases
- Native Docker and systemd integration

**Windows** (10/11 via WSL2):
- WSL2 required for full functionality
- Docker Desktop for Windows
- Phase 1-3 fully supported, Phase 4+ needs WSL2

### System Requirements

**Minimum (Phase 1):**
- 8GB RAM
- 4 CPU cores
- 20GB free disk space
- Godot 4.2+
- Python 3.8+
- Git 2.30+

**Recommended (Phase 2-3):**
- 16GB RAM
- 8 CPU cores
- 50GB free disk space
- Docker installed
- systemd available

**Optimal (Phase 4-6):**
- 32GB+ RAM
- 16+ CPU cores
- 100GB+ free disk space
- Dedicated server (24/7 uptime)

### Resource Estimates (Corrected)

| Phase | Original Estimate | Actual Requirement | Notes |
|-------|-------------------|---------------------|-------|
| Phase 1 | 4-6GB | 6-8GB | Claude + Godot + overhead |
| Phase 2 | 6-8GB | 12-16GB | Multi-agent needs more |
| Phase 3 | 8-10GB | 12-14GB | VPN/Dashboard overhead |
| Phase 4 | 12-16GB | 18-20GB | 3 agents + coordination |
| Phase 5 | 16GB | 24-32GB | GitLab CE alone needs 8GB |
| Phase 6 | 32GB+ | 32GB+ | Correct |

## Directory Structure

### Runtime Directories

**User Configuration** (`~/.config/lazy_birtd/`):
```
~/.config/lazy_birtd/
├── config.yml              # Main configuration
├── secrets/                # API tokens (chmod 700)
│   ├── api_token          # GitHub/GitLab token (chmod 600)
│   └── github_token       # Alternative token location
├── queue/                  # Task queue files
│   └── task-*.json        # Individual task files (project-id-issue-number)
├── logs/                   # System and task logs
│   ├── issue-watcher.log  # Issue detection service
│   ├── queue-processor.log# Task processing service
│   └── task-*.log         # Per-task execution logs
└── data/                   # Runtime data and metrics
```

**Temporary Worktrees** (`/tmp/`):
```
/tmp/
└── lazy-bird-agent-*/      # Isolated git worktrees
    └── feature-*           # Per-task branch (auto-cleaned after PR merge)
```

## Configuration Files

### Primary Config
- `~/.config/lazy_birtd/config.yml` - Main configuration
- `~/.config/lazy_birtd/secrets/` - API tokens, keys (chmod 700)
- `~/.config/lazy_birtd/data/` - Task queue, metrics

### Project-Specific
- `.github/ISSUE_TEMPLATE/task.yml` - GitHub issue template
- `.gitlab/issue_templates/task.md` - GitLab issue template
- `/var/lib/lazy_birtd/queue/` - Task queue files (alternative location)
- `/var/lib/lazy_birtd/tests/` - Test artifacts (alternative location)
- `/tmp/lazy-bird-agent-*/` - Git worktrees (ephemeral, task-specific)

### System Services
- `~/.config/systemd/user/issue-watcher.service` - User service (preferred)
- `~/.config/systemd/user/queue-processor.service` - User service (preferred)
- `/etc/systemd/system/godot-server.service` - System service (alternative)
- `/etc/systemd/system/issue-watcher.service` - System service (alternative)

## Testing Strategy

### Phase 0: Pre-Implementation
- Validate all assumptions
- Test Claude Code CLI
- Verify Godot headless mode
- Confirm git worktrees work
- Check API access

### Python/Lazy_Bird Testing (Current)

**Test Framework:** pytest with coverage tracking

**Running Tests:**
```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=lazy_bird --cov-report=term

# Run specific test markers
pytest -m unit          # Unit tests only
pytest -m integration   # Integration tests only
pytest -m "not slow"    # Skip slow tests
```

**Coverage Requirements:**
- **Minimum:** 10% (enforced in CI)
- **Target:** 70%+ for production-ready code
- **New code:** Aim for 80%+ coverage

**CI/CD Automation:**
- GitHub Actions runs tests on every push/PR
- Tests across Python 3.8, 3.9, 3.10, 3.11, 3.12
- Coverage uploaded to Codecov
- Code quality checks (black, flake8, mypy, bandit)

**See:** `CONTRIBUTING.md` for detailed testing guide

### Phase 1+: Per-Task (Godot Projects)
- Each task generates tests via Claude
- Tests run through Godot Server
- Retry up to 3 times on failure
- Only create PR if tests pass
- Log all test results

### Test Framework: gdUnit4 (Godot Projects)

**Installation:**
```bash
cd $PROJECT_PATH
git clone https://github.com/MikeSchulze/gdUnit4.git addons/gdUnit4
```

**Run Tests:**
```bash
godot --headless -s addons/gdUnit4/bin/GdUnitCmdTool.gd --test-suite all
```

**Test File Example:**
```gdscript
extends GdUnitTestSuite

func test_player_health():
    var player = Player.new()
    assert_that(player.health).is_equal(100)

func test_take_damage():
    var player = Player.new()
    player.take_damage(30)
    assert_that(player.health).is_equal(70)
```

## Git Workflow

### Branch Naming
- Feature branches: `feature-<issue-number>`
- Example: `feature-42` for GitHub issue #42

### Worktree Management
- Location: `/tmp/agents/agent-<issue-number>`
- Created per task
- Cleaned up after PR merge
- Registry tracks active worktrees

### Commit Messages
```
Task #42: Add player health system

Automated by Lazy_Birtd agent
Issue: https://github.com/user/repo/issues/42
```

### PR Creation
- Automatic after passing tests
- Includes test results
- Links to original issue
- Marked with `automated` label

## Documentation Structure

### Primary Documentation

**Root Directory:**
- `README.md` - Main project documentation
- `CLAUDE.md` - This file - Developer/Claude Code guidance
- `CONTRIBUTING.md` - **Comprehensive contributor guide with testing & CI/CD**
- `CODE_OF_CONDUCT.md` - Community guidelines
- `CHANGELOG.md` - Version history

**CI/CD Documentation:**
- `.github/CI-CD-SETUP.md` - Complete CI/CD setup guide
- `.github/workflows/test.yml` - Automated testing workflow
- `.github/workflows/lint.yml` - Code quality checks
- `.github/workflows/publish.yml` - PyPI publishing automation
- `.codecov.yml` - Coverage configuration
- `pytest.ini` - Pytest configuration
- `pyproject.toml` - Python package config & dev tools

### Design Documents (`Docs/Design/`)

**New Architecture Specs (IMPORTANT):**
- `wizard-complete-spec.md` - Full wizard specification
- `godot-server-spec.md` - Test coordination architecture
- `claude-cli-reference.md` - **Correct Claude commands**
- `issue-workflow.md` - GitHub/GitLab integration
- `retry-logic.md` - Test failure handling
- `security-baseline.md` - **Critical security guidelines**
- `phase0-validation.md` - **Required first step**

**Original Specs (Reference):**
- `game-dev-automation-plan-v2.md` - 6-phase plan (needs updates)
- `wizard-overview.md` - Original wizard concept (expanded)
- `implementation-roadmap.md` - Quick start (needs Phase 0)

## Quick Start

### For New Users

```bash
# 1. Clone repository
git clone https://github.com/yusyus/lazy_birtd.git
cd lazy_birtd

# 2. Run Phase 0 validation
./tests/phase0/validate-all.sh /path/to/your/godot-project

# 3. If validation passes, run wizard
./wizard.sh

# 4. Answer 8 questions

# 5. Wait 15 minutes for installation

# 6. Create first issue
gh issue create --template task --title "Add health system" --label "ready"

# 7. Watch it work
./wizard.sh --status
```

### For Developers Contributing to Lazy_Bird

```bash
# 1. Read contributor guide first (has testing & CI/CD info)
cat CONTRIBUTING.md

# 2. Read developer guide
cat CLAUDE.md

# 3. Review architecture
ls -la Docs/Design/

# 4. Understand correct Claude commands
cat Docs/Design/claude-cli-reference.md

# 5. Check security requirements
cat Docs/Design/security-baseline.md

# 6. Set up development environment
pip install -e ".[dev]"

# 7. Run tests to verify setup
pytest

# 8. Make your changes

# 9. Run pre-push checks (from CONTRIBUTING.md)
pytest --cov=lazy_bird --cov-fail-under=10
black --check --diff lazy_bird/ tests/
flake8 lazy_bird/ tests/

# 10. Submit PR
```

## Troubleshooting

### Wizard Won't Start
```bash
# Check dependencies
./wizard.sh --check-deps

# View logs
cat ~/.config/lazy_birtd/logs/wizard.log
```

### Godot Server Not Responding
```bash
# Check status
systemctl status godot-server

# View logs
journalctl -u godot-server -n 50

# Restart
sudo systemctl restart godot-server

# Or use wizard
./wizard.sh --repair
```

### Tasks Not Being Picked Up
```bash
# Check issue watcher (user service)
systemctl --user status issue-watcher
journalctl --user -u issue-watcher -n 50

# Check queue processor (user service)
systemctl --user status queue-processor
journalctl --user -u queue-processor -n 50

# Verify services are enabled
systemctl --user list-unit-files | grep lazy

# Check user lingering (required for services to run when not logged in)
loginctl show-user $USER | grep Linger
# If Linger=no, enable it:
sudo loginctl enable-linger $USER

# Verify API token
./tests/phase0/test-api-access.sh
cat ~/.config/lazy_birtd/secrets/github_token  # Should exist and be valid

# Check issue labels on GitHub
gh issue list --label "ready"

# Manually trigger queue processing (testing)
python3 scripts/queue-processor.py  # Run once manually
```

### Services Won't Start After Reboot
```bash
# This happens when user lingering is not enabled
# Enable it so services start without login:
sudo loginctl enable-linger $USER

# Verify lingering is enabled
loginctl show-user $USER | grep "Linger=yes"

# Restart services
systemctl --user daemon-reload
systemctl --user restart issue-watcher queue-processor
```

### Worktree Cleanup Failures
```bash
# List stale worktrees
git worktree list

# Remove stale worktree manually
git worktree remove /tmp/lazy-bird-agent-PROJECT-ISSUE --force

# Clean up all completed task worktrees
for dir in /tmp/lazy-bird-agent-*; do
    [ -d "$dir" ] && git worktree remove "$dir" --force
done
```

### Tests Failing
```bash
# Check test logs
cat /var/lib/lazy_birtd/tests/latest/output.log

# Verify Godot works
godot --headless --version

# Test gdUnit4
godot --headless -s addons/gdUnit4/bin/GdUnitCmdTool.gd --help
```

## Metrics & Monitoring

### Dashboard (Phase 3+)
- http://localhost:5000 (via VPN)
- Shows active agents, queue depth, recent PRs
- Real-time test status

### Logs
```bash
# System logs
journalctl -u godot-server -f
journalctl -u issue-watcher -f

# Application logs
tail -f ~/.config/lazy_birtd/logs/agent-*.log

# Security logs
tail -f /var/log/lazy_birtd/security.log
```

### Metrics (Prometheus format)
```
# Available on :9090/metrics (if monitoring enabled)
godot_server_queue_depth
godot_server_jobs_total
godot_server_average_duration_seconds
lazy_birtd_tasks_completed_total
lazy_birtd_tasks_failed_total
lazy_birtd_api_costs_usd
```

## Cost Tracking

**Expected Costs (based on usage patterns):**
- Phase 1: $50-100/month (Claude API)
- Phase 2-3: $100-150/month
- Phase 4+: $150-300/month (multiple agents)

**Cost Control:**
- Daily budget limits (default: $50)
- Per-task limits (default: $5)
- Retry limits (default: 3)
- Alerts at 80% budget

**Monitor Costs:**
```bash
./wizard.sh --cost-report
```

## License

MIT License - See LICENSE file

## Support & Contributing

- **Contributing Guide:** See `CONTRIBUTING.md` for complete guide (testing, CI/CD, pre-push checklist)
- **Documentation:** All specs in `Docs/Design/`
- **Issues:** GitHub Issues for bug reports
- **Discussions:** GitHub Discussions for questions
- **Pull Requests:** Follow `CONTRIBUTING.md` pre-push checklist before submitting

## Important Reminders

1. **Run Phase 0 first** - Don't skip validation
2. **Use wizard for installation** - It handles complexity
3. **Follow security baseline** - Protect secrets
4. **Use correct Claude commands** - Check claude-cli-reference.md
5. **Monitor costs** - Set budget limits
6. **Start simple** - Phase 1 first, then iterate

## Python Package Structure

Lazy_Bird is distributed as a Python package on PyPI:

```
lazy_bird/                    # Main Python package
├── __init__.py              # Package metadata, exports
├── cli.py                   # CLI entry point (lazy-bird command)
├── scripts/                 # Symlink to ../scripts/
└── web/                     # Symlink to ../web/

scripts/                     # Core automation scripts
├── agent-runner.sh          # Task execution engine
├── issue-watcher.py         # GitHub/GitLab issue monitor
├── queue-processor.py       # Task queue processor
├── project-manager.py       # Multi-project CLI tool
├── godot-server.py          # Test coordination server
└── wizard-multi-project.sh  # Multi-project wizard

web/                         # Web dashboard
├── backend/
│   ├── app.py              # Flask API server
│   ├── api/                # REST endpoints
│   └── services/           # Business logic
└── frontend/
    └── src/                # React + TypeScript SPA

tests/                       # Test suite
├── conftest.py             # pytest fixtures
├── unit/                   # Fast, isolated tests
└── integration/            # Integration tests

config/                      # Configuration templates
├── config.example.yml      # Example config
└── framework-presets.yml   # Framework definitions
```

**Installation Methods:**
1. **PyPI (Recommended):** `pip install lazy-bird`
2. **From source:** `pip install -e .` (development mode)
3. **Wizard script:** `curl -L <url> | bash` (legacy)

**Entry Points:**
- `lazy-bird` command → `lazy_bird.cli:main`
- Scripts accessible via package symlinks
- Web dashboard via `lazy-bird server`

---

**Last Updated:** 2025-12-29
**Version:** 2.5 (Enhanced Developer Documentation)
**Status:** Phase 1.1 implemented and tested - Production ready!
**CI/CD Status:** ✅ Automated testing, code quality checks, and coverage tracking operational
**Project Status:** Fully initialized - Multi-project support active with comprehensive test suite

**Recent Enhancements (v2.5):**
- Added Quick Reference section for developers
- Documented Python package CLI commands (`lazy-bird` command)
- Enhanced Web Dashboard architecture documentation
- Added comprehensive testing commands section
- Documented web development workflow (frontend + backend)
- Added Python package structure overview
- Improved code quality check commands
- Enhanced web API endpoint documentation
