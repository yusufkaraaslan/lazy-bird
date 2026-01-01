"""Unit tests for API dependencies (authentication).

Tests RequireRead, RequireWrite, RequireAdmin authentication dependencies.
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from lazy_bird.api.dependencies import RequireAdmin, RequireRead, RequireWrite
from lazy_bird.api.exceptions import AuthenticationError, AuthorizationError
from lazy_bird.models.api_key import ApiKey


class TestRequireRead:
    """Test RequireRead dependency."""

    @pytest.mark.asyncio
    async def test_valid_read_scope(self):
        """Test authentication with valid read scope."""
        # Create mock API key with read scope
        api_key = ApiKey(
            id=uuid4(),
            key_hash="test-hash",
            key_prefix="lb_test1",
            name="Test Key",
            scopes=["read"],
            is_active=True,
            created_at=datetime.now(timezone.utc),
        )

        # Mock database session
        mock_db = AsyncMock(spec=AsyncSession)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = api_key
        mock_db.execute = AsyncMock(return_value=mock_result)

        # Call dependency
        require_read = RequireRead()
        result = await require_read(api_key_header="test-hash", db=mock_db)

        assert result == api_key
        assert result.scopes == ["read"]

    @pytest.mark.asyncio
    async def test_valid_write_scope_allowed(self):
        """Test that write scope is allowed for read operations."""
        api_key = ApiKey(
            id=uuid4(),
            key_hash="test-hash",
            key_prefix="lb_test2",
            name="Test Key",
            scopes=["write"],  # write includes read
            is_active=True,
            created_at=datetime.now(timezone.utc),
        )

        mock_db = AsyncMock(spec=AsyncSession)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = api_key
        mock_db.execute = AsyncMock(return_value=mock_result)

        require_read = RequireRead()
        result = await require_read(api_key_header="test-hash", db=mock_db)

        assert result == api_key

    @pytest.mark.asyncio
    async def test_valid_admin_scope_allowed(self):
        """Test that admin scope is allowed for read operations."""
        api_key = ApiKey(
            id=uuid4(),
            key_hash="test-hash",
            key_prefix="lb_test3",
            name="Test Key",
            scopes=["admin"],  # admin includes all
            is_active=True,
            created_at=datetime.now(timezone.utc),
        )

        mock_db = AsyncMock(spec=AsyncSession)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = api_key
        mock_db.execute = AsyncMock(return_value=mock_result)

        require_read = RequireRead()
        result = await require_read(api_key_header="test-hash", db=mock_db)

        assert result == api_key

    @pytest.mark.asyncio
    async def test_missing_api_key_header(self):
        """Test authentication fails when API key header is missing."""
        mock_db = AsyncMock(spec=AsyncSession)

        require_read = RequireRead()

        with pytest.raises(AuthenticationError) as exc_info:
            await require_read(api_key_header=None, db=mock_db)

        assert "required" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_invalid_api_key(self):
        """Test authentication fails with invalid API key."""
        mock_db = AsyncMock(spec=AsyncSession)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None  # Key not found
        mock_db.execute = AsyncMock(return_value=mock_result)

        require_read = RequireRead()

        with pytest.raises(AuthenticationError) as exc_info:
            await require_read(api_key_header="invalid-key", db=mock_db)

        assert "invalid" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_inactive_api_key(self):
        """Test authentication fails with inactive API key."""
        api_key = ApiKey(
            id=uuid4(),
            key_hash="test-hash",
            key_prefix="lb_test4",
            name="Test Key",
            scopes=["read"],
            is_active=False,  # Inactive key
            created_at=datetime.now(timezone.utc),
        )

        mock_db = AsyncMock(spec=AsyncSession)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = api_key
        mock_db.execute = AsyncMock(return_value=mock_result)

        require_read = RequireRead()

        with pytest.raises(AuthenticationError) as exc_info:
            await require_read(api_key_header="test-hash", db=mock_db)

        assert "inactive" in exc_info.value.detail.lower() or "revoked" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_insufficient_scope(self):
        """Test authorization fails with insufficient scope."""
        # This shouldn't happen for RequireRead since all scopes include read
        # But we can test an empty scopes array
        api_key = ApiKey(
            id=uuid4(),
            key_hash="test-hash",
            key_prefix="lb_test5",
            name="Test Key",
            scopes=[],  # No scopes
            is_active=True,
            created_at=datetime.now(timezone.utc),
        )

        mock_db = AsyncMock(spec=AsyncSession)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = api_key
        mock_db.execute = AsyncMock(return_value=mock_result)

        require_read = RequireRead()

        with pytest.raises(AuthorizationError) as exc_info:
            await require_read(api_key_header="test-hash", db=mock_db)

        assert "permission" in exc_info.value.detail.lower() or "scope" in exc_info.value.detail.lower()


class TestRequireWrite:
    """Test RequireWrite dependency."""

    @pytest.mark.asyncio
    async def test_valid_write_scope(self):
        """Test authentication with valid write scope."""
        api_key = ApiKey(
            id=uuid4(),
            key_hash="test-hash",
            key_prefix="lb_write",
            name="Write Key",
            scopes=["read", "write"],
            is_active=True,
            created_at=datetime.now(timezone.utc),
        )

        mock_db = AsyncMock(spec=AsyncSession)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = api_key
        mock_db.execute = AsyncMock(return_value=mock_result)

        require_write = RequireWrite()
        result = await require_write(api_key_header="test-hash", db=mock_db)

        assert result == api_key

    @pytest.mark.asyncio
    async def test_read_scope_insufficient(self):
        """Test that read-only scope is insufficient for write operations."""
        api_key = ApiKey(
            id=uuid4(),
            key_hash="test-hash",
            key_prefix="lb_read",
            name="Read Key",
            scopes=["read"],  # Only read, not write
            is_active=True,
            created_at=datetime.now(timezone.utc),
        )

        mock_db = AsyncMock(spec=AsyncSession)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = api_key
        mock_db.execute = AsyncMock(return_value=mock_result)

        require_write = RequireWrite()

        with pytest.raises(AuthorizationError) as exc_info:
            await require_write(api_key_header="test-hash", db=mock_db)

        assert "write" in exc_info.value.required_scope or "permission" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_admin_scope_allowed(self):
        """Test that admin scope is allowed for write operations."""
        api_key = ApiKey(
            id=uuid4(),
            key_hash="test-hash",
            key_prefix="lb_admin",
            name="Admin Key",
            scopes=["admin"],  # admin includes write
            is_active=True,
            created_at=datetime.now(timezone.utc),
        )

        mock_db = AsyncMock(spec=AsyncSession)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = api_key
        mock_db.execute = AsyncMock(return_value=mock_result)

        require_write = RequireWrite()
        result = await require_write(api_key_header="test-hash", db=mock_db)

        assert result == api_key


class TestRequireAdmin:
    """Test RequireAdmin dependency."""

    @pytest.mark.asyncio
    async def test_valid_admin_scope(self):
        """Test authentication with valid admin scope."""
        api_key = ApiKey(
            id=uuid4(),
            key_hash="test-hash",
            key_prefix="lb_admin",
            name="Admin Key",
            scopes=["read", "write", "admin"],
            is_active=True,
            created_at=datetime.now(timezone.utc),
        )

        mock_db = AsyncMock(spec=AsyncSession)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = api_key
        mock_db.execute = AsyncMock(return_value=mock_result)

        require_admin = RequireAdmin()
        result = await require_admin(api_key_header="test-hash", db=mock_db)

        assert result == api_key

    @pytest.mark.asyncio
    async def test_read_scope_insufficient(self):
        """Test that read scope is insufficient for admin operations."""
        api_key = ApiKey(
            id=uuid4(),
            key_hash="test-hash",
            key_prefix="lb_read",
            name="Read Key",
            scopes=["read"],
            is_active=True,
            created_at=datetime.now(timezone.utc),
        )

        mock_db = AsyncMock(spec=AsyncSession)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = api_key
        mock_db.execute = AsyncMock(return_value=mock_result)

        require_admin = RequireAdmin()

        with pytest.raises(AuthorizationError) as exc_info:
            await require_admin(api_key_header="test-hash", db=mock_db)

        assert "admin" in exc_info.value.required_scope or "permission" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_write_scope_insufficient(self):
        """Test that write scope is insufficient for admin operations."""
        api_key = ApiKey(
            id=uuid4(),
            key_hash="test-hash",
            key_prefix="lb_write",
            name="Write Key",
            scopes=["read", "write"],  # No admin
            is_active=True,
            created_at=datetime.now(timezone.utc),
        )

        mock_db = AsyncMock(spec=AsyncSession)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = api_key
        mock_db.execute = AsyncMock(return_value=mock_result)

        require_admin = RequireAdmin()

        with pytest.raises(AuthorizationError) as exc_info:
            await require_admin(api_key_header="test-hash", db=mock_db)

        assert "admin" in exc_info.value.required_scope or "permission" in exc_info.value.detail.lower()


class TestScopeHierarchy:
    """Test scope hierarchy (admin > write > read)."""

    @pytest.mark.asyncio
    async def test_admin_can_do_everything(self):
        """Test that admin scope can perform read, write, and admin operations."""
        api_key = ApiKey(
            id=uuid4(),
            key_hash="test-hash",
            key_prefix="lb_admin",
            name="Admin Key",
            scopes=["admin"],
            is_active=True,
            created_at=datetime.now(timezone.utc),
        )

        mock_db = AsyncMock(spec=AsyncSession)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = api_key
        mock_db.execute = AsyncMock(return_value=mock_result)

        # Admin can do read operations
        require_read = RequireRead()
        result = await require_read(api_key_header="test-hash", db=mock_db)
        assert result == api_key

        # Admin can do write operations
        require_write = RequireWrite()
        mock_db.execute = AsyncMock(return_value=mock_result)  # Reset mock
        result = await require_write(api_key_header="test-hash", db=mock_db)
        assert result == api_key

        # Admin can do admin operations
        require_admin = RequireAdmin()
        mock_db.execute = AsyncMock(return_value=mock_result)  # Reset mock
        result = await require_admin(api_key_header="test-hash", db=mock_db)
        assert result == api_key

    @pytest.mark.asyncio
    async def test_write_can_do_read(self):
        """Test that write scope can perform read operations."""
        api_key = ApiKey(
            id=uuid4(),
            key_hash="test-hash",
            key_prefix="lb_write",
            name="Write Key",
            scopes=["write"],
            is_active=True,
            created_at=datetime.now(timezone.utc),
        )

        mock_db = AsyncMock(spec=AsyncSession)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = api_key
        mock_db.execute = AsyncMock(return_value=mock_result)

        # Write can do read operations
        require_read = RequireRead()
        result = await require_read(api_key_header="test-hash", db=mock_db)
        assert result == api_key

        # Write can do write operations
        require_write = RequireWrite()
        mock_db.execute = AsyncMock(return_value=mock_result)  # Reset mock
        result = await require_write(api_key_header="test-hash", db=mock_db)
        assert result == api_key

    @pytest.mark.asyncio
    async def test_read_cannot_do_write_or_admin(self):
        """Test that read scope cannot perform write or admin operations."""
        api_key = ApiKey(
            id=uuid4(),
            key_hash="test-hash",
            key_prefix="lb_read",
            name="Read Key",
            scopes=["read"],
            is_active=True,
            created_at=datetime.now(timezone.utc),
        )

        mock_db = AsyncMock(spec=AsyncSession)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = api_key
        mock_db.execute = AsyncMock(return_value=mock_result)

        # Read can do read operations
        require_read = RequireRead()
        result = await require_read(api_key_header="test-hash", db=mock_db)
        assert result == api_key

        # Read CANNOT do write operations
        require_write = RequireWrite()
        mock_db.execute = AsyncMock(return_value=mock_result)  # Reset mock
        with pytest.raises(AuthorizationError):
            await require_write(api_key_header="test-hash", db=mock_db)

        # Read CANNOT do admin operations
        require_admin = RequireAdmin()
        mock_db.execute = AsyncMock(return_value=mock_result)  # Reset mock
        with pytest.raises(AuthorizationError):
            await require_admin(api_key_header="test-hash", db=mock_db)
