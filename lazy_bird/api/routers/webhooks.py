"""Webhooks API endpoints for managing webhook subscriptions.

This module provides CRUD operations for webhook subscriptions with:
- Event-driven notifications for task execution events
- HMAC signature verification for security
- Project-scoped or global subscriptions
- Automatic failure tracking and retry logic
"""

from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from lazy_bird.api.dependencies import RequireAdmin, RequireRead, get_async_database
from lazy_bird.api.exceptions import ResourceNotFoundError
from lazy_bird.core.logging import get_logger
from lazy_bird.models.api_key import ApiKey
from lazy_bird.models.project import Project
from lazy_bird.models.webhook_subscription import WebhookSubscription
from lazy_bird.schemas.webhook import (
    WebhookSubscriptionCreate,
    WebhookSubscriptionListResponse,
    WebhookSubscriptionResponse,
    WebhookSubscriptionUpdate,
)

logger = get_logger(__name__)

# Create router
router = APIRouter(prefix="/webhooks", tags=["webhooks"])


@router.get("", response_model=WebhookSubscriptionListResponse)
@router.get("/", response_model=WebhookSubscriptionListResponse)
async def list_webhooks(
    # Pagination
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    # Filtering
    project_id: Optional[UUID] = Query(
        None, description="Filter by project ID (omit for global subscriptions)"
    ),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    event: Optional[str] = Query(
        None, description="Filter by event type (e.g., task.completed)"
    ),
    # Dependencies
    db: AsyncSession = Depends(get_async_database),
    api_key: ApiKey = Depends(RequireRead),
) -> WebhookSubscriptionListResponse:
    """List all webhook subscriptions with pagination and filtering.

    **Pagination:**
    - Offset-based pagination with page and page_size
    - Default: page=1, page_size=20
    - Max page_size: 100

    **Filtering:**
    - `project_id`: UUID - Filter by project (NULL for global subscriptions)
    - `is_active`: boolean - Filter by active status
    - `event`: string - Filter by subscribed event type

    **Returns:**
    - List of webhook subscriptions
    - Total count, page info, pagination metadata

    **Authentication:**
    - Requires: API key with 'read', 'write', or 'admin' scope

    **Event Types:**
    - task.queued - Task added to queue
    - task.started - Task execution started
    - task.completed - Task completed successfully
    - task.failed - Task failed
    - task.cancelled - Task cancelled
    - task.timeout - Task timed out
    - pr.created - Pull request created
    - pr.merged - Pull request merged
    - test.passed - Tests passed
    - test.failed - Tests failed
    """
    # Build base query
    query = select(WebhookSubscription)

    # Apply filters
    filters = []

    # Filter by project ID
    if project_id is not None:
        filters.append(WebhookSubscription.project_id == project_id)

    # Filter by active status
    if is_active is not None:
        filters.append(WebhookSubscription.is_active == is_active)

    # Filter by event type (check if array contains the event)
    if event:
        filters.append(WebhookSubscription.events.contains([event]))

    # Add all filters to query
    if filters:
        query = query.where(*filters)

    # Get total count
    count_query = select(func.count()).select_from(WebhookSubscription)
    if filters:
        count_query = count_query.where(*filters)
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Calculate pagination
    offset = (page - 1) * page_size
    pages = (total + page_size - 1) // page_size if total > 0 else 0

    # Apply pagination and sorting (most recent first)
    query = (
        query.order_by(WebhookSubscription.created_at.desc())
        .offset(offset)
        .limit(page_size)
    )

    # Execute query
    result = await db.execute(query)
    subscriptions = result.scalars().all()

    # Convert to response models
    subscription_responses = [
        WebhookSubscriptionResponse.model_validate(s) for s in subscriptions
    ]

    # Log successful query
    logger.info(
        f"Listed {len(subscriptions)} webhook subscriptions (page {page}/{pages})",
        extra={
            "extra_fields": {
                "total": total,
                "page": page,
                "page_size": page_size,
                "filters": {
                    "project_id": str(project_id) if project_id else None,
                    "is_active": is_active,
                    "event": event,
                },
            }
        },
    )

    return WebhookSubscriptionListResponse(
        items=subscription_responses,
        total=total,
        page=page,
        page_size=page_size,
        pages=pages,
    )


@router.post("", response_model=WebhookSubscriptionResponse, status_code=status.HTTP_201_CREATED)
@router.post("/", response_model=WebhookSubscriptionResponse, status_code=status.HTTP_201_CREATED)
async def create_webhook(
    subscription_data: WebhookSubscriptionCreate,
    db: AsyncSession = Depends(get_async_database),
    api_key: ApiKey = Depends(RequireAdmin),
) -> WebhookSubscriptionResponse:
    """Create a new webhook subscription.

    **Required Fields:**
    - url: Webhook endpoint URL (must be http/https)
    - secret: Secret for HMAC signature verification (min 16 chars)
    - events: Array of event types to subscribe to

    **Optional Fields:**
    - project_id: Project ID (NULL for global subscriptions)
    - is_active: Active status (default: true)
    - description: Subscription description

    **Event Types:**
    - task.queued, task.started, task.completed, task.failed, task.cancelled, task.timeout
    - pr.created, pr.merged
    - test.passed, test.failed

    **Returns:**
    - 201 Created: Subscription created successfully
    - 404 Not Found: Project doesn't exist (if project_id provided)
    - 422 Validation Error: Invalid input data

    **Authentication:**
    - Requires: API key with 'admin' scope

    **Webhook Payload Format:**
    ```json
    {
      "event": "task.completed",
      "timestamp": "2024-01-01T12:00:00Z",
      "project_id": "uuid",
      "task_run_id": "uuid",
      "data": { ... }
    }
    ```

    **HMAC Signature:**
    - Header: `X-Webhook-Signature: sha256=<hmac>`
    - Algorithm: HMAC-SHA256
    - Key: subscription secret
    - Payload: raw JSON body
    """
    # Validate project exists if project_id provided
    if subscription_data.project_id:
        project_query = select(Project).where(
            Project.id == subscription_data.project_id
        )
        project_result = await db.execute(project_query)
        project = project_result.scalar_one_or_none()

        if not project:
            raise ResourceNotFoundError(
                resource_type="Project",
                resource_id=str(subscription_data.project_id),
            )

    # Create webhook subscription
    subscription = WebhookSubscription(
        url=str(subscription_data.url),
        secret=subscription_data.secret,
        project_id=subscription_data.project_id,
        events=subscription_data.events,
        is_active=subscription_data.is_active,
        description=subscription_data.description,
        failure_count=0,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )

    db.add(subscription)
    await db.commit()
    await db.refresh(subscription)

    # Log successful creation (mask secret)
    logger.info(
        f"Created webhook subscription: {subscription.url}",
        extra={
            "extra_fields": {
                "subscription_id": str(subscription.id),
                "url": subscription.url,
                "events": subscription.events,
                "project_id": (
                    str(subscription.project_id) if subscription.project_id else None
                ),
            }
        },
    )

    return WebhookSubscriptionResponse.model_validate(subscription)


@router.get("/{subscription_id}", response_model=WebhookSubscriptionResponse)
async def get_webhook(
    subscription_id: UUID,
    db: AsyncSession = Depends(get_async_database),
    api_key: ApiKey = Depends(RequireRead),
) -> WebhookSubscriptionResponse:
    """Get a single webhook subscription by ID.

    **Path Parameters:**
    - subscription_id: UUID - Subscription identifier

    **Returns:**
    - Subscription details with delivery statistics

    **Errors:**
    - 404 Not Found: Subscription doesn't exist

    **Authentication:**
    - Requires: API key with 'read', 'write', or 'admin' scope
    """
    # Fetch subscription
    query = select(WebhookSubscription).where(
        WebhookSubscription.id == subscription_id
    )
    result = await db.execute(query)
    subscription = result.scalar_one_or_none()

    # Check if subscription exists
    if not subscription:
        raise ResourceNotFoundError(
            resource_type="WebhookSubscription",
            resource_id=str(subscription_id),
        )

    # Log successful query
    logger.info(
        f"Retrieved webhook subscription: {subscription.url}",
        extra={
            "extra_fields": {
                "subscription_id": str(subscription.id),
                "url": subscription.url,
            }
        },
    )

    return WebhookSubscriptionResponse.model_validate(subscription)


@router.patch("/{subscription_id}", response_model=WebhookSubscriptionResponse)
async def update_webhook(
    subscription_id: UUID,
    update_data: WebhookSubscriptionUpdate,
    db: AsyncSession = Depends(get_async_database),
    api_key: ApiKey = Depends(RequireAdmin),
) -> WebhookSubscriptionResponse:
    """Update an existing webhook subscription (partial update).

    **Path Parameters:**
    - subscription_id: UUID - Subscription identifier

    **Request Body (all optional):**
    - url: Webhook endpoint URL
    - secret: HMAC signature secret
    - events: Array of event types
    - is_active: Active status
    - description: Subscription description

    **Returns:**
    - Updated subscription

    **Errors:**
    - 404 Not Found: Subscription doesn't exist
    - 422 Validation Error: Invalid field values

    **Authentication:**
    - Requires: API key with 'admin' scope

    **Note:**
    - Set `is_active=false` to temporarily disable webhook deliveries
    - Cannot change project_id after creation
    - Changing secret will require updating webhook endpoint verification
    """
    # Fetch existing subscription
    query = select(WebhookSubscription).where(
        WebhookSubscription.id == subscription_id
    )
    result = await db.execute(query)
    subscription = result.scalar_one_or_none()

    # Check if subscription exists
    if not subscription:
        raise ResourceNotFoundError(
            resource_type="WebhookSubscription",
            resource_id=str(subscription_id),
        )

    # Get update data (only fields that were provided)
    update_fields = update_data.model_dump(exclude_unset=True)

    # If no fields to update, return existing subscription
    if not update_fields:
        logger.info(f"No fields to update for webhook subscription: {subscription.url}")
        return WebhookSubscriptionResponse.model_validate(subscription)

    # Apply updates
    for field, value in update_fields.items():
        # Convert HttpUrl to string for url field
        if field == "url" and value is not None:
            value = str(value)
        setattr(subscription, field, value)

    # Update timestamp
    subscription.updated_at = datetime.now(timezone.utc)

    # Commit changes
    await db.commit()
    await db.refresh(subscription)

    # Log successful update
    logger.info(
        f"Updated webhook subscription: {subscription.url}",
        extra={
            "extra_fields": {
                "subscription_id": str(subscription.id),
                "updated_fields": list(update_fields.keys()),
            }
        },
    )

    return WebhookSubscriptionResponse.model_validate(subscription)


@router.delete("/{subscription_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_webhook(
    subscription_id: UUID,
    db: AsyncSession = Depends(get_async_database),
    api_key: ApiKey = Depends(RequireAdmin),
) -> Response:
    """Delete a webhook subscription.

    **Path Parameters:**
    - subscription_id: UUID - Subscription identifier

    **Behavior:**
    - Hard delete (permanently removes record)
    - Immediately stops webhook deliveries

    **Returns:**
    - 204 No Content: Subscription deleted successfully

    **Errors:**
    - 404 Not Found: Subscription doesn't exist

    **Authentication:**
    - Requires: API key with 'admin' scope

    **Warning:**
    - This is a hard delete - subscription cannot be recovered
    - Consider setting is_active=false instead for temporary disabling
    """
    # Fetch existing subscription
    query = select(WebhookSubscription).where(
        WebhookSubscription.id == subscription_id
    )
    result = await db.execute(query)
    subscription = result.scalar_one_or_none()

    # Check if subscription exists
    if not subscription:
        raise ResourceNotFoundError(
            resource_type="WebhookSubscription",
            resource_id=str(subscription_id),
        )

    # Delete the subscription
    await db.delete(subscription)
    await db.commit()

    # Log deletion
    logger.info(
        f"Deleted webhook subscription: {subscription.url}",
        extra={
            "extra_fields": {
                "subscription_id": str(subscription_id),
                "url": subscription.url,
            }
        },
    )

    # Return 204 No Content (no response body)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{subscription_id}/test", status_code=status.HTTP_200_OK)
async def test_webhook_delivery(
    subscription_id: UUID,
    db: AsyncSession = Depends(get_async_database),
    api_key: ApiKey = Depends(RequireAdmin),
) -> dict:
    """Test webhook delivery by sending a test event.

    **Path Parameters:**
    - subscription_id: UUID - Subscription identifier

    **Behavior:**
    - Sends a test event to the webhook endpoint
    - Verifies endpoint is reachable and responds correctly
    - Updates delivery statistics

    **Returns:**
    - 200 OK: Test delivery details
    - 404 Not Found: Subscription doesn't exist
    - 500 Internal Server Error: Webhook delivery failed

    **Authentication:**
    - Requires: API key with 'admin' scope

    **Test Event Payload:**
    ```json
    {
      "event": "webhook.test",
      "timestamp": "2024-01-01T12:00:00Z",
      "subscription_id": "uuid",
      "data": {
        "message": "This is a test webhook delivery"
      }
    }
    ```

    **Note:**
    - This endpoint is useful for verifying webhook configuration
    - Does not count as a failure if delivery fails
    """
    # Fetch subscription
    query = select(WebhookSubscription).where(
        WebhookSubscription.id == subscription_id
    )
    result = await db.execute(query)
    subscription = result.scalar_one_or_none()

    # Check if subscription exists
    if not subscription:
        raise ResourceNotFoundError(
            resource_type="WebhookSubscription",
            resource_id=str(subscription_id),
        )

    # Import webhook service for test delivery
    from lazy_bird.services.webhook_service import test_webhook_delivery as send_test

    # Send test event
    delivery_result = await send_test(subscription, db)

    # Log test delivery
    logger.info(
        f"Test webhook delivery: {subscription.url}",
        extra={
            "extra_fields": {
                "subscription_id": str(subscription.id),
                "url": subscription.url,
                "success": delivery_result["success"],
                "status_code": delivery_result.get("status_code"),
            }
        },
    )

    return delivery_result
