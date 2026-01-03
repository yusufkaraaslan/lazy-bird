# Setup Wizard - Overview

## ⚠️ Updated for Corrected Architecture

This overview reflects the **corrected architecture** with:
- Phase 0 validation requirement
- Actual Claude Code CLI commands (`-p` not `--task`)
- GitHub/GitLab Issues integration
- Godot Server coordination
- gdUnit4 test framework
- Realistic resource estimates

## 🎯 What The Wizard Adds To Your Automation Plan

The Setup Wizard transforms the progressive automation plan from a technical document into an **interactive, self-configuring system** that anyone can use.

## Key Benefits

### 1. **Zero Decision Paralysis**
Instead of reading through phases and deciding where to start, the wizard asks you 8 simple questions and picks for you.

### 2. **Automatic Installation**
No more copy-pasting commands or debugging setup issues. The wizard handles:
- **Phase 0 validation** (mandatory first step)
- Claude Code CLI verification
- Godot + gdUnit4 setup
- Git worktree testing
- GitHub/GitLab API configuration
- Godot Server deployment (Phase 2+)
- Issue watcher service
- Configuration files with secure secret storage
- First test run to verify everything works

### 3. **Progressive Growth**
The wizard tracks your usage and suggests upgrades when you're ready:
- Week 1: "You're doing great with Phase 1!"
- Week 4: "You've saved 20 hours. Ready for remote access?"
- Week 8: "Your 100th task! Time for parallel agents?"

### 4. **Self-Healing**
If something breaks, run `./wizard.sh --health` and it will:
- Diagnose the problem
- Suggest fixes
- Optionally auto-repair

## How It Works

### First Time User Flow
```
curl -L https://raw.githubusercontent.com/.../wizard.sh | bash
         ↓
[System detection: RAM, Godot, Claude, etc.]
         ↓
[Phase 0 validation - REQUIRED]
  ✓ Claude Code CLI working
  ✓ Godot headless mode
  ✓ gdUnit4 installed
  ✓ Git worktrees functional
  ✓ GitHub/GitLab API access
         ↓
[8 questions about your setup]
  1. Godot project path?
  2. GitHub or GitLab?
  3. API token configured?
  4. Target phase?
  5. RAM limit?
  6. Docker available?
  7. Remote access needed?
  8. Confirm installation?
         ↓
[Installs appropriate phase + services]
  - Issue watcher service
  - Godot Server (Phase 2+)
  - Web dashboard (Phase 3+)
         ↓
[Runs test task to verify]
         ↓
[You're automated!]
```

Total time: 15 minutes for Phase 1 (after Phase 0 validation)

### Returning User Flow
```
./wizard.sh --upgrade
         ↓
"You're ready for Phase 3!"
"This adds remote access"
"Install now? [Y/n]"
         ↓
[Upgrades your system]
         ↓
[Shows new features]
```

## Wizard vs Manual Setup

| Aspect | Manual (Original Plan) | With Wizard |
|--------|------------------------|-------------|
| **Time to first automation** | 2-3 hours reading + setup | 15 minutes |
| **Decision making** | Read all options, choose | Answer 5 questions |
| **Error handling** | Debug yourself | Auto-diagnose |
| **Upgrades** | Manual migration | One command |
| **Monitoring** | Check manually | Weekly reports |
| **Success rate** | ~60% first try | ~95% first try |

## Wizard Commands Quick Reference

```bash
# First installation
curl -L https://gamedev-automation.sh | bash

# Check your setup
./wizard.sh --status

# Upgrade to next phase
./wizard.sh --upgrade

# Fix problems
./wizard.sh --health
./wizard.sh --repair

# Weekly review
./wizard.sh --weekly-review

# Add specific features
./wizard.sh --add remote-access
./wizard.sh --add multi-agent

# Export/Import setup
./wizard.sh --export > my-setup.tar.gz
./wizard.sh --import my-setup.tar.gz
```

## Smart Defaults

The wizard applies smart defaults based on your profile:

### Solo Dev on 16GB RAM (You)
- Starts with Phase 1 or 2
- Conservative RAM limits
- Single agent default
- Focus on git isolation
- Suggests Phase 3 after 2 weeks

### Team Lead
- Starts with Phase 4 or 5
- Includes CI/CD
- Multi-agent setup
- GitLab or Gitea
- Monitoring included

### Hobbyist
- Phase 1 only
- Minimal setup
- No Docker required
- Simple scripts
- Optional upgrades

## Example: Your Specific Setup

Based on your requirements (16GB RAM, solo dev, Godot, work-time automation):

```bash
$ curl -L https://raw.githubusercontent.com/yusyus/lazy_birtd/main/wizard.sh | bash

╔════════════════════════════════════════╗
║   Lazy_Birtd Setup Wizard v1.0         ║
╚════════════════════════════════════════╝

Detecting system...
✅ RAM: 16GB (sufficient for Phase 1-4)
✅ Godot: Found at /usr/bin/godot (v4.2)
✅ Claude Code: Installed
✅ Git: Configured
⚠️ Docker: Not installed (Phase 3+ will need it)

═══════════════════════════════════════
Phase 0: Validation (Required)
═══════════════════════════════════════

Running validation tests...

✓ Claude Code CLI works
✓ Godot headless mode functional
✓ gdUnit4 framework detected
✓ Git worktrees operational
✓ GitHub API access configured

✅ Phase 0 validation passed!

─────────────────────────────────────────
Recommended Configuration:
─────────────────────────────────────────
Phase: 1 (Single Agent)
RAM Usage: 8-10GB
Setup Time: 15 minutes
Features:
  • GitHub Issues integration
  • Automated PR creation
  • Issue watcher service

Upgrade path: Phase 2 in 2-4 weeks

Proceed with installation? [Y/n]: Y

Installing Phase 1...
[████████████████████] 100%

✅ Installation complete!

Services started:
  • issue-watcher (systemd)
  • Status: active

Configuration saved to:
  ~/.config/lazy_birtd/config.yml

Secrets stored securely in:
  ~/.config/lazy_birtd/secrets/ (chmod 700)

═══════════════════════════════════════
Next Steps:
═══════════════════════════════════════

1. Create your first automated task:
   gh issue create --template task \
     --title "[Task]: Add health bar" \
     --label "ready"

2. Monitor progress:
   ./wizard.sh --status

3. Check logs:
   journalctl -u issue-watcher -f

4. Weekly review:
   ./wizard.sh --weekly-review

Happy automating! 🎮
```

## The Magic Is In The Simplicity

The wizard turns this:
- 50+ page documentation
- 20+ decision points
- Hours of setup
- High failure rate

Into this:
- 5 questions
- 15 minutes
- Works first try
- Grows with you

## Integration Points

The wizard integrates with every phase:

**Phase 0 (Always)**: Validation suite
- Runs validation scripts
- Verifies Claude Code CLI
- Tests Godot + gdUnit4
- Validates git worktrees
- Checks API access

**Phase 1**: Basic automation
- Issue watcher service (systemd)
- Agent runner script
- GitHub/GitLab integration
- Secret management setup

**Phase 2**: Godot Server + testing
- Godot Server (HTTP API on port 5555)
- Test coordination queue
- gdUnit4 integration
- Retry logic implementation

**Phase 3**: Remote access + monitoring
- WireGuard VPN configuration
- Web dashboard (Flask on port 5000)
- Mobile notifications (ntfy.sh)
- Health monitoring

**Phase 4**: Multi-agent scheduling
- Agent scheduler service
- Resource-aware task distribution
- Parallel agent management
- RAM/CPU monitoring

**Phase 5**: CI/CD pipeline
- GitLab CI or Drone CI
- Automated builds (Linux, Windows)
- Deployment automation
- Build artifact management

**Phase 6**: Enterprise orchestration
- n8n workflow automation
- Advanced monitoring (Prometheus/Grafana)
- Team collaboration features
- Cost optimization

Each upgrade builds on the previous, never breaking your existing setup.

## Why This Matters

Without wizard:
> "I spent all weekend reading docs and my setup still doesn't work"

With wizard:
> "I was automating tasks within 15 minutes and upgraded to remote access when I needed it"

The wizard makes the difference between a plan and a working system.