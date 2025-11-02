#!/bin/bash
# Git Worktree Validation Script
# Tests isolated worktree creation for multi-agent architecture

set -euo pipefail

PROJECT_PATH="${1:-}"

if [ -z "$PROJECT_PATH" ]; then
    echo "Usage: $0 <godot-project-path>"
    echo ""
    echo "Example:"
    echo "  $0 /home/user/my-godot-game"
    exit 1
fi

if [ ! -d "$PROJECT_PATH" ]; then
    echo "Error: Project path does not exist: $PROJECT_PATH"
    exit 1
fi

if [ ! -d "$PROJECT_PATH/.git" ]; then
    echo "Error: Not a git repository: $PROJECT_PATH"
    exit 1
fi

echo "╔════════════════════════════════════════╗"
echo "║   Git Worktree Validation Suite       ║"
echo "╚════════════════════════════════════════╝"
echo ""
echo "Project: $PROJECT_PATH"
echo ""

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

PASSED=0
FAILED=0
WARNINGS=0

pass() {
    echo -e "${GREEN}✓${NC} $1"
    PASSED=$((PASSED + 1))
}

fail() {
    echo -e "${RED}✗${NC} $1"
    FAILED=$((FAILED + 1))
}

warn() {
    echo -e "${YELLOW}⚠${NC} $1"
    WARNINGS=$((WARNINGS + 1))
}

# Track created worktrees for cleanup
WORKTREES_TO_CLEANUP=()

cleanup() {
    echo ""
    echo "Cleaning up test worktrees..."
    cd "$PROJECT_PATH"

    for worktree in "${WORKTREES_TO_CLEANUP[@]}"; do
        if [ -d "$worktree" ]; then
            git worktree remove "$worktree" --force 2>/dev/null || true
            echo "  Removed: $worktree"
        fi
    done

    # Clean up test branches
    git branch -D test-worktree-1 2>/dev/null || true
    git branch -D test-worktree-2 2>/dev/null || true
    git branch -D test-worktree-3 2>/dev/null || true

    echo "Cleanup complete"
}

trap cleanup EXIT

cd "$PROJECT_PATH"

# Test 1: Git worktree command exists
echo "Test 1: Checking git worktree support..."
if git worktree --help > /dev/null 2>&1; then
    pass "git worktree command available"
else
    fail "git worktree not supported"
    echo "   Git 2.5+ required"
    exit 1
fi

# Test 2: Check current worktrees
echo ""
echo "Test 2: Listing existing worktrees..."
WORKTREE_LIST=$(git worktree list 2>&1)
if [ $? -eq 0 ]; then
    pass "Can list worktrees"
    WORKTREE_COUNT=$(echo "$WORKTREE_LIST" | wc -l)
    echo "   Found $WORKTREE_COUNT existing worktree(s)"
else
    fail "Cannot list worktrees"
fi

# Test 3: Create first worktree
echo ""
echo "Test 3: Creating first worktree..."
WORKTREE_1="/tmp/lazy_birtd_test_wt1_$$"
WORKTREES_TO_CLEANUP+=("$WORKTREE_1")

if git worktree add -b test-worktree-1 "$WORKTREE_1" HEAD > /dev/null 2>&1; then
    if [ -d "$WORKTREE_1" ]; then
        pass "First worktree created: $WORKTREE_1"

        # Verify files were copied (check for any common files)
        FILE_COUNT=$(ls -1A "$WORKTREE_1" 2>/dev/null | wc -l)
        if [ $FILE_COUNT -gt 0 ]; then
            pass "Repository files present in worktree ($FILE_COUNT files)"
        else
            warn "Worktree appears empty"
        fi
    else
        fail "Worktree directory not created"
    fi
else
    fail "Could not create worktree"
    echo "   Error: $(git worktree add -b test-worktree-1 "$WORKTREE_1" HEAD 2>&1)"
fi

# Test 4: Create second worktree (concurrent)
echo ""
echo "Test 4: Creating second worktree (concurrent test)..."
WORKTREE_2="/tmp/lazy_birtd_test_wt2_$$"
WORKTREES_TO_CLEANUP+=("$WORKTREE_2")

if git worktree add -b test-worktree-2 "$WORKTREE_2" HEAD > /dev/null 2>&1; then
    if [ -d "$WORKTREE_2" ]; then
        pass "Second worktree created: $WORKTREE_2"
        pass "Concurrent worktrees supported"
    else
        fail "Second worktree directory not created"
    fi
else
    fail "Could not create concurrent worktree"
fi

# Test 5: Isolation test - modify files in different worktrees
echo ""
echo "Test 5: Testing worktree isolation..."
if [ -d "$WORKTREE_1" ] && [ -d "$WORKTREE_2" ]; then
    # Create test file in worktree 1
    TEST_FILE_1="$WORKTREE_1/test_isolation_1.txt"
    echo "content from worktree 1" > "$TEST_FILE_1"

    # Create different test file in worktree 2
    TEST_FILE_2="$WORKTREE_2/test_isolation_2.txt"
    echo "content from worktree 2" > "$TEST_FILE_2"

    # Check isolation
    if [ -f "$TEST_FILE_1" ] && [ ! -f "$WORKTREE_2/test_isolation_1.txt" ]; then
        pass "Worktrees are isolated (files don't cross over)"
    else
        warn "Worktree isolation may be compromised"
    fi

    if [ -f "$TEST_FILE_2" ] && [ ! -f "$WORKTREE_1/test_isolation_2.txt" ]; then
        pass "Cross-worktree file isolation confirmed"
    else
        warn "Files appearing in wrong worktree"
    fi
else
    warn "Skipping isolation test (worktrees not created)"
fi

# Test 6: Git operations in worktree
echo ""
echo "Test 6: Testing git operations in worktree..."
if [ -d "$WORKTREE_1" ]; then
    cd "$WORKTREE_1"

    # Check current branch
    CURRENT_BRANCH=$(git branch --show-current)
    if [ "$CURRENT_BRANCH" = "test-worktree-1" ]; then
        pass "Worktree is on correct branch: $CURRENT_BRANCH"
    else
        warn "Worktree on unexpected branch: $CURRENT_BRANCH"
    fi

    # Test commit
    echo "test content" > test_commit.txt
    git add test_commit.txt
    if git commit -m "Test commit in worktree" > /dev/null 2>&1; then
        pass "Can commit in worktree"
    else
        fail "Cannot commit in worktree"
    fi

    cd "$PROJECT_PATH"
else
    warn "Skipping git operations test (worktree not available)"
fi

# Test 7: Worktree removal
echo ""
echo "Test 7: Testing worktree removal..."
WORKTREE_3="/tmp/lazy_birtd_test_wt3_$$"

if git worktree add -b test-worktree-3 "$WORKTREE_3" HEAD > /dev/null 2>&1; then
    if git worktree remove "$WORKTREE_3" > /dev/null 2>&1; then
        if [ ! -d "$WORKTREE_3" ]; then
            pass "Worktree removed successfully"
            pass "Cleanup mechanism works"
        else
            warn "Worktree directory still exists after removal"
        fi
    else
        # Try with --force
        if git worktree remove "$WORKTREE_3" --force > /dev/null 2>&1; then
            warn "Worktree removed with --force (had uncommitted changes)"
        else
            fail "Could not remove worktree"
        fi
    fi
else
    warn "Could not create test worktree for removal test"
fi

# Test 8: /tmp directory permissions
echo ""
echo "Test 8: Testing /tmp directory for agent worktrees..."
if [ -d /tmp ]; then
    pass "/tmp directory exists"

    # Test write permissions
    TEST_DIR="/tmp/lazy_birtd_test_dir_$$"
    if mkdir -p "$TEST_DIR" 2>/dev/null; then
        pass "/tmp is writable"
        rmdir "$TEST_DIR"

        # Check available space
        AVAILABLE_SPACE=$(df /tmp | tail -1 | awk '{print $4}')
        AVAILABLE_GB=$((AVAILABLE_SPACE / 1024 / 1024))

        if [ $AVAILABLE_GB -gt 5 ]; then
            pass "Sufficient space in /tmp: ${AVAILABLE_GB}GB available"
        else
            warn "Limited space in /tmp: ${AVAILABLE_GB}GB (5GB+ recommended)"
        fi
    else
        fail "/tmp is not writable"
    fi
else
    fail "/tmp directory does not exist"
fi

# Test 9: Multiple concurrent worktrees stress test
echo ""
echo "Test 9: Stress test - creating 3 concurrent worktrees..."
STRESS_WORKTREES=()
STRESS_SUCCESS=0

for i in 1 2 3; do
    STRESS_WT="/tmp/lazy_birtd_stress_wt${i}_$$"
    if git worktree add -b "stress-test-$i-$$" "$STRESS_WT" HEAD > /dev/null 2>&1; then
        STRESS_SUCCESS=$((STRESS_SUCCESS + 1))
        STRESS_WORKTREES+=("$STRESS_WT")
    fi
done

if [ $STRESS_SUCCESS -eq 3 ]; then
    pass "Created 3 concurrent worktrees successfully"
else
    warn "Only created $STRESS_SUCCESS/3 worktrees"
fi

# Cleanup stress test worktrees
for wt in "${STRESS_WORKTREES[@]}"; do
    git worktree remove "$wt" --force 2>/dev/null || true
    git branch -D "$(basename "$wt")" 2>/dev/null || true
done

# Test 10: Check worktree path length
echo ""
echo "Test 10: Testing worktree path length limits..."
LONG_PATH="/tmp/agents/agent-12345678-1234-1234-1234-123456789abc"
mkdir -p "$(dirname "$LONG_PATH")" 2>/dev/null || true

if git worktree add -b "long-path-test-$$" "$LONG_PATH" HEAD > /dev/null 2>&1; then
    pass "Long worktree paths supported"
    git worktree remove "$LONG_PATH" --force 2>/dev/null || true
    git branch -D "long-path-test-$$" 2>/dev/null || true
    rmdir "$(dirname "$LONG_PATH")" 2>/dev/null || true
else
    warn "Long worktree paths may have issues"
fi

# Summary
echo ""
echo "╔════════════════════════════════════════╗"
echo "║           VALIDATION RESULTS           ║"
echo "╠════════════════════════════════════════╣"
printf "║ %-20s %17s ║\n" "Passed:" "$PASSED"
printf "║ %-20s %17s ║\n" "Failed:" "$FAILED"
printf "║ %-20s %17s ║\n" "Warnings:" "$WARNINGS"
echo "╚════════════════════════════════════════╝"
echo ""

if [ $FAILED -gt 0 ]; then
    echo -e "${RED}❌ VALIDATION FAILED${NC}"
    echo ""
    echo "Git worktree does not meet requirements for multi-agent system."
    echo "Fix the failed tests above before proceeding."
    exit 1
elif [ $WARNINGS -gt 3 ]; then
    echo -e "${YELLOW}⚠ VALIDATION PASSED WITH WARNINGS${NC}"
    echo ""
    echo "Git worktree works but with some limitations."
    echo "Review warnings above and plan accordingly."
    exit 0
else
    echo -e "${GREEN}✅ VALIDATION PASSED${NC}"
    echo ""
    echo "Git worktree ready for multi-agent architecture!"
    echo ""
    echo "Verified:"
    echo "  ✓ Worktree creation and removal"
    echo "  ✓ Multiple concurrent worktrees"
    echo "  ✓ Worktree isolation (files don't cross)"
    echo "  ✓ Git operations in worktrees"
    echo "  ✓ /tmp directory suitable for agents"
    echo ""
    echo "Next: Run full Phase 0 validation"
    echo "  ./tests/phase0/validate-all.sh $PROJECT_PATH"
    exit 0
fi
