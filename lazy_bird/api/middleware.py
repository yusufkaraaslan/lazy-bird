"""Middleware components for FastAPI application.

This module provides middleware for:
- CORS configuration
- Request logging with correlation IDs
- Error handling and exception tracking
- Request ID generation
"""

import time
import uuid
from typing import Callable

from fastapi import Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from lazy_bird.core.config import settings
from lazy_bird.core.logging import (
    clear_correlation_id,
    get_logger,
    log_with_context,
    set_correlation_id,
)

logger = get_logger(__name__)


def setup_cors(app: ASGIApp) -> None:
    """Configure CORS middleware for the application.

    Args:
        app: FastAPI application instance

    Example:
        >>> from fastapi import FastAPI
        >>> app = FastAPI()
        >>> setup_cors(app)
    """
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],  # Allow all methods (GET, POST, PUT, DELETE, etc.)
        allow_headers=["*"],  # Allow all headers
        expose_headers=["X-Request-ID", "X-Correlation-ID"],
    )
    logger.info(
        "CORS middleware configured", extra={"extra_fields": {"origins": settings.CORS_ORIGINS}}
    )


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Middleware to add unique request ID to each request.

    Generates a UUID for each request and adds it to:
    - Request state (request.state.request_id)
    - Response headers (X-Request-ID)
    - Logging context (correlation_id)
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request and add request ID.

        Args:
            request: Incoming request
            call_next: Next middleware/route handler

        Returns:
            Response: Response with X-Request-ID header
        """
        # Check if request already has an ID (from client)
        request_id = request.headers.get("X-Request-ID")

        # Generate new ID if not provided
        if not request_id:
            request_id = str(uuid.uuid4())

        # Store in request state
        request.state.request_id = request_id

        # Set correlation ID for logging
        set_correlation_id(request_id)

        try:
            # Process request
            response = await call_next(request)

            # Add request ID to response headers
            response.headers["X-Request-ID"] = request_id
            response.headers["X-Correlation-ID"] = request_id

            return response
        finally:
            # Clear correlation ID after request
            clear_correlation_id()


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware to log all HTTP requests and responses.

    Logs:
    - Request method, path, query params
    - Request headers (configurable)
    - Response status code
    - Response time
    - Client IP address
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process and log request.

        Args:
            request: Incoming request
            call_next: Next middleware/route handler

        Returns:
            Response: Response from route handler
        """
        # Start timer
        start_time = time.time()

        # Extract request info
        request_id = getattr(request.state, "request_id", "unknown")
        client_ip = request.client.host if request.client else "unknown"
        method = request.method
        path = request.url.path
        query_params = str(request.query_params) if request.query_params else None

        # Log incoming request
        log_with_context(
            logger,
            20,  # INFO level
            f"{method} {path}",
            request_id=request_id,
            client_ip=client_ip,
            method=method,
            path=path,
            query_params=query_params,
        )

        # Process request
        try:
            response = await call_next(request)
        except Exception as e:
            # Log error and re-raise
            duration = time.time() - start_time
            log_with_context(
                logger,
                40,  # ERROR level
                f"{method} {path} - Exception: {str(e)}",
                request_id=request_id,
                client_ip=client_ip,
                method=method,
                path=path,
                duration_ms=round(duration * 1000, 2),
                error=str(e),
                error_type=type(e).__name__,
            )
            raise

        # Calculate response time
        duration = time.time() - start_time

        # Log response
        log_with_context(
            logger,
            20,  # INFO level
            f"{method} {path} - {response.status_code}",
            request_id=request_id,
            client_ip=client_ip,
            method=method,
            path=path,
            status_code=response.status_code,
            duration_ms=round(duration * 1000, 2),
        )

        # Add response time header
        response.headers["X-Response-Time"] = f"{round(duration * 1000, 2)}ms"

        return response


class ErrorHandlingMiddleware(BaseHTTPMiddleware):
    """Middleware to catch and handle uncaught exceptions.

    Converts unhandled exceptions into proper JSON error responses.
    Logs all errors with full context.
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request and handle errors.

        Args:
            request: Incoming request
            call_next: Next middleware/route handler

        Returns:
            Response: Response from handler or error response
        """
        try:
            return await call_next(request)
        except Exception as exc:
            # Get request ID for error tracking
            request_id = getattr(request.state, "request_id", "unknown")

            # Log the error
            log_with_context(
                logger,
                40,  # ERROR level
                f"Unhandled exception: {str(exc)}",
                request_id=request_id,
                error=str(exc),
                error_type=type(exc).__name__,
                method=request.method,
                path=request.url.path,
            )

            # Return JSON error response
            if settings.DEBUG:
                # Include detailed error info in debug mode
                error_detail = {
                    "error": type(exc).__name__,
                    "message": str(exc),
                    "request_id": request_id,
                }
            else:
                # Generic error in production
                error_detail = {
                    "error": "Internal Server Error",
                    "message": "An unexpected error occurred",
                    "request_id": request_id,
                }

            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content=error_detail,
                headers={
                    "X-Request-ID": request_id,
                },
            )


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Middleware to add security headers to all responses.

    Adds:
    - X-Content-Type-Options: nosniff
    - X-Frame-Options: DENY
    - X-XSS-Protection: 1; mode=block
    - Strict-Transport-Security (HSTS) in production
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Add security headers to response.

        Args:
            request: Incoming request
            call_next: Next middleware/route handler

        Returns:
            Response: Response with security headers
        """
        response = await call_next(request)

        # Add security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"

        # Add HSTS in production (not in development/testing)
        if not settings.DEBUG:
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"

        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Middleware for rate limiting requests.

    Implements token bucket algorithm using Redis for distributed rate limiting.
    Tracks requests per IP address and/or API key.
    """

    def __init__(self, app: ASGIApp, requests_per_minute: int = 60):
        """Initialize rate limiter.

        Args:
            app: ASGI application
            requests_per_minute: Max requests per minute (default: 60)
        """
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.window_seconds = 60

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Check rate limit and process request.

        Args:
            request: Incoming request
            call_next: Next middleware/route handler

        Returns:
            Response: Response from handler or 429 if rate limited
        """
        # Get client identifier (IP or API key)
        client_ip = request.client.host if request.client else "unknown"
        api_key = request.headers.get("X-API-Key", "")

        # Use API key if present, otherwise IP
        identifier = api_key[:16] if api_key else client_ip

        # Check rate limit using Redis
        try:
            from lazy_bird.core.redis import get_redis

            redis_client = get_redis()
            key = f"rate_limit:{identifier}"

            # Get current count
            current = redis_client.get(key)

            if current and int(current) >= self.requests_per_minute:
                # Rate limit exceeded
                log_with_context(
                    logger,
                    30,  # WARNING level
                    f"Rate limit exceeded for {identifier}",
                    client_ip=client_ip,
                    current_requests=int(current),
                    limit=self.requests_per_minute,
                )

                return JSONResponse(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    content={
                        "error": "Rate limit exceeded",
                        "message": f"Maximum {self.requests_per_minute} requests per minute",
                        "retry_after": self.window_seconds,
                    },
                    headers={
                        "Retry-After": str(self.window_seconds),
                        "X-RateLimit-Limit": str(self.requests_per_minute),
                        "X-RateLimit-Remaining": "0",
                        "X-RateLimit-Reset": str(self.window_seconds),
                    },
                )

            # Increment counter
            pipe = redis_client.pipeline()
            pipe.incr(key)
            if not current:
                # Set expiry on first request in window
                pipe.expire(key, self.window_seconds)
            pipe.execute()

            # Get updated count
            new_count = int(current) + 1 if current else 1
            remaining = max(0, self.requests_per_minute - new_count)

        except Exception as e:
            # If Redis fails, allow request (fail open)
            logger.warning(f"Rate limiting unavailable: {e}")
            remaining = self.requests_per_minute

        # Process request
        response = await call_next(request)

        # Add rate limit headers
        response.headers["X-RateLimit-Limit"] = str(self.requests_per_minute)
        response.headers["X-RateLimit-Remaining"] = str(remaining)

        return response


def setup_middleware(app: ASGIApp) -> None:
    """Configure all middleware for the application.

    Order matters! Middleware is executed in reverse order of addition.
    First added = outermost layer = executes first on request, last on response.

    Execution order (request):
    1. SecurityHeadersMiddleware
    2. RateLimitMiddleware
    3. ErrorHandlingMiddleware
    4. RequestLoggingMiddleware
    5. RequestIDMiddleware
    6. CORS (if applicable)
    7. Route handler

    Args:
        app: FastAPI application instance

    Example:
        >>> from fastapi import FastAPI
        >>> app = FastAPI()
        >>> setup_middleware(app)
    """
    # CORS - outermost layer (processes first on request)
    setup_cors(app)

    # Request ID - establishes correlation ID for logging
    app.add_middleware(RequestIDMiddleware)

    # Request logging - logs with correlation ID
    app.add_middleware(RequestLoggingMiddleware)

    # Error handling - catches all unhandled exceptions
    app.add_middleware(ErrorHandlingMiddleware)

    # Rate limiting - prevent abuse
    app.add_middleware(RateLimitMiddleware, requests_per_minute=settings.RATE_LIMIT_PER_MINUTE)

    # Security headers - adds security headers to all responses
    app.add_middleware(SecurityHeadersMiddleware)

    logger.info("All middleware configured successfully")
