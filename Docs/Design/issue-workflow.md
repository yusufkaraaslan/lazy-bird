# GitHub/GitLab Issue Workflow

**Applies to:** lazy-bird core engine (all versions)
**Related repos:** lazy-bird (core) - NOT lazy-bird-ui or plane-lazy-bird-integration
**Status:** ✅ Current and relevant for v2.0

## Overview

Lazy_Birtd uses GitHub or GitLab Issues as the task queue. Every morning, you create issues with detailed implementation steps, and the system automatically processes them throughout the day.

**Workflow:**
```
Morning (7-8am)          →  Day (Work Hours)           →  Lunch (12pm)        →  Evening (6pm)
Create 3-5 issues           System processes tasks          Review PRs            Merge & test
Add "ready" label           Creates PRs automatically        Approve/comment       Deploy if needed
Go to work                  Runs tests                       Continue work         Plan tomorrow
```

## Issue as Task Definition

### Why Issues?

1. **Native interface** - Use GitHub/GitLab UI you already know
2. **Mobile friendly** - Create/review tasks from phone
3. **Persistent history** - All tasks tracked forever
4. **Rich formatting** - Markdown, checklists, code blocks
5. **Collaboration ready** - Easy to add team members later
6. **API access** - Programmatic task management

### Issue Structure

**Required Fields:**
- **Title:** Short, descriptive task name
- **Body:** Detailed implementation steps
- **Labels:** `ready` (to trigger processing), complexity tags
- **Assignee:** (Optional) Auto-assigned to automation bot

**Recommended Template:**
```markdown
## Task Description
[Brief overview of what needs to be done]

## Detailed Steps
1. [Specific step with files and code]
2. [Another specific step]
3. [Final step]

## Acceptance Criteria
- [ ] Criterion 1
- [ ] Criterion 2
- [ ] Tests pass

## Complexity
[simple|medium|complex]

## Estimated Time
[How long you expect this to take]

## Context / References
[Links to docs, related issues, etc.]
```

## Creating Issues

### GitHub Interface

**Via Web UI:**
1. Navigate to repository
2. Click "Issues" → "New Issue"
3. Select "Task" template
4. Fill in details
5. Add label: `ready`
6. Click "Submit new issue"

**Via GitHub CLI:**
```bash
# Install gh if needed
# sudo pacman -S github-cli
# gh auth login

# Create from template
gh issue create \\
  --title "Add player health system" \\
  --body-file task-health-system.md \\
  --label "ready,gameplay,medium"

# Create with inline body
gh issue create \\
  --title "Fix jump physics" \\
  --body "$(cat <<'EOF'
## Task Description
Player jump feels floaty, needs to be snappier.

## Detailed Steps
1. Open res://player/player.gd
2. Modify JUMP_VELOCITY constant from -400 to -600
3. Adjust GRAVITY from 980 to 1200 for faster fall
4. Test in-game to ensure feels responsive

## Acceptance Criteria
- [ ] Jump reaches same height
- [ ] Fall is faster
- [ ] Double jump still works
- [ ] Tests pass

## Complexity
simple

## Estimated Time
15 minutes
EOF
)" \\
  --label "ready,bugfix,simple"
```

**Bulk Creation Script:**
```bash
#!/bin/bash
# scripts/create-morning-tasks.sh

# Read tasks from file
while IFS='|' read -r title body complexity; do
    gh issue create \\
      --title "$title" \\
      --body "$body" \\
      --label "ready,$complexity"

    sleep 2  # Rate limiting
done < morning-tasks.txt
```

### GitLab Interface

**Via Web UI:**
1. Navigate to project
2. Click "Issues" → "New issue"
3. Select "task" template (from `.gitlab/issue_templates/`)
4. Fill details
5. Add label: `ready`
6. Click "Create issue"

**Via GitLab CLI:**
```bash
# Install glab if needed
# sudo pacman -S gitlab-cli
# glab auth login

# Create issue
glab issue create \\
  --title "Add health system" \\
  --description-file task-health.md \\
  --label "ready,gameplay,medium"

# Create with inline description
glab issue create \\
  --title "Fix jump" \\
  --description "..." \\
  --label "ready,simple"
```

## Issue Watcher Service

### Purpose

Continuously monitors GitHub/GitLab for new issues with the `ready` label and queues them for processing.

**Phase 1.1:** Supports monitoring multiple projects simultaneously. Each project is polled sequentially, with per-project issue detection and task creation.

### Implementation

**Service:** `scripts/issue-watcher.py`

**Architecture (Phase 1.1):**
- **IssueWatcher class**: Orchestrates monitoring of multiple projects
- **ProjectWatcher class**: Monitors a single project's repository
- **Sequential polling**: Each project polled in order (foundation for Phase 2 parallelism)

```python
#!/usr/bin/env python3
"""
Issue Watcher Service
Polls GitHub/GitLab for issues labeled 'ready'
"""

import time
import requests
import yaml
import json
from pathlib import Path

class IssueWatcher:
    def __init__(self, config_path):
        self.config = self.load_config(config_path)
        self.platform = self.config['git_platform']
        self.repo = self.config['repository']
        self.token = self.load_token()
        self.poll_interval = self.config.get('poll_interval_seconds', 60)
        self.processed_issues = self.load_processed()

    def load_config(self, path):
        with open(path) as f:
            return yaml.safe_load(f)

    def load_token(self):
        token_file = Path.home() / '.config/lazy_birtd/secrets/api_token'
        return token_file.read_text().strip()

    def load_processed(self):
        """Load set of already-processed issue IDs"""
        processed_file = Path.home() / '.config/lazy_birtd/data/processed_issues.json'
        if processed_file.exists():
            return set(json.loads(processed_file.read_text()))
        return set()

    def save_processed(self):
        """Save processed issue IDs"""
        processed_file = Path.home() / '.config/lazy_birtd/data/processed_issues.json'
        processed_file.write_text(json.dumps(list(self.processed_issues)))

    def fetch_ready_issues(self):
        """Fetch issues with 'ready' label"""
        if self.platform == 'github':
            return self.fetch_github_issues()
        elif self.platform == 'gitlab':
            return self.fetch_gitlab_issues()

    def fetch_github_issues(self):
        """Fetch from GitHub API"""
        owner, repo = self.repo.split('/')[-2:]
        url = f"https://api.github.com/repos/{owner}/{repo}/issues"
        headers = {
            'Authorization': f'token {self.token}',
            'Accept': 'application/vnd.github.v3+json'
        }
        params = {
            'labels': 'ready',
            'state': 'open',
            'sort': 'created',
            'direction': 'asc'
        }

        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()

        issues = []
        for issue in response.json():
            # Skip pull requests (they show up as issues in GH API)
            if 'pull_request' in issue:
                continue

            issues.append({
                'id': issue['number'],
                'title': issue['title'],
                'body': issue['body'] or '',
                'labels': [l['name'] for l in issue['labels']],
                'url': issue['html_url']
            })

        return issues

    def fetch_gitlab_issues(self):
        """Fetch from GitLab API"""
        project_id = self.get_gitlab_project_id()
        url = f"https://gitlab.com/api/v4/projects/{project_id}/issues"
        headers = {'PRIVATE-TOKEN': self.token}
        params = {
            'labels': 'ready',
            'state': 'opened',
            'order_by': 'created_at',
            'sort': 'asc'
        }

        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()

        issues = []
        for issue in response.json():
            issues.append({
                'id': issue['iid'],
                'title': issue['title'],
                'body': issue['description'] or '',
                'labels': issue['labels'],
                'url': issue['web_url']
            })

        return issues

    def get_gitlab_project_id(self):
        """Get numeric project ID from repo URL"""
        # Parse from config or make API call
        # For simplicity, assuming it's stored in config
        return self.config.get('project_id')

    def parse_issue(self, issue):
        """Extract structured data from issue body"""
        body = issue['body']

        # Extract complexity from labels or body
        complexity = 'medium'  # default
        for label in issue['labels']:
            if label in ['simple', 'medium', 'complex']:
                complexity = label
                break

        # Extract sections from markdown
        # This is simplified; real parser would use markdown library
        steps = []
        in_steps_section = False
        for line in body.split('\\n'):
            if '## Detailed Steps' in line:
                in_steps_section = True
                continue
            if in_steps_section:
                if line.startswith('## '):
                    break
                if line.strip().startswith(('1.', '2.', '3.', '-', '*')):
                    steps.append(line.strip())

        return {
            'issue_id': issue['id'],
            'title': issue['title'],
            'body': body,
            'steps': steps,
            'complexity': complexity,
            'url': issue['url']
        }

    def queue_task(self, parsed_issue):
        """Add task to processing queue"""
        task_file = Path('/var/lib/lazy_birtd/queue') / f"task-{parsed_issue['issue_id']}.json"
        task_file.write_text(json.dumps(parsed_issue, indent=2))

        print(f"✅ Queued task #{parsed_issue['issue_id']}: {parsed_issue['title']}")

    def remove_ready_label(self, issue):
        """Remove 'ready' label after queuing"""
        if self.platform == 'github':
            owner, repo = self.repo.split('/')[-2:]
            url = f"https://api.github.com/repos/{owner}/{repo}/issues/{issue['id']}/labels/ready"
            headers = {'Authorization': f'token {self.token}'}
            requests.delete(url, headers=headers)

    def add_processing_label(self, issue):
        """Add 'processing' label"""
        if self.platform == 'github':
            owner, repo = self.repo.split('/')[-2:]
            url = f"https://api.github.com/repos/{owner}/{repo}/issues/{issue['id']}/labels"
            headers = {'Authorization': f'token {self.token}'}
            requests.post(url, headers=headers, json={'labels': ['processing']})

    def run(self):
        """Main loop"""
        print(f"🔍 Issue Watcher started")
        print(f"   Platform: {self.platform}")
        print(f"   Repository: {self.repo}")
        print(f"   Poll interval: {self.poll_interval}s")

        while True:
            try:
                issues = self.fetch_ready_issues()

                # Process new issues only
                new_issues = [i for i in issues if i['id'] not in self.processed_issues]

                if new_issues:
                    print(f"Found {len(new_issues)} new task(s)")

                for issue in new_issues:
                    parsed = self.parse_issue(issue)
                    self.queue_task(parsed)
                    self.remove_ready_label(issue)
                    self.add_processing_label(issue)
                    self.processed_issues.add(issue['id'])
                    self.save_processed()

                time.sleep(self.poll_interval)

            except KeyboardInterrupt:
                print("\\n👋 Shutting down gracefully...")
                break
            except Exception as e:
                print(f"❌ Error: {e}")
                time.sleep(self.poll_interval)

if __name__ == '__main__':
    config_path = Path.home() / '.config/lazy_birtd/config.yml'
    watcher = IssueWatcher(config_path)
    watcher.run()
```

### Systemd Service

**File:** `/etc/systemd/system/issue-watcher.service`

```ini
[Unit]
Description=Lazy_Birtd Issue Watcher
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=lazybirtd
WorkingDirectory=/opt/lazy_birtd
ExecStart=/usr/bin/python3 /opt/lazy_birtd/scripts/issue-watcher.py
Restart=always
RestartSec=30

# Logging
StandardOutput=journal
StandardError=journal
SyslogIdentifier=issue-watcher

# Environment
Environment="PYTHONUNBUFFERED=1"

[Install]
WantedBy=multi-user.target
```

**Management:**
```bash
sudo systemctl start issue-watcher
sudo systemctl enable issue-watcher
sudo systemctl status issue-watcher
journalctl -u issue-watcher -f
```

## Task Queue

### Queue Structure

**Location:** `/var/lib/lazy_birtd/queue/`

**Files:**
- `task-42.json` - Parsed task waiting to be processed
- `task-43.json` - Another queued task
- `processing/task-41.json` - Currently being processed

### Task File Format

**Phase 1 (Single Project):**
```json
{
  "issue_id": 42,
  "title": "Add player health system",
  "body": "## Task Description\\nAdd health to player...\\n",
  "steps": [
    "1. Create res://player/health.gd",
    "2. Add Health class with properties",
    "3. Implement take_damage method"
  ],
  "complexity": "medium",
  "url": "https://github.com/user/repo/issues/42",
  "queued_at": "2025-11-01T07:30:00Z",
  "priority": "normal"
}
```

**Phase 1.1 (Multi-Project) - Includes Project Context:**
```json
{
  "issue_id": 42,
  "title": "Add player health system",
  "body": "## Task Description\\nAdd health to player...\\n",
  "steps": [
    "1. Create res://player/health.gd",
    "2. Add Health class with properties",
    "3. Implement take_damage method"
  ],
  "complexity": "medium",
  "url": "https://github.com/user/my-game/issues/42",
  "queued_at": "2025-11-01T07:30:00Z",
  "priority": "normal",

  "_comment": "Phase 1.1: Project-specific context",
  "project_id": "my-game",
  "project_name": "My Platformer Game",
  "project_type": "godot",
  "project_path": "/home/user/projects/platformer",
  "repository": "https://github.com/user/my-game",
  "git_platform": "github",
  "test_command": "godot --headless -s addons/gdUnit4/bin/GdUnitCmdTool.gd --test-suite all",
  "build_command": null,
  "lint_command": null
}
```

**Key Changes in Phase 1.1:**
- `project_id`: Unique identifier for the project
- `project_name`: Display name
- `project_type`: Framework type (godot, python, rust, etc.)
- `project_path`: Absolute path to project directory
- `repository`: Full repository URL
- `test_command`, `build_command`, `lint_command`: Project-specific commands

## Multi-Project Workflow (Phase 1.1+)

### Monitoring Multiple Repositories

When configured with multiple projects, the issue watcher monitors each project's repository independently:

```
┌─────────────────────────────────────────────────────┐
│          Issue Watcher (Phase 1.1)                  │
│                                                     │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────┐ │
│  │ ProjectWatch │  │ ProjectWatch │  │  Project │ │
│  │  (my-game)   │  │ (my-backend) │  │  Watch   │ │
│  │   github.com │  │   github.com │  │(frontend)│ │
│  │   /user/game │  │  /user/backend│  │github.com│ │
│  └──────┬───────┘  └──────┬───────┘  └────┬─────┘ │
│         │                 │                │       │
└─────────┼─────────────────┼────────────────┼───────┘
          │                 │                │
          ▼                 ▼                ▼
    Poll every 60s      Poll every 60s    Poll every 60s
    Issues with         Issues with        Issues with
    'ready' label       'ready' label      'ready' label
          │                 │                │
          └─────────────────┴────────────────┘
                           │
                           ▼
                 Task Queue (/var/lib/lazy_birtd/queue/)
                 task-my-game-42.json
                 task-my-backend-15.json
                 task-my-frontend-89.json
```

### Creating Issues Across Projects

**Example Morning Routine:**
```bash
# Create task for game (Godot)
gh issue create --repo user/my-game --template task \
  --title "Add boss fight mechanics" \
  --label "ready,gameplay,medium"

# Create task for backend (Python/Django)
gh issue create --repo user/my-backend --template task \
  --title "Add WebSocket support for real-time events" \
  --label "ready,feature,medium"

# Create task for frontend (React)
gh issue create --repo user/my-frontend --template task \
  --title "Add real-time notification component" \
  --label "ready,feature,simple"
```

### Project-Aware Processing

Each task includes full project context, so the agent runner knows:
- Which repository to work on (`project_path`)
- Which test command to run (`test_command`)
- Which framework tools are available (`project_type`)
- Where to create the worktree (`feature-{project_id}-{issue_id}`)

**Task Queue Files:**
```bash
/var/lib/lazy_birtd/queue/
├── task-my-game-42.json          # project_id: my-game
├── task-my-backend-15.json       # project_id: my-backend
└── task-my-frontend-89.json      # project_id: my-frontend
```

**Worktree Isolation:**
```bash
/tmp/lazy-bird-agent-my-game-42/       # Game task worktree
/tmp/lazy-bird-agent-my-backend-15/    # Backend task worktree
/tmp/lazy-bird-agent-my-frontend-89/   # Frontend task worktree
```

### Multi-Project Logs

Issue watcher logs show per-project activity with `[project-id]` prefix:

```
2025-11-07 09:00:01 - INFO - [my-game] Polling for issues...
2025-11-07 09:00:02 - INFO - [my-game] Found issue #42: Add boss fight mechanics
2025-11-07 09:00:03 - INFO - [my-game] Creating task: task-my-game-42.json
2025-11-07 09:00:10 - INFO - [my-backend] Polling for issues...
2025-11-07 09:00:11 - INFO - [my-backend] Found issue #15: Add WebSocket support
2025-11-07 09:00:12 - INFO - [my-backend] Creating task: task-my-backend-15.json
2025-11-07 09:00:20 - INFO - [my-frontend] Polling for issues...
2025-11-07 09:00:21 - INFO - [my-frontend] No new issues
```

**Monitor with:**
```bash
journalctl --user -u issue-watcher -f | grep "\[my-game\]"
journalctl --user -u issue-watcher -f | grep "\[my-backend\]"
```

### Managing Projects

**List all configured projects:**
```bash
python3 scripts/project-manager.py list
```

**Temporarily disable a project:**
```bash
python3 scripts/project-manager.py disable --id "my-frontend"
systemctl --user restart issue-watcher
```

**Re-enable:**
```bash
python3 scripts/project-manager.py enable --id "my-frontend"
systemctl --user restart issue-watcher
```

## Processing Workflow

### Step 1: Issue Created

User creates issue with:
- Detailed steps
- `ready` label

### Step 2: Issue Watcher Detects

- Polls API every 60 seconds
- Finds new issue with `ready` label
- Parses issue body
- Creates task file in queue
- Removes `ready` label
- Adds `processing` label

### Step 3: Agent Picks Up Task

- Agent scheduler checks queue
- Assigns task to available agent
- Moves task to `processing/` directory

### Step 4: Agent Works

- Creates git worktree
- Runs Claude Code on task
- Executes tests via Godot Server
- Handles retry if tests fail

### Step 5: PR Created

- If tests pass:
  - Pushes feature branch
  - Creates Pull Request
  - Links PR to original issue
  - Adds comment to issue with PR link

- If tests fail after retries:
  - Adds comment to issue with error log
  - Removes `processing` label
  - Adds `failed` label

### Step 6: User Reviews

- User checks PRs during lunch
- Reviews code changes
- Approves or requests changes
- Can comment directly on PR or issue

### Step 7: Merge & Close

- If PR approved:
  - User merges PR
  - Issue automatically closes
  - Task marked complete

- If changes needed:
  - User adds comments
  - Can re-add `ready` label with updated instructions
  - Process repeats

## Issue Labels

### System Labels

| Label | Meaning | Set By |
|-------|---------|--------|
| `ready` | Task ready to process | User |
| `processing` | Agent working on it | System |
| `testing` | Tests running | System |
| `failed` | Task failed, needs attention | System |
| `blocked` | Waiting on dependency | System/User |

### Complexity Labels

| Label | RAM | Parallel Limit | Examples |
|-------|-----|----------------|----------|
| `simple` | 2GB | 3 agents | UI, dialogue, config |
| `medium` | 3GB | 2 agents | Gameplay, AI, refactoring |
| `complex` | 5GB | 1 agent | Physics, rendering, optimization |

### Feature Labels

| Label | Purpose |
|-------|---------|
| `bugfix` | Fixing a bug |
| `feature` | New functionality |
| `refactor` | Code improvement |
| `docs` | Documentation |
| `test` | Adding/fixing tests |

## Notifications

### When PR is Created

**GitHub/GitLab:** Automatic notification

**ntfy.sh:**
```bash
curl -d "✅ Task #42 complete - PR created: https://github.com/..." \\
  https://ntfy.sh/my-game-dev
```

### When Tests Fail

**Issue Comment:**
```markdown
❌ Tests failed after 3 attempts

**Last error:**
```
test_player_health: Expected 100, got 0
```

**Logs:** [View full output](link-to-logs)

**Next steps:**
- Review the error above
- Update task description if needed
- Re-add `ready` label to retry
```

**ntfy.sh:**
```bash
curl -d "❌ Task #42 failed tests" \\
  https://ntfy.sh/my-game-dev
```

## Advanced Features

### Task Dependencies

**Syntax in Issue Body:**
```markdown
## Dependencies
- Depends on #41 (must complete first)
- Blocks #45 (will unblock when done)
```

**Behavior:**
- System checks if dependencies are closed
- Only processes task when dependencies met
- Automatically triggers blocked tasks

### Task Priority

**Labels:**
- `priority:high` - Process before others
- `priority:low` - Process when idle

**Use Cases:**
- High: Critical bug, blocking others
- Low: Nice-to-have refactors

### Batch Tasks

**Syntax in Issue Body:**
```markdown
## Batch Processing
This is a batch task with multiple subtasks:
- [ ] Subtask 1
- [ ] Subtask 2
- [ ] Subtask 3

Process all in parallel if possible.
```

**Behavior:**
- System creates multiple tasks
- Assigns to different agents
- Merges results at end

## Best Practices

### Writing Good Task Descriptions

**Good:**
```markdown
## Task Description
Add a health system to the player character.

## Detailed Steps
1. Create res://player/health.gd with:
   - MAX_HEALTH constant = 100
   - current_health: int property
   - take_damage(amount: int) method
   - heal(amount: int) method
   - health_changed signal (emits old and new values)

2. In res://player/player.gd:
   - Add @onready var health = Health.new()
   - Connect health_changed signal to _on_health_changed
   - In _on_health_changed, update UI

3. Add tests in res://test/test_player_health.gd:
   - Test take_damage reduces health
   - Test heal increases health (not above max)
   - Test health_changed signal emitted

## Acceptance Criteria
- [ ] Health class exists and works
- [ ] Player integrates health system
- [ ] All tests pass
- [ ] Signal emits correctly
```

**Bad (too vague):**
```markdown
Add health to player
```

### Task Sizing

**Good:**
- One clear feature per task
- 30-60 minutes of work
- Testable outcome

**Bad:**
- "Implement entire combat system" (too big)
- "Change 1 constant" (too small)

### Using Labels Effectively

```bash
# Create task with all relevant labels
gh issue create \\
  --title "Add health system" \\
  --body-file task.md \\
  --label "ready,feature,gameplay,medium,priority:normal"
```

## Troubleshooting

### Issue Not Being Processed

**Check:**
1. Has `ready` label?
2. Issue-watcher service running?
3. Check logs: `journalctl -u issue-watcher -n 50`
4. API token valid?
5. Rate limits hit?

### Task Failed Immediately

**Check:**
1. Issue body parseable?
2. Steps clearly defined?
3. Project path correct?
4. Dependencies available?

### PR Not Created

**Check:**
1. Tests passed?
2. Git push successful?
3. API token has repo write permissions?
4. Branch protection rules preventing push?

## Metrics & Analytics

### Track Performance

**Query:**
```bash
# How many tasks completed today?
gh issue list --state closed --label "automated" \\
  --search "closed:>$(date -I)"

# Average time per task
# (requires custom metrics collection)
```

**Dashboard:**
- Tasks queued
- Tasks in progress
- Tasks completed today/week
- Success rate
- Average completion time

## Conclusion

Using GitHub/GitLab Issues as the task queue provides a familiar, powerful interface for managing automated game development. Combined with the issue watcher service, it creates a seamless workflow from task creation to PR review.

**Key Benefits:**
- ✅ Familiar UI (GitHub/GitLab)
- ✅ Mobile-friendly
- ✅ Rich formatting and attachments
- ✅ Built-in collaboration features
- ✅ Permanent task history
- ✅ API automation ready

This workflow scales from solo development to team collaboration without changing the core system.
