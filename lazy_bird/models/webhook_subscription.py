"""WebhookSubscription model - Client webhook endpoint registrations.

This module defines the WebhookSubscription model for registering webhook
endpoints that receive task execution events.
"""

import uuid
from datetime import datetime
from typing import List, Optional

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from lazy_bird.core.database import Base


class WebhookSubscription(Base):
    """WebhookSubscription model for webhook endpoint registrations.

    Attributes:
        id: Unique subscription identifier
        url: Webhook endpoint URL
        secret: Secret for HMAC signature verification
        project_id: Project ID (NULL for global subscriptions)
        events: Array of event types to subscribe to
        is_active: Whether subscription is active
        last_triggered_at: Last webhook delivery time
        failure_count: Number of consecutive failures
        last_failure_at: Last failure timestamp
        description: Subscription description
        created_at: Creation timestamp
        updated_at: Last update timestamp
    """

    __tablename__ = "webhook_subscriptions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.gen_random_uuid(),
        nullable=False,
    )

    url: Mapped[str] = mapped_column(String(500), nullable=False, comment="Webhook endpoint URL")

    secret: Mapped[str] = mapped_column(
        String(255), nullable=False, comment="Secret for HMAC signature verification"
    )

    project_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
        comment="Project ID (NULL for global subscriptions)",
    )

    events: Mapped[List[str]] = mapped_column(
        ARRAY(Text), nullable=False, comment="Array of event types"
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default="true",
        default=True,
        index=True,
        comment="Whether subscription is active",
    )

    last_triggered_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="Last webhook delivery time"
    )

    failure_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        server_default="0",
        default=0,
        comment="Number of consecutive failures",
    )

    last_failure_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="Last failure timestamp"
    )

    description: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True, comment="Subscription description"
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.current_timestamp(),
        default=func.current_timestamp(),
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.current_timestamp(),
        default=func.current_timestamp(),
        onupdate=func.current_timestamp(),
    )

    project: Mapped[Optional["Project"]] = relationship(
        "Project",
        back_populates="webhook_subscriptions",
        foreign_keys=[project_id],
    )

    __table_args__ = (
        CheckConstraint("url ~ '^https?://'", name="check_url_format"),
        Index("idx_webhook_subscriptions_events", events, postgresql_using="gin"),
        {"comment": "Client webhook endpoint registrations"},
    )

    def __repr__(self) -> str:
        return f"<WebhookSubscription(id={self.id}, url='{self.url}', active={self.is_active})>"
