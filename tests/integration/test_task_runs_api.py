"""Integration tests for TaskRuns API endpoints.

Tests all 7 TaskRun CRUD endpoints with state machine validation.
"""

from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from lazy_bird.api.main import app
from lazy_bird.models.claude_account import ClaudeAccount
from lazy_bird.models.framework_preset import FrameworkPreset
from lazy_bird.models.project import Project
from lazy_bird.models.task_run import TaskRun


class TestListTaskRuns:
    """Test GET /api/v1/task-runs endpoint."""

    async def test_list_task_runs_empty(self, test_client, test_api_key):
        """Test listing task runs when none exist."""
        response = test_client.get(
            "/api/v1/task-runs",
            headers={"X-API-Key": test_api_key.key_hash},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert data["items"] == []
        assert data["page"] == 1
        assert data["pages"] == 0

    async def test_list_task_runs_pagination(
        self, test_client, test_api_key, test_db, test_project
    ):
        """Test task runs pagination."""
        # Create 5 task runs
        for i in range(5):
            task_run = TaskRun(
                project_id=test_project.id,
                work_item_id=str(100 + i),
                prompt="Test task",
                status="queued",
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            )
            test_db.add(task_run)
        await test_db.commit()

        # Get page 1 with page_size=2
        response = test_client.get(
            "/api/v1/task-runs?page=1&page_size=2",
            headers={"X-API-Key": test_api_key.key_hash},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 5
        assert len(data["items"]) == 2
        assert data["page"] == 1
        assert data["pages"] == 3

    async def test_list_task_runs_filter_by_status(
        self, test_client, test_api_key, test_db, test_project
    ):
        """Test filtering task runs by status."""
        # Create task runs with different statuses
        statuses = ["queued", "running", "success", "failed"]
        for status in statuses:
            task_run = TaskRun(
                project_id=test_project.id,
                work_item_id="100",
                prompt="Test task",
                status=status,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            )
            test_db.add(task_run)
        await test_db.commit()

        # Filter for success only
        response = test_client.get(
            "/api/v1/task-runs?status=success",
            headers={"X-API-Key": test_api_key.key_hash},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["status"] == "success"

    async def test_list_task_runs_filter_by_project(self, test_client, test_api_key, test_db):
        """Test filtering task runs by project_id."""
        # Create two projects
        project1 = Project(
            name="Project 1",
            slug="project-1",
            project_type="game_engine",
            repo_url="https://github.com/user/project1",
            max_cost_per_task_usd=Decimal("5.00"),
            daily_cost_limit_usd=Decimal("50.00"),
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        project2 = Project(
            name="Project 2",
            slug="project-2",
            project_type="backend",
            repo_url="https://github.com/user/project2",
            max_cost_per_task_usd=Decimal("5.00"),
            daily_cost_limit_usd=Decimal("50.00"),
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        test_db.add_all([project1, project2])
        await test_db.commit()
        await test_db.refresh(project1)
        await test_db.refresh(project2)

        # Create task runs for each project
        task1 = TaskRun(
            project_id=project1.id,
            work_item_id="100",
            prompt="Test task",
            status="queued",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        task2 = TaskRun(
            project_id=project2.id,
            work_item_id="200",
            prompt="Test task",
            status="queued",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        test_db.add_all([task1, task2])
        await test_db.commit()

        # Filter by project1
        response = test_client.get(
            f"/api/v1/task-runs?project_id={project1.id}",
            headers={"X-API-Key": test_api_key.key_hash},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["work_item_id"] == "100"


class TestQueueTaskRun:
    """Test POST /api/v1/task-runs endpoint."""

    async def test_queue_task_run_success(self, test_client, test_api_key, test_db, test_project):
        """Test successful task run queueing."""
        payload = {
            "project_id": str(test_project.id),
            "work_item_id": "42",
            "work_item_title": "Add health system to player",
            "work_item_url": "https://github.com/user/repo/issues/42",
            "prompt": "Implement health system with take_damage and heal methods",
        }

        response = test_client.post(
            "/api/v1/task-runs",
            json=payload,
            headers={"X-API-Key": test_api_key.key_hash},
        )

        assert response.status_code == 201
        data = response.json()
        assert data["work_item_id"] == "42"
        assert data["status"] == "queued"
        assert data["work_item_title"] == "Add health system to player"
        assert "id" in data

    async def test_queue_task_run_project_not_found(self, test_client, test_api_key):
        """Test queueing task run for non-existent project."""
        payload = {
            "project_id": str(uuid4()),
            "work_item_id": "42",
            "prompt": "Test task",
        }

        response = test_client.post(
            "/api/v1/task-runs",
            json=payload,
            headers={"X-API-Key": test_api_key.key_hash},
        )

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    async def test_queue_task_run_automation_disabled(self, test_client, test_api_key, test_db):
        """Test queueing task run when automation is disabled."""
        # Create project with automation disabled
        project = Project(
            name="Disabled Project",
            slug="disabled-project",
            project_type="backend",
            repo_url="https://github.com/user/disabled",
            max_cost_per_task_usd=Decimal("5.00"),
            daily_cost_limit_usd=Decimal("50.00"),
            automation_enabled=False,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        test_db.add(project)
        await test_db.commit()
        await test_db.refresh(project)

        payload = {
            "project_id": str(project.id),
            "work_item_id": "42",
            "prompt": "Test task",
        }

        response = test_client.post(
            "/api/v1/task-runs",
            json=payload,
            headers={"X-API-Key": test_api_key.key_hash},
        )

        assert response.status_code == 409
        assert "automation disabled" in response.json()["detail"].lower()

    async def test_queue_task_run_concurrent_limit_exceeded(
        self, test_client, test_api_key, test_db
    ):
        """Test queueing task run when concurrent limit is exceeded."""
        # Create project with max_concurrent_tasks=1
        project = Project(
            name="Limited Project",
            slug="limited-project",
            project_type="backend",
            repo_url="https://github.com/user/limited",
            max_cost_per_task_usd=Decimal("5.00"),
            daily_cost_limit_usd=Decimal("50.00"),
            max_concurrent_tasks=1,
            automation_enabled=True,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        test_db.add(project)
        await test_db.commit()
        await test_db.refresh(project)

        # Create one running task
        task_run = TaskRun(
            project_id=project.id,
            work_item_id="100",
            prompt="Test task",
            status="running",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        test_db.add(task_run)
        await test_db.commit()

        # Try to queue another
        payload = {
            "project_id": str(project.id),
            "work_item_id": "42",
            "prompt": "Test task",
        }

        response = test_client.post(
            "/api/v1/task-runs",
            json=payload,
            headers={"X-API-Key": test_api_key.key_hash},
        )

        assert response.status_code == 409
        assert "concurrent" in response.json()["detail"].lower()


class TestGetTaskRun:
    """Test GET /api/v1/task-runs/{task_run_id} endpoint."""

    async def test_get_task_run_success(self, test_client, test_api_key, test_db, test_project):
        """Test getting single task run."""
        task_run = TaskRun(
            project_id=test_project.id,
            work_item_id="42",
            prompt="Test task",
            status="running",
            cost_usd=Decimal("0.15"),
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        test_db.add(task_run)
        await test_db.commit()
        await test_db.refresh(task_run)

        response = test_client.get(
            f"/api/v1/task-runs/{task_run.id}",
            headers={"X-API-Key": test_api_key.key_hash},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(task_run.id)
        assert data["work_item_id"] == "42"
        assert data["status"] == "running"
        assert Decimal(data["cost_usd"]) == Decimal("0.15")

    async def test_get_task_run_not_found(self, test_client, test_api_key):
        """Test getting non-existent task run."""
        response = test_client.get(
            f"/api/v1/task-runs/{uuid4()}",
            headers={"X-API-Key": test_api_key.key_hash},
        )

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()


class TestUpdateTaskRun:
    """Test PATCH /api/v1/task-runs/{task_run_id} endpoint."""

    async def test_update_task_run_success(self, test_client, test_api_key, test_db, test_project):
        """Test successful task run update."""
        task_run = TaskRun(
            project_id=test_project.id,
            work_item_id="42",
            prompt="Test task",
            status="queued",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        test_db.add(task_run)
        await test_db.commit()
        await test_db.refresh(task_run)

        payload = {
            "status": "running",
            "cost_usd": "0.25",
        }

        response = test_client.patch(
            f"/api/v1/task-runs/{task_run.id}",
            json=payload,
            headers={"X-API-Key": test_api_key.key_hash},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "running"
        assert Decimal(data["cost_usd"]) == Decimal("0.25")

    async def test_update_task_run_invalid_status_transition(
        self, test_client, test_api_key, test_db, test_project
    ):
        """Test invalid status transition (success -> queued not allowed)."""
        task_run = TaskRun(
            project_id=test_project.id,
            work_item_id="42",
            prompt="Test task",
            status="success",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        test_db.add(task_run)
        await test_db.commit()
        await test_db.refresh(task_run)

        payload = {"status": "queued"}

        response = test_client.patch(
            f"/api/v1/task-runs/{task_run.id}",
            json=payload,
            headers={"X-API-Key": test_api_key.key_hash},
        )

        assert response.status_code == 409
        assert "transition" in response.json()["detail"].lower()

    async def test_update_task_run_not_found(self, test_client, test_api_key):
        """Test updating non-existent task run."""
        payload = {"status": "running"}

        response = test_client.patch(
            f"/api/v1/task-runs/{uuid4()}",
            json=payload,
            headers={"X-API-Key": test_api_key.key_hash},
        )

        assert response.status_code == 404


class TestCancelTaskRun:
    """Test POST /api/v1/task-runs/{task_run_id}/cancel endpoint."""

    async def test_cancel_task_run_success(self, test_client, test_api_key, test_db, test_project):
        """Test successful task run cancellation."""
        task_run = TaskRun(
            project_id=test_project.id,
            work_item_id="42",
            prompt="Test task",
            status="running",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        test_db.add(task_run)
        await test_db.commit()
        await test_db.refresh(task_run)

        response = test_client.post(
            f"/api/v1/task-runs/{task_run.id}/cancel",
            headers={"X-API-Key": test_api_key.key_hash},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "cancelled"

    async def test_cancel_task_run_already_completed(
        self, test_client, test_api_key, test_db, test_project
    ):
        """Test cancelling already completed task run."""
        task_run = TaskRun(
            project_id=test_project.id,
            work_item_id="42",
            prompt="Test task",
            status="success",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        test_db.add(task_run)
        await test_db.commit()
        await test_db.refresh(task_run)

        response = test_client.post(
            f"/api/v1/task-runs/{task_run.id}/cancel",
            headers={"X-API-Key": test_api_key.key_hash},
        )

        assert response.status_code == 409
        assert "cannot cancel" in response.json()["detail"].lower()

    async def test_cancel_task_run_not_found(self, test_client, test_api_key):
        """Test cancelling non-existent task run."""
        response = test_client.post(
            f"/api/v1/task-runs/{uuid4()}/cancel",
            headers={"X-API-Key": test_api_key.key_hash},
        )

        assert response.status_code == 404


class TestRetryTaskRun:
    """Test POST /api/v1/task-runs/{task_run_id}/retry endpoint."""

    async def test_retry_task_run_success(self, test_client, test_api_key, test_db, test_project):
        """Test successful task run retry."""
        task_run = TaskRun(
            project_id=test_project.id,
            work_item_id="42",
            prompt="Test task",
            status="failed",
            error_message="Test error",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        test_db.add(task_run)
        await test_db.commit()
        await test_db.refresh(task_run)

        response = test_client.post(
            f"/api/v1/task-runs/{task_run.id}/retry",
            headers={"X-API-Key": test_api_key.key_hash},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "queued"
        assert data["retry_count"] == 1
        assert data["error_message"] is None

    async def test_retry_task_run_not_failed(
        self, test_client, test_api_key, test_db, test_project
    ):
        """Test retrying non-failed task run."""
        task_run = TaskRun(
            project_id=test_project.id,
            work_item_id="42",
            prompt="Test task",
            status="success",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        test_db.add(task_run)
        await test_db.commit()
        await test_db.refresh(task_run)

        response = test_client.post(
            f"/api/v1/task-runs/{task_run.id}/retry",
            headers={"X-API-Key": test_api_key.key_hash},
        )

        assert response.status_code == 409
        assert "cannot retry" in response.json()["detail"].lower()

    async def test_retry_task_run_not_found(self, test_client, test_api_key):
        """Test retrying non-existent task run."""
        response = test_client.post(
            f"/api/v1/task-runs/{uuid4()}/retry",
            headers={"X-API-Key": test_api_key.key_hash},
        )

        assert response.status_code == 404


class TestDeleteTaskRun:
    """Test DELETE /api/v1/task-runs/{task_run_id} endpoint."""

    async def test_delete_task_run_success(self, test_client, test_api_key, test_db, test_project):
        """Test successful task run deletion."""
        task_run = TaskRun(
            project_id=test_project.id,
            work_item_id="42",
            prompt="Test task",
            status="success",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        test_db.add(task_run)
        await test_db.commit()
        await test_db.refresh(task_run)
        task_run_id = task_run.id

        response = test_client.delete(
            f"/api/v1/task-runs/{task_run_id}",
            headers={"X-API-Key": test_api_key.key_hash},
        )

        assert response.status_code == 204

        # Verify deleted
        get_response = test_client.get(
            f"/api/v1/task-runs/{task_run_id}",
            headers={"X-API-Key": test_api_key.key_hash},
        )
        assert get_response.status_code == 404

    async def test_delete_task_run_not_found(self, test_client, test_api_key):
        """Test deleting non-existent task run."""
        response = test_client.delete(
            f"/api/v1/task-runs/{uuid4()}",
            headers={"X-API-Key": test_api_key.key_hash},
        )

        assert response.status_code == 404
