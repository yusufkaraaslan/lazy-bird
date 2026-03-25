"""Integration tests for Auth API endpoints.

Tests registration, login, token refresh, and duplicate email handling.
"""

import pytest
from fastapi.testclient import TestClient

from lazy_bird.core.security import hash_password


class TestRegister:
    """Test POST /api/v1/auth/register endpoint."""

    async def test_register_success(self, test_client):
        """Test successful user registration."""
        response = test_client.post(
            "/api/v1/auth/register",
            json={
                "email": "newuser@example.com",
                "password": "securepassword123",
                "display_name": "New User",
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["email"] == "newuser@example.com"
        assert data["display_name"] == "New User"
        assert data["role"] == "user"
        assert data["is_active"] is True
        assert "id" in data
        assert "created_at" in data
        # Password should never be in the response
        assert "password" not in data
        assert "password_hash" not in data

    async def test_register_without_display_name(self, test_client):
        """Test registration without optional display_name."""
        response = test_client.post(
            "/api/v1/auth/register",
            json={
                "email": "nodisplay@example.com",
                "password": "securepassword123",
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["email"] == "nodisplay@example.com"
        assert data["display_name"] is None

    async def test_register_duplicate_email(self, test_client):
        """Test registration with already registered email returns 409."""
        user_data = {
            "email": "duplicate@example.com",
            "password": "securepassword123",
            "display_name": "First User",
        }

        # Register first user
        response1 = test_client.post("/api/v1/auth/register", json=user_data)
        assert response1.status_code == 201

        # Try to register with same email
        response2 = test_client.post("/api/v1/auth/register", json=user_data)
        assert response2.status_code == 409

    async def test_register_invalid_email(self, test_client):
        """Test registration with invalid email returns 422."""
        response = test_client.post(
            "/api/v1/auth/register",
            json={
                "email": "not-an-email",
                "password": "securepassword123",
            },
        )

        assert response.status_code == 422

    async def test_register_short_password(self, test_client):
        """Test registration with too short password returns 422."""
        response = test_client.post(
            "/api/v1/auth/register",
            json={
                "email": "short@example.com",
                "password": "short",
            },
        )

        assert response.status_code == 422


class TestLogin:
    """Test POST /api/v1/auth/login endpoint."""

    async def test_login_success(self, test_client):
        """Test successful login returns tokens."""
        # Register user first
        test_client.post(
            "/api/v1/auth/register",
            json={
                "email": "loginuser@example.com",
                "password": "securepassword123",
            },
        )

        # Login
        response = test_client.post(
            "/api/v1/auth/login",
            json={
                "email": "loginuser@example.com",
                "password": "securepassword123",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"
        # Tokens should be non-empty JWT strings
        assert len(data["access_token"]) > 0
        assert len(data["refresh_token"]) > 0
        assert "." in data["access_token"]  # JWT has dots
        assert "." in data["refresh_token"]

    async def test_login_wrong_password(self, test_client):
        """Test login with wrong password returns 401."""
        # Register user first
        test_client.post(
            "/api/v1/auth/register",
            json={
                "email": "wrongpw@example.com",
                "password": "securepassword123",
            },
        )

        # Login with wrong password
        response = test_client.post(
            "/api/v1/auth/login",
            json={
                "email": "wrongpw@example.com",
                "password": "wrongpassword",
            },
        )

        assert response.status_code == 401

    async def test_login_nonexistent_user(self, test_client):
        """Test login with non-existent email returns 401."""
        response = test_client.post(
            "/api/v1/auth/login",
            json={
                "email": "nonexistent@example.com",
                "password": "securepassword123",
            },
        )

        assert response.status_code == 401

    async def test_login_inactive_user(self, test_client, test_db):
        """Test login with inactive user returns 401."""
        from lazy_bird.models.user import User
        from datetime import datetime, timezone

        # Create inactive user directly in DB
        user = User(
            email="inactive@example.com",
            password_hash=hash_password("securepassword123"),
            display_name="Inactive User",
            role="user",
            is_active=False,
            created_at=datetime.now(timezone.utc),
        )
        test_db.add(user)
        await test_db.commit()

        # Try to login
        response = test_client.post(
            "/api/v1/auth/login",
            json={
                "email": "inactive@example.com",
                "password": "securepassword123",
            },
        )

        assert response.status_code == 401


class TestRefresh:
    """Test POST /api/v1/auth/refresh endpoint."""

    async def test_refresh_success(self, test_client):
        """Test successful token refresh."""
        # Register and login
        test_client.post(
            "/api/v1/auth/register",
            json={
                "email": "refreshuser@example.com",
                "password": "securepassword123",
            },
        )

        login_response = test_client.post(
            "/api/v1/auth/login",
            json={
                "email": "refreshuser@example.com",
                "password": "securepassword123",
            },
        )

        login_data = login_response.json()
        refresh_token = login_data["refresh_token"]

        # Refresh token
        response = test_client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": refresh_token},
        )

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"

    async def test_refresh_invalid_token(self, test_client):
        """Test refresh with invalid token returns 401."""
        response = test_client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": "invalid.token.here"},
        )

        assert response.status_code == 401

    async def test_refresh_with_access_token(self, test_client):
        """Test refresh with access token (not refresh) returns 401."""
        # Register and login
        test_client.post(
            "/api/v1/auth/register",
            json={
                "email": "accesstoken@example.com",
                "password": "securepassword123",
            },
        )

        login_response = test_client.post(
            "/api/v1/auth/login",
            json={
                "email": "accesstoken@example.com",
                "password": "securepassword123",
            },
        )

        login_data = login_response.json()
        access_token = login_data["access_token"]

        # Try to use access token as refresh token
        response = test_client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": access_token},
        )

        assert response.status_code == 401


class TestLogout:
    """Test POST /api/v1/auth/logout endpoint."""

    async def test_logout(self, test_client):
        """Test logout returns success message."""
        response = test_client.post("/api/v1/auth/logout")

        assert response.status_code == 200
        data = response.json()
        assert "message" in data
