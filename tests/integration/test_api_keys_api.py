"""Integration tests for API Keys API endpoints.

Tests all 5 API Key CRUD endpoints with security focus.
"""

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from lazy_bird.api.main import app
from lazy_bird.models.api_key import ApiKey
from lazy_bird.models.project import Project


class TestListAPIKeys:
    """Test GET /api/v1/api-keys endpoint."""

    async def test_list_api_keys_empty(self, test_client, test_api_key):
        """Test listing API keys when none exist (except the test key)."""
        response = test_client.get(
            "/api/v1/api-keys",
            headers={"X-API-Key": test_api_key.key_hash},
        )

        assert response.status_code == 200
        data = response.json()
        # At least the test API key should exist
        assert data["total"] >= 1

    async def test_list_api_keys_pagination(self, test_client, test_api_key, test_db):
        """Test API keys pagination."""
        # Create 5 API keys
        for i in range(5):
            api_key = ApiKey(
                key_hash=f"hash-{i}",
                key_prefix=f"lb_test{i}",
                name=f"Test Key {i}",
                scopes=["read"],
                is_active=True,
                created_at=datetime.now(timezone.utc),
            )
            test_db.add(api_key)
        await test_db.commit()

        # Get page 1 with page_size=2
        response = test_client.get(
            "/api/v1/api-keys?page=1&page_size=2",
            headers={"X-API-Key": test_api_key.key_hash},
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 2
        assert data["page"] == 1

    async def test_list_api_keys_filter_by_scope(self, test_client, test_api_key, test_db):
        """Test filtering API keys by scope."""
        # Create keys with different scopes
        read_key = ApiKey(
            key_hash="hash-read",
            key_prefix="lb_read1",
            name="Read Key",
            scopes=["read"],
            is_active=True,
            created_at=datetime.now(timezone.utc),
        )
        admin_key = ApiKey(
            key_hash="hash-admin",
            key_prefix="lb_admin",
            name="Admin Key",
            scopes=["read", "write", "admin"],
            is_active=True,
            created_at=datetime.now(timezone.utc),
        )
        test_db.add_all([read_key, admin_key])
        await test_db.commit()

        # Filter for admin scope
        response = test_client.get(
            "/api/v1/api-keys?scope=admin",
            headers={"X-API-Key": test_api_key.key_hash},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 1
        # All returned items should have admin scope
        for item in data["items"]:
            assert "admin" in item["scopes"]


class TestCreateAPIKey:
    """Test POST /api/v1/api-keys endpoint."""

    async def test_create_api_key_success(self, test_client, test_api_key):
        """Test successful API key creation."""
        payload = {
            "name": "Production API Key",
            "scopes": ["read", "write"],
            "expires_at": (datetime.now(timezone.utc) + timedelta(days=365)).isoformat(),
        }

        response = test_client.post(
            "/api/v1/api-keys",
            json=payload,
            headers={"X-API-Key": test_api_key.key_hash},
        )

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Production API Key"
        assert set(data["scopes"]) == {"read", "write"}
        assert "key" in data  # Full key returned ONLY ONCE
        assert data["key"].startswith("lb_")
        assert len(data["key"]) == 67  # "lb_" + 64 hex chars
        assert data["key_prefix"] == data["key"][:8]

    async def test_create_api_key_organization_level(self, test_client, test_api_key):
        """Test creating organization-level API key (no project_id)."""
        payload = {
            "name": "Org-Level Key",
            "scopes": ["admin"],
        }

        response = test_client.post(
            "/api/v1/api-keys",
            json=payload,
            headers={"X-API-Key": test_api_key.key_hash},
        )

        assert response.status_code == 201
        data = response.json()
        assert data["project_id"] is None  # Organization-level

    async def test_create_api_key_project_scoped(self, test_client, test_api_key, test_project):
        """Test creating project-scoped API key."""
        payload = {
            "name": "Project-Specific Key",
            "project_id": str(test_project.id),
            "scopes": ["read", "write"],
        }

        response = test_client.post(
            "/api/v1/api-keys",
            json=payload,
            headers={"X-API-Key": test_api_key.key_hash},
        )

        assert response.status_code == 201
        data = response.json()
        assert data["project_id"] == str(test_project.id)

    async def test_create_api_key_project_not_found(self, test_client, test_api_key):
        """Test creating API key for non-existent project."""
        payload = {
            "name": "Invalid Project Key",
            "project_id": str(uuid4()),
            "scopes": ["read"],
        }

        response = test_client.post(
            "/api/v1/api-keys",
            json=payload,
            headers={"X-API-Key": test_api_key.key_hash},
        )

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    async def test_create_api_key_minimal_fields(self, test_client, test_api_key):
        """Test creating API key with minimal required fields."""
        payload = {"name": "Minimal Key"}  # Only name required

        response = test_client.post(
            "/api/v1/api-keys",
            json=payload,
            headers={"X-API-Key": test_api_key.key_hash},
        )

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Minimal Key"
        assert data["scopes"] == ["read"]  # Default scope
        assert data["project_id"] is None  # Default org-level


class TestGetAPIKey:
    """Test GET /api/v1/api-keys/{key_id} endpoint."""

    async def test_get_api_key_success(self, test_client, test_api_key, test_db):
        """Test getting single API key."""
        api_key = ApiKey(
            key_hash="test-hash-123",
            key_prefix="lb_test1",
            name="Test API Key",
            scopes=["read", "write"],
            is_active=True,
            last_used_at=datetime.now(timezone.utc),
            created_at=datetime.now(timezone.utc),
        )
        test_db.add(api_key)
        await test_db.commit()
        await test_db.refresh(api_key)

        response = test_client.get(
            f"/api/v1/api-keys/{api_key.id}",
            headers={"X-API-Key": test_api_key.key_hash},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(api_key.id)
        assert data["name"] == "Test API Key"
        assert data["key_prefix"] == "lb_test1"
        assert "key" not in data  # Full key NEVER returned after creation
        assert set(data["scopes"]) == {"read", "write"}

    async def test_get_api_key_not_found(self, test_client, test_api_key):
        """Test getting non-existent API key."""
        response = test_client.get(
            f"/api/v1/api-keys/{uuid4()}",
            headers={"X-API-Key": test_api_key.key_hash},
        )

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()


class TestUpdateAPIKey:
    """Test PATCH /api/v1/api-keys/{key_id} endpoint."""

    async def test_update_api_key_success(self, test_client, test_api_key, test_db):
        """Test successful API key update."""
        api_key = ApiKey(
            key_hash="test-hash-update",
            key_prefix="lb_updat",
            name="Original Name",
            scopes=["read"],
            is_active=True,
            created_at=datetime.now(timezone.utc),
        )
        test_db.add(api_key)
        await test_db.commit()
        await test_db.refresh(api_key)

        payload = {
            "name": "Updated Name",
            "scopes": ["read", "write", "admin"],
        }

        response = test_client.patch(
            f"/api/v1/api-keys/{api_key.id}",
            json=payload,
            headers={"X-API-Key": test_api_key.key_hash},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Name"
        assert set(data["scopes"]) == {"read", "write", "admin"}

    async def test_update_api_key_revoke(self, test_client, test_api_key, test_db):
        """Test revoking API key by setting is_active=false."""
        api_key = ApiKey(
            key_hash="test-hash-revoke",
            key_prefix="lb_revok",
            name="To Be Revoked",
            scopes=["read"],
            is_active=True,
            created_at=datetime.now(timezone.utc),
        )
        test_db.add(api_key)
        await test_db.commit()
        await test_db.refresh(api_key)

        payload = {"is_active": False}

        response = test_client.patch(
            f"/api/v1/api-keys/{api_key.id}",
            json=payload,
            headers={"X-API-Key": test_api_key.key_hash},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["is_active"] is False
        assert data["revoked_at"] is not None  # Should set revoked_at timestamp

    async def test_update_api_key_set_expiration(self, test_client, test_api_key, test_db):
        """Test setting expiration on API key."""
        api_key = ApiKey(
            key_hash="test-hash-expire",
            key_prefix="lb_expir",
            name="To Expire",
            scopes=["read"],
            is_active=True,
            expires_at=None,
            created_at=datetime.now(timezone.utc),
        )
        test_db.add(api_key)
        await test_db.commit()
        await test_db.refresh(api_key)

        expiration = datetime.now(timezone.utc) + timedelta(days=90)
        payload = {"expires_at": expiration.isoformat()}

        response = test_client.patch(
            f"/api/v1/api-keys/{api_key.id}",
            json=payload,
            headers={"X-API-Key": test_api_key.key_hash},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["expires_at"] is not None

    async def test_update_api_key_not_found(self, test_client, test_api_key):
        """Test updating non-existent API key."""
        payload = {"name": "Updated"}

        response = test_client.patch(
            f"/api/v1/api-keys/{uuid4()}",
            json=payload,
            headers={"X-API-Key": test_api_key.key_hash},
        )

        assert response.status_code == 404


class TestDeleteAPIKey:
    """Test DELETE /api/v1/api-keys/{key_id} endpoint."""

    async def test_delete_api_key_success(self, test_client, test_api_key, test_db):
        """Test successful API key deletion."""
        api_key = ApiKey(
            key_hash="test-hash-delete",
            key_prefix="lb_delet",
            name="To Delete",
            scopes=["read"],
            is_active=True,
            created_at=datetime.now(timezone.utc),
        )
        test_db.add(api_key)
        await test_db.commit()
        await test_db.refresh(api_key)
        key_id = api_key.id

        response = test_client.delete(
            f"/api/v1/api-keys/{key_id}",
            headers={"X-API-Key": test_api_key.key_hash},
        )

        assert response.status_code == 204

        # Verify deleted
        get_response = test_client.get(
            f"/api/v1/api-keys/{key_id}",
            headers={"X-API-Key": test_api_key.key_hash},
        )
        assert get_response.status_code == 404

    async def test_delete_api_key_not_found(self, test_client, test_api_key):
        """Test deleting non-existent API key."""
        response = test_client.delete(
            f"/api/v1/api-keys/{uuid4()}",
            headers={"X-API-Key": test_api_key.key_hash},
        )

        assert response.status_code == 404


class TestAPIKeySecurityFeatures:
    """Test API key security-specific features."""

    async def test_full_key_only_shown_on_creation(self, test_client, test_api_key, test_db):
        """Test that full key is only shown once during creation."""
        # Create key
        payload = {"name": "Security Test Key"}

        create_response = test_client.post(
            "/api/v1/api-keys",
            json=payload,
            headers={"X-API-Key": test_api_key.key_hash},
        )

        assert create_response.status_code == 201
        create_data = create_response.json()
        full_key = create_data["key"]
        key_id = create_data["id"]

        # Get the same key - should NOT return full key
        get_response = test_client.get(
            f"/api/v1/api-keys/{key_id}",
            headers={"X-API-Key": test_api_key.key_hash},
        )

        get_data = get_response.json()
        assert "key" not in get_data
        assert get_data["key_prefix"] == full_key[:8]

    async def test_key_prefix_for_identification(self, test_client, test_api_key, test_db):
        """Test that key_prefix is properly generated and displayed."""
        payload = {"name": "Prefix Test Key"}

        response = test_client.post(
            "/api/v1/api-keys",
            json=payload,
            headers={"X-API-Key": test_api_key.key_hash},
        )

        assert response.status_code == 201
        data = response.json()
        full_key = data["key"]
        key_prefix = data["key_prefix"]

        # Prefix should be first 8 characters
        assert key_prefix == full_key[:8]
        assert len(key_prefix) == 8
        assert key_prefix.startswith("lb_")

    async def test_revoked_key_has_timestamp(self, test_client, test_api_key, test_db):
        """Test that revoking a key sets revoked_at timestamp."""
        api_key = ApiKey(
            key_hash="test-hash-timestamp",
            key_prefix="lb_times",
            name="Timestamp Test",
            scopes=["read"],
            is_active=True,
            revoked_at=None,
            created_at=datetime.now(timezone.utc),
        )
        test_db.add(api_key)
        await test_db.commit()
        await test_db.refresh(api_key)

        # Revoke the key
        response = test_client.patch(
            f"/api/v1/api-keys/{api_key.id}",
            json={"is_active": False},
            headers={"X-API-Key": test_api_key.key_hash},
        )

        data = response.json()
        assert data["revoked_at"] is not None
        # Verify timestamp is recent
        revoked_str = data["revoked_at"].replace("Z", "+00:00")
        revoked_time = datetime.fromisoformat(revoked_str)
        if revoked_time.tzinfo is None:
            revoked_time = revoked_time.replace(tzinfo=timezone.utc)
        now = datetime.now(timezone.utc)
        assert (now - revoked_time).total_seconds() < 5  # Within 5 seconds
