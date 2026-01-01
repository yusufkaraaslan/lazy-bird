"""API layer for Lazy-Bird.

This package contains the FastAPI application and related components:
- middleware: Request/response middleware (CORS, logging, error handling)
- routers: API route handlers
- dependencies: FastAPI dependency injection functions
- exceptions: Custom exceptions and error handlers (RFC 7807)
"""

from lazy_bird.api.dependencies import (
    RequireAdmin,
    RequireRead,
    RequireScopes,
    RequireWrite,
    get_async_database,
    get_current_api_key,
    get_current_user,
    get_database,
    get_optional_api_key,
    get_optional_user,
)
from lazy_bird.api.exceptions import (
    ExternalServiceError,
    InsufficientPermissionsError,
    LazyBirdException,
    ProblemDetails,
    ResourceConflictError,
    ResourceNotFoundError,
    ValidationError,
    register_exception_handlers,
)
from lazy_bird.api.middleware import (
    ErrorHandlingMiddleware,
    RateLimitMiddleware,
    RequestIDMiddleware,
    RequestLoggingMiddleware,
    SecurityHeadersMiddleware,
    setup_cors,
    setup_middleware,
)

__all__ = [
    # Middleware classes
    "RequestIDMiddleware",
    "RequestLoggingMiddleware",
    "ErrorHandlingMiddleware",
    "SecurityHeadersMiddleware",
    "RateLimitMiddleware",
    # Setup functions
    "setup_cors",
    "setup_middleware",
    # Dependencies - Database
    "get_database",
    "get_async_database",
    # Dependencies - Authentication
    "get_current_api_key",
    "get_current_user",
    "get_optional_api_key",
    "get_optional_user",
    # Dependencies - Permissions
    "RequireScopes",
    "RequireRead",
    "RequireWrite",
    "RequireAdmin",
    # Exceptions - Custom Exception Classes
    "LazyBirdException",
    "ValidationError",
    "ResourceNotFoundError",
    "ResourceConflictError",
    "InsufficientPermissionsError",
    "ExternalServiceError",
    # Exceptions - Schemas and Handlers
    "ProblemDetails",
    "register_exception_handlers",
]
