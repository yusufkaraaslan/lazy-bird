"""Pydantic schemas for Auth API endpoints."""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserCreate(BaseModel):
    """Schema for user registration."""

    email: EmailStr = Field(
        ...,
        description="User email address",
        examples=["user@example.com"],
    )
    password: str = Field(
        ...,
        min_length=8,
        max_length=128,
        description="User password (8-128 characters)",
    )
    display_name: Optional[str] = Field(
        default=None,
        max_length=255,
        description="Human-readable display name",
        examples=["John Doe"],
    )


class UserLogin(BaseModel):
    """Schema for user login."""

    email: EmailStr = Field(
        ...,
        description="User email address",
        examples=["user@example.com"],
    )
    password: str = Field(
        ...,
        description="User password",
    )


class UserResponse(BaseModel):
    """Schema for user responses."""

    id: UUID = Field(..., description="Unique user identifier")
    email: str = Field(..., description="User email address")
    display_name: Optional[str] = Field(default=None, description="Display name")
    role: str = Field(..., description="User role (admin or user)")
    is_active: bool = Field(..., description="Whether account is active")
    created_at: datetime = Field(..., description="Account creation timestamp")

    model_config = ConfigDict(from_attributes=True)


class TokenResponse(BaseModel):
    """Schema for JWT token responses."""

    access_token: str = Field(..., description="JWT access token")
    refresh_token: str = Field(..., description="JWT refresh token")
    token_type: str = Field(default="bearer", description="Token type")


class RefreshRequest(BaseModel):
    """Schema for token refresh requests."""

    refresh_token: str = Field(
        ...,
        description="JWT refresh token",
    )
