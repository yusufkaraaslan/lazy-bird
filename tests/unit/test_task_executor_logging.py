"""Unit tests for task executor log publishing integration.

Tests that task executor properly publishes logs during execution.
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, Mock, patch
from uuid import uuid4

import pytest


class TestTaskExecutorLogPublishing:
    """Test log publishing integration in task executor."""

    @pytest.mark.asyncio
    async def test_executor_publishes_start_log(self):
        """Test executor publishes log when task starts."""
        from lazy_bird.tasks.task_executor import _execute_task_async

        task_run_id = str(uuid4())

        # Mock TaskRun
        mock_task_run = Mock()
        mock_task_run.id = uuid4()
        mock_task_run.project_id = uuid4()
        mock_task_run.work_item_id = "issue-42"
        mock_task_run.work_item_title = "Add health system"
        mock_task_run.task_type = "feature"
        mock_task_run.complexity = "medium"
        mock_task_run.status = "queued"

        # Mock database
        class MockResult:
            def scalar_one_or_none(self):
                return mock_task_run

        async def mock_db_generator():
            mock_db = AsyncMock()
            mock_db.execute = AsyncMock(return_value=MockResult())
            yield mock_db

        # Mock LogPublisher
        mock_log_publisher = AsyncMock()

        with patch(
            "lazy_bird.tasks.task_executor.get_async_db", return_value=mock_db_generator()
        ):
            with patch(
                "lazy_bird.tasks.task_executor.LogPublisher",
                return_value=mock_log_publisher,
            ):
                # Execute task
                await _execute_task_async(task_run_id)

                # Verify start log was published
                assert mock_log_publisher.publish_log_async.called

                # Find the start log call
                start_log_call = None
                for call in mock_log_publisher.publish_log_async.call_args_list:
                    if "Starting task execution" in call[1].get("message", ""):
                        start_log_call = call
                        break

                assert start_log_call is not None
                assert start_log_call[1]["level"] == "INFO"
                assert start_log_call[1]["task_id"] == str(mock_task_run.id)

    @pytest.mark.asyncio
    async def test_executor_publishes_completion_log(self):
        """Test executor publishes log when task completes."""
        from lazy_bird.tasks.task_executor import _execute_task_async

        task_run_id = str(uuid4())

        # Mock TaskRun
        mock_task_run = Mock()
        mock_task_run.id = uuid4()
        mock_task_run.project_id = uuid4()
        mock_task_run.work_item_id = "issue-42"
        mock_task_run.work_item_title = "Add health system"
        mock_task_run.task_type = "feature"
        mock_task_run.complexity = "medium"
        mock_task_run.status = "queued"

        # Mock database
        class MockResult:
            def scalar_one_or_none(self):
                return mock_task_run

        async def mock_db_generator():
            mock_db = AsyncMock()
            mock_db.execute = AsyncMock(return_value=MockResult())
            yield mock_db

        # Mock LogPublisher
        mock_log_publisher = AsyncMock()

        with patch(
            "lazy_bird.tasks.task_executor.get_async_db", return_value=mock_db_generator()
        ):
            with patch(
                "lazy_bird.tasks.task_executor.LogPublisher",
                return_value=mock_log_publisher,
            ):
                # Execute task
                result = await _execute_task_async(task_run_id)

                # Verify success
                assert result["success"] is True

                # Find the completion log call
                completion_log_call = None
                for call in mock_log_publisher.publish_log_async.call_args_list:
                    if "completed successfully" in call[1].get("message", ""):
                        completion_log_call = call
                        break

                assert completion_log_call is not None
                assert completion_log_call[1]["level"] == "INFO"
                assert completion_log_call[1]["metadata"]["task_complete"] is True

    @pytest.mark.asyncio
    async def test_executor_publishes_error_log(self):
        """Test executor publishes error log when task fails."""
        from lazy_bird.tasks.task_executor import _execute_task_async

        task_run_id = str(uuid4())

        # Mock database that raises error during query execution
        mock_db = AsyncMock()
        mock_db.execute = AsyncMock(
            side_effect=RuntimeError("Database query failed")
        )

        async def mock_db_generator():
            yield mock_db

        # Mock LogPublisher
        mock_log_publisher = AsyncMock()

        with patch("lazy_bird.tasks.task_executor.get_async_db") as mock_get_async_db:
            mock_get_async_db.return_value = mock_db_generator()

            with patch(
                "lazy_bird.tasks.task_executor.LogPublisher",
                return_value=mock_log_publisher,
            ):
                # Execute task (should fail)
                result = await _execute_task_async(task_run_id)

                # Verify failure
                assert result["success"] is False
                assert "Database query failed" in result["error"]

                # Find the error log call
                error_log_call = None
                for call in mock_log_publisher.publish_log_async.call_args_list:
                    if "Task execution failed" in call[1].get("message", ""):
                        error_log_call = call
                        break

                assert error_log_call is not None
                assert error_log_call[1]["level"] == "ERROR"

    @pytest.mark.asyncio
    async def test_executor_publishes_step_logs(self):
        """Test executor publishes logs for each execution step."""
        from lazy_bird.tasks.task_executor import _execute_task_async

        task_run_id = str(uuid4())

        # Mock TaskRun
        mock_task_run = Mock()
        mock_task_run.id = uuid4()
        mock_task_run.project_id = uuid4()
        mock_task_run.work_item_id = "issue-42"
        mock_task_run.work_item_title = "Add health system"
        mock_task_run.task_type = "feature"
        mock_task_run.complexity = "medium"
        mock_task_run.status = "queued"

        # Mock database
        class MockResult:
            def scalar_one_or_none(self):
                return mock_task_run

        async def mock_db_generator():
            mock_db = AsyncMock()
            mock_db.execute = AsyncMock(return_value=MockResult())
            yield mock_db

        # Mock LogPublisher
        mock_log_publisher = AsyncMock()

        with patch(
            "lazy_bird.tasks.task_executor.get_async_db", return_value=mock_db_generator()
        ):
            with patch(
                "lazy_bird.tasks.task_executor.LogPublisher",
                return_value=mock_log_publisher,
            ):
                # Execute task
                await _execute_task_async(task_run_id)

                # Verify multiple step logs were published
                log_messages = [
                    call[1].get("message", "")
                    for call in mock_log_publisher.publish_log_async.call_args_list
                ]

                # Check for expected step logs
                assert any("Starting task execution" in msg for msg in log_messages)
                assert any("status updated to 'running'" in msg for msg in log_messages)
                assert any("Creating git worktree" in msg for msg in log_messages)
                assert any("Running Claude Code CLI" in msg for msg in log_messages)
                assert any("Executing tests" in msg for msg in log_messages)
                assert any("Creating pull request" in msg for msg in log_messages)
                assert any("Cleaning up worktree" in msg for msg in log_messages)
                assert any("completed successfully" in msg for msg in log_messages)

    @pytest.mark.asyncio
    async def test_executor_includes_metadata_in_logs(self):
        """Test executor includes metadata in log entries."""
        from lazy_bird.tasks.task_executor import _execute_task_async

        task_run_id = str(uuid4())

        # Mock TaskRun
        mock_task_run = Mock()
        mock_task_run.id = uuid4()
        mock_task_run.project_id = uuid4()
        mock_task_run.work_item_id = "issue-42"
        mock_task_run.work_item_title = "Add health system"
        mock_task_run.task_type = "feature"
        mock_task_run.complexity = "medium"
        mock_task_run.status = "queued"

        # Mock database
        class MockResult:
            def scalar_one_or_none(self):
                return mock_task_run

        async def mock_db_generator():
            mock_db = AsyncMock()
            mock_db.execute = AsyncMock(return_value=MockResult())
            yield mock_db

        # Mock LogPublisher
        mock_log_publisher = AsyncMock()

        with patch(
            "lazy_bird.tasks.task_executor.get_async_db", return_value=mock_db_generator()
        ):
            with patch(
                "lazy_bird.tasks.task_executor.LogPublisher",
                return_value=mock_log_publisher,
            ):
                # Execute task
                await _execute_task_async(task_run_id)

                # Find start log with metadata
                start_log_call = None
                for call in mock_log_publisher.publish_log_async.call_args_list:
                    if "Starting task execution" in call[1].get("message", ""):
                        start_log_call = call
                        break

                assert start_log_call is not None
                metadata = start_log_call[1].get("metadata", {})
                assert metadata["work_item_id"] == "issue-42"
                assert metadata["task_type"] == "feature"
                assert metadata["complexity"] == "medium"

    @pytest.mark.asyncio
    async def test_executor_handles_not_found_task(self):
        """Test executor publishes error log when task not found."""
        from lazy_bird.tasks.task_executor import _execute_task_async

        task_run_id = str(uuid4())

        # Mock database returning None
        class MockResult:
            def scalar_one_or_none(self):
                return None

        async def mock_db_generator():
            mock_db = AsyncMock()
            mock_db.execute = AsyncMock(return_value=MockResult())
            yield mock_db

        # Mock LogPublisher
        mock_log_publisher = AsyncMock()

        with patch(
            "lazy_bird.tasks.task_executor.get_async_db", return_value=mock_db_generator()
        ):
            with patch(
                "lazy_bird.tasks.task_executor.LogPublisher",
                return_value=mock_log_publisher,
            ):
                # Execute task
                result = await _execute_task_async(task_run_id)

                # Verify failure
                assert result["success"] is False
                assert "not found" in result["error"]

                # Verify error log was published
                assert mock_log_publisher.publish_log_async.called
                error_call = mock_log_publisher.publish_log_async.call_args
                assert error_call[1]["level"] == "ERROR"
                assert "not found" in error_call[1]["message"]


class TestTaskExecutorLogPublisherIntegration:
    """Test LogPublisher instance management in task executor."""

    @pytest.mark.asyncio
    async def test_executor_creates_async_log_publisher(self):
        """Test executor creates LogPublisher with async mode."""
        from lazy_bird.tasks.task_executor import _execute_task_async

        task_run_id = str(uuid4())

        # Mock database returning None to exit early
        class MockResult:
            def scalar_one_or_none(self):
                return None

        async def mock_db_generator():
            mock_db = AsyncMock()
            mock_db.execute = AsyncMock(return_value=MockResult())
            yield mock_db

        # Mock LogPublisher instance with AsyncMock
        mock_log_publisher_instance = AsyncMock()

        with patch("lazy_bird.tasks.task_executor.get_async_db") as mock_get_async_db:
            mock_get_async_db.return_value = mock_db_generator()

            with patch(
                "lazy_bird.tasks.task_executor.LogPublisher",
                return_value=mock_log_publisher_instance,
            ) as mock_log_publisher_class:
                # Execute task
                await _execute_task_async(task_run_id)

                # Verify LogPublisher was created with use_async=True
                mock_log_publisher_class.assert_called_once_with(use_async=True)
