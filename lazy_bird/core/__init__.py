"""Core infrastructure modules for Lazy-Bird.

This package contains the foundational components used throughout the application:
- config: Application settings and configuration management
- database: SQLAlchemy database connection and session management
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
]
