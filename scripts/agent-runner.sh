#!/bin/bash
# Lazy_Bird Agent Runner
# Processes a single task in isolated git worktree

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Script version
VERSION="1.0.0"

# Usage information
usage() {
    cat << EOF
Usage: $0 <task-file>

Arguments:
  task-file    Path to JSON task file from queue

Example:
  $0 ~/.config/lazy_birtd/queue/task-42.json

Environment Variables:
  LAZY_BIRD_CONFIG    Path to config file (default: ~/.config/lazy_birtd/config.yml)
  LAZY_BIRD_LOG_DIR   Path to log directory (default: ~/.config/lazy_birtd/logs)

Exit Codes:
  0    Task completed successfully, PR created
  1    Task failed (Claude error, test failure, etc.)
  2    Invalid arguments or configuration
  3    Git/worktree error
  4    Cleanup failed (worktree may need manual removal)
EOF
}

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check dependencies
check_dependencies() {
    local missing_deps=()

    if ! command -v claude &> /dev/null; then
        missing_deps+=("claude (Claude Code CLI)")
    fi

    if ! command -v git &> /dev/null; then
        missing_deps+=("git")
    fi

    if ! command -v gh &> /dev/null; then
        missing_deps+=("gh (GitHub CLI)")
    fi

    if ! command -v jq &> /dev/null; then
        missing_deps+=("jq")
    fi

    if [ ${#missing_deps[@]} -gt 0 ]; then
        log_error "Missing required dependencies:"
        for dep in "${missing_deps[@]}"; do
            echo "  - $dep"
        done
        exit 2
    fi
}

# Load configuration
load_config() {
    local config_file="${LAZY_BIRD_CONFIG:-$HOME/.config/lazy_birtd/config.yml}"

    if [ ! -f "$config_file" ]; then
        log_error "Configuration file not found: $config_file"
        exit 2
    fi

    # Parse YAML config (basic parsing, assumes key: value format)
    GODOT_PROJECT_PATH=$(grep -E "^godot_project_path:" "$config_file" | sed 's/godot_project_path: *//' | tr -d '"' || echo "")
    REPOSITORY=$(grep -E "^repository:" "$config_file" | sed 's/repository: *//' | tr -d '"' || echo "")

    if [ -z "$GODOT_PROJECT_PATH" ]; then
        log_error "godot_project_path not found in config"
        exit 2
    fi

    if [ ! -d "$GODOT_PROJECT_PATH" ]; then
        log_error "Godot project path does not exist: $GODOT_PROJECT_PATH"
        exit 2
    fi

    if [ ! -d "$GODOT_PROJECT_PATH/.git" ]; then
        log_error "Not a git repository: $GODOT_PROJECT_PATH"
        exit 2
    fi
}

# Parse task JSON
parse_task() {
    local task_file="$1"

    if [ ! -f "$task_file" ]; then
        log_error "Task file not found: $task_file"
        exit 2
    fi

    TASK_ID=$(jq -r '.issue_id' "$task_file")
    TASK_TITLE=$(jq -r '.title' "$task_file")
    TASK_BODY=$(jq -r '.body' "$task_file")
    TASK_COMPLEXITY=$(jq -r '.complexity // "medium"' "$task_file")
    TASK_URL=$(jq -r '.url' "$task_file")
    TASK_REPOSITORY=$(jq -r '.repository' "$task_file")

    if [ -z "$TASK_ID" ] || [ "$TASK_ID" = "null" ]; then
        log_error "Invalid task file: missing issue_id"
        exit 2
    fi

    # Extract owner/repo from repository URL
    if [ -n "$TASK_REPOSITORY" ] && [ "$TASK_REPOSITORY" != "null" ]; then
        REPO_NAME=$(echo "$TASK_REPOSITORY" | sed -E 's|https?://github.com/||' | sed 's|\.git$||')
    else
        # Fallback to config if not in task
        REPO_NAME=$(echo "$REPOSITORY" | sed -E 's|https?://github.com/||' | sed 's|\.git$||')
    fi

    log_info "Task #$TASK_ID: $TASK_TITLE"
    log_info "Complexity: $TASK_COMPLEXITY"
}

# Update issue labels: in-queue → in-process
update_labels_to_processing() {
    log_info "Updating issue labels to 'in-process'..."

    if gh issue edit "$TASK_ID" \
        --repo "$REPO_NAME" \
        --remove-label "in-queue" \
        --add-label "in-process" 2>/dev/null; then
        log_success "Labels updated: in-queue → in-process"
    else
        log_warning "Failed to update labels (continuing anyway)"
    fi
}

# Update issue labels: in-process → in-review
update_labels_to_review() {
    log_info "Updating issue labels to 'in-review'..."

    if gh issue edit "$TASK_ID" \
        --repo "$REPO_NAME" \
        --remove-label "in-process" \
        --add-label "in-review" 2>/dev/null; then
        log_success "Labels updated: in-process → in-review"
    else
        log_warning "Failed to update labels (continuing anyway)"
    fi
}

# Create worktree
create_worktree() {
    BRANCH_NAME="feature-$TASK_ID"
    WORKTREE_PATH="/tmp/lazy-bird-agent-$TASK_ID"

    log_info "Creating worktree: $WORKTREE_PATH"

    cd "$GODOT_PROJECT_PATH" || exit 3

    # Clean up existing worktree if it exists
    if [ -d "$WORKTREE_PATH" ]; then
        log_warning "Worktree already exists, removing: $WORKTREE_PATH"
        git worktree remove "$WORKTREE_PATH" --force 2>/dev/null || rm -rf "$WORKTREE_PATH"
    fi

    # Check if branch exists (might be left over from previous run)
    if git show-ref --verify --quiet refs/heads/"$BRANCH_NAME"; then
        log_warning "Branch already exists, deleting: $BRANCH_NAME"
        git branch -D "$BRANCH_NAME" 2>/dev/null || true
    fi

    # Create new worktree with new branch
    if git worktree add -b "$BRANCH_NAME" "$WORKTREE_PATH" HEAD; then
        log_success "Worktree created successfully"
    else
        log_error "Failed to create worktree"
        exit 3
    fi
}

# Run Claude Code
run_claude() {
    log_info "Running Claude Code on task..."

    cd "$WORKTREE_PATH" || exit 3

    # Prepare prompt
    CLAUDE_PROMPT="TASK: $TASK_TITLE

DETAILS:
$TASK_BODY

Implement this task following the detailed steps above. Make sure to:
1. Follow the acceptance criteria
2. Write clean, well-documented code
3. Test your changes
4. **IMPORTANT**: DO NOT commit your changes - the automation system will handle git operations

Work in the current directory: $WORKTREE_PATH
This is a Godot game project.

**DO NOT use git commit** - just make the file changes. The automation will commit and push."

    # Create log file
    LOG_DIR="${LAZY_BIRD_LOG_DIR:-$HOME/.config/lazy_birtd/logs}"
    mkdir -p "$LOG_DIR"
    LOG_FILE="$LOG_DIR/agent-task-$TASK_ID.log"

    log_info "Logging to: $LOG_FILE"
    echo "=== Agent Task #$TASK_ID ===" > "$LOG_FILE"
    echo "Started: $(date)" >> "$LOG_FILE"
    echo "Task: $TASK_TITLE" >> "$LOG_FILE"
    echo "Worktree: $WORKTREE_PATH" >> "$LOG_FILE"
    echo "" >> "$LOG_FILE"

    # Run Claude with safety restrictions
    # Use --allowedTools to restrict what Claude can do
    # Don't use --dangerously-skip-permissions unless in container
    log_info "Executing Claude Code CLI..."

    if claude -p "$CLAUDE_PROMPT" \
        --allowedTools "Read,Write,Edit,Glob,Grep,Bash(git:*)" \
        2>&1 | tee -a "$LOG_FILE"; then

        CLAUDE_EXIT=0
        log_success "Claude completed successfully"
    else
        CLAUDE_EXIT=$?
        log_error "Claude failed with exit code: $CLAUDE_EXIT"
        echo "" >> "$LOG_FILE"
        echo "Failed: $(date)" >> "$LOG_FILE"
        echo "Exit code: $CLAUDE_EXIT" >> "$LOG_FILE"
        return 1
    fi

    echo "" >> "$LOG_FILE"
    echo "Completed: $(date)" >> "$LOG_FILE"

    return 0
}

# Check for changes
check_changes() {
    cd "$WORKTREE_PATH" || exit 3

    # Debug: List files in worktree
    log_info "Files in worktree:"
    ls -la | tee -a "$LOG_FILE"

    # Check if there are any changes (staged or unstaged)
    if git diff --quiet && git diff --cached --quiet; then
        # Check for untracked files
        if [ -n "$(git ls-files --others --exclude-standard)" ]; then
            log_info "Untracked files detected"
            git status --short | tee -a "$LOG_FILE"
            return 0
        else
            log_warning "No changes detected"
            return 1
        fi
    fi

    log_info "Changes detected:"
    git status --short | tee -a "$LOG_FILE"

    return 0
}

# Commit changes
commit_changes() {
    log_info "Committing changes..."

    cd "$WORKTREE_PATH" || exit 3

    # Stage all changes
    git add -A

    # Create commit message
    COMMIT_MESSAGE="Task #$TASK_ID: $TASK_TITLE

Automated implementation by Lazy_Bird agent

Task URL: $TASK_URL
Complexity: $TASK_COMPLEXITY

🤖 Generated with Lazy_Bird automation
https://github.com/yusufkaraaslan/lazy-bird"

    # Commit
    if git commit -m "$COMMIT_MESSAGE"; then
        log_success "Changes committed"
        return 0
    else
        log_error "Failed to commit changes"
        return 1
    fi
}

# Push branch
push_branch() {
    log_info "Pushing branch to remote..."

    cd "$WORKTREE_PATH" || exit 3

    # Get remote name (usually 'origin')
    REMOTE=$(git remote | head -1)

    if [ -z "$REMOTE" ]; then
        log_error "No git remote configured"
        return 1
    fi

    # Push branch
    if git push -u "$REMOTE" "$BRANCH_NAME"; then
        log_success "Branch pushed: $BRANCH_NAME"
        return 0
    else
        log_error "Failed to push branch"
        return 1
    fi
}

# Create pull request
create_pr() {
    log_info "Creating pull request..."

    cd "$WORKTREE_PATH" || exit 3

    # Prepare PR body
    PR_BODY="## Automated Task Implementation

**Task**: #$TASK_ID - $TASK_TITLE
**Complexity**: $TASK_COMPLEXITY
**Original Issue**: $TASK_URL

---

### Implementation Details

$TASK_BODY

---

### Testing

Please review the changes and test:
1. Code compiles without errors
2. Functionality works as expected
3. No regressions introduced

### Logs

View agent logs: \`~/.config/lazy_birtd/logs/agent-task-$TASK_ID.log\`

---

🤖 **This PR was automatically generated by Lazy_Bird**
Agent completed: $(date)

For issues or questions about this automation:
https://github.com/yusufkaraaslan/lazy-bird"

    # Create PR using gh CLI
    if gh pr create \
        --title "Task #$TASK_ID: $TASK_TITLE" \
        --body "$PR_BODY" \
        --base main \
        --head "$BRANCH_NAME" \
        --label "automated"; then

        PR_URL=$(gh pr view "$BRANCH_NAME" --json url -q '.url')
        log_success "Pull request created: $PR_URL"

        # Comment on original issue with PR link
        if [ -n "$TASK_URL" ]; then
            ISSUE_NUM=$(echo "$TASK_URL" | grep -oE '[0-9]+$')
            if [ -n "$ISSUE_NUM" ]; then
                gh issue comment "$ISSUE_NUM" --body "✅ **Automated implementation complete**

Pull request created: $PR_URL

The agent has completed the implementation. Please review the PR and merge if satisfied.

View logs: \`~/.config/lazy_birtd/logs/agent-task-$TASK_ID.log\`"
            fi
        fi

        return 0
    else
        log_error "Failed to create pull request"
        return 1
    fi
}

# Cleanup worktree
cleanup_worktree() {
    log_info "Cleaning up worktree..."

    if [ -z "$WORKTREE_PATH" ]; then
        log_warning "WORKTREE_PATH not set, skipping cleanup"
        return 0
    fi

    cd "$GODOT_PROJECT_PATH" || return 1

    # Remove worktree
    if git worktree remove "$WORKTREE_PATH" --force 2>/dev/null; then
        log_success "Worktree removed: $WORKTREE_PATH"
    else
        # Fallback: force remove directory
        log_warning "git worktree remove failed, forcing directory removal"
        if rm -rf "$WORKTREE_PATH"; then
            log_success "Worktree directory removed"
            git worktree prune
        else
            log_error "Failed to remove worktree directory: $WORKTREE_PATH"
            log_error "Manual cleanup required: rm -rf $WORKTREE_PATH"
            return 1
        fi
    fi

    return 0
}

# Main execution
main() {
    log_info "Lazy_Bird Agent Runner v$VERSION"

    # Check arguments
    if [ $# -ne 1 ]; then
        usage
        exit 2
    fi

    if [ "$1" = "-h" ] || [ "$1" = "--help" ]; then
        usage
        exit 0
    fi

    TASK_FILE="$1"

    # Setup trap for cleanup
    trap cleanup_worktree EXIT

    # Initialization
    log_info "Step 1/8: Checking dependencies..."
    check_dependencies

    log_info "Step 2/8: Loading configuration..."
    load_config

    log_info "Step 3/8: Parsing task..."
    parse_task "$TASK_FILE"

    log_info "Step 3.5/8: Updating labels to 'in-process'..."
    update_labels_to_processing

    log_info "Step 4/8: Creating worktree..."
    create_worktree

    # Execute task
    log_info "Step 5/8: Running Claude Code..."
    if ! run_claude; then
        log_error "Claude execution failed"
        exit 1
    fi

    log_info "Step 6/8: Checking for changes..."
    if ! check_changes; then
        log_warning "No changes to commit, task may not have completed"
        exit 1
    fi

    log_info "Step 7/8: Committing and pushing..."
    if ! commit_changes; then
        log_error "Failed to commit changes"
        exit 1
    fi

    if ! push_branch; then
        log_error "Failed to push branch"
        exit 1
    fi

    log_info "Step 8/8: Creating pull request..."
    if ! create_pr; then
        log_error "Failed to create PR"
        exit 1
    fi

    log_info "Step 8.5/8: Updating labels to 'in-review'..."
    update_labels_to_review

    # Success!
    log_success "✅ Task #$TASK_ID completed successfully!"
    log_info "Branch: $BRANCH_NAME"
    log_info "Worktree: $WORKTREE_PATH (will be cleaned up)"
    log_info "Log file: $LOG_FILE"

    exit 0
}

# Run main
main "$@"
