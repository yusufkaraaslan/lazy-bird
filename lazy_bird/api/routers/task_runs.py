"""TaskRuns API endpoints for managing task execution records.

This module provides CRUD operations for task runs with:
- List with cursor-based pagination
- Filtering by status, project, work item
- Task execution lifecycle management
- Cancellation, retry, and log retrieval
"""

import asyncio
import json
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response, status
from fastapi.responses import StreamingResponse
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from lazy_bird.api.dependencies import RequireRead, RequireWrite, get_async_database
from lazy_bird.api.exceptions import (
    InsufficientPermissionsError,
    ResourceConflictError,
    ResourceNotFoundError,
)
from lazy_bird.core.logging import get_logger
from lazy_bird.core.redis import get_async_redis
from lazy_bird.models.api_key import ApiKey
from lazy_bird.models.task_run import TaskRun
from lazy_bird.models.task_run_log import TaskRunLog
from lazy_bird.schemas.task_run import (
    TaskRunListResponse,
    TaskRunQueue,
    TaskRunResponse,
    TaskRunUpdate,
)
from lazy_bird.services.log_publisher import LogPublisher
from lazy_bird.tasks.task_executor import _fire_webhook

logger = get_logger(__name__)

# Create router
router = APIRouter(prefix="/task-runs", tags=["task-runs"])


@router.get("", response_model=TaskRunListResponse)
@router.get("/", response_model=TaskRunListResponse)
async def list_task_runs(
    # Pagination
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    # Filtering
    project_id: Optional[UUID] = Query(None, description="Filter by project ID"),
    status: Optional[str] = Query(
        None,
        description="Filter by status (queued, running, success, failed, cancelled, timeout)",
    ),
    work_item_id: Optional[str] = Query(None, description="Filter by work item ID"),
    task_type: Optional[str] = Query(
        None, description="Filter by task type (feature, bugfix, refactor, etc.)"
    ),
    complexity: Optional[str] = Query(
        None, description="Filter by complexity (simple, medium, complex)"
    ),
    # Search
    search: Optional[str] = Query(
        None, min_length=2, description="Search in work_item_title, work_item_id"
    ),
    # Dependencies
    db: AsyncSession = Depends(get_async_database),
    api_key: ApiKey = Depends(RequireRead),
) -> TaskRunListResponse:
    """List all task runs with pagination, filtering, and search.

    **Pagination:**
    - Offset-based pagination with page and page_size
    - Default: page=1, page_size=20
    - Max page_size: 100

    **Filtering:**
    - `project_id`: UUID - Filter by project
    - `status`: string - Filter by execution status
    - `work_item_id`: string - Filter by work item ID
    - `task_type`: string - Filter by task type
    - `complexity`: string - Filter by complexity

    **Search:**
    - `search`: string (min 2 chars) - Full-text search across work_item_title, work_item_id

    **Returns:**
    - List of task runs
    - Total count, page info, pagination metadata

    **Authentication:**
    - Requires: API key with 'read', 'write', or 'admin' scope
    """
    # Build base query
    query = select(TaskRun)

    # Apply filters
    filters = []

    # Filter by API key's project scope (if project-specific key)
    if api_key.project_id:
        filters.append(TaskRun.project_id == api_key.project_id)
    elif project_id:
        # Only apply project_id filter if API key is not project-specific
        filters.append(TaskRun.project_id == project_id)

    # Filter by status
    if status:
        filters.append(TaskRun.status == status)

    # Filter by work item ID
    if work_item_id:
        filters.append(TaskRun.work_item_id == work_item_id)

    # Filter by task type
    if task_type:
        filters.append(TaskRun.task_type == task_type)

    # Filter by complexity
    if complexity:
        filters.append(TaskRun.complexity == complexity)

    # Apply search (full-text search on work_item_title and work_item_id)
    if search:
        search_filters = [
            TaskRun.work_item_title.ilike(f"%{search}%"),
            TaskRun.work_item_id.ilike(f"%{search}%"),
        ]
        filters.append(or_(*search_filters))

    # Add all filters to query
    if filters:
        query = query.where(*filters)

    # Get total count
    count_query = select(func.count()).select_from(TaskRun)
    if filters:
        count_query = count_query.where(*filters)
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Calculate pagination
    offset = (page - 1) * page_size
    pages = (total + page_size - 1) // page_size if total > 0 else 0

    # Apply pagination and sorting
    query = (
        query.order_by(TaskRun.created_at.desc())
        .offset(offset)
        .limit(page_size)
        .options(
            selectinload(TaskRun.project),
            selectinload(TaskRun.claude_account),
        )
    )

    # Execute query
    result = await db.execute(query)
    task_runs = result.scalars().all()

    # Convert to response models
    task_run_responses = [TaskRunResponse.model_validate(tr) for tr in task_runs]

    # Log successful query
    logger.info(
        f"Listed {len(task_runs)} task runs (page {page}/{pages})",
        extra={
            "extra_fields": {
                "total": total,
                "page": page,
                "page_size": page_size,
                "filters": {
                    "project_id": str(project_id) if project_id else None,
                    "status": status,
                    "work_item_id": work_item_id,
                    "search": search,
                },
            }
        },
    )

    return TaskRunListResponse(
        items=task_run_responses,
        total=total,
        page=page,
        page_size=page_size,
        pages=pages,
    )


@router.post("", response_model=TaskRunResponse, status_code=status.HTTP_201_CREATED)
@router.post("/", response_model=TaskRunResponse, status_code=status.HTTP_201_CREATED)
async def queue_task_run(
    task_data: TaskRunQueue,
    db: AsyncSession = Depends(get_async_database),
    api_key: ApiKey = Depends(RequireWrite),
) -> TaskRunResponse:
    """Queue a new task run for execution.

    **Required Fields:**
    - project_id: UUID - Project to run task for
    - work_item_id: string - External work item ID (e.g., "issue-42")
    - prompt: string - Prompt to send to Claude

    **Optional Fields:**
    - claude_account_id: UUID - Specific Claude account to use
    - work_item_url, work_item_title, work_item_description
    - task_type: string (default: "feature")
    - complexity: "simple" | "medium" | "complex"
    - max_retries: int (default: 3)
    - metadata: dict - Additional task metadata

    **Validation:**
    - Project must exist and not be deleted
    - Project automation must be enabled
    - Claude account must exist (if provided)
    - Project must not exceed concurrent task limit
    - Project must not exceed daily cost limit

    **Returns:**
    - 201 Created: Task queued successfully
    - 404 Not Found: Project or Claude account doesn't exist
    - 409 Conflict: Automation disabled or limits exceeded
    - 422 Validation Error: Invalid input data

    **Authentication:**
    - Requires: API key with 'write' or 'admin' scope
    """
    # Validate project exists and automation enabled
    from lazy_bird.models.project import Project

    project_query = (
        select(Project)
        .where(Project.id == task_data.project_id)
        .where(Project.deleted_at.is_(None))
    )
    project_result = await db.execute(project_query)
    project = project_result.scalar_one_or_none()

    if not project:
        raise ResourceNotFoundError(
            resource_type="Project",
            resource_id=str(task_data.project_id),
        )

    # Check if automation is enabled
    if not project.automation_enabled:
        raise ResourceConflictError(
            detail=f"Project '{project.name}' has automation disabled. "
            "Enable automation in project settings to queue tasks.",
            conflict_field="automation_enabled",
        )

    # Check API key scope (if project-specific key)
    if api_key.project_id and api_key.project_id != project.id:
        raise InsufficientPermissionsError(
            detail=f"API key is scoped to project {api_key.project_id}, "
            f"cannot queue task for project {project.id}"
        )

    # Validate Claude account exists (if provided)
    if task_data.claude_account_id:
        from lazy_bird.models.claude_account import ClaudeAccount

        account_query = select(ClaudeAccount).where(ClaudeAccount.id == task_data.claude_account_id)
        account_result = await db.execute(account_query)
        account = account_result.scalar_one_or_none()

        if not account:
            raise ResourceNotFoundError(
                resource_type="ClaudeAccount",
                resource_id=str(task_data.claude_account_id),
            )

    # Check concurrent task limit
    running_count_query = (
        select(func.count())
        .select_from(TaskRun)
        .where(TaskRun.project_id == project.id)
        .where(TaskRun.status.in_(["queued", "running"]))
    )
    running_count_result = await db.execute(running_count_query)
    running_count = running_count_result.scalar() or 0

    if running_count >= project.max_concurrent_tasks:
        raise ResourceConflictError(
            detail=f"Project has {running_count} tasks queued/running, "
            f"max concurrent tasks is {project.max_concurrent_tasks}. "
            "Wait for tasks to complete or increase limit.",
            conflict_field="max_concurrent_tasks",
        )

    # Check daily cost limit (optional - for future implementation)
    # This would query sum of cost_usd for tasks created today
    # For now, we'll allow queuing (validation happens during execution)

    # Create task run
    task_run = TaskRun(
        project_id=task_data.project_id,
        claude_account_id=task_data.claude_account_id or project.claude_account_id,
        work_item_id=task_data.work_item_id,
        work_item_url=task_data.work_item_url,
        work_item_title=task_data.work_item_title,
        work_item_description=task_data.work_item_description,
        task_type=task_data.task_type,
        complexity=task_data.complexity,
        prompt=task_data.prompt,
        status="queued",
        max_retries=task_data.max_retries,
        task_metadata=task_data.metadata or {},
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )

    db.add(task_run)
    await db.commit()
    await db.refresh(task_run)

    # Trigger Celery task for execution
    try:
        from lazy_bird.tasks.task_executor import execute_task

        execute_task.delay(str(task_run.id))
        logger.info(f"Triggered Celery task for {task_run.id}")
    except Exception as e:
        logger.warning(
            f"Failed to trigger Celery task: {e}. " "Task will be picked up by queue processor."
        )

    # Log successful creation
    logger.info(
        f"Queued task run: {task_run.work_item_id} for project {project.name}",
        extra={
            "extra_fields": {
                "task_run_id": str(task_run.id),
                "project_id": str(project.id),
                "work_item_id": task_run.work_item_id,
                "status": task_run.status,
            }
        },
    )

    return TaskRunResponse.model_validate(task_run)


@router.get("/{task_run_id}", response_model=TaskRunResponse)
async def get_task_run(
    task_run_id: UUID,
    db: AsyncSession = Depends(get_async_database),
    api_key: ApiKey = Depends(RequireRead),
) -> TaskRunResponse:
    """Get a single task run by ID with full details.

    **Path Parameters:**
    - task_run_id: UUID - Task run identifier

    **Returns:**
    - Task run details with:
      - All task run fields
      - Related entities (project, claude_account)
      - Execution status and timings
      - Resource usage (tokens, cost)
      - Results (PR URL, tests, errors)

    **Errors:**
    - 404 Not Found: Task run doesn't exist
    - 403 Forbidden: API key scope restricted to different project

    **Authentication:**
    - Requires: API key with 'read', 'write', or 'admin' scope
    """
    # Build query with eager loading
    query = (
        select(TaskRun)
        .where(TaskRun.id == task_run_id)
        .options(
            selectinload(TaskRun.project),
            selectinload(TaskRun.claude_account),
        )
    )

    # Execute query
    result = await db.execute(query)
    task_run = result.scalar_one_or_none()

    # Check if task run exists
    if not task_run:
        raise ResourceNotFoundError(
            resource_type="TaskRun",
            resource_id=str(task_run_id),
        )

    # Check API key scope (if project-specific key)
    if api_key.project_id and api_key.project_id != task_run.project_id:
        raise InsufficientPermissionsError(
            detail=f"API key is scoped to project {api_key.project_id}, "
            f"cannot access task run for project {task_run.project_id}"
        )

    # Log successful query
    logger.info(
        f"Retrieved task run: {task_run.work_item_id} ({task_run.status})",
        extra={
            "extra_fields": {
                "task_run_id": str(task_run.id),
                "project_id": str(task_run.project_id),
                "status": task_run.status,
            }
        },
    )

    return TaskRunResponse.model_validate(task_run)


@router.patch("/{task_run_id}", response_model=TaskRunResponse)
async def update_task_run(
    task_run_id: UUID,
    update_data: TaskRunUpdate,
    db: AsyncSession = Depends(get_async_database),
    api_key: ApiKey = Depends(RequireWrite),
) -> TaskRunResponse:
    """Update task run status and results (partial update).

    **Path Parameters:**
    - task_run_id: UUID - Task run identifier

    **Request Body (all optional):**
    - status: string - Execution status
    - branch_name, worktree_path, commit_sha: Git details
    - pr_url, pr_number, tests_passed, test_output: Results
    - error_message: Error details
    - tokens_used, cost_usd: Resource usage
    - metadata: Additional data

    **Returns:**
    - Updated task run

    **Errors:**
    - 404 Not Found: Task run doesn't exist
    - 403 Forbidden: API key scope restricted to different project
    - 422 Validation Error: Invalid field values

    **Authentication:**
    - Requires: API key with 'write' or 'admin' scope

    **Note:**
    - Typically used by task execution system to update progress
    - Manual updates should be used with caution
    """
    # Fetch existing task run
    query = select(TaskRun).where(TaskRun.id == task_run_id)
    result = await db.execute(query)
    task_run = result.scalar_one_or_none()

    # Check if task run exists
    if not task_run:
        raise ResourceNotFoundError(
            resource_type="TaskRun",
            resource_id=str(task_run_id),
        )

    # Check API key scope
    if api_key.project_id and api_key.project_id != task_run.project_id:
        raise InsufficientPermissionsError(
            detail=f"API key is scoped to project {api_key.project_id}, "
            f"cannot update task run for project {task_run.project_id}"
        )

    # Get update data (only fields that were provided)
    update_fields = update_data.model_dump(exclude_unset=True)

    # If no fields to update, return existing task run
    if not update_fields:
        logger.info(f"No fields to update for task run: {task_run.work_item_id}")
        return TaskRunResponse.model_validate(task_run)

    # Validate status transition
    if "status" in update_fields:
        new_status = update_fields["status"]
        terminal_statuses = {"success", "failed", "cancelled", "timeout"}
        if task_run.status in terminal_statuses and new_status != task_run.status:
            raise ResourceConflictError(
                detail=f"Cannot transition from '{task_run.status}' to '{new_status}'. "
                f"Task in terminal status.",
                conflict_field="status",
            )

    # Apply updates to task run
    for field, value in update_fields.items():
        setattr(task_run, field, value)

    # Update updated_at timestamp
    task_run.updated_at = datetime.now(timezone.utc)

    # Commit changes
    await db.commit()
    await db.refresh(task_run)

    # Log successful update
    logger.info(
        f"Updated task run: {task_run.work_item_id}",
        extra={
            "extra_fields": {
                "task_run_id": str(task_run.id),
                "updated_fields": list(update_fields.keys()),
                "status": task_run.status,
            }
        },
    )

    return TaskRunResponse.model_validate(task_run)


@router.post("/{task_run_id}/cancel", response_model=TaskRunResponse)
async def cancel_task_run(
    task_run_id: UUID,
    db: AsyncSession = Depends(get_async_database),
    api_key: ApiKey = Depends(RequireWrite),
) -> TaskRunResponse:
    """Cancel a queued or running task.

    **Path Parameters:**
    - task_run_id: UUID - Task run identifier

    **Behavior:**
    - Sets status to 'cancelled'
    - Sets completed_at timestamp
    - Calculates duration if started
    - Signals Celery to stop task (future)

    **Validation:**
    - Task must be in 'queued' or 'running' status
    - Cannot cancel completed tasks

    **Returns:**
    - Updated task run with status='cancelled'

    **Errors:**
    - 404 Not Found: Task run doesn't exist
    - 409 Conflict: Task already in terminal status
    - 403 Forbidden: API key scope restricted

    **Authentication:**
    - Requires: API key with 'write' or 'admin' scope
    """
    # Fetch existing task run
    query = select(TaskRun).where(TaskRun.id == task_run_id)
    result = await db.execute(query)
    task_run = result.scalar_one_or_none()

    # Check if task run exists
    if not task_run:
        raise ResourceNotFoundError(
            resource_type="TaskRun",
            resource_id=str(task_run_id),
        )

    # Check API key scope
    if api_key.project_id and api_key.project_id != task_run.project_id:
        raise InsufficientPermissionsError(
            detail=f"API key is scoped to project {api_key.project_id}, "
            f"cannot cancel task run for project {task_run.project_id}"
        )

    # Check if task can be cancelled
    if task_run.status not in ["queued", "running"]:
        raise ResourceConflictError(
            detail=f"Cannot cancel task with status '{task_run.status}'. "
            "Only queued or running tasks can be cancelled.",
            conflict_field="status",
        )

    # Cancel the task
    task_run.status = "cancelled"
    task_run.completed_at = datetime.now(timezone.utc)
    task_run.updated_at = datetime.now(timezone.utc)

    # Calculate duration if started
    if task_run.started_at:
        duration = task_run.completed_at - task_run.started_at
        task_run.duration_seconds = int(duration.total_seconds())

    # Signal Celery to stop task
    try:
        from lazy_bird.tasks import app as celery_app

        celery_app.control.revoke(str(task_run.id), terminate=True)
        logger.info(f"Sent revoke signal for task {task_run.id}")
    except Exception as e:
        logger.warning(f"Failed to revoke Celery task: {e}")

    # Commit changes
    await db.commit()
    await db.refresh(task_run)

    # Fire webhook for cancelled state
    await _fire_webhook(db, task_run, "task.cancelled")

    # Log cancellation
    logger.info(
        f"Cancelled task run: {task_run.work_item_id}",
        extra={
            "extra_fields": {
                "task_run_id": str(task_run.id),
                "previous_status": task_run.status,
            }
        },
    )

    return TaskRunResponse.model_validate(task_run)


@router.post("/{task_run_id}/retry", response_model=TaskRunResponse)
async def retry_task_run(
    task_run_id: UUID,
    db: AsyncSession = Depends(get_async_database),
    api_key: ApiKey = Depends(RequireWrite),
) -> TaskRunResponse:
    """Retry a failed task.

    **Path Parameters:**
    - task_run_id: UUID - Task run identifier

    **Behavior:**
    - Increments retry_count
    - Resets status to 'queued'
    - Clears error_message
    - Resets started_at and completed_at
    - Triggers new execution (future)

    **Validation:**
    - Task must be in 'failed' or 'timeout' status
    - retry_count must be < max_retries

    **Returns:**
    - Updated task run with status='queued'

    **Errors:**
    - 404 Not Found: Task run doesn't exist
    - 409 Conflict: Task not failed or retry limit exceeded
    - 403 Forbidden: API key scope restricted

    **Authentication:**
    - Requires: API key with 'write' or 'admin' scope
    """
    # Fetch existing task run
    query = select(TaskRun).where(TaskRun.id == task_run_id)
    result = await db.execute(query)
    task_run = result.scalar_one_or_none()

    # Check if task run exists
    if not task_run:
        raise ResourceNotFoundError(
            resource_type="TaskRun",
            resource_id=str(task_run_id),
        )

    # Check API key scope
    if api_key.project_id and api_key.project_id != task_run.project_id:
        raise InsufficientPermissionsError(
            detail=f"API key is scoped to project {api_key.project_id}, "
            f"cannot retry task run for project {task_run.project_id}"
        )

    # Check if task can be retried
    if task_run.status not in ["failed", "timeout"]:
        raise ResourceConflictError(
            detail=f"Cannot retry task with status '{task_run.status}'. "
            "Only failed or timeout tasks can be retried.",
            conflict_field="status",
        )

    # Check retry limit
    if task_run.retry_count >= task_run.max_retries:
        raise ResourceConflictError(
            detail=f"Cannot retry task: retry limit exceeded "
            f"({task_run.retry_count}/{task_run.max_retries}).",
            conflict_field="retry_count",
        )

    # Retry the task
    task_run.retry_count += 1
    task_run.status = "queued"
    task_run.started_at = None
    task_run.completed_at = None
    task_run.duration_seconds = None
    task_run.error_message = None
    task_run.updated_at = datetime.now(timezone.utc)

    # Trigger Celery task for re-execution
    try:
        from lazy_bird.tasks.task_executor import execute_task

        execute_task.delay(str(task_run.id))
        logger.info(f"Triggered retry Celery task for {task_run.id}")
    except Exception as e:
        logger.warning(
            f"Failed to trigger retry Celery task: {e}. "
            "Task will be picked up by queue processor."
        )

    # Commit changes
    await db.commit()
    await db.refresh(task_run)

    # Fire webhook for queued state (retry)
    await _fire_webhook(db, task_run, "task.queued")

    # Log retry
    logger.info(
        f"Retrying task run: {task_run.work_item_id} (attempt {task_run.retry_count}/{task_run.max_retries})",
        extra={
            "extra_fields": {
                "task_run_id": str(task_run.id),
                "retry_count": task_run.retry_count,
                "max_retries": task_run.max_retries,
            }
        },
    )

    return TaskRunResponse.model_validate(task_run)


@router.delete("/{task_run_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_task_run(
    task_run_id: UUID,
    db: AsyncSession = Depends(get_async_database),
    api_key: ApiKey = Depends(RequireWrite),
) -> Response:
    """Delete a task run record."""
    query = select(TaskRun).where(TaskRun.id == task_run_id)
    result = await db.execute(query)
    task_run = result.scalar_one_or_none()

    if not task_run:
        raise ResourceNotFoundError(
            resource_type="TaskRun",
            resource_id=str(task_run_id),
        )

    await db.delete(task_run)
    await db.commit()

    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{task_run_id}/logs")
async def get_task_run_logs(
    task_run_id: UUID,
    # Pagination
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(100, ge=1, le=1000, description="Items per page"),
    # Filtering
    level: Optional[str] = Query(
        None, description="Filter by log level (DEBUG, INFO, WARNING, ERROR)"
    ),
    db: AsyncSession = Depends(get_async_database),
    api_key: ApiKey = Depends(RequireRead),
) -> dict:
    """Get task run logs with pagination and filtering.

    **Path Parameters:**
    - task_run_id: UUID - Task run identifier

    **Query Parameters:**
    - page: int - Page number (default: 1)
    - page_size: int - Items per page (default: 100, max: 1000)
    - level: string - Filter by log level (DEBUG, INFO, WARNING, ERROR)

    **Returns:**
    - Paginated list of log entries

    **Errors:**
    - 404 Not Found: Task run doesn't exist
    - 403 Forbidden: API key scope restricted

    **Authentication:**
    - Requires: API key with 'read', 'write', or 'admin' scope

    **Note:**
    - For real-time log streaming, use GET /task-runs/:id/logs/stream (SSE)
    """
    # Verify task run exists
    task_run_query = select(TaskRun).where(TaskRun.id == task_run_id)
    task_run_result = await db.execute(task_run_query)
    task_run = task_run_result.scalar_one_or_none()

    if not task_run:
        raise ResourceNotFoundError(
            resource_type="TaskRun",
            resource_id=str(task_run_id),
        )

    # Check API key scope
    if api_key.project_id and api_key.project_id != task_run.project_id:
        raise InsufficientPermissionsError(
            detail=f"API key is scoped to project {api_key.project_id}, "
            f"cannot access logs for project {task_run.project_id}"
        )

    # Build base filter condition
    conditions = [TaskRunLog.task_run_id == task_run_id]

    # Apply optional level filter (case-insensitive)
    if level:
        conditions.append(func.lower(TaskRunLog.level) == level.lower())

    # Get total count
    count_query = select(func.count()).select_from(TaskRunLog).where(*conditions)
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Calculate pagination
    offset = (page - 1) * page_size
    total_pages = (total + page_size - 1) // page_size if total > 0 else 0

    # Query logs with pagination, sorted oldest first
    query = (
        select(TaskRunLog)
        .where(*conditions)
        .order_by(TaskRunLog.created_at.asc())
        .offset(offset)
        .limit(page_size)
    )
    result = await db.execute(query)
    logs = result.scalars().all()

    return {
        "items": [log.to_dict() for log in logs],
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": total_pages,
    }


@router.get("/{task_run_id}/logs/stream")
async def stream_task_run_logs(
    task_run_id: UUID,
    level: Optional[str] = Query(
        None, description="Filter by log level (DEBUG, INFO, WARNING, ERROR)"
    ),
    search: Optional[str] = Query(
        None, description="Filter logs containing this text (case-insensitive)"
    ),
    since: Optional[datetime] = Query(
        None, description="Only show logs after this timestamp (ISO 8601 format)"
    ),
    db: AsyncSession = Depends(get_async_database),
    api_key: ApiKey = Depends(RequireRead),
):
    """Stream task run logs in real-time using Server-Sent Events (SSE).

    **Path Parameters:**
    - task_run_id: UUID - Task run identifier

    **Query Parameters:**
    - level: string - Filter by minimum log level (DEBUG < INFO < WARNING < ERROR)
    - search: string - Filter logs containing this text (case-insensitive)
    - since: datetime - Only show logs after this timestamp (ISO 8601 format)

    **Response Format (SSE):**
    ```
    event: log
    data: {"timestamp": "2025-01-02T10:30:00Z", "level": "INFO", "message": "...", "metadata": {...}}

    event: status
    data: {"status": "running", "progress": 50}

    event: error
    data: {"error": "Connection lost"}

    event: end
    data: {"message": "Task completed"}
    ```

    **Connection:**
    - Uses Server-Sent Events (text/event-stream)
    - Client reconnection handled via Last-Event-ID
    - Idle timeout: 30 seconds (keepalive pings)
    - Graceful disconnection on task completion

    **Errors:**
    - 404 Not Found: Task run doesn't exist
    - 403 Forbidden: API key scope restricted

    **Authentication:**
    - Requires: API key with 'read', 'write', or 'admin' scope

    **Usage Example (JavaScript):**
    ```javascript
    const eventSource = new EventSource('/api/task-runs/{id}/logs/stream?level=INFO');

    eventSource.addEventListener('log', (event) => {
        const logEntry = JSON.parse(event.data);
        console.log(logEntry.message);
    });

    eventSource.addEventListener('end', () => {
        eventSource.close();
    });
    ```
    """
    # Verify task run exists
    task_run_query = select(TaskRun).where(TaskRun.id == task_run_id)
    task_run_result = await db.execute(task_run_query)
    task_run = task_run_result.scalar_one_or_none()

    if not task_run:
        raise ResourceNotFoundError(
            resource_type="TaskRun",
            resource_id=str(task_run_id),
        )

    # Check API key scope
    if api_key.project_id and api_key.project_id != task_run.project_id:
        raise InsufficientPermissionsError(
            detail=f"API key is scoped to project {api_key.project_id}, "
            f"cannot access logs for project {task_run.project_id}"
        )

    # Define log level hierarchy
    LOG_LEVELS = {"DEBUG": 10, "INFO": 20, "WARNING": 30, "ERROR": 40, "CRITICAL": 50}
    min_level = LOG_LEVELS.get(level.upper(), 10) if level else 10

    def should_include_log(log_entry: dict) -> bool:
        """Check if log entry passes all filters."""
        # Filter by log level
        entry_level = LOG_LEVELS.get(log_entry.get("level", "INFO"), 20)
        if entry_level < min_level:
            return False

        # Filter by search text (case-insensitive)
        if search:
            message = log_entry.get("message", "").lower()
            if search.lower() not in message:
                return False

        # Filter by timestamp
        if since:
            timestamp_str = log_entry.get("timestamp")
            if timestamp_str:
                try:
                    from dateutil.parser import parse as parse_datetime

                    log_timestamp = parse_datetime(timestamp_str)
                    # Make both timezone-aware for comparison
                    if log_timestamp.tzinfo is None:
                        log_timestamp = log_timestamp.replace(tzinfo=timezone.utc)
                    if since.tzinfo is None:
                        since_aware = since.replace(tzinfo=timezone.utc)
                    else:
                        since_aware = since
                    if log_timestamp < since_aware:
                        return False
                except Exception:
                    # If timestamp parsing fails, include the log
                    pass

        return True

    async def event_generator():
        """Generate SSE events from Redis Pub/Sub and log history."""
        redis_client = await get_async_redis()
        publisher = LogPublisher(use_async=True)

        try:
            # Determine channel based on task run
            channel = f"lazy_bird:logs:task:{task_run_id}"

            # Send initial log history
            history = await publisher.get_log_history_async(task_id=str(task_run_id), limit=100)
            for log_entry in reversed(history):  # Send oldest first
                # Apply all filters
                if should_include_log(log_entry):
                    yield f"event: log\ndata: {json.dumps(log_entry)}\n\n"

            # Send status event
            yield f'event: status\ndata: {{"status": "{task_run.status}"}}\n\n'

            # Subscribe to Redis Pub/Sub for real-time logs
            pubsub = redis_client.pubsub()
            await pubsub.subscribe(channel)

            logger.info(
                f"Started SSE stream for task run: {task_run.work_item_id}",
                extra={
                    "extra_fields": {
                        "task_run_id": str(task_run_id),
                        "channel": channel,
                        "min_level": level or "DEBUG",
                    }
                },
            )

            # Stream real-time logs
            last_keepalive = asyncio.get_event_loop().time()
            keepalive_interval = 30  # seconds

            while True:
                try:
                    # Check for new messages with timeout
                    message = await asyncio.wait_for(
                        pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0),
                        timeout=2.0,
                    )

                    if message and message["type"] == "message":
                        # Parse log entry
                        log_entry = json.loads(message["data"])

                        # Apply all filters
                        if should_include_log(log_entry):
                            yield f"event: log\ndata: {json.dumps(log_entry)}\n\n"

                        # Check if task is complete
                        if log_entry.get("metadata", {}).get("task_complete"):
                            yield f'event: end\ndata: {{"message": "Task completed"}}\n\n'
                            break

                    # Send keepalive ping if needed
                    current_time = asyncio.get_event_loop().time()
                    if current_time - last_keepalive > keepalive_interval:
                        yield f": keepalive\n\n"
                        last_keepalive = current_time

                except asyncio.TimeoutError:
                    # No message received, send keepalive
                    yield f": keepalive\n\n"
                    last_keepalive = asyncio.get_event_loop().time()
                    continue

                except Exception as e:
                    logger.error(
                        f"Error in SSE stream: {str(e)}",
                        extra={
                            "extra_fields": {
                                "task_run_id": str(task_run_id),
                                "error": str(e),
                            }
                        },
                    )
                    yield f'event: error\ndata: {{"error": "{str(e)}"}}\n\n'
                    break

        except Exception as e:
            logger.error(
                f"Fatal error in SSE stream: {str(e)}",
                extra={
                    "extra_fields": {
                        "task_run_id": str(task_run_id),
                        "error": str(e),
                    }
                },
                exc_info=True,
            )
            yield f'event: error\ndata: {{"error": "Stream terminated: {str(e)}"}}\n\n'

        finally:
            # Cleanup
            try:
                await pubsub.unsubscribe(channel)
                await pubsub.close()
            except Exception:
                pass

            logger.info(
                f"Closed SSE stream for task run: {task_run.work_item_id}",
                extra={
                    "extra_fields": {
                        "task_run_id": str(task_run_id),
                    }
                },
            )

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        },
    )
