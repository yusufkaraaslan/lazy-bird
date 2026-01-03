# Phase 1.1: Multi-Project Support

**Applies to:** lazy-bird core engine (Phase 1.1+)
**Related repos:** lazy-bird (core) - NOT lazy-bird-ui or plane-lazy-bird-integration
**Status:** ✅ **IMPLEMENTED** and Tested
**Version:** 2.1 (incorporated into v2.0)
**Date:** November 7, 2025
**Complexity:** Medium
**Estimated Implementation:** 2-3 days
**Actual Implementation:** 2 days

---

## Overview

Phase 1.1 extends Phase 1 (single-agent sequential) to support **managing multiple projects with a single Lazy_Bird instance**. Instead of configuring one project, users can configure 2, 5, or 20+ projects, all monitored by the same issue-watcher service and processed by the same agent infrastructure.

### Key Benefit

**Before Phase 1.1:**
```
Server 1 → Project A (Godot game)
Server 2 → Project B (Django backend)
Server 3 → Project C (Rust CLI)
```

**After Phase 1.1:**
```
Single Server → Project A (Godot game)
             → Project B (Django backend)
             → Project C (Rust CLI)
             → Project D, E, F, ... (unlimited)
```

### Use Cases

1. **Multi-Project Solo Developer:** Maintains 3-5 personal projects simultaneously
2. **Small Team:** Team manages frontend, backend, and mobile app from one server
3. **Polyglot Developer:** Works across multiple languages/frameworks
4. **Consultants:** Manages client projects from centralized automation server

---

## Architecture Changes

### Phase 1 (Single Project)

```
┌─────────────────┐
│ Issue Watcher   │──> Single Repository (GitHub/GitLab)
└─────────────────┘
         │
         v
┌─────────────────┐
│ Task Queue      │──> Single project path
└─────────────────┘
         │
         v
┌─────────────────┐
│ Agent Runner    │──> Single worktree
└─────────────────┘
```

### Phase 1.1 (Multi-Project)

```
┌─────────────────────────────────────────────────┐
│ Issue Watcher (Orchestrator)                    │
└─────────────────────────────────────────────────┘
    │
    ├──> ProjectWatcher[project-A] ──> Repository A (Godot)
    ├──> ProjectWatcher[project-B] ──> Repository B (Django)
    └──> ProjectWatcher[project-C] ──> Repository C (Rust)
                 │
                 v
┌─────────────────────────────────────────────────┐
│ Task Queue (project-aware)                      │
│  - task-project-A-issue-42.json                 │
│  - task-project-B-issue-18.json                 │
│  - task-project-C-issue-7.json                  │
└─────────────────────────────────────────────────┘
                 │
                 v
┌─────────────────────────────────────────────────┐
│ Agent Runner (project-aware)                    │
│  - Reads project context from task              │
│  - Creates isolated worktree per project        │
│  - Uses project-specific commands                │
└─────────────────────────────────────────────────┘
```

---

## Configuration Schema

### New Format (Phase 1.1+)

**File:** `~/.config/lazy_birtd/config.yml`

```yaml
# Multi-Project Configuration
projects:
  - id: "my-game"                    # Unique identifier (required)
    name: "My Platformer Game"       # Display name (required)
    type: godot                      # Framework type (required)
    path: /home/user/projects/game  # Absolute path (required)
    repository: https://github.com/user/game  # Git URL (required)
    git_platform: github             # github or gitlab (required)
    test_command: "godot --headless -s addons/gdUnit4/bin/GdUnitCmdTool.gd --test-suite all"  # Required
    build_command: null              # Optional
    lint_command: null               # Optional
    format_command: null             # Optional
    enabled: true                    # true or false (required)

  - id: "my-backend"
    name: "API Backend"
    type: django
    path: /home/user/projects/backend
    repository: https://github.com/user/backend
    git_platform: github
    test_command: "pytest tests/ -v"
    build_command: null
    lint_command: "flake8 ."
    format_command: "black ."
    enabled: true

# System configuration (shared across all projects)
poll_interval_seconds: 60
phase: 1
max_concurrent_agents: 1
memory_limit_gb: 8

retry:
  max_attempts: 3
  max_cost_per_task_usd: 5.0
  daily_budget_limit_usd: 50.0
```

### Required Fields Per Project

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `id` | string | Unique alphanumeric ID | `my-game`, `api-backend` |
| `name` | string | Human-readable name | `My Platformer Game` |
| `type` | string | Framework/language | `godot`, `django`, `rust` |
| `path` | string | Absolute project path | `/home/user/projects/game` |
| `repository` | string | Git repository URL | `https://github.com/user/game` |
| `git_platform` | string | `github` or `gitlab` | `github` |
| `test_command` | string | Command to run tests | `pytest tests/` |
| `build_command` | string/null | Command to build (optional) | `cargo build` |
| `enabled` | boolean | Monitor this project? | `true` or `false` |

### Backward Compatibility

Phase 1.1 maintains **full backward compatibility** with single-project configs:

```yaml
# Legacy format (still works)
project:
  type: godot
  name: "My Game"
  path: /home/user/my-game

test_command: "godot --headless ..."
repository: https://github.com/user/game
git_platform: github
```

The system automatically detects and converts legacy configs to the new format.

---

## Component Changes

### 1. Issue Watcher (`scripts/issue-watcher.py`)

**Before:** Single `IssueWatcher` class monitoring one repository.

**After:**
- `ProjectWatcher` class - Monitors single project
- `IssueWatcher` orchestrator - Manages multiple `ProjectWatcher` instances

**Key Changes:**
```python
class ProjectWatcher:
    """Monitors a single project's GitHub/GitLab for ready-to-process issues"""
    def __init__(self, project_config: Dict, global_config: Dict):
        self.project_id = project_config['id']
        self.project_name = project_config['name']
        self.project_type = project_config['type']
        # ... load project-specific settings

class IssueWatcher:
    """Orchestrates monitoring of multiple projects (Phase 1.1)"""
    def __init__(self, config_path: Path):
        self.project_watchers = self.load_projects()  # List of ProjectWatcher

    def run(self):
        # Poll each project in sequence
        for project_watcher in self.project_watchers:
            issues = project_watcher.fetch_ready_issues()
            # Process issues with project context
```

**Token Hierarchy:**

Projects can use different API tokens:
1. Try `~/.config/lazy_birtd/secrets/{project_id}_token`
2. Try `~/.config/lazy_birtd/secrets/{platform}_token`
3. Fall back to `~/.config/lazy_birtd/secrets/api_token`

**State Management:**

Processed issues are tracked per-project:
```json
[
  "project-A:42",
  "project-B:18",
  "project-C:7"
]
```

Format: `{project_id}:{issue_number}`

### 2. Agent Runner (`scripts/agent-runner.sh`)

**Before:** Read project path from config.

**After:** Read project context from task JSON.

**Key Changes:**

```bash
# Parse task JSON (includes project context)
PROJECT_ID=$(jq -r '.project_id' "$task_file")
PROJECT_NAME=$(jq -r '.project_name' "$task_file")
PROJECT_TYPE=$(jq -r '.project_type' "$task_file")
PROJECT_PATH=$(jq -r '.project_path' "$task_file")

# Use task-specific commands (not config)
TEST_CMD=$(jq -r '.test_command' "$task_file")
BUILD_CMD=$(jq -r '.build_command' "$task_file")
LINT_CMD=$(jq -r '.lint_command' "$task_file")
```

**Project-Aware Logging:**
```
[INFO] [project-A] Creating worktree: /tmp/lazy-bird-agent-project-A-42
[INFO] [project-A] Running tests...
[SUCCESS] [project-A] Tests passed
```

**Isolated Worktrees:**
```
# Before: feature-42
# After:  feature-project-A-42

BRANCH_NAME="feature-$PROJECT_ID-$TASK_ID"
WORKTREE_PATH="/tmp/lazy-bird-agent-$PROJECT_ID-$TASK_ID"
```

**Enhanced Commits:**
```
[project-A] Task #42: Add health system

Automated implementation by Lazy_Bird agent

Project: My Platformer Game (godot)
Task URL: https://github.com/user/game/issues/42
Complexity: medium
```

### 3. Project Manager CLI (`scripts/project-manager.py`)

**New tool** for managing projects without editing YAML:

```bash
# List all projects
python3 scripts/project-manager.py list

# Show project details
python3 scripts/project-manager.py show my-game

# Add a new project
python3 scripts/project-manager.py add \
  --id my-app \
  --name "My Application" \
  --type python \
  --path /path/to/project \
  --repository https://github.com/user/app \
  --git-platform github \
  --test-command "pytest tests/"

# Edit a field
python3 scripts/project-manager.py edit my-app --field test_command --value "pytest -v"

# Disable a project (temporarily)
python3 scripts/project-manager.py disable my-app

# Re-enable
python3 scripts/project-manager.py enable my-app

# Remove a project
python3 scripts/project-manager.py remove my-app
```

**Features:**
- YAML parsing and generation
- Field validation
- Unique ID checking
- Path existence validation
- Automatic backups (`.yml.backup`)

### 4. Wizard (`wizard.sh` + `scripts/wizard-multi-project.sh`)

**Before:** Configure single project during setup.

**After:** Configure multiple projects with `--add-project` command.

**New Command:**
```bash
# Add a project to existing setup
./wizard.sh --add-project
```

**Functions:**
- `configure_single_project()` - Interactive project configuration
- `display_project_summary()` - Show all configured projects
- `generate_multiproject_config()` - Generate Phase 1.1 YAML
- `add_project_to_config()` - Add to existing setup

**Validation:**
- Project ID uniqueness
- Path existence
- Git repository detection
- Framework preset loading

---

## Task Queue Format

### Task JSON (Phase 1.1)

When the issue-watcher queues a task, it includes full project context:

```json
{
  "issue_id": 42,
  "title": "Add health system to player",
  "body": "## Task Description\n...",
  "steps": [...],
  "acceptance_criteria": [...],
  "complexity": "medium",
  "url": "https://github.com/user/game/issues/42",
  "queued_at": "2025-11-07T00:00:00Z",
  "platform": "github",
  "repository": "https://github.com/user/game",

  // NEW: Project context (Phase 1.1)
  "project_id": "my-game",
  "project_name": "My Platformer Game",
  "project_type": "godot",
  "project_path": "/home/user/projects/game",
  "test_command": "godot --headless -s addons/gdUnit4/bin/GdUnitCmdTool.gd --test-suite all",
  "build_command": null,
  "lint_command": null,
  "format_command": null
}
```

**File Naming:**
```
# Before: task-42.json
# After:  task-my-game-42.json

Format: task-{project_id}-{issue_number}.json
```

---

## Usage Examples

### Example 1: Solo Developer with 3 Projects

**Scenario:** Developer maintains a game, a website, and a CLI tool.

**Configuration:**
```yaml
projects:
  - id: "platformer"
    name: "My Platformer Game"
    type: godot
    path: /home/dev/platformer
    repository: https://github.com/dev/platformer
    git_platform: github
    test_command: "godot --headless -s addons/gdUnit4/bin/GdUnitCmdTool.gd --test-suite all"
    enabled: true

  - id: "portfolio"
    name: "Portfolio Website"
    type: react
    path: /home/dev/portfolio
    repository: https://github.com/dev/portfolio
    git_platform: github
    test_command: "npm test -- --watchAll=false"
    build_command: "npm run build"
    lint_command: "npm run lint"
    enabled: true

  - id: "devtools"
    name: "Developer Tools CLI"
    type: rust
    path: /home/dev/devtools
    repository: https://github.com/dev/devtools
    git_platform: github
    test_command: "cargo test --all"
    build_command: "cargo build --release"
    lint_command: "cargo clippy"
    enabled: true
```

**Workflow:**
1. Create issues in any of the 3 repositories with `ready` label
2. Single issue-watcher monitors all 3 repositories every 60 seconds
3. Tasks queued with project context: `task-platformer-5.json`, `task-portfolio-12.json`, etc.
4. Agent runner processes tasks sequentially, switching between projects as needed

### Example 2: Team with Frontend + Backend

**Scenario:** Team maintains a React frontend and Django backend.

**Configuration:**
```yaml
projects:
  - id: "frontend"
    name: "Web Frontend"
    type: react
    path: /var/www/frontend
    repository: https://github.com/team/frontend
    git_platform: github
    test_command: "npm test"
    build_command: "npm run build"
    enabled: true

  - id: "backend"
    name: "API Backend"
    type: django
    path: /var/www/backend
    repository: https://github.com/team/backend
    git_platform: github
    test_command: "python manage.py test"
    lint_command: "flake8 ."
    enabled: true
```

**Benefits:**
- Centralized automation for entire stack
- Consistent issue-to-PR workflow across frontend and backend
- Single server for both projects (cost savings)

### Example 3: Temporarily Disable a Project

**Scenario:** One project is in maintenance mode, no active development.

```bash
# Disable monitoring for "legacy-app"
python3 scripts/project-manager.py disable legacy-app

# View updated status
python3 scripts/project-manager.py list
# Output: [legacy-app] Status: ❌ DISABLED

# Issue-watcher will skip this project until re-enabled
```

---

## Migration Guide

### From Single-Project (Phase 1) to Multi-Project (Phase 1.1)

**Option 1: Automatic (using project-manager.py)**

The project-manager CLI automatically handles legacy configs:

```bash
# Add a second project
python3 scripts/project-manager.py add \
  --id project-2 \
  --name "My Second Project" \
  --type python \
  --path /path/to/project2 \
  --repository https://github.com/user/project2 \
  --git-platform github \
  --test-command "pytest tests/"
```

The CLI will:
1. Read existing config (legacy or new format)
2. Convert to `projects` array if needed
3. Add new project
4. Save in Phase 1.1 format

**Option 2: Manual**

1. **Backup existing config:**
   ```bash
   cp ~/.config/lazy_birtd/config.yml ~/.config/lazy_birtd/config.yml.backup
   ```

2. **Convert to new format:**

   **Before:**
   ```yaml
   project:
     type: godot
     name: "My Game"
     path: /home/user/my-game

   test_command: "godot --headless ..."
   repository: https://github.com/user/game
   git_platform: github
   ```

   **After:**
   ```yaml
   projects:
     - id: "my-game"
       name: "My Game"
       type: godot
       path: /home/user/my-game
       repository: https://github.com/user/game
       git_platform: github
       test_command: "godot --headless ..."
       build_command: null
       lint_command: null
       format_command: null
       enabled: true
   ```

3. **Restart services:**
   ```bash
   systemctl --user restart issue-watcher
   ```

4. **Verify:**
   ```bash
   python3 scripts/project-manager.py list
   ```

---

## Testing

### Unit Tests

**Test project configuration loading:**
```bash
# Create test config
cat > /tmp/test-config.yml <<EOF
projects:
  - id: "test1"
    name: "Test Project 1"
    type: python
    path: /tmp/test1
    repository: https://github.com/test/test1
    git_platform: github
    test_command: "pytest"
    enabled: true
  - id: "test2"
    name: "Test Project 2"
    type: rust
    path: /tmp/test2
    repository: https://github.com/test/test2
    git_platform: github
    test_command: "cargo test"
    enabled: false
EOF

# Test issue-watcher initialization
timeout 3 python3 scripts/issue-watcher.py --config /tmp/test-config.yml

# Expected output:
# Loading 2 project(s) from 'projects' array
# [test1] Test Project 1 (python)
# [test2] Test Project 2 (rust) - Skipping (disabled)
# Monitoring 1 project(s)
```

### Integration Tests

1. **Create test repositories**
2. **Configure 2-3 projects**
3. **Create issues with `ready` label in each repo**
4. **Verify issue-watcher picks up all issues**
5. **Verify tasks include project context**
6. **Verify agent-runner processes each correctly**

### End-to-End Test

See `/tmp/phase1.1-test-report.md` for comprehensive test results.

---

## Performance Considerations

### Sequential Polling

Projects are polled **sequentially** (not in parallel):

```python
for project_watcher in self.project_watchers:
    issues = project_watcher.fetch_ready_issues()  # One at a time
```

**Why sequential?**
- Simple implementation (Phase 1 is single-agent)
- Predictable resource usage
- Easier debugging
- API rate limit friendly

**Impact:**
- 3 projects × 1 second API call = 3 seconds per poll cycle
- 10 projects × 1 second = 10 seconds
- 60 second poll interval is sufficient for most use cases

**Future:** Phase 2+ may add parallel polling for large deployments.

### Memory Usage

**Per-Project Overhead:** ~5-10 MB (ProjectWatcher instance)

**Scaling:**
- 10 projects: ~100 MB overhead
- 50 projects: ~500 MB overhead
- 100 projects: ~1 GB overhead

**Recommended:**
- Phase 1.1: 1-20 projects per server
- Phase 2+: 20-50 projects (with parallel agents)

---

## Troubleshooting

### Issue: Projects not detected

**Symptom:**
```
ERROR - No projects configured!
```

**Solution:**
1. Verify config has `projects` array:
   ```bash
   grep "^projects:" ~/.config/lazy_birtd/config.yml
   ```

2. Check YAML syntax:
   ```bash
   python3 -c "import yaml; yaml.safe_load(open('~/.config/lazy_birtd/config.yml'))"
   ```

3. Use project-manager to list:
   ```bash
   python3 scripts/project-manager.py list
   ```

### Issue: Wrong project executed

**Symptom:** Agent runner uses wrong project path.

**Cause:** Task JSON missing project context.

**Solution:**
1. Check task file:
   ```bash
   cat ~/.config/lazy_birtd/queue/task-*.json | jq '.project_id'
   ```

2. Verify issue-watcher adds project context:
   ```bash
   journalctl --user -u issue-watcher -n 50 | grep "project_id"
   ```

3. Restart issue-watcher:
   ```bash
   systemctl --user restart issue-watcher
   ```

### Issue: Duplicate project IDs

**Symptom:**
```
ERROR - Project ID 'my-app' already exists
```

**Solution:**
```bash
# List all projects
python3 scripts/project-manager.py list

# Remove duplicate
python3 scripts/project-manager.py remove my-app

# Re-add with unique ID
python3 scripts/project-manager.py add --id my-app-2 ...
```

---

## Future Enhancements (Post Phase 1.1)

### Phase 2: Parallel Project Monitoring

```python
# Future: Parallel polling with asyncio
import asyncio

async def poll_all_projects(self):
    tasks = [
        asyncio.create_task(project.fetch_ready_issues())
        for project in self.project_watchers
    ]
    results = await asyncio.gather(*tasks)
```

### Phase 3: Per-Project Dashboards

- Web UI showing per-project statistics
- Project-specific cost tracking
- Per-project success rates

### Phase 4: Project Groups

```yaml
project_groups:
  - name: "Frontend Stack"
    projects: [web-frontend, mobile-app, admin-panel]
  - name: "Backend Services"
    projects: [api-server, worker-queue, cache-service]
```

### Phase 5: Cross-Project Dependencies

```yaml
projects:
  - id: "frontend"
    depends_on: [backend, shared-lib]  # Wait for these PRs first
```

---

## Resources

### Files Modified/Created

**Created:**
- `scripts/project-manager.py` (452 lines)
- `scripts/wizard-multi-project.sh` (411 lines)

**Modified:**
- `scripts/issue-watcher.py` (581 lines, major refactor)
- `scripts/agent-runner.sh` (674 lines, enhanced)
- `wizard.sh` (+8 lines, integration)
- `config/config.example.yml` (285 lines, rewritten)

### Related Documentation

- `Docs/Design/phase0-validation.md` - Prerequisites
- `Docs/Design/phase1.1-multi-project.md` - This document
- `Docs/Design/multi-framework-support.md` - Framework presets
- `Docs/Design/issue-workflow.md` - Issue processing
- `Docs/Design/wizard-complete-spec.md` - Setup wizard

---

## Summary

Phase 1.1 successfully extends Lazy_Bird to manage **unlimited projects** from a single server instance. The implementation:

✅ **Maintains simplicity** - Sequential processing (Phase 1 foundation)
✅ **Adds flexibility** - Support for heterogeneous projects (Godot + Python + Rust)
✅ **Provides tooling** - CLI for project management
✅ **Ensures isolation** - Project-aware tasks, worktrees, and logs
✅ **Preserves compatibility** - Legacy configs still work

**Recommendation:** Phase 1.1 is production-ready for teams managing 2-20 projects per server.

---

**Document Version:** 1.0
**Last Updated:** November 7, 2025
**Author:** Lazy_Bird Development Team
