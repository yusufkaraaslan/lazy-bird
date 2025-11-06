# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Lazy_Bird** is a progressive development automation system that enables Claude Code instances to work on software development tasks autonomously while developers are away. The system supports 15+ frameworks (Godot, Unity, Python, Rust, React, Django, and more) and scales from simple task automation to enterprise-level orchestration.

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

### 1. Setup Wizard (Primary Installation Method)

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

## Commands (Current Implementation Status)

### Wizard Commands (Primary Interface)
```bash
./wizard.sh                    # Install/configure system
./wizard.sh --status           # System health and status
./wizard.sh --upgrade          # Upgrade to next phase
./wizard.sh --health           # Run diagnostics
./wizard.sh --repair           # Fix common issues
./wizard.sh --weekly-review    # Progress report
```

### Godot Server (systemd service)
```bash
sudo systemctl start godot-server
sudo systemctl status godot-server
journalctl -u godot-server -f
```

### Issue Watcher (systemd service)
```bash
sudo systemctl start issue-watcher
sudo systemctl status issue-watcher
journalctl -u issue-watcher -f
```

### Manual Testing
```bash
# Test Claude Code (Phase 0)
./tests/phase0/validate-claude-all.sh

# Test Godot Server
curl http://localhost:5000/health

# Test issue creation
gh issue create --template task --title "Test" --label "ready"
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

## Configuration Files

### Primary Config
- `~/.config/lazy_birtd/config.yml` - Main configuration
- `~/.config/lazy_birtd/secrets/` - API tokens, keys (chmod 700)
- `~/.config/lazy_birtd/data/` - Task queue, metrics

### Project-Specific
- `.github/ISSUE_TEMPLATE/task.yml` - GitHub issue template
- `.gitlab/issue_templates/task.md` - GitLab issue template
- `/var/lib/lazy_birtd/queue/` - Task queue files
- `/var/lib/lazy_birtd/tests/` - Test artifacts
- `/tmp/agents/` - Git worktrees (ephemeral)

### System Services
- `/etc/systemd/system/godot-server.service`
- `/etc/systemd/system/issue-watcher.service`
- `/etc/lazy_birtd/godot-server.conf`

## Testing Strategy

### Phase 0: Pre-Implementation
- Validate all assumptions
- Test Claude Code CLI
- Verify Godot headless mode
- Confirm git worktrees work
- Check API access

### Phase 1+: Per-Task
- Each task generates tests via Claude
- Tests run through Godot Server
- Retry up to 3 times on failure
- Only create PR if tests pass
- Log all test results

### Test Framework: gdUnit4

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

All design documents in `Docs/Design/`:

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

### For Developers Contributing to Lazy_Birtd

```bash
# Read this first
cat CLAUDE.md

# Review architecture
ls -la Docs/Design/

# Understand correct Claude commands
cat Docs/Design/claude-cli-reference.md

# Check security requirements
cat Docs/Design/security-baseline.md

# Run Phase 0 tests
./tests/phase0/validate-all.sh ./test-project

# Make changes
# Test changes
# Submit PR
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
# Check issue watcher
systemctl status issue-watcher

# Verify API token
./tests/phase0/test-api-access.sh

# Check issue labels
gh issue list --label "ready"
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

- **Documentation:** All specs in `Docs/Design/`
- **Issues:** GitHub Issues for bug reports
- **Discussions:** GitHub Discussions for questions
- **Contributing:** Read CLAUDE.md, run Phase 0, submit PRs

## Important Reminders

1. **Run Phase 0 first** - Don't skip validation
2. **Use wizard for installation** - It handles complexity
3. **Follow security baseline** - Protect secrets
4. **Use correct Claude commands** - Check claude-cli-reference.md
5. **Monitor costs** - Set budget limits
6. **Start simple** - Phase 1 first, then iterate

---

**Last Updated:** 2025-11-06
**Version:** 2.1 (Phase 1 Complete)
**Status:** Phase 1 implemented and tested - Production ready!
**Project Status:** Fully initialized - All core components present
