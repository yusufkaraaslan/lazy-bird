"""Unit tests for WebhookSubscription model.

Tests WebhookSubscription model fields, validation, and relationships.
"""

from datetime import datetime, timezone
from uuid import uuid4

import pytest

from lazy_bird.models.webhook_subscription import WebhookSubscription


class TestWebhookSubscriptionCreation:
    """Test WebhookSubscription model creation and initialization."""

    def test_basic_creation(self):
        """Test creating a webhook subscription with minimum required fields."""
        subscription = WebhookSubscription(
            url="https://example.com/webhook",
            secret="supersecret",
            events=["task.started", "task.completed"],
        )

        assert subscription.url == "https://example.com/webhook"
        assert subscription.secret == "supersecret"
        assert subscription.events == ["task.started", "task.completed"]

    def test_creation_with_all_fields(self):
        """Test creating a subscription with all fields."""
        subscription_id = uuid4()
        project_id = uuid4()
        triggered_at = datetime.now(timezone.utc)
        failure_at = datetime.now(timezone.utc)

        subscription = WebhookSubscription(
            id=subscription_id,
            url="https://api.example.com/webhooks/lazy-bird",
            secret="my-webhook-secret",
            project_id=project_id,
            events=["task.started", "task.completed", "task.failed"],
            is_active=True,
            last_triggered_at=triggered_at,
            failure_count=5,
            last_failure_at=failure_at,
            description="Production webhook for task monitoring",
        )

        assert subscription.id == subscription_id
        assert subscription.project_id == project_id
        assert subscription.is_active is True
        assert subscription.last_triggered_at == triggered_at
        assert subscription.failure_count == 5
        assert subscription.last_failure_at == failure_at
        assert subscription.description == "Production webhook for task monitoring"

    def test_default_values(self):
        """Test that default values are set correctly when explicitly provided."""
        subscription = WebhookSubscription(
            url="https://example.com/webhook",
            secret="secret",
            events=["task.completed"],
            is_active=True,
            failure_count=0,
        )

        # Default values should be set as provided
        assert subscription.is_active is True
        assert subscription.failure_count == 0

    def test_global_subscription_no_project(self):
        """Test creating a global subscription (no project_id)."""
        subscription = WebhookSubscription(
            url="https://example.com/webhook",
            secret="secret",
            events=["task.completed"],
            project_id=None,
        )

        assert subscription.project_id is None


class TestWebhookSubscriptionFields:
    """Test WebhookSubscription field behavior."""

    def test_url_with_https(self):
        """Test URL with HTTPS protocol."""
        subscription = WebhookSubscription(
            url="https://secure.example.com/webhook",
            secret="secret",
            events=["task.completed"],
        )

        assert subscription.url.startswith("https://")

    def test_url_with_http(self):
        """Test URL with HTTP protocol."""
        subscription = WebhookSubscription(
            url="http://example.com/webhook",
            secret="secret",
            events=["task.completed"],
        )

        assert subscription.url.startswith("http://")

    def test_multiple_events(self):
        """Test subscription with multiple event types."""
        events = [
            "task.started",
            "task.completed",
            "task.failed",
            "task.cancelled",
            "test.passed",
            "test.failed",
        ]

        subscription = WebhookSubscription(
            url="https://example.com/webhook",
            secret="secret",
            events=events,
        )

        assert len(subscription.events) == 6
        assert "task.started" in subscription.events
        assert "test.failed" in subscription.events

    def test_single_event(self):
        """Test subscription with single event type."""
        subscription = WebhookSubscription(
            url="https://example.com/webhook",
            secret="secret",
            events=["task.completed"],
        )

        assert len(subscription.events) == 1
        assert subscription.events[0] == "task.completed"

    def test_failure_tracking(self):
        """Test failure tracking fields."""
        failure_time = datetime.now(timezone.utc)

        subscription = WebhookSubscription(
            url="https://example.com/webhook",
            secret="secret",
            events=["task.completed"],
            failure_count=3,
            last_failure_at=failure_time,
        )

        assert subscription.failure_count == 3
        assert subscription.last_failure_at == failure_time

    def test_last_triggered_at(self):
        """Test last_triggered_at field."""
        triggered_time = datetime.now(timezone.utc)

        subscription = WebhookSubscription(
            url="https://example.com/webhook",
            secret="secret",
            events=["task.completed"],
            last_triggered_at=triggered_time,
        )

        assert subscription.last_triggered_at == triggered_time

    def test_inactive_subscription(self):
        """Test creating an inactive subscription."""
        subscription = WebhookSubscription(
            url="https://example.com/webhook",
            secret="secret",
            events=["task.completed"],
            is_active=False,
        )

        assert subscription.is_active is False


class TestWebhookSubscriptionRelationships:
    """Test WebhookSubscription relationships."""

    def test_project_specific_subscription(self):
        """Test subscription with project_id set."""
        project_id = uuid4()

        subscription = WebhookSubscription(
            url="https://example.com/webhook",
            secret="secret",
            events=["task.completed"],
            project_id=project_id,
        )

        assert subscription.project_id == project_id

    def test_global_subscription(self):
        """Test global subscription without project_id."""
        subscription = WebhookSubscription(
            url="https://example.com/webhook",
            secret="secret",
            events=["task.completed"],
            project_id=None,
        )

        assert subscription.project_id is None


class TestWebhookSubscriptionRepr:
    """Test __repr__() method."""

    def test_repr_active(self):
        """Test __repr__() for active subscription."""
        subscription = WebhookSubscription(
            url="https://example.com/webhook",
            secret="secret",
            events=["task.completed"],
            is_active=True,
        )

        repr_string = repr(subscription)

        assert "WebhookSubscription" in repr_string
        assert "https://example.com/webhook" in repr_string
        assert "active=True" in repr_string

    def test_repr_inactive(self):
        """Test __repr__() for inactive subscription."""
        subscription = WebhookSubscription(
            url="https://example.com/webhook",
            secret="secret",
            events=["task.completed"],
            is_active=False,
        )

        repr_string = repr(subscription)

        assert "active=False" in repr_string


class TestWebhookSubscriptionEventTypes:
    """Test various event type combinations."""

    def test_task_lifecycle_events(self):
        """Test subscription to all task lifecycle events."""
        events = [
            "task.queued",
            "task.started",
            "task.running",
            "task.completed",
            "task.failed",
            "task.cancelled",
        ]

        subscription = WebhookSubscription(
            url="https://example.com/webhook",
            secret="secret",
            events=events,
        )

        assert all(event in subscription.events for event in events)

    def test_test_execution_events(self):
        """Test subscription to test execution events."""
        events = [
            "test.started",
            "test.passed",
            "test.failed",
            "test.skipped",
        ]

        subscription = WebhookSubscription(
            url="https://example.com/webhook",
            secret="secret",
            events=events,
        )

        assert len(subscription.events) == 4

    def test_build_events(self):
        """Test subscription to build events."""
        events = [
            "build.started",
            "build.succeeded",
            "build.failed",
        ]

        subscription = WebhookSubscription(
            url="https://example.com/webhook",
            secret="secret",
            events=events,
        )

        assert "build.started" in subscription.events
        assert "build.succeeded" in subscription.events
        assert "build.failed" in subscription.events

    def test_pr_events(self):
        """Test subscription to pull request events."""
        events = [
            "pr.created",
            "pr.updated",
            "pr.merged",
            "pr.closed",
        ]

        subscription = WebhookSubscription(
            url="https://example.com/webhook",
            secret="secret",
            events=events,
        )

        assert len(subscription.events) == 4


class TestWebhookSubscriptionOptionalFields:
    """Test optional field handling."""

    def test_no_description(self):
        """Test subscription without description."""
        subscription = WebhookSubscription(
            url="https://example.com/webhook",
            secret="secret",
            events=["task.completed"],
            description=None,
        )

        assert subscription.description is None

    def test_with_description(self):
        """Test subscription with description."""
        subscription = WebhookSubscription(
            url="https://example.com/webhook",
            secret="secret",
            events=["task.completed"],
            description="Webhook for production monitoring",
        )

        assert subscription.description == "Webhook for production monitoring"

    def test_no_failure_data(self):
        """Test subscription with no failure data."""
        subscription = WebhookSubscription(
            url="https://example.com/webhook",
            secret="secret",
            events=["task.completed"],
            failure_count=0,
            last_failure_at=None,
        )

        assert subscription.failure_count == 0
        assert subscription.last_failure_at is None

    def test_no_trigger_data(self):
        """Test subscription that has never been triggered."""
        subscription = WebhookSubscription(
            url="https://example.com/webhook",
            secret="secret",
            events=["task.completed"],
            last_triggered_at=None,
        )

        assert subscription.last_triggered_at is None
