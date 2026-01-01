"""FrameworkPresets API endpoints for managing framework configurations.

This module provides CRUD operations for framework presets with:
- Built-in presets (Godot, Django, React, etc.)
- Custom user-defined presets
- Test/build/lint/format command configuration
- Framework-specific metadata
"""

from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from lazy_bird.api.dependencies import RequireAdmin, RequireRead, get_async_database
from lazy_bird.api.exceptions import ResourceConflictError, ResourceNotFoundError
from lazy_bird.core.logging import get_logger
from lazy_bird.models.api_key import ApiKey
from lazy_bird.models.framework_preset import FrameworkPreset
from lazy_bird.schemas.framework_preset import (
    FrameworkPresetCreate,
    FrameworkPresetListResponse,
    FrameworkPresetResponse,
    FrameworkPresetUpdate,
)

logger = get_logger(__name__)

# Create router
router = APIRouter(prefix="/framework-presets", tags=["framework-presets"])


@router.get("", response_model=FrameworkPresetListResponse)
@router.get("/", response_model=FrameworkPresetListResponse)
async def list_framework_presets(
    # Pagination
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    # Filtering
    framework_type: Optional[str] = Query(
        None, description="Filter by framework type (game_engine, backend, frontend, language)"
    ),
    language: Optional[str] = Query(
        None, description="Filter by programming language"
    ),
    is_builtin: Optional[bool] = Query(
        None, description="Filter by built-in status (true for built-in, false for custom)"
    ),
    # Dependencies
    db: AsyncSession = Depends(get_async_database),
    api_key: ApiKey = Depends(RequireRead),
) -> FrameworkPresetListResponse:
    """List all framework presets with pagination and filtering.

    **Pagination:**
    - Offset-based pagination with page and page_size
    - Default: page=1, page_size=20
    - Max page_size: 100

    **Filtering:**
    - `framework_type`: string - Filter by type (game_engine, backend, frontend, language)
    - `language`: string - Filter by programming language
    - `is_builtin`: boolean - Filter by built-in vs custom presets

    **Returns:**
    - List of framework presets
    - Total count, page info, pagination metadata

    **Authentication:**
    - Requires: API key with 'read', 'write', or 'admin' scope

    **Built-in Presets:**
    - Godot, Unity, Unreal, Bevy (game engines)
    - Django, Flask, FastAPI, Express, Rails (backend)
    - React, Vue, Angular, Svelte (frontend)
    - Python, Rust, Node.js, Go (languages)
    """
    # Build base query
    query = select(FrameworkPreset)

    # Apply filters
    filters = []

    # Filter by framework type
    if framework_type:
        filters.append(FrameworkPreset.framework_type == framework_type)

    # Filter by language
    if language:
        filters.append(FrameworkPreset.language == language)

    # Filter by built-in status
    if is_builtin is not None:
        filters.append(FrameworkPreset.is_builtin == is_builtin)

    # Add all filters to query
    if filters:
        query = query.where(*filters)

    # Get total count
    count_query = select(func.count()).select_from(FrameworkPreset)
    if filters:
        count_query = count_query.where(*filters)
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Calculate pagination
    offset = (page - 1) * page_size
    pages = (total + page_size - 1) // page_size if total > 0 else 0

    # Apply pagination and sorting (built-in first, then by name)
    query = (
        query.order_by(FrameworkPreset.is_builtin.desc(), FrameworkPreset.name.asc())
        .offset(offset)
        .limit(page_size)
    )

    # Execute query
    result = await db.execute(query)
    presets = result.scalars().all()

    # Convert to response models
    preset_responses = [FrameworkPresetResponse.model_validate(p) for p in presets]

    # Log successful query
    logger.info(
        f"Listed {len(presets)} framework presets (page {page}/{pages})",
        extra={
            "extra_fields": {
                "total": total,
                "page": page,
                "page_size": page_size,
                "filters": {
                    "framework_type": framework_type,
                    "language": language,
                    "is_builtin": is_builtin,
                },
            }
        },
    )

    return FrameworkPresetListResponse(
        items=preset_responses,
        total=total,
        page=page,
        page_size=page_size,
        pages=pages,
    )


@router.post("", response_model=FrameworkPresetResponse, status_code=status.HTTP_201_CREATED)
@router.post("/", response_model=FrameworkPresetResponse, status_code=status.HTTP_201_CREATED)
async def create_framework_preset(
    preset_data: FrameworkPresetCreate,
    db: AsyncSession = Depends(get_async_database),
    api_key: ApiKey = Depends(RequireAdmin),
) -> FrameworkPresetResponse:
    """Create a new custom framework preset.

    **Required Fields:**
    - name: Internal name (lowercase, alphanumeric, hyphens)
    - display_name: Human-readable name
    - framework_type: Framework category
    - test_command: Command to run tests

    **Optional Fields:**
    - description: Preset description
    - language: Programming language
    - build_command: Build command
    - lint_command: Lint command
    - format_command: Format command
    - config_files: Framework-specific config file paths (JSON)

    **Validation:**
    - Name must be unique
    - Name format: lowercase, alphanumeric, hyphens only

    **Returns:**
    - 201 Created: Preset created successfully
    - 409 Conflict: Name already exists
    - 422 Validation Error: Invalid input data

    **Authentication:**
    - Requires: API key with 'admin' scope

    **Note:**
    - Custom presets have is_builtin=false
    - Built-in presets can only be created via database seeding
    """
    # Check name uniqueness
    name_query = select(FrameworkPreset).where(FrameworkPreset.name == preset_data.name)
    name_result = await db.execute(name_query)
    existing_preset = name_result.scalar_one_or_none()

    if existing_preset:
        raise ResourceConflictError(
            detail=f"Framework preset with name '{preset_data.name}' already exists",
            conflict_field="name",
        )

    # Create preset (custom presets have is_builtin=False)
    preset = FrameworkPreset(
        name=preset_data.name,
        display_name=preset_data.display_name,
        description=preset_data.description,
        framework_type=preset_data.framework_type,
        language=preset_data.language,
        test_command=preset_data.test_command,
        build_command=preset_data.build_command,
        lint_command=preset_data.lint_command,
        format_command=preset_data.format_command,
        config_files=preset_data.config_files or {},
        is_builtin=False,  # Custom presets are never built-in
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )

    db.add(preset)
    await db.commit()
    await db.refresh(preset)

    # Log successful creation
    logger.info(
        f"Created framework preset: {preset.display_name} ({preset.name})",
        extra={
            "extra_fields": {
                "preset_id": str(preset.id),
                "name": preset.name,
                "framework_type": preset.framework_type,
            }
        },
    )

    return FrameworkPresetResponse.model_validate(preset)


@router.get("/{preset_id}", response_model=FrameworkPresetResponse)
async def get_framework_preset(
    preset_id: UUID,
    db: AsyncSession = Depends(get_async_database),
    api_key: ApiKey = Depends(RequireRead),
) -> FrameworkPresetResponse:
    """Get a single framework preset by ID.

    **Path Parameters:**
    - preset_id: UUID - Preset identifier

    **Returns:**
    - Preset details with all configuration

    **Errors:**
    - 404 Not Found: Preset doesn't exist

    **Authentication:**
    - Requires: API key with 'read', 'write', or 'admin' scope
    """
    # Fetch preset
    query = select(FrameworkPreset).where(FrameworkPreset.id == preset_id)
    result = await db.execute(query)
    preset = result.scalar_one_or_none()

    # Check if preset exists
    if not preset:
        raise ResourceNotFoundError(
            resource_type="FrameworkPreset",
            resource_id=str(preset_id),
        )

    # Log successful query
    logger.info(
        f"Retrieved framework preset: {preset.display_name}",
        extra={
            "extra_fields": {
                "preset_id": str(preset.id),
                "name": preset.name,
            }
        },
    )

    return FrameworkPresetResponse.model_validate(preset)


@router.patch("/{preset_id}", response_model=FrameworkPresetResponse)
async def update_framework_preset(
    preset_id: UUID,
    update_data: FrameworkPresetUpdate,
    db: AsyncSession = Depends(get_async_database),
    api_key: ApiKey = Depends(RequireAdmin),
) -> FrameworkPresetResponse:
    """Update an existing framework preset (partial update).

    **Path Parameters:**
    - preset_id: UUID - Preset identifier

    **Request Body (all optional):**
    - display_name: Human-readable name
    - description: Preset description
    - framework_type: Framework category
    - language: Programming language
    - test_command: Test command
    - build_command: Build command
    - lint_command: Lint command
    - format_command: Format command
    - config_files: Config file paths

    **Returns:**
    - Updated preset

    **Errors:**
    - 404 Not Found: Preset doesn't exist
    - 409 Conflict: Cannot update built-in preset
    - 422 Validation Error: Invalid field values

    **Authentication:**
    - Requires: API key with 'admin' scope

    **Note:**
    - Built-in presets cannot be updated (protection against accidental modification)
    - Name field cannot be changed after creation
    """
    # Fetch existing preset
    query = select(FrameworkPreset).where(FrameworkPreset.id == preset_id)
    result = await db.execute(query)
    preset = result.scalar_one_or_none()

    # Check if preset exists
    if not preset:
        raise ResourceNotFoundError(
            resource_type="FrameworkPreset",
            resource_id=str(preset_id),
        )

    # Check if built-in (cannot update built-in presets)
    if preset.is_builtin:
        raise ResourceConflictError(
            detail=f"Cannot update built-in preset '{preset.name}'. "
            "Create a custom preset instead.",
            conflict_field="is_builtin",
        )

    # Get update data (only fields that were provided)
    update_fields = update_data.model_dump(exclude_unset=True)

    # If no fields to update, return existing preset
    if not update_fields:
        logger.info(f"No fields to update for framework preset: {preset.name}")
        return FrameworkPresetResponse.model_validate(preset)

    # Apply updates
    for field, value in update_fields.items():
        setattr(preset, field, value)

    # Update timestamp
    preset.updated_at = datetime.now(timezone.utc)

    # Commit changes
    await db.commit()
    await db.refresh(preset)

    # Log successful update
    logger.info(
        f"Updated framework preset: {preset.display_name}",
        extra={
            "extra_fields": {
                "preset_id": str(preset.id),
                "updated_fields": list(update_fields.keys()),
            }
        },
    )

    return FrameworkPresetResponse.model_validate(preset)


@router.delete("/{preset_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_framework_preset(
    preset_id: UUID,
    db: AsyncSession = Depends(get_async_database),
    api_key: ApiKey = Depends(RequireAdmin),
) -> Response:
    """Delete a custom framework preset.

    **Path Parameters:**
    - preset_id: UUID - Preset identifier

    **Behavior:**
    - Hard delete (permanently removes record)
    - Cascade effects:
      - Projects using this preset: framework_preset_id set to NULL

    **Returns:**
    - 204 No Content: Preset deleted successfully

    **Errors:**
    - 404 Not Found: Preset doesn't exist
    - 409 Conflict: Cannot delete built-in preset

    **Authentication:**
    - Requires: API key with 'admin' scope

    **Warning:**
    - Built-in presets cannot be deleted (protection)
    - Projects will lose preset association
    """
    # Fetch existing preset
    query = select(FrameworkPreset).where(FrameworkPreset.id == preset_id)
    result = await db.execute(query)
    preset = result.scalar_one_or_none()

    # Check if preset exists
    if not preset:
        raise ResourceNotFoundError(
            resource_type="FrameworkPreset",
            resource_id=str(preset_id),
        )

    # Check if built-in (cannot delete built-in presets)
    if preset.is_builtin:
        raise ResourceConflictError(
            detail=f"Cannot delete built-in preset '{preset.name}'. "
            "Built-in presets are protected.",
            conflict_field="is_builtin",
        )

    # Delete the preset (cascade handled by database)
    await db.delete(preset)
    await db.commit()

    # Log deletion
    logger.info(
        f"Deleted framework preset: {preset.display_name}",
        extra={
            "extra_fields": {
                "preset_id": str(preset_id),
                "name": preset.name,
            }
        },
    )

    # Return 204 No Content (no response body)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
