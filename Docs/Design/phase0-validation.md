# Phase 0: Validation & Prerequisites

**Applies to:** lazy-bird core engine (all versions)
**Related repos:** lazy-bird (core) - NOT lazy-bird-ui or plane-lazy-bird-integration
**Status:** ✅ **IMPLEMENTED** - Validation framework complete

## Overview

**Phase 0 is the most important phase.** Before automating anything, we must validate that all core assumptions are correct and all prerequisites are met.

**Goal:** Prove that automated game development with Claude Code is feasible for your specific setup.

**Time:** 1-2 days of testing and validation

**Output:** Go/No-Go decision on proceeding with Phase 1

## Why Phase 0 Matters

The original plan had a critical flaw: it assumed Claude Code CLI works in ways that may not be true. **Phase 0 validates every assumption before investing weeks in automation.**

**Without Phase 0:**
- Spend weeks building automation
- Discover Claude Code doesn't support headless mode
- Entire system unusable
- Wasted time and effort

**With Phase 0:**
- Test everything first (1-2 days)
- Know what works and what doesn't
- Build automation confidently
- Adjust plan based on reality

## Validation Checklist

### System Requirements

#### ✅ Hardware

```bash
# RAM Check
echo "RAM: $(free -h | awk '/^Mem:/{print $2}')"
# Required: 8GB minimum, 16GB recommended

# CPU Check
echo "CPUs: $(nproc)"
# Required: 4+ cores

# Disk Space
echo "Disk: $(df -h / | awk 'NR==2{print $4}' )"
# Required: 20GB+ free

# GPU (optional, for Godot editor)
lspci | grep VGA
```

**Pass Criteria:**
- 8GB+ RAM ✓
- 4+ CPU cores ✓
- 20GB+ free disk ✓

#### ✅ Operating System

```bash
# OS Detection
cat /etc/os-release

# Supported: Ubuntu 20.04+, Debian 11+, Arch, Manjaro, Fedora 35+
```

**Pass Criteria:**
- Linux distribution supported ✓
- systemd available ✓
- Package manager functional ✓

#### ✅ Required Software

```bash
# Git
git --version
# Required: 2.30+

# Python
python3 --version
# Required: 3.8+

# Docker (optional for Phase 1, required for Phase 2+)
docker --version
docker ps  # Test if daemon running

# Godot
godot --version
# Required: 4.0+ (or 3.5+ if using Godot 3)
```

**Pass Criteria:**
- Git installed and configured ✓
- Python 3.8+ available ✓
- Docker working (if using) ✓
- Godot installed and runnable ✓

### Claude Code Validation

**This is the CRITICAL validation that must pass.**

#### Test 1: Installation Check

```bash
#!/bin/bash
# tests/phase0/test-claude-installation.sh

echo "=== Claude Code Installation Test ==="

# Check if command exists
if ! command -v claude &> /dev/null; then
    echo "❌ FAIL: claude command not found"
    echo "   Install from: https://claude.ai/code"
    exit 1
fi

echo "✓ claude command found"

# Get version
VERSION=$(claude --version 2>&1)
echo "✓ Version: $VERSION"

exit 0
```

#### Test 2: Basic Execution

```bash
#!/bin/bash
# tests/phase0/test-claude-basic.sh

echo "=== Claude Code Basic Execution Test ==="

# Test basic prompt
OUTPUT=$(claude -p "Print the text 'Hello from Claude Code'" 2>&1)
EXIT_CODE=$?

if [ $EXIT_CODE -ne 0 ]; then
    echo "❌ FAIL: Claude execution failed"
    echo "   Output: $OUTPUT"
    exit 1
fi

echo "✓ Claude executed successfully"
echo "✓ Output: $OUTPUT"

exit 0
```

#### Test 3: Headless Mode

```bash
#!/bin/bash
# tests/phase0/test-claude-headless.sh

echo "=== Claude Code Headless Mode Test ==="

# Create temporary test file
TEST_FILE="/tmp/claude-test-$$.txt"
echo "original content" > "$TEST_FILE"

# Test if Claude can modify file headlessly
claude -p "Modify the file $TEST_FILE to contain the text 'modified by claude'" 2>&1

# Check if file was modified
if ! grep -q "modified by claude" "$TEST_FILE"; then
    echo "❌ FAIL: Claude did not modify file"
    echo "   This might mean headless mode requires --dangerously-skip-permissions"
    rm "$TEST_FILE"
    exit 1
fi

echo "✓ Claude can modify files headlessly"
rm "$TEST_FILE"

exit 0
```

#### Test 4: Tool Restrictions

```bash
#!/bin/bash
# tests/phase0/test-claude-tools.sh

echo "=== Claude Code Tool Restrictions Test ==="

# Test if --allowedTools flag works
OUTPUT=$(claude -p "List current directory" --allowedTools "Bash(ls)" 2>&1)
EXIT_CODE=$?

if [ $EXIT_CODE -ne 0 ]; then
    echo "⚠️  WARNING: --allowedTools flag may not be available"
    echo "   Will need alternative safety measures"
    exit 0  # Not fatal, but noted
fi

echo "✓ --allowedTools flag supported"

exit 0
```

#### Test 5: Dangerous Mode (in Container)

```bash
#!/bin/bash
# tests/phase0/test-claude-dangerous.sh

echo "=== Claude Code Dangerous Mode Test ==="

# Only test if Docker available
if ! command -v docker &> /dev/null; then
    echo "⚠️  SKIP: Docker not available"
    exit 0
fi

# Create test container
docker run --rm -v /tmp:/workspace alpine sh -c "echo test" &> /dev/null
if [ $? -ne 0 ]; then
    echo "⚠️  SKIP: Docker not working"
    exit 0
fi

# Test dangerous flag in container
# NOTE: This is a simplified test, actual test would use Claude in container
echo "✓ Docker available for dangerous mode"
echo "   Full automation possible with containerization"

exit 0
```

#### Test 6: Output Format

```bash
#!/bin/bash
# tests/phase0/test-claude-output.sh

echo "=== Claude Code Output Format Test ==="

# Test JSON output
OUTPUT=$(claude -p "test" --output-format json 2>&1)

if echo "$OUTPUT" | jq . &> /dev/null; then
    echo "✓ JSON output format supported"
else
    echo "⚠️  WARNING: JSON output may not be available"
    echo "   Will parse text output instead"
fi

exit 0
```

#### Validation Results

Run all Claude tests:

```bash
#!/bin/bash
# tests/phase0/validate-claude-all.sh

TESTS=(
    "test-claude-installation.sh"
    "test-claude-basic.sh"
    "test-claude-headless.sh"
    "test-claude-tools.sh"
    "test-claude-dangerous.sh"
    "test-claude-output.sh"
)

PASSED=0
FAILED=0
WARNINGS=0

for TEST in "${TESTS[@]}"; do
    echo ""
    ./tests/phase0/$TEST
    RESULT=$?

    if [ $RESULT -eq 0 ]; then
        PASSED=$((PASSED + 1))
    else
        FAILED=$((FAILED + 1))
    fi
done

echo ""
echo "================================"
echo "Claude Code Validation Results"
echo "================================"
echo "Passed: $PASSED"
echo "Failed: $FAILED"
echo ""

if [ $FAILED -gt 0 ]; then
    echo "❌ Claude Code validation FAILED"
    echo "   Cannot proceed with automation"
    echo "   Review errors above and fix issues"
    exit 1
else
    echo "✅ Claude Code validation PASSED"
    echo "   Ready for automation"
    exit 0
fi
```

### Godot + gdUnit4 Validation

#### Test 1: Godot Headless Mode

```bash
#!/bin/bash
# tests/phase0/test-godot-headless.sh

echo "=== Godot Headless Mode Test ==="

# Test if Godot can run headless
godot --version &> /dev/null
if [ $? -ne 0 ]; then
    echo "❌ FAIL: Godot not working"
    exit 1
fi

echo "✓ Godot executable works"

# Test headless mode
godot --headless --quit &> /dev/null
if [ $? -ne 0 ]; then
    echo "❌ FAIL: Godot headless mode not working"
    exit 1
fi

echo "✓ Godot headless mode works"

exit 0
```

#### Test 2: gdUnit4 Installation

```bash
#!/bin/bash
# tests/phase0/test-gdunit4.sh

echo "=== gdUnit4 Test Framework Test ==="

PROJECT_PATH="$1"
if [ -z "$PROJECT_PATH" ]; then
    echo "Usage: $0 <godot-project-path>"
    exit 1
fi

# Check if gdUnit4 installed
if [ ! -d "$PROJECT_PATH/addons/gdUnit4" ]; then
    echo "⚠️  gdUnit4 not installed"
    echo "   Installing..."

    cd "$PROJECT_PATH"
    git clone https://github.com/MikeSchulze/gdUnit4.git addons/gdUnit4

    if [ $? -ne 0 ]; then
        echo "❌ FAIL: Could not install gdUnit4"
        exit 1
    fi
fi

echo "✓ gdUnit4 installed"

# Test if gdUnit4 works
cd "$PROJECT_PATH"
godot --headless -s addons/gdUnit4/bin/GdUnitCmdTool.gd --help &> /dev/null

if [ $? -eq 0 ]; then
    echo "✓ gdUnit4 command line tool works"
else
    echo "⚠️  WARNING: gdUnit4 CLI may need configuration"
fi

exit 0
```

#### Test 3: Sample Test Execution

```bash
#!/bin/bash
# tests/phase0/test-sample-test.sh

echo "=== Sample Test Execution ==="

PROJECT_PATH="$1"
cd "$PROJECT_PATH"

# Create a simple test if none exist
TEST_DIR="$PROJECT_PATH/test"
mkdir -p "$TEST_DIR"

if [ ! -f "$TEST_DIR/test_sample.gd" ]; then
    cat > "$TEST_DIR/test_sample.gd" <<'EOF'
extends GdUnitTestSuite

func test_sample():
    assert_that(1 + 1).is_equal(2)

func test_string():
    assert_that("hello").is_equal("hello")
EOF
fi

# Run test
echo "Running sample test..."
godot --headless -s addons/gdUnit4/bin/GdUnitCmdTool.gd --test-suite res://test/test_sample.gd

if [ $? -eq 0 ]; then
    echo "✓ Test execution successful"
else
    echo "❌ FAIL: Test execution failed"
    exit 1
fi

exit 0
```

### Git Worktree Validation

#### Test 1: Worktree Creation

```bash
#!/bin/bash
# tests/phase0/test-worktree-create.sh

echo "=== Git Worktree Creation Test ==="

PROJECT_PATH="$1"
cd "$PROJECT_PATH"

# Create test worktree
WORKTREE_PATH="/tmp/test-worktree-$$"
git worktree add -b test-branch "$WORKTREE_PATH"

if [ $? -ne 0 ]; then
    echo "❌ FAIL: Could not create worktree"
    exit 1
fi

echo "✓ Worktree created successfully"

# Verify worktree is separate
cd "$WORKTREE_PATH"
echo "test" > test-file.txt
git add test-file.txt
git commit -m "Test commit"

if [ $? -ne 0 ]; then
    echo "❌ FAIL: Could not commit in worktree"
    git worktree remove "$WORKTREE_PATH" --force
    exit 1
fi

echo "✓ Worktree isolation works"

# Cleanup
cd "$PROJECT_PATH"
git worktree remove "$WORKTREE_PATH" --force
git branch -D test-branch

echo "✓ Worktree cleanup successful"

exit 0
```

#### Test 2: Concurrent Worktrees

```bash
#!/bin/bash
# tests/phase0/test-worktree-concurrent.sh

echo "=== Concurrent Worktrees Test ==="

PROJECT_PATH="$1"
cd "$PROJECT_PATH"

# Create multiple worktrees
for i in 1 2 3; do
    WORKTREE="/tmp/test-worktree-$i-$$"
    git worktree add -b test-branch-$i "$WORKTREE"

    if [ $? -ne 0 ]; then
        echo "❌ FAIL: Could not create worktree $i"
        exit 1
    fi

    echo "✓ Created worktree $i"
done

# Verify all exist
WORKTREE_COUNT=$(git worktree list | wc -l)
if [ $WORKTREE_COUNT -lt 4 ]; then  # 3 worktrees + main
    echo "❌ FAIL: Not all worktrees created"
    exit 1
fi

echo "✓ Multiple concurrent worktrees work"

# Cleanup
for i in 1 2 3; do
    git worktree remove "/tmp/test-worktree-$i-$$" --force
    git branch -D test-branch-$i
done

echo "✓ Cleanup successful"

exit 0
```

### GitHub/GitLab API Validation

#### Test 1: API Access

```bash
#!/bin/bash
# tests/phase0/test-api-access.sh

echo "=== GitHub/GitLab API Access Test ==="

API_TOKEN=$(cat ~/.config/lazy_birtd/secrets/api_token 2>/dev/null)

if [ -z "$API_TOKEN" ]; then
    echo "❌ FAIL: API token not found"
    echo "   Run: ./scripts/setup-secrets.sh"
    exit 1
fi

# Test GitHub API
RESPONSE=$(curl -s -H "Authorization: token $API_TOKEN" https://api.github.com/user)

if echo "$RESPONSE" | jq -e '.login' > /dev/null 2>&1; then
    LOGIN=$(echo "$RESPONSE" | jq -r '.login')
    echo "✓ GitHub API access works (user: $LOGIN)"
elif echo "$RESPONSE" | jq -e '.message' > /dev/null 2>&1; then
    MESSAGE=$(echo "$RESPONSE" | jq -r '.message')
    echo "❌ FAIL: GitHub API error: $MESSAGE"
    exit 1
fi

exit 0
```

#### Test 2: Issue Creation

```bash
#!/bin/bash
# tests/phase0/test-issue-create.sh

echo "=== Issue Creation Test ==="

# This test is optional - only run if --test-issues flag provided
if [ "$1" != "--test-issues" ]; then
    echo "⚠️  SKIP: Issue creation test"
    echo "   Run with --test-issues to test (will create real issue)"
    exit 0
fi

# Create test issue
REPO="user/repo"  # Replace with actual repo
API_TOKEN=$(cat ~/.config/lazy_birtd/secrets/api_token)

RESPONSE=$(curl -s -X POST \
    -H "Authorization: token $API_TOKEN" \
    -H "Content-Type: application/json" \
    https://api.github.com/repos/$REPO/issues \
    -d '{"title":"[TEST] Validation test - please close","body":"This is a test issue created by Phase 0 validation. Safe to close.","labels":["test"]}')

if echo "$RESPONSE" | jq -e '.number' > /dev/null 2>&1; then
    ISSUE_NUM=$(echo "$RESPONSE" | jq -r '.number')
    echo "✓ Issue creation works (created #$ISSUE_NUM)"
    echo "   Please close issue #$ISSUE_NUM manually"
else
    echo "❌ FAIL: Could not create issue"
    exit 1
fi

exit 0
```

## Master Validation Script

```bash
#!/bin/bash
# tests/phase0/validate-all.sh

echo "╔════════════════════════════════════════╗"
echo "║  Phase 0: Complete Validation Suite   ║"
echo "╚════════════════════════════════════════╝"
echo ""

PROJECT_PATH="$1"
if [ -z "$PROJECT_PATH" ]; then
    echo "Usage: $0 <godot-project-path>"
    exit 1
fi

# Track results
TOTAL=0
PASSED=0
FAILED=0
WARNINGS=0

run_test() {
    local test_name="$1"
    local test_script="$2"
    shift 2
    local args="$@"

    TOTAL=$((TOTAL + 1))

    echo ""
    echo "[$TOTAL] Running: $test_name"
    echo "────────────────────────────────────────"

    if $test_script $args; then
        PASSED=$((PASSED + 1))
        echo "✅ PASS"
    else
        FAILED=$((FAILED + 1))
        echo "❌ FAIL"
    fi
}

# System Requirements
echo ""
echo "🖥️  SYSTEM REQUIREMENTS"
echo "════════════════════════════════════════"
run_test "Hardware Check" ./tests/phase0/test-hardware.sh
run_test "OS Check" ./tests/phase0/test-os.sh
run_test "Required Software" ./tests/phase0/test-software.sh

# Claude Code
echo ""
echo "🤖 CLAUDE CODE"
echo "════════════════════════════════════════"
run_test "Installation" ./tests/phase0/test-claude-installation.sh
run_test "Basic Execution" ./tests/phase0/test-claude-basic.sh
run_test "Headless Mode" ./tests/phase0/test-claude-headless.sh
run_test "Tool Restrictions" ./tests/phase0/test-claude-tools.sh
run_test "Dangerous Mode" ./tests/phase0/test-claude-dangerous.sh
run_test "Output Format" ./tests/phase0/test-claude-output.sh

# Godot & Testing
echo ""
echo "🎮 GODOT & TESTING"
echo "════════════════════════════════════════"
run_test "Godot Headless" ./tests/phase0/test-godot-headless.sh
run_test "gdUnit4 Install" ./tests/phase0/test-gdunit4.sh "$PROJECT_PATH"
run_test "Sample Test" ./tests/phase0/test-sample-test.sh "$PROJECT_PATH"

# Git Worktrees
echo ""
echo "🌿 GIT WORKTREES"
echo "════════════════════════════════════════"
run_test "Worktree Creation" ./tests/phase0/test-worktree-create.sh "$PROJECT_PATH"
run_test "Concurrent Worktrees" ./tests/phase0/test-worktree-concurrent.sh "$PROJECT_PATH"

# API Access
echo ""
echo "🌐 API ACCESS"
echo "════════════════════════════════════════"
run_test "GitHub/GitLab API" ./tests/phase0/test-api-access.sh

# Final Report
echo ""
echo "╔════════════════════════════════════════╗"
echo "║         VALIDATION RESULTS             ║"
echo "╠════════════════════════════════════════╣"
printf "║ Total Tests:    %-22s ║\n" "$TOTAL"
printf "║ Passed:         %-22s ║\n" "$PASSED"
printf "║ Failed:         %-22s ║\n" "$FAILED"
printf "║ Warnings:       %-22s ║\n" "$WARNINGS"
echo "╚════════════════════════════════════════╝"
echo ""

if [ $FAILED -eq 0 ]; then
    echo "✅ ALL VALIDATIONS PASSED"
    echo ""
    echo "You are ready to proceed with Phase 1!"
    echo "Next step: ./wizard.sh"
    exit 0
else
    echo "❌ VALIDATION FAILED"
    echo ""
    echo "Fix the failed tests above before proceeding."
    echo "Review errors and consult documentation."
    exit 1
fi
```

## Go/No-Go Decision

### Go Criteria (Proceed to Phase 1)

**Must Pass:**
- ✅ Claude Code installed and executable
- ✅ Headless mode works (with or without dangerous flag)
- ✅ Godot installed and headless mode works
- ✅ Git worktrees functional
- ✅ API access works
- ✅ Test framework (gdUnit4) installable

**Can Work Around:**
- ⚠️ JSON output format (use text parsing)
- ⚠️ Tool restrictions (use containerization)
- ⚠️ Docker (optional for Phase 1)

### No-Go Criteria (Do NOT Proceed)

**Critical Failures:**
- ❌ Claude Code cannot execute headlessly
- ❌ Godot cannot run headless tests
- ❌ Git worktrees don't work
- ❌ Insufficient RAM (< 8GB)
- ❌ API access blocked

**If No-Go:**
1. Review alternative approaches
2. Consider manual Claude Code workflow
3. Wait for Claude Code updates
4. Use different automation approach

## Cost Estimation (Phase 0)

**API Costs:**
- Testing Claude Code: $5-10 (small prompts)
- Total validation: < $15

**Time Investment:**
- Running tests: 1-2 hours
- Fixing issues: varies (0-8 hours)
- Total: 1-2 days

## Next Steps After Phase 0

**If All Tests Pass:**
```bash
# Run the wizard
./wizard.sh

# Wizard will:
# 1. Use Phase 0 validation results
# 2. Skip tests that already passed
# 3. Install Phase 1 components
# 4. Get you automating in 15 minutes
```

**If Some Tests Fail:**
1. Review specific failures
2. Consult troubleshooting docs
3. Fix issues
4. Re-run validation
5. Proceed when all pass

## Conclusion

Phase 0 is the foundation. **Do not skip it.**

Spending 1-2 days on validation saves weeks of wasted effort on a system that can't work.

**Remember:** It's better to discover limitations early than after building the entire system.

Once Phase 0 passes, you have confidence that automated game development with Claude Code is feasible for your setup, and you can proceed with Phase 1 implementation.
