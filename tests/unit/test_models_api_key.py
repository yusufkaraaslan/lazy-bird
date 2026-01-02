"""Unit tests for ApiKey model.

Tests ApiKey model fields, scopes, and relationships.
"""

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest

from lazy_bird.models.api_key import ApiKey


class TestApiKeyCreation:
    """Test ApiKey model creation and initialization."""

    def test_basic_creation(self):
        """Test creating an API key with minimum required fields."""
        api_key = ApiKey(
            key_hash="a" * 64,  # SHA-256 hash (64 hex chars)
            key_prefix="lb_test1",
            name="Test Key",
        )

        assert api_key.key_hash == "a" * 64
        assert api_key.key_prefix == "lb_test1"
        assert api_key.name == "Test Key"

    def test_creation_with_all_fields(self):
        """Test creating an API key with all fields."""
        key_id = uuid4()
        project_id = uuid4()
        expires_at = datetime.now(timezone.utc) + timedelta(days=365)
        last_used_at = datetime.now(timezone.utc)
        revoked_at = datetime.now(timezone.utc)

        api_key = ApiKey(
            id=key_id,
            key_hash="b" * 64,
            key_prefix="lb_test2",
            name="Full Test Key",
            project_id=project_id,
            scopes=["read", "write", "admin"],
            is_active=False,
            expires_at=expires_at,
            last_used_at=last_used_at,
            created_by="user@example.com",
            revoked_at=revoked_at,
        )

        assert api_key.id == key_id
        assert api_key.project_id == project_id
        assert api_key.scopes == ["read", "write", "admin"]
        assert api_key.is_active is False
        assert api_key.expires_at == expires_at
        assert api_key.last_used_at == last_used_at
        assert api_key.created_by == "user@example.com"
        assert api_key.revoked_at == revoked_at

    def test_default_values(self):
        """Test that default values are set correctly when explicitly provided."""
        api_key = ApiKey(
            key_hash="c" * 64,
            key_prefix="lb_test3",
            name="Default Key",
            scopes=["read"],
            is_active=True,
        )

        # Default values should be set as provided
        assert api_key.scopes == ["read"]
        assert api_key.is_active is True


class TestApiKeyScopes:
    """Test API key scope handling."""

    def test_read_scope_only(self):
        """Test API key with read scope only."""
        api_key = ApiKey(
            key_hash="d" * 64,
            key_prefix="lb_read",
            name="Read Only Key",
            scopes=["read"],
        )

        assert api_key.scopes == ["read"]
        assert "read" in api_key.scopes

    def test_write_scope(self):
        """Test API key with write scope."""
        api_key = ApiKey(
            key_hash="e" * 64,
            key_prefix="lb_write",
            name="Write Key",
            scopes=["write"],
        )

        assert "write" in api_key.scopes

    def test_admin_scope(self):
        """Test API key with admin scope."""
        api_key = ApiKey(
            key_hash="f" * 64,
            key_prefix="lb_admin",
            name="Admin Key",
            scopes=["admin"],
        )

        assert "admin" in api_key.scopes

    def test_multiple_scopes(self):
        """Test API key with multiple scopes."""
        api_key = ApiKey(
            key_hash="1" * 64,
            key_prefix="lb_multi",
            name="Multi-Scope Key",
            scopes=["read", "write"],
        )

        assert len(api_key.scopes) == 2
        assert "read" in api_key.scopes
        assert "write" in api_key.scopes

    def test_all_scopes(self):
        """Test API key with all possible scopes."""
        api_key = ApiKey(
            key_hash="2" * 64,
            key_prefix="lb_all",
            name="All Scopes Key",
            scopes=["read", "write", "admin"],
        )

        assert len(api_key.scopes) == 3
        assert all(scope in api_key.scopes for scope in ["read", "write", "admin"])


class TestApiKeyFields:
    """Test ApiKey field behavior."""

    def test_key_hash_format(self):
        """Test key_hash is 64 character SHA-256 hash."""
        hash_value = "a" * 64  # 64 chars (simulates SHA-256 hash)

        api_key = ApiKey(
            key_hash=hash_value,
            key_prefix="lb_test",
            name="Hash Test",
        )

        assert len(api_key.key_hash) == 64

    def test_key_prefix_format(self):
        """Test key_prefix is used for identification."""
        api_key = ApiKey(
            key_hash="3" * 64,
            key_prefix="lb_prod",
            name="Production Key",
        )

        assert api_key.key_prefix.startswith("lb_")
        assert len(api_key.key_prefix) <= 10

    def test_active_key(self):
        """Test active API key."""
        api_key = ApiKey(
            key_hash="4" * 64,
            key_prefix="lb_active",
            name="Active Key",
            is_active=True,
        )

        assert api_key.is_active is True

    def test_inactive_key(self):
        """Test inactive API key."""
        api_key = ApiKey(
            key_hash="5" * 64,
            key_prefix="lb_inact",
            name="Inactive Key",
            is_active=False,
        )

        assert api_key.is_active is False

    def test_expires_at_future(self):
        """Test API key with future expiration."""
        future_date = datetime.now(timezone.utc) + timedelta(days=365)

        api_key = ApiKey(
            key_hash="6" * 64,
            key_prefix="lb_exp",
            name="Expiring Key",
            expires_at=future_date,
        )

        assert api_key.expires_at == future_date

    def test_no_expiration(self):
        """Test API key without expiration."""
        api_key = ApiKey(
            key_hash="7" * 64,
            key_prefix="lb_noexp",
            name="No Expiration Key",
            expires_at=None,
        )

        assert api_key.expires_at is None

    def test_last_used_at(self):
        """Test last_used_at tracking."""
        used_time = datetime.now(timezone.utc)

        api_key = ApiKey(
            key_hash="8" * 64,
            key_prefix="lb_used",
            name="Used Key",
            last_used_at=used_time,
        )

        assert api_key.last_used_at == used_time

    def test_never_used(self):
        """Test API key that was never used."""
        api_key = ApiKey(
            key_hash="9" * 64,
            key_prefix="lb_new",
            name="New Key",
            last_used_at=None,
        )

        assert api_key.last_used_at is None

    def test_created_by(self):
        """Test created_by field."""
        api_key = ApiKey(
            key_hash="a" * 64,
            key_prefix="lb_user",
            name="User Key",
            created_by="admin@example.com",
        )

        assert api_key.created_by == "admin@example.com"

    def test_revoked_key(self):
        """Test revoked API key."""
        revoked_time = datetime.now(timezone.utc)

        api_key = ApiKey(
            key_hash="b" * 64,
            key_prefix="lb_rev",
            name="Revoked Key",
            revoked_at=revoked_time,
        )

        assert api_key.revoked_at == revoked_time

    def test_not_revoked(self):
        """Test non-revoked API key."""
        api_key = ApiKey(
            key_hash="c" * 64,
            key_prefix="lb_valid",
            name="Valid Key",
            revoked_at=None,
        )

        assert api_key.revoked_at is None


class TestApiKeyRelationships:
    """Test ApiKey relationships."""

    def test_project_specific_key(self):
        """Test API key associated with a project."""
        project_id = uuid4()

        api_key = ApiKey(
            key_hash="d" * 64,
            key_prefix="lb_proj",
            name="Project Key",
            project_id=project_id,
        )

        assert api_key.project_id == project_id

    def test_organization_level_key(self):
        """Test organization-level API key (no project_id)."""
        api_key = ApiKey(
            key_hash="e" * 64,
            key_prefix="lb_org",
            name="Organization Key",
            project_id=None,
        )

        assert api_key.project_id is None


class TestApiKeyRepr:
    """Test __repr__() method."""

    def test_repr_active(self):
        """Test __repr__() for active key."""
        api_key = ApiKey(
            key_hash="f" * 64,
            key_prefix="lb_repr",
            name="Repr Test Key",
            is_active=True,
        )

        repr_string = repr(api_key)

        assert "ApiKey" in repr_string
        assert "Repr Test Key" in repr_string
        assert "lb_repr" in repr_string
        assert "active=True" in repr_string

    def test_repr_inactive(self):
        """Test __repr__() for inactive key."""
        api_key = ApiKey(
            key_hash="1" * 64,
            key_prefix="lb_off",
            name="Inactive Key",
            is_active=False,
        )

        repr_string = repr(api_key)

        assert "active=False" in repr_string


class TestApiKeyLifecycle:
    """Test API key lifecycle scenarios."""

    def test_fresh_key(self):
        """Test newly created API key."""
        api_key = ApiKey(
            key_hash="2" * 64,
            key_prefix="lb_fresh",
            name="Fresh Key",
            is_active=True,
            last_used_at=None,
            revoked_at=None,
        )

        assert api_key.is_active is True
        assert api_key.last_used_at is None
        assert api_key.revoked_at is None

    def test_active_used_key(self):
        """Test active key that has been used."""
        used_time = datetime.now(timezone.utc) - timedelta(hours=1)

        api_key = ApiKey(
            key_hash="3" * 64,
            key_prefix="lb_used",
            name="Used Key",
            is_active=True,
            last_used_at=used_time,
        )

        assert api_key.is_active is True
        assert api_key.last_used_at is not None

    def test_expired_key(self):
        """Test expired API key."""
        past_date = datetime.now(timezone.utc) - timedelta(days=30)

        api_key = ApiKey(
            key_hash="4" * 64,
            key_prefix="lb_exp",
            name="Expired Key",
            expires_at=past_date,
        )

        assert api_key.expires_at < datetime.now(timezone.utc)

    def test_revoked_and_inactive_key(self):
        """Test revoked and inactive key."""
        revoked_time = datetime.now(timezone.utc) - timedelta(days=7)

        api_key = ApiKey(
            key_hash="5" * 64,
            key_prefix="lb_dead",
            name="Revoked Key",
            is_active=False,
            revoked_at=revoked_time,
        )

        assert api_key.is_active is False
        assert api_key.revoked_at is not None
