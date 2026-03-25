"""Unit tests for lazy_bird.models.user module.

Tests User model instantiation and repr.
"""

import uuid
from datetime import datetime, timezone

import pytest

from lazy_bird.models.user import User


class TestUserModel:
    """Test User model."""

    def test_user_creation(self):
        """Test User model can be instantiated."""
        user = User(
            id=uuid.uuid4(),
            email="test@example.com",
            password_hash="$2b$12$hashed_password_here",
            display_name="Test User",
            role="admin",
            is_active=True,
            created_at=datetime.now(timezone.utc),
        )

        assert user.email == "test@example.com"
        assert user.display_name == "Test User"
        assert user.role == "admin"
        assert user.is_active is True

    def test_user_default_role(self):
        """Test User model role defaults to None in Python (server_default 'user').

        The 'user' default is set via server_default in PostgreSQL.
        In Python without DB, the default may be None or 'user' depending
        on SQLAlchemy version behavior.
        """
        user = User(
            id=uuid.uuid4(),
            email="test@example.com",
            password_hash="$2b$12$hashed_password_here",
            created_at=datetime.now(timezone.utc),
        )

        # The default is handled by server_default; Python-side may be None
        assert user.role is None or user.role == "user"

    def test_user_default_is_active(self):
        """Test User model is_active defaults to None in Python (server_default 'true').

        The 'true' default is set via server_default in PostgreSQL.
        In Python without DB, the default may be None or True.
        """
        user = User(
            id=uuid.uuid4(),
            email="test@example.com",
            password_hash="$2b$12$hashed_password_here",
            created_at=datetime.now(timezone.utc),
        )

        assert user.is_active is None or user.is_active is True

    def test_user_repr(self):
        """Test User __repr__ method."""
        user_id = uuid.uuid4()
        user = User(
            id=user_id,
            email="test@example.com",
            password_hash="$2b$12$hashed",
            role="admin",
            is_active=True,
            created_at=datetime.now(timezone.utc),
        )

        repr_str = repr(user)
        assert "User" in repr_str
        assert "test@example.com" in repr_str
        assert "admin" in repr_str

    def test_user_optional_fields(self):
        """Test User model optional fields."""
        user = User(
            id=uuid.uuid4(),
            email="test@example.com",
            password_hash="$2b$12$hashed",
            display_name=None,
            updated_at=None,
            created_at=datetime.now(timezone.utc),
        )

        assert user.display_name is None
        assert user.updated_at is None

    def test_user_tablename(self):
        """Test User model table name."""
        assert User.__tablename__ == "users"
