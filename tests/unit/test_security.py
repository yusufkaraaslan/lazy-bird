"""Unit tests for security utility functions.

Tests API key generation, hashing, password hashing, and JWT token operations.
"""

import re
from datetime import datetime, timedelta

import pytest

from lazy_bird.core.security import (
    constant_time_compare,
    create_access_token,
    create_refresh_token,
    generate_api_key,
    generate_secure_random_string,
    get_api_key_prefix,
    hash_api_key,
    hash_password,
    verify_api_key,
    verify_password,
    verify_refresh_token,
    verify_token,
)


class TestAPIKeyGeneration:
    """Test API key generation and management."""

    def test_generate_api_key_basic(self):
        """Test basic API key generation."""
        key = generate_api_key()

        assert key is not None
        assert key.startswith("lb_")
        assert len(key) == 67  # "lb_" (3) + 64 hex chars (32 bytes * 2)

    def test_generate_api_key_custom_prefix(self):
        """Test API key generation with custom prefix."""
        key = generate_api_key(prefix="custom")

        assert key.startswith("custom_")
        assert len(key) == 71  # "custom_" (7) + 64 hex chars

    def test_generate_api_key_custom_length(self):
        """Test API key generation with custom length."""
        key = generate_api_key(length=16)

        assert key.startswith("lb_")
        assert len(key) == 35  # "lb_" (3) + 32 hex chars (16 bytes * 2)

    def test_generate_api_key_uniqueness(self):
        """Test that generated keys are unique."""
        keys = [generate_api_key() for _ in range(100)]

        # All keys should be unique
        assert len(keys) == len(set(keys))

    def test_generate_api_key_format(self):
        """Test that generated keys have correct format."""
        key = generate_api_key()

        # Should match pattern: prefix_hexstring
        pattern = r"^lb_[0-9a-f]{64}$"
        assert re.match(pattern, key) is not None


class TestAPIKeyHashing:
    """Test API key hashing and verification."""

    def test_hash_api_key_basic(self):
        """Test basic API key hashing."""
        key = "lb_abc123def456"
        hashed = hash_api_key(key)

        assert hashed is not None
        assert len(hashed) == 64  # SHA-256 produces 64 hex characters
        assert all(c in "0123456789abcdef" for c in hashed)

    def test_hash_api_key_deterministic(self):
        """Test that same key produces same hash."""
        key = "lb_abc123def456"

        hash1 = hash_api_key(key)
        hash2 = hash_api_key(key)

        assert hash1 == hash2

    def test_hash_api_key_different_keys(self):
        """Test that different keys produce different hashes."""
        key1 = "lb_abc123def456"
        key2 = "lb_xyz789uvw012"

        hash1 = hash_api_key(key1)
        hash2 = hash_api_key(key2)

        assert hash1 != hash2

    def test_verify_api_key_valid(self):
        """Test API key verification with valid key."""
        raw_key = "lb_abc123def456"
        hashed_key = hash_api_key(raw_key)

        assert verify_api_key(raw_key, hashed_key) is True

    def test_verify_api_key_invalid(self):
        """Test API key verification with invalid key."""
        raw_key = "lb_abc123def456"
        wrong_key = "lb_wrongkey12345"
        hashed_key = hash_api_key(raw_key)

        assert verify_api_key(wrong_key, hashed_key) is False

    def test_verify_api_key_case_sensitive(self):
        """Test that API key verification is case-sensitive."""
        raw_key = "lb_AbC123DeF456"
        wrong_case = "lb_abc123def456"
        hashed_key = hash_api_key(raw_key)

        assert verify_api_key(wrong_case, hashed_key) is False


class TestAPIKeyPrefix:
    """Test API key prefix extraction."""

    def test_get_prefix_standard_key(self):
        """Test prefix extraction from standard key."""
        key = "lb_abc123def456"
        prefix = get_api_key_prefix(key)

        assert prefix == "lb_abc12"
        assert len(prefix) == 8

    def test_get_prefix_long_key(self):
        """Test prefix extraction from long key."""
        key = generate_api_key()  # 67 characters
        prefix = get_api_key_prefix(key)

        assert len(prefix) == 8
        assert key.startswith(prefix)

    def test_get_prefix_short_key(self):
        """Test prefix extraction from short key (less than 8 chars)."""
        key = "lb_abc"
        prefix = get_api_key_prefix(key)

        assert prefix == key  # Returns full key if less than 8 chars


class TestPasswordHashing:
    """Test password hashing and verification."""

    def test_hash_password_basic(self):
        """Test basic password hashing."""
        password = "mySecurePassword123!"
        hashed = hash_password(password)

        assert hashed is not None
        assert hashed.startswith("$2b$")  # Bcrypt format
        assert len(hashed) == 60  # Bcrypt hash length

    def test_hash_password_unique_salts(self):
        """Test that same password produces different hashes (different salts)."""
        password = "myPassword"

        hash1 = hash_password(password)
        hash2 = hash_password(password)

        # Hashes should be different due to random salts
        assert hash1 != hash2

    def test_verify_password_valid(self):
        """Test password verification with valid password."""
        password = "mySecurePassword123!"
        hashed = hash_password(password)

        assert verify_password(password, hashed) is True

    def test_verify_password_invalid(self):
        """Test password verification with invalid password."""
        password = "mySecurePassword123!"
        wrong_password = "wrongPassword"
        hashed = hash_password(password)

        assert verify_password(wrong_password, hashed) is False

    def test_verify_password_case_sensitive(self):
        """Test that password verification is case-sensitive."""
        password = "MyPassword"
        wrong_case = "mypassword"
        hashed = hash_password(password)

        assert verify_password(wrong_case, hashed) is False


class TestJWTTokens:
    """Test JWT access and refresh tokens."""

    def test_create_access_token_basic(self):
        """Test basic access token creation."""
        data = {"sub": "user123", "email": "user@example.com"}
        token = create_access_token(data)

        assert token is not None
        assert len(token) > 0
        assert token.count(".") == 2  # JWT has 3 parts separated by dots

    def test_create_access_token_with_expiration(self):
        """Test access token creation with custom expiration."""
        data = {"sub": "user123"}
        expires_delta = timedelta(minutes=60)
        token = create_access_token(data, expires_delta=expires_delta)

        payload = verify_token(token)
        assert payload is not None
        assert "exp" in payload
        assert "sub" in payload
        assert payload["sub"] == "user123"

    def test_verify_token_valid(self):
        """Test token verification with valid token."""
        data = {"sub": "user123", "email": "user@example.com", "role": "admin"}
        token = create_access_token(data)

        payload = verify_token(token)

        assert payload is not None
        assert payload["sub"] == "user123"
        assert payload["email"] == "user@example.com"
        assert payload["role"] == "admin"
        assert "exp" in payload

    def test_verify_token_invalid(self):
        """Test token verification with invalid token."""
        payload = verify_token("invalid.token.string")

        assert payload is None

    def test_verify_token_tampered(self):
        """Test token verification with tampered token."""
        data = {"sub": "user123"}
        token = create_access_token(data)

        # Tamper with token
        parts = token.split(".")
        parts[1] = parts[1][:-5] + "aaaaa"  # Change last 5 chars of payload
        tampered_token = ".".join(parts)

        payload = verify_token(tampered_token)

        assert payload is None

    def test_create_refresh_token_basic(self):
        """Test basic refresh token creation."""
        data = {"sub": "user123"}
        token = create_refresh_token(data)

        assert token is not None
        assert len(token) > 0
        assert token.count(".") == 2

    def test_verify_refresh_token_valid(self):
        """Test refresh token verification with valid token."""
        data = {"sub": "user123"}
        token = create_refresh_token(data)

        payload = verify_refresh_token(token)

        assert payload is not None
        assert payload["sub"] == "user123"
        assert payload["type"] == "refresh"

    def test_verify_refresh_token_with_access_token(self):
        """Test that access token is not accepted as refresh token."""
        data = {"sub": "user123"}
        access_token = create_access_token(data)

        payload = verify_refresh_token(access_token)

        assert payload is None  # Should reject access token


class TestSecureRandomString:
    """Test secure random string generation."""

    def test_generate_secure_random_string_basic(self):
        """Test basic secure random string generation."""
        random_str = generate_secure_random_string()

        assert random_str is not None
        assert len(random_str) == 32

    def test_generate_secure_random_string_custom_length(self):
        """Test secure random string with custom length."""
        random_str = generate_secure_random_string(length=64)

        assert len(random_str) == 64

    def test_generate_secure_random_string_uniqueness(self):
        """Test that generated strings are unique."""
        strings = [generate_secure_random_string() for _ in range(100)]

        # All strings should be unique
        assert len(strings) == len(set(strings))

    def test_generate_secure_random_string_url_safe(self):
        """Test that generated strings are URL-safe."""
        random_str = generate_secure_random_string()

        # Should only contain URL-safe characters
        allowed_chars = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_")
        assert all(c in allowed_chars for c in random_str)


class TestConstantTimeCompare:
    """Test constant-time string comparison."""

    def test_constant_time_compare_equal(self):
        """Test constant-time comparison with equal strings."""
        str1 = "secret_value_12345"
        str2 = "secret_value_12345"

        assert constant_time_compare(str1, str2) is True

    def test_constant_time_compare_not_equal(self):
        """Test constant-time comparison with different strings."""
        str1 = "secret_value_12345"
        str2 = "different_value_67890"

        assert constant_time_compare(str1, str2) is False

    def test_constant_time_compare_different_length(self):
        """Test constant-time comparison with different length strings."""
        str1 = "short"
        str2 = "much_longer_string"

        assert constant_time_compare(str1, str2) is False

    def test_constant_time_compare_empty_strings(self):
        """Test constant-time comparison with empty strings."""
        assert constant_time_compare("", "") is True

    def test_constant_time_compare_case_sensitive(self):
        """Test that constant-time comparison is case-sensitive."""
        str1 = "SecretValue"
        str2 = "secretvalue"

        assert constant_time_compare(str1, str2) is False


class TestSecurityIntegration:
    """Test integration scenarios with security functions."""

    def test_api_key_full_workflow(self):
        """Test complete API key workflow: generate -> hash -> verify."""
        # Generate key
        raw_key = generate_api_key()
        assert raw_key.startswith("lb_")

        # Hash key
        hashed_key = hash_api_key(raw_key)
        assert len(hashed_key) == 64

        # Get prefix for display
        prefix = get_api_key_prefix(raw_key)
        assert len(prefix) == 8

        # Verify key
        assert verify_api_key(raw_key, hashed_key) is True
        assert verify_api_key("lb_wrongkey", hashed_key) is False

    def test_password_full_workflow(self):
        """Test complete password workflow: hash -> verify."""
        password = "MySecureP@ssw0rd!"

        # Hash password
        hashed = hash_password(password)
        assert hashed.startswith("$2b$")

        # Verify correct password
        assert verify_password(password, hashed) is True

        # Reject wrong password
        assert verify_password("WrongPassword", hashed) is False

    def test_jwt_full_workflow(self):
        """Test complete JWT workflow: create -> verify -> refresh."""
        user_data = {"sub": "user123", "email": "user@example.com"}

        # Create access token
        access_token = create_access_token(user_data)
        assert access_token is not None

        # Verify access token
        payload = verify_token(access_token)
        assert payload["sub"] == "user123"
        assert payload["email"] == "user@example.com"

        # Create refresh token
        refresh_token = create_refresh_token(user_data)
        assert refresh_token is not None

        # Verify refresh token
        refresh_payload = verify_refresh_token(refresh_token)
        assert refresh_payload["sub"] == "user123"
        assert refresh_payload["type"] == "refresh"

        # Ensure access token is not accepted as refresh token
        assert verify_refresh_token(access_token) is None
