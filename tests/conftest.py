"""
Pytest configuration and shared fixtures for lazy-bird tests
"""

import pytest
import tempfile
import shutil
from pathlib import Path
from typing import Dict, Any
from unittest.mock import Mock, MagicMock


@pytest.fixture
def temp_dir():
    """Create a temporary directory for test files"""
    temp_path = Path(tempfile.mkdtemp())
    yield temp_path
    # Cleanup
    if temp_path.exists():
        shutil.rmtree(temp_path)


@pytest.fixture
def mock_config():
    """Mock lazy-bird configuration"""
    return {
        "project_type": "python",
        "project_path": "/tmp/test-project",
        "git_platform": "github",
        "repository": "user/repo",
        "test_command": "pytest",
        "build_command": None,
        "lint_command": "flake8",
        "docker": {"enabled": True, "memory_limit": "2G"},
        "godot_server": {"enabled": True, "port": 5000, "host": "127.0.0.1"},
    }


@pytest.fixture
def mock_project_config():
    """Mock project configuration for multi-project tests"""
    return {
        "id": "test-project",
        "name": "Test Project",
        "type": "python",
        "path": "/tmp/test-project",
        "repository": "user/test-project",
        "git_platform": "github",
        "test_command": "pytest",
        "build_command": "python -m build",
        "lint_command": "flake8",
        "enabled": True,
    }


@pytest.fixture
def mock_multi_project_config(mock_project_config):
    """Mock configuration with multiple projects"""
    return {
        "projects": [
            mock_project_config,
            {
                "id": "godot-game",
                "name": "Godot Game",
                "type": "godot",
                "path": "/tmp/godot-game",
                "repository": "user/godot-game",
                "git_platform": "github",
                "test_command": "godot --headless -s addons/gdUnit4/bin/GdUnitCmdTool.gd",
                "enabled": True,
            },
            {
                "id": "django-backend",
                "name": "Django Backend",
                "type": "django",
                "path": "/tmp/django-backend",
                "repository": "user/django-backend",
                "git_platform": "gitlab",
                "test_command": "pytest",
                "lint_command": "pylint",
                "enabled": False,
            },
        ],
        "global": {"poll_interval": 60, "max_retries": 3, "timeout": 300},
    }


@pytest.fixture
def mock_github_issue():
    """Mock GitHub issue response"""
    return {
        "number": 42,
        "title": "[Task]: Add player health system",
        "body": "## Task Description\nAdd health tracking to player\n\n## Detailed Steps\n1. Add health variable\n2. Add take_damage method\n\n## Acceptance Criteria\n- [ ] Health starts at 100\n- [ ] Damage reduces health\n\n## Complexity\nmedium",
        "state": "open",
        "labels": [{"name": "ready"}],
        "created_at": "2025-11-29T10:00:00Z",
        "updated_at": "2025-11-29T10:00:00Z",
        "html_url": "https://github.com/user/repo/issues/42",
    }


@pytest.fixture
def mock_gitlab_issue():
    """Mock GitLab issue response"""
    return {
        "iid": 42,
        "title": "[Task]: Add player health system",
        "description": "## Task Description\nAdd health tracking to player",
        "state": "opened",
        "labels": ["ready"],
        "created_at": "2025-11-29T10:00:00Z",
        "updated_at": "2025-11-29T10:00:00Z",
        "web_url": "https://gitlab.com/user/repo/-/issues/42",
    }


@pytest.fixture
def mock_test_job():
    """Mock Godot server test job"""
    return {
        "id": "job-12345",
        "project_path": "/tmp/test-project",
        "test_suite": "res://tests/test_player.gd",
        "status": "queued",
        "created_at": "2025-11-29T10:00:00",
        "timeout": 300,
    }


@pytest.fixture
def mock_flask_app():
    """Mock Flask app for testing"""
    from flask import Flask

    app = Flask(__name__)
    app.config["TESTING"] = True
    return app


@pytest.fixture
def mock_requests(monkeypatch):
    """Mock requests library"""
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"status": "ok"}

    mock_get = Mock(return_value=mock_response)
    mock_post = Mock(return_value=mock_response)

    monkeypatch.setattr("requests.get", mock_get)
    monkeypatch.setattr("requests.post", mock_post)

    return {"get": mock_get, "post": mock_post, "response": mock_response}


@pytest.fixture
def mock_subprocess(monkeypatch):
    """Mock subprocess calls"""
    mock_result = Mock()
    mock_result.returncode = 0
    mock_result.stdout = "Success"
    mock_result.stderr = ""

    mock_run = Mock(return_value=mock_result)
    mock_call = Mock(return_value=0)

    monkeypatch.setattr("subprocess.run", mock_run)
    monkeypatch.setattr("subprocess.call", mock_call)

    return {"run": mock_run, "call": mock_call, "result": mock_result}


@pytest.fixture
def secrets_dir(temp_dir):
    """Create a mock secrets directory with API token"""
    secrets_path = temp_dir / ".config" / "lazy_birtd" / "secrets"
    secrets_path.mkdir(parents=True, exist_ok=True)

    # Create mock API token
    token_file = secrets_path / "api_token"
    token_file.write_text("ghp_mock_token_12345")
    token_file.chmod(0o600)

    return secrets_path


@pytest.fixture
def mock_package_root(temp_dir):
    """Mock PACKAGE_ROOT directory structure"""
    # Create directory structure
    (temp_dir / "scripts").mkdir(parents=True)
    (temp_dir / "config").mkdir(parents=True)
    (temp_dir / "web").mkdir(parents=True)

    # Create mock wizard script
    wizard = temp_dir / "wizard.sh"
    wizard.write_text('#!/bin/bash\necho "Mock wizard"')
    wizard.chmod(0o755)

    # Create mock scripts
    (temp_dir / "scripts" / "godot-server.py").write_text(
        '#!/usr/bin/env python3\nprint("Mock godot server")'
    )
    (temp_dir / "scripts" / "issue-watcher.py").write_text(
        '#!/usr/bin/env python3\nprint("Mock issue watcher")'
    )
    (temp_dir / "scripts" / "project-manager.py").write_text(
        '#!/usr/bin/env python3\nprint("Mock project manager")'
    )

    return temp_dir


# ============================================================================
# FastAPI / API Testing Fixtures
# ============================================================================


def _create_sqlite_compatible_tables(connection):
    """Create tables in SQLite by stripping PostgreSQL-specific features.

    The models use PG-specific types (ARRAY, JSONB, UUID, TSVECTOR, etc.)
    and PG-specific server_defaults (gen_random_uuid). This function builds
    a clean MetaData with SQLite-compatible types.
    """
    from sqlalchemy import MetaData, Table, Column, String, JSON, Text
    import sqlalchemy.dialects.postgresql as pg_types

    from lazy_bird.core.database import Base
    # Import all models so they register with Base.metadata
    import lazy_bird.models  # noqa: F401

    # Map PG-specific types to SQLite-compatible equivalents
    PG_TYPE_MAP = {
        pg_types.ARRAY: lambda _: JSON(),
        pg_types.JSONB: lambda _: JSON(),
        pg_types.JSON: lambda _: JSON(),
        pg_types.UUID: lambda _: String(36),
        pg_types.TSVECTOR: lambda _: Text(),
        pg_types.INET: lambda _: String(45),
        pg_types.CIDR: lambda _: String(45),
        pg_types.MACADDR: lambda _: String(17),
        pg_types.ENUM: lambda t: String(255),
        pg_types.INTERVAL: lambda _: String(50),
    }

    meta = MetaData()
    for table in Base.metadata.sorted_tables:
        columns = []
        for col in table.columns:
            col_type = col.type

            # Replace any PG-specific type
            for pg_cls, factory in PG_TYPE_MAP.items():
                if isinstance(col_type, pg_cls):
                    col_type = factory(col_type)
                    break

            kwargs = {
                "primary_key": col.primary_key,
                "nullable": col.nullable,
            }

            # Skip PG-specific server_defaults (gen_random_uuid, array literals)
            if col.server_default is not None:
                sd_text = ""
                if hasattr(col.server_default, "arg"):
                    sd_text = str(col.server_default.arg)
                if not any(s in sd_text for s in ["gen_random_uuid", "'{", "ARRAY"]):
                    kwargs["server_default"] = col.server_default

            columns.append(Column(col.name, col_type, **kwargs))

        # Create table without PG-specific constraints
        Table(table.name, meta, *columns)

    meta.create_all(connection)


@pytest.fixture
async def test_db():
    """Create test database session.

    Creates an in-memory SQLite database for testing.
    PostgreSQL-specific types (ARRAY, gen_random_uuid) are replaced with
    SQLite-compatible equivalents.
    """
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
    from sqlalchemy.orm import sessionmaker

    import json
    from sqlalchemy import event as sa_event

    # Create in-memory async SQLite database
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
        json_serializer=json.dumps,
        json_deserializer=json.loads,
    )

    # Patch ARRAY and JSONB columns in ORM models to use JSON type on SQLite.
    # This ensures proper serialization/deserialization of list/dict values.
    from sqlalchemy import JSON as SA_JSON
    from sqlalchemy.dialects.postgresql import ARRAY, JSONB
    import lazy_bird.models  # noqa: F401
    from lazy_bird.core.database import Base

    for table in Base.metadata.sorted_tables:
        for col in table.columns:
            if isinstance(col.type, (ARRAY, JSONB)):
                col.type = SA_JSON()

    # Create tables with SQLite-compatible DDL
    async with engine.begin() as conn:
        await conn.run_sync(_create_sqlite_compatible_tables)

    # Create session factory
    async_session_factory = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

    # Create session
    async with async_session_factory() as session:
        yield session

    # Cleanup
    await engine.dispose()


@pytest.fixture
def test_client(test_db):
    """Create FastAPI test client with mocked database."""
    from fastapi.testclient import TestClient
    from lazy_bird.api.main import app
    from lazy_bird.api.dependencies import get_async_database

    # Override database dependency
    async def override_get_db():
        yield test_db

    app.dependency_overrides[get_async_database] = override_get_db

    client = TestClient(app)
    yield client

    # Cleanup
    app.dependency_overrides.clear()


@pytest.fixture
async def test_api_key(test_db):
    """Create test API key with admin scope.

    Returns the ApiKey model with an extra `raw_key` attribute
    containing the unhashed key for use in X-API-Key headers.
    """
    from lazy_bird.models.api_key import ApiKey
    from lazy_bird.core.security import generate_api_key, hash_api_key, get_api_key_prefix
    from datetime import datetime, timezone

    raw_key = generate_api_key()
    api_key = ApiKey(
        name="Test API Key",
        key_hash=hash_api_key(raw_key),
        key_prefix=get_api_key_prefix(raw_key),
        scopes=["admin"],
        is_active=True,
        created_at=datetime.now(timezone.utc),
    )

    test_db.add(api_key)
    await test_db.commit()
    await test_db.refresh(api_key)

    # Expunge from session so we can modify attributes without dirtying it.
    # Tests use test_api_key.key_hash as the X-API-Key header value,
    # so we swap key_hash to the raw key for convenience.
    from sqlalchemy.orm import make_transient
    test_db.expunge(api_key)
    make_transient(api_key)
    api_key.key_hash = raw_key
    return api_key


@pytest.fixture
async def test_project(test_db):
    """Create test project in database."""
    from lazy_bird.models.project import Project
    from datetime import datetime, timezone
    from decimal import Decimal

    project = Project(
        name="Test Project",
        slug="test-project",
        repo_url="https://github.com/user/test-project",
        default_branch="main",
        project_type="python",
        automation_enabled=True,
        test_command="pytest",
        build_command="python -m build",
        lint_command="flake8",
        max_concurrent_tasks=3,
        task_timeout_seconds=1800,
        max_cost_per_task_usd=Decimal("5.00"),
        daily_cost_limit_usd=Decimal("50.00"),
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )

    test_db.add(project)
    await test_db.commit()
    await test_db.refresh(project)

    return project
