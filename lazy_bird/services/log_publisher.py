"""Log publisher service for real-time log streaming via Redis Pub/Sub.

This module provides the LogPublisher class for publishing task execution logs
to Redis channels, enabling real-time log streaming to frontends via SSE.
"""

import json
import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional

from redis.exceptions import ConnectionError, RedisError

from lazy_bird.core.redis import get_async_redis, get_redis

logger = logging.getLogger(__name__)


class LogPublisher:
    """Service for publishing logs to Redis Pub/Sub channels.

    Publishes log messages to Redis channels for real-time streaming.
    Supports both synchronous and asynchronous publishing.

    Channel naming convention:
    - Task logs: `lazy_bird:logs:task:{task_id}`
    - Project logs: `lazy_bird:logs:project:{project_id}`
    - System logs: `lazy_bird:logs:system`
    """

    # Channel prefix
    CHANNEL_PREFIX = "lazy_bird:logs"

    # Log retention (seconds) - logs expire after 1 hour by default
    DEFAULT_LOG_TTL = 3600

    def __init__(self, use_async: bool = False):
        """Initialize LogPublisher.

        Args:
            use_async: Use async Redis client (default: False)
        """
        self.use_async = use_async
        self._redis = None

    def _get_client(self):
        """Get Redis client (sync or async).

        Returns:
            redis.Redis or AsyncRedis: Redis client
        """
        if self._redis is None:
            if self.use_async:
                # Async client needs to be awaited
                return None  # Will be created in async methods
            else:
                self._redis = get_redis()
        return self._redis

    def publish_log(
        self,
        message: str,
        level: str = "INFO",
        task_id: Optional[str] = None,
        project_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Publish log message to Redis channel (synchronous).

        Args:
            message: Log message
            level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            task_id: Task ID (if task-specific log)
            project_id: Project ID (if project-specific log)
            metadata: Additional metadata to include

        Returns:
            bool: True if published successfully, False otherwise

        Example:
            >>> publisher = LogPublisher()
            >>> publisher.publish_log(
            ...     message="Task started",
            ...     level="INFO",
            ...     task_id="123e4567-e89b-12d3-a456-426614174000",
            ...     project_id="my-project",
            ... )
            True
        """
        try:
            client = self._get_client()
            if client is None:
                logger.error("Redis client not initialized")
                return False

            # Build log entry
            log_entry = self._build_log_entry(
                message=message,
                level=level,
                task_id=task_id,
                project_id=project_id,
                metadata=metadata,
            )

            # Determine channel
            channel = self._get_channel(task_id=task_id, project_id=project_id)

            # Publish to Redis
            log_json = json.dumps(log_entry)
            subscribers = client.publish(channel, log_json)

            logger.debug(
                f"Published log to {channel}",
                extra={
                    "extra_fields": {
                        "channel": channel,
                        "subscribers": subscribers,
                        "level": level,
                    }
                },
            )

            # Also store in a list for history (with TTL)
            self._store_log_history(client, channel, log_json)

            return True

        except (ConnectionError, RedisError) as e:
            logger.error(
                f"Failed to publish log: {e}",
                extra={"extra_fields": {"error": str(e)}},
            )
            return False

    async def publish_log_async(
        self,
        message: str,
        level: str = "INFO",
        task_id: Optional[str] = None,
        project_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Publish log message to Redis channel (asynchronous).

        Args:
            message: Log message
            level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            task_id: Task ID (if task-specific log)
            project_id: Project ID (if project-specific log)
            metadata: Additional metadata to include

        Returns:
            bool: True if published successfully, False otherwise

        Example:
            >>> publisher = LogPublisher(use_async=True)
            >>> await publisher.publish_log_async(
            ...     message="Task started",
            ...     level="INFO",
            ...     task_id="123e4567-e89b-12d3-a456-426614174000",
            ... )
            True
        """
        try:
            client = await get_async_redis()

            # Build log entry
            log_entry = self._build_log_entry(
                message=message,
                level=level,
                task_id=task_id,
                project_id=project_id,
                metadata=metadata,
            )

            # Determine channel
            channel = self._get_channel(task_id=task_id, project_id=project_id)

            # Publish to Redis
            log_json = json.dumps(log_entry)
            subscribers = await client.publish(channel, log_json)

            logger.debug(
                f"Published log to {channel}",
                extra={
                    "extra_fields": {
                        "channel": channel,
                        "subscribers": subscribers,
                        "level": level,
                    }
                },
            )

            # Also store in a list for history (with TTL)
            await self._store_log_history_async(client, channel, log_json)

            return True

        except (ConnectionError, RedisError) as e:
            logger.error(
                f"Failed to publish log: {e}",
                extra={"extra_fields": {"error": str(e)}},
            )
            return False

    def _build_log_entry(
        self,
        message: str,
        level: str,
        task_id: Optional[str],
        project_id: Optional[str],
        metadata: Optional[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Build structured log entry.

        Args:
            message: Log message
            level: Log level
            task_id: Task ID (optional)
            project_id: Project ID (optional)
            metadata: Additional metadata (optional)

        Returns:
            dict: Structured log entry
        """
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": level.upper(),
            "message": message,
        }

        if task_id:
            entry["task_id"] = task_id

        if project_id:
            entry["project_id"] = project_id

        if metadata:
            entry["metadata"] = metadata

        return entry

    def _get_channel(self, task_id: Optional[str] = None, project_id: Optional[str] = None) -> str:
        """Get Redis channel name based on context.

        Args:
            task_id: Task ID (optional)
            project_id: Project ID (optional)

        Returns:
            str: Channel name

        Channel priority:
        1. Task-specific: lazy_bird:logs:task:{task_id}
        2. Project-specific: lazy_bird:logs:project:{project_id}
        3. System-wide: lazy_bird:logs:system
        """
        if task_id:
            return f"{self.CHANNEL_PREFIX}:task:{task_id}"
        elif project_id:
            return f"{self.CHANNEL_PREFIX}:project:{project_id}"
        else:
            return f"{self.CHANNEL_PREFIX}:system"

    def _store_log_history(self, client, channel: str, log_json: str) -> None:
        """Store log in history list with TTL (synchronous).

        Args:
            client: Redis client
            channel: Channel name
            log_json: JSON-encoded log entry
        """
        try:
            # Store in a list for history
            history_key = f"{channel}:history"
            client.lpush(history_key, log_json)

            # Limit list to last 1000 entries
            client.ltrim(history_key, 0, 999)

            # Set expiration on the history key
            client.expire(history_key, self.DEFAULT_LOG_TTL)

        except RedisError as e:
            logger.warning(f"Failed to store log history: {e}")

    async def _store_log_history_async(self, client, channel: str, log_json: str) -> None:
        """Store log in history list with TTL (asynchronous).

        Args:
            client: Async Redis client
            channel: Channel name
            log_json: JSON-encoded log entry
        """
        try:
            # Store in a list for history
            history_key = f"{channel}:history"
            await client.lpush(history_key, log_json)

            # Limit list to last 1000 entries
            await client.ltrim(history_key, 0, 999)

            # Set expiration on the history key
            await client.expire(history_key, self.DEFAULT_LOG_TTL)

        except RedisError as e:
            logger.warning(f"Failed to store log history: {e}")

    def get_log_history(
        self,
        task_id: Optional[str] = None,
        project_id: Optional[str] = None,
        limit: int = 100,
    ) -> list:
        """Get log history from Redis (synchronous).

        Args:
            task_id: Task ID (optional)
            project_id: Project ID (optional)
            limit: Maximum number of logs to retrieve (default: 100)

        Returns:
            list: List of log entries (most recent first)

        Example:
            >>> publisher = LogPublisher()
            >>> logs = publisher.get_log_history(task_id="task-123", limit=50)
            >>> for log in logs:
            ...     print(log["message"])
        """
        try:
            client = self._get_client()
            if client is None:
                return []

            channel = self._get_channel(task_id=task_id, project_id=project_id)
            history_key = f"{channel}:history"

            # Get logs from history list
            log_entries = client.lrange(history_key, 0, limit - 1)

            # Parse JSON entries
            return [json.loads(entry) for entry in log_entries]

        except (ConnectionError, RedisError) as e:
            logger.error(f"Failed to get log history: {e}")
            return []

    async def get_log_history_async(
        self,
        task_id: Optional[str] = None,
        project_id: Optional[str] = None,
        limit: int = 100,
    ) -> list:
        """Get log history from Redis (asynchronous).

        Args:
            task_id: Task ID (optional)
            project_id: Project ID (optional)
            limit: Maximum number of logs to retrieve (default: 100)

        Returns:
            list: List of log entries (most recent first)

        Example:
            >>> publisher = LogPublisher(use_async=True)
            >>> logs = await publisher.get_log_history_async(task_id="task-123")
            >>> for log in logs:
            ...     print(log["message"])
        """
        try:
            client = await get_async_redis()

            channel = self._get_channel(task_id=task_id, project_id=project_id)
            history_key = f"{channel}:history"

            # Get logs from history list
            log_entries = await client.lrange(history_key, 0, limit - 1)

            # Parse JSON entries
            return [json.loads(entry) for entry in log_entries]

        except (ConnectionError, RedisError) as e:
            logger.error(f"Failed to get log history: {e}")
            return []


# Convenience function for publishing logs
def publish_task_log(
    message: str,
    task_id: str,
    level: str = "INFO",
    project_id: Optional[str] = None,
    **metadata,
) -> bool:
    """Convenience function to publish task-specific log.

    Args:
        message: Log message
        task_id: Task ID
        level: Log level (default: INFO)
        project_id: Project ID (optional)
        **metadata: Additional metadata as keyword arguments

    Returns:
        bool: True if published successfully

    Example:
        >>> publish_task_log(
        ...     "Running tests",
        ...     task_id="task-123",
        ...     level="INFO",
        ...     test_framework="pytest"
        ... )
        True
    """
    publisher = LogPublisher()
    return publisher.publish_log(
        message=message,
        level=level,
        task_id=task_id,
        project_id=project_id,
        metadata=metadata if metadata else None,
    )


__all__ = [
    "LogPublisher",
    "publish_task_log",
]
