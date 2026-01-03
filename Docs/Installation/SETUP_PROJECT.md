# GitHub Project Setup Guide

This guide will help you set up GitHub Issues + Projects for tracking Lazy_Bird implementation.

## Step 1: Create Labels

Go to: `https://github.com/yusufkaraaslan/lazy-bird/labels`

Create these labels:

### Priority Labels
- `priority: critical` - #d73a4a (red) - Must be done immediately
- `priority: high` - #ff9800 (orange) - Important, do soon
- `priority: medium` - #fbca04 (yellow) - Normal priority
- `priority: low` - #0e8a16 (green) - Nice to have

### Phase Labels
- `phase-0: validation` - #1d76db (blue) - Phase 0 validation scripts
- `phase-1: core` - #0052cc (dark blue) - Phase 1 core automation
- `phase-2: testing` - #5319e7 (purple) - Phase 2 Godot Server + testing
- `phase-3: remote` - #d93f0b (dark orange) - Phase 3 remote access
- `phase-4+: advanced` - #fbca04 (yellow) - Phase 4+ advanced features

### Type Labels
- `type: feature` - #a2eeef (light blue) - New feature
- `type: bug` - #d73a4a (red) - Bug fix
- `type: docs` - #0075ca (blue) - Documentation
- `type: test` - #d4c5f9 (light purple) - Testing
- `type: refactor` - #ffffff (white) - Code refactoring

### Status Labels (optional - Projects will track this)
- `status: blocked` - #b60205 (dark red) - Blocked by dependency
- `status: help-wanted` - #008672 (teal) - Need help/input
- `status: in-review` - #fbca04 (yellow) - Under review

### Component Labels
- `component: wizard` - #bfdadc (light teal) - Setup wizard
- `component: godot-server` - #c5def5 (light blue) - Godot Server
- `component: issue-watcher` - #fef2c0 (light yellow) - Issue watcher
- `component: agent-runner` - #bfd4f2 (light blue) - Agent runner
- `component: validation` - #d4c5f9 (light purple) - Validation scripts

## Step 2: Create Milestones

Go to: `https://github.com/yusufkaraaslan/lazy-bird/milestones`

Create these milestones:

1. **Phase 0: Validation Ready**
   - Due date: 1 week from now
   - Description: All validation scripts working and tested

2. **Phase 1: Core Automation MVP**
   - Due date: 2 weeks from now
   - Description: Basic issue-driven automation working end-to-end

3. **Phase 2: Testing Integration**
   - Due date: 1 month from now
   - Description: Godot Server + gdUnit4 integration complete

4. **Phase 3: Production Ready**
   - Due date: 6 weeks from now
   - Description: Remote access, monitoring, production-ready

## Step 3: Create GitHub Project

### Option A: New Projects (Beta) - Recommended

1. Go to: `https://github.com/yusufkaraaslan/lazy-bird/projects`
2. Click **"New project"**
3. Choose **"Board"** template
4. Name: `Lazy_Bird Implementation`
5. Description: `Track implementation progress for Lazy_Bird automation system`

**Set up columns:**
- 📋 **Backlog** - Future work, not prioritized yet
- 🎯 **Ready** - Prioritized, ready to start
- 🚧 **In Progress** - Currently working on
- 👀 **In Review** - Code complete, needs review/testing
- ✅ **Done** - Completed

**Configure automation:**
- Auto-add: New issues → Backlog
- Auto-move: Issue assigned → Ready
- Auto-move: PR opened → In Review
- Auto-move: Issue closed → Done

### Option B: Classic Projects

1. Go to: `https://github.com/yusufkaraaslan/lazy-bird/projects`
2. Click **"New project"** → **"Project (classic)"**
3. Name: `Implementation Roadmap`
4. Template: **"Automated kanban"**

## Step 4: Create Initial Issues

Run this script or create manually:

```bash
# This will be provided as create-issues.sh
```

Or create manually using the templates below.

## Issue Templates

### Phase 0 Issues

#### Issue 1: Implement validate-claude.sh
```markdown
**Labels:** `phase-0: validation`, `type: feature`, `priority: critical`, `component: validation`
**Milestone:** Phase 0: Validation Ready

## Description
Implement the Claude Code CLI validation script that tests all required functionality.

## Tasks
- [ ] Test `claude --version` works
- [ ] Test `-p` flag for prompts
- [ ] Test `--allowedTools` flag
- [ ] Test `--dangerously-skip-permissions` flag (in container)
- [ ] Test file modification capability
- [ ] Test directory handling
- [ ] Test output parsing
- [ ] Create comprehensive test suite

## Acceptance Criteria
- [ ] Script runs without errors
- [ ] All 8 tests pass on valid setup
- [ ] Clear error messages for failures
- [ ] Exit codes: 0 (success), 1 (failure)
- [ ] Documented in scripts/validate-claude.sh

## References
- Design: Docs/Design/phase0-validation.md
- Existing stub: scripts/validate-claude.sh
```

#### Issue 2: Implement validate-godot.sh
```markdown
**Labels:** `phase-0: validation`, `type: feature`, `priority: critical`, `component: validation`
**Milestone:** Phase 0: Validation Ready

## Description
Implement Godot + gdUnit4 validation script.

## Tasks
- [ ] Check Godot executable exists
- [ ] Verify Godot 4.x version
- [ ] Test headless mode (`--headless --quit`)
- [ ] Test project loading (`--check-only`)
- [ ] Check gdUnit4 installation
- [ ] Test gdUnit4 CLI tool
- [ ] Create sample test file
- [ ] Run sample test to verify

## Acceptance Criteria
- [ ] Script accepts project path argument
- [ ] All 8 tests pass on valid setup
- [ ] Installs gdUnit4 if missing (with confirmation)
- [ ] Clear error messages
- [ ] Documented in scripts/validate-godot.sh

## References
- Design: Docs/Design/phase0-validation.md
- Existing stub: scripts/validate-godot.sh
```

#### Issue 3: Implement test-worktree.sh
```markdown
**Labels:** `phase-0: validation`, `type: feature`, `priority: high`, `component: validation`
**Milestone:** Phase 0: Validation Ready

## Description
Implement git worktree validation for multi-agent isolation.

## Tasks
- [ ] Test git worktree command availability
- [ ] Create test worktree
- [ ] Test multiple concurrent worktrees
- [ ] Test worktree isolation (files don't cross)
- [ ] Test git operations in worktree
- [ ] Test worktree removal/cleanup
- [ ] Test /tmp directory permissions
- [ ] Stress test (3+ worktrees)

## Acceptance Criteria
- [ ] All 10 tests pass
- [ ] Proper cleanup (removes test worktrees)
- [ ] Works with /tmp directory
- [ ] Clear error messages
- [ ] Documented in scripts/test-worktree.sh

## References
- Design: Docs/Design/phase0-validation.md
- Existing stub: scripts/test-worktree.sh
```

#### Issue 4: Create validate-all.sh master script
```markdown
**Labels:** `phase-0: validation`, `type: feature`, `priority: high`, `component: validation`
**Milestone:** Phase 0: Validation Ready

## Description
Create master validation script that runs all Phase 0 tests.

## Tasks
- [ ] Create tests/phase0/ directory
- [ ] Create validate-all.sh script
- [ ] Call validate-claude.sh
- [ ] Call validate-godot.sh (with project path)
- [ ] Call test-worktree.sh (with project path)
- [ ] Generate summary report
- [ ] Exit with appropriate code
- [ ] Add to wizard.sh Phase 0 step

## Acceptance Criteria
- [ ] Runs all 3 validation scripts
- [ ] Accepts Godot project path argument
- [ ] Shows summary (X/Y tests passed)
- [ ] Clear PASS/FAIL indication
- [ ] Stops on critical failures
- [ ] Returns 0 only if all pass

## References
- Design: Docs/Design/phase0-validation.md
- Location: tests/phase0/validate-all.sh
```

### Phase 1 Issues

#### Issue 5: Implement issue-watcher.py
```markdown
**Labels:** `phase-1: core`, `type: feature`, `priority: critical`, `component: issue-watcher`
**Milestone:** Phase 1: Core Automation MVP

## Description
Implement GitHub/GitLab issue monitoring service.

## Tasks
- [ ] Create scripts/issue-watcher.py
- [ ] Implement GitHub API integration
- [ ] Implement GitLab API integration (optional)
- [ ] Poll for issues with "ready" label
- [ ] Change labels: ready → processing → automated
- [ ] Launch agent-runner.sh for each issue
- [ ] Error handling and logging
- [ ] Systemd service file

## Acceptance Criteria
- [ ] Polls every 60 seconds
- [ ] Detects new "ready" issues
- [ ] Launches agents correctly
- [ ] Handles API errors gracefully
- [ ] Logs to systemd journal
- [ ] Can run as systemd service

## References
- Design: Docs/Design/issue-workflow.md
- Spec: Docs/Design/wizard-complete-spec.md

## Dependencies
- Requires: Phase 0 complete
- Requires: API tokens configured
```

#### Issue 6: Implement agent-runner.sh
```markdown
**Labels:** `phase-1: core`, `type: feature`, `priority: critical`, `component: agent-runner`
**Milestone:** Phase 1: Core Automation MVP

## Description
Implement the agent launcher that creates worktrees and runs Claude.

## Tasks
- [ ] Create scripts/agent-runner.sh
- [ ] Accept issue ID, title, body as arguments
- [ ] Create git worktree for task
- [ ] Run Claude Code with correct syntax
- [ ] Commit changes if any
- [ ] Push branch to remote
- [ ] Create PR via gh CLI
- [ ] Cleanup worktree on completion
- [ ] Error handling and logging

## Acceptance Criteria
- [ ] Creates isolated worktree in /tmp
- [ ] Uses correct Claude syntax: `claude -p "..."`
- [ ] Commits with proper message
- [ ] Creates PR if changes made
- [ ] Cleans up worktree always
- [ ] Logs all actions
- [ ] Returns proper exit codes

## References
- Design: Docs/Design/claude-cli-reference.md
- Example: Docs/Design/implementation-roadmap.md

## Dependencies
- Requires: Phase 0 complete
- Requires: GitHub CLI (gh) installed
```

#### Issue 7: Implement wizard.sh core functionality
```markdown
**Labels:** `phase-1: core`, `type: feature`, `priority: high`, `component: wizard`
**Milestone:** Phase 1: Core Automation MVP

## Description
Complete the wizard.sh implementation beyond the branding.

## Tasks
- [ ] Implement system detection
- [ ] Implement Phase 0 validation integration
- [ ] Implement 8 question flow
- [ ] Implement configuration file generation
- [ ] Implement secret storage setup
- [ ] Implement systemd service installation
- [ ] Implement --status command
- [ ] Implement --health command

## Acceptance Criteria
- [ ] Asks all 8 questions
- [ ] Runs Phase 0 validation
- [ ] Creates ~/.config/lazy_bird/
- [ ] Generates config.yml
- [ ] Installs systemd services
- [ ] Runs test task
- [ ] Shows clear success/failure

## References
- Design: Docs/Design/wizard-complete-spec.md
- Existing: wizard.sh (branding only)

## Dependencies
- Requires: Phase 0 scripts complete
- Requires: issue-watcher.py complete
- Requires: agent-runner.sh complete
```

## Step 5: Organize Issues in Project

1. Create all issues from templates above
2. Drag them into project board:
   - Phase 0 issues → **Ready** column
   - Phase 1 issues → **Backlog** column
3. Assign yourself to first issue
4. Start working!

## Workflow

### Daily workflow:
1. Check project board
2. Move current task to **In Progress**
3. Work on it
4. Create PR when done → moves to **In Review**
5. Merge PR → issue auto-closes → moves to **Done**

### Weekly workflow:
1. Review **Done** column (celebrate progress!)
2. Move items from **Backlog** to **Ready**
3. Reprioritize based on learnings

## Tips

- **One issue in progress at a time** - Focus!
- **Break down large issues** - Max 1-2 days work per issue
- **Reference issues in commits** - `git commit -m "Implement validation script (#5)"`
- **Use issue templates** - Create .github/ISSUE_TEMPLATE/ for consistency
- **Link PRs to issues** - Use "Closes #5" in PR description

## Next Steps

1. Create the labels
2. Create the milestones
3. Create the project board
4. Create Phase 0 issues (Issues 1-4)
5. Start with Issue #1!

---

**Ready to track your implementation like a pro! 🦜📊**
