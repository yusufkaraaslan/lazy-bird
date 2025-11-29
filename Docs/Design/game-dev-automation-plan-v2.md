# Lazy_Bird Development Automation - Progressive Development Plan

## ⚠️ CRITICAL: Read This First

**This plan has been corrected from the original v1.** Key changes:
- ✅ Uses actual Claude Code CLI commands (`claude -p`, not fictional `--task` flag)
- ✅ Tasks from GitHub/GitLab Issues (not task files)
- ✅ Multi-framework support (18 frameworks via presets)
- ✅ Test Server for multi-framework test coordination
- ✅ Phase 0 validation required before implementation
- ✅ Wizard-first installation approach
- ✅ Corrected resource estimates
- ✅ **Phase 0 Web UI: COMPLETE** (React + TypeScript dashboard)
- ✅ **Phase 1.1: COMPLETE** (Multi-project management)
- ✅ **Package Distribution: COMPLETE** (pip/UV installable)

**Current Status:** Phase 1.1 Complete - Production Ready!

**Before implementing ANY phase, you MUST:**
1. Run Phase 0 validation: `./tests/phase0/validate-all.sh --type <framework>`
2. Ensure validation passes completely
3. Use the wizard for installation: `./wizard.sh`

**Quick Install:**
```bash
# Option 1: pip/UV (recommended)
pip install lazy-bird
# or
uv pip install lazy-bird

# Option 2: From source
git clone https://github.com/yusufkaraaslan/lazy-bird.git
cd lazy-bird
./wizard.sh
```

## 🎯 Vision
Build an automated development system that continues working while you're away, supporting any framework (Godot, React, Django, Rust, etc.) and scaling from simple task automation to enterprise-level orchestration based on your actual needs.

## 🔑 Core Philosophy
**Start simple, add complexity only when needed.** Each phase must deliver immediate value.

---

## 📈 Progressive Development Phases

### Phase 0: Validation (REQUIRED FIRST)
**Goal:** *"Verify all assumptions before building anything"*
**Time to complete:** 15-30 minutes
**RAM required:** None (validation only)

#### What Phase 0 Tests
```bash
# Run comprehensive validation with framework type
./tests/phase0/validate-all.sh /path/to/project --type <framework>

# Examples:
./tests/phase0/validate-all.sh ~/my-godot-game --type godot
./tests/phase0/validate-all.sh ~/my-react-app --type react
./tests/phase0/validate-all.sh ~/my-django-app --type django

# Tests performed:
✓ Claude Code CLI exists and works
✓ Correct flags available (-p, --allowedTools, etc.)
✓ Framework-specific tools installed (varies by framework)
✓ Test framework installed and functional
✓ Git worktrees work correctly
✓ GitHub/GitLab API access configured
✓ Required directory permissions
```

#### Critical Findings from Phase 0
Phase 0 revealed that **the original plan used fictional CLI flags**:

**❌ WRONG (doesn't exist):**
```bash
claude-code --task "Add feature" --auto-commit
```

**✅ CORRECT (actual syntax):**
```bash
claude -p "Add feature to res://player.gd"
# Handle git commits separately
```

#### Phase 0 Validation Scripts
- `scripts/validate-claude.sh` - Test Claude Code CLI
- `scripts/validate-godot.sh` - Test Godot + gdUnit4
- `scripts/test-worktree.sh` - Test git worktrees

**Deliverable:** Green checkmarks on all validation tests

**⚠️ DO NOT PROCEED to Phase 1 without passing Phase 0**

---

### Phase 1: Minimal Viable Automation (Wizard Setup)
**Goal:** *"Just get Claude working on tasks while I'm away"*
**Time to implement:** 15 minutes (wizard) or 2 hours (manual)
**RAM required:** 8GB minimum (Claude needs 4-6GB + system overhead)

#### Installation Method: Use the Wizard
```bash
# Recommended approach
./wizard.sh

# Wizard will:
# 1. Detect your system (RAM, Godot, Claude CLI)
# 2. Ask 8 simple questions
# 3. Set up Phase 1 automatically
# 4. Run a test task to verify everything works
```

#### Task Source: GitHub/GitLab Issues
Phase 1 uses GitHub Issues (or GitLab) as the task source:

```bash
# Morning routine (before work)
gh issue create \
  --title "[Task]: Add player health system" \
  --body "$(cat <<EOF
## Task Description
Add health tracking to player character

## Detailed Steps
1. Create res://player/health.gd
2. Add Health class extending Node
3. Add max_health and current_health properties
4. Implement take_damage() method
5. Implement heal() method

## Acceptance Criteria
- [ ] Health class exists
- [ ] Tests pass
- [ ] Health cannot go below 0
EOF
)" \
  --label "ready"

# The "ready" label triggers automation
```

#### Architecture Overview
```
GitHub/GitLab
    ↓ (polls every 60s)
Issue Watcher Service
    ↓ (detects "ready" label)
Agent Runner
    ↓ (creates worktree)
Claude Code
    ↓ (implements feature)
Git Branch + PR
```

#### Simple Automation Script (Correct CLI)
```bash
#!/bin/bash
# agent-runner.sh - Corrected Claude Code usage

ISSUE_ID=$1
ISSUE_TITLE=$2
ISSUE_BODY=$3

# Setup
PROJECT_ROOT="/home/user/godot-game"
WORKTREE="/tmp/agent-${ISSUE_ID}"
BRANCH="feature-${ISSUE_ID}"

# Create isolated worktree
cd "$PROJECT_ROOT"
git worktree add -b "$BRANCH" "$WORKTREE"

cd "$WORKTREE"

# Run Claude Code (CORRECT SYNTAX)
claude -p "$(cat <<EOF
You are working on a Godot game project.

TASK: $ISSUE_TITLE

DETAILS:
$ISSUE_BODY

Please implement this feature according to the detailed steps.
When done, commit your changes.
EOF
)" > output.log 2>&1

# Check if changes were made
if git diff --quiet; then
    echo "No changes made"
else
    # Commit changes
    git add .
    git commit -m "Implement: $ISSUE_TITLE

Auto-generated by Lazy_Birtd Agent $ISSUE_ID"

    git push origin "$BRANCH"

    # Create PR via GitHub CLI
    gh pr create \
        --title "Auto PR #${ISSUE_ID}: ${ISSUE_TITLE}" \
        --body "Automated implementation.

Review and test before merging." \
        --base main \
        --head "$BRANCH"
fi

# Cleanup
cd /
git worktree remove "$WORKTREE" --force
```

#### Issue Watcher Service
```python
#!/usr/bin/env python3
# issue-watcher.py - Monitors GitHub for tasks

import time
import subprocess
from github import Github

def main():
    gh = Github("YOUR_GITHUB_TOKEN")
    repo = gh.get_repo("username/game-repo")

    while True:
        # Find issues with "ready" label
        issues = repo.get_issues(labels=["ready"], state="open")

        for issue in issues:
            print(f"Processing issue #{issue.number}: {issue.title}")

            # Remove "ready" label, add "processing"
            issue.remove_from_labels("ready")
            issue.add_to_labels("processing")

            # Launch agent
            subprocess.run([
                './agent-runner.sh',
                str(issue.number),
                issue.title,
                issue.body
            ])

            # Mark as complete
            issue.remove_from_labels("processing")
            issue.add_to_labels("automated")

        time.sleep(60)  # Check every minute

if __name__ == '__main__':
    main()
```

#### Morning Workflow (Mobile-Friendly)
1. **7:00 AM** - Create GitHub Issues with "ready" label (from phone or desktop)
2. **7:05 AM** - Issue watcher picks them up automatically
3. **12:00 PM** - Check PRs during lunch (GitHub mobile app)
4. **6:00 PM** - Review and merge completed work

**Deliverable:** Working automation with GitHub Issues integration

**⚠️ Security Note:** Store GitHub token in `~/.config/lazy_birtd/secrets/github_token` with chmod 600

---

### Phase 2: Godot Server + Testing Integration (Week 2)
**Goal:** *"Add test execution and prepare for multi-agent"*
**Time to implement:** 1 day
**RAM required:** 10-12GB (8GB Phase 1 + 2-4GB for Godot Server)  

#### Critical Component: Godot Server

Phase 2 introduces the **Godot Server** - an HTTP API that queues and executes Godot tests sequentially. This is ESSENTIAL for preventing conflicts when multiple agents need to run tests.

**Why Godot Server?**
- Only one Godot instance can run at a time per project
- Multiple Claude agents may finish simultaneously
- Server coordinates test execution safely

#### Godot Server Architecture
```
Claude Agent 1 ──┐
Claude Agent 2 ──┼──> Godot Server (Queue) ──> Single Godot Process
Claude Agent 3 ──┘
```

#### Godot Server Implementation
```python
#!/usr/bin/env python3
# godot-server.py - Test coordination server

from flask import Flask, request, jsonify
import subprocess
import queue
import threading
import uuid
import time

app = Flask(__name__)
test_queue = queue.Queue()
test_results = {}

def test_worker():
    """Background worker that processes tests sequentially"""
    while True:
        job = test_queue.get()
        job_id = job['id']
        worktree_path = job['worktree']

        test_results[job_id] = {'status': 'running', 'started': time.time()}

        # Run gdUnit4 tests
        result = subprocess.run([
            'godot',
            '--headless',
            '--path', worktree_path,
            '-s', 'res://addons/gdUnit4/bin/GdUnitCmdTool.gd',
            '--test-all'
        ], capture_output=True, text=True, timeout=300)

        test_results[job_id] = {
            'status': 'completed',
            'exit_code': result.returncode,
            'stdout': result.stdout,
            'stderr': result.stderr,
            'passed': result.returncode == 0,
            'finished': time.time()
        }

        test_queue.task_done()

# Start worker thread
threading.Thread(target=test_worker, daemon=True).start()

@app.route('/test/submit', methods=['POST'])
def submit_test():
    """Submit a test job to the queue"""
    data = request.json
    job_id = str(uuid.uuid4())

    test_queue.put({
        'id': job_id,
        'worktree': data['worktree_path']
    })

    return jsonify({'job_id': job_id, 'position': test_queue.qsize()})

@app.route('/test/status/<job_id>', methods=['GET'])
def get_status(job_id):
    """Check test status"""
    if job_id in test_results:
        return jsonify(test_results[job_id])
    return jsonify({'status': 'queued'}), 202

@app.route('/health', methods=['GET'])
def health():
    return jsonify({
        'status': 'healthy',
        'queue_size': test_queue.qsize(),
        'active_jobs': len([r for r in test_results.values() if r['status'] == 'running'])
    })

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5555)
```

#### Enhanced Agent Runner with Godot Server
```bash
#!/bin/bash
# agent-runner-v2.sh - With test integration

ISSUE_ID=$1
ISSUE_TITLE=$2
ISSUE_BODY=$3

PROJECT_ROOT="/home/user/godot-game"
WORKTREE="/tmp/agent-${ISSUE_ID}"
BRANCH="feature-${ISSUE_ID}"
GODOT_SERVER="http://localhost:5555"

# Create worktree
cd "$PROJECT_ROOT"
git worktree add -b "$BRANCH" "$WORKTREE"
cd "$WORKTREE"

# Phase 1: Implementation
claude -p "$(cat <<EOF
Implement this Godot feature:

TASK: $ISSUE_TITLE

DETAILS:
$ISSUE_BODY

Use gdUnit4 for any tests. When done, commit your changes.
EOF
)" > output.log 2>&1

# Phase 2: Submit to Godot Server for testing
if ! git diff --quiet; then
    # Commit implementation
    git add .
    git commit -m "Implement: $ISSUE_TITLE"

    # Submit test job to Godot Server
    JOB_RESPONSE=$(curl -s -X POST "$GODOT_SERVER/test/submit" \
        -H "Content-Type: application/json" \
        -d "{\"worktree_path\": \"$WORKTREE\"}")

    JOB_ID=$(echo "$JOB_RESPONSE" | jq -r '.job_id')
    echo "Test job submitted: $JOB_ID"

    # Wait for test results (with timeout)
    MAX_WAIT=600  # 10 minutes
    WAITED=0
    while [ $WAITED -lt $MAX_WAIT ]; do
        STATUS=$(curl -s "$GODOT_SERVER/test/status/$JOB_ID")
        TEST_STATUS=$(echo "$STATUS" | jq -r '.status')

        if [ "$TEST_STATUS" = "completed" ]; then
            PASSED=$(echo "$STATUS" | jq -r '.passed')

            if [ "$PASSED" = "true" ]; then
                # Tests passed! Create PR
                git push origin "$BRANCH"

                gh pr create \
                    --title "Auto PR #${ISSUE_ID}: ${ISSUE_TITLE}" \
                    --body "✅ All tests passing

Implementation details in commits.

Automated by Lazy_Birtd" \
                    --base main \
                    --head "$BRANCH"

                echo "✅ Task complete with passing tests"
            else
                echo "❌ Tests failed"
                echo "$STATUS" | jq -r '.stdout'
            fi
            break
        fi

        sleep 5
        WAITED=$((WAITED + 5))
    done
fi

# Cleanup
cd /
git worktree remove "$WORKTREE" --force
```

#### gdUnit4 Setup
```bash
# Install gdUnit4 in your Godot project
cd /path/to/godot-project
git clone https://github.com/MikeSchulze/gdUnit4.git addons/gdUnit4

# Enable in project.godot
# Project > Project Settings > Plugins > Enable gdUnit4
```

**Deliverable:** Test-gated PRs with Godot Server coordination

**⚠️ Important:** Godot Server must be running as a systemd service:
```bash
# Install as service
sudo cp godot-server.service /etc/systemd/system/
sudo systemctl enable godot-server
sudo systemctl start godot-server
```

---

### Phase 3: Remote Access + Monitoring (Week 3-4)
**Goal:** *"Check progress from anywhere"*  
**Time to implement:** 1 weekend  
**RAM required:** 8-10GB  

#### Remote Access Stack
```yaml
# docker-compose.yml additions
  wireguard:
    image: linuxserver/wireguard
    cap_add:
      - NET_ADMIN
      - SYS_MODULE
    ports:
      - '51820:51820/udp'
    volumes:
      - './wireguard:/config'
    restart: unless-stopped
  
  novnc:
    image: theasp/novnc:latest
    ports:
      - '6080:6080'
    environment:
      - DISPLAY_WIDTH=1920
      - DISPLAY_HEIGHT=1080
      - RUN_XTERM=no
    restart: unless-stopped
```

#### Simple Web Dashboard
```python
# dashboard.py - Flask monitoring dashboard
from flask import Flask, render_template, jsonify
import json
import subprocess

app = Flask(__name__)

@app.route('/')
def dashboard():
    with open('tasks.json', 'r') as f:
        tasks = json.load(f)
    
    # Check active worktrees
    result = subprocess.run(['git', 'worktree', 'list'], 
                          capture_output=True, text=True)
    active_agents = len(result.stdout.strip().split('\n')) - 1
    
    return render_template('dashboard.html',
                         pending_tasks=len(tasks),
                         active_agents=active_agents)

@app.route('/api/status')
def status():
    return jsonify({
        'tasks': get_task_count(),
        'completed_today': get_completed_count(),
        'active_agents': get_active_agents()
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
```

#### Mobile Notifications via Ntfy
```bash
# Add to process script
notify_complete() {
    curl -d "Task completed: $1" https://ntfy.sh/your-game-dev
}
```

**Deliverable:** Full remote monitoring and control

---

### Phase 4: Multi-Agent Parallel Processing (Month 2)
**Goal:** *"2-3 agents working simultaneously"*
**Time to implement:** 1 week
**RAM required:** 16GB minimum (multiple Claude instances + Godot Server)

**⚠️ Prerequisites:**
- Phase 0, 1, 2, 3 complete and working
- Godot Server running and tested
- At least 16GB RAM available
- Understanding of resource management  

#### Agent Scheduler
```python
#!/usr/bin/env python3
# scheduler.py - Smart resource-aware agent scheduler

import json
import psutil
import subprocess
import time
from enum import Enum

class TaskComplexity(Enum):
    SIMPLE = "simple"    # UI, dialogue, config
    MEDIUM = "medium"    # gameplay, AI
    COMPLEX = "complex"  # physics, rendering

class AgentScheduler:
    def __init__(self):
        self.config = {
            "simple": {"ram_gb": 2, "max_parallel": 3},
            "medium": {"ram_gb": 3, "max_parallel": 2},
            "complex": {"ram_gb": 5, "max_parallel": 1}
        }
        self.active_agents = []
    
    def get_available_ram(self):
        return psutil.virtual_memory().available / (1024**3)
    
    def estimate_complexity(self, task):
        # Simple heuristic based on task tags
        if any(tag in task.get('tags', []) 
               for tag in ['ui', 'dialogue', 'config']):
            return TaskComplexity.SIMPLE
        elif any(tag in task.get('tags', []) 
                 for tag in ['physics', 'rendering']):
            return TaskComplexity.COMPLEX
        return TaskComplexity.MEDIUM
    
    def can_schedule(self, task):
        complexity = self.estimate_complexity(task)
        required_ram = self.config[complexity.value]["ram_gb"]
        max_parallel = self.config[complexity.value]["max_parallel"]
        
        # Check RAM
        if self.get_available_ram() < required_ram + 2:  # 2GB buffer
            return False
        
        # Check parallel limit for this complexity
        same_complexity = sum(1 for a in self.active_agents 
                            if a['complexity'] == complexity)
        if same_complexity >= max_parallel:
            return False
        
        return True
    
    def schedule_task(self, task):
        if not self.can_schedule(task):
            return False
        
        complexity = self.estimate_complexity(task)
        
        # Launch agent in background
        process = subprocess.Popen([
            './launch-agent.sh',
            str(task['id']),
            task['description'],
            complexity.value
        ])
        
        self.active_agents.append({
            'id': task['id'],
            'process': process,
            'complexity': complexity,
            'started': time.time()
        })
        
        return True
    
    def cleanup_finished(self):
        self.active_agents = [
            a for a in self.active_agents 
            if a['process'].poll() is None
        ]
    
    def run(self):
        while True:
            self.cleanup_finished()
            
            # Load pending tasks
            with open('tasks.json', 'r') as f:
                tasks = json.load(f)
            
            # Try to schedule tasks
            scheduled = []
            for task in tasks:
                if self.schedule_task(task):
                    scheduled.append(task['id'])
                    time.sleep(10)  # Stagger launches
            
            # Remove scheduled tasks
            if scheduled:
                tasks = [t for t in tasks if t['id'] not in scheduled]
                with open('tasks.json', 'w') as f:
                    json.dump(tasks, f)
            
            time.sleep(60)  # Check every minute

if __name__ == '__main__':
    scheduler = AgentScheduler()
    scheduler.run()
```

#### Enhanced Agent Launch Script
```bash
#!/bin/bash
# launch-agent.sh - Isolated agent launcher with testing

ISSUE_ID=$1
TASK_DESCRIPTION=$2
COMPLEXITY=$3

PROJECT_ROOT="/home/user/godot-game"
WORKTREE_DIR="/tmp/agents/agent-${ISSUE_ID}"

# Resource limits based on complexity
case $COMPLEXITY in
    simple)
        MEMORY_LIMIT="2G"
        CPU_LIMIT="50%"
        ;;
    medium)
        MEMORY_LIMIT="3G"
        CPU_LIMIT="75%"
        ;;
    complex)
        MEMORY_LIMIT="5G"
        CPU_LIMIT="100%"
        ;;
esac

# Create worktree
git worktree add -b feature-${ISSUE_ID} ${WORKTREE_DIR}
cd ${WORKTREE_DIR}

# Phase 1: Implementation (with resource limits)
cd ${WORKTREE_DIR}

systemd-run --scope \
    -p MemoryLimit=$MEMORY_LIMIT \
    -p CPUQuota=$CPU_LIMIT \
    claude -p "$(cat <<EOF_PROMPT
You are working on a Godot game project.

TASK: ${TASK_DESCRIPTION}

Implement this feature according to the specifications.
Use gdUnit4 for tests if applicable.
Commit your changes when complete.
EOF_PROMPT
)" > /tmp/agent-${ISSUE_ID}-impl.log 2>&1

# Check if implementation was done
if git diff --quiet; then
    echo "❌ No changes made by agent"
    exit 1
fi

# Commit implementation
git add .
git commit -m "Implement: ${TASK_DESCRIPTION}

Agent: ${ISSUE_ID}"

# Phase 2: Submit tests to Godot Server
JOB_RESPONSE=$(curl -s -X POST "http://localhost:5555/test/submit" \
    -H "Content-Type: application/json" \
    -d "{\"worktree_path\": \"${WORKTREE_DIR}\"}")

JOB_ID=$(echo "$JOB_RESPONSE" | jq -r '.job_id')

# Phase 3: Test Retry Logic (max 3 attempts)
TEST_ATTEMPTS=0
MAX_ATTEMPTS=3

while [ $TEST_ATTEMPTS -lt $MAX_ATTEMPTS ]; do
    # Wait for test results
    WAITED=0
    MAX_WAIT=600
    while [ $WAITED -lt $MAX_WAIT ]; do
        STATUS=$(curl -s "http://localhost:5555/test/status/$JOB_ID")
        TEST_STATUS=$(echo "$STATUS" | jq -r '.status')

        if [ "$TEST_STATUS" = "completed" ]; then
            PASSED=$(echo "$STATUS" | jq -r '.passed')

            if [ "$PASSED" = "true" ]; then
                # Success! Create PR
                git push origin feature-${ISSUE_ID}

                gh pr create \
                    --title "Auto PR #${ISSUE_ID}: ${TASK_DESCRIPTION}" \
                    --body "✅ All tests passing (${TEST_ATTEMPTS} retries)

Automated implementation by Lazy_Birtd Agent ${ISSUE_ID}" \
                    --base main \
                    --head "feature-${ISSUE_ID}"

                # Notify success
                curl -d "✅ Task ${ISSUE_ID} complete with tests" \
                     https://ntfy.sh/your-game-dev
                exit 0
            else
                # Tests failed - try to fix
                TEST_ATTEMPTS=$((TEST_ATTEMPTS + 1))

                if [ $TEST_ATTEMPTS -lt $MAX_ATTEMPTS ]; then
                    TEST_OUTPUT=$(echo "$STATUS" | jq -r '.stdout')
                    TEST_ERRORS=$(echo "$STATUS" | jq -r '.stderr')

                    echo "⚠️ Tests failed, attempt ${TEST_ATTEMPTS}/${MAX_ATTEMPTS}"

                    # Ask Claude to fix
                    claude -p "$(cat <<EOF_FIX
The tests are failing. Please fix the issues.

ERROR OUTPUT:
${TEST_OUTPUT}

${TEST_ERRORS}

Fix the code and commit your changes.
EOF_FIX
)" > /tmp/agent-${ISSUE_ID}-fix-${TEST_ATTEMPTS}.log 2>&1

                    git add .
                    git commit -m "Fix tests (attempt ${TEST_ATTEMPTS})"

                    # Submit new test job
                    JOB_RESPONSE=$(curl -s -X POST "http://localhost:5555/test/submit" \
                        -H "Content-Type: application/json" \
                        -d "{\"worktree_path\": \"${WORKTREE_DIR}\"}")
                    JOB_ID=$(echo "$JOB_RESPONSE" | jq -r '.job_id')
                else
                    echo "❌ Max test attempts reached"
                    exit 1
                fi
            fi
            break
        fi

        sleep 5
        WAITED=$((WAITED + 5))
    done
done

# Cleanup
cd /
git worktree remove ${WORKTREE_DIR} --force
```

**Deliverable:** 2-3x development speed with parallel agents

---

### Phase 5: Production CI/CD Pipeline (Month 3)
**Goal:** *"Automated testing, building, and deployment"*  
**Time to implement:** 1-2 weeks  
**RAM required:** 16GB  

#### Choose Your Stack

##### Option A: Gitea + Drone CI (Lightweight)
```yaml
# docker-compose.yml additions
  drone:
    image: drone/drone:2
    ports:
      - '8000:80'
    volumes:
      - './drone:/data'
    environment:
      - DRONE_GITEA_SERVER=http://gitea:3000
      - DRONE_RPC_SECRET=your-secret
      - DRONE_SERVER_HOST=localhost:8000
      - DRONE_SERVER_PROTO=http
    restart: unless-stopped
    
  drone-runner:
    image: drone/drone-runner-docker:1
    ports:
      - '3001:3000'
    volumes:
      - '/var/run/docker.sock:/var/run/docker.sock'
    environment:
      - DRONE_RPC_HOST=drone:80
      - DRONE_RPC_SECRET=your-secret
    restart: unless-stopped
```

##### Option B: GitLab CE (Full Featured)
```yaml
# docker-compose.yml for GitLab
version: '3.8'
services:
  gitlab:
    image: gitlab/gitlab-ce:latest
    hostname: 'gitlab.local'
    environment:
      GITLAB_OMNIBUS_CONFIG: |
        external_url 'http://gitlab.local'
        gitlab_rails['gitlab_shell_ssh_port'] = 2222
        # Reduce memory usage
        postgresql['shared_buffers'] = "256MB"
        prometheus_monitoring['enable'] = false
        grafana['enable'] = false
    ports:
      - '80:80'
      - '443:443'
      - '2222:22'
    volumes:
      - './gitlab/config:/etc/gitlab'
      - './gitlab/logs:/var/log/gitlab'
      - './gitlab/data:/var/opt/gitlab'
    restart: unless-stopped
```

#### CI/CD Pipeline
```yaml
# .gitlab-ci.yml or .drone.yml
stages:
  - test
  - build
  - deploy

variables:
  GODOT_VERSION: "4.2"

test:unit:
  stage: test
  image: barichello/godot-ci:${GODOT_VERSION}
  script:
    - godot --headless -s addons/gdUnit4/bin/GdUnitCmdTool.gd --test-all
  artifacts:
    reports:
      junit: test-results.xml

test:scene:
  stage: test
  image: barichello/godot-ci:${GODOT_VERSION}
  script:
    - godot --headless --quit --check-only

build:linux:
  stage: build
  image: barichello/godot-ci:${GODOT_VERSION}
  script:
    - mkdir -v -p builds/linux
    - godot --headless --export-release "Linux/X11" builds/linux/game.x86_64
  artifacts:
    paths:
      - builds/linux/
    expire_in: 1 week

build:windows:
  stage: build
  image: barichello/godot-ci:${GODOT_VERSION}
  script:
    - mkdir -v -p builds/windows
    - godot --headless --export-release "Windows Desktop" builds/windows/game.exe
  artifacts:
    paths:
      - builds/windows/
    expire_in: 1 week

deploy:itch:
  stage: deploy
  image: barichello/godot-ci:${GODOT_VERSION}
  script:
    - butler push builds/linux $ITCH_USER/$ITCH_GAME:linux
    - butler push builds/windows $ITCH_USER/$ITCH_GAME:windows
  only:
    - main
```

**Deliverable:** Automated builds and deployment

---

### Phase 6: Enterprise Orchestration (Optional)
**Goal:** *"Full team development with advanced automation"*  
**Time to implement:** 2-4 weeks  
**RAM required:** 32GB+  

#### Full Stack
```yaml
# Full enterprise docker-compose.yml
version: '3.8'

services:
  gitlab:
    image: gitlab/gitlab-ce:latest
    # Full GitLab configuration
    
  n8n:
    image: n8nio/n8n
    ports:
      - '5678:5678'
    volumes:
      - './n8n:/home/node/.n8n'
    environment:
      - N8N_BASIC_AUTH_ACTIVE=true
      - N8N_BASIC_AUTH_USER=admin
      - N8N_BASIC_AUTH_PASSWORD=changeme
    
  prometheus:
    image: prom/prometheus:latest
    ports:
      - '9090:9090'
    volumes:
      - './prometheus:/etc/prometheus'
      
  grafana:
    image: grafana/grafana-oss:latest
    ports:
      - '3000:3000'
    volumes:
      - './grafana:/var/lib/grafana'
  
  # ... additional enterprise services
```

#### n8n Advanced Workflows
```json
{
  "name": "Advanced Agent Orchestration",
  "nodes": [
    {
      "name": "GitLab Issue Trigger",
      "type": "n8n-nodes-base.gitlabTrigger",
      "webhookId": "gitlab-issues",
      "events": ["issues"]
    },
    {
      "name": "Complexity Analysis",
      "type": "n8n-nodes-base.function",
      "functionCode": "// Analyze task complexity\nreturn items;"
    },
    {
      "name": "Resource Check",
      "type": "n8n-nodes-base.httpRequest",
      "url": "http://monitor:9090/api/v1/query",
      "qs": {
        "query": "node_memory_MemAvailable_bytes"
      }
    },
    {
      "name": "Launch Agent",
      "type": "n8n-nodes-base.executeCommand",
      "command": "./orchestrate-agent.sh {{$json.issue_id}}"
    },
    {
      "name": "Monitor Progress",
      "type": "n8n-nodes-base.wait",
      "webhookPath": "agent-complete"
    },
    {
      "name": "Quality Gate",
      "type": "n8n-nodes-base.if",
      "conditions": {
        "tests_passed": true,
        "coverage": "> 80%"
      }
    }
  ]
}
```

**Deliverable:** Enterprise-grade automation

---

## 🧙 Automated Setup Wizard

### Interactive Installation System
The setup wizard automatically assesses your needs and installs the appropriate phase, making the entire system accessible to everyone regardless of technical level.

### Wizard Flow
```
┌─────────────────────────────┐
│  Welcome to Setup Wizard    │
│  "Let's automate your game  │
│   development workflow"      │
└─────────────┬───────────────┘
              ↓
┌─────────────────────────────┐
│  System Assessment          │
│  • Checking RAM (16GB)      │
│  • Finding Godot project    │
│  • Testing Claude Code      │
│  • Checking Docker/Git      │
└─────────────┬───────────────┘
              ↓
┌─────────────────────────────┐
│  Profile Questions          │
│  1. Solo or team?           │
│  2. Hours available?        │
│  3. Current pain points?    │
│  4. Technical comfort?      │
└─────────────┬───────────────┘
              ↓
┌─────────────────────────────┐
│  Recommendation             │
│  "Based on your setup:      │
│   → Start with Phase 2      │
│   → 8GB RAM usage          │
│   → 1 weekend setup"        │
└─────────────┬───────────────┘
              ↓
┌─────────────────────────────┐
│  Auto Installation          │
│  [██████████████....] 75%   │
│  Installing Gitea...        │
│  Creating scripts...        │
│  Setting up automation...   │
└─────────────┬───────────────┘
              ↓
┌─────────────────────────────┐
│  First Task Demo            │
│  "Let's run your first      │
│   automated task together"  │
│  → Creating test task       │
│  → Running Claude Code      │
│  → Showing results          │
└─────────────────────────────┘
```

### Wizard Features

#### 1. System Detection
```bash
# Automatic detection of:
- Available RAM and CPU
- Godot installation and projects
- Claude Code CLI availability  
- Docker/Podman presence
- Git configuration
- Existing automation setup
```

#### 2. Intelligent Recommendations
Based on assessment, recommends:
- Appropriate starting phase (1-6)
- Compatible tool stack
- Resource limits
- Expected time investment

#### 3. Progressive Installation
```yaml
install_modes:
  quick_start:
    time: "15 minutes"
    installs:
      - Basic scripts
      - Task file setup
      - First automation
  
  standard:
    time: "1 hour"
    installs:
      - Quick start +
      - Docker containers
      - Git integration
      - Web dashboard
  
  advanced:
    time: "2-3 hours"
    installs:
      - Standard +
      - CI/CD pipeline
      - Remote access
      - Monitoring
```

#### 4. Upgrade Wizard
Run anytime to level up:
```bash
./wizard.sh --upgrade

Current: Phase 2 (Git Isolation)
Ready for: Phase 3 (Remote Access)

Upgrade will add:
✓ WireGuard VPN setup
✓ Web dashboard  
✓ Mobile notifications
✓ TigerVNC access

Proceed? [Y/n]
```

### Wizard Commands

#### First Run
```bash
# Download and run wizard
curl -L https://gamedev-automation.sh | bash

# Or clone and run
git clone https://github.com/game-automation/wizard
cd wizard && ./setup.sh
```

#### Management Commands
```bash
# Check current setup
./wizard.sh --status

# Upgrade to next phase  
./wizard.sh --upgrade

# Add specific features
./wizard.sh --add remote-access
./wizard.sh --add multi-agent

# Reconfigure existing
./wizard.sh --reconfigure

# Health check
./wizard.sh --health
```

### Setup Wizard Interface Options

#### Option A: Terminal UI (Recommended)
```
╔════════════════════════════════╗
║   Game Automation Setup v2.0   ║
╠════════════════════════════════╣
║ 1. 🚀 Quick Start (Phase 1)    ║
║ 2. 🎯 Recommended Setup        ║
║ 3. ⚙️  Custom Installation     ║
║ 4. ⬆️  Upgrade Existing        ║
║ 5. 📊 System Check             ║
║ 6. ❓ Help                     ║
╚════════════════════════════════╝
Select [1-6]: _
```

#### Option B: Web Interface
```html
<!-- Local web UI at http://localhost:8888 -->
<div class="wizard-container">
  <div class="step-indicator">
    ● ○ ○ ○ ○ Complete
  </div>
  
  <div class="current-step">
    <h2>How much RAM do you have?</h2>
    <button>8 GB</button>
    <button>16 GB</button>
    <button>32+ GB</button>
    <button>Not sure (detect)</button>
  </div>
</div>
```

#### Option C: Config File
```yaml
# auto-setup.yml
profile: solo_developer
ram_limit: 16GB
phases:
  start: 1
  target: 3
features:
  - git_isolation
  - remote_access
  - testing
skip_interactive: true
```

### Wizard Decision Tree

```
START
  ├─ New User?
  │   ├─ YES → Assessment
  │   │   ├─ < 8GB RAM → Phase 1 only
  │   │   ├─ 16GB RAM → Phase 1-4 available
  │   │   └─ 32GB+ → All phases available
  │   └─ NO → Check existing
  │       ├─ Phase detected → Offer upgrade
  │       └─ Broken setup → Repair wizard
  │
  ├─ Time Available?
  │   ├─ < 1 hour → Quick setup
  │   ├─ Weekend → Standard setup
  │   └─ Week+ → Full setup
  │
  └─ Team Size?
      ├─ Solo → Phase 1-3 focus
      ├─ 2-3 → Phase 4-5 recommended
      └─ 4+ → Phase 6 enterprise
```

### Automatic Updates

The wizard self-updates and can upgrade your installation:

```bash
# Check for updates weekly via cron
0 0 * * 0 /home/user/game-automation/wizard.sh --check-updates

# Auto-update notification
┌────────────────────────────────┐
│ 🔄 Update Available!           │
│                                │
│ New features in Phase 2.1:     │
│ • Better error handling        │
│ • Faster git operations        │
│ • New task templates          │
│                                │
│ Update now? [Y/n]             │
└────────────────────────────────┘
```

### Health Monitoring

Built-in health checks:
```bash
$ ./wizard.sh --health

System Health Check
═══════════════════
✅ Claude Code: Connected
✅ Git: Configured  
✅ Docker: Running
⚠️  RAM Usage: 14/16 GB (high)
✅ Automation: 3 tasks pending
✅ Last run: 23 min ago
❌ Error rate: 2 failures today

Recommendations:
• Consider reducing parallel agents
• Check failed task logs
```

### Migration Support

Helps migrate between phases or systems:

```bash
# Export current setup
./wizard.sh --export > my-setup.tar.gz

# Import on new machine
./wizard.sh --import my-setup.tar.gz

# Migrate from manual to automated
./wizard.sh --migrate-from manual
```

### Example Wizard Sessions

#### Example 1: Beginner Solo Dev
```
🧙 Welcome to Game Dev Automation Setup!

❓ Is this your first time setting up automation?
> Yes

❓ How much RAM does your system have?
> [Auto-detected: 16GB]

❓ How many hours can you dedicate to setup?
> Just want to try it (< 1 hour)

📊 Recommendation: Phase 1 - Simple Automation
   • 15 minute setup
   • 4GB RAM usage  
   • Save 5-10 hours/week

Ready to install? [Y/n]: Y

Installing Phase 1...
✅ Created automation directory
✅ Set up task file
✅ Configured Claude Code
✅ Created first automation script

🎉 Setup complete! Let's run your first task:
> Creating test task: "Add a comment to player.gd"
> Running automation...
> ✅ Task completed successfully!

Next steps:
1. Add your tasks to tasks.md
2. Run: ./process.sh
3. Check back in 30 minutes!
```

#### Example 2: Experienced Dev Upgrading
```
🧙 Automation Upgrade Wizard

📊 Current Setup Detected:
   • Phase: 2 (Git Isolation)
   • Runtime: 47 days
   • Tasks completed: 234
   • Average time saved: 31 hours/week

❓ What would you like to improve?
1. Add remote monitoring
2. Speed up with parallel agents
3. Add CI/CD pipeline
> 1

📦 Phase 3 Upgrade Package:
   • WireGuard VPN
   • Web Dashboard
   • Mobile notifications
   • Resource: +2GB RAM

⚠️  This will take ~1 hour. Continue? [Y/n]: Y

Upgrading to Phase 3...
[████████████████████] 100%

✅ Upgrade complete!
🌐 Dashboard: http://localhost:5000
📱 VPN Config: ~/wireguard-mobile.conf
📬 Notifications: https://ntfy.sh/your-game-dev
```

#### Example 3: Team Lead Setup
```
🧙 Team Automation Setup

❓ How many developers on your team?
> 3

❓ Do you have existing CI/CD?
> No

❓ Primary Git platform?
> Self-hosted

📊 Recommended Configuration:
   • Phase 5: Full CI/CD
   • GitLab CE (lighter config)
   • 3 parallel agents max
   • Drone CI for builds

❓ Available RAM?
> 16GB

⚠️  Note: 16GB is tight for team setup.
   Optimizations will be applied:
   • Memory-limited containers
   • Sequential agent scheduling
   • Swap file recommended

Proceed with optimized setup? [Y/n]: Y
```

### Wizard Configuration Profiles

The wizard automatically creates profiles based on your answers:

```json
// ~/.game-automation/profile.json
{
  "profile_name": "solo_developer",
  "created": "2025-11-01",
  "phase": 2,
  "system": {
    "ram_gb": 16,
    "cpu_cores": 4,
    "os": "manjaro"
  },
  "features": {
    "git_isolation": true,
    "testing": true,
    "remote_access": false,
    "multi_agent": false,
    "ci_cd": false
  },
  "preferences": {
    "max_parallel_agents": 1,
    "task_check_interval": 1800,
    "auto_upgrade": true,
    "notifications": true
  },
  "metrics": {
    "tasks_completed": 45,
    "hours_saved": 67,
    "last_run": "2025-11-01T10:30:00Z"
  }
}
```

### Progressive Wizard Updates

The wizard learns and adapts:

```bash
# Weekly check-in
$ ./wizard.sh --weekly-review

📊 Week 12 Review
═════════════════
Tasks automated: 47 (+15 from last week)
Time saved: 23 hours
Success rate: 91%
Current phase: 2

🎯 Observations:
• You're running 15+ tasks/week
• RAM usage peaks at 9GB  
• No remote access attempts

💡 Suggestions:
1. Ready for Phase 3 (Remote Access)
   - Check progress from phone
   - Get notifications
   
2. Optimize current setup:
   - Add task prioritization
   - Improve test coverage

What would you like to do?
[1] Upgrade to Phase 3
[2] Optimize Phase 2
[3] Skip this week
```

---

## 🎮 Configuration Profiles

### Profile Selection Guide

```yaml
# config.yml - Choose your profile

profiles:
  weekend_warrior:
    phase: 1
    ram: 6GB
    setup_time: "2 hours"
    features:
      - single_agent
      - basic_automation
      - git_commits
    
  serious_solo:
    phase: 3
    ram: 10GB
    setup_time: "1 week"
    features:
      - git_worktrees
      - testing
      - remote_access
      - web_dashboard
      - notifications
    
  power_user:
    phase: 4
    ram: 16GB
    setup_time: "2 weeks"
    features:
      - multi_agent
      - smart_scheduling
      - parallel_processing
      - advanced_testing
    
  small_team:
    phase: 5
    ram: 16-24GB
    setup_time: "1 month"
    features:
      - full_ci_cd
      - automated_builds
      - deployment_pipeline
      - code_review_flow
    
  enterprise:
    phase: 6
    ram: 32GB+
    setup_time: "2 months"
    features:
      - everything
      - monitoring
      - orchestration
      - analytics
```

---

## 📋 Quick Start Guide

### Step 1: Assess Your Needs
```bash
# Answer these questions:
# 1. How much RAM do you have? → Determines max phase
# 2. Solo or team? → Determines complexity needs  
# 3. How much setup time? → Determines starting phase
# 4. Current skill level? → Determines tooling choices
```

### Step 2: Start Simple (Phase 1)
```bash
# This weekend - 2 hours
git clone https://github.com/yourusername/game-automation
cd game-automation/phase1
chmod +x process.sh
./process.sh &
```

### Step 3: Iterate Weekly
- **Week 1:** Get Phase 1 working
- **Week 2:** Add git isolation (Phase 2)
- **Week 3:** Add remote access (Phase 3)
- **Month 2:** Consider multi-agent (Phase 4)
- **When needed:** Add CI/CD (Phase 5)

---

## 💰 Cost Analysis

| Phase | Setup Cost | Monthly Cost | Time Saved/Month |
|-------|------------|--------------|------------------|
| 1 | $0 | $50-100 (Claude API) | 20 hours |
| 2 | $0 | $75-125 | 30 hours |
| 3 | $0 | $75-125 | 40 hours |
| 4 | $0 | $100-200 (multi-agent) | 60 hours |
| 5 | $0 | $100-200 | 80 hours |
| 6 | $0 | $150-300 | 100+ hours |

**Notes:**
- Claude API costs vary by usage (tokens consumed)
- Set budget limits to prevent overages
- Phase 4+ costs increase with parallel agents
- **Electricity:** ~$5/month for 24/7 operation
- **ROI:** Usually positive after first month

---

## 🎯 Success Metrics

### Phase 1 Success
- ✅ Tasks complete while you're at work
- ✅ Git commits happening automatically
- ✅ 5+ hours/week saved

### Phase 3 Success
- ✅ Can review code from phone
- ✅ Remote monitoring working
- ✅ 15+ hours/week saved

### Phase 5 Success
- ✅ Automated testing on every commit
- ✅ Builds generated automatically
- ✅ 30+ hours/week saved

---

## 🚨 Common Pitfalls to Avoid

1. **Starting too complex** - Begin with Phase 1, not Phase 6
2. **Over-engineering** - Don't add features you won't use this week
3. **Ignoring RAM limits** - Respect your 16GB constraint
4. **Perfect vs working** - Get it running, then improve
5. **Tool obsession** - Focus on results, not the stack

---

## 📚 Resources

### Essential Documentation
- [Claude Code CLI Docs](https://docs.claude.com/claude-code)
- [Godot CI/CD Guide](https://github.com/abarichello/godot-ci)
- [Git Worktrees Tutorial](https://git-scm.com/docs/git-worktree)

### Community & Support
- Discord: [Your Game Dev Automation Server]
- GitHub: [github.com/yourusername/game-automation]
- Blog: [Your progress updates]

---

## 🎮 Real-World Usage Patterns

### Daily Workflow (Phase 3+)
```markdown
7:00 AM - Before work:
- Review yesterday's PRs on phone
- Write today's tasks in web UI
- Check agent status dashboard

12:00 PM - Lunch break:
- Quick VNC check from phone
- Review any failed tests
- Adjust task priorities

6:00 PM - After work:
- Review 3-5 completed PRs
- Merge tested code
- Plan tomorrow's tasks
```

### Weekly Maintenance
```markdown
Monday: Review metrics, adjust scheduler
Friday: Clean up old worktrees, update dependencies
Weekend: Implement next phase improvements
```

---

## 🔄 Migration Paths

### From Manual to Phase 1
```bash
# Monday: Keep working manually
# Tuesday: Setup basic script
# Wednesday: First automated task
# Thursday: Refine process
# Friday: Fully automated
```

### From Phase 1 to Phase 2
```bash
# Gradual migration over a week
# Keep Phase 1 running while setting up Phase 2
# Switch over once Phase 2 is stable
```

---

## 💡 Final Wisdom

> "Perfect is the enemy of good. A simple script running today beats a complex system planned for next month."

Start with Phase 1 this weekend. You'll save 20+ hours in your first month, which you can reinvest into moving to Phase 2. Let the system grow with your needs, not your ambitions.

**Remember:** The goal is to develop games, not to build infrastructure. Every hour spent on tooling should save 5+ hours of development time.

---

*Last Updated: November 2025*  
*Version: 2.0 - Progressive Approach*  
*Tested on: Manjaro Linux, 16GB RAM, Godot 4.2*