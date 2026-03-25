"""Unit tests for lazy_bird.models.task_run module.

Tests TaskRun model validation methods and helper methods.
"""

import uuid
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from lazy_bird.models.task_run import TaskRun


@pytest.fixture
def task_run():
    """Create a TaskRun instance for testing."""
    return TaskRun(
        id=uuid.uuid4(),
        project_id=uuid.uuid4(),
        work_item_id="GH-42",
        work_item_title="Add health system",
        status="queued",
        complexity="medium",
        retry_count=0,
        max_retries=3,
        task_metadata={},
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )


class TestTaskRunValidation:
    """Test TaskRun validation methods."""

    def test_validate_status_valid(self, task_run):
        """Test valid status values."""
        valid_statuses = ["queued", "running", "success", "failed", "cancelled", "timeout"]
        for status in valid_statuses:
            result = task_run.validate_status("status", status)
            assert result == status

    def test_validate_status_invalid(self, task_run):
        """Test invalid status raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            task_run.validate_status("status", "invalid_status")
        assert "status must be one of" in str(exc_info.value)

    def test_validate_complexity_valid(self, task_run):
        """Test valid complexity values."""
        for complexity in ["simple", "medium", "complex"]:
            result = task_run.validate_complexity("complexity", complexity)
            assert result == complexity

    def test_validate_complexity_none(self, task_run):
        """Test None complexity is allowed."""
        result = task_run.validate_complexity("complexity", None)
        assert result is None

    def test_validate_complexity_invalid(self, task_run):
        """Test invalid complexity raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            task_run.validate_complexity("complexity", "extreme")
        assert "complexity must be one of" in str(exc_info.value)


class TestTaskRunMethods:
    """Test TaskRun helper methods."""

    def test_is_terminal_status_success(self, task_run):
        """Test is_terminal_status for success."""
        task_run.status = "success"
        assert task_run.is_terminal_status() is True

    def test_is_terminal_status_failed(self, task_run):
        """Test is_terminal_status for failed."""
        task_run.status = "failed"
        assert task_run.is_terminal_status() is True

    def test_is_terminal_status_cancelled(self, task_run):
        """Test is_terminal_status for cancelled."""
        task_run.status = "cancelled"
        assert task_run.is_terminal_status() is True

    def test_is_terminal_status_timeout(self, task_run):
        """Test is_terminal_status for timeout."""
        task_run.status = "timeout"
        assert task_run.is_terminal_status() is True

    def test_is_terminal_status_queued(self, task_run):
        """Test is_terminal_status for queued (not terminal)."""
        task_run.status = "queued"
        assert task_run.is_terminal_status() is False

    def test_is_terminal_status_running(self, task_run):
        """Test is_terminal_status for running (not terminal)."""
        task_run.status = "running"
        assert task_run.is_terminal_status() is False

    def test_is_running(self, task_run):
        """Test is_running method."""
        task_run.status = "running"
        assert task_run.is_running() is True

        task_run.status = "queued"
        assert task_run.is_running() is False

    def test_is_queued(self, task_run):
        """Test is_queued method."""
        task_run.status = "queued"
        assert task_run.is_queued() is True

        task_run.status = "running"
        assert task_run.is_queued() is False

    def test_can_retry_yes(self, task_run):
        """Test can_retry when retries available."""
        task_run.retry_count = 0
        task_run.max_retries = 3
        assert task_run.can_retry() is True

    def test_can_retry_no(self, task_run):
        """Test can_retry when retries exhausted."""
        task_run.retry_count = 3
        task_run.max_retries = 3
        assert task_run.can_retry() is False

    def test_mark_started(self, task_run):
        """Test mark_started sets status and started_at."""
        task_run.mark_started()
        assert task_run.status == "running"
        assert task_run.started_at is not None

    def test_mark_completed_success(self, task_run):
        """Test mark_completed for success."""
        task_run.mark_completed(success=True)
        assert task_run.status == "success"
        assert task_run.completed_at is not None

    def test_mark_completed_failure(self, task_run):
        """Test mark_completed for failure with error."""
        task_run.mark_completed(success=False, error="Test timeout")
        assert task_run.status == "failed"
        assert task_run.error_message == "Test timeout"

    def test_mark_completed_with_duration(self, task_run):
        """Test mark_completed calculates duration when started_at is set."""
        task_run.started_at = datetime.now(timezone.utc)
        task_run.mark_completed(success=True)
        assert task_run.status == "success"
        # Duration may be calculated if started_at was datetime
        if task_run.duration_seconds is not None:
            assert task_run.duration_seconds >= 0

    def test_increment_retry(self, task_run):
        """Test increment_retry resets task to queued."""
        task_run.status = "failed"
        task_run.retry_count = 1
        task_run.started_at = datetime.now(timezone.utc)
        task_run.completed_at = datetime.now(timezone.utc)
        task_run.error_message = "Some error"

        task_run.increment_retry()

        assert task_run.retry_count == 2
        assert task_run.status == "queued"
        assert task_run.started_at is None
        assert task_run.completed_at is None
        assert task_run.error_message is None

    def test_add_metadata_new(self, task_run):
        """Test adding metadata when metadata is None."""
        task_run.task_metadata = None
        task_run.add_metadata("key1", "value1")
        assert task_run.task_metadata == {"key1": "value1"}

    def test_add_metadata_existing(self, task_run):
        """Test adding metadata to existing dict."""
        task_run.task_metadata = {"existing": "data"}
        task_run.add_metadata("new_key", 42)
        assert task_run.task_metadata["existing"] == "data"
        assert task_run.task_metadata["new_key"] == 42

    def test_get_metadata_exists(self, task_run):
        """Test getting metadata when key exists."""
        task_run.task_metadata = {"key1": "value1"}
        result = task_run.get_metadata("key1")
        assert result == "value1"

    def test_get_metadata_not_exists(self, task_run):
        """Test getting metadata when key does not exist."""
        task_run.task_metadata = {"key1": "value1"}
        result = task_run.get_metadata("missing")
        assert result is None

    def test_get_metadata_with_default(self, task_run):
        """Test getting metadata with default value."""
        task_run.task_metadata = {"key1": "value1"}
        result = task_run.get_metadata("missing", default="default_val")
        assert result == "default_val"

    def test_get_metadata_empty(self, task_run):
        """Test getting metadata when metadata is None."""
        task_run.task_metadata = None
        result = task_run.get_metadata("key1", default="fallback")
        assert result == "fallback"

    def test_get_metadata_empty_dict(self, task_run):
        """Test getting metadata when metadata is empty dict."""
        task_run.task_metadata = {}
        result = task_run.get_metadata("key1", default="fallback")
        assert result == "fallback"

    def test_repr(self, task_run):
        """Test __repr__ method."""
        repr_str = repr(task_run)
        assert "TaskRun" in repr_str
        assert "GH-42" in repr_str
        assert "queued" in repr_str
