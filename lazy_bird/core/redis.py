"""Redis client utilities for caching and Celery.

This module provides Redis connection management for:
- Celery message broker
- Application caching
- Session storage
"""

import logging
from typing import Optional

import redis
from redis.asyncio import Redis as AsyncRedis
from redis.exceptions import ConnectionError, RedisError

from lazy_bird.core.config import settings

logger = logging.getLogger(__name__)

# Synchronous Redis client
_redis_client: Optional[redis.Redis] = None

# Asynchronous Redis client
_async_redis_client: Optional[AsyncRedis] = None


def get_redis() -> redis.Redis:
    """Get or create synchronous Redis client.

    Returns:
        redis.Redis: Redis client instance

    Raises:
        ConnectionError: If unable to connect to Redis

    Example:
        >>> r = get_redis()
        >>> r.set("key", "value")
        >>> r.get("key")
        b'value'
    """
    global _redis_client

    if _redis_client is None:
        _redis_client = redis.from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True,
            max_connections=settings.REDIS_MAX_CONNECTIONS,
            socket_timeout=settings.REDIS_SOCKET_TIMEOUT,
            socket_connect_timeout=settings.REDIS_SOCKET_TIMEOUT,
        )
        logger.info("Redis client initialized", extra={"extra_fields": {"url": settings.REDIS_URL}})

    return _redis_client


async def get_async_redis() -> AsyncRedis:
    """Get or create asynchronous Redis client.

    Returns:
        AsyncRedis: Async Redis client instance

    Raises:
        ConnectionError: If unable to connect to Redis

    Example:
        >>> r = await get_async_redis()
        >>> await r.set("key", "value")
        >>> await r.get("key")
        'value'
    """
    global _async_redis_client

    if _async_redis_client is None:
        _async_redis_client = await AsyncRedis.from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True,
            max_connections=settings.REDIS_MAX_CONNECTIONS,
            socket_timeout=settings.REDIS_SOCKET_TIMEOUT,
            socket_connect_timeout=settings.REDIS_SOCKET_TIMEOUT,
        )
        logger.info("Async Redis client initialized")

    return _async_redis_client


def check_redis_connection() -> bool:
    """Check if Redis connection is working.

    Returns:
        bool: True if connected, False otherwise

    Example:
        >>> check_redis_connection()
        True
    """
    try:
        r = get_redis()
        r.ping()
        logger.info("Redis connection successful")
        return True
    except (ConnectionError, RedisError) as e:
        logger.error(f"Redis connection failed: {e}")
        return False


async def check_async_redis_connection() -> bool:
    """Check if async Redis connection is working.

    Returns:
        bool: True if connected, False otherwise

    Example:
        >>> await check_async_redis_connection()
        True
    """
    try:
        r = await get_async_redis()
        await r.ping()
        logger.info("Async Redis connection successful")
        return True
    except (ConnectionError, RedisError) as e:
        logger.error(f"Async Redis connection failed: {e}")
        return False


def close_redis() -> None:
    """Close synchronous Redis connection.

    Example:
        >>> close_redis()
    """
    global _redis_client

    if _redis_client is not None:
        _redis_client.close()
        _redis_client = None
        logger.info("Redis client closed")


async def close_async_redis() -> None:
    """Close asynchronous Redis connection.

    Example:
        >>> await close_async_redis()
    """
    global _async_redis_client

    if _async_redis_client is not None:
        await _async_redis_client.close()
        _async_redis_client = None
        logger.info("Async Redis client closed")


class RedisCache:
    """Simple Redis cache wrapper with common operations."""

    def __init__(self, prefix: str = "lazy_bird:", ttl: int = 3600):
        """Initialize cache wrapper.

        Args:
            prefix: Key prefix for namespacing (default: "lazy_bird:")
            ttl: Default time-to-live in seconds (default: 3600 = 1 hour)
        """
        self.prefix = prefix
        self.ttl = ttl
        self.redis = get_redis()

    def _make_key(self, key: str) -> str:
        """Create prefixed key.

        Args:
            key: Raw key

        Returns:
            str: Prefixed key
        """
        return f"{self.prefix}{key}"

    def get(self, key: str) -> Optional[str]:
        """Get value from cache.

        Args:
            key: Cache key

        Returns:
            Optional[str]: Cached value or None if not found

        Example:
            >>> cache = RedisCache()
            >>> cache.get("user:123")
        """
        try:
            return self.redis.get(self._make_key(key))
        except RedisError as e:
            logger.error(f"Cache get failed for key {key}: {e}")
            return None

    def set(self, key: str, value: str, ttl: Optional[int] = None) -> bool:
        """Set value in cache.

        Args:
            key: Cache key
            value: Value to cache
            ttl: Time-to-live in seconds (default: use instance ttl)

        Returns:
            bool: True if successful, False otherwise

        Example:
            >>> cache = RedisCache()
            >>> cache.set("user:123", "John Doe", ttl=300)
        """
        try:
            expiry = ttl if ttl is not None else self.ttl
            self.redis.setex(self._make_key(key), expiry, value)
            return True
        except RedisError as e:
            logger.error(f"Cache set failed for key {key}: {e}")
            return False

    def delete(self, key: str) -> bool:
        """Delete value from cache.

        Args:
            key: Cache key

        Returns:
            bool: True if deleted, False otherwise

        Example:
            >>> cache = RedisCache()
            >>> cache.delete("user:123")
        """
        try:
            self.redis.delete(self._make_key(key))
            return True
        except RedisError as e:
            logger.error(f"Cache delete failed for key {key}: {e}")
            return False

    def exists(self, key: str) -> bool:
        """Check if key exists in cache.

        Args:
            key: Cache key

        Returns:
            bool: True if exists, False otherwise

        Example:
            >>> cache = RedisCache()
            >>> cache.exists("user:123")
        """
        try:
            return self.redis.exists(self._make_key(key)) > 0
        except RedisError as e:
            logger.error(f"Cache exists check failed for key {key}: {e}")
            return False

    def flush(self, pattern: Optional[str] = None) -> int:
        """Flush cache keys matching pattern.

        Args:
            pattern: Key pattern (default: flush all keys with prefix)

        Returns:
            int: Number of keys deleted

        Example:
            >>> cache = RedisCache()
            >>> cache.flush("user:*")  # Delete all user keys
        """
        try:
            search_pattern = self._make_key(pattern if pattern else "*")
            keys = self.redis.keys(search_pattern)
            if keys:
                return self.redis.delete(*keys)
            return 0
        except RedisError as e:
            logger.error(f"Cache flush failed: {e}")
            return 0


# Convenience function for FastAPI dependency injection
def get_redis_client() -> redis.Redis:
    """FastAPI dependency for Redis client.

    Yields:
        redis.Redis: Redis client instance

    Example:
        >>> from fastapi import Depends
        >>> @app.get("/")
        >>> def endpoint(redis: redis.Redis = Depends(get_redis_client)):
        >>>     redis.set("key", "value")
    """
    return get_redis()


# Convenience function for async FastAPI dependency injection
async def get_async_redis_client() -> AsyncRedis:
    """FastAPI dependency for async Redis client.

    Yields:
        AsyncRedis: Async Redis client instance

    Example:
        >>> from fastapi import Depends
        >>> @app.get("/")
        >>> async def endpoint(redis: AsyncRedis = Depends(get_async_redis_client)):
        >>>     await redis.set("key", "value")
    """
    return await get_async_redis()
