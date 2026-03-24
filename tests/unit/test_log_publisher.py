"""Unit tests for LogPublisher.

Tests log publishing to Redis Pub/Sub, history storage, and retrieval.
"""

import json
from unittest.mock import Mock, patch, AsyncMock

import pytest

from lazy_bird.services.log_publisher import (
    LogPublisher,
    publish_task_log,
)


class TestLogPublisherInit:
    """Test LogPublisher initialization."""

    def test_init_sync(self):
        """Test LogPublisher with sync client."""
        publisher = LogPublisher(use_async=False)

        assert publisher.use_async is False
        assert publisher._redis is None

    def test_init_async(self):
        """Test LogPublisher with async client."""
        publisher = LogPublisher(use_async=True)

        assert publisher.use_async is True
        assert publisher._redis is None


class TestGetChannel:
    """Test _get_channel method."""

    def test_get_channel_task_specific(self):
        """Test channel for task-specific logs."""
        publisher = LogPublisher()

        channel = publisher._get_channel(task_id="task-123")

        assert channel == "lazy_bird:logs:task:task-123"

    def test_get_channel_project_specific(self):
        """Test channel for project-specific logs."""
        publisher = LogPublisher()

        channel = publisher._get_channel(project_id="my-project")

        assert channel == "lazy_bird:logs:project:my-project"

    def test_get_channel_system(self):
        """Test channel for system logs."""
        publisher = LogPublisher()

        channel = publisher._get_channel()

        assert channel == "lazy_bird:logs:system"

    def test_get_channel_priority(self):
        """Test task_id takes priority over project_id."""
        publisher = LogPublisher()

        channel = publisher._get_channel(task_id="task-123", project_id="my-project")

        assert channel == "lazy_bird:logs:task:task-123"


class TestBuildLogEntry:
    """Test _build_log_entry method."""

    def test_build_log_entry_minimal(self):
        """Test building minimal log entry."""
        publisher = LogPublisher()

        entry = publisher._build_log_entry(
            message="Test message",
            level="INFO",
            task_id=None,
            project_id=None,
            metadata=None,
        )

        assert entry["message"] == "Test message"
        assert entry["level"] == "INFO"
        assert "timestamp" in entry
        assert "task_id" not in entry
        assert "project_id" not in entry

    def test_build_log_entry_with_ids(self):
        """Test building log entry with task and project IDs."""
        publisher = LogPublisher()

        entry = publisher._build_log_entry(
            message="Test message",
            level="DEBUG",
            task_id="task-123",
            project_id="my-project",
            metadata=None,
        )

        assert entry["task_id"] == "task-123"
        assert entry["project_id"] == "my-project"

    def test_build_log_entry_with_metadata(self):
        """Test building log entry with metadata."""
        publisher = LogPublisher()

        metadata = {"test_framework": "pytest", "tests_passed": 10}

        entry = publisher._build_log_entry(
            message="Tests completed",
            level="INFO",
            task_id=None,
            project_id=None,
            metadata=metadata,
        )

        assert entry["metadata"] == metadata


class TestPublishLog:
    """Test publish_log method (synchronous)."""

    def test_publish_log_success(self):
        """Test successful log publishing."""
        publisher = LogPublisher()

        with patch("lazy_bird.services.log_publisher.get_redis") as mock_get_redis:
            mock_redis = Mock()
            mock_redis.publish.return_value = 1  # 1 subscriber
            mock_get_redis.return_value = mock_redis

            result = publisher.publish_log(
                message="Test message",
                level="INFO",
                task_id="task-123",
            )

            assert result is True
            assert mock_redis.publish.called
            assert mock_redis.lpush.called  # History storage

            # Check channel name
            call_args = mock_redis.publish.call_args[0]
            assert call_args[0] == "lazy_bird:logs:task:task-123"

            # Check message is JSON
            log_json = call_args[1]
            log_data = json.loads(log_json)
            assert log_data["message"] == "Test message"
            assert log_data["level"] == "INFO"

    def test_publish_log_with_metadata(self):
        """Test publishing log with metadata."""
        publisher = LogPublisher()

        with patch("lazy_bird.services.log_publisher.get_redis") as mock_get_redis:
            mock_redis = Mock()
            mock_redis.publish.return_value = 1
            mock_get_redis.return_value = mock_redis

            metadata = {"test": "value"}

            result = publisher.publish_log(
                message="Test",
                level="INFO",
                task_id="task-123",
                metadata=metadata,
            )

            assert result is True

            # Check metadata is included
            call_args = mock_redis.publish.call_args[0]
            log_data = json.loads(call_args[1])
            assert log_data["metadata"] == metadata

    def test_publish_log_connection_error(self):
        """Test publishing with Redis connection error."""
        publisher = LogPublisher()

        with patch("lazy_bird.services.log_publisher.get_redis") as mock_get_redis:
            from redis.exceptions import ConnectionError

            mock_get_redis.side_effect = ConnectionError("Connection failed")

            result = publisher.publish_log(
                message="Test",
                level="INFO",
                task_id="task-123",
            )

            assert result is False


@pytest.mark.asyncio
class TestPublishLogAsync:
    """Test publish_log_async method (asynchronous)."""

    async def test_publish_log_async_success(self):
        """Test successful async log publishing."""
        publisher = LogPublisher(use_async=True)

        with patch("lazy_bird.services.log_publisher.get_async_redis") as mock_get_redis:
            mock_redis = AsyncMock()
            mock_redis.publish.return_value = 1  # 1 subscriber
            mock_get_redis.return_value = mock_redis

            result = await publisher.publish_log_async(
                message="Test message",
                level="INFO",
                task_id="task-123",
            )

            assert result is True
            assert mock_redis.publish.called
            assert mock_redis.lpush.called  # History storage

    async def test_publish_log_async_connection_error(self):
        """Test async publishing with connection error."""
        publisher = LogPublisher(use_async=True)

        with patch("lazy_bird.services.log_publisher.get_async_redis") as mock_get_redis:
            from redis.exceptions import ConnectionError

            mock_get_redis.side_effect = ConnectionError("Connection failed")

            result = await publisher.publish_log_async(
                message="Test",
                level="INFO",
                task_id="task-123",
            )

            assert result is False


class TestGetLogHistory:
    """Test get_log_history method (synchronous)."""

    def test_get_log_history_success(self):
        """Test retrieving log history."""
        publisher = LogPublisher()

        with patch("lazy_bird.services.log_publisher.get_redis") as mock_get_redis:
            mock_redis = Mock()
            log_entries = [
                json.dumps({"message": "Log 1", "level": "INFO"}),
                json.dumps({"message": "Log 2", "level": "DEBUG"}),
            ]
            mock_redis.lrange.return_value = log_entries
            mock_get_redis.return_value = mock_redis

            history = publisher.get_log_history(task_id="task-123", limit=10)

            assert len(history) == 2
            assert history[0]["message"] == "Log 1"
            assert history[1]["message"] == "Log 2"

    def test_get_log_history_empty(self):
        """Test retrieving empty log history."""
        publisher = LogPublisher()

        with patch("lazy_bird.services.log_publisher.get_redis") as mock_get_redis:
            mock_redis = Mock()
            mock_redis.lrange.return_value = []
            mock_get_redis.return_value = mock_redis

            history = publisher.get_log_history(task_id="task-123")

            assert history == []

    def test_get_log_history_connection_error(self):
        """Test get history with connection error."""
        publisher = LogPublisher()

        with patch("lazy_bird.services.log_publisher.get_redis") as mock_get_redis:
            from redis.exceptions import ConnectionError

            mock_get_redis.side_effect = ConnectionError("Connection failed")

            history = publisher.get_log_history(task_id="task-123")

            assert history == []


@pytest.mark.asyncio
class TestGetLogHistoryAsync:
    """Test get_log_history_async method (asynchronous)."""

    async def test_get_log_history_async_success(self):
        """Test async log history retrieval."""
        publisher = LogPublisher(use_async=True)

        with patch("lazy_bird.services.log_publisher.get_async_redis") as mock_get_redis:
            mock_redis = AsyncMock()
            log_entries = [
                json.dumps({"message": "Log 1", "level": "INFO"}),
                json.dumps({"message": "Log 2", "level": "DEBUG"}),
            ]
            mock_redis.lrange.return_value = log_entries
            mock_get_redis.return_value = mock_redis

            history = await publisher.get_log_history_async(task_id="task-123")

            assert len(history) == 2
            assert history[0]["message"] == "Log 1"


class TestPublishTaskLog:
    """Test publish_task_log convenience function."""

    def test_publish_task_log_success(self):
        """Test convenience function for publishing task logs."""
        with patch("lazy_bird.services.log_publisher.get_redis") as mock_get_redis:
            mock_redis = Mock()
            mock_redis.publish.return_value = 1
            mock_get_redis.return_value = mock_redis

            result = publish_task_log(
                message="Test task log",
                task_id="task-123",
                level="INFO",
                test_framework="pytest",
            )

            assert result is True
            assert mock_redis.publish.called

            # Check metadata was passed
            call_args = mock_redis.publish.call_args[0]
            log_data = json.loads(call_args[1])
            assert log_data["metadata"] == {"test_framework": "pytest"}
