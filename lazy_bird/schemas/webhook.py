"""Pydantic schemas for WebhookSubscription API endpoints."""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, HttpUrl


class WebhookSubscriptionBase(BaseModel):
    """Base WebhookSubscription schema with shared fields."""

    url: HttpUrl = Field(
        ...,
        description="Webhook endpoint URL (must be http/https)",
        examples=["https://example.com/webhooks/lazy-bird"],
    )

    secret: str = Field(
        ...,
        min_length=16,
        max_length=255,
        description="Secret for HMAC signature verification",
    )

    project_id: Optional[UUID] = Field(
        default=None,
        description="Project ID (NULL for global subscriptions)",
    )

    events: list[str] = Field(
        ...,
        min_length=1,
        description="Array of event types to subscribe to",
        examples=[["task.completed", "task.failed", "pr.created"]],
    )

    is_active: bool = Field(
        default=True,
        description="Whether subscription is active",
    )

    description: Optional[str] = Field(
        default=None,
        description="Subscription description",
    )


class WebhookSubscriptionCreate(WebhookSubscriptionBase):
    """Schema for creating a new webhook subscription."""

    pass


class WebhookSubscriptionUpdate(BaseModel):
    """Schema for updating an existing webhook subscription."""

    url: Optional[HttpUrl] = Field(default=None)
    secret: Optional[str] = Field(default=None, min_length=16, max_length=255)
    events: Optional[list[str]] = Field(default=None, min_length=1)
    is_active: Optional[bool] = Field(default=None)
    description: Optional[str] = Field(default=None)

    model_config = ConfigDict(extra="forbid")


class WebhookSubscriptionResponse(WebhookSubscriptionBase):
    """Schema for webhook subscription API responses."""

    id: UUID = Field(..., description="Unique subscription identifier")

    last_triggered_at: Optional[datetime] = Field(
        default=None,
        description="Last webhook delivery time",
    )

    failure_count: int = Field(..., ge=0, description="Number of consecutive failures")

    last_failure_at: Optional[datetime] = Field(
        default=None,
        description="Last failure timestamp",
    )

    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")

    model_config = ConfigDict(from_attributes=True)


class WebhookSubscriptionListResponse(BaseModel):
    """Schema for paginated webhook subscription list responses."""

    items: list[WebhookSubscriptionResponse] = Field(..., description="List of subscriptions")
    total: int = Field(..., ge=0, description="Total number of subscriptions")
    page: int = Field(..., ge=1, description="Current page number")
    page_size: int = Field(..., ge=1, le=100, description="Items per page")
    pages: int = Field(..., ge=0, description="Total number of pages")

    model_config = ConfigDict(from_attributes=True)
