"""Pydantic schemas for ClaudeAccount API endpoints.

This module defines validation schemas for ClaudeAccount CRUD operations.
Handles dual mode (API vs Subscription) and encrypted credential storage.
"""

from datetime import datetime
from decimal import Decimal
from typing import Literal, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class ClaudeAccountBase(BaseModel):
    """Base ClaudeAccount schema with shared fields."""

    name: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Human-readable account name",
        examples=["Production API", "Personal Subscription"],
    )

    account_type: Literal["api", "subscription"] = Field(
        ...,
        description="Account type: api or subscription",
    )

    # Claude settings
    model: str = Field(
        default="claude-sonnet-4-5",
        min_length=1,
        max_length=100,
        description="Claude model identifier",
        examples=["claude-sonnet-4-5", "claude-opus-4"],
    )

    max_tokens: int = Field(
        default=8000,
        ge=1,
        le=200000,
        description="Maximum tokens per request",
    )

    temperature: Decimal = Field(
        default=Decimal("0.7"),
        ge=Decimal("0.0"),
        le=Decimal("1.0"),
        description="Model temperature (0.00-1.00)",
    )

    # Usage limits
    monthly_budget_usd: Optional[Decimal] = Field(
        default=None,
        ge=Decimal("1.00"),
        description="Monthly spending limit in USD",
    )

    is_active: bool = Field(
        default=True,
        description="Whether account is active and can be used",
    )


class ClaudeAccountCreate(ClaudeAccountBase):
    """Schema for creating a new Claude account.

    Requires either api_key (for API mode) or config_directory (for subscription mode).
    """

    # API mode credentials
    api_key: Optional[str] = Field(
        default=None,
        min_length=1,
        max_length=500,
        description="Anthropic API key (required for api mode, will be encrypted)",
    )

    # Subscription mode credentials
    config_directory: Optional[str] = Field(
        default=None,
        min_length=1,
        max_length=500,
        description="Config directory path (required for subscription mode)",
    )

    session_token: Optional[str] = Field(
        default=None,
        min_length=1,
        max_length=500,
        description="Session token (for subscription mode, will be encrypted)",
    )

    @model_validator(mode="after")
    def validate_credentials(self):
        """Validate that required credentials are provided based on account_type."""
        if self.account_type == "api":
            if not self.api_key:
                raise ValueError("api_key is required for API mode accounts")
        elif self.account_type == "subscription":
            if not self.config_directory:
                raise ValueError("config_directory is required for subscription mode accounts")
        return self


class ClaudeAccountUpdate(BaseModel):
    """Schema for updating an existing Claude account.

    All fields are optional - only provided fields will be updated.
    """

    name: Optional[str] = Field(
        default=None,
        min_length=1,
        max_length=255,
        description="Human-readable account name",
    )

    # Note: account_type cannot be changed after creation

    # API mode credentials (encrypted before storage)
    api_key: Optional[str] = Field(
        default=None,
        min_length=1,
        max_length=500,
        description="New API key (will be encrypted)",
    )

    # Subscription mode credentials
    config_directory: Optional[str] = Field(
        default=None,
        min_length=1,
        max_length=500,
        description="Config directory path",
    )

    session_token: Optional[str] = Field(
        default=None,
        min_length=1,
        max_length=500,
        description="New session token (will be encrypted)",
    )

    # Claude settings
    model: Optional[str] = Field(
        default=None,
        min_length=1,
        max_length=100,
        description="Claude model identifier",
    )

    max_tokens: Optional[int] = Field(
        default=None,
        ge=1,
        le=200000,
        description="Maximum tokens per request",
    )

    temperature: Optional[Decimal] = Field(
        default=None,
        ge=Decimal("0.0"),
        le=Decimal("1.0"),
        description="Model temperature",
    )

    monthly_budget_usd: Optional[Decimal] = Field(
        default=None,
        ge=Decimal("1.00"),
        description="Monthly spending limit",
    )

    is_active: Optional[bool] = Field(
        default=None,
        description="Whether account is active",
    )

    model_config = ConfigDict(extra="forbid")


class ClaudeAccountResponse(BaseModel):
    """Schema for Claude account API responses.

    Includes all fields except encrypted credentials (uses preview instead).
    """

    id: UUID = Field(..., description="Unique account identifier")
    name: str = Field(..., description="Human-readable account name")
    account_type: Literal["api", "subscription"] = Field(..., description="Account type")

    # API key preview (not full key)
    api_key_preview: Optional[str] = Field(
        default=None,
        description="Safe preview of API key (e.g., 'sk-ant-1***ghij')",
    )

    # Subscription mode (non-sensitive)
    config_directory: Optional[str] = Field(
        default=None,
        description="Config directory path",
    )

    # Claude settings
    model: str = Field(..., description="Claude model identifier")
    max_tokens: int = Field(..., description="Maximum tokens per request")
    temperature: Decimal = Field(..., description="Model temperature")

    # Usage limits
    monthly_budget_usd: Optional[Decimal] = Field(
        default=None,
        description="Monthly spending limit in USD",
    )

    is_active: bool = Field(..., description="Whether account is active")

    # Metadata
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    last_used_at: Optional[datetime] = Field(
        default=None,
        description="Last time this account was used",
    )

    model_config = ConfigDict(from_attributes=True)


class ClaudeAccountListResponse(BaseModel):
    """Schema for paginated Claude account list responses."""

    items: list[ClaudeAccountResponse] = Field(..., description="List of accounts")
    total: int = Field(..., ge=0, description="Total number of accounts")
    page: int = Field(..., ge=1, description="Current page number")
    page_size: int = Field(..., ge=1, le=100, description="Items per page")
    pages: int = Field(..., ge=0, description="Total number of pages")

    model_config = ConfigDict(from_attributes=True)
