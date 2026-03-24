"""ApiKeys API endpoints for managing API authentication tokens.

This module provides CRUD operations for API keys with:
- Secure key generation (shown only once at creation)
- SHA-256 key hashing for storage
- Project-scoped or organization-level keys
- Scope-based permissions (read, write, admin)
- Key expiration and revocation
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
from lazy_bird.core.security import generate_api_key, get_api_key_prefix, hash_api_key
from lazy_bird.models.api_key import ApiKey
from lazy_bird.models.project import Project
from lazy_bird.schemas.api_key import (
    ApiKeyCreate,
    ApiKeyCreateResponse,
    ApiKeyListResponse,
    ApiKeyResponse,
    ApiKeyUpdate,
)

logger = get_logger(__name__)

# Create router
router = APIRouter(prefix="/api-keys", tags=["api-keys"])


@router.get("", response_model=ApiKeyListResponse)
@router.get("/", response_model=ApiKeyListResponse)
async def list_api_keys(
    # Pagination
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    # Filtering
    project_id: Optional[UUID] = Query(
        None, description="Filter by project ID (omit for organization-level keys)"
    ),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    scope: Optional[str] = Query(
        None, description="Filter by scope (read, write, admin)"
    ),
    # Dependencies
    db: AsyncSession = Depends(get_async_database),
    api_key: ApiKey = Depends(RequireRead),
) -> ApiKeyListResponse:
    """List all API keys with pagination and filtering.

    **Pagination:**
    - Offset-based pagination with page and page_size
    - Default: page=1, page_size=20
    - Max page_size: 100

    **Filtering:**
    - `project_id`: UUID - Filter by project (NULL for org-level keys)
    - `is_active`: boolean - Filter by active status
    - `scope`: string - Filter by scope (read, write, admin)

    **Returns:**
    - List of API keys (only key_prefix shown, not full key)
    - Total count, page info, pagination metadata

    **Authentication:**
    - Requires: API key with 'read', 'write', or 'admin' scope

    **Security:**
    - Full API keys are NEVER returned (only key_prefix)
    - Keys are shown in full ONLY once during creation
    """
    # Build base query
    query = select(ApiKey)

    # Apply filters
    filters = []

    # Filter by project ID
    if project_id is not None:
        filters.append(ApiKey.project_id == project_id)

    # Filter by active status
    if is_active is not None:
        filters.append(ApiKey.is_active == is_active)

    # Filter by scope (check if array contains the scope)
    if scope:
        filters.append(ApiKey.scopes.contains([scope]))

    # Add all filters to query
    if filters:
        query = query.where(*filters)

    # Get total count
    count_query = select(func.count()).select_from(ApiKey)
    if filters:
        count_query = count_query.where(*filters)
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Calculate pagination
    offset = (page - 1) * page_size
    pages = (total + page_size - 1) // page_size if total > 0 else 0

    # Apply pagination and sorting (most recent first)
    query = query.order_by(ApiKey.created_at.desc()).offset(offset).limit(page_size)

    # Execute query
    result = await db.execute(query)
    keys = result.scalars().all()

    # Convert to response models (key_prefix only, not full key!)
    key_responses = [ApiKeyResponse.model_validate(k) for k in keys]

    # Log successful query
    logger.info(
        f"Listed {len(keys)} API keys (page {page}/{pages})",
        extra={
            "extra_fields": {
                "total": total,
                "page": page,
                "page_size": page_size,
                "filters": {
                    "project_id": str(project_id) if project_id else None,
                    "is_active": is_active,
                    "scope": scope,
                },
            }
        },
    )

    return ApiKeyListResponse(
        items=key_responses,
        total=total,
        page=page,
        page_size=page_size,
        pages=pages,
    )


@router.post("", response_model=ApiKeyCreateResponse, status_code=status.HTTP_201_CREATED)
@router.post("/", response_model=ApiKeyCreateResponse, status_code=status.HTTP_201_CREATED)
async def create_api_key(
    key_data: ApiKeyCreate,
    db: AsyncSession = Depends(get_async_database),
    api_key: ApiKey = Depends(RequireAdmin),
) -> ApiKeyCreateResponse:
    """Create a new API key.

    **Required Fields:**
    - name: Human-readable key name

    **Optional Fields:**
    - project_id: Project ID (NULL for organization-level key)
    - scopes: Array of scopes (default: ["read"])
    - expires_at: Expiration timestamp (NULL for no expiration)

    **Valid Scopes:**
    - read: Read-only access
    - write: Read and write access (includes read)
    - admin: Full administrative access (includes read and write)

    **Returns:**
    - 201 Created: Key created successfully
    - **IMPORTANT:** Full key is returned ONLY ONCE - save it securely!
    - 404 Not Found: Project doesn't exist (if project_id provided)
    - 422 Validation Error: Invalid input data

    **Authentication:**
    - Requires: API key with 'admin' scope

    **Security:**
    - Key is hashed with SHA-256 before storage
    - Only key_prefix (first 8 chars) is stored in plain text
    - Full key is shown ONLY in this response - cannot be recovered later
    """
    # Validate project exists if project_id provided
    if key_data.project_id:
        project_query = select(Project).where(Project.id == key_data.project_id)
        project_result = await db.execute(project_query)
        project = project_result.scalar_one_or_none()

        if not project:
            raise ResourceNotFoundError(
                resource_type="Project",
                resource_id=str(key_data.project_id),
            )

    # Generate secure API key
    raw_key = generate_api_key(prefix="lb")
    key_hash = hash_api_key(raw_key)
    key_prefix = get_api_key_prefix(raw_key)

    # Create API key record
    new_key = ApiKey(
        key_hash=key_hash,
        key_prefix=key_prefix,
        name=key_data.name,
        project_id=key_data.project_id,
        scopes=key_data.scopes,
        expires_at=key_data.expires_at,
        is_active=True,
        created_at=datetime.now(timezone.utc),
    )

    db.add(new_key)
    await db.commit()
    await db.refresh(new_key)

    # Log successful creation (without sensitive data)
    logger.info(
        f"Created API key: {new_key.name} ({new_key.key_prefix})",
        extra={
            "extra_fields": {
                "key_id": str(new_key.id),
                "key_prefix": new_key.key_prefix,
                "scopes": new_key.scopes,
                "project_id": str(new_key.project_id) if new_key.project_id else None,
            }
        },
    )

    # Return response with FULL KEY (only time it's shown!)
    response_data = {
        "id": new_key.id,
        "key_prefix": new_key.key_prefix,
        "name": new_key.name,
        "project_id": new_key.project_id,
        "scopes": new_key.scopes,
        "is_active": new_key.is_active,
        "expires_at": new_key.expires_at,
        "last_used_at": new_key.last_used_at,
        "created_by": new_key.created_by,
        "created_at": new_key.created_at,
        "revoked_at": new_key.revoked_at,
        "key": raw_key,  # Full key shown only once!
    }
    return ApiKeyCreateResponse(**response_data)


@router.get("/{key_id}", response_model=ApiKeyResponse)
async def get_api_key(
    key_id: UUID,
    db: AsyncSession = Depends(get_async_database),
    api_key: ApiKey = Depends(RequireRead),
) -> ApiKeyResponse:
    """Get a single API key by ID.

    **Path Parameters:**
    - key_id: UUID - Key identifier

    **Returns:**
    - Key details (only key_prefix shown, not full key)

    **Errors:**
    - 404 Not Found: Key doesn't exist

    **Authentication:**
    - Requires: API key with 'read', 'write', or 'admin' scope

    **Security:**
    - Full key is NEVER returned (only key_prefix)
    - Key was shown in full only once during creation
    """
    # Fetch key
    query = select(ApiKey).where(ApiKey.id == key_id)
    result = await db.execute(query)
    key = result.scalar_one_or_none()

    # Check if key exists
    if not key:
        raise ResourceNotFoundError(
            resource_type="ApiKey",
            resource_id=str(key_id),
        )

    # Log successful query
    logger.info(
        f"Retrieved API key: {key.name}",
        extra={
            "extra_fields": {
                "key_id": str(key.id),
                "key_prefix": key.key_prefix,
            }
        },
    )

    return ApiKeyResponse.model_validate(key)


@router.patch("/{key_id}", response_model=ApiKeyResponse)
async def update_api_key(
    key_id: UUID,
    update_data: ApiKeyUpdate,
    db: AsyncSession = Depends(get_async_database),
    api_key: ApiKey = Depends(RequireAdmin),
) -> ApiKeyResponse:
    """Update an existing API key (partial update).

    **Path Parameters:**
    - key_id: UUID - Key identifier

    **Request Body (all optional):**
    - name: Key name
    - scopes: Permission scopes array
    - expires_at: Expiration timestamp
    - is_active: Active status (set to false to revoke key)

    **Returns:**
    - Updated key

    **Errors:**
    - 404 Not Found: Key doesn't exist
    - 422 Validation Error: Invalid field values

    **Authentication:**
    - Requires: API key with 'admin' scope

    **Note:**
    - Set `is_active=false` to revoke a key (cannot be un-revoked)
    - Cannot change project_id after creation
    - Cannot recover the full key (only prefix is stored)
    """
    # Fetch existing key
    query = select(ApiKey).where(ApiKey.id == key_id)
    result = await db.execute(query)
    key = result.scalar_one_or_none()

    # Check if key exists
    if not key:
        raise ResourceNotFoundError(
            resource_type="ApiKey",
            resource_id=str(key_id),
        )

    # Get update data (only fields that were provided)
    update_fields = update_data.model_dump(exclude_unset=True)

    # If no fields to update, return existing key
    if not update_fields:
        logger.info(f"No fields to update for API key: {key.name}")
        return ApiKeyResponse.model_validate(key)

    # Apply updates
    for field, value in update_fields.items():
        setattr(key, field, value)

    # If key is being revoked, set revoked_at timestamp
    if update_fields.get("is_active") is False and not key.revoked_at:
        key.revoked_at = datetime.now(timezone.utc)

    # Commit changes
    await db.commit()
    await db.refresh(key)

    # Log successful update
    logger.info(
        f"Updated API key: {key.name}",
        extra={
            "extra_fields": {
                "key_id": str(key.id),
                "updated_fields": list(update_fields.keys()),
            }
        },
    )

    return ApiKeyResponse.model_validate(key)


@router.delete("/{key_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_api_key(
    key_id: UUID,
    db: AsyncSession = Depends(get_async_database),
    api_key: ApiKey = Depends(RequireAdmin),
) -> Response:
    """Delete an API key.

    **Path Parameters:**
    - key_id: UUID - Key identifier

    **Behavior:**
    - Hard delete (permanently removes record)
    - Immediately invalidates the key

    **Returns:**
    - 204 No Content: Key deleted successfully

    **Errors:**
    - 404 Not Found: Key doesn't exist

    **Authentication:**
    - Requires: API key with 'admin' scope

    **Warning:**
    - This is a hard delete - key cannot be recovered
    - Consider setting `is_active=false` instead for soft revocation
    """
    # Fetch existing key
    query = select(ApiKey).where(ApiKey.id == key_id)
    result = await db.execute(query)
    key = result.scalar_one_or_none()

    # Check if key exists
    if not key:
        raise ResourceNotFoundError(
            resource_type="ApiKey",
            resource_id=str(key_id),
        )

    # Delete the key
    await db.delete(key)
    await db.commit()

    # Log deletion
    logger.info(
        f"Deleted API key: {key.name}",
        extra={
            "extra_fields": {
                "key_id": str(key_id),
                "key_prefix": key.key_prefix,
            }
        },
    )

    # Return 204 No Content (no response body)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
