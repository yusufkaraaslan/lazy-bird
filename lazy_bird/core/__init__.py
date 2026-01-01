"""Core infrastructure modules for Lazy-Bird.

This package contains the foundational components used throughout the application:
- config: Application settings and configuration management
- database: SQLAlchemy database connection and session management
- logging: Structured logging with correlation IDs
- security: Authentication and authorization utilities
- redis: Redis client for caching and Celery
"""

from lazy_bird.core.config import Settings, get_settings, settings
from lazy_bird.core.database import (
    AsyncSessionLocal,
    Base,
    SessionLocal,
    async_engine,
    check_async_db_connection,
    check_db_connection,
    drop_async_db,
    drop_db,
    engine,
    get_async_db,
    get_db,
    init_async_db,
    init_db,
)
from lazy_bird.core.logging import (
    clear_correlation_id,
    get_correlation_id,
    get_logger,
    log_with_context,
    set_correlation_id,
    setup_logging,
)
from lazy_bird.core.redis import (
    RedisCache,
    check_async_redis_connection,
    check_redis_connection,
    close_async_redis,
    close_redis,
    get_async_redis,
    get_async_redis_client,
    get_redis,
    get_redis_client,
)
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

__all__ = [
    # Config
    "Settings",
    "get_settings",
    "settings",
    # Database - Base and engines
    "Base",
    "engine",
    "async_engine",
    # Database - Session factories
    "SessionLocal",
    "AsyncSessionLocal",
    # Database - Dependencies
    "get_db",
    "get_async_db",
    # Database - Utilities
    "init_db",
    "drop_db",
    "init_async_db",
    "drop_async_db",
    # Database - Health checks
    "check_db_connection",
    "check_async_db_connection",
    # Logging
    "setup_logging",
    "get_logger",
    "set_correlation_id",
    "clear_correlation_id",
    "get_correlation_id",
    "log_with_context",
    # Security - API Keys
    "generate_api_key",
    "hash_api_key",
    "verify_api_key",
    "get_api_key_prefix",
    # Security - Passwords
    "hash_password",
    "verify_password",
    # Security - JWT Tokens
    "create_access_token",
    "verify_token",
    "create_refresh_token",
    "verify_refresh_token",
    # Security - Utilities
    "generate_secure_random_string",
    "constant_time_compare",
    # Redis - Clients
    "get_redis",
    "get_async_redis",
    "get_redis_client",
    "get_async_redis_client",
    # Redis - Connection Management
    "check_redis_connection",
    "check_async_redis_connection",
    "close_redis",
    "close_async_redis",
    # Redis - Cache
    "RedisCache",
]
