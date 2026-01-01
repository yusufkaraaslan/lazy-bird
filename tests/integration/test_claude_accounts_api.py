"""Integration tests for ClaudeAccounts API endpoints.

Tests all 5 ClaudeAccount CRUD endpoints with both API and subscription modes.
"""

from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from lazy_bird.api.main import app
from lazy_bird.models.claude_account import ClaudeAccount


class TestListClaudeAccounts:
    """Test GET /api/v1/claude-accounts endpoint."""

    async def test_list_claude_accounts_empty(self, test_client, test_api_key):
        """Test listing Claude accounts when none exist."""
        response = test_client.get(
            "/api/v1/claude-accounts",
            headers={"X-API-Key": test_api_key.key_hash},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert data["items"] == []

    async def test_list_claude_accounts_pagination(
        self, test_client, test_api_key, test_db
    ):
        """Test Claude accounts pagination."""
        # Create 5 accounts
        for i in range(5):
            account = ClaudeAccount(
                name=f"Account {i}",
                account_type="api",
                api_key_encrypted=f"sk-ant-test-key-{i}",
                model="claude-sonnet-4-5",
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            )
            test_db.add(account)
        await test_db.commit()

        # Get page 1 with page_size=2
        response = test_client.get(
            "/api/v1/claude-accounts?page=1&page_size=2",
            headers={"X-API-Key": test_api_key.key_hash},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 5
        assert len(data["items"]) == 2
        assert data["pages"] == 3

    async def test_list_claude_accounts_filter_by_type(
        self, test_client, test_api_key, test_db
    ):
        """Test filtering Claude accounts by account_type."""
        # Create API and subscription accounts
        api_account = ClaudeAccount(
            name="API Account",
            account_type="api",
            api_key_encrypted="sk-ant-test-key-api",
            model="claude-sonnet-4-5",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        sub_account = ClaudeAccount(
            name="Subscription Account",
            account_type="subscription",
            config_directory="/home/user/.claude",
            model="claude-sonnet-4-5",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        test_db.add_all([api_account, sub_account])
        await test_db.commit()

        # Filter for API accounts only
        response = test_client.get(
            "/api/v1/claude-accounts?account_type=api",
            headers={"X-API-Key": test_api_key.key_hash},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["account_type"] == "api"


class TestCreateClaudeAccount:
    """Test POST /api/v1/claude-accounts endpoint."""

    async def test_create_api_account_success(self, test_client, test_api_key):
        """Test successful API account creation."""
        payload = {
            "name": "Production API Account",
            "account_type": "api",
            "api_key": "sk-ant-api-test-key-123456",
            "model": "claude-sonnet-4-5",
            "max_tokens": 8000,
            "temperature": 0.7,
            "monthly_budget_usd": 500.0,
        }

        response = test_client.post(
            "/api/v1/claude-accounts",
            json=payload,
            headers={"X-API-Key": test_api_key.key_hash},
        )

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Production API Account"
        assert data["account_type"] == "api"
        assert data["model"] == "claude-sonnet-4-5"
        assert data["max_tokens"] == 8000
        assert Decimal(data["temperature"]) == Decimal("0.7")
        assert "id" in data
        # API key should not be returned
        assert "api_key" not in data

    async def test_create_subscription_account_success(self, test_client, test_api_key):
        """Test successful subscription account creation."""
        payload = {
            "name": "Personal Subscription",
            "account_type": "subscription",
            "config_directory": "/home/user/.config/claude",
            "session_token": "session-token-test-123",
            "model": "claude-sonnet-4-5",
        }

        response = test_client.post(
            "/api/v1/claude-accounts",
            json=payload,
            headers={"X-API-Key": test_api_key.key_hash},
        )

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Personal Subscription"
        assert data["account_type"] == "subscription"
        assert data["config_directory"] == "/home/user/.config/claude"
        # Session token should not be returned
        assert "session_token" not in data

    async def test_create_account_missing_api_key_for_api_type(
        self, test_client, test_api_key
    ):
        """Test creating API account without api_key."""
        payload = {
            "name": "Incomplete API Account",
            "account_type": "api",
            "model": "claude-sonnet-4-5",
            # api_key missing
        }

        response = test_client.post(
            "/api/v1/claude-accounts",
            json=payload,
            headers={"X-API-Key": test_api_key.key_hash},
        )

        assert response.status_code == 422  # Validation error

    async def test_create_account_missing_config_directory_for_subscription(
        self, test_client, test_api_key
    ):
        """Test creating subscription account without config_directory."""
        payload = {
            "name": "Incomplete Subscription Account",
            "account_type": "subscription",
            "model": "claude-sonnet-4-5",
            # config_directory missing
        }

        response = test_client.post(
            "/api/v1/claude-accounts",
            json=payload,
            headers={"X-API-Key": test_api_key.key_hash},
        )

        assert response.status_code == 422  # Validation error


class TestGetClaudeAccount:
    """Test GET /api/v1/claude-accounts/{account_id} endpoint."""

    async def test_get_claude_account_success(self, test_client, test_api_key, test_db):
        """Test getting single Claude account."""
        account = ClaudeAccount(
            name="Test Account",
            account_type="api",
            api_key_encrypted="sk-ant-test-key",
            model="claude-sonnet-4-5",
            max_tokens=8000,
            temperature=Decimal("0.7"),
            current_cost_usd=Decimal("15.50"),
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        test_db.add(account)
        await test_db.commit()
        await test_db.refresh(account)

        response = test_client.get(
            f"/api/v1/claude-accounts/{account.id}",
            headers={"X-API-Key": test_api_key.key_hash},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(account.id)
        assert data["name"] == "Test Account"
        assert data["account_type"] == "api"
        assert Decimal(data["current_cost_usd"]) == Decimal("15.50")

    async def test_get_claude_account_not_found(self, test_client, test_api_key):
        """Test getting non-existent Claude account."""
        response = test_client.get(
            f"/api/v1/claude-accounts/{uuid4()}",
            headers={"X-API-Key": test_api_key.key_hash},
        )

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()


class TestUpdateClaudeAccount:
    """Test PATCH /api/v1/claude-accounts/{account_id} endpoint."""

    async def test_update_claude_account_success(
        self, test_client, test_api_key, test_db
    ):
        """Test successful Claude account update."""
        account = ClaudeAccount(
            name="Original Name",
            account_type="api",
            api_key_encrypted="sk-ant-test-key",
            model="claude-sonnet-4-5",
            max_tokens=8000,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        test_db.add(account)
        await test_db.commit()
        await test_db.refresh(account)

        payload = {
            "name": "Updated Name",
            "max_tokens": 16000,
            "temperature": 0.8,
        }

        response = test_client.patch(
            f"/api/v1/claude-accounts/{account.id}",
            json=payload,
            headers={"X-API-Key": test_api_key.key_hash},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Name"
        assert data["max_tokens"] == 16000
        assert Decimal(data["temperature"]) == Decimal("0.8")

    async def test_update_claude_account_api_key(
        self, test_client, test_api_key, test_db
    ):
        """Test updating API key (encryption should work)."""
        account = ClaudeAccount(
            name="Test Account",
            account_type="api",
            api_key_encrypted="sk-ant-old-key",
            model="claude-sonnet-4-5",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        test_db.add(account)
        await test_db.commit()
        await test_db.refresh(account)

        payload = {"api_key": "sk-ant-new-key-updated"}

        response = test_client.patch(
            f"/api/v1/claude-accounts/{account.id}",
            json=payload,
            headers={"X-API-Key": test_api_key.key_hash},
        )

        assert response.status_code == 200
        # API key should not be in response
        data = response.json()
        assert "api_key" not in data

    async def test_update_claude_account_not_found(self, test_client, test_api_key):
        """Test updating non-existent Claude account."""
        payload = {"name": "Updated Name"}

        response = test_client.patch(
            f"/api/v1/claude-accounts/{uuid4()}",
            json=payload,
            headers={"X-API-Key": test_api_key.key_hash},
        )

        assert response.status_code == 404


class TestDeleteClaudeAccount:
    """Test DELETE /api/v1/claude-accounts/{account_id} endpoint."""

    async def test_delete_claude_account_success(
        self, test_client, test_api_key, test_db
    ):
        """Test successful Claude account deletion."""
        account = ClaudeAccount(
            name="To Delete",
            account_type="api",
            api_key_encrypted="sk-ant-test-key",
            model="claude-sonnet-4-5",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        test_db.add(account)
        await test_db.commit()
        await test_db.refresh(account)
        account_id = account.id

        response = test_client.delete(
            f"/api/v1/claude-accounts/{account_id}",
            headers={"X-API-Key": test_api_key.key_hash},
        )

        assert response.status_code == 204

        # Verify deleted
        get_response = test_client.get(
            f"/api/v1/claude-accounts/{account_id}",
            headers={"X-API-Key": test_api_key.key_hash},
        )
        assert get_response.status_code == 404

    async def test_delete_claude_account_not_found(self, test_client, test_api_key):
        """Test deleting non-existent Claude account."""
        response = test_client.delete(
            f"/api/v1/claude-accounts/{uuid4()}",
            headers={"X-API-Key": test_api_key.key_hash},
        )

        assert response.status_code == 404
