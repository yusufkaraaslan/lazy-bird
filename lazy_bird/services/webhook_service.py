"""Webhook delivery service with HMAC signatures and retry logic.

This module provides webhook event publishing with:
- HMAC-SHA256 signature generation for security
- Automatic retry with exponential backoff
- Failure tracking and auto-disable
- Async HTTP delivery
"""

import asyncio
import hashlib
import hmac
import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from lazy_bird.core.logging import get_logger
from lazy_bird.models.webhook_subscription import WebhookSubscription

logger = get_logger(__name__)

# Webhook delivery configuration
MAX_RETRIES = 3
INITIAL_BACKOFF_SECONDS = 1
MAX_BACKOFF_SECONDS = 60
TIMEOUT_SECONDS = 30
MAX_CONSECUTIVE_FAILURES = 10  # Auto-disable after this many failures


def generate_webhook_signature(payload: str, secret: str) -> str:
    """Generate HMAC-SHA256 signature for webhook payload.

    Args:
        payload: JSON payload as string
        secret: Webhook subscription secret

    Returns:
        str: Hexadecimal HMAC-SHA256 signature

    Example:
        >>> payload = '{"event": "task.completed"}'
        >>> secret = "my-webhook-secret"
        >>> sig = generate_webhook_signature(payload, secret)
        >>> len(sig)
        64  # SHA-256 produces 64 hex characters
    """
    signature = hmac.new(
        secret.encode("utf-8"), payload.encode("utf-8"), hashlib.sha256
    ).hexdigest()

    return signature


def verify_webhook_signature(payload: str, secret: str, signature: str) -> bool:
    """Verify HMAC-SHA256 signature for webhook payload.

    Args:
        payload: JSON payload as string
        secret: Webhook subscription secret
        signature: HMAC signature to verify

    Returns:
        bool: True if signature is valid, False otherwise

    Example:
        >>> payload = '{"event": "task.completed"}'
        >>> secret = "my-webhook-secret"
        >>> sig = generate_webhook_signature(payload, secret)
        >>> verify_webhook_signature(payload, secret, sig)
        True
        >>> verify_webhook_signature(payload, secret, "wrong_signature")
        False
    """
    expected_signature = generate_webhook_signature(payload, secret)
    return hmac.compare_digest(signature, expected_signature)


async def deliver_webhook(
    url: str,
    payload: Dict[str, Any],
    secret: str,
    timeout: int = TIMEOUT_SECONDS,
) -> Dict[str, Any]:
    """Deliver webhook event to endpoint with HMAC signature.

    Args:
        url: Webhook endpoint URL
        payload: Event payload dictionary
        secret: Webhook subscription secret
        timeout: Request timeout in seconds

    Returns:
        Dict with delivery result:
        - success: bool - Whether delivery succeeded
        - status_code: int - HTTP status code
        - response_time_ms: float - Response time in milliseconds
        - error: str - Error message (if failed)

    Example:
        >>> payload = {"event": "task.completed", "data": {...}}
        >>> result = await deliver_webhook("https://example.com/webhook", payload, "secret")
        >>> result["success"]
        True
        >>> result["status_code"]
        200
    """
    # Serialize payload to JSON
    payload_json = json.dumps(payload, default=str)

    # Generate HMAC signature
    signature = generate_webhook_signature(payload_json, secret)

    # Prepare headers
    headers = {
        "Content-Type": "application/json",
        "X-Lazy-Bird-Signature": f"sha256={signature}",
        "X-Lazy-Bird-Event": payload.get("event", "unknown"),
        "User-Agent": "Lazy-Bird-Webhook/2.0",
    }

    # Measure response time
    start_time = datetime.now(timezone.utc)

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(url, content=payload_json, headers=headers)

        # Calculate response time
        end_time = datetime.now(timezone.utc)
        response_time_ms = (end_time - start_time).total_seconds() * 1000

        # Check if successful (2xx status code)
        success = 200 <= response.status_code < 300

        return {
            "success": success,
            "status_code": response.status_code,
            "response_time_ms": response_time_ms,
            "response_body": response.text[:500],  # First 500 chars
        }

    except httpx.TimeoutException as e:
        end_time = datetime.now(timezone.utc)
        response_time_ms = (end_time - start_time).total_seconds() * 1000

        logger.warning(f"Webhook delivery timeout: {url}", exc_info=True)
        return {
            "success": False,
            "status_code": 0,
            "response_time_ms": response_time_ms,
            "error": f"Request timeout after {timeout}s",
        }

    except Exception as e:
        end_time = datetime.now(timezone.utc)
        response_time_ms = (end_time - start_time).total_seconds() * 1000

        logger.error(f"Webhook delivery failed: {url}", exc_info=True)
        return {
            "success": False,
            "status_code": 0,
            "response_time_ms": response_time_ms,
            "error": str(e),
        }


async def deliver_webhook_with_retry(
    subscription: WebhookSubscription,
    payload: Dict[str, Any],
    db: AsyncSession,
    max_retries: int = MAX_RETRIES,
) -> Dict[str, Any]:
    """Deliver webhook with automatic retry and exponential backoff.

    Args:
        subscription: WebhookSubscription model instance
        payload: Event payload dictionary
        db: Database session for updating failure counts
        max_retries: Maximum number of retry attempts

    Returns:
        Dict with delivery result (same as deliver_webhook)

    Example:
        >>> subscription = WebhookSubscription(url="https://example.com/webhook", secret="secret")
        >>> payload = {"event": "task.completed"}
        >>> result = await deliver_webhook_with_retry(subscription, payload, db)
        >>> result["success"]
        True
    """
    last_result = None
    backoff_seconds = INITIAL_BACKOFF_SECONDS

    for attempt in range(max_retries + 1):  # +1 for initial attempt
        # Deliver webhook
        result = await deliver_webhook(
            url=subscription.url,
            payload=payload,
            secret=subscription.secret,
        )

        last_result = result

        # If successful, reset failure count and update last_triggered_at
        if result["success"]:
            if subscription.failure_count > 0:
                subscription.failure_count = 0
                subscription.last_failure_at = None

            subscription.last_triggered_at = datetime.now(timezone.utc)
            await db.commit()

            logger.info(
                f"Webhook delivered successfully: {subscription.url}",
                extra={
                    "extra_fields": {
                        "subscription_id": str(subscription.id),
                        "attempt": attempt + 1,
                        "status_code": result["status_code"],
                        "response_time_ms": result["response_time_ms"],
                    }
                },
            )

            return result

        # If failed and retries remain, wait and retry
        if attempt < max_retries:
            wait_time = min(backoff_seconds, MAX_BACKOFF_SECONDS)
            logger.warning(
                f"Webhook delivery failed (attempt {attempt + 1}/{max_retries + 1}), "
                f"retrying in {wait_time}s: {subscription.url}",
                extra={
                    "extra_fields": {
                        "subscription_id": str(subscription.id),
                        "status_code": result.get("status_code"),
                        "error": result.get("error"),
                    }
                },
            )

            await asyncio.sleep(wait_time)
            backoff_seconds *= 2  # Exponential backoff

    # All retries failed - update failure count
    subscription.failure_count += 1
    subscription.last_failure_at = datetime.now(timezone.utc)

    # Auto-disable if too many consecutive failures
    if subscription.failure_count >= MAX_CONSECUTIVE_FAILURES:
        subscription.is_active = False
        logger.error(
            f"Webhook auto-disabled after {MAX_CONSECUTIVE_FAILURES} consecutive failures: {subscription.url}",
            extra={
                "extra_fields": {
                    "subscription_id": str(subscription.id),
                    "failure_count": subscription.failure_count,
                }
            },
        )

    await db.commit()

    logger.error(
        f"Webhook delivery failed after {max_retries + 1} attempts: {subscription.url}",
        extra={
            "extra_fields": {
                "subscription_id": str(subscription.id),
                "failure_count": subscription.failure_count,
                "last_error": last_result.get("error"),
            }
        },
    )

    return last_result


async def publish_event(
    event_type: str,
    data: Dict[str, Any],
    db: AsyncSession,
    project_id: Optional[UUID] = None,
) -> int:
    """Publish event to all matching webhook subscriptions.

    Args:
        event_type: Event type (e.g., "task.completed", "pr.created")
        data: Event data dictionary
        db: Database session for querying subscriptions
        project_id: Project ID (None for global events)

    Returns:
        int: Number of webhooks delivered

    Example:
        >>> event_data = {
        ...     "task_run_id": "uuid",
        ...     "status": "success",
        ...     "duration_seconds": 120
        ... }
        >>> count = await publish_event("task.completed", event_data, db, project_id=uuid)
        >>> count
        3  # Delivered to 3 subscriptions
    """
    # Build query to find matching subscriptions
    query = select(WebhookSubscription).where(
        WebhookSubscription.is_active == True,  # noqa: E712
        WebhookSubscription.events.contains([event_type]),
    )

    # Filter by project_id (NULL matches global subscriptions)
    if project_id is not None:
        # Match both global (NULL) and project-specific subscriptions
        query = query.where(
            (WebhookSubscription.project_id == project_id)
            | (WebhookSubscription.project_id.is_(None))
        )
    else:
        # Only match global subscriptions
        query = query.where(WebhookSubscription.project_id.is_(None))

    # Execute query
    result = await db.execute(query)
    subscriptions = result.scalars().all()

    if not subscriptions:
        logger.debug(
            f"No active webhook subscriptions found for event: {event_type}",
            extra={
                "extra_fields": {
                    "event_type": event_type,
                    "project_id": str(project_id) if project_id else None,
                }
            },
        )
        return 0

    # Build webhook payload
    payload = {
        "event": event_type,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "project_id": str(project_id) if project_id else None,
        "data": data,
    }

    # Deliver to all matching subscriptions in parallel
    delivery_tasks = [
        deliver_webhook_with_retry(subscription, payload, db)
        for subscription in subscriptions
    ]

    await asyncio.gather(*delivery_tasks, return_exceptions=True)

    logger.info(
        f"Published event to {len(subscriptions)} webhook(s): {event_type}",
        extra={
            "extra_fields": {
                "event_type": event_type,
                "subscription_count": len(subscriptions),
                "project_id": str(project_id) if project_id else None,
            }
        },
    )

    return len(subscriptions)


async def send_test_webhook(
    subscription: WebhookSubscription,
    db: AsyncSession,
) -> Dict[str, Any]:
    """Send a test event to verify webhook configuration.

    Args:
        subscription: WebhookSubscription model instance
        db: Database session

    Returns:
        Dict with delivery result:
        - success: bool
        - status_code: int
        - response_time_ms: float
        - message: str

    Example:
        >>> subscription = WebhookSubscription(url="https://example.com/webhook", secret="secret")
        >>> result = await send_test_webhook(subscription, db)
        >>> result["success"]
        True
    """
    # Build test payload
    payload = {
        "event": "webhook.test",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "subscription_id": str(subscription.id),
        "data": {
            "message": "This is a test webhook delivery from Lazy-Bird",
            "url": subscription.url,
            "events": subscription.events,
        },
    }

    # Deliver without retry (test should be fast)
    result = await deliver_webhook(
        url=subscription.url,
        payload=payload,
        secret=subscription.secret,
    )

    # Add user-friendly message
    if result["success"]:
        result["message"] = "Test webhook delivered successfully"
    else:
        result["message"] = f"Test webhook delivery failed: {result.get('error', 'Unknown error')}"

    return result
