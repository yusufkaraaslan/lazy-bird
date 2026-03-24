"""Project model - Project configurations and settings.

This module defines the Project model which stores project configurations,
automation settings, integration details, and resource limits.
"""

import uuid
from datetime import datetime
from decimal import Decimal
from typing import List, Optional

from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import TSVECTOR, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from lazy_bird.core.database import Base


class Project(Base):
    """Project model for storing project configurations.

    A Project represents a software project being automated by Lazy-Bird.
    It contains git repository information, framework configuration,
    automation settings, and resource limits.

    Attributes:
        id: Unique project identifier (UUID)
        name: Human-readable project name
        slug: URL-safe unique identifier

        repo_url: Git repository URL
        default_branch: Default git branch (usually 'main' or 'master')

        framework_preset_id: Reference to framework preset
        framework_preset: Relationship to FrameworkPreset model
        project_type: Project type (python, nodejs, rust, godot, etc.)

        test_command: Custom test command (overrides preset)
        build_command: Custom build command (overrides preset)
        lint_command: Custom lint command (overrides preset)
        format_command: Custom format command (overrides preset)

        automation_enabled: Whether automation is active
        ready_state_name: State name for ready tasks (e.g., "Ready")
        in_progress_state_name: State name for running tasks
        review_state_name: State name for review
        done_state_name: State name for completed tasks

        max_concurrent_tasks: Maximum parallel task executions
        task_timeout_seconds: Task execution timeout
        max_cost_per_task_usd: Cost limit per task
        daily_cost_limit_usd: Daily total cost limit

        github_installation_id: GitHub App installation ID
        gitlab_project_id: GitLab project ID
        source_platform: Platform type (github, gitlab, plane)
        source_platform_url: Platform URL

        claude_account_id: Reference to Claude account
        claude_account: Relationship to ClaudeAccount model

        created_at: Creation timestamp
        updated_at: Last update timestamp
        deleted_at: Soft delete timestamp (NULL if active)

        search_vector: Full-text search vector (auto-generated)

        task_runs: Relationship to TaskRun models
        webhook_subscriptions: Relationship to WebhookSubscription models
        daily_usages: Relationship to DailyUsage models
        api_keys: Relationship to ApiKey models
    """

    __tablename__ = "projects"

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
        String(255), nullable=False, comment="Human-readable project name"
    )

    slug: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        nullable=False,
        index=True,  # idx_projects_slug
        comment="URL-safe unique identifier",
    )

    # -------------------------------------------------------------------------
    # GIT CONFIGURATION
    # -------------------------------------------------------------------------

    repo_url: Mapped[str] = mapped_column(
        String(500), nullable=False, comment="Git repository URL (GitHub, GitLab, etc.)"
    )

    default_branch: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        server_default="main",
        default="main",
        comment="Default git branch for task execution",
    )

    # -------------------------------------------------------------------------
    # FRAMEWORK CONFIGURATION
    # -------------------------------------------------------------------------

    framework_preset_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("framework_presets.id", ondelete="SET NULL"),
        nullable=True,
        comment="Reference to framework preset (optional)",
    )

    project_type: Mapped[str] = mapped_column(
        String(50), nullable=False, comment="Project type: python, nodejs, rust, godot, etc."
    )

    # -------------------------------------------------------------------------
    # CUSTOM COMMANDS (override preset)
    # -------------------------------------------------------------------------

    test_command: Mapped[Optional[str]] = mapped_column(
        String(500), nullable=True, comment="Custom test command (overrides preset)"
    )

    build_command: Mapped[Optional[str]] = mapped_column(
        String(500), nullable=True, comment="Custom build command (overrides preset)"
    )

    lint_command: Mapped[Optional[str]] = mapped_column(
        String(500), nullable=True, comment="Custom lint command (overrides preset)"
    )

    format_command: Mapped[Optional[str]] = mapped_column(
        String(500), nullable=True, comment="Custom format command (overrides preset)"
    )

    # -------------------------------------------------------------------------
    # AUTOMATION SETTINGS
    # -------------------------------------------------------------------------

    automation_enabled: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default="false",
        default=False,
        index=True,  # idx_projects_automation_enabled
        comment="Whether automation is active for this project",
    )

    ready_state_name: Mapped[Optional[str]] = mapped_column(
        String(100), nullable=True, comment="State name for ready tasks (e.g., 'Ready', 'To Do')"
    )

    in_progress_state_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        server_default="In Progress",
        default="In Progress",
        comment="State name for running tasks",
    )

    review_state_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        server_default="In Review",
        default="In Review",
        comment="State name for tasks in review",
    )

    done_state_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        server_default="Done",
        default="Done",
        comment="State name for completed tasks",
    )

    # -------------------------------------------------------------------------
    # RESOURCE LIMITS
    # -------------------------------------------------------------------------

    max_concurrent_tasks: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        server_default="3",
        default=3,
        comment="Maximum number of parallel task executions",
    )

    task_timeout_seconds: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        server_default="1800",
        default=1800,  # 30 minutes
        comment="Task execution timeout in seconds",
    )

    max_cost_per_task_usd: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False,
        server_default="5.00",
        default=Decimal("5.00"),
        comment="Maximum cost per task in USD",
    )

    daily_cost_limit_usd: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False,
        server_default="50.00",
        default=Decimal("50.00"),
        comment="Daily total cost limit in USD",
    )

    # -------------------------------------------------------------------------
    # INTEGRATION SETTINGS
    # -------------------------------------------------------------------------

    github_installation_id: Mapped[Optional[int]] = mapped_column(
        BigInteger, nullable=True, comment="GitHub App installation ID for this project"
    )

    gitlab_project_id: Mapped[Optional[int]] = mapped_column(
        BigInteger, nullable=True, comment="GitLab project ID for this project"
    )

    source_platform: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        index=True,  # idx_projects_source_platform
        comment="Source platform: github, gitlab, plane, etc.",
    )

    source_platform_url: Mapped[Optional[str]] = mapped_column(
        String(500), nullable=True, comment="Platform URL for web UI integration"
    )

    # -------------------------------------------------------------------------
    # CLAUDE ACCOUNT
    # -------------------------------------------------------------------------

    claude_account_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("claude_accounts.id", ondelete="SET NULL"),
        nullable=True,
        comment="Reference to Claude API account",
    )

    # -------------------------------------------------------------------------
    # METADATA
    # -------------------------------------------------------------------------

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.current_timestamp(),
        default=func.current_timestamp(),
        comment="Creation timestamp",
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.current_timestamp(),
        default=func.current_timestamp(),
        onupdate=func.current_timestamp(),
        comment="Last update timestamp",
    )

    deleted_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="Soft delete timestamp (NULL if active)"
    )

    # -------------------------------------------------------------------------
    # FULL-TEXT SEARCH
    # -------------------------------------------------------------------------

    search_vector: Mapped[Optional[str]] = mapped_column(
        TSVECTOR,
        nullable=True,
        # Note: In PostgreSQL, this is a GENERATED ALWAYS column
        # SQLAlchemy doesn't directly support GENERATED columns in declarative,
        # so we'll create this via Alembic migration with raw SQL
        comment="Full-text search vector (auto-generated from name + repo_url)",
    )

    # -------------------------------------------------------------------------
    # RELATIONSHIPS
    # -------------------------------------------------------------------------

    # Framework preset (many-to-one)
    framework_preset: Mapped[Optional["FrameworkPreset"]] = relationship(
        "FrameworkPreset",
        back_populates="projects",
        foreign_keys=[framework_preset_id],
        lazy="joined",  # Eager load preset data
    )

    # Claude account (many-to-one)
    claude_account: Mapped[Optional["ClaudeAccount"]] = relationship(
        "ClaudeAccount",
        back_populates="projects",
        foreign_keys=[claude_account_id],
        lazy="joined",  # Eager load account data
    )

    # Task runs (one-to-many)
    task_runs: Mapped[List["TaskRun"]] = relationship(
        "TaskRun",
        back_populates="project",
        cascade="all, delete-orphan",
        lazy="select",
    )

    # Webhook subscriptions (one-to-many)
    webhook_subscriptions: Mapped[List["WebhookSubscription"]] = relationship(
        "WebhookSubscription",
        back_populates="project",
        cascade="all, delete-orphan",
        lazy="dynamic",
    )

    # Daily usage records (one-to-many)
    daily_usages: Mapped[List["DailyUsage"]] = relationship(
        "DailyUsage",
        back_populates="project",
        cascade="all, delete-orphan",
        lazy="dynamic",
    )

    # API keys (one-to-many)
    api_keys: Mapped[List["ApiKey"]] = relationship(
        "ApiKey",
        back_populates="project",
        cascade="all, delete-orphan",
        lazy="dynamic",
    )

    # -------------------------------------------------------------------------
    # TABLE ARGUMENTS (indexes, constraints)
    # -------------------------------------------------------------------------

    __table_args__ = (
        # Index on slug (already defined via index=True on column)
        # Index("idx_projects_slug", "slug"),  # Auto-created by index=True
        # Index on source_platform
        # Index("idx_projects_source_platform", "source_platform"),  # Auto-created
        # Index on automation_enabled
        # Index("idx_projects_automation_enabled", "automation_enabled"),  # Auto-created
        # GIN index for full-text search (created via Alembic migration)
        Index("idx_projects_search", search_vector, postgresql_using="gin"),
        # Partial index for active projects (non-deleted)
        Index(
            "idx_projects_deleted_at",
            deleted_at,
            postgresql_where=(deleted_at.is_(None)),
        ),
        # Table comment
        {"comment": "Project configurations and automation settings"},
    )

    # -------------------------------------------------------------------------
    # METHODS
    # -------------------------------------------------------------------------

    def __repr__(self) -> str:
        """String representation of Project."""
        return (
            f"<Project(id={self.id}, slug='{self.slug}', "
            f"name='{self.name}', type='{self.project_type}', "
            f"enabled={self.automation_enabled})>"
        )

    @property
    def is_active(self) -> bool:
        """Check if project is active (not soft-deleted).

        Returns:
            bool: True if project is active, False if deleted
        """
        return self.deleted_at is None

    def get_effective_test_command(self) -> Optional[str]:
        """Get effective test command (custom or from preset).

        Returns:
            Optional[str]: Test command to use
        """
        if self.test_command:
            return self.test_command
        if self.framework_preset:
            return self.framework_preset.test_command
        return None

    def get_effective_build_command(self) -> Optional[str]:
        """Get effective build command (custom or from preset).

        Returns:
            Optional[str]: Build command to use
        """
        if self.build_command:
            return self.build_command
        if self.framework_preset:
            return self.framework_preset.build_command
        return None

    def get_effective_lint_command(self) -> Optional[str]:
        """Get effective lint command (custom or from preset).

        Returns:
            Optional[str]: Lint command to use
        """
        if self.lint_command:
            return self.lint_command
        if self.framework_preset:
            return self.framework_preset.lint_command
        return None

    def get_effective_format_command(self) -> Optional[str]:
        """Get effective format command (custom or from preset).

        Returns:
            Optional[str]: Format command to use
        """
        if self.format_command:
            return self.format_command
        if self.framework_preset:
            return self.framework_preset.format_command
        return None

    def soft_delete(self) -> None:
        """Soft delete the project by setting deleted_at timestamp."""
        self.deleted_at = func.current_timestamp()
        self.automation_enabled = False  # Disable automation on delete

    def restore(self) -> None:
        """Restore a soft-deleted project."""
        self.deleted_at = None
