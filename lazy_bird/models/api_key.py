"""ApiKey model - API authentication tokens.

This module defines the ApiKey model for API authentication and authorization.
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
    String,
    func,
)
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from lazy_bird.core.database import Base


class ApiKey(Base):
    """ApiKey model for API authentication.

    Attributes:
        id: Unique key identifier
        key_hash: SHA-256 hash of actual key
        key_prefix: First 8 chars for identification
        name: Human-readable key name
        project_id: Project ID (NULL for organization-level)
        scopes: Array of permission scopes
        is_active: Whether key is active
        expires_at: Expiration timestamp
        last_used_at: Last usage timestamp
        created_by: Creator identifier
        created_at: Creation timestamp
        revoked_at: Revocation timestamp
    """

    __tablename__ = "api_keys"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.gen_random_uuid(),
        nullable=False,
    )

    key_hash: Mapped[str] = mapped_column(
        String(64),
        unique=True,
        nullable=False,
        index=True,
        comment="SHA-256 hash of actual key"
    )

    key_prefix: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
        index=True,
        comment="First 8 chars for identification"
    )

    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    project_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
        comment="Project ID (NULL for organization-level)"
    )

    scopes: Mapped[List[str]] = mapped_column(
        ARRAY(String),
        nullable=False,
        server_default="ARRAY['read']",
        default=lambda: ["read"],
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default="true",
        default=True,
        index=True,
    )

    expires_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    last_used_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    created_by: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.current_timestamp(),
        default=func.current_timestamp(),
    )

    revoked_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    project: Mapped[Optional["Project"]] = relationship(
        "Project",
        back_populates="api_keys",
        foreign_keys=[project_id],
    )

    __table_args__ = (
        CheckConstraint(
            "scopes <@ ARRAY['read', 'write', 'admin']::TEXT[]",
            name="check_scopes",
        ),
        {"comment": "API authentication tokens"},
    )

    def __repr__(self) -> str:
        return f"<ApiKey(id={self.id}, name='{self.name}', prefix='{self.key_prefix}', active={self.is_active})>"
