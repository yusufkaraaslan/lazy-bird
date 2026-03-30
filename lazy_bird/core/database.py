"""Database connection and session management.

This module provides the SQLAlchemy engine, session factory, and
declarative base for all database models. It uses SQLAlchemy 2.0 syntax
with async support and proper connection pooling.
"""

from typing import AsyncGenerator, Generator

from sqlalchemy import create_engine, event, pool, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Session, sessionmaker

from lazy_bird.core.config import settings

# =============================================================================
# DECLARATIVE BASE
# =============================================================================

Base = declarative_base()
"""SQLAlchemy declarative base for all models.

All database models should inherit from this base class.

Example:
    ```python
    from lazy_bird.core.database import Base

    class Project(Base):
        __tablename__ = "projects"
        id = Column(Integer, primary_key=True)
    ```
"""

# =============================================================================
# SYNCHRONOUS DATABASE (for migrations, admin tasks)
# =============================================================================

engine = create_engine(
    settings.DATABASE_URL,
    pool_size=settings.DB_POOL_SIZE,
    max_overflow=settings.DB_MAX_OVERFLOW,
    pool_timeout=settings.DB_POOL_TIMEOUT,
    pool_recycle=settings.DB_POOL_RECYCLE,
    pool_pre_ping=True,  # Verify connections before using
    echo=settings.DB_ECHO,  # Log SQL queries if enabled
    future=True,  # Use SQLAlchemy 2.0 style
)
"""Synchronous SQLAlchemy engine for database operations.

Uses connection pooling with the following configuration:
- Pool size: Configured via DB_POOL_SIZE
- Max overflow: Configured via DB_MAX_OVERFLOW
- Pool timeout: Configured via DB_POOL_TIMEOUT
- Pool recycle: Configured via DB_POOL_RECYCLE
- Pool pre-ping: Enabled (validates connections)
- Echo: Configured via DB_ECHO (development only)

Used for:
- Database migrations (Alembic)
- Admin scripts and CLI tools
- Background tasks (Celery)
"""


SessionLocal = sessionmaker(
    bind=engine,
    class_=Session,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,  # Keep objects usable after commit
    future=True,  # Use SQLAlchemy 2.0 style
)
"""Synchronous session factory for database transactions.

Creates new database sessions for each request/task.
Sessions should always be used with context managers.

Example:
    ```python
    from lazy_bird.core.database import SessionLocal

    # Using context manager (recommended)
    with SessionLocal() as db:
        projects = db.query(Project).all()
        db.commit()

    # Using FastAPI dependency
    def get_db():
        db = SessionLocal()
        try:
            yield db
        finally:
            db.close()
    ```
"""

# =============================================================================
# ASYNCHRONOUS DATABASE (for FastAPI endpoints)
# =============================================================================

# Convert PostgreSQL URL to async version (postgresql+asyncpg://)
async_database_url = settings.DATABASE_URL.replace(
    "postgresql://", "postgresql+asyncpg://"
).replace("postgresql+psycopg2://", "postgresql+asyncpg://")

async_engine = create_async_engine(
    async_database_url,
    pool_size=settings.DB_POOL_SIZE,
    max_overflow=settings.DB_MAX_OVERFLOW,
    pool_timeout=settings.DB_POOL_TIMEOUT,
    pool_recycle=settings.DB_POOL_RECYCLE,
    pool_pre_ping=True,
    echo=settings.DB_ECHO,
    future=True,
)
"""Asynchronous SQLAlchemy engine for FastAPI endpoints.

Uses asyncpg driver for high-performance async database operations.
Configuration matches synchronous engine for consistency.

Used for:
- FastAPI endpoint handlers
- Real-time SSE streams
- Async background tasks
"""

AsyncSessionLocal = async_sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
    future=True,
)
"""Asynchronous session factory for FastAPI endpoints.

Creates new async database sessions for each request.
Must be used with async context managers.

Example:
    ```python
    from lazy_bird.core.database import AsyncSessionLocal

    # Using async context manager
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Project))
        projects = result.scalars().all()
        await db.commit()

    # Using FastAPI dependency
    async def get_async_db():
        async with AsyncSessionLocal() as db:
            yield db
    ```
"""

# =============================================================================
# DATABASE DEPENDENCIES (for FastAPI)
# =============================================================================


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency for synchronous database sessions.

    Provides a database session to FastAPI endpoints.
    Automatically handles session lifecycle and cleanup.

    Yields:
        Session: SQLAlchemy database session

    Example:
        ```python
        from fastapi import Depends
        from sqlalchemy.orm import Session
        from lazy_bird.core.database import get_db

        @app.get("/projects")
        def list_projects(db: Session = Depends(get_db)):
            projects = db.query(Project).all()
            return projects
        ```

    Note:
        - Session is automatically committed on success
        - Session is automatically rolled back on exception
        - Session is always closed after request
    """
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


async def get_async_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency for asynchronous database sessions.

    Provides an async database session to FastAPI endpoints.
    Automatically handles session lifecycle and cleanup.

    Yields:
        AsyncSession: Async SQLAlchemy database session

    Example:
        ```python
        from fastapi import Depends
        from sqlalchemy.ext.asyncio import AsyncSession
        from lazy_bird.core.database import get_async_db

        @app.get("/projects")
        async def list_projects(db: AsyncSession = Depends(get_async_db)):
            result = await db.execute(select(Project))
            projects = result.scalars().all()
            return projects
        ```

    Note:
        - Session is automatically committed on success
        - Session is automatically rolled back on exception
        - Session is always closed after request
    """
    async with AsyncSessionLocal() as db:
        try:
            yield db
            await db.commit()
        except Exception:
            await db.rollback()
            raise


# =============================================================================
# DATABASE UTILITIES
# =============================================================================


def init_db() -> None:
    """Initialize database schema.

    Creates all tables defined in SQLAlchemy models.
    Should only be used in development or testing.

    For production, use Alembic migrations instead.

    Example:
        ```python
        from lazy_bird.core.database import init_db

        # Development setup
        init_db()  # Creates all tables
        ```

    Warning:
        This does NOT run migrations. Use `alembic upgrade head` for production.
    """
    Base.metadata.create_all(bind=engine)


def drop_db() -> None:
    """Drop all database tables.

    Removes all tables defined in SQLAlchemy models.
    DANGEROUS - Only use in development or testing.

    Example:
        ```python
        from lazy_bird.core.database import drop_db

        # Testing cleanup
        drop_db()  # Removes all tables
        ```

    Warning:
        This will DELETE ALL DATA. Use with extreme caution.
        Never call this in production.
    """
    Base.metadata.drop_all(bind=engine)


async def init_async_db() -> None:
    """Initialize database schema asynchronously.

    Async version of init_db(). Creates all tables.
    Should only be used in development or testing.

    For production, use Alembic migrations instead.

    Example:
        ```python
        from lazy_bird.core.database import init_async_db

        # Async development setup
        await init_async_db()
        ```

    Warning:
        This does NOT run migrations. Use `alembic upgrade head` for production.
    """
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def drop_async_db() -> None:
    """Drop all database tables asynchronously.

    Async version of drop_db(). Removes all tables.
    DANGEROUS - Only use in development or testing.

    Example:
        ```python
        from lazy_bird.core.database import drop_async_db

        # Async testing cleanup
        await drop_async_db()
        ```

    Warning:
        This will DELETE ALL DATA. Use with extreme caution.
        Never call this in production.
    """
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


# =============================================================================
# CONNECTION POOL MONITORING (optional, for debugging)
# =============================================================================


@event.listens_for(pool.Pool, "connect")
def receive_connect(dbapi_conn, connection_record):
    """Event listener for new database connections.

    Logs when new connections are created in the pool.
    Useful for debugging connection issues.

    Args:
        dbapi_conn: Database API connection
        connection_record: SQLAlchemy connection record
    """
    if settings.DB_ECHO:
        print(f"Database connection opened: {id(dbapi_conn)}")


@event.listens_for(pool.Pool, "checkout")
def receive_checkout(dbapi_conn, connection_record, connection_proxy):
    """Event listener for connection checkout from pool.

    Logs when connections are checked out from the pool.
    Useful for debugging connection pool exhaustion.

    Args:
        dbapi_conn: Database API connection
        connection_record: SQLAlchemy connection record
        connection_proxy: Connection proxy
    """
    if settings.DB_ECHO:
        print(f"Database connection checked out: {id(dbapi_conn)}")


@event.listens_for(pool.Pool, "checkin")
def receive_checkin(dbapi_conn, connection_record):
    """Event listener for connection checkin to pool.

    Logs when connections are returned to the pool.
    Useful for debugging connection leaks.

    Args:
        dbapi_conn: Database API connection
        connection_record: SQLAlchemy connection record
    """
    if settings.DB_ECHO:
        print(f"Database connection checked in: {id(dbapi_conn)}")


# =============================================================================
# HEALTH CHECK
# =============================================================================


def check_db_connection() -> bool:
    """Check if database connection is healthy.

    Attempts to execute a simple query to verify database connectivity.

    Returns:
        bool: True if connection is healthy, False otherwise

    Example:
        ```python
        from lazy_bird.core.database import check_db_connection

        if check_db_connection():
            print("Database is healthy")
        else:
            print("Database is down")
        ```
    """
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception as e:
        if settings.DB_ECHO:
            print(f"Database health check failed: {e}")
        return False


async def check_async_db_connection() -> bool:
    """Check if async database connection is healthy.

    Async version of check_db_connection().
    Attempts to execute a simple query to verify database connectivity.

    Returns:
        bool: True if connection is healthy, False otherwise

    Example:
        ```python
        from lazy_bird.core.database import check_async_db_connection

        if await check_async_db_connection():
            print("Async database is healthy")
        else:
            print("Async database is down")
        ```
    """
    try:
        async with async_engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return True
    except Exception as e:
        if settings.DB_ECHO:
            print(f"Async database health check failed: {e}")
        return False
