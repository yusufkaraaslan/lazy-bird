"""Dependency injection for FastAPI endpoints.

This module provides dependency functions for:
- Database session management
- API key authentication
- JWT token authentication
- Current user retrieval
"""

from typing import AsyncGenerator, Generator, Optional

from fastapi import Depends, HTTPException, Header, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from lazy_bird.core.database import AsyncSessionLocal, SessionLocal, get_async_db, get_db
from lazy_bird.core.logging import get_logger
from lazy_bird.core.security import verify_token
from lazy_bird.models.api_key import ApiKey

logger = get_logger(__name__)


# Re-export database dependencies from core
def get_database() -> Generator[Session, None, None]:
    """Get synchronous database session.

    Yields:
        Session: SQLAlchemy session

    Example:
        >>> from fastapi import Depends
        >>> @app.get("/")
        >>> def endpoint(db: Session = Depends(get_database)):
        >>>     # Use db session
    """
    yield from get_db()


async def get_async_database() -> AsyncGenerator[AsyncSession, None]:
    """Get asynchronous database session.

    Yields:
        AsyncSession: SQLAlchemy async session

    Example:
        >>> from fastapi import Depends
        >>> @app.get("/")
        >>> async def endpoint(db: AsyncSession = Depends(get_async_database)):
        >>>     # Use async db session
    """
    async for session in get_async_db():
        yield session


# API Key Authentication
async def get_api_key_from_header(
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
) -> Optional[str]:
    """Extract API key from X-API-Key header.

    Args:
        x_api_key: API key from header

    Returns:
        Optional[str]: API key if present, None otherwise

    Example:
        >>> curl -H "X-API-Key: lb_abc123..." http://localhost:8000/api/v1/projects
    """
    return x_api_key


async def get_current_api_key(
    api_key: Optional[str] = Depends(get_api_key_from_header),
    db: AsyncSession = Depends(get_async_database),
) -> ApiKey:
    """Validate API key and return ApiKey model.

    Args:
        api_key: API key from header
        db: Database session

    Returns:
        ApiKey: Validated ApiKey model

    Raises:
        HTTPException: 401 if API key is missing or invalid
        HTTPException: 403 if API key is inactive or expired

    Example:
        >>> from fastapi import Depends
        >>> @app.get("/protected")
        >>> async def endpoint(api_key: ApiKey = Depends(get_current_api_key)):
        >>>     # api_key is validated and active
    """
    from lazy_bird.core.security import hash_api_key
    from sqlalchemy import select

    # Check if API key provided
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key required. Provide X-API-Key header.",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    # Hash the provided key
    hashed_key = hash_api_key(api_key)

    # Query database for matching API key
    result = await db.execute(
        select(ApiKey).where(
            ApiKey.key_hash == hashed_key,
            ApiKey.is_active == True,  # noqa: E712
        )
    )
    api_key_model = result.scalar_one_or_none()

    # Check if API key exists
    if not api_key_model:
        logger.warning(f"Invalid API key attempt: {api_key[:8]}...")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    # Check if API key is expired
    from datetime import datetime

    if api_key_model.expires_at and api_key_model.expires_at < datetime.utcnow():
        logger.warning(f"Expired API key used: {api_key_model.key_prefix}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="API key has expired",
        )

    # Update last_used_at timestamp
    api_key_model.last_used_at = datetime.utcnow()
    await db.commit()

    logger.info(
        f"API key authenticated: {api_key_model.key_prefix}",
        extra={"extra_fields": {"api_key_id": str(api_key_model.id)}},
    )

    return api_key_model


# JWT Token Authentication
async def get_token_from_header(
    authorization: Optional[str] = Header(None, alias="Authorization"),
) -> Optional[str]:
    """Extract JWT token from Authorization header.

    Args:
        authorization: Authorization header value

    Returns:
        Optional[str]: JWT token if present and valid format, None otherwise

    Example:
        >>> curl -H "Authorization: Bearer eyJ..." http://localhost:8000/api/v1/projects
    """
    if not authorization:
        return None

    # Check format: "Bearer <token>"
    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        return None

    return parts[1]


async def get_current_user(
    token: Optional[str] = Depends(get_token_from_header),
) -> dict:
    """Validate JWT token and return user information.

    Args:
        token: JWT token from header

    Returns:
        dict: User information from token payload

    Raises:
        HTTPException: 401 if token is missing or invalid

    Example:
        >>> from fastapi import Depends
        >>> @app.get("/me")
        >>> async def endpoint(user: dict = Depends(get_current_user)):
        >>>     # user contains: {"sub": "user_id", "email": "user@example.com", ...}
    """
    # Check if token provided
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Provide Authorization: Bearer <token> header.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Verify token
    payload = verify_token(token)

    if not payload:
        logger.warning("Invalid JWT token attempt")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Check required claims
    if "sub" not in payload:
        logger.error("JWT token missing 'sub' claim")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token: missing user identifier",
            headers={"WWW-Authenticate": "Bearer"},
        )

    logger.info(
        f"JWT authenticated: {payload.get('sub')}",
        extra={"extra_fields": {"user_id": payload.get("sub")}},
    )

    return payload


# Optional Authentication (doesn't raise exception if missing)
async def get_optional_api_key(
    api_key: Optional[str] = Depends(get_api_key_from_header),
    db: AsyncSession = Depends(get_async_database),
) -> Optional[ApiKey]:
    """Optional API key validation (doesn't raise if missing).

    Args:
        api_key: API key from header
        db: Database session

    Returns:
        Optional[ApiKey]: Validated ApiKey model or None if no key provided

    Example:
        >>> from fastapi import Depends
        >>> @app.get("/public-or-private")
        >>> async def endpoint(api_key: Optional[ApiKey] = Depends(get_optional_api_key)):
        >>>     if api_key:
        >>>         # Authenticated user
        >>>     else:
        >>>         # Public access
    """
    if not api_key:
        return None

    try:
        return await get_current_api_key(api_key, db)
    except HTTPException:
        return None


async def get_optional_user(
    token: Optional[str] = Depends(get_token_from_header),
) -> Optional[dict]:
    """Optional JWT validation (doesn't raise if missing).

    Args:
        token: JWT token from header

    Returns:
        Optional[dict]: User payload or None if no token provided

    Example:
        >>> from fastapi import Depends
        >>> @app.get("/public-or-private")
        >>> async def endpoint(user: Optional[dict] = Depends(get_optional_user)):
        >>>     if user:
        >>>         # Authenticated user
        >>>     else:
        >>>         # Public access
    """
    if not token:
        return None

    try:
        return await get_current_user(token)
    except HTTPException:
        return None


# Permission Checking Dependencies
class RequireScopes:
    """Dependency to check API key has required scopes.

    Example:
        >>> from fastapi import Depends
        >>> @app.delete("/projects/{id}")
        >>> async def delete_project(
        >>>     api_key: ApiKey = Depends(RequireScopes(["write", "admin"]))
        >>> ):
        >>>     # api_key has either "write" OR "admin" scope
    """

    def __init__(self, required_scopes: list[str]):
        """Initialize scope checker.

        Args:
            required_scopes: List of acceptable scopes (any match is sufficient)
        """
        self.required_scopes = required_scopes

    async def __call__(
        self,
        api_key: ApiKey = Depends(get_current_api_key),
    ) -> ApiKey:
        """Check if API key has required scopes.

        Args:
            api_key: Validated API key

        Returns:
            ApiKey: API key model if scopes match

        Raises:
            HTTPException: 403 if API key lacks required scopes
        """
        # Check if any required scope is present
        api_key_scopes = set(api_key.scopes)
        required_scopes_set = set(self.required_scopes)

        if not api_key_scopes.intersection(required_scopes_set):
            logger.warning(
                f"Insufficient permissions for API key {api_key.key_prefix}. "
                f"Required: {self.required_scopes}, Has: {api_key.scopes}"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Required scopes: {self.required_scopes}",
            )

        return api_key


# Convenience: Common permission dependencies
RequireRead = RequireScopes(["read", "write", "admin"])
RequireWrite = RequireScopes(["write", "admin"])
RequireAdmin = RequireScopes(["admin"])
