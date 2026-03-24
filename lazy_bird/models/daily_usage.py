"""DailyUsage model - Daily usage tracking and billing.

This module defines the DailyUsage model for tracking daily metrics
and resource consumption per project.
"""

import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from lazy_bird.core.database import Base


class DailyUsage(Base):
    """DailyUsage model for daily usage tracking.

    Attributes:
        id: Unique record identifier
        project_id: Reference to project
        date: Usage date
        tasks_queued: Number of tasks queued
        tasks_completed: Number of tasks completed
        tasks_failed: Number of tasks failed
        total_tokens_used: Total tokens consumed
        total_cost_usd: Total cost in USD
        total_duration_seconds: Total execution time
        created_at: Creation timestamp
        updated_at: Last update timestamp
    """

    __tablename__ = "daily_usage"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.gen_random_uuid(),
        nullable=False,
    )

    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
    )

    date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
    )

    tasks_queued: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        server_default="0",
        default=0,
    )

    tasks_completed: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        server_default="0",
        default=0,
    )

    tasks_failed: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        server_default="0",
        default=0,
    )

    total_tokens_used: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
        server_default="0",
        default=0,
    )

    total_cost_usd: Mapped[Decimal] = mapped_column(
        Numeric(10, 4),
        nullable=False,
        server_default="0",
        default=Decimal("0"),
    )

    total_duration_seconds: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
        server_default="0",
        default=0,
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

    project: Mapped["Project"] = relationship(
        "Project",
        back_populates="daily_usages",
        foreign_keys=[project_id],
    )

    __table_args__ = (
        UniqueConstraint(project_id, date, name="uq_daily_usage_project_date"),
        Index("idx_daily_usage_project_date", project_id, date.desc()),
        Index("idx_daily_usage_date", date.desc()),
        {"comment": "Daily usage tracking and billing"},
    )

    def __repr__(self) -> str:
        return f"<DailyUsage(project_id={self.project_id}, date={self.date}, completed={self.tasks_completed})>"
