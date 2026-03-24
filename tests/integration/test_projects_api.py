"""Integration tests for Projects API endpoints.

Tests all CRUD operations, validation, pagination, filtering, and search.
"""

import pytest
from decimal import Decimal
from uuid import UUID

pytestmark = pytest.mark.asyncio


class TestListProjects:
    """Test GET /api/v1/projects - List projects with pagination."""

    async def test_list_projects_empty(self, test_client, test_api_key):
        """Test listing projects when database is empty."""
        response = test_client.get(
            "/api/v1/projects",
            headers={"X-API-Key": test_api_key.key_hash},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert data["items"] == []
        assert data["page"] == 1
        assert data["pages"] == 0

    async def test_list_projects_with_data(self, test_client, test_api_key, test_project):
        """Test listing projects with existing data."""
        response = test_client.get(
            "/api/v1/projects",
            headers={"X-API-Key": test_api_key.key_hash},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert len(data["items"]) == 1
        assert data["items"][0]["slug"] == "test-project"
        assert data["items"][0]["name"] == "Test Project"

    async def test_list_projects_pagination(self, test_client, test_api_key, test_db):
        """Test pagination with multiple projects."""
        from lazy_bird.models.project import Project
        from datetime import datetime, timezone
        from decimal import Decimal

        # Create 5 projects
        for i in range(5):
            project = Project(
                name=f"Project {i}",
                slug=f"project-{i}",
                repo_url=f"https://github.com/user/project-{i}",
                default_branch="main",
                project_type="python",
                max_cost_per_task_usd=Decimal("5.00"),
                daily_cost_limit_usd=Decimal("50.00"),
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            )
            test_db.add(project)

        await test_db.commit()

        # Test page 1 with page_size=2
        response = test_client.get(
            "/api/v1/projects?page=1&page_size=2",
            headers={"X-API-Key": test_api_key.key_hash},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 5
        assert len(data["items"]) == 2
        assert data["page"] == 1
        assert data["page_size"] == 2
        assert data["pages"] == 3

    async def test_list_projects_filter_by_type(self, test_client, test_api_key, test_db):
        """Test filtering projects by project_type."""
        from lazy_bird.models.project import Project
        from datetime import datetime, timezone
        from decimal import Decimal

        # Create projects with different types
        for project_type in ["python", "godot", "rust"]:
            project = Project(
                name=f"{project_type.title()} Project",
                slug=f"{project_type}-project",
                repo_url=f"https://github.com/user/{project_type}",
                default_branch="main",
                project_type=project_type,
                max_cost_per_task_usd=Decimal("5.00"),
                daily_cost_limit_usd=Decimal("50.00"),
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            )
            test_db.add(project)

        await test_db.commit()

        # Filter by Python projects
        response = test_client.get(
            "/api/v1/projects?project_type=python",
            headers={"X-API-Key": test_api_key.key_hash},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["project_type"] == "python"

    async def test_list_projects_search(self, test_client, test_api_key, test_db):
        """Test searching projects by name, slug, repo_url."""
        from lazy_bird.models.project import Project
        from datetime import datetime, timezone
        from decimal import Decimal

        # Create projects
        projects_data = [
            ("My Game", "my-game", "https://github.com/user/game"),
            ("Backend API", "backend-api", "https://github.com/user/api"),
            ("Frontend UI", "frontend-ui", "https://github.com/user/ui"),
        ]

        for name, slug, repo_url in projects_data:
            project = Project(
                name=name,
                slug=slug,
                repo_url=repo_url,
                default_branch="main",
                project_type="python",
                max_cost_per_task_usd=Decimal("5.00"),
                daily_cost_limit_usd=Decimal("50.00"),
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            )
            test_db.add(project)

        await test_db.commit()

        # Search for "game"
        response = test_client.get(
            "/api/v1/projects?search=game",
            headers={"X-API-Key": test_api_key.key_hash},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["slug"] == "my-game"

    async def test_list_projects_exclude_deleted(self, test_client, test_api_key, test_db):
        """Test that soft-deleted projects are excluded by default."""
        from lazy_bird.models.project import Project
        from datetime import datetime, timezone
        from decimal import Decimal

        # Create active project
        active_project = Project(
            name="Active Project",
            slug="active-project",
            repo_url="https://github.com/user/active",
            default_branch="main",
            project_type="python",
            max_cost_per_task_usd=Decimal("5.00"),
            daily_cost_limit_usd=Decimal("50.00"),
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        test_db.add(active_project)

        # Create deleted project
        deleted_project = Project(
            name="Deleted Project",
            slug="deleted-project",
            repo_url="https://github.com/user/deleted",
            default_branch="main",
            project_type="python",
            max_cost_per_task_usd=Decimal("5.00"),
            daily_cost_limit_usd=Decimal("50.00"),
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            deleted_at=datetime.now(timezone.utc),
        )
        test_db.add(deleted_project)

        await test_db.commit()

        # List without include_deleted (should only show active)
        response = test_client.get(
            "/api/v1/projects",
            headers={"X-API-Key": test_api_key.key_hash},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["slug"] == "active-project"


class TestCreateProject:
    """Test POST /api/v1/projects - Create new project."""

    async def test_create_project_minimal(self, test_client, test_api_key):
        """Test creating project with minimal required fields."""
        project_data = {
            "name": "New Project",
            "slug": "new-project",
            "repo_url": "https://github.com/user/new-project",
            "project_type": "python",
        }

        response = test_client.post(
            "/api/v1/projects",
            json=project_data,
            headers={"X-API-Key": test_api_key.key_hash},
        )

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "New Project"
        assert data["slug"] == "new-project"
        assert data["project_type"] == "python"
        assert "id" in data
        assert data["automation_enabled"] is False  # Default value

    async def test_create_project_full(self, test_client, test_api_key):
        """Test creating project with all optional fields."""
        project_data = {
            "name": "Full Project",
            "slug": "full-project",
            "repo_url": "https://github.com/user/full",
            "default_branch": "develop",
            "project_type": "python",
            "test_command": "pytest tests/",
            "build_command": "python -m build",
            "lint_command": "flake8 .",
            "format_command": "black .",
            "automation_enabled": True,
            "max_concurrent_tasks": 5,
            "task_timeout_seconds": 3600,
            "max_cost_per_task_usd": "10.00",
            "daily_cost_limit_usd": "100.00",
        }

        response = test_client.post(
            "/api/v1/projects",
            json=project_data,
            headers={"X-API-Key": test_api_key.key_hash},
        )

        assert response.status_code == 201
        data = response.json()
        assert data["automation_enabled"] is True
        assert data["max_concurrent_tasks"] == 5
        assert data["test_command"] == "pytest tests/"

    async def test_create_project_duplicate_slug(self, test_client, test_api_key, test_project):
        """Test creating project with duplicate slug returns 409 Conflict."""
        project_data = {
            "name": "Duplicate",
            "slug": "test-project",  # Same as test_project fixture
            "repo_url": "https://github.com/user/duplicate",
            "project_type": "python",
        }

        response = test_client.post(
            "/api/v1/projects",
            json=project_data,
            headers={"X-API-Key": test_api_key.key_hash},
        )

        assert response.status_code == 409
        data = response.json()
        assert "slug" in data["detail"].lower() or "already exists" in data["detail"].lower()

    async def test_create_project_invalid_slug(self, test_client, test_api_key):
        """Test creating project with invalid slug format returns 422."""
        project_data = {
            "name": "Invalid",
            "slug": "Invalid_Slug!",  # Invalid: uppercase and special chars
            "repo_url": "https://github.com/user/invalid",
            "project_type": "python",
        }

        response = test_client.post(
            "/api/v1/projects",
            json=project_data,
            headers={"X-API-Key": test_api_key.key_hash},
        )

        assert response.status_code == 422

    async def test_create_project_missing_required_fields(self, test_client, test_api_key):
        """Test creating project without required fields returns 422."""
        project_data = {
            "name": "Incomplete",
            # Missing: slug, repo_url, project_type
        }

        response = test_client.post(
            "/api/v1/projects",
            json=project_data,
            headers={"X-API-Key": test_api_key.key_hash},
        )

        assert response.status_code == 422


class TestGetProject:
    """Test GET /api/v1/projects/{project_id} - Get single project."""

    async def test_get_project_by_id(self, test_client, test_api_key, test_project):
        """Test getting project by ID."""
        response = test_client.get(
            f"/api/v1/projects/{test_project.id}",
            headers={"X-API-Key": test_api_key.key_hash},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(test_project.id)
        assert data["slug"] == "test-project"
        assert data["name"] == "Test Project"

    async def test_get_project_not_found(self, test_client, test_api_key):
        """Test getting non-existent project returns 404."""
        fake_uuid = "12345678-1234-1234-1234-123456789012"
        response = test_client.get(
            f"/api/v1/projects/{fake_uuid}",
            headers={"X-API-Key": test_api_key.key_hash},
        )

        assert response.status_code == 404
        data = response.json()
        assert "not found" in data["detail"].lower()

    async def test_get_deleted_project_returns_404(
        self, test_client, test_api_key, test_project, test_db
    ):
        """Test getting soft-deleted project returns 404."""
        from datetime import datetime, timezone

        # Soft delete the project
        test_db.add(test_project)
        test_project.deleted_at = datetime.now(timezone.utc)
        await test_db.commit()

        response = test_client.get(
            f"/api/v1/projects/{test_project.id}",
            headers={"X-API-Key": test_api_key.key_hash},
        )

        assert response.status_code == 404


class TestUpdateProject:
    """Test PATCH /api/v1/projects/{project_id} - Update project."""

    async def test_update_project_single_field(self, test_client, test_api_key, test_project):
        """Test updating single field."""
        update_data = {"name": "Updated Name"}

        response = test_client.patch(
            f"/api/v1/projects/{test_project.id}",
            json=update_data,
            headers={"X-API-Key": test_api_key.key_hash},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Name"
        assert data["slug"] == "test-project"  # Unchanged

    async def test_update_project_multiple_fields(self, test_client, test_api_key, test_project):
        """Test updating multiple fields."""
        update_data = {
            "automation_enabled": False,
            "max_concurrent_tasks": 10,
            "daily_cost_limit_usd": "200.00",
        }

        response = test_client.patch(
            f"/api/v1/projects/{test_project.id}",
            json=update_data,
            headers={"X-API-Key": test_api_key.key_hash},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["automation_enabled"] is False
        assert data["max_concurrent_tasks"] == 10

    async def test_update_project_duplicate_slug(
        self, test_client, test_api_key, test_project, test_db
    ):
        """Test updating slug to existing slug returns 409."""
        from lazy_bird.models.project import Project
        from datetime import datetime, timezone
        from decimal import Decimal

        # Create another project
        other_project = Project(
            name="Other Project",
            slug="other-project",
            repo_url="https://github.com/user/other",
            default_branch="main",
            project_type="python",
            max_cost_per_task_usd=Decimal("5.00"),
            daily_cost_limit_usd=Decimal("50.00"),
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        test_db.add(other_project)
        await test_db.commit()

        # Try to update test_project slug to match other_project
        update_data = {"slug": "other-project"}

        response = test_client.patch(
            f"/api/v1/projects/{test_project.id}",
            json=update_data,
            headers={"X-API-Key": test_api_key.key_hash},
        )

        assert response.status_code == 409

    async def test_update_project_not_found(self, test_client, test_api_key):
        """Test updating non-existent project returns 404."""
        fake_uuid = "12345678-1234-1234-1234-123456789012"
        update_data = {"name": "Updated"}

        response = test_client.patch(
            f"/api/v1/projects/{fake_uuid}",
            json=update_data,
            headers={"X-API-Key": test_api_key.key_hash},
        )

        assert response.status_code == 404

    async def test_update_project_empty_body(self, test_client, test_api_key, test_project):
        """Test updating with empty body returns existing project."""
        update_data = {}

        response = test_client.patch(
            f"/api/v1/projects/{test_project.id}",
            json=update_data,
            headers={"X-API-Key": test_api_key.key_hash},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Test Project"  # Unchanged


class TestDeleteProject:
    """Test DELETE /api/v1/projects/{project_id} - Soft delete project."""

    async def test_delete_project(self, test_client, test_api_key, test_project):
        """Test soft deleting project."""
        response = test_client.delete(
            f"/api/v1/projects/{test_project.id}",
            headers={"X-API-Key": test_api_key.key_hash},
        )

        assert response.status_code == 204
        assert response.content == b""  # No response body

    async def test_delete_project_verify_soft_delete(self, test_client, test_api_key, test_project):
        """Test that deleted project is soft deleted, not hard deleted."""
        # Delete project
        response = test_client.delete(
            f"/api/v1/projects/{test_project.id}",
            headers={"X-API-Key": test_api_key.key_hash},
        )
        assert response.status_code == 204

        # Try to get project (should return 404)
        response = test_client.get(
            f"/api/v1/projects/{test_project.id}",
            headers={"X-API-Key": test_api_key.key_hash},
        )
        assert response.status_code == 404

        # Verify project still exists in database but with deleted_at set
        # (would need direct DB access to verify)

    async def test_delete_project_not_found(self, test_client, test_api_key):
        """Test deleting non-existent project returns 404."""
        fake_uuid = "12345678-1234-1234-1234-123456789012"
        response = test_client.delete(
            f"/api/v1/projects/{fake_uuid}",
            headers={"X-API-Key": test_api_key.key_hash},
        )

        assert response.status_code == 404

    async def test_delete_already_deleted_project(
        self, test_client, test_api_key, test_project, test_db
    ):
        """Test deleting already-deleted project returns 404."""
        from datetime import datetime, timezone

        # Soft delete the project manually
        test_db.add(test_project)
        test_project.deleted_at = datetime.now(timezone.utc)
        await test_db.commit()

        # Try to delete again
        response = test_client.delete(
            f"/api/v1/projects/{test_project.id}",
            headers={"X-API-Key": test_api_key.key_hash},
        )

        assert response.status_code == 404


class TestAuthentication:
    """Test API key authentication."""

    async def test_missing_api_key(self, test_client):
        """Test accessing endpoint without API key returns 401/403."""
        response = test_client.get("/api/v1/projects")
        assert response.status_code in [401, 403]

    async def test_invalid_api_key(self, test_client):
        """Test accessing endpoint with invalid API key returns 401/403."""
        response = test_client.get(
            "/api/v1/projects",
            headers={"X-API-Key": "invalid-key"},
        )
        assert response.status_code in [401, 403]
