# Lazy-Bird v2.0 End-to-End Tests

## Overview

The E2E test suite verifies the complete lazy-bird v2.0 workflow from database operations through Godot test execution.

## Requirements

**Critical:** These tests require **PostgreSQL** (not SQLite) because the models use PostgreSQL-specific types (JSONB).

### System Requirements:
- Python 3.8+
- PostgreSQL 13+ (running)
- Godot 4.5+ 
- gdUnit4 test framework
- Git with lazy_bied_test project cloned

### Python Dependencies:
- lazy-bird package (installed in editable mode)
- alembic
- sqlalchemy[asyncio]
- asyncpg (PostgreSQL async driver)

## Running the Tests

### Method 1: Docker PostgreSQL (Recommended - No Installation Required)

The easiest way to run E2E tests is using Docker:

```bash
# 1. Start PostgreSQL container
./tests/e2e/start-test-db.sh

# 2. Run E2E test (copy the command from start-test-db.sh output)
export DATABASE_URL="postgresql+asyncpg://postgres:testpassword123@localhost:5433/lazy_bird_e2e_test"
./tests/e2e/test_full_workflow.sh

# 3. Clean up when done
./tests/e2e/stop-test-db.sh
```

**One-liner:**
```bash
./tests/e2e/start-test-db.sh && \
export DATABASE_URL="postgresql+asyncpg://postgres:testpassword123@localhost:5433/lazy_bird_e2e_test" && \
./tests/e2e/test_full_workflow.sh
```

### Method 2: System PostgreSQL (If Already Installed)

If you have PostgreSQL installed system-wide:

```bash
# Start PostgreSQL (systemd)
sudo systemctl start postgresql

# Create test database
sudo -u postgres createdb lazy_bird_e2e_test

# Set DATABASE_URL
export DATABASE_URL="postgresql+asyncpg://postgres:password@localhost/lazy_bird_e2e_test"

# Run test
./tests/e2e/test_full_workflow.sh
```

## What the Test Does

1. **Prerequisites Check**: Verifies python3, godot, and test project exist
2. **Virtual Environment**: Creates isolated venv with lazy-bird installed
3. **Database Setup**: Runs Alembic migrations and creates tables
4. **Framework Preset**: Creates Godot framework preset
5. **Test Project**: Creates test project record in database
6. **Task Queue**: Queues a test task
7. **Database Verification**: Counts records to verify persistence
8. **Godot Tests**: Runs gdUnit4 tests from lazy_bied_test project
9. **Cleanup**: Removes venv and temp files

## Known Limitations

- **PostgreSQL Only**: SQLite is not supported due to JSONB type usage
- **Requires lazy_bied_test**: Must have test Godot project at ../lazy_bied_test
- **Alembic Async Issue**: Alembic migrations may fail with aiosqlite (expected, fallback to manual table creation)

## Test Output

- **Exit Code 0**: All tests passed
- **Exit Code 1**: Test failed (check log file)
- **Log File**: `/tmp/lazy-bird-e2e-test-TIMESTAMP.log`

## Troubleshooting

### "ModuleNotFoundError: No module named 'lazy_bird'"
- Ensure you're running from the project root
- Verify lazy-bird is installed: `pip list | grep lazy-bird`

### "no such table: framework_presets"
- Check DATABASE_URL points to PostgreSQL (not SQLite)
- Verify PostgreSQL is running: `systemctl status postgresql`
- Check migrations ran: `alembic current`

### "JSONB type not supported"
- You're using SQLite - switch to PostgreSQL
- Update DATABASE_URL to use postgresql+asyncpg://

### "gdUnit4 not found"
- Clone lazy_bied_test project: `git clone https://github.com/yusufkaraaslan/lazy_bied_test`
- Verify gdUnit4 exists: `ls ../lazy_bied_test/addons/gdUnit4`

## Future Improvements

1. Add Docker Compose setup for PostgreSQL (automated)
2. Add cleanup of test database after run
3. Add more assertion checks on test results
4. Add webhook event verification
5. Add task run log verification
