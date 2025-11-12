#!/bin/bash
# Lazy_Bird Agent Runner
# Processes a single task in isolated git worktree

set -euo pipefail

# Ensure user local bin is in PATH for godot and other tools
export PATH="$HOME/.local/bin:$PATH"

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
    # Try new schema first (project.path), fallback to old schema (godot_project_path)
    PROJECT_PATH=$(grep -E "^  path:" "$config_file" | head -1 | sed 's/.*path: *//' | tr -d '"' || echo "")

    if [ -z "$PROJECT_PATH" ]; then
        # Fallback to old schema for backward compatibility
        PROJECT_PATH=$(grep -E "^godot_project_path:" "$config_file" | sed 's/godot_project_path: *//' | tr -d '"' || echo "")
    fi

    REPOSITORY=$(grep -E "^repository:" "$config_file" | sed 's/repository: *//' | tr -d '"' || echo "")

    if [ -z "$PROJECT_PATH" ]; then
        log_error "Project path not found in config (looked for 'project.path' or 'godot_project_path')"
        exit 2
    fi

    if [ ! -d "$PROJECT_PATH" ]; then
        log_error "Project path does not exist: $PROJECT_PATH"
        exit 2
    fi

    if [ ! -d "$PROJECT_PATH/.git" ]; then
        log_error "Not a git repository: $PROJECT_PATH"
        exit 2
    fi

    log_info "Project path: $PROJECT_PATH"
}

# Parse task JSON
parse_task() {
    local task_file="$1"

    if [ ! -f "$task_file" ]; then
        log_error "Task file not found: $task_file"
        exit 2
    fi

    # Basic task fields
    TASK_ID=$(jq -r '.issue_id' "$task_file")
    TASK_TITLE=$(jq -r '.title' "$task_file")
    TASK_BODY=$(jq -r '.body' "$task_file")
    TASK_COMPLEXITY=$(jq -r '.complexity // "medium"' "$task_file")
    TASK_URL=$(jq -r '.url' "$task_file")
    TASK_REPOSITORY=$(jq -r '.repository' "$task_file")

    # Phase 1.1: Project context
    PROJECT_ID=$(jq -r '.project_id // "default"' "$task_file")
    PROJECT_NAME=$(jq -r '.project_name // "Default Project"' "$task_file")
    PROJECT_TYPE=$(jq -r '.project_type // "unknown"' "$task_file")
    TASK_PROJECT_PATH=$(jq -r '.project_path // ""' "$task_file")

    # Phase 1.1: Project-specific commands (from task, not config)
    TASK_TEST_CMD=$(jq -r '.test_command // ""' "$task_file")
    TASK_BUILD_CMD=$(jq -r '.build_command // ""' "$task_file")
    TASK_LINT_CMD=$(jq -r '.lint_command // ""' "$task_file")

    if [ -z "$TASK_ID" ] || [ "$TASK_ID" = "null" ]; then
        log_error "Invalid task file: missing issue_id"
        exit 2
    fi

    # Phase 1.1: If task has project_path, use it directly (overrides config)
    if [ -n "$TASK_PROJECT_PATH" ] && [ "$TASK_PROJECT_PATH" != "null" ]; then
        PROJECT_PATH="$TASK_PROJECT_PATH"
        log_info "Using project path from task: $PROJECT_PATH"
    fi

    # Extract owner/repo from repository URL
    if [ -n "$TASK_REPOSITORY" ] && [ "$TASK_REPOSITORY" != "null" ]; then
        REPO_NAME=$(echo "$TASK_REPOSITORY" | sed -E 's|https?://github.com/||' | sed 's|\.git$||')
    else
        # Fallback to config if not in task
        REPO_NAME=$(echo "$REPOSITORY" | sed -E 's|https?://github.com/||' | sed 's|\.git$||')
    fi

    log_info "[$PROJECT_ID] Task #$TASK_ID: $TASK_TITLE"
    log_info "[$PROJECT_ID] Project: $PROJECT_NAME ($PROJECT_TYPE)"
    log_info "[$PROJECT_ID] Complexity: $TASK_COMPLEXITY"
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
    # Phase 1.1: Include project-id in branch and worktree names
    BRANCH_NAME="feature-$PROJECT_ID-$TASK_ID"
    WORKTREE_PATH="/tmp/lazy-bird-agent-$PROJECT_ID-$TASK_ID"

    log_info "[$PROJECT_ID] Creating worktree: $WORKTREE_PATH"

    cd "$PROJECT_PATH" || exit 3

    # Clean up existing worktree if it exists
    if [ -d "$WORKTREE_PATH" ]; then
        log_warning "[$PROJECT_ID] Worktree already exists, removing: $WORKTREE_PATH"
        git worktree remove "$WORKTREE_PATH" --force 2>/dev/null || rm -rf "$WORKTREE_PATH"
    fi

    # Check if branch exists (might be left over from previous run)
    if git show-ref --verify --quiet refs/heads/"$BRANCH_NAME"; then
        log_warning "[$PROJECT_ID] Branch already exists, deleting: $BRANCH_NAME"
        git branch -D "$BRANCH_NAME" 2>/dev/null || true
    fi

    # Create new worktree with new branch
    if git worktree add -b "$BRANCH_NAME" "$WORKTREE_PATH" HEAD; then
        log_success "[$PROJECT_ID] Worktree created successfully"
    else
        log_error "[$PROJECT_ID] Failed to create worktree"
        exit 3
    fi
}

# Initialize Godot project in worktree (gdUnit4 requires .godot directory)
initialize_godot_worktree() {
    # Only run for Godot projects
    if [ "$PROJECT_TYPE" != "godot" ]; then
        log_info "[$PROJECT_ID] Not a Godot project, skipping initialization"
        return 0
    fi

    log_info "[$PROJECT_ID] Initializing Godot project in worktree..."

    cd "$WORKTREE_PATH" || exit 3

    # Check if godot command is available
    if ! command -v godot &> /dev/null; then
        log_warning "[$PROJECT_ID] godot command not found, skipping initialization"
        return 0
    fi

    # Always run godot --editor --quit to initialize the project properly
    # This scans all scripts and registers global classes, which is required for gdUnit4
    log_info "[$PROJECT_ID] Running 'godot --editor --quit --headless' to scan scripts..."

    local godot_log="/tmp/godot-init-$$.log"
    if timeout 45 godot --editor --quit --headless > "$godot_log" 2>&1; then
        log_success "[$PROJECT_ID] Godot project initialized successfully"

        # Verify .godot directory was created
        if [ -d ".godot" ]; then
            log_success "[$PROJECT_ID] .godot directory created"

            # Verify critical files exist
            if [ -f ".godot/global_script_class_cache.cfg" ]; then
                log_success "[$PROJECT_ID] Plugin class cache generated"
            else
                log_warning "[$PROJECT_ID] Plugin class cache not found (tests may fail)"
            fi
        else
            log_warning "[$PROJECT_ID] .godot directory not created (tests may fail)"
        fi
    else
        log_warning "[$PROJECT_ID] Godot initialization had issues (tests may fail)"
        cat "$godot_log" || true
    fi

    return 0
}

# Run Claude Code
run_claude() {
    log_info "[$PROJECT_ID] Running Claude Code on task..."

    cd "$WORKTREE_PATH" || exit 3

    # Prepare prompt (Phase 1.1: include project context)
    CLAUDE_PROMPT="PROJECT: $PROJECT_NAME ($PROJECT_TYPE)
PROJECT ID: $PROJECT_ID

TASK: $TASK_TITLE

DETAILS:
$TASK_BODY

Implement this task following the detailed steps above. Make sure to:
1. Follow the acceptance criteria
2. Write clean, well-documented code
3. Test your changes
4. **IMPORTANT**: DO NOT commit your changes - the automation system will handle git operations

Work in the current directory: $WORKTREE_PATH

**DO NOT use git commit** - just make the file changes. The automation will commit and push."

    # Create log file (Phase 1.1: include project-id in filename)
    LOG_DIR="${LAZY_BIRD_LOG_DIR:-$HOME/.config/lazy_birtd/logs}"
    mkdir -p "$LOG_DIR"
    LOG_FILE="$LOG_DIR/agent-$PROJECT_ID-task-$TASK_ID.log"

    log_info "[$PROJECT_ID] Logging to: $LOG_FILE"
    echo "=== Agent Task #$TASK_ID (Project: $PROJECT_ID) ===" > "$LOG_FILE"
    echo "Started: $(date)" >> "$LOG_FILE"
    echo "Project: $PROJECT_NAME ($PROJECT_TYPE)" >> "$LOG_FILE"
    echo "Task: $TASK_TITLE" >> "$LOG_FILE"
    echo "Worktree: $WORKTREE_PATH" >> "$LOG_FILE"
    echo "" >> "$LOG_FILE"

    # Run Claude with safety restrictions
    # Use --allowedTools to restrict what Claude can do
    # Don't use --dangerously-skip-permissions unless in container
    log_info "[$PROJECT_ID] Executing Claude Code CLI..."

    if claude -p "$CLAUDE_PROMPT" \
        --allowedTools "Read,Write,Edit,Glob,Grep,Bash(git:*)" \
        2>&1 | tee -a "$LOG_FILE"; then

        CLAUDE_EXIT=0
        log_success "[$PROJECT_ID] Claude completed successfully"
    else
        CLAUDE_EXIT=$?
        log_error "[$PROJECT_ID] Claude failed with exit code: $CLAUDE_EXIT"
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

# Run lint command (optional)
run_lint() {
    log_info "[$PROJECT_ID] Running lint (if configured)..."

    # Phase 1.1: Use lint command from task (not config)
    local LINT_CMD="$TASK_LINT_CMD"

    if [ -z "$LINT_CMD" ] || [ "$LINT_CMD" = "null" ]; then
        log_info "[$PROJECT_ID] No lint command configured, skipping linting"
        return 0
    fi

    log_info "[$PROJECT_ID] Lint command: $LINT_CMD"

    cd "$WORKTREE_PATH" || exit 3

    # Execute lint
    if eval "$LINT_CMD" > "$LOG_DIR/lint-output.log" 2>&1; then
        log_success "[$PROJECT_ID] Lint passed"
        return 0
    else
        log_warning "[$PROJECT_ID] Lint failed (continuing anyway)"
        cat "$LOG_DIR/lint-output.log"
        return 0  # Don't fail build on lint errors
    fi
}

# Run test command
run_tests() {
    log_info "[$PROJECT_ID] Running tests..."

    # Phase 1.1: Use test command from task (not config)
    local TEST_CMD="$TASK_TEST_CMD"

    if [ -z "$TEST_CMD" ] || [ "$TEST_CMD" = "null" ]; then
        log_warning "[$PROJECT_ID] No test command configured, skipping tests"
        return 0
    fi

    log_info "[$PROJECT_ID] Test command: $TEST_CMD"

    cd "$WORKTREE_PATH" || exit 3

    # Execute tests
    if eval "$TEST_CMD" > "$LOG_DIR/test-output.log" 2>&1; then
        log_success "[$PROJECT_ID] Tests passed"
        return 0
    else
        log_error "[$PROJECT_ID] Tests failed"
        cat "$LOG_DIR/test-output.log"
        return 1
    fi
}

# Run build command (optional)
run_build() {
    log_info "[$PROJECT_ID] Running build (if configured)..."

    # Phase 1.1: Use build command from task (not config)
    local BUILD_CMD="$TASK_BUILD_CMD"

    if [ -z "$BUILD_CMD" ] || [ "$BUILD_CMD" = "null" ]; then
        log_info "[$PROJECT_ID] No build command configured, skipping build"
        return 0
    fi

    log_info "[$PROJECT_ID] Build command: $BUILD_CMD"

    cd "$WORKTREE_PATH" || exit 3

    # Execute build
    if eval "$BUILD_CMD" > "$LOG_DIR/build-output.log" 2>&1; then
        log_success "[$PROJECT_ID] Build succeeded"
        return 0
    else
        log_error "[$PROJECT_ID] Build failed"
        cat "$LOG_DIR/build-output.log"
        return 1
    fi
}

# Commit changes
commit_changes() {
    log_info "[$PROJECT_ID] Committing changes..."

    cd "$WORKTREE_PATH" || exit 3

    # Stage all changes
    git add -A

    # Create commit message (Phase 1.1: include project context)
    COMMIT_MESSAGE="[$PROJECT_ID] Task #$TASK_ID: $TASK_TITLE

Automated implementation by Lazy_Bird agent

Project: $PROJECT_NAME ($PROJECT_TYPE)
Task URL: $TASK_URL
Complexity: $TASK_COMPLEXITY

🤖 Generated with Lazy_Bird automation
https://github.com/yusufkaraaslan/lazy-bird"

    # Commit
    if git commit -m "$COMMIT_MESSAGE"; then
        log_success "[$PROJECT_ID] Changes committed"
        return 0
    else
        log_error "[$PROJECT_ID] Failed to commit changes"
        return 1
    fi
}

# Push branch
push_branch() {
    log_info "[$PROJECT_ID] Pushing branch to remote..."

    cd "$WORKTREE_PATH" || exit 3

    # Get remote name (usually 'origin')
    REMOTE=$(git remote | head -1)

    if [ -z "$REMOTE" ]; then
        log_error "[$PROJECT_ID] No git remote configured"
        return 1
    fi

    # Push branch
    if git push -u "$REMOTE" "$BRANCH_NAME"; then
        log_success "[$PROJECT_ID] Branch pushed: $BRANCH_NAME"
        return 0
    else
        log_error "[$PROJECT_ID] Failed to push branch"
        return 1
    fi
}

# Create pull request
create_pr() {
    log_info "[$PROJECT_ID] Creating pull request..."

    cd "$WORKTREE_PATH" || exit 3

    # Prepare PR body (Phase 1.1: include project context)
    PR_BODY="## Automated Task Implementation

**Project**: $PROJECT_NAME ($PROJECT_TYPE)
**Project ID**: $PROJECT_ID
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

View agent logs: \`~/.config/lazy_birtd/logs/agent-$PROJECT_ID-task-$TASK_ID.log\`

---

🤖 **This PR was automatically generated by Lazy_Bird**
Agent completed: $(date)

For issues or questions about this automation:
https://github.com/yusufkaraaslan/lazy-bird"

    # Create PR using gh CLI
    if gh pr create \
        --title "[$PROJECT_ID] Task #$TASK_ID: $TASK_TITLE" \
        --body "$PR_BODY" \
        --base main \
        --head "$BRANCH_NAME" \
        --label "automated"; then

        PR_URL=$(gh pr view "$BRANCH_NAME" --json url -q '.url')
        log_success "[$PROJECT_ID] Pull request created: $PR_URL"

        # Comment on original issue with PR link
        if [ -n "$TASK_URL" ]; then
            ISSUE_NUM=$(echo "$TASK_URL" | grep -oE '[0-9]+$')
            if [ -n "$ISSUE_NUM" ]; then
                gh issue comment "$ISSUE_NUM" --body "✅ **Automated implementation complete**

Pull request created: $PR_URL

The agent has completed the implementation. Please review the PR and merge if satisfied.

View logs: \`~/.config/lazy_birtd/logs/agent-$PROJECT_ID-task-$TASK_ID.log\`"
            fi
        fi

        return 0
    else
        log_error "[$PROJECT_ID] Failed to create pull request"
        return 1
    fi
}

# Cleanup worktree
cleanup_worktree() {
    # Use PROJECT_ID if set, otherwise use generic message
    local prefix="${PROJECT_ID:+[$PROJECT_ID] }"

    log_info "${prefix}Cleaning up worktree..."

    if [ -z "${WORKTREE_PATH:-}" ]; then
        log_warning "${prefix}WORKTREE_PATH not set, skipping cleanup"
        return 0
    fi

    if [ -z "${PROJECT_PATH:-}" ]; then
        log_warning "${prefix}PROJECT_PATH not set, skipping cleanup"
        return 0
    fi

    cd "$PROJECT_PATH" || return 1

    # Remove worktree
    if git worktree remove "$WORKTREE_PATH" --force 2>/dev/null; then
        log_success "${prefix}Worktree removed: $WORKTREE_PATH"
    else
        # Fallback: force remove directory
        log_warning "${prefix}git worktree remove failed, forcing directory removal"
        if rm -rf "$WORKTREE_PATH"; then
            log_success "${prefix}Worktree directory removed"
            git worktree prune
        else
            log_error "${prefix}Failed to remove worktree directory: $WORKTREE_PATH"
            log_error "${prefix}Manual cleanup required: rm -rf $WORKTREE_PATH"
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
    log_info "Step 1/11: Checking dependencies..."
    check_dependencies

    log_info "Step 2/11: Parsing task..."
    parse_task "$TASK_FILE"

    # Phase 1.1: Only load config if task doesn't have project_path
    if [ -z "$PROJECT_PATH" ]; then
        log_info "Step 3/11: Loading configuration..."
        load_config
    else
        log_info "Step 3/11: Using project path from task (skipping config load)"
    fi

    log_info "Step 3.5/11: Updating labels to 'in-process'..."
    update_labels_to_processing

    log_info "Step 4/11: Creating worktree..."
    create_worktree

    log_info "Step 4.5/11: Initializing Godot worktree..."
    initialize_godot_worktree

    # Execute task
    log_info "Step 5/11: Running Claude Code..."
    if ! run_claude; then
        log_error "Claude execution failed"
        exit 1
    fi

    log_info "Step 6/11: Checking for changes..."
    if ! check_changes; then
        log_warning "No changes to commit, task may not have completed"
        exit 1
    fi

    log_info "Step 7/11: Running lint..."
    if ! run_lint; then
        log_error "Lint failed"
        # Continue anyway - lint is optional
    fi

    log_info "Step 8/11: Running tests..."
    if ! run_tests; then
        log_error "Tests failed"
        exit 1
    fi

    log_info "Step 9/11: Running build..."
    if ! run_build; then
        log_error "Build failed"
        exit 1
    fi

    log_info "Step 10/11: Committing and pushing..."
    if ! commit_changes; then
        log_error "Failed to commit changes"
        exit 1
    fi

    if ! push_branch; then
        log_error "Failed to push branch"
        exit 1
    fi

    log_info "Step 11/11: Creating pull request..."
    if ! create_pr; then
        log_error "Failed to create PR"
        exit 1
    fi

    log_info "Step 11.5/11: Updating labels to 'in-review'..."
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
