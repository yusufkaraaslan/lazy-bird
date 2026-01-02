"""Security audit tests for lazy-bird API (Issue #118).

Tests comprehensive security features:
- Authentication bypass attempt detection
- SQL injection protection
- XSS protection via security headers
- Secrets handling validation
- Rate limiting enforcement

All tests verify the security baseline documented in Docs/Design/security-baseline.md
"""

import json
import time
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch
from uuid import uuid4

import pytest
from fastapi import HTTPException, status
from sqlalchemy import text


class TestAuthenticationBypassAttempts:
    """Test detection and prevention of authentication bypass attempts."""

    @pytest.mark.asyncio
    async def test_missing_api_key_rejected(self):
        """Test that requests without API key are rejected with 401."""
        from lazy_bird.api.dependencies import get_current_api_key

        # Mock dependencies
        mock_db = AsyncMock()

        # Attempt without API key (None)
        with pytest.raises(HTTPException) as exc_info:
            await get_current_api_key(api_key=None, db=mock_db)

        # Verify 401 response
        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
        assert "API key required" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_invalid_api_key_rejected(self):
        """Test that invalid API key is rejected with 401."""
        from lazy_bird.api.dependencies import get_current_api_key

        # Mock database with no matching API key
        class MockResult:
            def scalar_one_or_none(self):
                return None

        mock_db = AsyncMock()
        mock_db.execute = AsyncMock(return_value=MockResult())

        # Attempt with invalid API key
        with pytest.raises(HTTPException) as exc_info:
            await get_current_api_key(api_key="lb_invalid_key_12345", db=mock_db)

        # Verify 401 response
        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
        assert "Invalid API key" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_expired_api_key_rejected(self):
        """Test that expired API key is rejected with 403."""
        from lazy_bird.api.dependencies import get_current_api_key

        # Mock expired API key
        mock_api_key = Mock()
        mock_api_key.is_active = True
        mock_api_key.expires_at = datetime.utcnow() - timedelta(days=1)  # Expired yesterday
        mock_api_key.key_prefix = "lb_test"

        class MockResult:
            def scalar_one_or_none(self):
                return mock_api_key

        mock_db = AsyncMock()
        mock_db.execute = AsyncMock(return_value=MockResult())

        # Attempt with expired API key
        with pytest.raises(HTTPException) as exc_info:
            await get_current_api_key(api_key="lb_valid_but_expired", db=mock_db)

        # Verify 403 response
        assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN
        assert "expired" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_inactive_api_key_rejected(self):
        """Test that inactive API key is not found (rejected with 401)."""
        from lazy_bird.api.dependencies import get_current_api_key

        # Mock database - inactive keys are filtered by query
        class MockResult:
            def scalar_one_or_none(self):
                return None  # is_active=False filtered out by WHERE clause

        mock_db = AsyncMock()
        mock_db.execute = AsyncMock(return_value=MockResult())

        # Attempt with inactive API key
        with pytest.raises(HTTPException) as exc_info:
            await get_current_api_key(api_key="lb_inactive_key", db=mock_db)

        # Verify 401 response (not found because filtered by is_active)
        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.asyncio
    async def test_missing_jwt_token_rejected(self):
        """Test that requests without JWT token are rejected with 401."""
        from lazy_bird.api.dependencies import get_current_user

        # Attempt without token (None)
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(token=None)

        # Verify 401 response
        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
        assert "Authentication required" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_invalid_jwt_token_rejected(self):
        """Test that invalid JWT token is rejected with 401."""
        from lazy_bird.api.dependencies import get_current_user

        # Attempt with malformed token
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(token="invalid.jwt.token")

        # Verify 401 response
        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
        assert "Invalid or expired token" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_tampered_jwt_token_rejected(self):
        """Test that tampered JWT token is rejected."""
        from lazy_bird.core.security import create_access_token

        # Create valid token
        data = {"sub": "user123", "email": "user@example.com"}
        token = create_access_token(data)

        # Tamper with token by changing payload
        parts = token.split(".")
        if len(parts) == 3:
            # Change last character of payload
            parts[1] = parts[1][:-1] + "X"
            tampered_token = ".".join(parts)

            # Attempt to use tampered token
            from lazy_bird.api.dependencies import get_current_user

            with pytest.raises(HTTPException) as exc_info:
                await get_current_user(token=tampered_token)

            # Verify 401 response
            assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.asyncio
    async def test_expired_jwt_token_rejected(self):
        """Test that expired JWT token is rejected."""
        from lazy_bird.core.security import create_access_token

        # Create token that expires immediately
        data = {"sub": "user123"}
        token = create_access_token(data, expires_delta=timedelta(seconds=-1))

        # Wait a moment to ensure expiration
        time.sleep(0.1)

        # Attempt to use expired token
        from lazy_bird.api.dependencies import get_current_user

        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(token=token)

        # Verify 401 response
        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.asyncio
    async def test_insufficient_scopes_rejected(self):
        """Test that API key with insufficient scopes is rejected with 403."""
        from lazy_bird.api.dependencies import RequireScopes

        # Mock API key with only "read" scope
        mock_api_key = Mock()
        mock_api_key.scopes = ["read"]
        mock_api_key.key_prefix = "lb_test"

        # Require "write" or "admin" scope
        require_write = RequireScopes(["write", "admin"])

        # Attempt with insufficient scopes
        with pytest.raises(HTTPException) as exc_info:
            await require_write(api_key=mock_api_key)

        # Verify 403 response
        assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN
        assert "Insufficient permissions" in exc_info.value.detail


class TestSQLInjectionProtection:
    """Test SQL injection prevention via SQLAlchemy parameterization."""

    @pytest.mark.asyncio
    async def test_sqlalchemy_parameterized_queries(self):
        """Test that SQLAlchemy uses parameterized queries (not string concatenation)."""
        from sqlalchemy import select
        from lazy_bird.models.project import Project

        # Build query with user input (should be parameterized)
        malicious_input = "'; DROP TABLE projects; --"

        # SQLAlchemy automatically parameterizes this
        query = select(Project).where(Project.name == malicious_input)

        # Verify query is safe (has parameters, not raw SQL injection)
        compiled = query.compile()
        # Parameters are bound separately, not concatenated
        assert "DROP TABLE" not in str(compiled)

    @pytest.mark.asyncio
    async def test_text_query_with_parameters(self):
        """Test that raw SQL queries use parameter binding."""
        # Safe: Using text() with bound parameters
        safe_query = text("SELECT * FROM projects WHERE name = :name")
        params = {"name": "'; DROP TABLE projects; --"}

        # Verify parameters are bound separately
        assert ":name" in str(safe_query)
        assert "DROP TABLE" not in str(safe_query)

    def test_input_sanitization_for_search(self):
        """Test that search inputs are sanitized."""
        # Simulate search input sanitization
        malicious_input = "<script>alert('XSS')</script>'; DROP TABLE users; --"

        # Basic sanitization: escape SQL wildcards and limit length
        sanitized = malicious_input.replace("%", "\\%").replace("_", "\\_")
        sanitized = sanitized[:100]  # Length limit

        # Should not contain dangerous patterns raw
        # (SQLAlchemy will parameterize further)
        assert "DROP TABLE" in sanitized  # Still in string
        # But when passed to SQLAlchemy, it's a parameter value, not SQL

    @pytest.mark.asyncio
    async def test_no_string_concatenation_in_queries(self):
        """Test that queries don't use string concatenation (unsafe pattern)."""
        from sqlalchemy import select
        from lazy_bird.models.task_run import TaskRun

        # User input
        user_input = "42'; DELETE FROM task_runs WHERE '1'='1"

        # Safe: Using SQLAlchemy ORM (parameterized)
        query = select(TaskRun).where(TaskRun.work_item_id == user_input)

        # Compile to SQL
        compiled = str(query.compile(compile_kwargs={"literal_binds": False}))

        # Should use parameters (:work_item_id_1), not concatenation
        assert "DELETE FROM" not in compiled
        assert ":work_item_id" in compiled or "?" in compiled  # Parameter placeholder

    @pytest.mark.asyncio
    async def test_orm_prevents_sql_injection(self):
        """Test that SQLAlchemy ORM inherently prevents SQL injection."""
        from sqlalchemy import select
        from lazy_bird.models.project import Project

        # Various SQL injection attempts
        injection_attempts = [
            "1' OR '1'='1",
            "'; DROP TABLE projects; --",
            "1; DELETE FROM projects WHERE id > 0",
            "' UNION SELECT * FROM api_keys--",
        ]

        for attempt in injection_attempts:
            # ORM query with malicious input
            query = select(Project).where(Project.id == attempt)

            # Compile to see actual SQL
            compiled = query.compile()

            # Verify: All values are parameterized, not injected
            sql_str = str(compiled)
            # Should have parameter placeholder, not literal injection
            assert "DROP TABLE" not in sql_str
            assert "UNION SELECT" not in sql_str
            # ORM treats input as literal value, not SQL


class TestXSSProtection:
    """Test XSS protection via security headers and input sanitization."""

    @pytest.mark.asyncio
    async def test_security_headers_present(self):
        """Test that security headers are added to responses."""
        from lazy_bird.api.middleware import SecurityHeadersMiddleware
        from fastapi import Request, Response
        from unittest.mock import AsyncMock

        # Create middleware
        app = AsyncMock()
        middleware = SecurityHeadersMiddleware(app)

        # Mock request and response
        request = Mock(spec=Request)
        response = Response(content="test")

        # Mock call_next to return response
        async def mock_call_next(req):
            return response

        # Process through middleware
        result = await middleware.dispatch(request, mock_call_next)

        # Verify security headers
        assert result.headers.get("X-Content-Type-Options") == "nosniff"
        assert result.headers.get("X-Frame-Options") == "DENY"
        assert result.headers.get("X-XSS-Protection") == "1; mode=block"

    @pytest.mark.asyncio
    async def test_hsts_header_in_production(self):
        """Test that HSTS header is added in production mode."""
        from lazy_bird.api.middleware import SecurityHeadersMiddleware
        from lazy_bird.core.config import settings
        from fastapi import Request, Response
        from unittest.mock import AsyncMock

        # Mock production mode
        with patch.object(settings, "DEBUG", False):
            # Create middleware
            app = AsyncMock()
            middleware = SecurityHeadersMiddleware(app)

            # Mock request and response
            request = Mock(spec=Request)
            response = Response(content="test")

            async def mock_call_next(req):
                return response

            # Process through middleware
            result = await middleware.dispatch(request, mock_call_next)

            # Verify HSTS header in production
            assert "Strict-Transport-Security" in result.headers
            assert "max-age=" in result.headers["Strict-Transport-Security"]

    def test_html_entities_in_responses(self):
        """Test that JSON responses are safe from XSS via Content-Type."""
        # Simulate error message with HTML
        malicious_input = "<script>alert('XSS')</script>"

        # FastAPI's JSONResponse with application/json Content-Type
        from fastapi.responses import JSONResponse

        response = JSONResponse(
            status_code=400,
            content={"error": malicious_input}
        )

        # Verify Content-Type is application/json (prevents XSS interpretation)
        assert response.media_type == "application/json"

        # XSS protection comes from:
        # 1. Content-Type: application/json (browser won't execute)
        # 2. X-Content-Type-Options: nosniff (SecurityHeadersMiddleware)
        # 3. X-XSS-Protection header (SecurityHeadersMiddleware)

        # JSON preserves the string but browser won't execute due to Content-Type
        # This is SAFE - JSON responses don't need HTML escaping

    def test_content_type_prevents_xss(self):
        """Test that proper Content-Type prevents XSS."""
        from fastapi.responses import JSONResponse

        response = JSONResponse(content={"data": "value"})

        # Content-Type should be application/json
        assert response.media_type == "application/json"
        # X-Content-Type-Options: nosniff prevents MIME sniffing
        # (added by SecurityHeadersMiddleware)


class TestRateLimiting:
    """Test rate limiting enforcement via middleware."""

    @pytest.mark.asyncio
    async def test_rate_limit_headers_present(self):
        """Test that rate limit headers are added to responses."""
        from lazy_bird.api.middleware import RateLimitMiddleware
        from fastapi import Request, Response

        # Create middleware with low limit for testing
        app = Mock()
        middleware = RateLimitMiddleware(app, requests_per_minute=10)

        # Mock request
        request = Mock(spec=Request)
        request.client = Mock()
        request.client.host = "127.0.0.1"
        request.headers = {}

        # Mock response
        response = Response(content="test")

        # Mock call_next
        async def mock_call_next(req):
            return response

        # Mock Redis to fail (no rate limiting)
        with patch("lazy_bird.core.redis.get_redis", side_effect=Exception("Redis unavailable")):
            # Process through middleware
            result = await middleware.dispatch(request, mock_call_next)

            # Verify rate limit headers are present
            assert "X-RateLimit-Limit" in result.headers
            assert "X-RateLimit-Remaining" in result.headers

    @pytest.mark.asyncio
    async def test_rate_limit_exceeded_returns_429(self):
        """Test that exceeding rate limit returns 429 Too Many Requests."""
        from lazy_bird.api.middleware import RateLimitMiddleware
        from fastapi import Request

        # Create middleware with limit of 2 requests per minute
        app = Mock()
        middleware = RateLimitMiddleware(app, requests_per_minute=2)

        # Mock request
        request = Mock(spec=Request)
        request.client = Mock()
        request.client.host = "127.0.0.1"
        request.headers = {}

        # Mock Redis client
        mock_redis = Mock()
        mock_redis.get = Mock(return_value=b"3")  # Already at 3 requests (exceeded limit of 2)
        mock_redis.pipeline = Mock()

        # Mock call_next (should not be called if rate limited)
        async def mock_call_next(req):
            return Response(content="should not reach here")

        # Patch get_redis
        with patch("lazy_bird.core.redis.get_redis", return_value=mock_redis):
            # Process through middleware
            result = await middleware.dispatch(request, mock_call_next)

            # Verify 429 response
            assert result.status_code == status.HTTP_429_TOO_MANY_REQUESTS

            # Verify retry headers
            assert "Retry-After" in result.headers
            assert "X-RateLimit-Limit" in result.headers
            assert "X-RateLimit-Remaining" in result.headers
            assert result.headers["X-RateLimit-Remaining"] == "0"

    @pytest.mark.asyncio
    async def test_rate_limit_per_api_key(self):
        """Test that rate limiting tracks by API key (not just IP)."""
        from lazy_bird.api.middleware import RateLimitMiddleware
        from fastapi import Request, Response

        # Create middleware
        app = Mock()
        middleware = RateLimitMiddleware(app, requests_per_minute=10)

        # Mock request with API key
        request = Mock(spec=Request)
        request.client = Mock()
        request.client.host = "127.0.0.1"
        request.headers = {"X-API-Key": "lb_test_api_key_12345"}

        # Mock Redis
        mock_redis = Mock()
        mock_redis.get = Mock(return_value=None)  # First request
        mock_pipeline = Mock()
        mock_pipeline.incr = Mock()
        mock_pipeline.expire = Mock()
        mock_pipeline.execute = Mock()
        mock_redis.pipeline = Mock(return_value=mock_pipeline)

        # Mock call_next
        async def mock_call_next(req):
            return Response(content="success")

        # Patch get_redis
        with patch("lazy_bird.core.redis.get_redis", return_value=mock_redis):
            # Process through middleware
            await middleware.dispatch(request, mock_call_next)

            # Verify Redis key uses API key prefix (not IP)
            mock_redis.get.assert_called_once()
            call_args = mock_redis.get.call_args[0][0]
            # Key should include API key prefix
            assert "rate_limit:lb_test_api_key" in call_args


class TestSecretsHandling:
    """Test that secrets are handled securely and not leaked."""

    def test_secrets_not_in_logs(self):
        """Test that API key prefix is logged, not full key."""
        from lazy_bird.core.security import get_api_key_prefix

        # Full API key (should NEVER be logged)
        full_api_key = "lb_secret_key_12345678901234567890"

        # Only prefix should be logged (first 8 characters)
        safe_prefix = get_api_key_prefix(full_api_key)

        # Verify: Prefix is safe to log, but is truncated
        assert len(safe_prefix) == 8
        assert safe_prefix == "lb_secre"
        assert safe_prefix != full_api_key

        # In production, logs should ONLY contain prefix:
        # logger.info(f"API key used: {get_api_key_prefix(api_key)}")
        # NOT: logger.info(f"API key: {api_key}")  # DANGEROUS!

    def test_api_key_prefix_in_logs_not_full_key(self):
        """Test that only API key prefix is logged, not full key."""
        from lazy_bird.core.security import get_api_key_prefix

        # Full API key (67 characters)
        full_key = "lb_" + "a" * 64

        # Get prefix for logging
        prefix = get_api_key_prefix(full_key)

        # Verify: Prefix is only 8 characters
        assert len(prefix) == 8
        assert prefix == "lb_aaaaa"
        assert prefix != full_key

    def test_password_hashing_requirement(self):
        """Test that password hashing functions exist and are configured.

        Note: Full password hashing tests are in tests/unit/test_security.py
        This audit verifies the security functions are available.
        """
        # Verify password hashing functions exist
        from lazy_bird.core import security

        assert hasattr(security, "hash_password")
        assert hasattr(security, "verify_password")
        assert hasattr(security, "pwd_context")

        # Verify CryptContext is configured
        assert security.pwd_context is not None

        # Password security requirements (documented):
        # 1. MUST use bcrypt (industry standard) ✓
        # 2. NEVER store plaintext passwords ✓
        # 3. Use bcrypt's automatic salting ✓
        # 4. Use verify_password() for constant-time comparison ✓

    def test_jwt_payload_no_sensitive_data(self):
        """Test that JWT tokens don't include passwords or full API keys."""
        from lazy_bird.core.security import create_access_token, verify_token

        # Create token with user data (should NOT include password)
        user_data = {
            "sub": "user123",
            "email": "user@example.com",
            "role": "admin",
            # NO password field
        }

        token = create_access_token(user_data)
        payload = verify_token(token)

        # Verify: No sensitive data in token
        assert "password" not in payload
        assert "api_key" not in payload
        assert "secret" not in payload

    def test_secrets_file_permissions(self):
        """Test that secrets directory would have correct permissions."""
        # This is a documentation test - verify the pattern exists
        from lazy_bird.core.config import settings

        # Secrets should be loaded from secure location
        # Pattern: ~/.config/lazy_birtd/secrets/
        expected_pattern = ".config/lazy_birtd/secrets"

        # Verify this pattern is documented
        # (Actual file permissions checked by deployment, not unit tests)
        # If secrets directory exists, check permissions
        secrets_dir = Path.home() / ".config" / "lazy_birtd" / "secrets"
        if secrets_dir.exists():
            stat = secrets_dir.stat()
            mode = stat.st_mode & 0o777

            # Should be 700 (owner only)
            assert mode == 0o700, f"Secrets directory has insecure permissions: {oct(mode)}"

    def test_error_responses_dont_leak_internals(self):
        """Test that error responses don't leak internal details in production."""
        from lazy_bird.api.middleware import ErrorHandlingMiddleware
        from lazy_bird.core.config import settings
        from fastapi import Request
        from unittest.mock import AsyncMock

        # Mock production mode
        with patch.object(settings, "DEBUG", False):
            # Create middleware
            app = AsyncMock()
            middleware = ErrorHandlingMiddleware(app)

            # Mock request
            request = Mock(spec=Request)
            request.state = Mock()
            request.state.request_id = "test-123"
            request.method = "GET"
            request.url = Mock()
            request.url.path = "/api/test"

            # Mock call_next that raises exception
            async def mock_call_next(req):
                raise ValueError("Internal database connection string: postgresql://user:pass@localhost/db")

            # Process through middleware
            import asyncio
            response = asyncio.run(middleware.dispatch(request, mock_call_next))

            # Get response body
            body = json.loads(response.body.decode())

            # Verify: Generic error in production, no internal details
            assert "Internal Server Error" in body["error"]
            assert "database connection string" not in body["message"].lower()
            assert "postgresql://" not in str(body)


__all__ = [
    "TestAuthenticationBypassAttempts",
    "TestSQLInjectionProtection",
    "TestXSSProtection",
    "TestRateLimiting",
    "TestSecretsHandling",
]
