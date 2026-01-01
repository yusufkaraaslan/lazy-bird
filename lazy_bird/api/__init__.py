"""API layer for Lazy-Bird.

This package contains the FastAPI application and related components:
- middleware: Request/response middleware (CORS, logging, error handling)
- routers: API route handlers
- dependencies: FastAPI dependency injection functions
"""

from lazy_bird.api.middleware import (
    ErrorHandlingMiddleware,
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
    # Setup functions
    "setup_cors",
    "setup_middleware",
]
