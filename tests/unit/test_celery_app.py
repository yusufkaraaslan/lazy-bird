"""Unit tests for Celery application configuration.

Tests Celery app initialization, configuration, and basic functionality.
"""

import pytest
from celery import Celery

from lazy_bird.tasks import app, debug_task


class TestCeleryApp:
    """Test Celery application initialization and configuration."""

    def test_celery_app_instance(self):
        """Test that Celery app is properly instantiated."""
        assert isinstance(app, Celery)
        assert app.main == "lazy_bird"

    def test_celery_app_config_loaded(self):
        """Test that Celery configuration is loaded."""
        # Check broker URL is set
        assert app.conf.broker_url is not None
        assert "redis://" in app.conf.broker_url

        # Check result backend is set
        assert app.conf.result_backend is not None
        assert "redis://" in app.conf.result_backend

    def test_celery_serializer_config(self):
        """Test task serialization configuration."""
        assert app.conf.task_serializer == "json"
        assert app.conf.result_serializer == "json"
        assert "json" in app.conf.accept_content

    def test_celery_task_time_limits(self):
        """Test task time limit configuration."""
        assert app.conf.task_soft_time_limit == 3600  # 1 hour
        assert app.conf.task_time_limit == 3900  # 65 minutes

    def test_celery_worker_settings(self):
        """Test worker configuration."""
        assert app.conf.worker_prefetch_multiplier == 1
        assert app.conf.task_acks_late is True
        assert app.conf.task_reject_on_worker_lost is True

    def test_celery_queues_configured(self):
        """Test that task queues are configured."""
        queues = app.conf.task_queues
        assert queues is not None
        assert len(queues) == 3  # default, high_priority, low_priority

        queue_names = [q.name for q in queues]
        assert "default" in queue_names
        assert "high_priority" in queue_names
        assert "low_priority" in queue_names

    def test_celery_task_routes_configured(self):
        """Test that task routing is configured."""
        routes = app.conf.task_routes
        assert routes is not None
        assert isinstance(routes, dict)

        # Check some expected routes exist
        assert "lazy_bird.tasks.queue_processor.process_queue" in routes

    def test_celery_beat_schedule_configured(self):
        """Test that beat schedule is configured."""
        schedule = app.conf.beat_schedule
        assert schedule is not None
        assert isinstance(schedule, dict)

        # Check periodic tasks are scheduled
        assert "process-queue-every-60-seconds" in schedule
        assert schedule["process-queue-every-60-seconds"]["schedule"] == 60.0

        assert "cleanup-old-worktrees-daily" in schedule
        assert schedule["cleanup-old-worktrees-daily"]["schedule"] == 86400.0

    def test_celery_timezone_utc(self):
        """Test that timezone is set to UTC."""
        assert app.conf.timezone == "UTC"
        assert app.conf.enable_utc is True

    def test_celery_result_settings(self):
        """Test result storage settings."""
        assert app.conf.result_expires == 3600  # 1 hour
        assert app.conf.result_extended is True

    def test_celery_monitoring_enabled(self):
        """Test that monitoring settings are enabled."""
        assert app.conf.worker_send_task_events is True
        assert app.conf.task_send_sent_event is True
        assert app.conf.task_track_started is True


class TestDebugTask:
    """Test debug task functionality."""

    def test_debug_task_exists(self):
        """Test that debug task is registered."""
        assert debug_task is not None
        assert hasattr(debug_task, "delay")
        assert hasattr(debug_task, "apply_async")

    def test_debug_task_eager_mode(self):
        """Test debug task in eager mode (immediate execution)."""
        # Configure eager mode for this test
        app.conf.task_always_eager = True
        app.conf.task_eager_propagates = True

        # Execute task
        result = debug_task.delay()

        # Check result
        assert result is not None
        task_result = result.get()
        assert task_result["status"] == "ok"
        assert "celery_version" in task_result

    def test_debug_task_signature(self):
        """Test creating task signature."""
        signature = debug_task.s()
        assert signature is not None
        assert signature.task == debug_task.name


class TestCeleryQueuePriorities:
    """Test queue priority configuration."""

    def test_default_queue_has_priority(self):
        """Test that default queue supports priorities."""
        queues = {q.name: q for q in app.conf.task_queues}
        default_queue = queues["default"]

        assert default_queue.queue_arguments is not None
        assert "x-max-priority" in default_queue.queue_arguments
        assert default_queue.queue_arguments["x-max-priority"] == 10

    def test_high_priority_queue_configured(self):
        """Test that high priority queue exists."""
        queues = {q.name: q for q in app.conf.task_queues}
        high_priority_queue = queues["high_priority"]

        assert high_priority_queue is not None
        assert high_priority_queue.routing_key == "high.#"

    def test_low_priority_queue_configured(self):
        """Test that low priority queue exists."""
        queues = {q.name: q for q in app.conf.task_queues}
        low_priority_queue = queues["low_priority"]

        assert low_priority_queue is not None
        assert low_priority_queue.routing_key == "low.#"


class TestCeleryRetrySettings:
    """Test task retry configuration."""

    def test_task_retry_enabled(self):
        """Test that task auto-retry is enabled."""
        assert app.conf.task_autoretry_for == (Exception,)

    def test_task_retry_max_retries(self):
        """Test max retries configuration."""
        retry_kwargs = app.conf.task_retry_kwargs
        assert retry_kwargs is not None
        assert retry_kwargs["max_retries"] == 3

    def test_task_retry_delay(self):
        """Test retry delay configuration."""
        assert app.conf.task_default_retry_delay == 60  # 60 seconds
