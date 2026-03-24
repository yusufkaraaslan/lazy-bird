"""Integration tests for FrameworkPresets API endpoints.

Tests all 5 FrameworkPreset CRUD endpoints with built-in protection.
"""

from datetime import datetime, timezone
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from lazy_bird.api.main import app
from lazy_bird.models.framework_preset import FrameworkPreset


class TestListFrameworkPresets:
    """Test GET /api/v1/framework-presets endpoint."""

    async def test_list_framework_presets_empty(self, test_client, test_api_key):
        """Test listing framework presets when none exist."""
        response = test_client.get(
            "/api/v1/framework-presets",
            headers={"X-API-Key": test_api_key.key_hash},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert data["items"] == []

    async def test_list_framework_presets_pagination(self, test_client, test_api_key, test_db):
        """Test framework presets pagination."""
        # Create 5 presets
        for i in range(5):
            preset = FrameworkPreset(
                name=f"preset-{i}",
                display_name=f"Preset {i}",
                framework_type="backend",
                test_command=f"pytest test-{i}",
                is_builtin=False,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            )
            test_db.add(preset)
        await test_db.commit()

        # Get page 1 with page_size=2
        response = test_client.get(
            "/api/v1/framework-presets?page=1&page_size=2",
            headers={"X-API-Key": test_api_key.key_hash},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 5
        assert len(data["items"]) == 2
        assert data["pages"] == 3

    async def test_list_framework_presets_filter_by_type(self, test_client, test_api_key, test_db):
        """Test filtering framework presets by framework_type."""
        # Create presets with different types
        backend = FrameworkPreset(
            name="django",
            display_name="Django",
            framework_type="backend",
            test_command="pytest",
            is_builtin=True,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        frontend = FrameworkPreset(
            name="react",
            display_name="React",
            framework_type="frontend",
            test_command="npm test",
            is_builtin=True,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        test_db.add_all([backend, frontend])
        await test_db.commit()

        # Filter for backend only
        response = test_client.get(
            "/api/v1/framework-presets?framework_type=backend",
            headers={"X-API-Key": test_api_key.key_hash},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["framework_type"] == "backend"

    async def test_list_framework_presets_filter_by_builtin(
        self, test_client, test_api_key, test_db
    ):
        """Test filtering framework presets by is_builtin."""
        # Create built-in and custom presets
        builtin = FrameworkPreset(
            name="godot",
            display_name="Godot",
            framework_type="game_engine",
            test_command="godot --test",
            is_builtin=True,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        custom = FrameworkPreset(
            name="custom-framework",
            display_name="Custom Framework",
            framework_type="backend",
            test_command="custom test",
            is_builtin=False,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        test_db.add_all([builtin, custom])
        await test_db.commit()

        # Filter for custom only
        response = test_client.get(
            "/api/v1/framework-presets?is_builtin=false",
            headers={"X-API-Key": test_api_key.key_hash},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["is_builtin"] is False


class TestCreateFrameworkPreset:
    """Test POST /api/v1/framework-presets endpoint."""

    async def test_create_framework_preset_success(self, test_client, test_api_key):
        """Test successful custom framework preset creation."""
        payload = {
            "name": "my-custom-framework",
            "display_name": "My Custom Framework",
            "framework_type": "backend",
            "language": "Python",
            "test_command": "pytest tests/",
            "build_command": "python setup.py build",
            "lint_command": "flake8 .",
            "format_command": "black .",
            "config_files": {"pyproject": "pyproject.toml", "setup": "setup.py"},
            "description": "Custom Python framework",
        }

        response = test_client.post(
            "/api/v1/framework-presets",
            json=payload,
            headers={"X-API-Key": test_api_key.key_hash},
        )

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "my-custom-framework"
        assert data["display_name"] == "My Custom Framework"
        assert data["framework_type"] == "backend"
        assert data["language"] == "Python"
        assert data["test_command"] == "pytest tests/"
        assert data["is_builtin"] is False  # Custom presets are never built-in
        assert "id" in data

    async def test_create_framework_preset_duplicate_name(self, test_client, test_api_key, test_db):
        """Test creating preset with duplicate name."""
        # Create existing preset
        existing = FrameworkPreset(
            name="existing-preset",
            display_name="Existing Preset",
            framework_type="backend",
            test_command="pytest",
            is_builtin=False,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        test_db.add(existing)
        await test_db.commit()

        payload = {
            "name": "existing-preset",  # Duplicate name
            "display_name": "Another Preset",
            "framework_type": "backend",
            "test_command": "pytest",
        }

        response = test_client.post(
            "/api/v1/framework-presets",
            json=payload,
            headers={"X-API-Key": test_api_key.key_hash},
        )

        assert response.status_code == 409
        assert "already exists" in response.json()["detail"].lower()

    async def test_create_framework_preset_minimal(self, test_client, test_api_key):
        """Test creating preset with minimal required fields."""
        payload = {
            "name": "minimal-preset",
            "display_name": "Minimal Preset",
            "framework_type": "language",
            "test_command": "run tests",
        }

        response = test_client.post(
            "/api/v1/framework-presets",
            json=payload,
            headers={"X-API-Key": test_api_key.key_hash},
        )

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "minimal-preset"
        assert data["language"] is None  # Optional field
        assert data["build_command"] is None  # Optional field


class TestGetFrameworkPreset:
    """Test GET /api/v1/framework-presets/{preset_id} endpoint."""

    async def test_get_framework_preset_success(self, test_client, test_api_key, test_db):
        """Test getting single framework preset."""
        preset = FrameworkPreset(
            name="godot",
            display_name="Godot Engine",
            framework_type="game_engine",
            language="GDScript",
            test_command="godot --headless --test",
            build_command="godot --export",
            is_builtin=True,
            config_files={"project": "project.godot"},
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        test_db.add(preset)
        await test_db.commit()
        await test_db.refresh(preset)

        response = test_client.get(
            f"/api/v1/framework-presets/{preset.id}",
            headers={"X-API-Key": test_api_key.key_hash},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(preset.id)
        assert data["name"] == "godot"
        assert data["display_name"] == "Godot Engine"
        assert data["is_builtin"] is True
        assert data["config_files"]["project"] == "project.godot"

    async def test_get_framework_preset_not_found(self, test_client, test_api_key):
        """Test getting non-existent framework preset."""
        response = test_client.get(
            f"/api/v1/framework-presets/{uuid4()}",
            headers={"X-API-Key": test_api_key.key_hash},
        )

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()


class TestUpdateFrameworkPreset:
    """Test PATCH /api/v1/framework-presets/{preset_id} endpoint."""

    async def test_update_custom_preset_success(self, test_client, test_api_key, test_db):
        """Test successful update of custom framework preset."""
        preset = FrameworkPreset(
            name="custom-preset",
            display_name="Custom Preset",
            framework_type="backend",
            test_command="pytest",
            is_builtin=False,  # Custom preset
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        test_db.add(preset)
        await test_db.commit()
        await test_db.refresh(preset)

        payload = {
            "display_name": "Updated Custom Preset",
            "test_command": "pytest -v",
            "build_command": "python -m build",
        }

        response = test_client.patch(
            f"/api/v1/framework-presets/{preset.id}",
            json=payload,
            headers={"X-API-Key": test_api_key.key_hash},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["display_name"] == "Updated Custom Preset"
        assert data["test_command"] == "pytest -v"
        assert data["build_command"] == "python -m build"

    async def test_update_builtin_preset_forbidden(self, test_client, test_api_key, test_db):
        """Test that built-in presets cannot be updated."""
        preset = FrameworkPreset(
            name="godot",
            display_name="Godot Engine",
            framework_type="game_engine",
            test_command="godot --test",
            is_builtin=True,  # Built-in preset
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        test_db.add(preset)
        await test_db.commit()
        await test_db.refresh(preset)

        payload = {"display_name": "Modified Godot"}

        response = test_client.patch(
            f"/api/v1/framework-presets/{preset.id}",
            json=payload,
            headers={"X-API-Key": test_api_key.key_hash},
        )

        assert response.status_code == 409
        assert "built-in" in response.json()["detail"].lower()

    async def test_update_framework_preset_not_found(self, test_client, test_api_key):
        """Test updating non-existent framework preset."""
        payload = {"display_name": "Updated"}

        response = test_client.patch(
            f"/api/v1/framework-presets/{uuid4()}",
            json=payload,
            headers={"X-API-Key": test_api_key.key_hash},
        )

        assert response.status_code == 404


class TestDeleteFrameworkPreset:
    """Test DELETE /api/v1/framework-presets/{preset_id} endpoint."""

    async def test_delete_custom_preset_success(self, test_client, test_api_key, test_db):
        """Test successful deletion of custom framework preset."""
        preset = FrameworkPreset(
            name="custom-to-delete",
            display_name="Custom To Delete",
            framework_type="backend",
            test_command="pytest",
            is_builtin=False,  # Custom preset
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        test_db.add(preset)
        await test_db.commit()
        await test_db.refresh(preset)
        preset_id = preset.id

        response = test_client.delete(
            f"/api/v1/framework-presets/{preset_id}",
            headers={"X-API-Key": test_api_key.key_hash},
        )

        assert response.status_code == 204

        # Verify deleted
        get_response = test_client.get(
            f"/api/v1/framework-presets/{preset_id}",
            headers={"X-API-Key": test_api_key.key_hash},
        )
        assert get_response.status_code == 404

    async def test_delete_builtin_preset_forbidden(self, test_client, test_api_key, test_db):
        """Test that built-in presets cannot be deleted."""
        preset = FrameworkPreset(
            name="django",
            display_name="Django",
            framework_type="backend",
            test_command="pytest",
            is_builtin=True,  # Built-in preset
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        test_db.add(preset)
        await test_db.commit()
        await test_db.refresh(preset)

        response = test_client.delete(
            f"/api/v1/framework-presets/{preset.id}",
            headers={"X-API-Key": test_api_key.key_hash},
        )

        assert response.status_code == 409
        assert "built-in" in response.json()["detail"].lower()

    async def test_delete_framework_preset_not_found(self, test_client, test_api_key):
        """Test deleting non-existent framework preset."""
        response = test_client.delete(
            f"/api/v1/framework-presets/{uuid4()}",
            headers={"X-API-Key": test_api_key.key_hash},
        )

        assert response.status_code == 404
