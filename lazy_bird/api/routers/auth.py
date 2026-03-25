"""Authentication API endpoints for JWT-based auth.

This module provides endpoints for:
- User registration
- User login (credential verification, token issuance)
- Token refresh
- Logout (token blacklisting via Redis)
"""

from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from lazy_bird.api.dependencies import get_async_database, get_token_from_header
from lazy_bird.core.config import settings
from lazy_bird.api.exceptions import AuthenticationError, ResourceConflictError
from lazy_bird.core.logging import get_logger
from lazy_bird.core.security import (
    create_access_token,
    create_refresh_token,
    hash_password,
    verify_password,
    verify_refresh_token,
)
from lazy_bird.models.user import User
from lazy_bird.schemas.user import (
    RefreshRequest,
    TokenResponse,
    UserCreate,
    UserLogin,
    UserResponse,
)

logger = get_logger(__name__)

# Create router
router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(
    user_data: UserCreate,
    db: AsyncSession = Depends(get_async_database),
) -> UserResponse:
    """Register a new user.

    **Request Body:**
    - email: Valid email address (must be unique)
    - password: Password (8-128 characters)
    - display_name: Optional display name

    **Returns:**
    - 201 Created: User created successfully
    - 409 Conflict: Email already registered

    **Authentication:**
    - None required (public endpoint)
    """
    # Check if email already exists
    existing_query = select(User).where(User.email == user_data.email)
    existing_result = await db.execute(existing_query)
    existing_user = existing_result.scalar_one_or_none()

    if existing_user:
        raise ResourceConflictError(
            detail=f"Email '{user_data.email}' is already registered",
            conflict_field="email",
            conflict_value=user_data.email,
        )

    # Create user
    new_user = User(
        email=user_data.email,
        password_hash=hash_password(user_data.password),
        display_name=user_data.display_name,
        role="user",
        is_active=True,
        created_at=datetime.now(timezone.utc),
    )

    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)

    logger.info(
        f"User registered: {new_user.email}",
        extra={
            "extra_fields": {
                "user_id": str(new_user.id),
                "email": new_user.email,
            }
        },
    )

    return UserResponse.model_validate(new_user)


@router.post("/login", response_model=TokenResponse)
async def login(
    credentials: UserLogin,
    db: AsyncSession = Depends(get_async_database),
) -> TokenResponse:
    """Login with email and password.

    **Request Body:**
    - email: Registered email address
    - password: Account password

    **Returns:**
    - 200 OK: TokenResponse with access_token and refresh_token
    - 401 Unauthorized: Invalid credentials

    **Authentication:**
    - None required (public endpoint)
    """
    # Find user by email
    query = select(User).where(User.email == credentials.email)
    result = await db.execute(query)
    user = result.scalar_one_or_none()

    # Verify user exists and password matches
    if not user or not verify_password(credentials.password, user.password_hash):
        raise AuthenticationError(detail="Invalid email or password")

    # Check if user is active
    if not user.is_active:
        raise AuthenticationError(detail="Account is disabled")

    # Create tokens
    token_data = {"sub": str(user.id), "email": user.email, "role": user.role}
    access_token = create_access_token(data=token_data)
    refresh_token = create_refresh_token(data=token_data)

    logger.info(
        f"User logged in: {user.email}",
        extra={
            "extra_fields": {
                "user_id": str(user.id),
                "email": user.email,
            }
        },
    )

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh(
    request: RefreshRequest,
    db: AsyncSession = Depends(get_async_database),
) -> TokenResponse:
    """Refresh access token using a valid refresh token.

    **Request Body:**
    - refresh_token: Valid JWT refresh token

    **Returns:**
    - 200 OK: New TokenResponse with fresh access_token and refresh_token
    - 401 Unauthorized: Invalid or expired refresh token

    **Authentication:**
    - None required (uses refresh token for authentication)
    """
    # Verify refresh token
    payload = verify_refresh_token(request.refresh_token)

    if not payload:
        raise AuthenticationError(detail="Invalid or expired refresh token")

    # Get user ID from token
    user_id_str = payload.get("sub")
    if not user_id_str:
        raise AuthenticationError(detail="Invalid token: missing user identifier")

    # Convert string back to UUID for database query
    try:
        user_id = UUID(user_id_str)
    except (ValueError, AttributeError):
        raise AuthenticationError(detail="Invalid token: malformed user identifier")

    # Verify user still exists and is active
    query = select(User).where(User.id == user_id)
    result = await db.execute(query)
    user = result.scalar_one_or_none()

    if not user:
        raise AuthenticationError(detail="User not found")

    if not user.is_active:
        raise AuthenticationError(detail="Account is disabled")

    # Create new tokens
    token_data = {"sub": str(user.id), "email": user.email, "role": user.role}
    access_token = create_access_token(data=token_data)
    new_refresh_token = create_refresh_token(data=token_data)

    logger.info(
        f"Token refreshed for user: {user.email}",
        extra={
            "extra_fields": {
                "user_id": str(user.id),
            }
        },
    )

    return TokenResponse(
        access_token=access_token,
        refresh_token=new_refresh_token,
        token_type="bearer",
    )


@router.post("/logout", status_code=status.HTTP_200_OK)
async def logout(
    token: Optional[str] = Depends(get_token_from_header),
) -> dict:
    """Logout by blacklisting the current access token in Redis.

    **Behavior:**
    - Adds the token's JTI (or hash) to a Redis blacklist
    - Token becomes invalid for future requests
    - Blacklist entry expires when the token would have expired

    **Returns:**
    - 200 OK: Logout successful

    **Authentication:**
    - Optional: If token provided, it's blacklisted
    """
    if token:
        try:
            from lazy_bird.core.security import verify_token
            from lazy_bird.core.redis import get_async_redis

            payload = verify_token(token)
            if payload:
                redis_client = await get_async_redis()
                if redis_client:
                    import hashlib

                    token_hash = hashlib.sha256(token.encode()).hexdigest()
                    # Blacklist for remaining token lifetime (default 15 min)
                    ttl = settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60
                    await redis_client.setex(f"blacklist:{token_hash}", ttl, "1")
                    logger.info("Token blacklisted on logout")
        except Exception as e:
            logger.warning(f"Token blacklisting failed (non-critical): {e}")

    return {"message": "Logged out successfully."}
