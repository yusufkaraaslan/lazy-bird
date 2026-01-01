"""Pydantic schemas for Project API endpoints.

This module defines validation schemas for Project CRUD operations.
Uses Pydantic v2 with comprehensive validation and documentation.
"""

from datetime import datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator


class ProjectBase(BaseModel):
    """Base Project schema with shared fields.

    This schema contains fields common to both create and update operations.
    """

    name: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Human-readable project name",
        examples=["My Godot Game", "Backend API"],
    )

    repo_url: str = Field(
        ...,
        min_length=1,
        max_length=500,
        description="Git repository URL (GitHub, GitLab, etc.)",
        examples=["https://github.com/user/my-game"],
    )

    default_branch: str = Field(
        default="main",
        min_length=1,
        max_length=100,
        description="Default git branch for task execution",
        examples=["main", "master", "develop"],
    )

    project_type: str = Field(
        ...,
        min_length=1,
        max_length=50,
        description="Project type: python, nodejs, rust, godot, etc.",
        examples=["godot", "python", "nodejs", "rust"],
    )

    # Optional: Framework preset
    framework_preset_id: Optional[UUID] = Field(
        default=None,
        description="Reference to framework preset (optional)",
    )

    # Optional: Custom commands (override preset)
    test_command: Optional[str] = Field(
        default=None,
        max_length=500,
        description="Custom test command (overrides preset)",
        examples=["pytest tests/"],
    )

    build_command: Optional[str] = Field(
        default=None,
        max_length=500,
        description="Custom build command (overrides preset)",
        examples=["npm run build"],
    )

    lint_command: Optional[str] = Field(
        default=None,
        max_length=500,
        description="Custom lint command (overrides preset)",
        examples=["flake8 ."],
    )

    format_command: Optional[str] = Field(
        default=None,
        max_length=500,
        description="Custom format command (overrides preset)",
        examples=["black ."],
    )

    # Automation settings
    automation_enabled: bool = Field(
        default=False,
        description="Whether automation is active for this project",
    )

    ready_state_name: Optional[str] = Field(
        default=None,
        max_length=100,
        description="State name for ready tasks (e.g., 'Ready', 'To Do')",
        examples=["Ready", "To Do", "Backlog"],
    )

    in_progress_state_name: str = Field(
        default="In Progress",
        max_length=100,
        description="State name for running tasks",
    )

    review_state_name: str = Field(
        default="In Review",
        max_length=100,
        description="State name for tasks in review",
    )

    done_state_name: str = Field(
        default="Done",
        max_length=100,
        description="State name for completed tasks",
    )

    # Resource limits
    max_concurrent_tasks: int = Field(
        default=3,
        ge=1,
        le=10,
        description="Maximum number of parallel task executions",
    )

    task_timeout_seconds: int = Field(
        default=1800,
        ge=300,
        le=7200,
        description="Task execution timeout in seconds",
    )

    max_cost_per_task_usd: Decimal = Field(
        default=Decimal("5.00"),
        ge=Decimal("0.01"),
        le=Decimal("100.00"),
        description="Maximum cost per task in USD",
    )

    daily_cost_limit_usd: Decimal = Field(
        default=Decimal("50.00"),
        ge=Decimal("1.00"),
        le=Decimal("1000.00"),
        description="Daily total cost limit in USD",
    )

    # Integration settings
    github_installation_id: Optional[int] = Field(
        default=None,
        description="GitHub App installation ID for this project",
    )

    gitlab_project_id: Optional[int] = Field(
        default=None,
        description="GitLab project ID for this project",
    )

    source_platform: Optional[str] = Field(
        default=None,
        max_length=50,
        description="Source platform: github, gitlab, plane, etc.",
        examples=["github", "gitlab", "plane"],
    )

    source_platform_url: Optional[str] = Field(
        default=None,
        max_length=500,
        description="Platform URL for web UI integration",
    )

    # Claude account
    claude_account_id: Optional[UUID] = Field(
        default=None,
        description="Reference to Claude API account",
    )

    @field_validator("project_type")
    @classmethod
    def validate_project_type(cls, v: str) -> str:
        """Validate project_type is reasonable."""
        valid_types = [
            "python", "nodejs", "rust", "go", "java", "csharp",
            "godot", "unity", "bevy", "unreal",
            "django", "fastapi", "flask", "rails", "express",
            "react", "vue", "angular", "svelte",
            "custom"
        ]
        if v.lower() not in valid_types:
            # Allow any type, just warn in logs
            pass
        return v.lower()

    @field_validator("source_platform")
    @classmethod
    def validate_source_platform(cls, v: Optional[str]) -> Optional[str]:
        """Validate source_platform is known platform."""
        if v is None:
            return v
        valid_platforms = ["github", "gitlab", "plane", "linear", "jira", "custom"]
        if v.lower() not in valid_platforms:
            # Allow any platform
            pass
        return v.lower()


class ProjectCreate(ProjectBase):
    """Schema for creating a new project.

    Requires slug in addition to base fields.
    """

    slug: str = Field(
        ...,
        min_length=1,
        max_length=100,
        pattern=r"^[a-z0-9-]+$",
        description="URL-safe unique identifier (lowercase, alphanumeric, hyphens)",
        examples=["my-godot-game", "backend-api"],
    )

    @field_validator("slug")
    @classmethod
    def validate_slug(cls, v: str) -> str:
        """Validate slug format."""
        if not v:
            raise ValueError("slug cannot be empty")
        if v.startswith("-") or v.endswith("-"):
            raise ValueError("slug cannot start or end with hyphen")
        if "--" in v:
            raise ValueError("slug cannot contain consecutive hyphens")
        return v.lower()


class ProjectUpdate(BaseModel):
    """Schema for updating an existing project.

    All fields are optional - only provided fields will be updated.
    """

    name: Optional[str] = Field(
        default=None,
        min_length=1,
        max_length=255,
        description="Human-readable project name",
    )

    repo_url: Optional[str] = Field(
        default=None,
        min_length=1,
        max_length=500,
        description="Git repository URL",
    )

    default_branch: Optional[str] = Field(
        default=None,
        min_length=1,
        max_length=100,
        description="Default git branch",
    )

    project_type: Optional[str] = Field(
        default=None,
        min_length=1,
        max_length=50,
        description="Project type",
    )

    framework_preset_id: Optional[UUID] = Field(
        default=None,
        description="Framework preset ID",
    )

    test_command: Optional[str] = Field(default=None, max_length=500)
    build_command: Optional[str] = Field(default=None, max_length=500)
    lint_command: Optional[str] = Field(default=None, max_length=500)
    format_command: Optional[str] = Field(default=None, max_length=500)

    automation_enabled: Optional[bool] = Field(default=None)
    ready_state_name: Optional[str] = Field(default=None, max_length=100)
    in_progress_state_name: Optional[str] = Field(default=None, max_length=100)
    review_state_name: Optional[str] = Field(default=None, max_length=100)
    done_state_name: Optional[str] = Field(default=None, max_length=100)

    max_concurrent_tasks: Optional[int] = Field(default=None, ge=1, le=10)
    task_timeout_seconds: Optional[int] = Field(default=None, ge=300, le=7200)
    max_cost_per_task_usd: Optional[Decimal] = Field(default=None, ge=Decimal("0.01"), le=Decimal("100.00"))
    daily_cost_limit_usd: Optional[Decimal] = Field(default=None, ge=Decimal("1.00"), le=Decimal("1000.00"))

    github_installation_id: Optional[int] = Field(default=None)
    gitlab_project_id: Optional[int] = Field(default=None)
    source_platform: Optional[str] = Field(default=None, max_length=50)
    source_platform_url: Optional[str] = Field(default=None, max_length=500)

    claude_account_id: Optional[UUID] = Field(default=None)

    model_config = ConfigDict(extra="forbid")  # Reject unknown fields


class ProjectResponse(ProjectBase):
    """Schema for project API responses.

    Includes all fields plus id, slug, timestamps, and relationships.
    """

    id: UUID = Field(..., description="Unique project identifier")
    slug: str = Field(..., description="URL-safe unique identifier")

    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    deleted_at: Optional[datetime] = Field(
        default=None,
        description="Soft delete timestamp (NULL if active)",
    )

    # Computed field
    is_active: bool = Field(
        default=True,
        description="Whether project is active (not deleted)",
    )

    model_config = ConfigDict(from_attributes=True)  # Enable ORM mode


class ProjectListResponse(BaseModel):
    """Schema for paginated project list responses."""

    items: list[ProjectResponse] = Field(..., description="List of projects")
    total: int = Field(..., ge=0, description="Total number of projects")
    page: int = Field(..., ge=1, description="Current page number")
    page_size: int = Field(..., ge=1, le=100, description="Items per page")
    pages: int = Field(..., ge=0, description="Total number of pages")

    model_config = ConfigDict(from_attributes=True)
