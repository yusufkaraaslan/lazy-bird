"""Pydantic schemas for TaskRun API endpoints."""

from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, Literal, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class TaskRunQueue(BaseModel):
    """Schema for queuing a new task."""

    project_id: UUID = Field(..., description="Project identifier")
    claude_account_id: Optional[UUID] = Field(default=None, description="Claude account to use")

    work_item_id: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="External work item ID",
        examples=["issue-42", "JIRA-123"],
    )

    work_item_url: Optional[str] = Field(default=None, max_length=500)
    work_item_title: Optional[str] = Field(default=None, max_length=500)
    work_item_description: Optional[str] = Field(default=None)

    task_type: str = Field(
        default="feature",
        max_length=50,
        description="Task type: feature, bugfix, refactor, docs, etc.",
    )

    complexity: Optional[Literal["simple", "medium", "complex"]] = Field(
        default=None,
        description="Task complexity level",
    )

    prompt: str = Field(
        ...,
        min_length=1,
        description="Prompt sent to Claude for task execution",
    )

    max_retries: int = Field(
        default=3,
        ge=0,
        le=5,
        description="Maximum retry attempts",
    )

    metadata: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Additional task metadata",
    )


class TaskRunUpdate(BaseModel):
    """Schema for updating task run status/results."""

    status: Optional[Literal["queued", "running", "success", "failed", "cancelled", "timeout"]] = (
        Field(
            default=None,
            description="Execution status",
        )
    )

    branch_name: Optional[str] = Field(default=None, max_length=255)
    worktree_path: Optional[str] = Field(default=None, max_length=500)
    commit_sha: Optional[str] = Field(default=None, max_length=40)

    pr_url: Optional[str] = Field(default=None, max_length=500)
    pr_number: Optional[int] = Field(default=None)
    tests_passed: Optional[bool] = Field(default=None)
    test_output: Optional[str] = Field(default=None)
    error_message: Optional[str] = Field(default=None)

    tokens_used: Optional[int] = Field(default=None, ge=0)
    cost_usd: Optional[Decimal] = Field(default=None, ge=Decimal("0"))

    task_metadata: Optional[Dict[str, Any]] = Field(default=None)

    model_config = ConfigDict(extra="forbid")


class TaskRunResponse(BaseModel):
    """Schema for task run API responses."""

    id: UUID = Field(..., description="Unique task run identifier")
    project_id: UUID = Field(..., description="Project identifier")
    claude_account_id: Optional[UUID] = Field(default=None)

    work_item_id: str = Field(..., description="External work item ID")
    work_item_url: Optional[str] = Field(default=None)
    work_item_title: Optional[str] = Field(default=None)

    task_type: str = Field(..., description="Task type")
    complexity: Optional[Literal["simple", "medium", "complex"]] = Field(default=None)

    status: Literal["queued", "running", "success", "failed", "cancelled", "timeout"] = Field(
        ..., description="Execution status"
    )

    started_at: Optional[datetime] = Field(default=None)
    completed_at: Optional[datetime] = Field(default=None)
    duration_seconds: Optional[int] = Field(default=None)

    retry_count: int = Field(..., description="Number of retries attempted")
    max_retries: int = Field(..., description="Maximum retries allowed")

    branch_name: Optional[str] = Field(default=None)
    commit_sha: Optional[str] = Field(default=None)

    pr_url: Optional[str] = Field(default=None)
    pr_number: Optional[int] = Field(default=None)
    tests_passed: Optional[bool] = Field(default=None)

    tokens_used: Optional[int] = Field(default=None)
    cost_usd: Optional[Decimal] = Field(default=None)

    error_message: Optional[str] = Field(default=None)
    task_metadata: Optional[Dict[str, Any]] = Field(default=None)

    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")

    model_config = ConfigDict(from_attributes=True)


class TaskRunListResponse(BaseModel):
    """Schema for paginated task run list responses."""

    items: list[TaskRunResponse] = Field(..., description="List of task runs")
    total: int = Field(..., ge=0, description="Total number of task runs")
    page: int = Field(..., ge=1, description="Current page number")
    page_size: int = Field(..., ge=1, le=100, description="Items per page")
    pages: int = Field(..., ge=0, description="Total number of pages")

    model_config = ConfigDict(from_attributes=True)
