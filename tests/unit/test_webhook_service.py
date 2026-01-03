"""Unit tests for webhook service functions.

Tests HMAC signature generation, webhook delivery, retry logic, and event publishing.
"""

import asyncio
import json
from datetime import datetime, timezone
from typing import Dict, Any
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import httpx
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from lazy_bird.models.webhook_subscription import WebhookSubscription
from lazy_bird.services.webhook_service import (
    MAX_CONSECUTIVE_FAILURES,
    MAX_RETRIES,
    deliver_webhook,
    deliver_webhook_with_retry,
    generate_webhook_signature,
    publish_event,
    send_test_webhook,
    verify_webhook_signature,
)


class TestHMACSignatures:
    """Test HMAC-SHA256 signature generation and verification."""

    def test_generate_signature_basic(self):
        """Test basic HMAC signature generation."""
        payload = '{"event": "task.completed"}'
        secret = "my-secret-key-12345"

        signature = generate_webhook_signature(payload, secret)

        assert signature is not None
        assert len(signature) == 64  # SHA-256 produces 64 hex characters
        assert all(c in "0123456789abcdef" for c in signature)

    def test_generate_signature_deterministic(self):
        """Test that same payload + secret generates same signature."""
        payload = '{"event": "task.completed", "data": {"id": "123"}}'
        secret = "my-secret-key"

        sig1 = generate_webhook_signature(payload, secret)
        sig2 = generate_webhook_signature(payload, secret)

        assert sig1 == sig2

    def test_generate_signature_different_payload(self):
        """Test that different payloads generate different signatures."""
        secret = "my-secret-key"
        payload1 = '{"event": "task.completed"}'
        payload2 = '{"event": "task.failed"}'

        sig1 = generate_webhook_signature(payload1, secret)
        sig2 = generate_webhook_signature(payload2, secret)

        assert sig1 != sig2

    def test_generate_signature_different_secret(self):
        """Test that different secrets generate different signatures."""
        payload = '{"event": "task.completed"}'
        secret1 = "secret-key-one"
        secret2 = "secret-key-two"

        sig1 = generate_webhook_signature(payload, secret1)
        sig2 = generate_webhook_signature(payload, secret2)

        assert sig1 != sig2

    def test_verify_signature_valid(self):
        """Test signature verification with valid signature."""
        payload = '{"event": "task.completed"}'
        secret = "my-secret-key-12345"

        signature = generate_webhook_signature(payload, secret)
        is_valid = verify_webhook_signature(payload, secret, signature)

        assert is_valid is True

    def test_verify_signature_invalid(self):
        """Test signature verification with invalid signature."""
        payload = '{"event": "task.completed"}'
        secret = "my-secret-key-12345"

        is_valid = verify_webhook_signature(payload, secret, "invalid_signature")

        assert is_valid is False

    def test_verify_signature_wrong_secret(self):
        """Test signature verification with wrong secret."""
        payload = '{"event": "task.completed"}'
        secret1 = "secret-key-one"
        secret2 = "secret-key-two"

        signature = generate_webhook_signature(payload, secret1)
        is_valid = verify_webhook_signature(payload, secret2, signature)

        assert is_valid is False

    def test_verify_signature_wrong_payload(self):
        """Test signature verification with tampered payload."""
        payload1 = '{"event": "task.completed"}'
        payload2 = '{"event": "task.failed"}'
        secret = "my-secret-key"

        signature = generate_webhook_signature(payload1, secret)
        is_valid = verify_webhook_signature(payload2, secret, signature)

        assert is_valid is False

    def test_signature_with_special_characters(self):
        """Test signature generation with special characters in payload."""
        payload = '{"message": "Test with émojis 🎉 and spëcial chars: @#$%"}'
        secret = "my-secret-key"

        signature = generate_webhook_signature(payload, secret)
        is_valid = verify_webhook_signature(payload, secret, signature)

        assert is_valid is True
        assert len(signature) == 64


class TestWebhookDelivery:
    """Test webhook HTTP delivery."""

    @pytest.mark.asyncio
    async def test_deliver_webhook_success(self):
        """Test successful webhook delivery."""
        url = "https://example.com/webhook"
        payload = {"event": "task.completed", "data": {"id": "123"}}
        secret = "my-secret-key"

        # Mock successful HTTP response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = '{"status": "ok"}'

        with patch("lazy_bird.services.webhook_service.httpx.AsyncClient") as mock_client:
            mock_client_instance = AsyncMock()
            mock_client_instance.post = AsyncMock(return_value=mock_response)
            mock_client.return_value.__aenter__.return_value = mock_client_instance

            result = await deliver_webhook(url, payload, secret)

        assert result["success"] is True
        assert result["status_code"] == 200
        assert "response_time_ms" in result
        assert result["response_time_ms"] > 0

        # Verify correct headers were sent
        call_args = mock_client_instance.post.call_args
        headers = call_args.kwargs["headers"]
        assert "X-Lazy-Bird-Signature" in headers
        assert headers["X-Lazy-Bird-Signature"].startswith("sha256=")
        assert headers["X-Lazy-Bird-Event"] == "task.completed"
        assert headers["Content-Type"] == "application/json"

    @pytest.mark.asyncio
    async def test_deliver_webhook_failure_4xx(self):
        """Test webhook delivery with 4xx error."""
        url = "https://example.com/webhook"
        payload = {"event": "task.completed"}
        secret = "my-secret-key"

        # Mock 404 response
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.text = "Not Found"

        with patch("lazy_bird.services.webhook_service.httpx.AsyncClient") as mock_client:
            mock_client_instance = AsyncMock()
            mock_client_instance.post = AsyncMock(return_value=mock_response)
            mock_client.return_value.__aenter__.return_value = mock_client_instance

            result = await deliver_webhook(url, payload, secret)

        assert result["success"] is False
        assert result["status_code"] == 404

    @pytest.mark.asyncio
    async def test_deliver_webhook_failure_5xx(self):
        """Test webhook delivery with 5xx error."""
        url = "https://example.com/webhook"
        payload = {"event": "task.completed"}
        secret = "my-secret-key"

        # Mock 500 response
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"

        with patch("lazy_bird.services.webhook_service.httpx.AsyncClient") as mock_client:
            mock_client_instance = AsyncMock()
            mock_client_instance.post = AsyncMock(return_value=mock_response)
            mock_client.return_value.__aenter__.return_value = mock_client_instance

            result = await deliver_webhook(url, payload, secret)

        assert result["success"] is False
        assert result["status_code"] == 500

    @pytest.mark.asyncio
    async def test_deliver_webhook_timeout(self):
        """Test webhook delivery with timeout."""
        url = "https://example.com/webhook"
        payload = {"event": "task.completed"}
        secret = "my-secret-key"

        with patch("lazy_bird.services.webhook_service.httpx.AsyncClient") as mock_client:
            mock_client_instance = AsyncMock()
            mock_client_instance.post = AsyncMock(side_effect=httpx.TimeoutException("Timeout"))
            mock_client.return_value.__aenter__.return_value = mock_client_instance

            result = await deliver_webhook(url, payload, secret, timeout=1)

        assert result["success"] is False
        assert result["status_code"] == 0
        assert "timeout" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_deliver_webhook_connection_error(self):
        """Test webhook delivery with connection error."""
        url = "https://example.com/webhook"
        payload = {"event": "task.completed"}
        secret = "my-secret-key"

        with patch("lazy_bird.services.webhook_service.httpx.AsyncClient") as mock_client:
            mock_client_instance = AsyncMock()
            mock_client_instance.post = AsyncMock(
                side_effect=httpx.ConnectError("Connection refused")
            )
            mock_client.return_value.__aenter__.return_value = mock_client_instance

            result = await deliver_webhook(url, payload, secret)

        assert result["success"] is False
        assert result["status_code"] == 0
        assert "error" in result


class TestWebhookRetryLogic:
    """Test webhook retry logic with exponential backoff."""

    @pytest.mark.asyncio
    async def test_retry_success_first_attempt(self):
        """Test successful delivery on first attempt (no retry needed)."""
        subscription = WebhookSubscription(
            id=uuid4(),
            url="https://example.com/webhook",
            secret="my-secret-key",
            events=["task.completed"],
            is_active=True,
            failure_count=5,  # Should reset to 0
        )

        mock_db = AsyncMock(spec=AsyncSession)
        mock_db.commit = AsyncMock()

        with patch("lazy_bird.services.webhook_service.deliver_webhook") as mock_deliver:
            mock_deliver.return_value = {
                "success": True,
                "status_code": 200,
                "response_time_ms": 100,
            }

            result = await deliver_webhook_with_retry(
                subscription,
                {"event": "task.completed"},
                mock_db,
            )

        assert result["success"] is True
        assert subscription.failure_count == 0
        assert subscription.last_triggered_at is not None
        assert subscription.last_failure_at is None
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_retry_success_second_attempt(self):
        """Test successful delivery on second attempt after one failure."""
        subscription = WebhookSubscription(
            id=uuid4(),
            url="https://example.com/webhook",
            secret="my-secret-key",
            events=["task.completed"],
            is_active=True,
            failure_count=0,
        )

        mock_db = AsyncMock(spec=AsyncSession)
        mock_db.commit = AsyncMock()

        with patch("lazy_bird.services.webhook_service.deliver_webhook") as mock_deliver:
            # First attempt fails, second succeeds
            mock_deliver.side_effect = [
                {"success": False, "status_code": 500, "error": "Server error"},
                {"success": True, "status_code": 200, "response_time_ms": 100},
            ]

            with patch("asyncio.sleep", new_callable=AsyncMock):
                result = await deliver_webhook_with_retry(
                    subscription,
                    {"event": "task.completed"},
                    mock_db,
                )

        assert result["success"] is True
        assert subscription.failure_count == 0
        assert subscription.last_triggered_at is not None

    @pytest.mark.asyncio
    async def test_retry_all_attempts_fail(self):
        """Test all retry attempts fail."""
        subscription = WebhookSubscription(
            id=uuid4(),
            url="https://example.com/webhook",
            secret="my-secret-key",
            events=["task.completed"],
            is_active=True,
            failure_count=0,
        )

        mock_db = AsyncMock(spec=AsyncSession)
        mock_db.commit = AsyncMock()

        with patch("lazy_bird.services.webhook_service.deliver_webhook") as mock_deliver:
            # All attempts fail
            mock_deliver.return_value = {
                "success": False,
                "status_code": 500,
                "error": "Server error",
            }

            with patch("asyncio.sleep", new_callable=AsyncMock):
                result = await deliver_webhook_with_retry(
                    subscription,
                    {"event": "task.completed"},
                    mock_db,
                    max_retries=MAX_RETRIES,
                )

        assert result["success"] is False
        assert subscription.failure_count == 1
        assert subscription.last_failure_at is not None
        assert subscription.is_active is True  # Not disabled yet

    @pytest.mark.asyncio
    async def test_retry_auto_disable_after_max_failures(self):
        """Test webhook auto-disables after MAX_CONSECUTIVE_FAILURES."""
        subscription = WebhookSubscription(
            id=uuid4(),
            url="https://example.com/webhook",
            secret="my-secret-key",
            events=["task.completed"],
            is_active=True,
            failure_count=MAX_CONSECUTIVE_FAILURES - 1,  # One away from threshold
        )

        mock_db = AsyncMock(spec=AsyncSession)
        mock_db.commit = AsyncMock()

        with patch("lazy_bird.services.webhook_service.deliver_webhook") as mock_deliver:
            mock_deliver.return_value = {
                "success": False,
                "status_code": 500,
                "error": "Server error",
            }

            with patch("asyncio.sleep", new_callable=AsyncMock):
                await deliver_webhook_with_retry(
                    subscription,
                    {"event": "task.completed"},
                    mock_db,
                )

        assert subscription.failure_count == MAX_CONSECUTIVE_FAILURES
        assert subscription.is_active is False  # Auto-disabled

    @pytest.mark.asyncio
    async def test_retry_exponential_backoff(self):
        """Test exponential backoff timing."""
        subscription = WebhookSubscription(
            id=uuid4(),
            url="https://example.com/webhook",
            secret="my-secret-key",
            events=["task.completed"],
            is_active=True,
            failure_count=0,
        )

        mock_db = AsyncMock(spec=AsyncSession)
        mock_db.commit = AsyncMock()

        with patch("lazy_bird.services.webhook_service.deliver_webhook") as mock_deliver:
            mock_deliver.return_value = {
                "success": False,
                "status_code": 500,
                "error": "Server error",
            }

            with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
                await deliver_webhook_with_retry(
                    subscription,
                    {"event": "task.completed"},
                    mock_db,
                    max_retries=3,
                )

                # Verify exponential backoff: 1s, 2s, 4s
                assert mock_sleep.call_count == 3
                sleep_times = [call.args[0] for call in mock_sleep.call_args_list]
                assert sleep_times == [1, 2, 4]


class TestPublishEvent:
    """Test event publishing to matching subscriptions."""

    @pytest.mark.asyncio
    async def test_publish_event_no_subscriptions(self):
        """Test publishing when no subscriptions match."""
        mock_db = AsyncMock(spec=AsyncSession)
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute = AsyncMock(return_value=mock_result)

        count = await publish_event(
            event_type="task.completed",
            data={"task_id": "123"},
            db=mock_db,
        )

        assert count == 0

    @pytest.mark.asyncio
    async def test_publish_event_single_subscription(self):
        """Test publishing to single matching subscription."""
        subscription = WebhookSubscription(
            id=uuid4(),
            url="https://example.com/webhook",
            secret="my-secret-key",
            events=["task.completed"],
            is_active=True,
            failure_count=0,
        )

        mock_db = AsyncMock(spec=AsyncSession)
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [subscription]
        mock_db.execute = AsyncMock(return_value=mock_result)
        mock_db.commit = AsyncMock()

        with patch(
            "lazy_bird.services.webhook_service.deliver_webhook_with_retry"
        ) as mock_retry:
            mock_retry.return_value = {"success": True, "status_code": 200}

            count = await publish_event(
                event_type="task.completed",
                data={"task_id": "123"},
                db=mock_db,
                project_id=uuid4(),
            )

        assert count == 1
        mock_retry.assert_called_once()

    @pytest.mark.asyncio
    async def test_publish_event_multiple_subscriptions(self):
        """Test publishing to multiple matching subscriptions in parallel."""
        subscriptions = [
            WebhookSubscription(
                id=uuid4(),
                url=f"https://example{i}.com/webhook",
                secret="my-secret-key",
                events=["task.completed"],
                is_active=True,
                failure_count=0,
            )
            for i in range(3)
        ]

        mock_db = AsyncMock(spec=AsyncSession)
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = subscriptions
        mock_db.execute = AsyncMock(return_value=mock_result)
        mock_db.commit = AsyncMock()

        with patch(
            "lazy_bird.services.webhook_service.deliver_webhook_with_retry"
        ) as mock_retry:
            mock_retry.return_value = {"success": True, "status_code": 200}

            count = await publish_event(
                event_type="task.completed",
                data={"task_id": "123"},
                db=mock_db,
            )

        assert count == 3
        assert mock_retry.call_count == 3

    @pytest.mark.asyncio
    async def test_publish_event_payload_structure(self):
        """Test that published event has correct payload structure."""
        subscription = WebhookSubscription(
            id=uuid4(),
            url="https://example.com/webhook",
            secret="my-secret-key",
            events=["task.completed"],
            is_active=True,
            failure_count=0,
        )

        project_id = uuid4()
        event_data = {"task_id": "123", "status": "success"}

        mock_db = AsyncMock(spec=AsyncSession)
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [subscription]
        mock_db.execute = AsyncMock(return_value=mock_result)
        mock_db.commit = AsyncMock()

        with patch(
            "lazy_bird.services.webhook_service.deliver_webhook_with_retry"
        ) as mock_retry:
            mock_retry.return_value = {"success": True, "status_code": 200}

            await publish_event(
                event_type="task.completed",
                data=event_data,
                db=mock_db,
                project_id=project_id,
            )

            # Get the payload argument
            call_args = mock_retry.call_args
            payload = call_args[0][1]  # Second positional argument

            assert payload["event"] == "task.completed"
            assert payload["project_id"] == str(project_id)
            assert payload["data"] == event_data
            assert "timestamp" in payload


class TestWebhookTestDelivery:
    """Test webhook test delivery endpoint."""

    @pytest.mark.asyncio
    async def test_test_delivery_success(self):
        """Test successful test webhook delivery."""
        subscription = WebhookSubscription(
            id=uuid4(),
            url="https://example.com/webhook",
            secret="my-secret-key",
            events=["task.completed"],
            is_active=True,
        )

        mock_db = AsyncMock(spec=AsyncSession)

        with patch("lazy_bird.services.webhook_service.deliver_webhook") as mock_deliver:
            mock_deliver.return_value = {
                "success": True,
                "status_code": 200,
                "response_time_ms": 100,
            }

            result = await send_test_webhook(subscription, mock_db)

        assert result["success"] is True
        assert result["status_code"] == 200
        assert "message" in result
        assert "successfully" in result["message"].lower()

    @pytest.mark.asyncio
    async def test_test_delivery_failure(self):
        """Test failed test webhook delivery."""
        subscription = WebhookSubscription(
            id=uuid4(),
            url="https://example.com/webhook",
            secret="my-secret-key",
            events=["task.completed"],
            is_active=True,
        )

        mock_db = AsyncMock(spec=AsyncSession)

        with patch("lazy_bird.services.webhook_service.deliver_webhook") as mock_deliver:
            mock_deliver.return_value = {
                "success": False,
                "status_code": 500,
                "error": "Server error",
            }

            result = await send_test_webhook(subscription, mock_db)

        assert result["success"] is False
        assert result["status_code"] == 500
        assert "message" in result
        assert "failed" in result["message"].lower()

    @pytest.mark.asyncio
    async def test_test_delivery_payload_structure(self):
        """Test that test delivery has correct payload structure."""
        subscription = WebhookSubscription(
            id=uuid4(),
            url="https://example.com/webhook",
            secret="my-secret-key",
            events=["task.completed", "pr.created"],
            is_active=True,
        )

        mock_db = AsyncMock(spec=AsyncSession)

        with patch("lazy_bird.services.webhook_service.deliver_webhook") as mock_deliver:
            mock_deliver.return_value = {
                "success": True,
                "status_code": 200,
                "response_time_ms": 100,
            }

            await send_test_webhook(subscription, mock_db)

            # Get the payload argument
            call_args = mock_deliver.call_args
            payload = call_args.kwargs["payload"]

            assert payload["event"] == "webhook.test"
            assert payload["subscription_id"] == str(subscription.id)
            assert "timestamp" in payload
            assert "data" in payload
            assert payload["data"]["url"] == subscription.url
            assert payload["data"]["events"] == subscription.events
