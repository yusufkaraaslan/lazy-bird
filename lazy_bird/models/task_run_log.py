"""TaskRunLog model - Detailed task execution logs.

This module defines the TaskRunLog model which stores detailed logs for
task execution, including Claude interactions, tool usage, and progress tracking.
"""

import uuid
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional

from sqlalchemy import CheckConstraint, Column, DateTime, ForeignKey, Index, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates

from lazy_bird.core.database import Base


class LogLevel(str, Enum):
    """Log level enumeration.

    Attributes:
        DEBUG: Debug-level information
        INFO: Informational messages
        WARNING: Warning messages
        ERROR: Error messages
        CRITICAL: Critical error messages
    """

    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class TaskRunLog(Base):
    """TaskRunLog model for detailed task execution logs.

    A TaskRunLog represents a single log entry during task execution.
    Logs capture Claude's interactions, tool usage, errors, and progress.

    Attributes:
        id: Unique log identifier (UUID)
        task_run_id: Reference to task run (cascade delete)
        task_run: Relationship to TaskRun model

        level: Log level (debug, info, warning, error, critical)
        message: Log message text
        step: Execution step (init, planning, implementation, testing, etc.)
        tool_name: Claude tool name used (Read, Write, Bash, etc.)

        log_metadata: Additional data as JSONB
        created_at: Log timestamp
    """

    __tablename__ = "task_run_logs"

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

    task_run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("task_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,  # idx_task_run_logs_task_run
        comment="Reference to task run (cascade delete)"
    )

    # -------------------------------------------------------------------------
    # LOG DETAILS
    # -------------------------------------------------------------------------

    level: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        index=True,  # idx_task_run_logs_level
        comment="Log level: debug, info, warning, error, critical"
    )

    message: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="Log message text"
    )

    # -------------------------------------------------------------------------
    # CONTEXT
    # -------------------------------------------------------------------------

    step: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        comment="Execution step: init, planning, implementation, testing, etc."
    )

    tool_name: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        comment="Claude tool name: Read, Write, Edit, Bash, Grep, etc."
    )

    # -------------------------------------------------------------------------
    # ADDITIONAL DATA
    # -------------------------------------------------------------------------

    log_metadata: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=True,
        server_default="{}",
        default=dict,
        comment="Additional log metadata as JSON"
    )

    # -------------------------------------------------------------------------
    # TIMESTAMP
    # -------------------------------------------------------------------------

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.current_timestamp(),
        default=func.current_timestamp(),
        index=True,  # idx_task_run_logs_created_at
        comment="Log timestamp"
    )

    # -------------------------------------------------------------------------
    # RELATIONSHIPS
    # -------------------------------------------------------------------------

    # Task run (many-to-one)
    task_run: Mapped["TaskRun"] = relationship(
        "TaskRun",
        back_populates="logs",
        foreign_keys=[task_run_id],
    )

    # -------------------------------------------------------------------------
    # TABLE ARGUMENTS (constraints, indexes)
    # -------------------------------------------------------------------------

    __table_args__ = (
        # Level constraint
        CheckConstraint(
            "level IN ('debug', 'info', 'warning', 'error', 'critical')",
            name="check_level",
        ),

        # Composite index for querying logs by task and time
        Index("idx_task_run_logs_task_run_created", task_run_id, created_at),

        # Table comment
        {"comment": "Detailed task execution logs"},
    )

    # -------------------------------------------------------------------------
    # VALIDATORS
    # -------------------------------------------------------------------------

    @validates("level")
    def validate_level(self, key: str, value: str) -> str:
        """Validate log level is valid.

        Args:
            key: Field name
            value: Log level value

        Returns:
            str: Validated log level

        Raises:
            ValueError: If log level is invalid
        """
        valid_levels = ["debug", "info", "warning", "error", "critical"]
        if value not in valid_levels:
            raise ValueError(f"level must be one of {valid_levels}, got '{value}'")
        return value

    # -------------------------------------------------------------------------
    # METHODS
    # -------------------------------------------------------------------------

    def __repr__(self) -> str:
        """String representation of TaskRunLog."""
        return (
            f"<TaskRunLog(id={self.id}, task_run_id={self.task_run_id}, "
            f"level='{self.level}', step='{self.step}')>"
        )

    def is_error(self) -> bool:
        """Check if log is an error or critical level.

        Returns:
            bool: True if error or critical, False otherwise
        """
        return self.level in ["error", "critical"]

    def add_metadata(self, key: str, value: Any) -> None:
        """Add or update a metadata field.

        Args:
            key: Metadata key
            value: Metadata value (must be JSON-serializable)
        """
        if self.metadata is None:
            self.metadata = {}
        self.metadata[key] = value

        # Flag as modified for SQLAlchemy JSONB change detection
        from sqlalchemy.orm.attributes import flag_modified
        from sqlalchemy import inspect

        session = inspect(self).session
        if session:
            flag_modified(self, "metadata")

    def get_metadata(self, key: str, default: Any = None) -> Any:
        """Get a metadata value.

        Args:
            key: Metadata key
            default: Default value if key not found

        Returns:
            Any: Metadata value or default
        """
        if not self.metadata:
            return default
        return self.metadata.get(key, default)

    def to_dict(self) -> dict:
        """Convert log to dictionary for API responses.

        Returns:
            dict: Log data as dictionary
        """
        return {
            "id": str(self.id),
            "task_run_id": str(self.task_run_id),
            "level": self.level,
            "message": self.message,
            "step": self.step,
            "tool_name": self.tool_name,
            "metadata": self.metadata or {},
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    @staticmethod
    def create_log(
        task_run_id: uuid.UUID,
        level: str,
        message: str,
        step: Optional[str] = None,
        tool_name: Optional[str] = None,
        **metadata: Any,
    ) -> "TaskRunLog":
        """Factory method to create a log entry.

        Args:
            task_run_id: Task run UUID
            level: Log level (debug, info, warning, error, critical)
            message: Log message
            step: Optional execution step
            tool_name: Optional Claude tool name
            **metadata: Additional metadata as keyword arguments

        Returns:
            TaskRunLog: Created log instance

        Example:
            >>> log = TaskRunLog.create_log(
            ...     task_run_id=task.id,
            ...     level="info",
            ...     message="Starting task execution",
            ...     step="init",
            ...     duration_ms=150,
            ...     memory_mb=256,
            ... )
        """
        return TaskRunLog(
            task_run_id=task_run_id,
            level=level,
            message=message,
            step=step,
            tool_name=tool_name,
            metadata=metadata if metadata else {},
        )
