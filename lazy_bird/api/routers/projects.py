"""Projects API endpoints for managing development projects.

This module provides CRUD operations for projects with:
- List with cursor-based pagination
- Filtering by automation status and project type
- Full-text search
- Project statistics
"""

from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from lazy_bird.api.dependencies import RequireRead, RequireWrite, get_async_database
from lazy_bird.api.exceptions import ResourceConflictError, ResourceNotFoundError
from lazy_bird.core.logging import get_logger
from lazy_bird.models.api_key import ApiKey
from lazy_bird.models.project import Project
from lazy_bird.models.task_run import TaskRun
from lazy_bird.schemas.project import (
    ProjectCreate,
    ProjectListResponse,
    ProjectResponse,
    ProjectUpdate,
)

logger = get_logger(__name__)

# Create router
router = APIRouter(prefix="/projects", tags=["projects"])


@router.get("", response_model=ProjectListResponse)
@router.get("/", response_model=ProjectListResponse)
async def list_projects(
    # Pagination
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    # Filtering
    automation_enabled: Optional[bool] = Query(None, description="Filter by automation status"),
    project_type: Optional[str] = Query(
        None, description="Filter by project type (e.g., 'python', 'godot')"
    ),
    include_deleted: Optional[bool] = Query(
        False, description="Include soft-deleted projects (default: false)"
    ),
    # Search
    search: Optional[str] = Query(
        None, min_length=2, description="Search in name, description, repository"
    ),
    # Dependencies
    db: AsyncSession = Depends(get_async_database),
    api_key: ApiKey = Depends(RequireRead),
) -> ProjectListResponse:
    """List all projects with pagination, filtering, and search.

    **Pagination:**
    - Offset-based pagination with page and page_size
    - Default: page=1, page_size=20
    - Max page_size: 100

    **Filtering:**
    - `automation_enabled`: true/false - Filter by automation status
    - `project_type`: string - Filter by project type
    - `include_deleted`: true/false - Include soft-deleted projects (default: false)

    **Search:**
    - `search`: string (min 2 chars) - Full-text search across name, description, repository

    **Returns:**
    - List of projects with statistics
    - Total count, page info, pagination metadata

    **Authentication:**
    - Requires: API key with 'read', 'write', or 'admin' scope
    """
    # Build base query
    query = select(Project)

    # Apply filters
    filters = []

    # Filter by API key's project scope (if project-specific key)
    if api_key.project_id:
        filters.append(Project.id == api_key.project_id)

    # Filter by automation status
    if automation_enabled is not None:
        filters.append(Project.automation_enabled == automation_enabled)

    # Filter by project type
    if project_type:
        filters.append(Project.project_type == project_type)

    # Filter by deleted status (default: exclude deleted)
    if not include_deleted:
        filters.append(Project.deleted_at.is_(None))

    # Apply search (full-text search or simple LIKE)
    if search:
        # Simple LIKE search on name and repo_url
        search_filters = [
            Project.name.ilike(f"%{search}%"),
            Project.repo_url.ilike(f"%{search}%"),
            Project.slug.ilike(f"%{search}%"),
        ]
        filters.append(or_(*search_filters))

    # Add all filters to query
    if filters:
        query = query.where(*filters)

    # Get total count
    count_query = select(func.count()).select_from(Project)
    if filters:
        count_query = count_query.where(*filters)
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Calculate pagination
    offset = (page - 1) * page_size
    pages = (total + page_size - 1) // page_size if total > 0 else 0

    # Apply pagination and sorting
    query = (
        query.order_by(Project.created_at.desc())
        .offset(offset)
        .limit(page_size)
        .options(
            selectinload(Project.framework_preset),
            selectinload(Project.task_runs),
        )
    )

    # Execute query
    result = await db.execute(query)
    projects = result.scalars().all()

    # Enrich projects with statistics
    project_responses = []
    for project in projects:
        # Get task run statistics
        stats_query = (
            select(
                TaskRun.status,
                func.count(TaskRun.id).label("count"),
            )
            .where(TaskRun.project_id == project.id)
            .group_by(TaskRun.status)
        )
        stats_result = await db.execute(stats_query)
        stats = {row.status: row.count for row in stats_result}

        # Calculate total tasks
        total_tasks = sum(stats.values())

        # Get last task run
        last_task_query = (
            select(TaskRun.created_at)
            .where(TaskRun.project_id == project.id)
            .order_by(TaskRun.created_at.desc())
            .limit(1)
        )
        last_task_result = await db.execute(last_task_query)
        last_task_at = last_task_result.scalar_one_or_none()

        # Create response with stats using model_validate to handle ORM attrs
        project_response = ProjectResponse.model_validate(project)
        project_response.total_tasks = total_tasks
        project_response.tasks_queued = stats.get("queued", 0)
        project_response.tasks_running = stats.get("running", 0)
        project_response.tasks_success = stats.get("success", 0)
        project_response.tasks_failed = stats.get("failed", 0)
        project_response.last_task_at = last_task_at
        project_responses.append(project_response)

    # Log successful query
    logger.info(
        f"Listed {len(projects)} projects (page {page}/{pages})",
        extra={
            "extra_fields": {
                "total": total,
                "page": page,
                "page_size": page_size,
                "filters": {
                    "automation_enabled": automation_enabled,
                    "project_type": project_type,
                    "search": search,
                },
            }
        },
    )

    return ProjectListResponse(
        items=project_responses,
        total=total,
        page=page,
        page_size=page_size,
        pages=pages,
    )


@router.post("", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
@router.post("/", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_project(
    project_data: ProjectCreate,
    db: AsyncSession = Depends(get_async_database),
    api_key: ApiKey = Depends(RequireWrite),
) -> ProjectResponse:
    """Create a new project.

    **Required Fields:**
    - name: Human-readable project name
    - slug: URL-safe unique identifier (lowercase, alphanumeric, hyphens)
    - repo_url: Git repository URL
    - project_type: Project type (python, godot, etc.)

    **Optional Fields:**
    - framework_preset_id: Reference to framework preset
    - test_command, build_command, lint_command, format_command: Custom commands
    - automation_enabled: Enable automation (default: false)
    - max_concurrent_tasks: Max parallel tasks (default: 3)
    - task_timeout_seconds: Timeout in seconds (default: 1800)
    - max_cost_per_task_usd: Cost limit per task (default: 5.00)
    - daily_cost_limit_usd: Daily cost limit (default: 50.00)
    - claude_account_id: Reference to Claude account

    **Validation:**
    - Slug must be unique across all projects
    - Slug format: lowercase, alphanumeric, hyphens only
    - Framework preset ID must exist (if provided)
    - Claude account ID must exist (if provided)

    **Returns:**
    - 201 Created: Project created successfully
    - 409 Conflict: Slug already exists
    - 422 Validation Error: Invalid input data

    **Authentication:**
    - Requires: API key with 'write' or 'admin' scope
    """
    # Check slug uniqueness
    slug_query = select(Project).where(Project.slug == project_data.slug)
    slug_result = await db.execute(slug_query)
    existing_project = slug_result.scalar_one_or_none()

    if existing_project:
        raise ResourceConflictError(
            detail=f"Project with slug '{project_data.slug}' already exists",
            conflict_field="slug",
        )

    # Validate framework preset exists (if provided)
    if project_data.framework_preset_id:
        from lazy_bird.models.framework_preset import FrameworkPreset

        preset_query = select(FrameworkPreset).where(
            FrameworkPreset.id == project_data.framework_preset_id
        )
        preset_result = await db.execute(preset_query)
        preset = preset_result.scalar_one_or_none()

        if not preset:
            raise ResourceNotFoundError(
                resource_type="FrameworkPreset",
                resource_id=str(project_data.framework_preset_id),
            )

    # Validate Claude account exists (if provided)
    if project_data.claude_account_id:
        from lazy_bird.models.claude_account import ClaudeAccount

        account_query = select(ClaudeAccount).where(
            ClaudeAccount.id == project_data.claude_account_id
        )
        account_result = await db.execute(account_query)
        account = account_result.scalar_one_or_none()

        if not account:
            raise ResourceNotFoundError(
                resource_type="ClaudeAccount",
                resource_id=str(project_data.claude_account_id),
            )

    # Create project
    project = Project(
        name=project_data.name,
        slug=project_data.slug,
        repo_url=project_data.repo_url,
        default_branch=project_data.default_branch,
        project_type=project_data.project_type,
        # Framework preset
        framework_preset_id=project_data.framework_preset_id,
        # Commands
        test_command=project_data.test_command,
        build_command=project_data.build_command,
        lint_command=project_data.lint_command,
        format_command=project_data.format_command,
        # Automation settings
        automation_enabled=project_data.automation_enabled,
        ready_state_name=project_data.ready_state_name,
        in_progress_state_name=project_data.in_progress_state_name,
        review_state_name=project_data.review_state_name,
        done_state_name=project_data.done_state_name,
        # Resource limits
        max_concurrent_tasks=project_data.max_concurrent_tasks,
        task_timeout_seconds=project_data.task_timeout_seconds,
        max_cost_per_task_usd=project_data.max_cost_per_task_usd,
        daily_cost_limit_usd=project_data.daily_cost_limit_usd,
        # Integration settings
        github_installation_id=project_data.github_installation_id,
        gitlab_project_id=project_data.gitlab_project_id,
        source_platform=project_data.source_platform,
        source_platform_url=project_data.source_platform_url,
        # Claude account
        claude_account_id=project_data.claude_account_id,
    )

    db.add(project)
    await db.commit()
    await db.refresh(project)

    # Log successful creation
    logger.info(
        f"Created project: {project.name} ({project.slug})",
        extra={
            "extra_fields": {
                "project_id": str(project.id),
                "slug": project.slug,
                "project_type": project.project_type,
                "automation_enabled": project.automation_enabled,
            }
        },
    )

    # Return response without stats (stats are empty for new project)
    return ProjectResponse.model_validate(project)


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: UUID,
    db: AsyncSession = Depends(get_async_database),
    api_key: ApiKey = Depends(RequireRead),
) -> ProjectResponse:
    """Get a single project by ID with full details and statistics.

    **Path Parameters:**
    - project_id: UUID - Unique project identifier

    **Returns:**
    - Project details with:
      - All project fields
      - Related entities (framework preset, Claude account)
      - Task statistics (queued, running, success, failed)
      - Last task timestamp

    **Errors:**
    - 404 Not Found: Project does not exist or is soft-deleted
    - 403 Forbidden: API key scope restricted to different project

    **Authentication:**
    - Requires: API key with 'read', 'write', or 'admin' scope
    """
    # Build query with eager loading
    query = (
        select(Project)
        .where(Project.id == project_id)
        .where(Project.deleted_at.is_(None))  # Exclude soft-deleted
        .options(
            selectinload(Project.framework_preset),
            selectinload(Project.task_runs),
        )
    )

    # Execute query
    result = await db.execute(query)
    project = result.scalar_one_or_none()

    # Check if project exists
    if not project:
        raise ResourceNotFoundError(
            resource_type="Project",
            resource_id=str(project_id),
        )

    # Check API key scope (if project-specific key)
    if api_key.project_id and api_key.project_id != project.id:
        raise InsufficientPermissionsError(
            detail=f"API key is scoped to project {api_key.project_id}, cannot access project {project.id}"
        )

    # Get task run statistics
    stats_query = (
        select(
            TaskRun.status,
            func.count(TaskRun.id).label("count"),
        )
        .where(TaskRun.project_id == project.id)
        .group_by(TaskRun.status)
    )
    stats_result = await db.execute(stats_query)
    stats = {row.status: row.count for row in stats_result}

    # Calculate total tasks
    total_tasks = sum(stats.values())

    # Get last task run
    last_task_query = (
        select(TaskRun.created_at)
        .where(TaskRun.project_id == project.id)
        .order_by(TaskRun.created_at.desc())
        .limit(1)
    )
    last_task_result = await db.execute(last_task_query)
    last_task_at = last_task_result.scalar_one_or_none()

    # Create response with stats using model_validate to handle ORM attrs
    project_response = ProjectResponse.model_validate(project)
    project_response.total_tasks = total_tasks
    project_response.tasks_queued = stats.get("queued", 0)
    project_response.tasks_running = stats.get("running", 0)
    project_response.tasks_success = stats.get("success", 0)
    project_response.tasks_failed = stats.get("failed", 0)
    project_response.last_task_at = last_task_at

    # Log successful query
    logger.info(
        f"Retrieved project: {project.name} ({project.slug})",
        extra={
            "extra_fields": {
                "project_id": str(project.id),
                "slug": project.slug,
                "total_tasks": total_tasks,
            }
        },
    )

    return project_response


@router.patch("/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: UUID,
    update_data: ProjectUpdate,
    db: AsyncSession = Depends(get_async_database),
    api_key: ApiKey = Depends(RequireWrite),
) -> ProjectResponse:
    """Update an existing project (partial update).

    **Path Parameters:**
    - project_id: UUID - Project identifier

    **Request Body:**
    - All fields optional (partial update)
    - Only provided fields will be updated
    - See ProjectUpdate schema for available fields

    **Validation:**
    - Slug uniqueness (if slug is changed)
    - Framework preset existence (if framework_preset_id is changed)
    - Claude account existence (if claude_account_id is changed)

    **Returns:**
    - Updated project with full details and statistics

    **Errors:**
    - 404 Not Found: Project doesn't exist or is soft-deleted
    - 409 Conflict: Slug already exists
    - 422 Validation Error: Invalid field values
    - 403 Forbidden: API key scope restricted to different project

    **Authentication:**
    - Requires: API key with 'write' or 'admin' scope
    """
    # Fetch existing project
    query = select(Project).where(Project.id == project_id).where(Project.deleted_at.is_(None))
    result = await db.execute(query)
    project = result.scalar_one_or_none()

    # Check if project exists
    if not project:
        raise ResourceNotFoundError(
            resource_type="Project",
            resource_id=str(project_id),
        )

    # Check API key scope (if project-specific key)
    if api_key.project_id and api_key.project_id != project.id:
        raise InsufficientPermissionsError(
            detail=f"API key is scoped to project {api_key.project_id}, cannot update project {project.id}"
        )

    # Get update data (only fields that were provided)
    update_fields = update_data.model_dump(exclude_unset=True)

    # If no fields to update, return existing project
    if not update_fields:
        logger.info(
            f"No fields to update for project: {project.name} ({project.slug})",
            extra={"extra_fields": {"project_id": str(project.id)}},
        )
        return ProjectResponse.model_validate(project)

    # Validate slug uniqueness (if slug is being changed)
    if "slug" in update_fields and update_fields["slug"] != project.slug:
        slug_query = select(Project).where(Project.slug == update_fields["slug"])
        slug_result = await db.execute(slug_query)
        existing_project = slug_result.scalar_one_or_none()

        if existing_project:
            raise ResourceConflictError(
                detail=f"Project with slug '{update_fields['slug']}' already exists",
                conflict_field="slug",
            )

    # Validate framework preset exists (if being changed)
    if "framework_preset_id" in update_fields and update_fields["framework_preset_id"]:
        from lazy_bird.models.framework_preset import FrameworkPreset

        preset_query = select(FrameworkPreset).where(
            FrameworkPreset.id == update_fields["framework_preset_id"]
        )
        preset_result = await db.execute(preset_query)
        preset = preset_result.scalar_one_or_none()

        if not preset:
            raise ResourceNotFoundError(
                resource_type="FrameworkPreset",
                resource_id=str(update_fields["framework_preset_id"]),
            )

    # Validate Claude account exists (if being changed)
    if "claude_account_id" in update_fields and update_fields["claude_account_id"]:
        from lazy_bird.models.claude_account import ClaudeAccount

        account_query = select(ClaudeAccount).where(
            ClaudeAccount.id == update_fields["claude_account_id"]
        )
        account_result = await db.execute(account_query)
        account = account_result.scalar_one_or_none()

        if not account:
            raise ResourceNotFoundError(
                resource_type="ClaudeAccount",
                resource_id=str(update_fields["claude_account_id"]),
            )

    # Apply updates to project
    for field, value in update_fields.items():
        setattr(project, field, value)

    # Commit changes
    await db.commit()
    await db.refresh(project)

    # Log successful update
    logger.info(
        f"Updated project: {project.name} ({project.slug})",
        extra={
            "extra_fields": {
                "project_id": str(project.id),
                "slug": project.slug,
                "updated_fields": list(update_fields.keys()),
            }
        },
    )

    # Return updated project without stats (detail view)
    return ProjectResponse.model_validate(project)


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(
    project_id: UUID,
    db: AsyncSession = Depends(get_async_database),
    api_key: ApiKey = Depends(RequireWrite),
) -> Response:
    """Soft delete a project (sets deleted_at timestamp).

    **Path Parameters:**
    - project_id: UUID - Project identifier

    **Behavior:**
    - Sets \`deleted_at\` timestamp (soft delete)
    - Does not physically delete the record
    - Project will be excluded from list/get queries
    - Related records (task runs, webhooks) remain in database

    **Cascade Effects:**
    - Project becomes inaccessible via standard endpoints
    - Task runs remain in database (historical data preserved)
    - Webhooks remain in database (can be cleaned up separately)
    - API keys scoped to this project become ineffective

    **Returns:**
    - 204 No Content: Project deleted successfully (no response body)

    **Errors:**
    - 404 Not Found: Project doesn't exist or already deleted
    - 403 Forbidden: API key scope restricted to different project

    **Authentication:**
    - Requires: API key with 'write' or 'admin' scope

    **Note:**
    - This is a soft delete - data is preserved for recovery
    - To permanently delete, use database admin tools
    """
    # Fetch existing project
    query = (
        select(Project)
        .where(Project.id == project_id)
        .where(Project.deleted_at.is_(None))  # Only allow deleting active projects
    )
    result = await db.execute(query)
    project = result.scalar_one_or_none()

    # Check if project exists
    if not project:
        raise ResourceNotFoundError(
            resource_type="Project",
            resource_id=str(project_id),
        )

    # Check API key scope (if project-specific key)
    if api_key.project_id and api_key.project_id != project.id:
        raise InsufficientPermissionsError(
            detail=f"API key is scoped to project {api_key.project_id}, cannot delete project {project.id}"
        )

    # Set deleted_at timestamp (soft delete)
    project.deleted_at = datetime.now(timezone.utc)

    # Commit changes
    await db.commit()

    # Log successful deletion
    logger.info(
        f"Soft deleted project: {project.name} ({project.slug})",
        extra={
            "extra_fields": {
                "project_id": str(project.id),
                "slug": project.slug,
                "deleted_at": project.deleted_at.isoformat(),
            }
        },
    )

    # Return 204 No Content (no response body)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
