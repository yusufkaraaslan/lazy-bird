"""Unit tests for custom exception classes.

Tests RFC 7807 Problem Details error responses.
"""

import pytest
from fastapi import status

from lazy_bird.api.exceptions import (
    AuthenticationError,
    AuthorizationError,
    ResourceConflictError,
    ResourceNotFoundError,
    ValidationError,
)


class TestResourceNotFoundError:
    """Test ResourceNotFoundError (404) exception."""

    def test_basic_initialization(self):
        """Test basic exception initialization."""
        error = ResourceNotFoundError(
            resource_type="Project",
            resource_id="123",
        )

        assert error.status_code == status.HTTP_404_NOT_FOUND
        assert error.resource_type == "Project"
        assert error.resource_id == "123"
        assert "Project" in error.detail
        assert "123" in error.detail

    def test_custom_detail_message(self):
        """Test exception with custom detail message."""
        error = ResourceNotFoundError(
            resource_type="Project",
            resource_id="abc-123",
            detail="Custom error message",
        )

        assert error.detail == "Custom error message"

    def test_headers_property(self):
        """Test that headers property returns correct format."""
        error = ResourceNotFoundError(
            resource_type="ApiKey",
            resource_id="key-456",
        )

        headers = error.headers
        assert headers["Content-Type"] == "application/problem+json"

    def test_to_problem_details(self):
        """Test conversion to RFC 7807 Problem Details format."""
        error = ResourceNotFoundError(
            resource_type="TaskRun",
            resource_id="task-789",
        )

        problem_details = error.to_problem_details()

        assert problem_details["type"] == "about:blank"
        assert problem_details["title"] == "Not Found"
        assert problem_details["status"] == 404
        assert problem_details["detail"] == error.detail
        assert "resource_type" in problem_details
        assert problem_details["resource_type"] == "TaskRun"
        assert "resource_id" in problem_details
        assert problem_details["resource_id"] == "task-789"


class TestResourceConflictError:
    """Test ResourceConflictError (409) exception."""

    def test_basic_initialization(self):
        """Test basic exception initialization."""
        error = ResourceConflictError(
            detail="Resource already exists",
            conflict_field="name",
        )

        assert error.status_code == status.HTTP_409_CONFLICT
        assert error.detail == "Resource already exists"
        assert error.conflict_field == "name"

    def test_with_conflict_value(self):
        """Test exception with conflict_value."""
        error = ResourceConflictError(
            detail="Name already taken",
            conflict_field="name",
            conflict_value="my-project",
        )

        assert error.conflict_value == "my-project"

    def test_to_problem_details(self):
        """Test conversion to RFC 7807 Problem Details format."""
        error = ResourceConflictError(
            detail="Duplicate slug",
            conflict_field="slug",
            conflict_value="duplicate-slug",
        )

        problem_details = error.to_problem_details()

        assert problem_details["type"] == "about:blank"
        assert problem_details["title"] == "Conflict"
        assert problem_details["status"] == 409
        assert problem_details["detail"] == "Duplicate slug"
        assert problem_details["conflict_field"] == "slug"
        assert problem_details["conflict_value"] == "duplicate-slug"

    def test_without_conflict_value(self):
        """Test that conflict_value is optional."""
        error = ResourceConflictError(
            detail="Invalid state transition",
            conflict_field="status",
        )

        problem_details = error.to_problem_details()
        assert "conflict_value" not in problem_details


class TestAuthenticationError:
    """Test AuthenticationError (401) exception."""

    def test_basic_initialization(self):
        """Test basic exception initialization."""
        error = AuthenticationError(detail="Invalid API key")

        assert error.status_code == status.HTTP_401_UNAUTHORIZED
        assert error.detail == "Invalid API key"

    def test_default_detail_message(self):
        """Test default detail message."""
        error = AuthenticationError()

        assert "authentication" in error.detail.lower()

    def test_www_authenticate_header(self):
        """Test WWW-Authenticate header."""
        error = AuthenticationError()

        headers = error.headers
        assert "WWW-Authenticate" in headers
        assert headers["WWW-Authenticate"] == 'Bearer realm="api"'

    def test_to_problem_details(self):
        """Test conversion to RFC 7807 Problem Details format."""
        error = AuthenticationError(detail="Token expired")

        problem_details = error.to_problem_details()

        assert problem_details["type"] == "about:blank"
        assert problem_details["title"] == "Unauthorized"
        assert problem_details["status"] == 401
        assert problem_details["detail"] == "Token expired"


class TestAuthorizationError:
    """Test AuthorizationError (403) exception."""

    def test_basic_initialization(self):
        """Test basic exception initialization."""
        error = AuthorizationError(
            detail="Insufficient permissions",
            required_scope="admin",
        )

        assert error.status_code == status.HTTP_403_FORBIDDEN
        assert error.detail == "Insufficient permissions"
        assert error.required_scope == "admin"

    def test_default_detail_message(self):
        """Test default detail message."""
        error = AuthorizationError()

        assert "permission" in error.detail.lower() or "forbidden" in error.detail.lower()

    def test_to_problem_details(self):
        """Test conversion to RFC 7807 Problem Details format."""
        error = AuthorizationError(
            detail="Admin access required",
            required_scope="admin",
            user_scopes=["read", "write"],
        )

        problem_details = error.to_problem_details()

        assert problem_details["type"] == "about:blank"
        assert problem_details["title"] == "Forbidden"
        assert problem_details["status"] == 403
        assert problem_details["detail"] == "Admin access required"
        assert problem_details["required_scope"] == "admin"
        assert problem_details["user_scopes"] == ["read", "write"]


class TestValidationError:
    """Test ValidationError (422) exception."""

    def test_basic_initialization(self):
        """Test basic exception initialization."""
        error = ValidationError(
            detail="Invalid input data",
            field="email",
            reason="Invalid email format",
        )

        assert error.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        assert error.detail == "Invalid input data"
        assert error.field == "email"
        assert error.reason == "Invalid email format"

    def test_to_problem_details(self):
        """Test conversion to RFC 7807 Problem Details format."""
        error = ValidationError(
            detail="Validation failed",
            field="max_tokens",
            reason="Must be between 1 and 100000",
        )

        problem_details = error.to_problem_details()

        assert problem_details["type"] == "about:blank"
        assert problem_details["title"] == "Unprocessable Entity"
        assert problem_details["status"] == 422
        assert problem_details["detail"] == "Validation failed"
        assert problem_details["field"] == "max_tokens"
        assert problem_details["reason"] == "Must be between 1 and 100000"


class TestExceptionHeaders:
    """Test exception headers and content types."""

    def test_all_exceptions_have_problem_json_header(self):
        """Test that all exceptions return application/problem+json content type."""
        exceptions = [
            ResourceNotFoundError("Project", "123"),
            ResourceConflictError("Conflict", "name"),
            AuthenticationError(),
            AuthorizationError(),
            ValidationError("Error", "field"),
        ]

        for exception in exceptions:
            assert exception.headers["Content-Type"] == "application/problem+json"

    def test_authentication_error_has_www_authenticate(self):
        """Test that authentication error includes WWW-Authenticate header."""
        error = AuthenticationError()

        assert "WWW-Authenticate" in error.headers
        assert error.headers["WWW-Authenticate"] == 'Bearer realm="api"'


class TestExceptionInheritance:
    """Test exception class inheritance."""

    def test_all_inherit_from_base_exception(self):
        """Test that all custom exceptions inherit from Exception."""
        from lazy_bird.api.exceptions import LazyBirdException

        exceptions = [
            ResourceNotFoundError("Project", "123"),
            ResourceConflictError("Conflict", "name"),
            AuthenticationError(),
            AuthorizationError(),
            ValidationError("Error", "field"),
        ]

        for exception in exceptions:
            assert isinstance(exception, LazyBirdException)
            assert isinstance(exception, Exception)

    def test_exceptions_can_be_raised_and_caught(self):
        """Test that exceptions can be raised and caught."""
        with pytest.raises(ResourceNotFoundError) as exc_info:
            raise ResourceNotFoundError("Project", "123")

        assert exc_info.value.status_code == 404
        assert "Project" in exc_info.value.detail

        with pytest.raises(ResourceConflictError) as exc_info:
            raise ResourceConflictError("Conflict", "name")

        assert exc_info.value.status_code == 409
