"""Pydantic schemas for ApiKey API endpoints."""

from datetime import datetime
from typing import Literal, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ApiKeyBase(BaseModel):
    """Base ApiKey schema with shared fields."""

    name: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Human-readable key name",
        examples=["Production API Key", "Development Key"],
    )

    project_id: Optional[UUID] = Field(
        default=None,
        description="Project ID (NULL for organization-level keys)",
    )

    scopes: list[Literal["read", "write", "admin"]] = Field(
        default=["read"],
        min_length=1,
        description="Array of permission scopes",
        examples=[["read", "write"]],
    )

    expires_at: Optional[datetime] = Field(
        default=None,
        description="Expiration timestamp (NULL for no expiration)",
    )


class ApiKeyCreate(ApiKeyBase):
    """Schema for creating a new API key."""
    pass


class ApiKeyUpdate(BaseModel):
    """Schema for updating an existing API key."""

    name: Optional[str] = Field(default=None, min_length=1, max_length=255)
    scopes: Optional[list[Literal["read", "write", "admin"]]] = Field(default=None, min_length=1)
    expires_at: Optional[datetime] = Field(default=None)
    is_active: Optional[bool] = Field(default=None)

    model_config = ConfigDict(extra="forbid")


class ApiKeyResponse(BaseModel):
    """Schema for API key responses.

    Note: Only returns key_prefix for security. Full key is only shown once during creation.
    """

    id: UUID = Field(..., description="Unique key identifier")
    key_prefix: str = Field(..., description="First 8 chars of key for identification")
    name: str = Field(..., description="Human-readable key name")

    project_id: Optional[UUID] = Field(default=None, description="Project ID")
    scopes: list[str] = Field(..., description="Permission scopes")

    is_active: bool = Field(..., description="Whether key is active")
    expires_at: Optional[datetime] = Field(default=None, description="Expiration timestamp")
    last_used_at: Optional[datetime] = Field(default=None, description="Last usage timestamp")

    created_by: Optional[str] = Field(default=None, description="Creator identifier")
    created_at: datetime = Field(..., description="Creation timestamp")
    revoked_at: Optional[datetime] = Field(default=None, description="Revocation timestamp")

    model_config = ConfigDict(from_attributes=True)


class ApiKeyCreateResponse(ApiKeyResponse):
    """Schema for API key creation response.

    Includes the full key - THIS IS THE ONLY TIME THE FULL KEY IS RETURNED.
    """

    key: str = Field(..., description="Full API key (save this - won't be shown again!)")


class ApiKeyListResponse(BaseModel):
    """Schema for paginated API key list responses."""

    items: list[ApiKeyResponse] = Field(..., description="List of API keys")
    total: int = Field(..., ge=0, description="Total number of keys")
    page: int = Field(..., ge=1, description="Current page number")
    page_size: int = Field(..., ge=1, le=100, description="Items per page")
    pages: int = Field(..., ge=0, description="Total number of pages")

    model_config = ConfigDict(from_attributes=True)
