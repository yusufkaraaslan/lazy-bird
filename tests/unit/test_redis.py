"""Unit tests for lazy_bird.core.redis module.

Tests Redis client management, connection checking, closing, and RedisCache wrapper.
"""

import pytest
from unittest.mock import MagicMock, Mock, patch, PropertyMock

import lazy_bird.core.redis as redis_module


@pytest.fixture(autouse=True)
def reset_redis_globals():
    """Reset global Redis clients between tests."""
    redis_module._redis_client = None
    redis_module._async_redis_client = None
    yield
    redis_module._redis_client = None
    redis_module._async_redis_client = None


class TestGetRedis:
    """Test get_redis() function."""

    @patch("lazy_bird.core.redis.redis.from_url")
    @patch("lazy_bird.core.redis.settings")
    def test_get_redis_creates_client(self, mock_settings, mock_from_url):
        """Test that get_redis creates a client on first call."""
        mock_settings.REDIS_URL = "redis://localhost:6379/0"
        mock_settings.REDIS_MAX_CONNECTIONS = 10
        mock_settings.REDIS_SOCKET_TIMEOUT = 5
        mock_client = MagicMock()
        mock_from_url.return_value = mock_client

        result = redis_module.get_redis()

        assert result is mock_client
        mock_from_url.assert_called_once_with(
            "redis://localhost:6379/0",
            encoding="utf-8",
            decode_responses=True,
            max_connections=10,
            socket_timeout=5,
            socket_connect_timeout=5,
        )

    @patch("lazy_bird.core.redis.redis.from_url")
    @patch("lazy_bird.core.redis.settings")
    def test_get_redis_reuses_client(self, mock_settings, mock_from_url):
        """Test that get_redis returns same client on subsequent calls."""
        mock_settings.REDIS_URL = "redis://localhost:6379/0"
        mock_settings.REDIS_MAX_CONNECTIONS = 10
        mock_settings.REDIS_SOCKET_TIMEOUT = 5
        mock_client = MagicMock()
        mock_from_url.return_value = mock_client

        result1 = redis_module.get_redis()
        result2 = redis_module.get_redis()

        assert result1 is result2
        assert mock_from_url.call_count == 1


class TestGetAsyncRedis:
    """Test get_async_redis() function."""

    @pytest.mark.asyncio
    @patch("lazy_bird.core.redis.settings")
    async def test_get_async_redis_creates_client(self, mock_settings):
        """Test that get_async_redis creates a client on first call."""
        mock_settings.REDIS_URL = "redis://localhost:6379/0"
        mock_settings.REDIS_MAX_CONNECTIONS = 10
        mock_settings.REDIS_SOCKET_TIMEOUT = 5
        mock_client = MagicMock()

        async def mock_from_url(*args, **kwargs):
            return mock_client

        with patch.object(redis_module.AsyncRedis, "from_url", side_effect=mock_from_url):
            result = await redis_module.get_async_redis()

            assert result is mock_client

    @pytest.mark.asyncio
    @patch("lazy_bird.core.redis.settings")
    async def test_get_async_redis_reuses_client(self, mock_settings):
        """Test that get_async_redis returns same client on subsequent calls."""
        mock_settings.REDIS_URL = "redis://localhost:6379/0"
        mock_settings.REDIS_MAX_CONNECTIONS = 10
        mock_settings.REDIS_SOCKET_TIMEOUT = 5
        mock_client = MagicMock()

        # Set client directly to test reuse
        redis_module._async_redis_client = mock_client

        result = await redis_module.get_async_redis()

        assert result is mock_client


class TestCheckRedisConnection:
    """Test check_redis_connection() function."""

    @patch("lazy_bird.core.redis.get_redis")
    def test_check_redis_connection_success(self, mock_get_redis):
        """Test successful Redis connection check."""
        mock_client = MagicMock()
        mock_client.ping.return_value = True
        mock_get_redis.return_value = mock_client

        result = redis_module.check_redis_connection()

        assert result is True
        mock_client.ping.assert_called_once()

    @patch("lazy_bird.core.redis.get_redis")
    def test_check_redis_connection_failure(self, mock_get_redis):
        """Test failed Redis connection check."""
        from redis.exceptions import ConnectionError

        mock_client = MagicMock()
        mock_client.ping.side_effect = ConnectionError("Connection refused")
        mock_get_redis.return_value = mock_client

        result = redis_module.check_redis_connection()

        assert result is False

    @patch("lazy_bird.core.redis.get_redis")
    def test_check_redis_connection_redis_error(self, mock_get_redis):
        """Test Redis connection check with RedisError."""
        from redis.exceptions import RedisError

        mock_client = MagicMock()
        mock_client.ping.side_effect = RedisError("Some redis error")
        mock_get_redis.return_value = mock_client

        result = redis_module.check_redis_connection()

        assert result is False


class TestCheckAsyncRedisConnection:
    """Test check_async_redis_connection() function."""

    @pytest.mark.asyncio
    async def test_check_async_redis_connection_success(self):
        """Test successful async Redis connection check."""
        from unittest.mock import AsyncMock

        mock_client = MagicMock()
        mock_client.ping = AsyncMock(return_value=True)

        async def mock_get_async():
            return mock_client

        with patch("lazy_bird.core.redis.get_async_redis", side_effect=mock_get_async):
            result = await redis_module.check_async_redis_connection()

        assert result is True

    @pytest.mark.asyncio
    async def test_check_async_redis_connection_failure(self):
        """Test failed async Redis connection check."""
        from redis.exceptions import ConnectionError
        from unittest.mock import AsyncMock

        mock_client = MagicMock()
        mock_client.ping = AsyncMock(side_effect=ConnectionError("Connection refused"))

        async def mock_get_async():
            return mock_client

        with patch("lazy_bird.core.redis.get_async_redis", side_effect=mock_get_async):
            result = await redis_module.check_async_redis_connection()

        assert result is False


class TestCloseRedis:
    """Test close_redis() function."""

    def test_close_redis_with_active_client(self):
        """Test closing an active Redis client."""
        mock_client = MagicMock()
        redis_module._redis_client = mock_client

        redis_module.close_redis()

        mock_client.close.assert_called_once()
        assert redis_module._redis_client is None

    def test_close_redis_with_no_client(self):
        """Test closing when no client exists."""
        redis_module._redis_client = None

        # Should not raise
        redis_module.close_redis()

        assert redis_module._redis_client is None


class TestCloseAsyncRedis:
    """Test close_async_redis() function."""

    @pytest.mark.asyncio
    async def test_close_async_redis_with_active_client(self):
        """Test closing an active async Redis client."""
        from unittest.mock import AsyncMock

        mock_client = MagicMock()
        mock_client.close = AsyncMock(return_value=None)
        redis_module._async_redis_client = mock_client

        await redis_module.close_async_redis()

        mock_client.close.assert_called_once()
        assert redis_module._async_redis_client is None

    @pytest.mark.asyncio
    async def test_close_async_redis_with_no_client(self):
        """Test closing when no async client exists."""
        redis_module._async_redis_client = None

        await redis_module.close_async_redis()

        assert redis_module._async_redis_client is None


class TestRedisCache:
    """Test RedisCache class."""

    @patch("lazy_bird.core.redis.get_redis")
    def test_init_defaults(self, mock_get_redis):
        """Test RedisCache initialization with defaults."""
        mock_client = MagicMock()
        mock_get_redis.return_value = mock_client

        cache = redis_module.RedisCache()

        assert cache.prefix == "lazy_bird:"
        assert cache.ttl == 3600
        assert cache.redis is mock_client

    @patch("lazy_bird.core.redis.get_redis")
    def test_init_custom(self, mock_get_redis):
        """Test RedisCache initialization with custom settings."""
        mock_client = MagicMock()
        mock_get_redis.return_value = mock_client

        cache = redis_module.RedisCache(prefix="test:", ttl=600)

        assert cache.prefix == "test:"
        assert cache.ttl == 600

    @patch("lazy_bird.core.redis.get_redis")
    def test_make_key(self, mock_get_redis):
        """Test _make_key creates prefixed key."""
        mock_get_redis.return_value = MagicMock()
        cache = redis_module.RedisCache(prefix="app:")

        assert cache._make_key("user:123") == "app:user:123"

    @patch("lazy_bird.core.redis.get_redis")
    def test_get_success(self, mock_get_redis):
        """Test cache get returns value."""
        mock_client = MagicMock()
        mock_client.get.return_value = "cached_value"
        mock_get_redis.return_value = mock_client

        cache = redis_module.RedisCache()
        result = cache.get("test_key")

        assert result == "cached_value"
        mock_client.get.assert_called_once_with("lazy_bird:test_key")

    @patch("lazy_bird.core.redis.get_redis")
    def test_get_redis_error(self, mock_get_redis):
        """Test cache get returns None on error."""
        from redis.exceptions import RedisError

        mock_client = MagicMock()
        mock_client.get.side_effect = RedisError("Connection lost")
        mock_get_redis.return_value = mock_client

        cache = redis_module.RedisCache()
        result = cache.get("test_key")

        assert result is None

    @patch("lazy_bird.core.redis.get_redis")
    def test_set_success(self, mock_get_redis):
        """Test cache set returns True on success."""
        mock_client = MagicMock()
        mock_get_redis.return_value = mock_client

        cache = redis_module.RedisCache(ttl=3600)
        result = cache.set("test_key", "test_value")

        assert result is True
        mock_client.setex.assert_called_once_with("lazy_bird:test_key", 3600, "test_value")

    @patch("lazy_bird.core.redis.get_redis")
    def test_set_custom_ttl(self, mock_get_redis):
        """Test cache set with custom TTL."""
        mock_client = MagicMock()
        mock_get_redis.return_value = mock_client

        cache = redis_module.RedisCache(ttl=3600)
        result = cache.set("test_key", "test_value", ttl=120)

        assert result is True
        mock_client.setex.assert_called_once_with("lazy_bird:test_key", 120, "test_value")

    @patch("lazy_bird.core.redis.get_redis")
    def test_set_redis_error(self, mock_get_redis):
        """Test cache set returns False on error."""
        from redis.exceptions import RedisError

        mock_client = MagicMock()
        mock_client.setex.side_effect = RedisError("Connection lost")
        mock_get_redis.return_value = mock_client

        cache = redis_module.RedisCache()
        result = cache.set("test_key", "test_value")

        assert result is False

    @patch("lazy_bird.core.redis.get_redis")
    def test_delete_success(self, mock_get_redis):
        """Test cache delete returns True on success."""
        mock_client = MagicMock()
        mock_get_redis.return_value = mock_client

        cache = redis_module.RedisCache()
        result = cache.delete("test_key")

        assert result is True
        mock_client.delete.assert_called_once_with("lazy_bird:test_key")

    @patch("lazy_bird.core.redis.get_redis")
    def test_delete_redis_error(self, mock_get_redis):
        """Test cache delete returns False on error."""
        from redis.exceptions import RedisError

        mock_client = MagicMock()
        mock_client.delete.side_effect = RedisError("Connection lost")
        mock_get_redis.return_value = mock_client

        cache = redis_module.RedisCache()
        result = cache.delete("test_key")

        assert result is False

    @patch("lazy_bird.core.redis.get_redis")
    def test_exists_true(self, mock_get_redis):
        """Test cache exists returns True when key exists."""
        mock_client = MagicMock()
        mock_client.exists.return_value = 1
        mock_get_redis.return_value = mock_client

        cache = redis_module.RedisCache()
        result = cache.exists("test_key")

        assert result is True

    @patch("lazy_bird.core.redis.get_redis")
    def test_exists_false(self, mock_get_redis):
        """Test cache exists returns False when key does not exist."""
        mock_client = MagicMock()
        mock_client.exists.return_value = 0
        mock_get_redis.return_value = mock_client

        cache = redis_module.RedisCache()
        result = cache.exists("test_key")

        assert result is False

    @patch("lazy_bird.core.redis.get_redis")
    def test_exists_redis_error(self, mock_get_redis):
        """Test cache exists returns False on error."""
        from redis.exceptions import RedisError

        mock_client = MagicMock()
        mock_client.exists.side_effect = RedisError("Connection lost")
        mock_get_redis.return_value = mock_client

        cache = redis_module.RedisCache()
        result = cache.exists("test_key")

        assert result is False

    @patch("lazy_bird.core.redis.get_redis")
    def test_flush_with_keys(self, mock_get_redis):
        """Test cache flush deletes matching keys."""
        mock_client = MagicMock()
        mock_client.keys.return_value = ["lazy_bird:a", "lazy_bird:b"]
        mock_client.delete.return_value = 2
        mock_get_redis.return_value = mock_client

        cache = redis_module.RedisCache()
        result = cache.flush()

        assert result == 2
        mock_client.keys.assert_called_once_with("lazy_bird:*")
        mock_client.delete.assert_called_once_with("lazy_bird:a", "lazy_bird:b")

    @patch("lazy_bird.core.redis.get_redis")
    def test_flush_with_pattern(self, mock_get_redis):
        """Test cache flush with custom pattern."""
        mock_client = MagicMock()
        mock_client.keys.return_value = ["lazy_bird:user:1"]
        mock_client.delete.return_value = 1
        mock_get_redis.return_value = mock_client

        cache = redis_module.RedisCache()
        result = cache.flush("user:*")

        assert result == 1
        mock_client.keys.assert_called_once_with("lazy_bird:user:*")

    @patch("lazy_bird.core.redis.get_redis")
    def test_flush_no_keys(self, mock_get_redis):
        """Test cache flush returns 0 when no keys match."""
        mock_client = MagicMock()
        mock_client.keys.return_value = []
        mock_get_redis.return_value = mock_client

        cache = redis_module.RedisCache()
        result = cache.flush()

        assert result == 0

    @patch("lazy_bird.core.redis.get_redis")
    def test_flush_redis_error(self, mock_get_redis):
        """Test cache flush returns 0 on error."""
        from redis.exceptions import RedisError

        mock_client = MagicMock()
        mock_client.keys.side_effect = RedisError("Connection lost")
        mock_get_redis.return_value = mock_client

        cache = redis_module.RedisCache()
        result = cache.flush()

        assert result == 0


class TestConvenienceFunctions:
    """Test convenience functions for FastAPI dependency injection."""

    @patch("lazy_bird.core.redis.get_redis")
    def test_get_redis_client(self, mock_get_redis):
        """Test get_redis_client returns Redis client."""
        mock_client = MagicMock()
        mock_get_redis.return_value = mock_client

        result = redis_module.get_redis_client()

        assert result is mock_client

    @pytest.mark.asyncio
    async def test_get_async_redis_client(self):
        """Test get_async_redis_client returns async Redis client."""
        mock_client = MagicMock()

        with patch("lazy_bird.core.redis.get_async_redis", return_value=mock_client):
            result = await redis_module.get_async_redis_client()

        assert result is mock_client
