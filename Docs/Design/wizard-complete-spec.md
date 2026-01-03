# Setup Wizard - Complete Specification

**Applies to:** lazy-bird core engine (all versions)
**Related repos:** lazy-bird (core) - NOT lazy-bird-ui or plane-lazy-bird-integration
**Status:** ✅ **IMPLEMENTED** - wizard.sh functional

## Overview

The Setup Wizard is the primary installation and management interface for the Lazy_Birtd game development automation system. It transforms a complex multi-phase setup into a simple, interactive process that takes 15-30 minutes for initial installation.

## Design Philosophy

1. **Zero-knowledge required** - Anyone can install without reading documentation
2. **Safe by default** - Validates before installing, backs up before changing
3. **Progressive disclosure** - Start simple, add complexity only when needed
4. **Self-healing** - Detects and fixes common problems automatically
5. **Transparent** - Shows what it's doing and why

## Core Components

### 1. System Detection Engine

**Purpose:** Automatically detect system capabilities and requirements

**Detection Points:**
```bash
# Hardware
- RAM available (total and free)
- CPU cores
- Disk space (/, /tmp, project directory)
- GPU availability (for Godot editor)

# Software
- OS type and version (Ubuntu/Debian/Arch/Manjaro/WSL2)
- Docker/Podman installation
- systemd availability
- Godot installation (version, location)
- Claude Code CLI (installed, version, working)
- Git (version, config)
- Python 3 (version 3.8+)

# Project
- Godot project location
- Project version (Godot 3 vs 4)
- Existing test framework (GUT, gdUnit4, WAT, none)
- Git repository (local, remote URL)
- Existing CI/CD (detect .gitlab-ci.yml, .github/workflows)

# Network
- GitHub/GitLab accessibility
- API token validity
- ntfy.sh reachability
- Docker registry access
```

**Detection Script: `scripts/wizard/detect.sh`**
```bash
#!/bin/bash
# Returns JSON with all detected values
{
  "hardware": {
    "ram_total_gb": 16,
    "ram_free_gb": 12,
    "cpu_cores": 8,
    "disk_free_gb": 120
  },
  "software": {
    "os": "manjaro",
    "os_version": "23.1",
    "docker": true,
    "docker_version": "24.0.7",
    "systemd": true,
    "godot": "/usr/bin/godot",
    "godot_version": "4.2.1",
    "claude_code": true,
    "claude_version": "1.2.0",
    "git_version": "2.43.0",
    "python_version": "3.11.6"
  },
  "project": {
    "found": true,
    "path": "/home/user/my-game",
    "godot_version": "4.2",
    "test_framework": "none",
    "git_repo": true,
    "git_remote": "https://github.com/user/my-game.git"
  }
}
```

### 2. Claude Code Validator

**Purpose:** Verify Claude Code CLI works in headless mode

**Tests:**
```bash
# Test 1: Basic headless prompt
claude -p "Print hello world"

# Test 2: With dangerous flag (in container)
docker run --rm claude-test \
  claude -p "List files" --dangerously-skip-permissions

# Test 3: Output format
claude -p "Test" --output-format json

# Test 4: Tool restrictions
claude -p "Test" --allowedTools "Read"
```

**Validation Results:**
- ✅ All tests pass → Full automation possible
- ⚠️ Some fail → Limited automation, warn user
- ❌ All fail → Cannot proceed, show error

### 3. Interactive Questionnaire

**8 Core Questions:**

**Q1: Project Location**
```
Where is your Godot project?

[Browse...] or enter path: _______________________

Detected: /home/user/my-game
Use this path? [Y/n]
```

**Q2: Git Platform**
```
Which platform do you use for version control?

1. GitHub (public repository)
2. GitHub (private repository)
3. GitLab (public)
4. GitLab (private)
5. Self-hosted GitLab
6. Self-hosted Gitea
7. Other

Choice [1-7]: _
```

**Q3: Repository Details**
```
Repository URL: https://github.com/user/my-game.git

API Token (for creating PRs and issues):
[Create token: https://github.com/settings/tokens]

Token: ______________________________________
(will be stored securely in ~/.config/lazy_birtd/secrets)
```

**Q4: Testing Framework**
```
Test framework for your Godot project?

Current: none detected

1. Install gdUnit4 (recommended for Godot 4.x)
2. Install GUT (Godot 3.x and 4.x compatible)
3. I have my own test setup
4. Skip testing (not recommended)

Choice [1-4]: _
```

**Q5: Notifications**
```
Get notified when tasks complete?

1. ntfy.sh (push notifications to phone)
2. Discord webhook
3. Telegram bot
4. Email (via SMTP)
5. No notifications

Choice [1-5]: _

[If ntfy.sh selected]
Topic name: my-game-dev
Your notification URL: https://ntfy.sh/my-game-dev

Test notification? [Y/n]
```

**Q6: Resource Allocation**
```
How much RAM can Claude agents use?

Available: 16GB total, 12GB free
Recommended: 10GB (leaves 6GB for system + Godot)

Maximum RAM for agents [10GB]: _
```

**Q7: Starting Phase**
```
Which phase would you like to install?

Based on your system (16GB RAM, solo dev):

Phase 1: Single Agent, Sequential ⭐ RECOMMENDED
  • One task at a time
  • Safest option
  • 15 minute setup
  • ~4GB RAM usage

Phase 2: Multi-Agent (2-3 parallel)
  • Multiple tasks simultaneously
  • Requires coordination
  • 30 minute setup
  • ~8-10GB RAM usage

Phase 3: Remote Access + Monitoring
  • Includes Phase 2 + VPN + Dashboard
  • 1 hour setup
  • ~10-12GB RAM usage

Choose phase [1-3]: _
```

**Q8: Godot Server Mode**
```
How should the Godot test server run?

1. systemd service (native, recommended)
2. Docker container (isolated)
3. Manual (I'll start it myself)

Choice [1-3]: _
```

### 4. Installation Engine

**Pre-Installation Checklist:**
```bash
# Validate all prerequisites
✓ Godot project exists and is valid
✓ Git repository configured
✓ API token works (test API call)
✓ Sufficient disk space (20GB+ free)
✓ Required ports available (5000, 6080, etc)
✓ Claude Code CLI validated
✓ Test framework installable
✓ Godot can run headless

# Create backup
✓ Backup Godot project to /tmp/lazy_birtd_backup_<timestamp>
✓ Backup git config
✓ Export current settings

# Dry run (optional)
--dry-run flag shows what would be installed without doing it
```

**Installation Steps (Phase 1):**

```bash
# Step 1: Directory Structure
mkdir -p ~/.config/lazy_birtd/{secrets,logs,data}
mkdir -p /var/lib/lazy_birtd/{worktrees,tests,artifacts}

# Step 2: Install Test Framework
cd $PROJECT_PATH
# If gdUnit4 selected:
git clone https://github.com/MikeSchulze/gdUnit4.git addons/gdUnit4
# Configure in project.godot

# Step 3: Deploy Godot Server
cp scripts/godot-server.py /usr/local/bin/godot-server
# If systemd:
cp systemd/godot-server.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable godot-server
systemctl start godot-server

# Step 4: Issue Watcher
cp scripts/issue-watcher.py /usr/local/bin/issue-watcher
cp systemd/issue-watcher.service /etc/systemd/system/
systemctl enable issue-watcher
systemctl start issue-watcher

# Step 5: Docker Environment
docker build -t lazy-birtd/claude-agent:latest docker/claude-agent/
docker pull anthropics/claude-code:latest  # If available

# Step 6: Issue Templates
# GitHub:
mkdir -p $PROJECT_PATH/.github/ISSUE_TEMPLATE
cp templates/github-task.yml $PROJECT_PATH/.github/ISSUE_TEMPLATE/task.yml
# GitLab:
mkdir -p $PROJECT_PATH/.gitlab/issue_templates
cp templates/gitlab-task.md $PROJECT_PATH/.gitlab/issue_templates/task.md

# Step 7: Configuration Files
cat > ~/.config/lazy_birtd/config.yml <<EOF
version: 1.0
project_path: $PROJECT_PATH
git_platform: github
repository: $REPO_URL
phase: 1
agent_max_ram_gb: 10
godot_server_mode: systemd
test_framework: gdUnit4
notifications:
  enabled: true
  method: ntfy
  topic: my-game-dev
EOF

# Step 8: Secrets Storage
cat > ~/.config/lazy_birtd/secrets/api_token <<EOF
$API_TOKEN
EOF
chmod 600 ~/.config/lazy_birtd/secrets/api_token

# Step 9: Helper Scripts
ln -s /usr/local/bin/godot-server ~/.local/bin/godot-server
ln -s /usr/local/bin/issue-watcher ~/.local/bin/issue-watcher

# Step 10: Validation
./wizard.sh --validate
```

**Installation Progress Display:**
```
🧙 Installing Lazy_Birtd - Phase 1

[████████████████████░░░░] 85% - Starting Godot server...

✓ Created directory structure
✓ Installed gdUnit4 test framework
✓ Deployed Godot server (systemd)
✓ Configured issue watcher
✓ Built Docker images
✓ Created issue templates
✓ Saved configuration
✓ Secured API tokens
✓ Installing validation scripts...

Estimated time remaining: 1 minute
```

### 5. Post-Install Validation

**Validation Tests:**
```bash
#!/bin/bash
# scripts/wizard/validate.sh

echo "Running post-install validation..."

# Test 1: Godot Server
echo -n "Godot server health... "
curl -f http://localhost:5000/health || exit 1
echo "✓"

# Test 2: Issue Watcher
echo -n "Issue watcher running... "
systemctl is-active issue-watcher || exit 1
echo "✓"

# Test 3: Docker Images
echo -n "Claude agent image... "
docker images | grep lazy-birtd/claude-agent || exit 1
echo "✓"

# Test 4: Test Framework
echo -n "gdUnit4 installed... "
test -d "$PROJECT_PATH/addons/gdUnit4" || exit 1
echo "✓"

# Test 5: Issue Template
echo -n "Issue template deployed... "
test -f "$PROJECT_PATH/.github/ISSUE_TEMPLATE/task.yml" || exit 1
echo "✓"

# Test 6: Configuration
echo -n "Configuration valid... "
test -f ~/.config/lazy_birtd/config.yml || exit 1
echo "✓"

# Test 7: Secrets secured
echo -n "API token secured... "
test -f ~/.config/lazy_birtd/secrets/api_token || exit 1
stat -c "%a" ~/.config/lazy_birtd/secrets/api_token | grep 600 || exit 1
echo "✓"

# Test 8: End-to-end workflow (optional)
if [ "$FULL_VALIDATION" = "true" ]; then
    echo "Running end-to-end test..."
    ./scripts/test-workflow.sh
fi

echo ""
echo "✅ All validation tests passed!"
```

### 6. First Run Experience

**After successful installation:**
```
┌─────────────────────────────────────────────┐
│  ✅ Installation Complete!                  │
│                                             │
│  🎮 Godot Server: http://localhost:5000    │
│  📋 Issue Watcher: Active                   │
│  🤖 Agent Slots: 1 available                │
│  🔔 Notifications: ntfy.sh/my-game-dev      │
│                                             │
│  🎯 Next Steps:                             │
│                                             │
│  1. Create your first task:                 │
│     gh issue create --template task \\       │
│       --title "Add player health system" \\  │
│       --label "ready"                       │
│                                             │
│  2. Watch progress:                         │
│     ./wizard.sh --status                    │
│                                             │
│  3. Check Godot server:                     │
│     curl http://localhost:5000/health       │
│                                             │
│  📚 Documentation: ./Docs/README.md         │
│  🆘 Help: ./wizard.sh --help                │
│  💬 Issues: github.com/yusyus/lazy_birtd    │
│                                             │
│  Want to create a demo task now? [Y/n]     │
└─────────────────────────────────────────────┘
```

**Demo Task Creation:**
```bash
# If user says Yes:
echo "Creating demo task..."

gh issue create \
  --title "[DEMO] Add comment to main scene" \
  --body "$(cat <<'EOF'
## Task Description
Add a comment at the top of the main scene script explaining what it does.

## Detailed Steps
1. Open the main scene script (res://main.gd or similar)
2. Add a comment block at the top:
   ```gdscript
   ## Main Scene
   ## This is the entry point of the game
   ```
3. Save the file

## Acceptance Criteria
- Comment exists at top of file
- Follows GDScript comment conventions
- File still runs without errors

## Complexity
simple

## Estimated Time
5 minutes
EOF
)" \
  --label "ready,demo"

echo "✅ Demo task created!"
echo "Watch it get processed: ./wizard.sh --status"
echo "View PR when done: gh pr list"
```

## Management Commands

### Status Command

```bash
./wizard.sh --status
```

**Output:**
```
🧙 Lazy_Birtd Status Report
═══════════════════════════════════════

📊 System Health
  ✓ Godot Server: Running (uptime: 2d 3h)
  ✓ Issue Watcher: Active (last check: 30s ago)
  ✓ Docker: Running (2 containers)

🤖 Agent Status
  Active: 0 / 1
  Queue: 3 tasks pending

  Recent Activity:
    ✅ #42: Add health UI - PR #89 (2 hours ago)
    ✅ #41: Fix jump physics - PR #88 (5 hours ago)
    ⏳ #43: Enemy spawn - In progress (15 min)

📋 Task Queue
  1. #44: Add pause menu (ready)
  2. #45: Implement save system (ready)
  3. #46: Sound effects (ready)

🔔 Recent Notifications
  13:45 - Task #42 complete, tests passing
  10:30 - Task #41 complete, PR created
  09:15 - Started processing task #43

💾 Resource Usage
  RAM: 6.2 GB / 10 GB (62%)
  Disk: 15 GB / 20 GB (75%)
  Worktrees: 1 active, 15 archived

📈 Statistics (Last 7 days)
  Tasks completed: 23
  PRs created: 23
  PRs merged: 19
  Success rate: 95.7%
  Avg time per task: 42 minutes

Next: ./wizard.sh --weekly-review
```

### Upgrade Command

```bash
./wizard.sh --upgrade
```

**Flow:**
```
🧙 Checking for available upgrades...

Current Setup:
  Phase: 1 (Single Agent)
  Installed: 15 days ago
  Usage: 23 tasks completed

Analysis:
  ✓ System stable for 2+ weeks
  ✓ High task volume (1-2 per day)
  ✓ 10GB RAM headroom available
  ⚠ Single-agent bottleneck detected

Recommendation: Upgrade to Phase 2

═══════════════════════════════════════

Phase 2: Multi-Agent System

What you'll get:
  ✓ 2-3 tasks processed simultaneously
  ✓ Intelligent task scheduling
  ✓ 2-3x faster development
  ✓ Godot server queue management

Requirements:
  • Additional 4-6GB RAM (~10GB total)
  • Docker Compose for coordination
  • 30 minutes installation time

New Components:
  ├─ Agent Scheduler (Python)
  ├─ Worktree Registry
  ├─ Godot Server Queue System
  └─ Enhanced Monitoring

Your system: ✅ Compatible

Proceed with upgrade? [Y/n]: _
```

### Health Check Command

```bash
./wizard.sh --health
```

**Comprehensive Health Check:**
```
🧙 Running health diagnostics...

🔍 Service Status
  ✓ Godot Server: Healthy
    - Port 5000: Responding
    - API /health: 200 OK
    - Queue depth: 0
    - Last test: 2 minutes ago

  ✓ Issue Watcher: Healthy
    - Service: Active (running)
    - Last poll: 28 seconds ago
    - API rate limit: 4850/5000 remaining
    - Pending issues: 3

  ✓ Docker: Healthy
    - Daemon: Running
    - Images: 3 present
    - Containers: 0 running, 0 stopped
    - Disk usage: 2.4 GB

🔍 Configuration
  ✓ Config file: Valid YAML
  ✓ API token: Valid (tested)
  ✓ Project path: Exists and readable
  ✓ Git remote: Accessible
  ✓ Test framework: gdUnit4 present

🔍 Resource Health
  ✓ RAM: 6.2 / 16 GB used (healthy)
  ✓ Disk: 105 / 250 GB used (healthy)
  ⚠ Worktrees: 18 total (recommend cleanup)
  ✓ Temp space: 45 GB free

🔍 Recent Errors
  ⚠ 2 test failures in last 24h:
    - Task #41: Retry 2/3 succeeded
    - Task #40: Retry 3/3 succeeded
  ✓ No fatal errors

🔍 Performance Metrics
  ✓ Avg task time: 42 min (target: < 60 min)
  ✓ Test success rate: 95.7% (target: > 90%)
  ✓ Godot server response: 45ms (healthy)

Recommendations:
  • Run: ./wizard.sh --cleanup-worktrees
  • Consider upgrading to Phase 2 for better throughput

Overall Health: ✅ HEALTHY
```

### Weekly Review Command

```bash
./wizard.sh --weekly-review
```

**Output:**
```
🧙 Weekly Review - Week 3

📊 Activity Summary
  Tasks automated: 23 (+5 from last week)
  PRs created: 23
  PRs merged: 19 (82.6% merge rate)
  Time saved: ~27 hours ⭐
  API cost: $87 (within budget)

📈 Trends
  Tasks per day: 3.3 (↑ 15%)
  Success rate: 95.7% (↑ 2%)
  Avg task time: 42 min (↓ 8 min)

  Busiest day: Wednesday (7 tasks)
  Task types:
    - UI/UX: 35%
    - Gameplay: 30%
    - Bug fixes: 20%
    - Refactoring: 15%

🎯 Goals Progress
  ✅ Automate 20+ tasks/week (achieved: 23)
  ✅ Maintain 90%+ success rate (achieved: 95.7%)
  ⏳ Reduce avg time to 35 min (current: 42 min)

💡 Insights
  • Most failures on "complex" tasks
  • Best results with detailed task descriptions
  • Peak processing: 10am-2pm
  • RAM usage stable at 60-65%

🎨 Top Completed Features (This Week)
  1. Player health system with UI
  2. Enemy AI pathfinding
  3. Save/load game functionality
  4. Pause menu implementation
  5. Sound effect integration

🚀 Recommendation
  Your system is performing well! Consider:

  1. Upgrade to Phase 2 for parallel processing
     → Could complete 5-6 tasks/day instead of 3
     → Would recover setup time in 1 week

  2. Add remote access (Phase 3)
     → Check progress from work
     → Get mobile notifications

  Ready to upgrade? [Y/n]: _
```

### Repair Command

```bash
./wizard.sh --repair
```

**Auto-Repair Scenarios:**

**Scenario 1: Stale Worktrees**
```
🔧 Detected issue: 5 stale worktrees

Worktrees older than 48 hours:
  - feature-42 (3 days old, PR merged)
  - feature-38 (4 days old, PR closed)
  - feature-35 (5 days old, PR merged)
  - feature-31 (7 days old, abandoned)
  - feature-28 (10 days old, PR merged)

Action: Remove stale worktrees? [Y/n]: Y

Removing worktrees...
  ✓ Removed feature-42 (freed 1.2 GB)
  ✓ Removed feature-38 (freed 1.1 GB)
  ✓ Removed feature-35 (freed 1.3 GB)
  ✓ Removed feature-31 (freed 1.2 GB)
  ✓ Removed feature-28 (freed 1.1 GB)

Total space freed: 5.9 GB
```

**Scenario 2: Hung Godot Server**
```
🔧 Detected issue: Godot server not responding

Last response: 10 minutes ago
Status: Process running but unresponsive

Action: Restart Godot server? [Y/n]: Y

Stopping Godot server...
  ✓ Sent SIGTERM
  ✓ Process stopped

Starting Godot server...
  ✓ Service started
  ✓ Health check: OK
  ✓ Ready to accept requests

Godot server restored.
```

**Scenario 3: Corrupted Config**
```
🔧 Detected issue: Configuration file corrupted

Error: YAML parse error at line 15
Backup found: config.yml.backup (2 days old)

Action: Restore from backup? [Y/n]: Y

Restoring configuration...
  ✓ Backed up corrupted file to config.yml.corrupted
  ✓ Restored config.yml.backup
  ✓ Validated configuration
  ✓ Services reloaded

Configuration restored.
```

### Add Features Command

```bash
./wizard.sh --add <feature>
```

**Available Features:**
```bash
# Remote Access (Phase 3 components)
./wizard.sh --add remote-access
# Installs: WireGuard VPN, Dashboard, Enhanced notifications

# Multi-Agent (Phase 2 if on Phase 1)
./wizard.sh --add multi-agent
# Installs: Scheduler, Registry, Queue system

# CI/CD Pipeline (Phase 5 components)
./wizard.sh --add ci-cd
# Installs: GitLab/Drone CI configuration

# Monitoring (Phase 3+ enhancement)
./wizard.sh --add monitoring
# Installs: Prometheus, Grafana, metrics collection

# Custom scripts
./wizard.sh --add custom-scripts
# Interactive script builder for common tasks
```

## Error Handling & Recovery

### Installation Failures

**Rollback Strategy:**
```bash
# If installation fails at any step:
1. Stop all running services
2. Remove partial installations
3. Restore backed up files
4. Show detailed error log
5. Offer to retry or abort

# Logs saved to:
~/.config/lazy_birtd/logs/install-<timestamp>.log
```

**Common Failures & Solutions:**

| Error | Cause | Solution |
|-------|-------|----------|
| "Claude Code not found" | CLI not installed | Show installation instructions |
| "Insufficient RAM" | < 8GB available | Suggest closing applications or upgrading |
| "Docker not running" | Docker daemon stopped | `systemctl start docker` |
| "API token invalid" | Wrong or expired token | Re-prompt for token |
| "Port 5000 in use" | Another service | Detect and offer alternative port |
| "Godot not found" | Not in PATH | Prompt for manual path |
| "Git repo not clean" | Uncommitted changes | Offer to stash or commit |

### Runtime Failures

**Self-Healing Capabilities:**

1. **Service Restart**
   ```bash
   # If Godot server crashes:
   - Detect via health check failure
   - Automatic restart (systemd handles this)
   - Alert user if restart fails 3 times
   - Offer to run --repair
   ```

2. **Worktree Cleanup**
   ```bash
   # If worktree operations fail:
   - Detect stuck/locked worktrees
   - Force removal with --force
   - Prune git worktree list
   - Verify main repo integrity
   ```

3. **Docker Recovery**
   ```bash
   # If agent container fails:
   - Capture error logs
   - Stop and remove container
   - Check Docker daemon health
   - Retry with fresh container
   - Alert after 3 failures
   ```

## Security Considerations

### Secret Management

**API Tokens:**
```bash
# Stored with restricted permissions
~/.config/lazy_birtd/secrets/
├── api_token (chmod 600)
├── vpn_key (chmod 600)
└── webhook_urls (chmod 600)

# Never committed to git
# Backed up separately
# Can be rotated via wizard
```

**Environment Isolation:**
```bash
# Claude agents run in Docker
# Limited access to:
- Project worktree only
- No access to secrets directory
- No network access (except git/API)
- Resource limits enforced
```

### Update Security

**Wizard Updates:**
```bash
# Verify updates before applying
- Check GPG signature of wizard.sh
- Compare SHA256 hash
- Option to review changes before install
- Rollback available for 30 days
```

## Platform-Specific Notes

### Linux (Ubuntu/Debian/Arch)
- Native installation preferred
- systemd services
- Full feature support

### Windows WSL2
- Requires WSL2 (not WSL1)
- Docker Desktop for Windows
- systemd emulation via `systemd-genie`
- Some limitations on Phase 3 (VPN)

### macOS
- Docker Desktop required
- No systemd (use launchd)
- Experimental support (Phase 1-2 only)

## Testing the Wizard

### Unit Tests
```bash
# Test each component independently
tests/wizard/test_detection.sh
tests/wizard/test_validation.sh
tests/wizard/test_installation.sh
tests/wizard/test_upgrade.sh
```

### Integration Tests
```bash
# Full end-to-end wizard run
tests/wizard/integration_test.sh
# Uses:
- Disposable VM
- Mock Godot project
- Fake API responses
- Validates complete flow
```

### User Acceptance Testing
```bash
# Real user scenarios
1. Fresh install on clean system
2. Upgrade from Phase 1 to Phase 2
3. Repair after manual breakage
4. Uninstall and reinstall
5. Import/export configuration
```

## Future Enhancements

### Planned Features (v2.0)
- Web-based wizard (alternative to CLI)
- Remote installation (install on VPS from laptop)
- Multi-project support (one wizard, many projects)
- Wizard API (programmatic access)
- Custom phase definitions (user-defined phases)
- Wizard plugins (community extensions)

### Telemetry (Opt-in)
```bash
# Anonymous usage stats
- Which phases are most popular
- Common failure points
- Average installation times
- Feature usage patterns

# User benefit:
- Improved wizard recommendations
- Better error messages
- Prioritize fixes for common issues
```

## Conclusion

The Setup Wizard is the cornerstone of Lazy_Birtd's user experience. It transforms a complex system into an accessible tool that anyone can use, regardless of technical expertise.

**Key Success Metrics:**
- ✅ 95%+ successful installations on first try
- ✅ < 20 minutes average setup time (Phase 1)
- ✅ < 5 minutes for upgrades
- ✅ Self-healing success rate > 80%
- ✅ User satisfaction > 4.5/5

By investing heavily in the wizard, we ensure that the power of automated game development is accessible to all developers, not just DevOps experts.
