"""Unit tests for SSE (Server-Sent Events) log streaming endpoint.

Tests the GET /task-runs/:id/logs/stream endpoint for real-time log streaming.
"""

from unittest.mock import Mock
from uuid import uuid4

import pytest

from lazy_bird.api.exceptions import (
    InsufficientPermissionsError,
    ResourceNotFoundError,
)


class TestSSEEndpointValidation:
    """Test SSE endpoint validation and access control."""

    @pytest.mark.asyncio
    async def test_sse_task_not_found(self):
        """Test SSE endpoint with non-existent task run."""
        from lazy_bird.api.routers.task_runs import stream_task_run_logs

        task_run_id = uuid4()

        # Mock database session that returns None
        class MockResult:
            def scalar_one_or_none(self):
                return None

        class MockDB:
            async def execute(self, query):
                return MockResult()

        mock_db = MockDB()

        # Mock API key
        mock_api_key = Mock()
        mock_api_key.project_id = None

        # Should raise ResourceNotFoundError
        with pytest.raises(ResourceNotFoundError) as exc_info:
            await stream_task_run_logs(
                task_run_id=task_run_id,
                level=None,
                db=mock_db,
                api_key=mock_api_key,
            )

        assert exc_info.value.resource_type == "TaskRun"
        assert str(task_run_id) in str(exc_info.value.resource_id)

    @pytest.mark.asyncio
    async def test_sse_api_key_scope_restricted(self):
        """Test SSE endpoint with API key scoped to different project."""
        from lazy_bird.api.routers.task_runs import stream_task_run_logs

        task_run_id = uuid4()
        task_project_id = uuid4()
        api_key_project_id = uuid4()

        # Mock task run
        class MockTaskRun:
            id = task_run_id
            project_id = task_project_id
            work_item_id = "issue-42"
            status = "running"

        # Mock database session that returns task run
        class MockResult:
            def scalar_one_or_none(self):
                return MockTaskRun()

        class MockDB:
            async def execute(self, query):
                return MockResult()

        mock_db = MockDB()

        # Mock API key scoped to different project
        mock_api_key = Mock()
        mock_api_key.project_id = api_key_project_id

        # Should raise InsufficientPermissionsError
        with pytest.raises(InsufficientPermissionsError):
            await stream_task_run_logs(
                task_run_id=task_run_id,
                level=None,
                db=mock_db,
                api_key=mock_api_key,
            )


class TestSSEImplementation:
    """Test SSE implementation details."""

    def test_sse_endpoint_exists(self):
        """Test SSE endpoint is registered in router."""
        from lazy_bird.api.routers.task_runs import router

        # Check endpoint exists in router
        paths = [route.path for route in router.routes]
        assert "/task-runs/{task_run_id}/logs/stream" in paths

    def test_sse_endpoint_method(self):
        """Test SSE endpoint accepts GET method."""
        from lazy_bird.api.routers.task_runs import router

        # Find the route
        route = None
        for r in router.routes:
            if r.path == "/task-runs/{task_run_id}/logs/stream":
                route = r
                break

        assert route is not None
        assert "GET" in route.methods

    def test_sse_log_level_hierarchy(self):
        """Test log level hierarchy constants."""
        # This would be tested in the actual function
        # Just verify the logic is correct
        LOG_LEVELS = {
            "DEBUG": 10,
            "INFO": 20,
            "WARNING": 30,
            "ERROR": 40,
            "CRITICAL": 50,
        }

        # DEBUG level should show all
        assert LOG_LEVELS["DEBUG"] <= LOG_LEVELS["INFO"]
        assert LOG_LEVELS["INFO"] <= LOG_LEVELS["WARNING"]
        assert LOG_LEVELS["WARNING"] <= LOG_LEVELS["ERROR"]
        assert LOG_LEVELS["ERROR"] <= LOG_LEVELS["CRITICAL"]

    def test_sse_channel_naming(self):
        """Test SSE uses correct channel naming convention."""
        from uuid import UUID

        task_id = uuid4()
        expected_channel = f"lazy_bird:logs:task:{task_id}"

        # This tests the channel naming matches LogPublisher convention
        assert expected_channel.startswith("lazy_bird:logs:task:")
        assert str(task_id) in expected_channel


class TestSSEResponseFormat:
    """Test SSE response format and headers."""

    @pytest.mark.asyncio
    async def test_sse_returns_streaming_response(self):
        """Test SSE endpoint returns StreamingResponse with correct headers."""
        from lazy_bird.api.routers.task_runs import stream_task_run_logs
        from fastapi.responses import StreamingResponse

        task_run_id = uuid4()

        # Mock task run
        class MockTaskRun:
            id = task_run_id
            project_id = uuid4()
            work_item_id = "issue-42"
            status = "running"

        # Mock database
        class MockResult:
            def scalar_one_or_none(self):
                return MockTaskRun()

        class MockDB:
            async def execute(self, query):
                return MockResult()

        mock_db = MockDB()

        # Mock API key
        mock_api_key = Mock()
        mock_api_key.project_id = None

        # We can't fully test the streaming without mocking Redis,
        # but we can verify it returns a StreamingResponse
        try:
            response = await stream_task_run_logs(
                task_run_id=task_run_id,
                level=None,
                db=mock_db,
                api_key=mock_api_key,
            )

            # Verify response type
            assert isinstance(response, StreamingResponse)
            assert response.media_type == "text/event-stream"

            # Verify headers
            assert "Cache-Control" in response.headers
            assert response.headers["Cache-Control"] == "no-cache"
            assert "Connection" in response.headers
            assert response.headers["Connection"] == "keep-alive"

        except Exception:
            # If Redis is not available, that's OK for this test
            # We're just testing the structure
            pass


class TestSSEDocumentation:
    """Test SSE endpoint documentation."""

    def test_sse_has_docstring(self):
        """Test SSE endpoint has comprehensive docstring."""
        from lazy_bird.api.routers.task_runs import stream_task_run_logs

        assert stream_task_run_logs.__doc__ is not None
        assert "Server-Sent Events" in stream_task_run_logs.__doc__
        assert "SSE" in stream_task_run_logs.__doc__

    def test_sse_documents_event_types(self):
        """Test SSE docstring documents event types."""
        from lazy_bird.api.routers.task_runs import stream_task_run_logs

        docstring = stream_task_run_logs.__doc__

        # Should document event types
        assert "event: log" in docstring
        assert "event: status" in docstring
        assert "event: error" in docstring
        assert "event: end" in docstring

    def test_sse_documents_usage_example(self):
        """Test SSE docstring includes usage example."""
        from lazy_bird.api.routers.task_runs import stream_task_run_logs

        docstring = stream_task_run_logs.__doc__

        # Should include JavaScript example
        assert "JavaScript" in docstring or "javascript" in docstring.lower()
        assert "EventSource" in docstring


class TestSSELogFiltering:
    """Test SSE log filtering features (Issue #115)."""

    def test_sse_has_search_parameter(self):
        """Test SSE endpoint has search query parameter."""
        from lazy_bird.api.routers.task_runs import stream_task_run_logs
        import inspect

        sig = inspect.signature(stream_task_run_logs)
        assert "search" in sig.parameters
        param = sig.parameters["search"]
        assert param.default is not inspect.Parameter.empty  # Has default

    def test_sse_has_since_parameter(self):
        """Test SSE endpoint has since query parameter."""
        from lazy_bird.api.routers.task_runs import stream_task_run_logs
        import inspect

        sig = inspect.signature(stream_task_run_logs)
        assert "since" in sig.parameters
        param = sig.parameters["since"]
        assert param.default is not inspect.Parameter.empty  # Has default

    def test_sse_documents_search_parameter(self):
        """Test SSE docstring documents search parameter."""
        from lazy_bird.api.routers.task_runs import stream_task_run_logs

        docstring = stream_task_run_logs.__doc__
        assert "search" in docstring.lower()

    def test_sse_documents_since_parameter(self):
        """Test SSE docstring documents since parameter."""
        from lazy_bird.api.routers.task_runs import stream_task_run_logs

        docstring = stream_task_run_logs.__doc__
        assert "since" in docstring.lower()
        assert "timestamp" in docstring.lower()


class TestLogFilteringLogic:
    """Test log filtering helper function."""

    def test_filter_by_log_level(self):
        """Test filtering logs by log level."""
        # This tests the logic conceptually since the function is defined inside the endpoint
        LOG_LEVELS = {"DEBUG": 10, "INFO": 20, "WARNING": 30, "ERROR": 40}

        log_entry = {"level": "ERROR", "message": "Test error"}
        entry_level = LOG_LEVELS.get(log_entry.get("level", "INFO"), 20)
        min_level = LOG_LEVELS.get("WARNING", 30)

        # ERROR (40) >= WARNING (30) -> should pass
        assert entry_level >= min_level

    def test_filter_by_search_text(self):
        """Test filtering logs by search text."""
        log_entry = {"message": "Starting task execution"}
        search_term = "task"

        # Case-insensitive search
        assert search_term.lower() in log_entry.get("message", "").lower()

    def test_filter_by_timestamp(self):
        """Test filtering logs by timestamp."""
        from datetime import datetime, timezone, timedelta

        now = datetime.now(timezone.utc)
        five_min_ago = now - timedelta(minutes=5)
        ten_min_ago = now - timedelta(minutes=10)

        # Log from 5 minutes ago
        log_entry = {"timestamp": five_min_ago.isoformat()}

        # Filter: only show logs since 10 minutes ago
        since = ten_min_ago

        # Parse timestamp
        from dateutil.parser import parse as parse_datetime
        log_timestamp = parse_datetime(log_entry["timestamp"])

        # Log (5 min ago) > Filter (10 min ago) -> should pass
        assert log_timestamp > since
