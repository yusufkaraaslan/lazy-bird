"""TaskRun model - Task execution records.

This module defines the TaskRun model which stores task execution records,
including work item details, execution status, git information, test results,
and resource usage.
"""

import uuid
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional

from sqlalchemy import (
    Boolean,
    CheckConstraint,
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
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates

from lazy_bird.core.database import Base


class TaskStatus(str, Enum):
    """Task execution status enumeration.

    Attributes:
        QUEUED: Task is queued and waiting to execute
        RUNNING: Task is currently executing
        SUCCESS: Task completed successfully
        FAILED: Task failed with error
        CANCELLED: Task was cancelled by user
        TIMEOUT: Task exceeded timeout limit
    """

    QUEUED = "queued"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMEOUT = "timeout"


class TaskComplexity(str, Enum):
    """Task complexity level enumeration.

    Attributes:
        SIMPLE: Simple task (UI, config, documentation)
        MEDIUM: Medium complexity (features, refactoring)
        COMPLEX: Complex task (architecture, systems, optimization)
    """

    SIMPLE = "simple"
    MEDIUM = "medium"
    COMPLEX = "complex"


class TaskRun(Base):
    """TaskRun model for task execution records.

    A TaskRun represents a single execution of a development task by Claude.
    It tracks the complete lifecycle from queued to completion, including
    git operations, test results, PR creation, and resource usage.

    Attributes:
        id: Unique task run identifier (UUID)

        project_id: Reference to project
        project: Relationship to Project model
        claude_account_id: Reference to Claude account used
        claude_account: Relationship to ClaudeAccount model

        work_item_id: External work item ID (e.g., "issue-42")
        work_item_url: URL to work item on platform
        work_item_title: Work item title
        work_item_description: Work item description

        task_type: Task type (feature, bugfix, refactor)
        complexity: Task complexity (simple, medium, complex)
        prompt: Prompt sent to Claude

        status: Execution status (queued, running, success, failed, cancelled, timeout)

        started_at: When task execution started
        completed_at: When task execution completed
        duration_seconds: Total execution time in seconds
        retry_count: Number of retries attempted
        max_retries: Maximum retries allowed

        branch_name: Git branch created for task
        worktree_path: Path to git worktree
        commit_sha: Git commit SHA

        pr_url: URL to created pull request
        pr_number: PR number on platform
        tests_passed: Whether tests passed
        test_output: Test execution output
        error_message: Error message if failed

        tokens_used: Total tokens consumed
        cost_usd: Total cost in USD

        task_metadata: Additional data as JSONB
        created_at: Creation timestamp
        updated_at: Last update timestamp

        logs: Relationship to TaskRunLog models
    """

    __tablename__ = "task_runs"

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
    # RELATIONS
    # -------------------------------------------------------------------------

    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,  # idx_task_runs_project
        comment="Reference to project (cascade delete)",
    )

    claude_account_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("claude_accounts.id", ondelete="SET NULL"),
        nullable=True,
        comment="Reference to Claude account used for execution",
    )

    # -------------------------------------------------------------------------
    # WORK ITEM IDENTIFICATION
    # -------------------------------------------------------------------------

    work_item_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,  # idx_task_runs_work_item
        comment="External work item ID (e.g., 'issue-42', 'JIRA-123')",
    )

    work_item_url: Mapped[Optional[str]] = mapped_column(
        String(500), nullable=True, comment="URL to work item on platform"
    )

    work_item_title: Mapped[Optional[str]] = mapped_column(
        String(500), nullable=True, comment="Work item title"
    )

    work_item_description: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True, comment="Work item description/body"
    )

    # -------------------------------------------------------------------------
    # TASK DETAILS
    # -------------------------------------------------------------------------

    task_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        server_default="feature",
        default="feature",
        comment="Task type: feature, bugfix, refactor, docs, etc.",
    )

    complexity: Mapped[Optional[str]] = mapped_column(
        String(20), nullable=True, comment="Task complexity: simple, medium, complex"
    )

    prompt: Mapped[str] = mapped_column(
        Text, nullable=False, comment="Prompt sent to Claude for task execution"
    )

    # -------------------------------------------------------------------------
    # EXECUTION STATUS
    # -------------------------------------------------------------------------

    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        server_default="queued",
        default="queued",
        index=True,  # idx_task_runs_status
        comment="Execution status: queued, running, success, failed, cancelled, timeout",
    )

    # -------------------------------------------------------------------------
    # PROGRESS TRACKING
    # -------------------------------------------------------------------------

    started_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="When task execution started"
    )

    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="When task execution completed"
    )

    duration_seconds: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True, comment="Total execution time in seconds (auto-calculated)"
    )

    retry_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        server_default="0",
        default=0,
        comment="Number of retries attempted",
    )

    max_retries: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default="3", default=3, comment="Maximum retries allowed"
    )

    # -------------------------------------------------------------------------
    # GIT DETAILS
    # -------------------------------------------------------------------------

    branch_name: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True, comment="Git branch name created for this task"
    )

    worktree_path: Mapped[Optional[str]] = mapped_column(
        String(500), nullable=True, comment="Path to git worktree"
    )

    commit_sha: Mapped[Optional[str]] = mapped_column(
        String(40), nullable=True, comment="Git commit SHA"
    )

    # -------------------------------------------------------------------------
    # RESULTS
    # -------------------------------------------------------------------------

    pr_url: Mapped[Optional[str]] = mapped_column(
        String(500), nullable=True, comment="URL to created pull request"
    )

    pr_number: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True, comment="Pull request number on platform"
    )

    tests_passed: Mapped[Optional[bool]] = mapped_column(
        Boolean, nullable=True, comment="Whether tests passed (NULL if not run)"
    )

    test_output: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True, comment="Test execution output"
    )

    error_message: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True, comment="Error message if task failed"
    )

    # -------------------------------------------------------------------------
    # RESOURCE USAGE
    # -------------------------------------------------------------------------

    tokens_used: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True, comment="Total tokens consumed by Claude"
    )

    cost_usd: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(10, 4), nullable=True, comment="Total cost in USD"
    )

    # -------------------------------------------------------------------------
    # METADATA
    # -------------------------------------------------------------------------

    task_metadata: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=True,
        server_default="{}",
        default=dict,
        comment="Additional task metadata as JSON",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.current_timestamp(),
        default=func.current_timestamp(),
        index=True,  # idx_task_runs_created_at (with DESC)
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

    # -------------------------------------------------------------------------
    # RELATIONSHIPS
    # -------------------------------------------------------------------------

    # Project (many-to-one)
    project: Mapped["Project"] = relationship(
        "Project",
        back_populates="task_runs",
        foreign_keys=[project_id],
        lazy="joined",  # Eager load project data
    )

    # Claude account (many-to-one)
    claude_account: Mapped[Optional["ClaudeAccount"]] = relationship(
        "ClaudeAccount",
        back_populates="task_runs",
        foreign_keys=[claude_account_id],
        lazy="joined",  # Eager load account data
    )

    # Task run logs (one-to-many)
    logs: Mapped[List["TaskRunLog"]] = relationship(
        "TaskRunLog",
        back_populates="task_run",
        cascade="all, delete-orphan",
        order_by="TaskRunLog.created_at",
        lazy="dynamic",
    )

    # -------------------------------------------------------------------------
    # TABLE ARGUMENTS (constraints, indexes)
    # -------------------------------------------------------------------------

    __table_args__ = (
        # Status constraint
        CheckConstraint(
            "status IN ('queued', 'running', 'success', 'failed', 'cancelled', 'timeout')",
            name="check_status",
        ),
        # Complexity constraint
        CheckConstraint(
            "complexity IS NULL OR complexity IN ('simple', 'medium', 'complex')",
            name="check_complexity",
        ),
        # Composite index for common query: project + status
        Index("idx_task_runs_project_status", project_id, status),
        # Index on created_at DESC for recent tasks
        Index("idx_task_runs_created_at", created_at.desc()),
        # Table comment
        {"comment": "Task execution records and results"},
    )

    # -------------------------------------------------------------------------
    # VALIDATORS
    # -------------------------------------------------------------------------

    @validates("status")
    def validate_status(self, key: str, value: str) -> str:
        """Validate status is valid.

        Args:
            key: Field name
            value: Status value

        Returns:
            str: Validated status

        Raises:
            ValueError: If status is invalid
        """
        valid_statuses = ["queued", "running", "success", "failed", "cancelled", "timeout"]
        if value not in valid_statuses:
            raise ValueError(f"status must be one of {valid_statuses}, got '{value}'")
        return value

    @validates("complexity")
    def validate_complexity(self, key: str, value: Optional[str]) -> Optional[str]:
        """Validate complexity is valid.

        Args:
            key: Field name
            value: Complexity value

        Returns:
            Optional[str]: Validated complexity

        Raises:
            ValueError: If complexity is invalid
        """
        if value is None:
            return value
        valid_complexities = ["simple", "medium", "complex"]
        if value not in valid_complexities:
            raise ValueError(f"complexity must be one of {valid_complexities}, got '{value}'")
        return value

    # -------------------------------------------------------------------------
    # METHODS
    # -------------------------------------------------------------------------

    def __repr__(self) -> str:
        """String representation of TaskRun."""
        return (
            f"<TaskRun(id={self.id}, work_item='{self.work_item_id}', "
            f"status='{self.status}', project_id={self.project_id})>"
        )

    def is_terminal_status(self) -> bool:
        """Check if task is in terminal status (completed or failed).

        Returns:
            bool: True if in terminal status, False otherwise
        """
        return self.status in ["success", "failed", "cancelled", "timeout"]

    def is_running(self) -> bool:
        """Check if task is currently running.

        Returns:
            bool: True if status is running, False otherwise
        """
        return self.status == "running"

    def is_queued(self) -> bool:
        """Check if task is queued.

        Returns:
            bool: True if status is queued, False otherwise
        """
        return self.status == "queued"

    def can_retry(self) -> bool:
        """Check if task can be retried.

        Returns:
            bool: True if retry_count < max_retries, False otherwise
        """
        return self.retry_count < self.max_retries

    def mark_started(self) -> None:
        """Mark task as started (sets started_at and status)."""
        self.status = "running"
        self.started_at = func.current_timestamp()

    def mark_completed(self, success: bool = True, error: Optional[str] = None) -> None:
        """Mark task as completed.

        Args:
            success: Whether task completed successfully
            error: Error message if failed
        """
        self.status = "success" if success else "failed"
        self.completed_at = func.current_timestamp()
        if error:
            self.error_message = error

        # Calculate duration (will be handled by trigger in database)
        if self.started_at and isinstance(self.started_at, datetime):
            duration = datetime.now(self.started_at.tzinfo) - self.started_at
            self.duration_seconds = int(duration.total_seconds())

    def increment_retry(self) -> None:
        """Increment retry count and reset to queued status."""
        self.retry_count += 1
        self.status = "queued"
        self.started_at = None
        self.completed_at = None
        self.error_message = None

    def add_metadata(self, key: str, value: Any) -> None:
        """Add or update a metadata field.

        Args:
            key: Metadata key
            value: Metadata value (must be JSON-serializable)
        """
        if self.task_metadata is None:
            self.task_metadata = {}
        self.task_metadata[key] = value

        # Flag as modified for SQLAlchemy JSONB change detection
        from sqlalchemy.orm.attributes import flag_modified
        from sqlalchemy import inspect

        session = inspect(self).session
        if session:
            flag_modified(self, "task_metadata")

    def get_metadata(self, key: str, default: Any = None) -> Any:
        """Get a metadata value.

        Args:
            key: Metadata key
            default: Default value if key not found

        Returns:
            Any: Metadata value or default
        """
        if not self.task_metadata:
            return default
        return self.task_metadata.get(key, default)

    def to_dict(self) -> dict:
        """Convert task run to dictionary for API responses.

        Returns:
            dict: Task run data as dictionary
        """
        return {
            "id": str(self.id),
            "project_id": str(self.project_id),
            "claude_account_id": str(self.claude_account_id) if self.claude_account_id else None,
            "work_item_id": self.work_item_id,
            "work_item_url": self.work_item_url,
            "work_item_title": self.work_item_title,
            "task_type": self.task_type,
            "complexity": self.complexity,
            "status": self.status,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "duration_seconds": self.duration_seconds,
            "retry_count": self.retry_count,
            "max_retries": self.max_retries,
            "branch_name": self.branch_name,
            "commit_sha": self.commit_sha,
            "pr_url": self.pr_url,
            "pr_number": self.pr_number,
            "tests_passed": self.tests_passed,
            "tokens_used": self.tokens_used,
            "cost_usd": float(self.cost_usd) if self.cost_usd else None,
            "task_metadata": self.task_metadata or {},
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
