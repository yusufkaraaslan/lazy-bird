"""Unit tests for lazy_bird.models.task_run_log module.

Tests TaskRunLog model validation, methods, and factory.
"""

import uuid
from datetime import datetime, timezone

import pytest

from lazy_bird.models.task_run_log import LogLevel, TaskRunLog


@pytest.fixture
def task_run_log():
    """Create a TaskRunLog instance for testing."""
    return TaskRunLog(
        id=uuid.uuid4(),
        task_run_id=uuid.uuid4(),
        level="info",
        message="Test log message",
        step="implementation",
        tool_name="Write",
        log_metadata={"file": "test.py"},
        created_at=datetime.now(timezone.utc),
    )


class TestLogLevel:
    """Test LogLevel enum."""

    def test_log_level_values(self):
        """Test LogLevel enum values."""
        assert LogLevel.DEBUG == "debug"
        assert LogLevel.INFO == "info"
        assert LogLevel.WARNING == "warning"
        assert LogLevel.ERROR == "error"
        assert LogLevel.CRITICAL == "critical"

    def test_log_level_is_string(self):
        """Test LogLevel inherits from str."""
        assert isinstance(LogLevel.INFO, str)


class TestTaskRunLogValidation:
    """Test TaskRunLog validation."""

    def test_validate_level_valid(self, task_run_log):
        """Test valid log levels."""
        for level in ["debug", "info", "warning", "error", "critical"]:
            result = task_run_log.validate_level("level", level)
            assert result == level

    def test_validate_level_invalid(self, task_run_log):
        """Test invalid log level raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            task_run_log.validate_level("level", "trace")
        assert "level must be one of" in str(exc_info.value)


class TestTaskRunLogMethods:
    """Test TaskRunLog methods."""

    def test_repr(self, task_run_log):
        """Test __repr__ method."""
        repr_str = repr(task_run_log)
        assert "TaskRunLog" in repr_str
        assert "info" in repr_str
        assert "implementation" in repr_str

    def test_is_error_true(self, task_run_log):
        """Test is_error returns True for error level."""
        task_run_log.level = "error"
        assert task_run_log.is_error() is True

    def test_is_error_critical(self, task_run_log):
        """Test is_error returns True for critical level."""
        task_run_log.level = "critical"
        assert task_run_log.is_error() is True

    def test_is_error_false(self, task_run_log):
        """Test is_error returns False for non-error levels."""
        for level in ["debug", "info", "warning"]:
            task_run_log.level = level
            assert task_run_log.is_error() is False


class TestTaskRunLogFactory:
    """Test TaskRunLog.create_log factory method."""

    def test_create_log_basic(self):
        """Test basic log creation."""
        task_run_id = uuid.uuid4()
        log = TaskRunLog.create_log(
            task_run_id=task_run_id,
            level="info",
            message="Task started",
        )

        assert log.task_run_id == task_run_id
        assert log.level == "info"
        assert log.message == "Task started"
        assert log.step is None
        assert log.tool_name is None

    def test_create_log_with_step_and_tool(self):
        """Test log creation with step and tool name."""
        log = TaskRunLog.create_log(
            task_run_id=uuid.uuid4(),
            level="debug",
            message="Reading file",
            step="implementation",
            tool_name="Read",
        )

        assert log.step == "implementation"
        assert log.tool_name == "Read"

    def test_create_log_with_metadata(self):
        """Test log creation with metadata kwargs."""
        log = TaskRunLog.create_log(
            task_run_id=uuid.uuid4(),
            level="info",
            message="Test complete",
            duration_ms=150,
            tests_passed=5,
        )

        assert log.metadata == {"duration_ms": 150, "tests_passed": 5}
