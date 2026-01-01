"""ClaudeAccount model - Claude API credentials and settings.

This module defines the ClaudeAccount model which stores Claude API credentials,
configuration, and usage limits. Supports both API mode and subscription mode.
"""

import uuid
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import List, Optional

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    Decimal as SQLDecimal,
    Integer,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates

from lazy_bird.core.database import Base


class AccountType(str, Enum):
    """Claude account type enumeration.

    Attributes:
        API: Use Anthropic API with API key
        SUBSCRIPTION: Use Claude subscription with session token
    """

    API = "api"
    SUBSCRIPTION = "subscription"


class ClaudeAccount(Base):
    """ClaudeAccount model for storing Claude API credentials.

    A ClaudeAccount represents authentication and configuration for accessing
    Claude AI. It supports two modes:
    - API mode: Uses Anthropic API key
    - Subscription mode: Uses Claude subscription session token

    Attributes:
        id: Unique account identifier (UUID)
        name: Human-readable account name
        account_type: Account type (api or subscription)

        api_key: API key for API mode (encrypted at application layer)
        config_directory: Config directory for subscription mode
        session_token: Session token for subscription mode (encrypted)

        model: Claude model to use (e.g., claude-sonnet-4-5)
        max_tokens: Maximum tokens per request
        temperature: Model temperature (0.0-1.0)

        monthly_budget_usd: Monthly spending limit
        is_active: Whether account is active

        created_at: Creation timestamp
        updated_at: Last update timestamp
        last_used_at: Last time account was used

        projects: Relationship to Project models
    """

    __tablename__ = "claude_accounts"

    # -------------------------------------------------------------------------
    # PRIMARY KEY
    # -------------------------------------------------------------------------

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.gen_random_uuid(),
        nullable=False,
    )

    # -------------------------------------------------------------------------
    # BASIC INFORMATION
    # -------------------------------------------------------------------------

    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Human-readable account name"
    )

    account_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,  # idx_claude_accounts_type
        comment="Account type: api or subscription"
    )

    # -------------------------------------------------------------------------
    # API MODE CREDENTIALS
    # -------------------------------------------------------------------------

    api_key: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
        comment="Anthropic API key (encrypted at application layer)"
    )

    # -------------------------------------------------------------------------
    # SUBSCRIPTION MODE CREDENTIALS
    # -------------------------------------------------------------------------

    config_directory: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
        comment="Config directory path for subscription mode"
    )

    session_token: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
        comment="Session token for subscription mode (encrypted at application layer)"
    )

    # -------------------------------------------------------------------------
    # CLAUDE SETTINGS
    # -------------------------------------------------------------------------

    model: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        server_default="claude-sonnet-4-5",
        default="claude-sonnet-4-5",
        comment="Claude model identifier"
    )

    max_tokens: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        server_default="8000",
        default=8000,
        comment="Maximum tokens per request"
    )

    temperature: Mapped[Decimal] = mapped_column(
        Numeric(3, 2),
        nullable=False,
        server_default="0.7",
        default=Decimal("0.7"),
        comment="Model temperature (0.00-1.00)"
    )

    # -------------------------------------------------------------------------
    # USAGE LIMITS
    # -------------------------------------------------------------------------

    monthly_budget_usd: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(10, 2),
        nullable=True,
        comment="Monthly spending limit in USD"
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default="true",
        default=True,
        index=True,  # idx_claude_accounts_active
        comment="Whether account is active and can be used"
    )

    # -------------------------------------------------------------------------
    # METADATA
    # -------------------------------------------------------------------------

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.current_timestamp(),
        default=func.current_timestamp(),
        comment="Creation timestamp"
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.current_timestamp(),
        default=func.current_timestamp(),
        onupdate=func.current_timestamp(),
        comment="Last update timestamp"
    )

    last_used_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Last time this account was used for a task"
    )

    # -------------------------------------------------------------------------
    # RELATIONSHIPS
    # -------------------------------------------------------------------------

    # Projects using this account (one-to-many)
    projects: Mapped[List["Project"]] = relationship(
        "Project",
        back_populates="claude_account",
        foreign_keys="Project.claude_account_id",
        lazy="dynamic",  # Return query object for filtering
    )

    # Task runs using this account (one-to-many)
    task_runs: Mapped[List["TaskRun"]] = relationship(
        "TaskRun",
        back_populates="claude_account",
        foreign_keys="TaskRun.claude_account_id",
        lazy="dynamic",
    )

    # -------------------------------------------------------------------------
    # TABLE ARGUMENTS (constraints, indexes)
    # -------------------------------------------------------------------------

    __table_args__ = (
        # Check constraint: account_type must be 'api' or 'subscription'
        CheckConstraint(
            "account_type IN ('api', 'subscription')",
            name="check_account_type",
        ),

        # Check constraint: API mode requires api_key, subscription mode requires config_directory
        CheckConstraint(
            "(account_type = 'api' AND api_key IS NOT NULL) OR "
            "(account_type = 'subscription' AND config_directory IS NOT NULL)",
            name="check_api_key_required",
        ),

        # Check constraint: temperature must be between 0.0 and 1.0
        CheckConstraint(
            "temperature >= 0.0 AND temperature <= 1.0",
            name="check_temperature_range",
        ),

        # Check constraint: max_tokens must be positive
        CheckConstraint(
            "max_tokens > 0",
            name="check_max_tokens_positive",
        ),

        # Check constraint: monthly_budget must be positive if set
        CheckConstraint(
            "monthly_budget_usd IS NULL OR monthly_budget_usd > 0",
            name="check_monthly_budget_positive",
        ),

        # Table comment
        {"comment": "Claude API credentials and configuration"},
    )

    # -------------------------------------------------------------------------
    # VALIDATORS
    # -------------------------------------------------------------------------

    @validates("account_type")
    def validate_account_type(self, key: str, value: str) -> str:
        """Validate account_type is valid.

        Args:
            key: Field name
            value: Account type value

        Returns:
            str: Validated account type

        Raises:
            ValueError: If account type is invalid
        """
        if value not in ("api", "subscription"):
            raise ValueError(f"account_type must be 'api' or 'subscription', got '{value}'")
        return value

    @validates("temperature")
    def validate_temperature(self, key: str, value: Decimal) -> Decimal:
        """Validate temperature is in valid range.

        Args:
            key: Field name
            value: Temperature value

        Returns:
            Decimal: Validated temperature

        Raises:
            ValueError: If temperature is out of range
        """
        if value < 0 or value > 1:
            raise ValueError(f"temperature must be between 0.0 and 1.0, got {value}")
        return value

    @validates("max_tokens")
    def validate_max_tokens(self, key: str, value: int) -> int:
        """Validate max_tokens is positive.

        Args:
            key: Field name
            value: Max tokens value

        Returns:
            int: Validated max tokens

        Raises:
            ValueError: If max_tokens is not positive
        """
        if value <= 0:
            raise ValueError(f"max_tokens must be positive, got {value}")
        return value

    # -------------------------------------------------------------------------
    # METHODS
    # -------------------------------------------------------------------------

    def __repr__(self) -> str:
        """String representation of ClaudeAccount."""
        return (
            f"<ClaudeAccount(id={self.id}, name='{self.name}', "
            f"type='{self.account_type}', model='{self.model}', "
            f"active={self.is_active})>"
        )

    def is_api_mode(self) -> bool:
        """Check if account is in API mode.

        Returns:
            bool: True if API mode, False if subscription mode
        """
        return self.account_type == "api"

    def is_subscription_mode(self) -> bool:
        """Check if account is in subscription mode.

        Returns:
            bool: True if subscription mode, False if API mode
        """
        return self.account_type == "subscription"

    def has_budget_limit(self) -> bool:
        """Check if account has a monthly budget limit set.

        Returns:
            bool: True if monthly budget is set, False otherwise
        """
        return self.monthly_budget_usd is not None

    def update_last_used(self) -> None:
        """Update the last_used_at timestamp to current time."""
        self.last_used_at = func.current_timestamp()

    def deactivate(self) -> None:
        """Deactivate the account (prevents further use)."""
        self.is_active = False

    def activate(self) -> None:
        """Activate the account (allows use)."""
        self.is_active = True

    def get_api_key_preview(self) -> Optional[str]:
        """Get a safe preview of the API key.

        Returns first 8 characters and last 4 characters for identification,
        with the middle part masked.

        Returns:
            Optional[str]: Masked API key preview, or None if not set

        Example:
            >>> account.api_key = "sk-ant-1234567890abcdefghij"
            >>> account.get_api_key_preview()
            'sk-ant-1***ghij'
        """
        if not self.api_key:
            return None

        if len(self.api_key) <= 12:
            # Key too short to preview safely
            return f"{self.api_key[:4]}***"

        # Show first 8 and last 4 characters
        return f"{self.api_key[:8]}***{self.api_key[-4:]}"

    def to_dict(self, include_sensitive: bool = False) -> dict:
        """Convert account to dictionary.

        Args:
            include_sensitive: Whether to include sensitive fields (api_key, session_token)

        Returns:
            dict: Account data as dictionary

        Example:
            >>> account.to_dict()
            {
                'id': '123e4567-e89b-12d3-a456-426614174000',
                'name': 'Production API',
                'account_type': 'api',
                'model': 'claude-sonnet-4-5',
                'is_active': True,
                ...
            }
        """
        data = {
            "id": str(self.id),
            "name": self.name,
            "account_type": self.account_type,
            "model": self.model,
            "max_tokens": self.max_tokens,
            "temperature": float(self.temperature),
            "monthly_budget_usd": float(self.monthly_budget_usd) if self.monthly_budget_usd else None,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "last_used_at": self.last_used_at.isoformat() if self.last_used_at else None,
        }

        if include_sensitive:
            data["api_key"] = self.api_key
            data["config_directory"] = self.config_directory
            data["session_token"] = self.session_token
        else:
            # Include safe previews only
            data["api_key_preview"] = self.get_api_key_preview()

        return data
