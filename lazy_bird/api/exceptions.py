"""Custom exceptions and error handlers for Lazy-Bird API.

This module implements RFC 7807 Problem Details for HTTP APIs.
See: https://tools.ietf.org/html/rfc7807
"""

from typing import Any, Dict, Optional

from fastapi import HTTPException, Request, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from lazy_bird.core.logging import get_logger

logger = get_logger(__name__)


# -------------------------------------------------------------------------
# RFC 7807 Problem Details Schema
# -------------------------------------------------------------------------


class ProblemDetails(BaseModel):
    """RFC 7807 Problem Details schema.

    Example:
        {
            "type": "https://lazy-bird.dev/errors/validation-error",
            "title": "Validation Error",
            "status": 422,
            "detail": "The 'name' field is required",
            "instance": "/api/v1/projects",
            "request_id": "550e8400-e29b-41d4-a716-446655440000",
            "errors": {...}
        }
    """

    type: str = Field(
        ...,
        description="A URI reference that identifies the problem type",
        examples=["https://lazy-bird.dev/errors/validation-error"],
    )
    title: str = Field(
        ...,
        description="A short, human-readable summary of the problem type",
        examples=["Validation Error"],
    )
    status: int = Field(
        ...,
        ge=400,
        le=599,
        description="The HTTP status code",
        examples=[422],
    )
    detail: str = Field(
        ...,
        description="A human-readable explanation specific to this occurrence",
        examples=["The 'name' field is required"],
    )
    instance: Optional[str] = Field(
        default=None,
        description="A URI reference that identifies the specific occurrence",
        examples=["/api/v1/projects"],
    )
    # Extension members (non-standard)
    request_id: Optional[str] = Field(
        default=None,
        description="Request ID for tracking",
    )
    errors: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Additional error details (validation errors, etc.)",
    )


# -------------------------------------------------------------------------
# Custom Exception Classes
# -------------------------------------------------------------------------


class LazyBirdException(HTTPException):
    """Base exception for Lazy-Bird API errors.

    All custom exceptions inherit from this class.
    """

    def __init__(
        self,
        status_code: int,
        detail: str,
        error_type: str = "about:blank",
        title: Optional[str] = None,
        errors: Optional[Dict[str, Any]] = None,
    ):
        """Initialize exception.

        Args:
            status_code: HTTP status code
            detail: Human-readable error message
            error_type: URI identifying error type (RFC 7807)
            title: Short summary of error type
            errors: Additional error details
        """
        super().__init__(status_code=status_code, detail=detail)
        self.error_type = error_type
        self.title = title or self._default_title(status_code)
        self.errors = errors

    @staticmethod
    def _default_title(status_code: int) -> str:
        """Get default title for status code.

        Args:
            status_code: HTTP status code

        Returns:
            str: Default title
        """
        titles = {
            400: "Bad Request",
            401: "Unauthorized",
            403: "Forbidden",
            404: "Not Found",
            409: "Conflict",
            422: "Unprocessable Entity",
            429: "Too Many Requests",
            500: "Internal Server Error",
            503: "Service Unavailable",
        }
        return titles.get(status_code, "Error")


class ValidationError(LazyBirdException):
    """Validation error (422)."""

    def __init__(
        self,
        detail: str,
        errors: Optional[Dict[str, Any]] = None,
    ):
        """Initialize validation error.

        Args:
            detail: Human-readable error message
            errors: Field-level validation errors
        """
        super().__init__(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=detail,
            error_type="https://lazy-bird.dev/errors/validation-error",
            title="Validation Error",
            errors=errors,
        )


class ResourceNotFoundError(LazyBirdException):
    """Resource not found (404)."""

    def __init__(
        self,
        resource_type: str,
        resource_id: str,
    ):
        """Initialize not found error.

        Args:
            resource_type: Type of resource (e.g., "Project", "ApiKey")
            resource_id: ID of resource that wasn't found
        """
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"{resource_type} with ID '{resource_id}' not found",
            error_type="https://lazy-bird.dev/errors/not-found",
            title="Resource Not Found",
            errors={"resource_type": resource_type, "resource_id": resource_id},
        )


class ResourceConflictError(LazyBirdException):
    """Resource conflict (409)."""

    def __init__(
        self,
        detail: str,
        conflict_field: Optional[str] = None,
    ):
        """Initialize conflict error.

        Args:
            detail: Human-readable error message
            conflict_field: Field that caused the conflict
        """
        errors = {"conflict_field": conflict_field} if conflict_field else None
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            detail=detail,
            error_type="https://lazy-bird.dev/errors/conflict",
            title="Resource Conflict",
            errors=errors,
        )


class InsufficientPermissionsError(LazyBirdException):
    """Insufficient permissions (403)."""

    def __init__(
        self,
        detail: str,
        required_scopes: Optional[list[str]] = None,
    ):
        """Initialize permissions error.

        Args:
            detail: Human-readable error message
            required_scopes: Required permission scopes
        """
        errors = {"required_scopes": required_scopes} if required_scopes else None
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=detail,
            error_type="https://lazy-bird.dev/errors/insufficient-permissions",
            title="Insufficient Permissions",
            errors=errors,
        )


class ExternalServiceError(LazyBirdException):
    """External service error (503)."""

    def __init__(
        self,
        service: str,
        detail: str,
    ):
        """Initialize service error.

        Args:
            service: Name of external service
            detail: Human-readable error message
        """
        super().__init__(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=detail,
            error_type="https://lazy-bird.dev/errors/service-unavailable",
            title="External Service Error",
            errors={"service": service},
        )


# -------------------------------------------------------------------------
# Exception Handlers
# -------------------------------------------------------------------------


async def lazy_bird_exception_handler(
    request: Request, exc: LazyBirdException
) -> JSONResponse:
    """Handle custom Lazy-Bird exceptions with RFC 7807 format.

    Args:
        request: FastAPI request
        exc: LazyBirdException instance

    Returns:
        JSONResponse: RFC 7807 formatted error response
    """
    # Get request ID from state (set by RequestIDMiddleware)
    request_id = getattr(request.state, "request_id", None)

    # Create problem details
    problem = ProblemDetails(
        type=exc.error_type,
        title=exc.title,
        status=exc.status_code,
        detail=exc.detail,
        instance=str(request.url.path),
        request_id=request_id,
        errors=exc.errors,
    )

    # Log error
    logger.error(
        f"{exc.title}: {exc.detail}",
        extra={
            "extra_fields": {
                "status_code": exc.status_code,
                "error_type": exc.error_type,
                "request_id": request_id,
                "path": str(request.url.path),
                "errors": exc.errors,
            }
        },
    )

    return JSONResponse(
        status_code=exc.status_code,
        content=problem.model_dump(exclude_none=True),
        headers={
            "Content-Type": "application/problem+json",
            "X-Request-ID": request_id or "unknown",
        },
    )


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """Handle standard HTTPException with RFC 7807 format.

    Args:
        request: FastAPI request
        exc: HTTPException instance

    Returns:
        JSONResponse: RFC 7807 formatted error response
    """
    # Get request ID from state
    request_id = getattr(request.state, "request_id", None)

    # Map status code to error type
    error_types = {
        400: ("https://lazy-bird.dev/errors/bad-request", "Bad Request"),
        401: ("https://lazy-bird.dev/errors/unauthorized", "Unauthorized"),
        403: ("https://lazy-bird.dev/errors/forbidden", "Forbidden"),
        404: ("https://lazy-bird.dev/errors/not-found", "Not Found"),
        405: ("https://lazy-bird.dev/errors/method-not-allowed", "Method Not Allowed"),
        409: ("https://lazy-bird.dev/errors/conflict", "Conflict"),
        422: ("https://lazy-bird.dev/errors/validation-error", "Validation Error"),
        429: ("https://lazy-bird.dev/errors/rate-limit-exceeded", "Rate Limit Exceeded"),
        500: ("https://lazy-bird.dev/errors/internal-server-error", "Internal Server Error"),
        503: ("https://lazy-bird.dev/errors/service-unavailable", "Service Unavailable"),
    }

    error_type, title = error_types.get(
        exc.status_code, ("about:blank", "Error")
    )

    # Create problem details
    problem = ProblemDetails(
        type=error_type,
        title=title,
        status=exc.status_code,
        detail=exc.detail,
        instance=str(request.url.path),
        request_id=request_id,
    )

    # Log error
    logger.warning(
        f"{title}: {exc.detail}",
        extra={
            "extra_fields": {
                "status_code": exc.status_code,
                "request_id": request_id,
                "path": str(request.url.path),
            }
        },
    )

    return JSONResponse(
        status_code=exc.status_code,
        content=problem.model_dump(exclude_none=True),
        headers={
            "Content-Type": "application/problem+json",
            "X-Request-ID": request_id or "unknown",
        },
    )


async def validation_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle Pydantic validation errors with RFC 7807 format.

    Args:
        request: FastAPI request
        exc: Pydantic ValidationError

    Returns:
        JSONResponse: RFC 7807 formatted error response
    """
    from pydantic import ValidationError as PydanticValidationError

    # Get request ID
    request_id = getattr(request.state, "request_id", None)

    # Extract validation errors
    errors = {}
    if isinstance(exc, PydanticValidationError):
        for error in exc.errors():
            field = ".".join(str(loc) for loc in error["loc"])
            errors[field] = error["msg"]

    # Create problem details
    problem = ProblemDetails(
        type="https://lazy-bird.dev/errors/validation-error",
        title="Validation Error",
        status=status.HTTP_422_UNPROCESSABLE_ENTITY,
        detail="Request validation failed",
        instance=str(request.url.path),
        request_id=request_id,
        errors=errors,
    )

    # Log error
    logger.warning(
        "Validation error",
        extra={
            "extra_fields": {
                "request_id": request_id,
                "path": str(request.url.path),
                "errors": errors,
            }
        },
    )

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=problem.model_dump(exclude_none=True),
        headers={
            "Content-Type": "application/problem+json",
            "X-Request-ID": request_id or "unknown",
        },
    )


def register_exception_handlers(app) -> None:
    """Register all exception handlers with FastAPI app.

    Args:
        app: FastAPI application instance

    Example:
        >>> from fastapi import FastAPI
        >>> app = FastAPI()
        >>> register_exception_handlers(app)
    """
    from pydantic import ValidationError as PydanticValidationError

    # Register custom exception handlers
    app.add_exception_handler(LazyBirdException, lazy_bird_exception_handler)
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(PydanticValidationError, validation_exception_handler)

    logger.info("Exception handlers registered")
