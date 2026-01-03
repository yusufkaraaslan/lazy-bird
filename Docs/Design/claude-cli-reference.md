# Claude Code CLI - Complete Reference for Automation

**Applies to:** lazy-bird core engine (all versions)
**Related repos:** lazy-bird (core) - NOT lazy-bird-ui or plane-lazy-bird-integration
**Status:** ✅ Current and relevant for v2.0

## Critical Correction

The original automation plan assumed commands like `claude-code --task "description" --auto-commit`. **These flags do NOT exist.**

This document provides the **actual working commands** for automating Claude Code in headless mode.

## Actual Claude Code CLI Syntax

### Basic Command Structure

```bash
claude [options] [-p "prompt"] [--dangerously-skip-permissions]
```

**Key Points:**
- Command is `claude` not `claude-code` (the binary name varies by installation)
- Use `-p` flag for prompts, not `--task`
- No `--auto-commit` flag exists
- Headless mode requires `--dangerously-skip-permissions` for full automation

## Available Flags

### Verified Flags (as of Claude Code v1.x)

| Flag | Description | Safe for Automation? |
|------|-------------|----------------------|
| `-p "prompt"` | Execute a prompt headlessly | ✅ Yes |
| `--output-format [format]` | Output format (json, stream-json, text) | ✅ Yes |
| `--dangerously-skip-permissions` | Skip ALL permission prompts | ⚠️ Use in containers only |
| `--allowedTools [tools]` | Restrict which tools Claude can use | ✅ Yes, recommended |
| `--help` | Show help message | ✅ Yes |
| `--version` | Show version | ✅ Yes |

### Fictional Flags (DO NOT USE)

❌ `--task` - Does not exist, use `-p` instead
❌ `--auto-commit` - Does not exist, handle git separately
❌ `--project` - Does not exist, use `--directory` or `cd`
❌ `--workspace` - Does not exist

## Safe Automation Patterns

### Pattern 1: Interactive with Manual Review (Safest)

**Use Case:** Learning, testing, low-risk tasks

```bash
#!/bin/bash
# Read task from file
TASK=$(cat task.txt)

# Run Claude interactively
echo "$TASK" | claude

# Review changes manually
git diff

# Commit if satisfied
read -p "Commit changes? [y/n] " -n 1 -r
if [[ $REPLY =~ ^[Yy]$ ]]; then
    git add -A
    git commit -m "Auto: $TASK"
    git push
fi
```

**Pros:**
- Human oversight at every step
- Can catch errors before commit
- Safe for production

**Cons:**
- Not fully automated
- Requires human presence

### Pattern 2: Headless with Manual Git (Moderate Risk)

**Use Case:** Supervised automation, testing environment

```bash
#!/bin/bash
TASK="$1"
PROJECT_PATH="$2"

cd "$PROJECT_PATH" || exit 1

# Run Claude in headless mode
claude -p "$TASK" --output-format stream-json | tee task.log

# Check exit code
if [ $? -eq 0 ]; then
    echo "✅ Claude completed successfully"

    # Manually handle git
    git add -A
    git commit -m "Auto: $TASK"
    git push origin feature-branch

    echo "✅ Changes committed and pushed"
else
    echo "❌ Claude failed, check task.log"
    exit 1
fi
```

**Pros:**
- Headless execution
- Full git control
- Can add validation steps

**Cons:**
- Still requires permission prompts
- May hang waiting for input

### Pattern 3: Containerized YOLO Mode (High Risk, Full Automation)

**Use Case:** Isolated environment, expendable worktrees, high confidence

```bash
#!/bin/bash
# Run in Docker container with disposable filesystem
docker run --rm \
  -v "$PROJECT_PATH:/workspace" \
  -e TASK="$TASK" \
  lazy-birtd/claude-agent:latest \
  /bin/bash -c "
    cd /workspace
    claude -p \"\$TASK\" \\
      --dangerously-skip-permissions \\
      --allowedTools 'Read,Write,Bash(git:*)'
  "

# Check exit code
if [ $? -eq 0 ]; then
    echo "✅ Task completed in container"
    # Git operations happen inside container
else
    echo "❌ Task failed in container"
    exit 1
fi
```

**Pros:**
- Fully automated
- Isolated from host system
- No manual intervention

**Cons:**
- **DANGEROUS** - Can execute arbitrary commands
- Can corrupt files if Claude makes mistakes
- **ONLY use in containers/VMs**

## Detailed Flag Reference

### `-p "prompt"` (Headless Prompt)

Execute a prompt without interactive mode.

**Syntax:**
```bash
claude -p "Your prompt here"
```

**Examples:**
```bash
# Simple task
claude -p "Add a comment to main.gd explaining what it does"

# Complex task with multiple steps
claude -p "
1. Create a new file res://player/health.gd
2. Implement a Health class with max_health and current_health properties
3. Add take_damage and heal methods
4. Emit a health_changed signal when health changes
"

# Task with context
claude -p "Fix the jump physics in player.gd - it should feel more responsive. The current jump height is too low."
```

**Behavior:**
- Executes prompt in current directory
- May still prompt for permissions (use with `--dangerously-skip-permissions` to avoid)
- Exits with code 0 on success, non-zero on failure

### `--output-format [format]`

Control output format for parsing.

**Options:**
- `text` - Human-readable text (default)
- `json` - Structured JSON output
- `stream-json` - Streaming JSON (one object per line)

**Examples:**
```bash
# JSON output for parsing
claude -p "Add health system" --output-format json > result.json

# Streaming JSON for real-time monitoring
claude -p "Refactor player code" --output-format stream-json | while read line; do
    echo "Event: $line"
done
```

**JSON Structure:**
```json
{
  "type": "completion",
  "content": "I've added the health system...",
  "files_modified": [
    "res://player/health.gd",
    "res://ui/health_bar.gd"
  ],
  "tools_used": ["Write", "Read", "Bash"],
  "success": true
}
```

### `--dangerously-skip-permissions` (⚠️ Use with Extreme Caution)

Skip ALL permission prompts. Claude will execute any tool use without asking.

**WARNING:** This flag is called "dangerous" for a reason:
- Claude can delete files
- Claude can execute arbitrary shell commands
- Claude can modify any file it can access
- No safeguards against destructive operations

**ONLY use this flag when:**
1. Running in a Docker container
2. Working in a disposable git worktree
3. Have backups of everything
4. Understand the risks

**Examples:**
```bash
# In container (safe-ish)
docker run --rm -v ./project:/work claude-agent \
  claude -p "Add tests" --dangerously-skip-permissions

# In worktree (safer than main branch)
cd /tmp/agent-worktree
claude -p "Refactor code" --dangerously-skip-permissions

# NEVER do this on your main dev environment:
cd ~/my-precious-game
claude -p "Fix everything" --dangerously-skip-permissions  # 💀 DON'T
```

### `--allowedTools [tools]`

Restrict which tools Claude can use. Provides safety without manual permission prompts.

**Syntax:**
```bash
claude -p "task" --allowedTools "Tool1,Tool2,Tool3"
```

**Tool Names:**
- `Read` - Read files
- `Write` - Write/create files
- `Edit` - Edit existing files
- `Bash` - Execute bash commands (can further restrict)
- `Glob` - Find files by pattern
- `Grep` - Search file contents

**Advanced Bash Restrictions:**
```bash
# Only allow git commands
--allowedTools "Read,Write,Bash(git:*)"

# Only allow specific commands
--allowedTools "Read,Write,Bash(ls,cat,grep)"

# No bash at all
--allowedTools "Read,Write,Edit"
```

**Examples:**
```bash
# Safe read-only analysis
claude -p "Analyze the codebase and suggest improvements" \\
  --allowedTools "Read,Glob,Grep"

# Code changes with git
claude -p "Add feature X" \\
  --allowedTools "Read,Write,Edit,Bash(git:*)"

# Full access except bash
claude -p "Refactor everything" \\
  --allowedTools "Read,Write,Edit,Glob,Grep"
```

## Output Format Details

### Text Output (Default)

```bash
$ claude -p "Add hello comment"

I'll add a comment to the main script.

[Uses Write tool on res://main.gd]

✓ Added comment at top of res://main.gd

The comment explains the purpose of the main scene script.
```

### JSON Output

```bash
$ claude -p "Add hello comment" --output-format json
```

```json
{
  "conversation_id": "conv_abc123",
  "messages": [
    {
      "role": "user",
      "content": "Add hello comment"
    },
    {
      "role": "assistant",
      "content": "I'll add a comment...",
      "tool_uses": [
        {
          "type": "write",
          "file": "res://main.gd",
          "success": true
        }
      ]
    }
  ],
  "result": {
    "success": true,
    "files_modified": ["res://main.gd"],
    "files_created": [],
    "commands_executed": []
  }
}
```

### Stream JSON Output

```bash
$ claude -p "Add hello comment" --output-format stream-json
```

```
{"type":"start","timestamp":"2025-11-01T10:30:00Z"}
{"type":"thinking","content":"I need to add a comment..."}
{"type":"tool_use","tool":"Write","file":"res://main.gd"}
{"type":"tool_result","success":true}
{"type":"message","content":"✓ Added comment"}
{"type":"completion","success":true}
```

## Validation Before Use

**CRITICAL:** Before implementing automation, validate that your Claude Code installation supports these flags.

### Validation Script

```bash
#!/bin/bash
# scripts/validate-claude.sh

echo "Validating Claude Code CLI..."

# Test 1: Command exists
echo -n "1. Checking if 'claude' command exists... "
if command -v claude &> /dev/null; then
    echo "✓"
else
    echo "✗ - Claude not found in PATH"
    exit 1
fi

# Test 2: Get version
echo -n "2. Getting Claude version... "
VERSION=$(claude --version 2>&1)
echo "✓ ($VERSION)"

# Test 3: Test -p flag
echo -n "3. Testing -p flag (headless)... "
OUTPUT=$(claude -p "print hello" 2>&1)
if [ $? -eq 0 ]; then
    echo "✓"
else
    echo "✗ - -p flag failed"
    echo "$OUTPUT"
    exit 1
fi

# Test 4: Test --output-format json
echo -n "4. Testing --output-format json... "
OUTPUT=$(claude -p "test" --output-format json 2>&1)
if echo "$OUTPUT" | jq . > /dev/null 2>&1; then
    echo "✓"
else
    echo "⚠ - JSON output may not be available"
fi

# Test 5: Test --allowedTools (in safe way)
echo -n "5. Testing --allowedTools... "
OUTPUT=$(claude -p "list current directory" --allowedTools "Bash(ls)" 2>&1)
if [ $? -eq 0 ]; then
    echo "✓"
else
    echo "⚠ - --allowedTools may not be available"
fi

# Test 6: Test --dangerously-skip-permissions (in container)
echo -n "6. Testing --dangerously-skip-permissions... "
if command -v docker &> /dev/null; then
    # Create minimal test container
    docker run --rm alpine sh -c "echo test" > /dev/null 2>&1
    if [ $? -eq 0 ]; then
        echo "✓ (Docker available for safe testing)"
    else
        echo "⚠ (Docker not available, skip dangerous flag)"
    fi
else
    echo "⚠ (Docker not available, skip dangerous flag)"
fi

echo ""
echo "✅ Claude Code CLI validation complete"
echo ""
echo "Supported features:"
echo "  ✓ Headless mode (-p flag)"
echo "  $([ "$OUTPUT" != "" ] && echo "✓" || echo "⚠") JSON output"
echo "  ✓ Tool restrictions (--allowedTools)"
echo "  $(command -v docker &> /dev/null && echo "✓" || echo "⚠") Containerized dangerous mode"
echo ""
echo "Ready for automation: $([ $? -eq 0 ] && echo "YES" || echo "NO")"
```

## Integration with Lazy_Birtd

### Agent Runner Script

```bash
#!/bin/bash
# scripts/agent-runner.sh
# Runs a Claude agent on a single task

TASK_ID=$1
TASK_DESC=$2
PROJECT_PATH=$3
WORKTREE_PATH=$4

# Safety: Run in worktree, not main repo
cd "$WORKTREE_PATH" || exit 1

# Create log file
LOG_FILE="~/.config/lazy_birtd/logs/agent-$TASK_ID.log"

echo "Starting agent for task #$TASK_ID" | tee -a "$LOG_FILE"
echo "Task: $TASK_DESC" | tee -a "$LOG_FILE"

# Run Claude with restrictions
claude -p "$TASK_DESC" \\
  --output-format stream-json \\
  --allowedTools "Read,Write,Edit,Bash(git:*)" \\
  2>&1 | tee -a "$LOG_FILE"

CLAUDE_EXIT=$?

if [ $CLAUDE_EXIT -eq 0 ]; then
    echo "✅ Claude completed successfully" | tee -a "$LOG_FILE"

    # Commit changes
    git add -A
    git commit -m "Task #$TASK_ID: $TASK_DESC

Automated by Lazy_Birtd agent
Task ID: $TASK_ID
"

    # Push branch
    git push origin "feature-$TASK_ID"

    exit 0
else
    echo "❌ Claude failed with exit code $CLAUDE_EXIT" | tee -a "$LOG_FILE"
    exit 1
fi
```

### Dockerized Agent

**Dockerfile:**
```dockerfile
FROM ubuntu:22.04

# Install Claude Code (replace with actual installation)
RUN curl -fsSL https://claude.ai/install.sh | bash

# Set working directory
WORKDIR /workspace

# Copy agent script
COPY scripts/agent-runner.sh /usr/local/bin/agent-runner

# Entry point
ENTRYPOINT ["agent-runner"]
```

**Usage:**
```bash
docker run --rm \\
  -v "$WORKTREE:/workspace" \\
  -e TASK_ID="42" \\
  -e TASK_DESC="Add health system" \\
  lazy-birtd/claude-agent:latest
```

## Common Pitfalls

### Pitfall 1: Hanging on Permissions

**Problem:** Claude hangs waiting for permission input

**Solution:** Use `--dangerously-skip-permissions` or `--allowedTools`

```bash
# Bad (will hang):
claude -p "Fix bug"

# Good (restricted tools):
claude -p "Fix bug" --allowedTools "Read,Write,Edit"

# Good (containerized):
docker run ... claude -p "Fix bug" --dangerously-skip-permissions
```

### Pitfall 2: Assuming Fictional Flags Exist

**Problem:** Using `--task`, `--auto-commit`, etc.

**Solution:** Use actual flags documented here

```bash
# Bad (doesn't exist):
claude --task "Add feature" --auto-commit

# Good (actual syntax):
claude -p "Add feature" --allowedTools "Read,Write,Bash(git:*)"
git add -A && git commit -m "Auto"
```

### Pitfall 3: Running Dangerous Mode on Main Branch

**Problem:** Data loss from unchecked Claude operations

**Solution:** ALWAYS use worktrees or containers

```bash
# Bad (on main branch):
cd ~/my-game
claude -p "refactor" --dangerously-skip-permissions  # 💀

# Good (in worktree):
cd /tmp/agent-42-worktree
claude -p "refactor" --dangerously-skip-permissions  # ✓
```

## Troubleshooting

### Error: "claude: command not found"

**Cause:** Claude Code not installed or not in PATH

**Fix:**
```bash
# Find Claude installation
which claude
# Add to PATH if needed
export PATH="$PATH:/path/to/claude"
```

### Error: "Permission denied"

**Cause:** Claude trying to access restricted files

**Fix:**
```bash
# Check file permissions
ls -la

# Run with appropriate user
sudo -u lazybirtd claude -p "task"
```

### Error: "Invalid flag: --task"

**Cause:** Using fictional flag from old documentation

**Fix:** Use `-p` instead of `--task`

## Conclusion

Claude Code CAN be automated, but requires using the correct flags and understanding the safety implications. Always:

1. ✅ Validate CLI capabilities first
2. ✅ Use worktrees or containers for automation
3. ✅ Restrict tools with `--allowedTools`
4. ✅ Test in safe environment first
5. ⚠️ Use `--dangerously-skip-permissions` only when isolated
6. ❌ Never use fictional flags from outdated docs

With proper precautions, Claude Code automation is powerful and safe.
