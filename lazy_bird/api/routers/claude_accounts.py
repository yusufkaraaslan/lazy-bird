"""ClaudeAccounts API endpoints for managing Claude API/subscription accounts.

This module provides CRUD operations for Claude accounts with:
- Support for both API and subscription modes
- Encrypted credential storage
- Usage tracking and budget limits
- Account activation/deactivation
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
from lazy_bird.models.claude_account import ClaudeAccount
from lazy_bird.schemas.claude_account import (
    ClaudeAccountCreate,
    ClaudeAccountListResponse,
    ClaudeAccountResponse,
    ClaudeAccountUpdate,
)

logger = get_logger(__name__)

# Create router
router = APIRouter(prefix="/claude-accounts", tags=["claude-accounts"])


@router.get("", response_model=ClaudeAccountListResponse)
@router.get("/", response_model=ClaudeAccountListResponse)
async def list_claude_accounts(
    # Pagination
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    # Filtering
    account_type: Optional[str] = Query(
        None, description="Filter by account type (api, subscription)"
    ),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    # Dependencies
    db: AsyncSession = Depends(get_async_database),
    api_key: ApiKey = Depends(RequireRead),
) -> ClaudeAccountListResponse:
    """List all Claude accounts with pagination and filtering.

    **Pagination:**
    - Offset-based pagination with page and page_size
    - Default: page=1, page_size=20
    - Max page_size: 100

    **Filtering:**
    - `account_type`: string - Filter by type (api, subscription)
    - `is_active`: boolean - Filter by active status

    **Returns:**
    - List of Claude accounts (credentials masked)
    - Total count, page info, pagination metadata

    **Authentication:**
    - Requires: API key with 'read', 'write', or 'admin' scope

    **Security:**
    - API keys are never returned (only safe preview)
    - Session tokens are never returned
    """
    # Build base query
    query = select(ClaudeAccount)

    # Apply filters
    filters = []

    # Filter by account type
    if account_type:
        filters.append(ClaudeAccount.account_type == account_type)

    # Filter by active status
    if is_active is not None:
        filters.append(ClaudeAccount.is_active == is_active)

    # Add all filters to query
    if filters:
        query = query.where(*filters)

    # Get total count
    count_query = select(func.count()).select_from(ClaudeAccount)
    if filters:
        count_query = count_query.where(*filters)
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Calculate pagination
    offset = (page - 1) * page_size
    pages = (total + page_size - 1) // page_size if total > 0 else 0

    # Apply pagination and sorting
    query = query.order_by(ClaudeAccount.created_at.desc()).offset(offset).limit(page_size)

    # Execute query
    result = await db.execute(query)
    accounts = result.scalars().all()

    # Convert to response models (credentials automatically masked by schema)
    account_responses = [ClaudeAccountResponse.model_validate(acc) for acc in accounts]

    # Log successful query
    logger.info(
        f"Listed {len(accounts)} Claude accounts (page {page}/{pages})",
        extra={
            "extra_fields": {
                "total": total,
                "page": page,
                "page_size": page_size,
                "filters": {
                    "account_type": account_type,
                    "is_active": is_active,
                },
            }
        },
    )

    return ClaudeAccountListResponse(
        items=account_responses,
        total=total,
        page=page,
        page_size=page_size,
        pages=pages,
    )


@router.post("", response_model=ClaudeAccountResponse, status_code=status.HTTP_201_CREATED)
@router.post("/", response_model=ClaudeAccountResponse, status_code=status.HTTP_201_CREATED)
async def create_claude_account(
    account_data: ClaudeAccountCreate,
    db: AsyncSession = Depends(get_async_database),
    api_key: ApiKey = Depends(RequireAdmin),
) -> ClaudeAccountResponse:
    """Create a new Claude account.

    **Required Fields:**
    - name: Human-readable account name
    - account_type: "api" or "subscription"

    **API Mode (account_type="api"):**
    - api_key: Anthropic API key (will be encrypted)

    **Subscription Mode (account_type="subscription"):**
    - config_directory: Path to Claude config directory
    - session_token: Session token (will be encrypted, optional)

    **Optional Fields:**
    - model: Claude model (default: "claude-sonnet-4-5")
    - max_tokens: Maximum tokens (default: 8000)
    - temperature: Model temperature (default: 0.7)
    - monthly_budget_usd: Monthly spending limit
    - is_active: Active status (default: true)

    **Returns:**
    - 201 Created: Account created successfully
    - 422 Validation Error: Invalid input data

    **Authentication:**
    - Requires: API key with 'admin' scope

    **Security:**
    - API keys and session tokens are encrypted before storage
    - Credentials are never returned in responses
    """
    # Create account (encryption handled by model)
    account = ClaudeAccount(
        name=account_data.name,
        account_type=account_data.account_type,
        # API mode
        api_key_encrypted=account_data.api_key,  # Will be encrypted by model
        # Subscription mode
        config_directory=account_data.config_directory,
        session_token_encrypted=account_data.session_token,  # Will be encrypted
        # Claude settings
        model=account_data.model,
        max_tokens=account_data.max_tokens,
        temperature=account_data.temperature,
        # Usage limits
        monthly_budget_usd=account_data.monthly_budget_usd,
        is_active=account_data.is_active,
        # Timestamps
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )

    db.add(account)
    await db.commit()
    await db.refresh(account)

    # Log successful creation (without sensitive data)
    logger.info(
        f"Created Claude account: {account.name} ({account.account_type})",
        extra={
            "extra_fields": {
                "account_id": str(account.id),
                "account_type": account.account_type,
                "model": account.model,
            }
        },
    )

    return ClaudeAccountResponse.model_validate(account)


@router.get("/{account_id}", response_model=ClaudeAccountResponse)
async def get_claude_account(
    account_id: UUID,
    db: AsyncSession = Depends(get_async_database),
    api_key: ApiKey = Depends(RequireRead),
) -> ClaudeAccountResponse:
    """Get a single Claude account by ID.

    **Path Parameters:**
    - account_id: UUID - Account identifier

    **Returns:**
    - Account details (credentials masked)

    **Errors:**
    - 404 Not Found: Account doesn't exist

    **Authentication:**
    - Requires: API key with 'read', 'write', or 'admin' scope

    **Security:**
    - Full API keys and session tokens are never returned
    - Only safe previews are included in response
    """
    # Fetch account
    query = select(ClaudeAccount).where(ClaudeAccount.id == account_id)
    result = await db.execute(query)
    account = result.scalar_one_or_none()

    # Check if account exists
    if not account:
        raise ResourceNotFoundError(
            resource_type="ClaudeAccount",
            resource_id=str(account_id),
        )

    # Log successful query
    logger.info(
        f"Retrieved Claude account: {account.name}",
        extra={
            "extra_fields": {
                "account_id": str(account.id),
                "account_type": account.account_type,
            }
        },
    )

    return ClaudeAccountResponse.model_validate(account)


@router.patch("/{account_id}", response_model=ClaudeAccountResponse)
async def update_claude_account(
    account_id: UUID,
    update_data: ClaudeAccountUpdate,
    db: AsyncSession = Depends(get_async_database),
    api_key: ApiKey = Depends(RequireAdmin),
) -> ClaudeAccountResponse:
    """Update an existing Claude account (partial update).

    **Path Parameters:**
    - account_id: UUID - Account identifier

    **Request Body (all optional):**
    - name: Account name
    - api_key: New API key (will be encrypted)
    - config_directory: Config directory path
    - session_token: New session token (will be encrypted)
    - model: Claude model
    - max_tokens: Maximum tokens
    - temperature: Model temperature
    - monthly_budget_usd: Monthly spending limit
    - is_active: Active status

    **Returns:**
    - Updated account

    **Errors:**
    - 404 Not Found: Account doesn't exist
    - 422 Validation Error: Invalid field values

    **Authentication:**
    - Requires: API key with 'admin' scope

    **Note:**
    - account_type cannot be changed after creation
    - Updating credentials (api_key, session_token) will re-encrypt them
    """
    # Fetch existing account
    query = select(ClaudeAccount).where(ClaudeAccount.id == account_id)
    result = await db.execute(query)
    account = result.scalar_one_or_none()

    # Check if account exists
    if not account:
        raise ResourceNotFoundError(
            resource_type="ClaudeAccount",
            resource_id=str(account_id),
        )

    # Get update data (only fields that were provided)
    update_fields = update_data.model_dump(exclude_unset=True)

    # If no fields to update, return existing account
    if not update_fields:
        logger.info(f"No fields to update for Claude account: {account.name}")
        return ClaudeAccountResponse.model_validate(account)

    # Apply updates (encryption handled by model setters)
    for field, value in update_fields.items():
        # Map schema fields to model fields
        if field == "api_key":
            account.api_key_encrypted = value  # Will be encrypted
        elif field == "session_token":
            account.session_token_encrypted = value  # Will be encrypted
        else:
            setattr(account, field, value)

    # Update timestamp
    account.updated_at = datetime.now(timezone.utc)

    # Commit changes
    await db.commit()
    await db.refresh(account)

    # Log successful update (without sensitive data)
    logger.info(
        f"Updated Claude account: {account.name}",
        extra={
            "extra_fields": {
                "account_id": str(account.id),
                "updated_fields": list(update_fields.keys()),
            }
        },
    )

    return ClaudeAccountResponse.model_validate(account)


@router.delete("/{account_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_claude_account(
    account_id: UUID,
    db: AsyncSession = Depends(get_async_database),
    api_key: ApiKey = Depends(RequireAdmin),
) -> Response:
    """Delete a Claude account.

    **Path Parameters:**
    - account_id: UUID - Account identifier

    **Behavior:**
    - Hard delete (permanently removes record)
    - Cascade effects:
      - Projects using this account: claude_account_id set to NULL
      - Task runs using this account: claude_account_id set to NULL

    **Returns:**
    - 204 No Content: Account deleted successfully

    **Errors:**
    - 404 Not Found: Account doesn't exist

    **Authentication:**
    - Requires: API key with 'admin' scope

    **Warning:**
    - This is a hard delete - account cannot be recovered
    - Projects and task runs will lose account association
    - Consider setting is_active=false instead for soft deactivation
    """
    # Fetch existing account
    query = select(ClaudeAccount).where(ClaudeAccount.id == account_id)
    result = await db.execute(query)
    account = result.scalar_one_or_none()

    # Check if account exists
    if not account:
        raise ResourceNotFoundError(
            resource_type="ClaudeAccount",
            resource_id=str(account_id),
        )

    # Delete the account (cascade handled by database)
    await db.delete(account)
    await db.commit()

    # Log deletion
    logger.info(
        f"Deleted Claude account: {account.name}",
        extra={
            "extra_fields": {
                "account_id": str(account_id),
                "account_type": account.account_type,
            }
        },
    )

    # Return 204 No Content (no response body)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
