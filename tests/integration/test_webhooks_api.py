"""Integration tests for Webhooks API endpoints.

Tests all 6 Webhook subscription CRUD endpoints including test delivery.
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from lazy_bird.api.main import app
from lazy_bird.models.webhook_subscription import WebhookSubscription


class TestListWebhooks:
    """Test GET /api/v1/webhooks endpoint."""

    async def test_list_webhooks_empty(self, test_client, test_api_key):
        """Test listing webhooks when none exist."""
        response = test_client.get(
            "/api/v1/webhooks",
            headers={"X-API-Key": test_api_key.key_hash},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert data["items"] == []

    async def test_list_webhooks_pagination(self, test_client, test_api_key, test_db):
        """Test webhooks pagination."""
        # Create 5 webhooks
        for i in range(5):
            webhook = WebhookSubscription(
                url=f"https://example{i}.com/webhook",
                secret=f"secret-key-{i}-16chars",
                events=["task.completed"],
                is_active=True,
                failure_count=0,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            )
            test_db.add(webhook)
        await test_db.commit()

        # Get page 1 with page_size=2
        response = test_client.get(
            "/api/v1/webhooks?page=1&page_size=2",
            headers={"X-API-Key": test_api_key.key_hash},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 5
        assert len(data["items"]) == 2
        assert data["pages"] == 3

    async def test_list_webhooks_filter_by_event(self, test_client, test_api_key, test_db):
        """Test filtering webhooks by event type."""
        # Create webhooks with different events
        webhook1 = WebhookSubscription(
            url="https://example1.com/webhook",
            secret="secret-key-1-16chars",
            events=["task.completed", "task.failed"],
            is_active=True,
            failure_count=0,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        webhook2 = WebhookSubscription(
            url="https://example2.com/webhook",
            secret="secret-key-2-16chars",
            events=["pr.created", "pr.merged"],
            is_active=True,
            failure_count=0,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        test_db.add_all([webhook1, webhook2])
        await test_db.commit()

        # Filter for task.completed
        response = test_client.get(
            "/api/v1/webhooks?event=task.completed",
            headers={"X-API-Key": test_api_key.key_hash},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert "task.completed" in data["items"][0]["events"]


class TestCreateWebhook:
    """Test POST /api/v1/webhooks endpoint."""

    async def test_create_webhook_success(self, test_client, test_api_key):
        """Test successful webhook subscription creation."""
        payload = {
            "url": "https://example.com/webhook",
            "secret": "my-webhook-secret-16chars-minimum",
            "events": ["task.completed", "task.failed", "pr.created"],
            "is_active": True,
            "description": "Production webhook for task events",
        }

        response = test_client.post(
            "/api/v1/webhooks",
            json=payload,
            headers={"X-API-Key": test_api_key.key_hash},
        )

        assert response.status_code == 201
        data = response.json()
        assert data["url"] == "https://example.com/webhook"
        assert set(data["events"]) == {"task.completed", "task.failed", "pr.created"}
        assert data["is_active"] is True
        assert data["failure_count"] == 0
        assert "id" in data

    async def test_create_webhook_project_scoped(self, test_client, test_api_key, test_project):
        """Test creating project-scoped webhook."""
        payload = {
            "url": "https://example.com/webhook",
            "secret": "project-webhook-secret-16chars",
            "events": ["task.completed"],
            "project_id": str(test_project.id),
        }

        response = test_client.post(
            "/api/v1/webhooks",
            json=payload,
            headers={"X-API-Key": test_api_key.key_hash},
        )

        assert response.status_code == 201
        data = response.json()
        assert data["project_id"] == str(test_project.id)

    async def test_create_webhook_global(self, test_client, test_api_key):
        """Test creating global webhook (no project_id)."""
        payload = {
            "url": "https://example.com/webhook",
            "secret": "global-webhook-secret-16chars",
            "events": ["task.completed"],
        }

        response = test_client.post(
            "/api/v1/webhooks",
            json=payload,
            headers={"X-API-Key": test_api_key.key_hash},
        )

        assert response.status_code == 201
        data = response.json()
        assert data["project_id"] is None  # Global webhook

    async def test_create_webhook_project_not_found(self, test_client, test_api_key):
        """Test creating webhook for non-existent project."""
        payload = {
            "url": "https://example.com/webhook",
            "secret": "webhook-secret-16chars",
            "events": ["task.completed"],
            "project_id": str(uuid4()),
        }

        response = test_client.post(
            "/api/v1/webhooks",
            json=payload,
            headers={"X-API-Key": test_api_key.key_hash},
        )

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    async def test_create_webhook_invalid_url(self, test_client, test_api_key):
        """Test creating webhook with invalid URL."""
        payload = {
            "url": "not-a-valid-url",
            "secret": "webhook-secret-16chars",
            "events": ["task.completed"],
        }

        response = test_client.post(
            "/api/v1/webhooks",
            json=payload,
            headers={"X-API-Key": test_api_key.key_hash},
        )

        assert response.status_code == 422  # Validation error

    async def test_create_webhook_secret_too_short(self, test_client, test_api_key):
        """Test creating webhook with secret shorter than 16 chars."""
        payload = {
            "url": "https://example.com/webhook",
            "secret": "short",  # Less than 16 chars
            "events": ["task.completed"],
        }

        response = test_client.post(
            "/api/v1/webhooks",
            json=payload,
            headers={"X-API-Key": test_api_key.key_hash},
        )

        assert response.status_code == 422  # Validation error


class TestGetWebhook:
    """Test GET /api/v1/webhooks/{subscription_id} endpoint."""

    async def test_get_webhook_success(self, test_client, test_api_key, test_db):
        """Test getting single webhook subscription."""
        webhook = WebhookSubscription(
            url="https://example.com/webhook",
            secret="webhook-secret-16chars",
            events=["task.completed", "pr.created"],
            is_active=True,
            failure_count=3,
            last_triggered_at=datetime.now(timezone.utc),
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        test_db.add(webhook)
        await test_db.commit()
        await test_db.refresh(webhook)

        response = test_client.get(
            f"/api/v1/webhooks/{webhook.id}",
            headers={"X-API-Key": test_api_key.key_hash},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(webhook.id)
        assert data["url"] == "https://example.com/webhook"
        assert data["failure_count"] == 3
        assert "last_triggered_at" in data

    async def test_get_webhook_not_found(self, test_client, test_api_key):
        """Test getting non-existent webhook."""
        response = test_client.get(
            f"/api/v1/webhooks/{uuid4()}",
            headers={"X-API-Key": test_api_key.key_hash},
        )

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()


class TestUpdateWebhook:
    """Test PATCH /api/v1/webhooks/{subscription_id} endpoint."""

    async def test_update_webhook_success(self, test_client, test_api_key, test_db):
        """Test successful webhook subscription update."""
        webhook = WebhookSubscription(
            url="https://example.com/webhook",
            secret="old-webhook-secret-16chars",
            events=["task.completed"],
            is_active=True,
            failure_count=0,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        test_db.add(webhook)
        await test_db.commit()
        await test_db.refresh(webhook)

        payload = {
            "url": "https://new-example.com/webhook",
            "events": ["task.completed", "task.failed", "pr.created"],
            "description": "Updated webhook description",
        }

        response = test_client.patch(
            f"/api/v1/webhooks/{webhook.id}",
            json=payload,
            headers={"X-API-Key": test_api_key.key_hash},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["url"] == "https://new-example.com/webhook"
        assert len(data["events"]) == 3
        assert data["description"] == "Updated webhook description"

    async def test_update_webhook_disable(self, test_client, test_api_key, test_db):
        """Test disabling webhook subscription."""
        webhook = WebhookSubscription(
            url="https://example.com/webhook",
            secret="webhook-secret-16chars",
            events=["task.completed"],
            is_active=True,
            failure_count=0,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        test_db.add(webhook)
        await test_db.commit()
        await test_db.refresh(webhook)

        payload = {"is_active": False}

        response = test_client.patch(
            f"/api/v1/webhooks/{webhook.id}",
            json=payload,
            headers={"X-API-Key": test_api_key.key_hash},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["is_active"] is False

    async def test_update_webhook_not_found(self, test_client, test_api_key):
        """Test updating non-existent webhook."""
        payload = {"is_active": False}

        response = test_client.patch(
            f"/api/v1/webhooks/{uuid4()}",
            json=payload,
            headers={"X-API-Key": test_api_key.key_hash},
        )

        assert response.status_code == 404


class TestDeleteWebhook:
    """Test DELETE /api/v1/webhooks/{subscription_id} endpoint."""

    async def test_delete_webhook_success(self, test_client, test_api_key, test_db):
        """Test successful webhook subscription deletion."""
        webhook = WebhookSubscription(
            url="https://example.com/webhook",
            secret="webhook-secret-16chars",
            events=["task.completed"],
            is_active=True,
            failure_count=0,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        test_db.add(webhook)
        await test_db.commit()
        await test_db.refresh(webhook)
        webhook_id = webhook.id

        response = test_client.delete(
            f"/api/v1/webhooks/{webhook_id}",
            headers={"X-API-Key": test_api_key.key_hash},
        )

        assert response.status_code == 204

        # Verify deleted
        get_response = test_client.get(
            f"/api/v1/webhooks/{webhook_id}",
            headers={"X-API-Key": test_api_key.key_hash},
        )
        assert get_response.status_code == 404

    async def test_delete_webhook_not_found(self, test_client, test_api_key):
        """Test deleting non-existent webhook."""
        response = test_client.delete(
            f"/api/v1/webhooks/{uuid4()}",
            headers={"X-API-Key": test_api_key.key_hash},
        )

        assert response.status_code == 404


class TestWebhookTestDelivery:
    """Test POST /api/v1/webhooks/{subscription_id}/test endpoint."""

    async def test_test_webhook_delivery_success(self, test_client, test_api_key, test_db):
        """Test successful test webhook delivery."""
        webhook = WebhookSubscription(
            url="https://example.com/webhook",
            secret="webhook-secret-16chars",
            events=["task.completed"],
            is_active=True,
            failure_count=0,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        test_db.add(webhook)
        await test_db.commit()
        await test_db.refresh(webhook)

        # Mock the test delivery to succeed
        with patch("lazy_bird.services.webhook_service.send_test_webhook") as mock_test:
            mock_test.return_value = {
                "success": True,
                "status_code": 200,
                "response_time_ms": 123.45,
                "message": "Test webhook delivered successfully",
            }

            response = test_client.post(
                f"/api/v1/webhooks/{webhook.id}/test",
                headers={"X-API-Key": test_api_key.key_hash},
            )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["status_code"] == 200
        assert "message" in data

    async def test_test_webhook_delivery_failure(self, test_client, test_api_key, test_db):
        """Test failed test webhook delivery."""
        webhook = WebhookSubscription(
            url="https://example.com/webhook",
            secret="webhook-secret-16chars",
            events=["task.completed"],
            is_active=True,
            failure_count=0,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        test_db.add(webhook)
        await test_db.commit()
        await test_db.refresh(webhook)

        # Mock the test delivery to fail
        with patch("lazy_bird.services.webhook_service.send_test_webhook") as mock_test:
            mock_test.return_value = {
                "success": False,
                "status_code": 500,
                "error": "Internal Server Error",
                "message": "Test webhook delivery failed: Internal Server Error",
            }

            response = test_client.post(
                f"/api/v1/webhooks/{webhook.id}/test",
                headers={"X-API-Key": test_api_key.key_hash},
            )

        assert response.status_code == 200  # Endpoint returns 200 even if delivery fails
        data = response.json()
        assert data["success"] is False
        assert data["status_code"] == 500

    async def test_test_webhook_delivery_not_found(self, test_client, test_api_key):
        """Test test delivery for non-existent webhook."""
        response = test_client.post(
            f"/api/v1/webhooks/{uuid4()}/test",
            headers={"X-API-Key": test_api_key.key_hash},
        )

        assert response.status_code == 404


class TestWebhookDeliveryStatistics:
    """Test webhook delivery statistics tracking."""

    async def test_webhook_tracks_last_triggered_at(self, test_client, test_api_key, test_db):
        """Test that webhook tracks last successful delivery time."""
        webhook = WebhookSubscription(
            url="https://example.com/webhook",
            secret="webhook-secret-16chars",
            events=["task.completed"],
            is_active=True,
            failure_count=0,
            last_triggered_at=None,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        test_db.add(webhook)
        await test_db.commit()
        await test_db.refresh(webhook)

        # Get webhook before any deliveries
        response = test_client.get(
            f"/api/v1/webhooks/{webhook.id}",
            headers={"X-API-Key": test_api_key.key_hash},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["last_triggered_at"] is None
        assert data["failure_count"] == 0

    async def test_webhook_tracks_failure_count(self, test_client, test_api_key, test_db):
        """Test that webhook tracks consecutive failures."""
        webhook = WebhookSubscription(
            url="https://example.com/webhook",
            secret="webhook-secret-16chars",
            events=["task.completed"],
            is_active=True,
            failure_count=5,
            last_failure_at=datetime.now(timezone.utc),
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        test_db.add(webhook)
        await test_db.commit()
        await test_db.refresh(webhook)

        response = test_client.get(
            f"/api/v1/webhooks/{webhook.id}",
            headers={"X-API-Key": test_api_key.key_hash},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["failure_count"] == 5
        assert data["last_failure_at"] is not None
