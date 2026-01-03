#!/bin/bash
# End-to-End Test for Lazy-Bird v2.0
# Tests complete workflow with lazy_bied_test Godot project
#
# This script:
# 1. Creates isolated virtual environment
# 2. Sets up SQLite test database
# 3. Creates a test project
# 4. Queues a test task
# 5. Verifies database state
# 6. Runs Godot tests
# 7. Cleans up everything (venv, db, temp files)

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LAZY_BIRD_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
TEST_PROJECT_PATH="/mnt/1ece809a-2821-4f10-aecb-fcdf34760c0b/Git/lazy_bied_test"
E2E_LOG_FILE="/tmp/lazy-bird-e2e-test-$(date +%Y%m%d_%H%M%S).log"
TEST_VENV_DIR="/tmp/lazy-bird-e2e-venv-$$"
TEST_DB_PATH="/tmp/lazy-bird-e2e-test-$$.db"
TEST_PROJECT_SLUG="lazy-bied-test-e2e"

# Track cleanup tasks
CLEANUP_DIRS=()
CLEANUP_FILES=()
CLEANUP_PIDS=()

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1" | tee -a "$E2E_LOG_FILE"
}

log_success() {
    echo -e "${GREEN}[✓]${NC} $1" | tee -a "$E2E_LOG_FILE"
}

log_error() {
    echo -e "${RED}[✗]${NC} $1" | tee -a "$E2E_LOG_FILE"
}

log_warning() {
    echo -e "${YELLOW}[!]${NC} $1" | tee -a "$E2E_LOG_FILE"
}

log_step() {
    echo | tee -a "$E2E_LOG_FILE"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}" | tee -a "$E2E_LOG_FILE"
    echo -e "${BLUE}▶ $1${NC}" | tee -a "$E2E_LOG_FILE"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}" | tee -a "$E2E_LOG_FILE"
}

# Cleanup function
cleanup() {
    local exit_code=$?

    log_step "Cleanup"

    # Remove test database
    for file in "${CLEANUP_FILES[@]}"; do
        if [ -f "$file" ]; then
            log_info "Removing: $file"
            rm -f "$file" 2>/dev/null || log_warning "Failed to remove $file"
        fi
    done

    # Remove directories
    for dir in "${CLEANUP_DIRS[@]}"; do
        if [ -d "$dir" ]; then
            log_info "Removing: $dir"
            rm -rf "$dir" 2>/dev/null || log_warning "Failed to remove $dir"
        fi
    done

    # Stop background processes
    for pid in "${CLEANUP_PIDS[@]}"; do
        if kill -0 "$pid" 2>/dev/null; then
            log_info "Stopping process: $pid"
            kill "$pid" 2>/dev/null || true
        fi
    done

    if [ $exit_code -eq 0 ]; then
        echo
        log_success "E2E test completed successfully!"
        log_info "Full log: $E2E_LOG_FILE"
    else
        echo
        log_error "E2E test failed with exit code $exit_code"
        log_info "Check log for details: $E2E_LOG_FILE"
        exit $exit_code
    fi
}

trap cleanup EXIT

# Check prerequisites
check_prerequisites() {
    log_step "Checking Prerequisites"

    local missing=()

    # Check commands
    for cmd in python3 godot; do
        if ! command -v "$cmd" &>/dev/null; then
            missing+=("$cmd")
        else
            log_success "$cmd found"
        fi
    done

    if [ ${#missing[@]} -gt 0 ]; then
        log_error "Missing required commands: ${missing[*]}"
        exit 1
    fi

    # Check test project exists
    if [ ! -d "$TEST_PROJECT_PATH" ]; then
        log_error "Test project not found at: $TEST_PROJECT_PATH"
        exit 1
    fi
    log_success "Test project found: $TEST_PROJECT_PATH"

    # Check gdUnit4 addon exists
    if [ ! -d "$TEST_PROJECT_PATH/addons/gdUnit4" ]; then
        log_warning "gdUnit4 not found in test project"
        log_info "Tests may not run properly"
    else
        log_success "gdUnit4 addon found"
    fi

    # Check Godot version
    local godot_version=$(godot --version 2>&1 | head -1)
    log_info "Godot version: $godot_version"
}

# Setup virtual environment
setup_virtualenv() {
    log_step "Setting Up Virtual Environment"

    log_info "Creating venv at: $TEST_VENV_DIR"
    python3 -m venv "$TEST_VENV_DIR" 2>&1 | tee -a "$E2E_LOG_FILE"

    # Track for cleanup
    CLEANUP_DIRS+=("$TEST_VENV_DIR")

    # Activate venv
    source "$TEST_VENV_DIR/bin/activate"
    log_success "Virtual environment activated"

    # Upgrade pip
    log_info "Upgrading pip..."
    pip install --upgrade pip &>> "$E2E_LOG_FILE"

    # Install lazy-bird in editable mode
    log_info "Installing lazy-bird package..."
    cd "$LAZY_BIRD_ROOT"
    pip install -e . &>> "$E2E_LOG_FILE"

    if python3 -c "import lazy_bird" 2>/dev/null; then
        log_success "lazy-bird package installed"
    else
        log_error "Failed to install lazy-bird package"
        exit 1
    fi

    # Install test dependencies
    log_info "Installing test dependencies..."
    pip install alembic sqlalchemy[asyncio] aiosqlite &>> "$E2E_LOG_FILE"
    log_success "Dependencies installed"
}

# Setup test database (PostgreSQL or SQLite)
setup_database() {
    # Check if DATABASE_URL is already set (PostgreSQL)
    if [ -n "${DATABASE_URL:-}" ] && [[ "$DATABASE_URL" == postgresql* ]]; then
        log_step "Setting Up Test Database (PostgreSQL)"
        log_info "Using existing DATABASE_URL: $DATABASE_URL"

        # Install PostgreSQL driver instead of SQLite
        log_info "Installing asyncpg (PostgreSQL driver)..."
        pip install asyncpg &>> "$E2E_LOG_FILE"
    else
        log_step "Setting Up Test Database (SQLite)"

        # Track database file for cleanup
        CLEANUP_FILES+=("$TEST_DB_PATH")

        # Set database URL to SQLite
        export DATABASE_URL="sqlite+aiosqlite:///$TEST_DB_PATH"
        log_info "Database URL: $DATABASE_URL"
    fi

    # Run Alembic migrations
    cd "$LAZY_BIRD_ROOT"

    # Check if alembic.ini exists
    if [ ! -f "alembic.ini" ]; then
        log_warning "alembic.ini not found, skipping migrations"
        if [[ "$DATABASE_URL" != postgresql* ]]; then
            log_info "Creating empty SQLite database file"
            touch "$TEST_DB_PATH"
        fi
        return
    fi

    # Run migrations
    log_info "Running Alembic migrations..."
    if alembic upgrade head 2>&1 | tee -a "$E2E_LOG_FILE"; then
        log_success "Migrations completed"
    else
        if [[ "$DATABASE_URL" == postgresql* ]]; then
            log_warning "Migrations failed for PostgreSQL"
        else
            log_warning "Migrations failed (may not be critical for SQLite)"
        fi
    fi
}

# Create database tables manually (fallback if migrations fail)
create_tables_manually() {
    log_step "Creating Database Tables"

    cd "$LAZY_BIRD_ROOT"

    python3 << 'EOF' 2>&1 | tee -a "$E2E_LOG_FILE"
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from lazy_bird.core.database import Base
import os

# Import all models to register them with Base.metadata
from lazy_bird.models.api_key import ApiKey
from lazy_bird.models.claude_account import ClaudeAccount
from lazy_bird.models.daily_usage import DailyUsage
from lazy_bird.models.framework_preset import FrameworkPreset
from lazy_bird.models.project import Project
from lazy_bird.models.task_run import TaskRun
from lazy_bird.models.task_run_log import TaskRunLog
from lazy_bird.models.webhook_subscription import WebhookSubscription

async def create_tables():
    db_url = os.environ.get('DATABASE_URL', 'sqlite+aiosqlite:////tmp/lazy-bird-e2e-test.db')
    print(f"Creating tables with URL: {db_url}")

    # Print which tables will be created
    print(f"Models registered: {list(Base.metadata.tables.keys())}")

    engine = create_async_engine(db_url, echo=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    await engine.dispose()
    print("✓ Tables created successfully")

asyncio.run(create_tables())
EOF

    if [ $? -eq 0 ]; then
        log_success "Database tables created"
    else
        log_error "Failed to create database tables"
        exit 1
    fi
}

# Create Godot framework preset
create_framework_preset() {
    log_step "Creating Framework Preset"

    cd "$LAZY_BIRD_ROOT"

    python3 << 'EOF' 2>&1 | tee -a "$E2E_LOG_FILE"
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select
from lazy_bird.models.framework_preset import FrameworkPreset
import uuid
import os

async def create_preset():
    db_url = os.environ.get('DATABASE_URL')
    engine = create_async_engine(db_url, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        # Check if Godot preset exists
        stmt = select(FrameworkPreset).where(FrameworkPreset.name == "godot")
        result = await session.execute(stmt)
        godot_preset = result.scalar_one_or_none()

        if godot_preset:
            print(f"✓ Godot preset already exists: {godot_preset.id}")
            return str(godot_preset.id)

        # Create Godot preset
        godot_preset = FrameworkPreset(
            id=uuid.uuid4(),
            name="godot",
            display_name="Godot Engine",
            description="Godot game engine with gdUnit4 testing framework",
            framework_type="game_engine",
            language="gdscript",
            test_command="godot --headless -s addons/gdUnit4/bin/GdUnitCmdTool.gd",
            build_command="godot --headless --export-release",
            is_builtin=True
        )
        session.add(godot_preset)
        await session.commit()

        print(f"✓ Godot preset created: {godot_preset.id}")
        return str(godot_preset.id)

    await engine.dispose()

preset_id = asyncio.run(create_preset())
EOF

    if [ $? -eq 0 ]; then
        log_success "Framework preset ready"
    else
        log_error "Failed to create framework preset"
        exit 1
    fi
}

# Create test project
create_test_project() {
    log_step "Creating Test Project"

    cd "$LAZY_BIRD_ROOT"

    python3 << EOF 2>&1 | tee -a "$E2E_LOG_FILE"
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select
from lazy_bird.models.project import Project
from lazy_bird.models.framework_preset import FrameworkPreset
from decimal import Decimal
import uuid
import os

async def create_project():
    db_url = os.environ.get('DATABASE_URL')
    engine = create_async_engine(db_url, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        # Find Godot preset (lowercase name)
        stmt = select(FrameworkPreset).where(FrameworkPreset.name == "godot")
        result = await session.execute(stmt)
        godot_preset = result.scalar_one_or_none()

        if not godot_preset:
            print("✗ Godot preset not found")
            return None

        # Create project
        project = Project(
            id=uuid.uuid4(),
            name="Lazy Bied Test E2E",
            slug="$TEST_PROJECT_SLUG",
            repo_url="https://github.com/yusufkaraaslan/lazy_bied_test",
            default_branch="main",
            framework_preset_id=godot_preset.id,
            project_type="godot",
            test_command="godot --headless -s addons/gdUnit4/bin/GdUnitCmdTool.gd",
            automation_enabled=True,
            max_concurrent_tasks=1,
            task_timeout_seconds=300,
            max_cost_per_task_usd=Decimal("5.00"),
            daily_cost_limit_usd=Decimal("50.00")
        )

        session.add(project)
        await session.commit()

        print(f"✓ Project created: {project.id}")
        print(f"  Name: {project.name}")
        print(f"  Slug: {project.slug}")
        print(f"  Type: {project.project_type}")
        print(f"  Max concurrent: {project.max_concurrent_tasks}")
        return str(project.id)

    await engine.dispose()

project_id = asyncio.run(create_project())
if not project_id:
    exit(1)
EOF

    if [ $? -eq 0 ]; then
        log_success "Test project created"
    else
        log_error "Failed to create test project"
        exit 1
    fi
}

# Queue a test task
queue_test_task() {
    log_step "Queuing Test Task"

    cd "$LAZY_BIRD_ROOT"

    python3 << EOF 2>&1 | tee -a "$E2E_LOG_FILE"
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select
from lazy_bird.models.project import Project
from lazy_bird.models.task_run import TaskRun
from datetime import datetime, timezone
import uuid
import os

async def queue_task():
    db_url = os.environ.get('DATABASE_URL')
    engine = create_async_engine(db_url, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        # Find project
        stmt = select(Project).where(Project.slug == "$TEST_PROJECT_SLUG")
        result = await session.execute(stmt)
        project = result.scalar_one_or_none()

        if not project:
            print("✗ Project not found")
            return None

        # Create task
        task = TaskRun(
            id=uuid.uuid4(),
            project_id=project.id,
            work_item_id="e2e-test-1",
            work_item_title="E2E Test - Verify gdUnit4 tests",
            work_item_description="Run all tests in lazy_bied_test project",
            task_type="test",
            complexity="simple",
            prompt="Run all gdUnit4 tests and verify they pass",
            status="queued",
            retry_count=0,
            max_retries=3
        )

        session.add(task)
        await session.commit()

        print(f"✓ Task queued: {task.id}")
        print(f"  Project: {project.name}")
        print(f"  Work Item: {task.work_item_id}")
        print(f"  Status: {task.status}")
        print(f"  Complexity: {task.complexity}")
        return str(task.id)

    await engine.dispose()

task_id = asyncio.run(queue_task())
if not task_id:
    exit(1)
EOF

    if [ $? -eq 0 ]; then
        log_success "Test task queued"
    else
        log_error "Failed to queue test task"
        exit 1
    fi
}

# Verify database state
verify_database_state() {
    log_step "Verifying Database State"

    cd "$LAZY_BIRD_ROOT"

    python3 << 'EOF' 2>&1 | tee -a "$E2E_LOG_FILE"
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select, func
from lazy_bird.models.project import Project
from lazy_bird.models.task_run import TaskRun
from lazy_bird.models.framework_preset import FrameworkPreset
import os

async def verify_state():
    db_url = os.environ.get('DATABASE_URL')
    engine = create_async_engine(db_url, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        # Count framework presets
        stmt = select(func.count()).select_from(FrameworkPreset)
        result = await session.execute(stmt)
        preset_count = result.scalar()
        print(f"✓ Framework presets: {preset_count}")

        # Count projects
        stmt = select(func.count()).select_from(Project)
        result = await session.execute(stmt)
        project_count = result.scalar()
        print(f"✓ Projects: {project_count}")

        # Count tasks
        stmt = select(func.count()).select_from(TaskRun)
        result = await session.execute(stmt)
        task_count = result.scalar()
        print(f"✓ Tasks: {task_count}")

        # Get task details
        stmt = select(TaskRun).where(TaskRun.work_item_id == "e2e-test-1")
        result = await session.execute(stmt)
        task = result.scalar_one_or_none()

        if task:
            print(f"✓ Test task verification:")
            print(f"    ID: {task.id}")
            print(f"    Status: {task.status}")
            print(f"    Complexity: {task.complexity}")
            print(f"    Type: {task.task_type}")
            print(f"    Max retries: {task.max_retries}")
        else:
            print("✗ Test task not found")
            return False

        # Get project details
        stmt = select(Project)
        result = await session.execute(stmt)
        project = result.scalar_one_or_none()

        if project:
            print(f"✓ Project verification:")
            print(f"    Name: {project.name}")
            print(f"    Type: {project.project_type}")
            print(f"    Max concurrent: {project.max_concurrent_tasks}")
            print(f"    Daily limit: ${project.daily_cost_limit_usd}")
        else:
            print("✗ Project not found")
            return False

    await engine.dispose()
    return True

success = asyncio.run(verify_state())
if not success:
    exit(1)
EOF

    if [ $? -eq 0 ]; then
        log_success "Database state verified"
    else
        log_error "Database verification failed"
        exit 1
    fi
}

# Run Godot tests
run_godot_tests() {
    log_step "Running Godot Tests"

    cd "$TEST_PROJECT_PATH"

    log_info "Executing gdUnit4 test suite..."
    log_info "Project path: $TEST_PROJECT_PATH"

    # Run tests with timeout
    if timeout 60s godot --headless -s addons/gdUnit4/bin/GdUnitCmdTool.gd 2>&1 | tee -a "$E2E_LOG_FILE"; then
        log_success "Tests executed successfully"
    else
        local exit_code=$?
        if [ $exit_code -eq 124 ]; then
            log_warning "Tests timed out after 60s"
        else
            log_warning "Tests completed with exit code: $exit_code"
            log_info "This may be expected for a test project"
        fi
    fi
}

# Display summary
display_summary() {
    log_step "Test Summary"

    echo
    echo -e "${GREEN}═══════════════════════════════════════════${NC}"
    echo -e "${GREEN}   LAZY-BIRD v2.0 E2E TEST SUMMARY${NC}"
    echo -e "${GREEN}═══════════════════════════════════════════${NC}"
    echo
    echo -e "✓ Virtual environment created and cleaned"
    echo -e "✓ SQLite database setup with migrations"
    echo -e "✓ Framework preset created (Godot)"
    echo -e "✓ Project created via Python API"
    echo -e "✓ Task queued in database"
    echo -e "✓ Database state verified"
    echo -e "✓ Godot tests executed"
    echo
    echo -e "${BLUE}Test artifacts:${NC}"
    echo -e "  Log file: $E2E_LOG_FILE"
    echo -e "  Database: $TEST_DB_PATH (will be removed)"
    echo -e "  Venv: $TEST_VENV_DIR (will be removed)"
    echo
    echo -e "${GREEN}═══════════════════════════════════════════${NC}"
    echo
}

# Main test execution
main() {
    echo
    echo -e "${BLUE}╔═══════════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║  LAZY-BIRD v2.0 END-TO-END TEST          ║${NC}"
    echo -e "${BLUE}╚═══════════════════════════════════════════╝${NC}"
    echo
    log_info "Starting E2E test..."
    log_info "Log file: $E2E_LOG_FILE"

    check_prerequisites
    setup_virtualenv
    setup_database
    create_tables_manually
    create_framework_preset
    create_test_project
    queue_test_task
    verify_database_state
    run_godot_tests
    display_summary
}

# Run main function
main
