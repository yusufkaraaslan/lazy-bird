"""Unit tests for ClaudeAccount model.

Tests ClaudeAccount model fields, methods, validators, and business logic.
"""

from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4

import pytest

from lazy_bird.models.claude_account import AccountType, ClaudeAccount


class TestClaudeAccountCreation:
    """Test ClaudeAccount model creation and initialization."""

    def test_api_mode_creation(self):
        """Test creating an API mode Claude account."""
        account = ClaudeAccount(
            name="Production API",
            account_type=AccountType.API,
            api_key="sk-ant-api03-test",
            model="claude-sonnet-4-5",
            max_tokens=8000,
            temperature=Decimal("0.7"),
        )

        assert account.name == "Production API"
        assert account.account_type == AccountType.API
        assert account.api_key == "sk-ant-api03-test"
        assert account.model == "claude-sonnet-4-5"
        assert account.max_tokens == 8000
        assert account.temperature == Decimal("0.7")

    def test_subscription_mode_creation(self):
        """Test creating a subscription mode Claude account."""
        account = ClaudeAccount(
            name="Subscription Account",
            account_type=AccountType.SUBSCRIPTION,
            config_directory="/home/user/.config/claude",
            session_token="test-session-token",
            model="claude-opus-4-5",
        )

        assert account.name == "Subscription Account"
        assert account.account_type == AccountType.SUBSCRIPTION
        assert account.config_directory == "/home/user/.config/claude"
        assert account.session_token == "test-session-token"

    def test_default_values(self):
        """Test default values when explicitly provided."""
        account = ClaudeAccount(
            name="Default Account",
            account_type=AccountType.API,
            api_key="test-key",
            model="claude-sonnet-4-5",
            max_tokens=8000,
            temperature=Decimal("0.7"),
            is_active=True,
        )

        assert account.model == "claude-sonnet-4-5"
        assert account.max_tokens == 8000
        assert account.temperature == Decimal("0.7")
        assert account.is_active is True

    def test_with_budget_limit(self):
        """Test creating account with monthly budget limit."""
        account = ClaudeAccount(
            name="Budget Account",
            account_type=AccountType.API,
            api_key="test-key",
            monthly_budget_usd=Decimal("100.00"),
        )

        assert account.monthly_budget_usd == Decimal("100.00")


class TestClaudeAccountMethods:
    """Test ClaudeAccount model methods."""

    def test_is_api_mode(self):
        """Test is_api_mode() returns True for API accounts."""
        account = ClaudeAccount(
            name="API Account",
            account_type=AccountType.API,
            api_key="test-key",
        )

        assert account.is_api_mode() is True
        assert account.is_subscription_mode() is False

    def test_is_subscription_mode(self):
        """Test is_subscription_mode() returns True for subscription accounts."""
        account = ClaudeAccount(
            name="Sub Account",
            account_type=AccountType.SUBSCRIPTION,
            config_directory="/config",
            session_token="token",
        )

        assert account.is_subscription_mode() is True
        assert account.is_api_mode() is False

    def test_has_budget_limit_true(self):
        """Test has_budget_limit() returns True when budget is set."""
        account = ClaudeAccount(
            name="Budget Account",
            account_type=AccountType.API,
            api_key="test-key",
            monthly_budget_usd=Decimal("50.00"),
        )

        assert account.has_budget_limit() is True

    def test_has_budget_limit_false(self):
        """Test has_budget_limit() returns False when budget is None."""
        account = ClaudeAccount(
            name="No Budget Account",
            account_type=AccountType.API,
            api_key="test-key",
            monthly_budget_usd=None,
        )

        assert account.has_budget_limit() is False

    def test_activate(self):
        """Test activate() sets is_active to True."""
        account = ClaudeAccount(
            name="Inactive Account",
            account_type=AccountType.API,
            api_key="test-key",
            is_active=False,
        )

        assert account.is_active is False

        account.activate()

        assert account.is_active is True

    def test_deactivate(self):
        """Test deactivate() sets is_active to False."""
        account = ClaudeAccount(
            name="Active Account",
            account_type=AccountType.API,
            api_key="test-key",
            is_active=True,
        )

        assert account.is_active is True

        account.deactivate()

        assert account.is_active is False

    def test_update_last_used(self):
        """Test update_last_used() sets last_used_at timestamp."""
        account = ClaudeAccount(
            name="Account",
            account_type=AccountType.API,
            api_key="test-key",
        )

        assert account.last_used_at is None

        account.update_last_used()

        assert account.last_used_at is not None

    def test_get_api_key_preview_with_key(self):
        """Test get_api_key_preview() returns masked preview."""
        account = ClaudeAccount(
            name="Account",
            account_type=AccountType.API,
            api_key="sk-ant-api03-1234567890abcdefghij",
        )

        preview = account.get_api_key_preview()

        assert preview is not None
        assert preview.startswith("sk-ant")
        assert "***" in preview
        assert len(preview) < len(account.api_key)

    def test_get_api_key_preview_none(self):
        """Test get_api_key_preview() returns None when no API key."""
        account = ClaudeAccount(
            name="Account",
            account_type=AccountType.SUBSCRIPTION,
            config_directory="/config",
            session_token="token",
        )

        assert account.get_api_key_preview() is None

    def test_repr(self):
        """Test __repr__() method."""
        account = ClaudeAccount(
            name="Test Account",
            account_type=AccountType.API,
            api_key="test-key",
        )

        repr_string = repr(account)

        assert "ClaudeAccount" in repr_string
        assert "Test Account" in repr_string


class TestClaudeAccountValidators:
    """Test ClaudeAccount model validators."""

    def test_validate_account_type_valid_api(self):
        """Test account_type validator accepts 'api'."""
        account = ClaudeAccount(
            name="Account",
            account_type="api",
            api_key="test-key",
        )

        assert account.account_type == "api"

    def test_validate_account_type_valid_subscription(self):
        """Test account_type validator accepts 'subscription'."""
        account = ClaudeAccount(
            name="Account",
            account_type="subscription",
            config_directory="/config",
            session_token="token",
        )

        assert account.account_type == "subscription"

    def test_validate_account_type_invalid(self):
        """Test account_type validator rejects invalid types."""
        with pytest.raises(ValueError, match="account_type must be"):
            ClaudeAccount(
                name="Account",
                account_type="invalid",
                api_key="test-key",
            )

    def test_validate_temperature_valid_range(self):
        """Test temperature validator accepts values in 0.0-1.0 range."""
        valid_temps = [Decimal("0.0"), Decimal("0.5"), Decimal("1.0")]

        for temp in valid_temps:
            account = ClaudeAccount(
                name="Account",
                account_type=AccountType.API,
                api_key="test-key",
                temperature=temp,
            )
            assert account.temperature == temp

    def test_validate_temperature_below_min(self):
        """Test temperature validator rejects values below 0.0."""
        with pytest.raises(ValueError, match="temperature must be between"):
            ClaudeAccount(
                name="Account",
                account_type=AccountType.API,
                api_key="test-key",
                temperature=Decimal("-0.1"),
            )

    def test_validate_temperature_above_max(self):
        """Test temperature validator rejects values above 1.0."""
        with pytest.raises(ValueError, match="temperature must be between"):
            ClaudeAccount(
                name="Account",
                account_type=AccountType.API,
                api_key="test-key",
                temperature=Decimal("1.1"),
            )

    def test_validate_max_tokens_valid(self):
        """Test max_tokens validator accepts valid values."""
        valid_tokens = [1000, 8000, 100000]

        for tokens in valid_tokens:
            account = ClaudeAccount(
                name="Account",
                account_type=AccountType.API,
                api_key="test-key",
                max_tokens=tokens,
            )
            assert account.max_tokens == tokens

    def test_validate_max_tokens_too_low(self):
        """Test max_tokens validator rejects values below 1."""
        with pytest.raises(ValueError, match="max_tokens must be between"):
            ClaudeAccount(
                name="Account",
                account_type=AccountType.API,
                api_key="test-key",
                max_tokens=0,
            )

    def test_validate_max_tokens_too_high(self):
        """Test max_tokens validator rejects values above 200000."""
        with pytest.raises(ValueError, match="max_tokens must be between"):
            ClaudeAccount(
                name="Account",
                account_type=AccountType.API,
                api_key="test-key",
                max_tokens=200001,
            )


class TestClaudeAccountToDictMethod:
    """Test to_dict() method with sensitive data handling."""

    def test_to_dict_without_sensitive(self):
        """Test to_dict() excludes sensitive data by default."""
        account = ClaudeAccount(
            name="Account",
            account_type=AccountType.API,
            api_key="sk-ant-api03-secret-key",
            model="claude-sonnet-4-5",
            max_tokens=8000,
        )

        data = account.to_dict(include_sensitive=False)

        assert "name" in data
        assert "account_type" in data
        assert "model" in data
        assert "api_key" not in data  # Should be excluded
        assert "session_token" not in data

    def test_to_dict_with_sensitive(self):
        """Test to_dict() includes sensitive data when requested."""
        account = ClaudeAccount(
            name="Account",
            account_type=AccountType.API,
            api_key="sk-ant-api03-secret-key",
        )

        data = account.to_dict(include_sensitive=True)

        assert "api_key" in data
        assert data["api_key"] == "sk-ant-api03-secret-key"
