"""Unit tests for lazy_bird.api.middleware module.

Tests CORS setup, request ID, logging, error handling, security headers,
and rate limiting middleware.
"""

import time
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest
from fastapi import FastAPI, Request, status
from fastapi.testclient import TestClient

from lazy_bird.api.middleware import (
    ErrorHandlingMiddleware,
    RateLimitMiddleware,
    RequestIDMiddleware,
    RequestLoggingMiddleware,
    SecurityHeadersMiddleware,
    setup_cors,
    setup_middleware,
)


@pytest.fixture
def simple_app():
    """Create a simple FastAPI app for testing middleware."""
    app = FastAPI()

    @app.get("/test")
    async def test_endpoint():
        return {"status": "ok"}

    @app.get("/error")
    async def error_endpoint():
        raise RuntimeError("Test error")

    @app.get("/slow")
    async def slow_endpoint():
        return {"status": "slow"}

    return app


class TestSetupCors:
    """Test setup_cors function."""

    @patch("lazy_bird.api.middleware.settings")
    def test_setup_cors_adds_middleware(self, mock_settings):
        """Test that setup_cors adds CORS middleware to app."""
        mock_settings.CORS_ORIGINS = ["http://localhost:3000"]
        app = FastAPI()

        setup_cors(app)

        # The middleware stack should have the CORS middleware
        # We verify indirectly by checking the app user middleware
        assert len(app.user_middleware) > 0


class TestRequestIDMiddleware:
    """Test RequestIDMiddleware."""

    def test_adds_request_id_header(self, simple_app):
        """Test that middleware adds X-Request-ID to response."""
        simple_app.add_middleware(RequestIDMiddleware)
        client = TestClient(simple_app)

        response = client.get("/test")

        assert response.status_code == 200
        assert "X-Request-ID" in response.headers
        assert "X-Correlation-ID" in response.headers

    def test_uses_client_provided_request_id(self, simple_app):
        """Test that middleware uses client-provided X-Request-ID."""
        simple_app.add_middleware(RequestIDMiddleware)
        client = TestClient(simple_app)

        response = client.get("/test", headers={"X-Request-ID": "custom-id-123"})

        assert response.headers["X-Request-ID"] == "custom-id-123"
        assert response.headers["X-Correlation-ID"] == "custom-id-123"

    def test_generates_uuid_when_no_id_provided(self, simple_app):
        """Test that middleware generates UUID when no ID provided."""
        simple_app.add_middleware(RequestIDMiddleware)
        client = TestClient(simple_app)

        response = client.get("/test")

        request_id = response.headers["X-Request-ID"]
        # UUID format check (8-4-4-4-12 hex chars)
        parts = request_id.split("-")
        assert len(parts) == 5


class TestRequestLoggingMiddleware:
    """Test RequestLoggingMiddleware."""

    def test_logs_request_and_response(self, simple_app):
        """Test that middleware logs request info."""
        simple_app.add_middleware(RequestLoggingMiddleware)
        client = TestClient(simple_app)

        with patch("lazy_bird.api.middleware.log_with_context") as mock_log:
            response = client.get("/test")

        assert response.status_code == 200
        # Should have been called at least twice (request + response)
        assert mock_log.call_count >= 2

    def test_adds_response_time_header(self, simple_app):
        """Test that middleware adds X-Response-Time header."""
        simple_app.add_middleware(RequestLoggingMiddleware)
        client = TestClient(simple_app)

        response = client.get("/test")

        assert "X-Response-Time" in response.headers
        assert response.headers["X-Response-Time"].endswith("ms")

    def test_logs_error_on_exception(self, simple_app):
        """Test that middleware logs errors for exceptions."""
        simple_app.add_middleware(RequestLoggingMiddleware)
        client = TestClient(simple_app, raise_server_exceptions=False)

        with patch("lazy_bird.api.middleware.log_with_context") as mock_log:
            response = client.get("/error")

        # Should have logged an error
        error_calls = [call for call in mock_log.call_args_list if call[0][1] == 40]  # ERROR level
        assert len(error_calls) >= 1


class TestErrorHandlingMiddleware:
    """Test ErrorHandlingMiddleware."""

    @patch("lazy_bird.api.middleware.settings")
    def test_catches_unhandled_exceptions_debug(self, mock_settings, simple_app):
        """Test that middleware catches exceptions in debug mode."""
        mock_settings.DEBUG = True
        simple_app.add_middleware(ErrorHandlingMiddleware)
        client = TestClient(simple_app, raise_server_exceptions=False)

        response = client.get("/error")

        assert response.status_code == 500
        data = response.json()
        assert "error" in data
        assert data["error"] == "RuntimeError"
        assert "Test error" in data["message"]

    @patch("lazy_bird.api.middleware.settings")
    def test_catches_unhandled_exceptions_production(self, mock_settings, simple_app):
        """Test that middleware returns generic error in production."""
        mock_settings.DEBUG = False
        simple_app.add_middleware(ErrorHandlingMiddleware)
        client = TestClient(simple_app, raise_server_exceptions=False)

        response = client.get("/error")

        assert response.status_code == 500
        data = response.json()
        assert data["error"] == "Internal Server Error"
        assert data["message"] == "An unexpected error occurred"

    def test_passes_through_successful_requests(self, simple_app):
        """Test that middleware passes through successful requests."""
        simple_app.add_middleware(ErrorHandlingMiddleware)
        client = TestClient(simple_app)

        response = client.get("/test")

        assert response.status_code == 200
        assert response.json() == {"status": "ok"}

    @patch("lazy_bird.api.middleware.settings")
    def test_includes_request_id_in_error(self, mock_settings, simple_app):
        """Test error response includes request ID header."""
        mock_settings.DEBUG = True
        simple_app.add_middleware(ErrorHandlingMiddleware)
        client = TestClient(simple_app, raise_server_exceptions=False)

        response = client.get("/error")

        assert "X-Request-ID" in response.headers


class TestSecurityHeadersMiddleware:
    """Test SecurityHeadersMiddleware."""

    @patch("lazy_bird.api.middleware.settings")
    def test_adds_security_headers(self, mock_settings, simple_app):
        """Test that middleware adds security headers."""
        mock_settings.DEBUG = True
        simple_app.add_middleware(SecurityHeadersMiddleware)
        client = TestClient(simple_app)

        response = client.get("/test")

        assert response.headers["X-Content-Type-Options"] == "nosniff"
        assert response.headers["X-Frame-Options"] == "DENY"
        assert response.headers["X-XSS-Protection"] == "1; mode=block"

    @patch("lazy_bird.api.middleware.settings")
    def test_adds_hsts_in_production(self, mock_settings, simple_app):
        """Test that HSTS header is added in production mode."""
        mock_settings.DEBUG = False
        simple_app.add_middleware(SecurityHeadersMiddleware)
        client = TestClient(simple_app)

        response = client.get("/test")

        assert "Strict-Transport-Security" in response.headers

    @patch("lazy_bird.api.middleware.settings")
    def test_no_hsts_in_debug(self, mock_settings, simple_app):
        """Test that HSTS header is NOT added in debug mode."""
        mock_settings.DEBUG = True
        simple_app.add_middleware(SecurityHeadersMiddleware)
        client = TestClient(simple_app)

        response = client.get("/test")

        assert "Strict-Transport-Security" not in response.headers


class TestRateLimitMiddleware:
    """Test RateLimitMiddleware."""

    def test_init_defaults(self):
        """Test RateLimitMiddleware initialization."""
        app = FastAPI()
        middleware = RateLimitMiddleware(app, requests_per_minute=100)

        assert middleware.requests_per_minute == 100
        assert middleware.window_seconds == 60

    @patch("lazy_bird.api.middleware.settings")
    def test_allows_request_under_limit(self, mock_settings, simple_app):
        """Test that requests under the limit are allowed."""
        mock_settings.DEBUG = True
        simple_app.add_middleware(RateLimitMiddleware, requests_per_minute=100)

        mock_redis = MagicMock()
        mock_redis.get.return_value = "5"  # 5 requests so far
        mock_pipe = MagicMock()
        mock_redis.pipeline.return_value = mock_pipe

        with patch("lazy_bird.core.redis.get_redis", return_value=mock_redis):
            client = TestClient(simple_app)
            response = client.get("/test")

        assert response.status_code == 200
        assert "X-RateLimit-Limit" in response.headers

    @patch("lazy_bird.api.middleware.settings")
    def test_blocks_request_over_limit(self, mock_settings, simple_app):
        """Test that requests over the limit are blocked."""
        mock_settings.DEBUG = True
        simple_app.add_middleware(RateLimitMiddleware, requests_per_minute=10)

        mock_redis = MagicMock()
        mock_redis.get.return_value = "10"  # At limit
        mock_redis.pipeline.return_value = MagicMock()

        with patch("lazy_bird.core.redis.get_redis", return_value=mock_redis):
            client = TestClient(simple_app)
            response = client.get("/test")

        assert response.status_code == 429
        data = response.json()
        assert "Rate limit exceeded" in data["error"]
        assert "Retry-After" in response.headers

    @patch("lazy_bird.api.middleware.settings")
    def test_fails_open_when_redis_unavailable(self, mock_settings, simple_app):
        """Test that rate limiting fails open when Redis is unavailable."""
        mock_settings.DEBUG = True
        simple_app.add_middleware(RateLimitMiddleware, requests_per_minute=10)

        with patch(
            "lazy_bird.core.redis.get_redis",
            side_effect=Exception("Redis unavailable"),
        ):
            client = TestClient(simple_app)
            response = client.get("/test")

        # Should still allow the request
        assert response.status_code == 200

    @patch("lazy_bird.api.middleware.settings")
    def test_sets_expiry_on_first_request(self, mock_settings, simple_app):
        """Test that expiry is set on first request in window."""
        mock_settings.DEBUG = True
        simple_app.add_middleware(RateLimitMiddleware, requests_per_minute=100)

        mock_redis = MagicMock()
        mock_redis.get.return_value = None  # No previous requests
        mock_pipe = MagicMock()
        mock_redis.pipeline.return_value = mock_pipe

        with patch("lazy_bird.core.redis.get_redis", return_value=mock_redis):
            client = TestClient(simple_app)
            response = client.get("/test")

        assert response.status_code == 200
        # Pipeline should have been called with incr + expire
        mock_pipe.incr.assert_called_once()
        mock_pipe.expire.assert_called_once()


class TestSetupMiddleware:
    """Test setup_middleware function."""

    @patch("lazy_bird.api.middleware.settings")
    def test_setup_middleware_configures_all(self, mock_settings):
        """Test that setup_middleware configures all middleware."""
        mock_settings.CORS_ORIGINS = ["http://localhost:3000"]
        mock_settings.RATE_LIMIT_PER_MINUTE = 60
        app = FastAPI()

        setup_middleware(app)

        # Should have multiple middleware registered
        assert len(app.user_middleware) >= 4
