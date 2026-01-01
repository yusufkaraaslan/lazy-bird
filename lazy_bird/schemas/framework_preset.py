"""Pydantic schemas for FrameworkPreset API endpoints."""

from datetime import datetime
from typing import Any, Dict, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class FrameworkPresetBase(BaseModel):
    """Base FrameworkPreset schema with shared fields."""

    name: str = Field(
        ...,
        min_length=1,
        max_length=100,
        pattern=r"^[a-z0-9-]+$",
        description="Internal preset name (lowercase, unique)",
        examples=["godot", "django", "react"],
    )

    display_name: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Human-readable display name",
        examples=["Godot Engine 4.x", "Django", "React + Vite"],
    )

    description: Optional[str] = Field(
        default=None,
        description="Preset description",
    )

    framework_type: str = Field(
        ...,
        min_length=1,
        max_length=50,
        description="Framework category: game_engine, backend, frontend, language",
        examples=["game_engine", "backend", "frontend", "language"],
    )

    language: Optional[str] = Field(
        default=None,
        max_length=50,
        description="Programming language",
        examples=["gdscript", "python", "javascript", "rust"],
    )

    test_command: str = Field(
        ...,
        min_length=1,
        max_length=500,
        description="Command to run tests (required)",
        examples=["pytest", "npm test", "cargo test"],
    )

    build_command: Optional[str] = Field(
        default=None,
        max_length=500,
        description="Command to build project",
    )

    lint_command: Optional[str] = Field(
        default=None,
        max_length=500,
        description="Command to lint code",
    )

    format_command: Optional[str] = Field(
        default=None,
        max_length=500,
        description="Command to format code",
    )

    config_files: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Framework-specific config file paths (JSON)",
        examples=[{"godot": "project.godot", "python": "pyproject.toml"}],
    )


class FrameworkPresetCreate(FrameworkPresetBase):
    """Schema for creating a new framework preset."""
    pass


class FrameworkPresetUpdate(BaseModel):
    """Schema for updating an existing framework preset."""

    display_name: Optional[str] = Field(default=None, min_length=1, max_length=255)
    description: Optional[str] = Field(default=None)
    framework_type: Optional[str] = Field(default=None, max_length=50)
    language: Optional[str] = Field(default=None, max_length=50)
    test_command: Optional[str] = Field(default=None, max_length=500)
    build_command: Optional[str] = Field(default=None, max_length=500)
    lint_command: Optional[str] = Field(default=None, max_length=500)
    format_command: Optional[str] = Field(default=None, max_length=500)
    config_files: Optional[Dict[str, Any]] = Field(default=None)

    model_config = ConfigDict(extra="forbid")


class FrameworkPresetResponse(FrameworkPresetBase):
    """Schema for framework preset API responses."""

    id: UUID = Field(..., description="Unique preset identifier")
    is_builtin: bool = Field(..., description="Whether this is a built-in preset")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")

    model_config = ConfigDict(from_attributes=True)


class FrameworkPresetListResponse(BaseModel):
    """Schema for paginated framework preset list responses."""

    items: list[FrameworkPresetResponse] = Field(..., description="List of presets")
    total: int = Field(..., ge=0, description="Total number of presets")
    page: int = Field(..., ge=1, description="Current page number")
    page_size: int = Field(..., ge=1, le=100, description="Items per page")
    pages: int = Field(..., ge=0, description="Total number of pages")

    model_config = ConfigDict(from_attributes=True)
