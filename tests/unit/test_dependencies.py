"""Unit tests for API dependencies (authentication).

Tests RequireRead, RequireWrite, RequireAdmin authentication dependencies.
"""

from datetime import datetime, timezone
from uuid import uuid4

import pytest
from fastapi import HTTPException

from lazy_bird.api.dependencies import RequireAdmin, RequireRead, RequireWrite
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

        # Call dependency directly with ApiKey object
        result = await RequireRead(api_key=api_key)

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

        result = await RequireRead(api_key=api_key)

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

        result = await RequireRead(api_key=api_key)

        assert result == api_key

    @pytest.mark.asyncio
    async def test_insufficient_scope(self):
        """Test authorization fails with insufficient scope."""
        api_key = ApiKey(
            id=uuid4(),
            key_hash="test-hash",
            key_prefix="lb_test5",
            name="Test Key",
            scopes=[],  # No scopes
            is_active=True,
            created_at=datetime.now(timezone.utc),
        )

        with pytest.raises(HTTPException) as exc_info:
            await RequireRead(api_key=api_key)

        assert exc_info.value.status_code == 403
        assert (
            "permission" in exc_info.value.detail.lower()
            or "scope" in exc_info.value.detail.lower()
        )


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
            scopes=["write"],
            is_active=True,
            created_at=datetime.now(timezone.utc),
        )

        result = await RequireWrite(api_key=api_key)

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

        with pytest.raises(HTTPException) as exc_info:
            await RequireWrite(api_key=api_key)

        assert exc_info.value.status_code == 403
        assert "permission" in exc_info.value.detail.lower()

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

        result = await RequireWrite(api_key=api_key)

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
            scopes=["admin"],
            is_active=True,
            created_at=datetime.now(timezone.utc),
        )

        result = await RequireAdmin(api_key=api_key)

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

        with pytest.raises(HTTPException) as exc_info:
            await RequireAdmin(api_key=api_key)

        assert exc_info.value.status_code == 403
        assert "permission" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_write_scope_insufficient(self):
        """Test that write scope is insufficient for admin operations."""
        api_key = ApiKey(
            id=uuid4(),
            key_hash="test-hash",
            key_prefix="lb_write",
            name="Write Key",
            scopes=["write"],  # No admin
            is_active=True,
            created_at=datetime.now(timezone.utc),
        )

        with pytest.raises(HTTPException) as exc_info:
            await RequireAdmin(api_key=api_key)

        assert exc_info.value.status_code == 403
        assert "permission" in exc_info.value.detail.lower()


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

        # Admin can do read operations
        result = await RequireRead(api_key=api_key)
        assert result == api_key

        # Admin can do write operations
        result = await RequireWrite(api_key=api_key)
        assert result == api_key

        # Admin can do admin operations
        result = await RequireAdmin(api_key=api_key)
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

        # Write can do read operations
        result = await RequireRead(api_key=api_key)
        assert result == api_key

        # Write can do write operations
        result = await RequireWrite(api_key=api_key)
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

        # Read can do read operations
        result = await RequireRead(api_key=api_key)
        assert result == api_key

        # Read CANNOT do write operations
        with pytest.raises(HTTPException) as exc_info:
            await RequireWrite(api_key=api_key)
        assert exc_info.value.status_code == 403

        # Read CANNOT do admin operations
        with pytest.raises(HTTPException) as exc_info:
            await RequireAdmin(api_key=api_key)
        assert exc_info.value.status_code == 403
