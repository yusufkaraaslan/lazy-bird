"""Main FastAPI application for Lazy-Bird v2.0.

This module initializes the FastAPI application with:
- Middleware configuration (CORS, logging, error handling)
- OpenAPI documentation
- Lifecycle events (startup/shutdown)
- API routers
"""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from lazy_bird.api.middleware import setup_middleware
from lazy_bird.core.config import settings
from lazy_bird.core.database import (
    check_async_db_connection,
    check_db_connection,
    drop_async_db,
    drop_db,
    init_async_db,
    init_db,
)
from lazy_bird.core.logging import get_logger, setup_logging
from lazy_bird.core.redis import (
    check_async_redis_connection,
    check_redis_connection,
    close_async_redis,
    close_redis,
)

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan manager.

    Handles startup and shutdown tasks:
    - Database initialization and connection checks
    - Redis connection checks
    - Resource cleanup on shutdown

    Args:
        app: FastAPI application instance

    Yields:
        None
    """
    # Startup tasks
    logger.info("Starting Lazy-Bird API v2.0...")

    # Initialize logging first
    setup_logging()
    logger.info("Logging configured")

    # Initialize databases
    try:
        if settings.USE_ASYNC_DB:
            logger.info("Initializing async database...")
            init_async_db()
            if await check_async_db_connection():
                logger.info("✓ Async database connection successful")
            else:
                logger.error("✗ Async database connection failed")
        else:
            logger.info("Initializing sync database...")
            init_db()
            if check_db_connection():
                logger.info("✓ Database connection successful")
            else:
                logger.error("✗ Database connection failed")
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")

    # Check Redis connection
    try:
        if settings.USE_ASYNC_DB:
            if await check_async_redis_connection():
                logger.info("✓ Async Redis connection successful")
            else:
                logger.warning("✗ Async Redis connection failed (Celery may not work)")
        else:
            if check_redis_connection():
                logger.info("✓ Redis connection successful")
            else:
                logger.warning("✗ Redis connection failed (Celery may not work)")
    except Exception as e:
        logger.warning(f"Redis connection check failed: {e}")

    logger.info("Lazy-Bird API v2.0 started successfully")
    logger.info(f"Environment: {settings.ENVIRONMENT}")
    logger.info(f"Debug mode: {settings.DEBUG}")
    logger.info(f"API documentation: http://{settings.HOST}:{settings.PORT}/docs")

    # Yield control to the application
    yield

    # Shutdown tasks
    logger.info("Shutting down Lazy-Bird API v2.0...")

    # Close Redis connections
    try:
        if settings.USE_ASYNC_DB:
            await close_async_redis()
            logger.info("Async Redis connection closed")
        else:
            close_redis()
            logger.info("Redis connection closed")
    except Exception as e:
        logger.error(f"Error closing Redis connection: {e}")

    # Drop database connections if in test mode
    if settings.ENVIRONMENT == "testing":
        try:
            if settings.USE_ASYNC_DB:
                drop_async_db()
                logger.info("Async database connections dropped")
            else:
                drop_db()
                logger.info("Database connections dropped")
        except Exception as e:
            logger.error(f"Error dropping database connections: {e}")

    logger.info("Lazy-Bird API v2.0 shutdown complete")


# Create FastAPI application instance
app = FastAPI(
    title=settings.API_TITLE,
    description="""
    **Lazy-Bird v2.0** - Progressive Development Automation System

    Enables Claude Code instances to work on software development tasks autonomously.

    ## Features

    - 🤖 **Autonomous Task Execution**: Claude Code agents execute development tasks
    - 📊 **Multi-Project Support**: Manage multiple projects from a single server
    - 🔄 **Framework Agnostic**: Support for 15+ frameworks (Godot, Django, React, etc.)
    - ✅ **Automated Testing**: Test runners for each framework
    - 🔐 **Secure**: API key authentication, JWT tokens, encryption
    - 📈 **Scalable**: From solo dev (Phase 1) to enterprise (Phase 6)
    - 🌐 **RESTful API**: Complete REST API for all operations
    - 📡 **Webhooks**: Event-driven notifications
    - 💰 **Cost Tracking**: Claude API usage monitoring

    ## API Sections

    - **Projects**: Manage development projects
    - **Claude Accounts**: Configure Claude API or subscription accounts
    - **Framework Presets**: Built-in framework configurations
    - **Task Runs**: Execute and monitor automated tasks
    - **Webhooks**: Event subscriptions
    - **API Keys**: Authentication key management
    - **Health**: System health and status endpoints

    ## Authentication

    Most endpoints require authentication via:
    - **API Key**: `X-API-Key` header
    - **JWT Token**: `Authorization: Bearer <token>` header

    ## Links

    - [GitHub Repository](https://github.com/yusyus/lazy-bird)
    - [Documentation](https://github.com/yusyus/lazy-bird/tree/main/Docs)
    - [Issue Tracker](https://github.com/yusyus/lazy-bird/issues)
    """,
    version=settings.API_VERSION,
    openapi_url="/api/v1/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
    # OpenAPI metadata
    contact={
        "name": "Lazy-Bird Team",
        "url": "https://github.com/yusyus/lazy-bird",
        "email": "support@lazy-bird.dev",
    },
    license_info={
        "name": "MIT License",
        "url": "https://github.com/yusyus/lazy-bird/blob/main/LICENSE",
    },
    openapi_tags=[
        {
            "name": "health",
            "description": "System health and status endpoints",
        },
        {
            "name": "projects",
            "description": "Project management operations",
        },
        {
            "name": "claude-accounts",
            "description": "Claude account configuration",
        },
        {
            "name": "framework-presets",
            "description": "Framework preset management",
        },
        {
            "name": "task-runs",
            "description": "Task execution and monitoring",
        },
        {
            "name": "webhooks",
            "description": "Webhook subscription management",
        },
        {
            "name": "api-keys",
            "description": "API key management",
        },
        {
            "name": "auth",
            "description": "Authentication endpoints",
        },
    ],
)

# Setup middleware
setup_middleware(app)

# Register exception handlers
from lazy_bird.api.exceptions import register_exception_handlers

register_exception_handlers(app)

# Import routers
from lazy_bird.api.routers import (
    api_keys_router,
    claude_accounts_router,
    framework_presets_router,
    health_router,
    projects_router,
    task_runs_router,
    webhooks_router,
)

# Include API routers
app.include_router(health_router, prefix="/api/v1")
app.include_router(projects_router, prefix="/api/v1")
app.include_router(task_runs_router, prefix="/api/v1")
app.include_router(claude_accounts_router, prefix="/api/v1")
app.include_router(framework_presets_router, prefix="/api/v1")
app.include_router(api_keys_router, prefix="/api/v1")
app.include_router(webhooks_router, prefix="/api/v1")

# TODO: Add remaining routers when implemented
# app.include_router(auth_router, prefix="/api/v1")


# Root endpoint
@app.get("/", tags=["health"])
async def root() -> JSONResponse:
    """Root endpoint returning API information.

    Returns:
        JSONResponse: API name, version, and documentation links
    """
    return JSONResponse(
        content={
            "name": settings.API_TITLE,
            "version": settings.API_VERSION,
            "status": "operational",
            "environment": settings.ENVIRONMENT,
            "docs": "/docs",
            "redoc": "/redoc",
            "openapi": "/api/v1/openapi.json",
        }
    )


if __name__ == "__main__":
    import uvicorn

    # Run with uvicorn when executed directly
    uvicorn.run(
        "lazy_bird.api.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower(),
    )
