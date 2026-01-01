"""Health check endpoints for system monitoring.

This module provides health check endpoints for:
- Overall system health
- Database connection status
- Redis connection status
- Celery worker status
- Disk space and memory usage
"""

import os
import shutil
from datetime import datetime
from typing import Any, Dict

import psutil
from fastapi import APIRouter, status
from fastapi.responses import JSONResponse

from lazy_bird.core.config import settings
from lazy_bird.core.database import check_async_db_connection, check_db_connection
from lazy_bird.core.logging import get_logger
from lazy_bird.core.redis import check_async_redis_connection, check_redis_connection

logger = get_logger(__name__)

# Create router
router = APIRouter(prefix="/health", tags=["health"])


async def check_database() -> Dict[str, Any]:
    """Check database connection status.

    Returns:
        Dict[str, Any]: Database health status
    """
    try:
        if settings.USE_ASYNC_DB:
            is_healthy = await check_async_db_connection()
        else:
            is_healthy = check_db_connection()

        return {
            "status": "healthy" if is_healthy else "unhealthy",
            "database_url": settings.DATABASE_URL.split("@")[-1] if "@" in settings.DATABASE_URL else "unknown",
            "mode": "async" if settings.USE_ASYNC_DB else "sync",
        }
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e),
        }


async def check_redis_status() -> Dict[str, Any]:
    """Check Redis connection status.

    Returns:
        Dict[str, Any]: Redis health status
    """
    try:
        if settings.USE_ASYNC_DB:
            is_healthy = await check_async_redis_connection()
        else:
            is_healthy = check_redis_connection()

        return {
            "status": "healthy" if is_healthy else "unhealthy",
            "redis_url": settings.REDIS_URL.split("@")[-1] if "@" in settings.REDIS_URL else "unknown",
        }
    except Exception as e:
        logger.error(f"Redis health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e),
        }


async def check_celery_status() -> Dict[str, Any]:
    """Check Celery worker status.

    Returns:
        Dict[str, Any]: Celery health status
    """
    try:
        # Import Celery app
        from lazy_bird.tasks import celery_app

        # Get active workers
        inspect = celery_app.control.inspect(timeout=2.0)
        active_workers = inspect.active()

        if active_workers:
            worker_count = len(active_workers)
            total_tasks = sum(len(tasks) for tasks in active_workers.values())

            return {
                "status": "healthy",
                "workers": worker_count,
                "active_tasks": total_tasks,
                "worker_names": list(active_workers.keys()),
            }
        else:
            return {
                "status": "degraded",
                "workers": 0,
                "message": "No active Celery workers found",
            }
    except ImportError:
        return {
            "status": "not_configured",
            "message": "Celery tasks module not yet implemented",
        }
    except Exception as e:
        logger.error(f"Celery health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e),
        }


def get_system_metrics() -> Dict[str, Any]:
    """Get system resource metrics.

    Returns:
        Dict[str, Any]: System metrics (CPU, memory, disk)
    """
    try:
        # Memory usage
        memory = psutil.virtual_memory()

        # Disk usage (current directory)
        disk = shutil.disk_usage(os.getcwd())

        # CPU usage (1 second average)
        cpu_percent = psutil.cpu_percent(interval=1)

        return {
            "cpu": {
                "usage_percent": cpu_percent,
                "cores": psutil.cpu_count(),
            },
            "memory": {
                "total_mb": round(memory.total / (1024 * 1024)),
                "available_mb": round(memory.available / (1024 * 1024)),
                "used_mb": round(memory.used / (1024 * 1024)),
                "percent": memory.percent,
            },
            "disk": {
                "total_gb": round(disk.total / (1024 * 1024 * 1024)),
                "used_gb": round(disk.used / (1024 * 1024 * 1024)),
                "free_gb": round(disk.free / (1024 * 1024 * 1024)),
                "percent": round((disk.used / disk.total) * 100, 1),
            },
        }
    except Exception as e:
        logger.error(f"System metrics collection failed: {e}")
        return {
            "error": str(e),
        }


@router.get("", response_class=JSONResponse)
@router.get("/", response_class=JSONResponse)
async def health_check() -> JSONResponse:
    """Comprehensive health check endpoint.

    Checks:
    - Database connection
    - Redis connection
    - Celery workers
    - System metrics

    Returns:
        JSONResponse: Overall health status

    Status Codes:
        - 200: All systems healthy
        - 503: One or more systems unhealthy
    """
    # Check all services
    db_health = await check_database()
    redis_health = await check_redis_status()
    celery_health = await check_celery_status()
    system_metrics = get_system_metrics()

    # Determine overall status
    is_healthy = (
        db_health.get("status") == "healthy"
        and redis_health.get("status") == "healthy"
        and celery_health.get("status") in ("healthy", "degraded", "not_configured")
    )

    overall_status = "healthy" if is_healthy else "unhealthy"

    response = {
        "status": overall_status,
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "version": settings.API_VERSION,
        "environment": settings.ENVIRONMENT,
        "services": {
            "database": db_health,
            "redis": redis_health,
            "celery": celery_health,
        },
        "system": system_metrics,
    }

    # Return appropriate status code
    status_code = status.HTTP_200_OK if is_healthy else status.HTTP_503_SERVICE_UNAVAILABLE

    return JSONResponse(content=response, status_code=status_code)


@router.get("/live", response_class=JSONResponse)
async def liveness_probe() -> JSONResponse:
    """Kubernetes liveness probe endpoint.

    Simple check that the application is running.

    Returns:
        JSONResponse: Basic liveness status

    Status Codes:
        - 200: Application is alive
    """
    return JSONResponse(
        content={
            "status": "alive",
            "timestamp": datetime.utcnow().isoformat() + "Z",
        },
        status_code=status.HTTP_200_OK,
    )


@router.get("/ready", response_class=JSONResponse)
async def readiness_probe() -> JSONResponse:
    """Kubernetes readiness probe endpoint.

    Checks if application is ready to serve traffic.
    Requires database and Redis to be healthy.

    Returns:
        JSONResponse: Readiness status

    Status Codes:
        - 200: Application is ready
        - 503: Application is not ready
    """
    # Check critical services only (no Celery check for readiness)
    db_health = await check_database()
    redis_health = await check_redis_status()

    is_ready = (
        db_health.get("status") == "healthy" and redis_health.get("status") == "healthy"
    )

    response = {
        "status": "ready" if is_ready else "not_ready",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "services": {
            "database": db_health.get("status"),
            "redis": redis_health.get("status"),
        },
    }

    status_code = status.HTTP_200_OK if is_ready else status.HTTP_503_SERVICE_UNAVAILABLE

    return JSONResponse(content=response, status_code=status_code)


@router.get("/startup", response_class=JSONResponse)
async def startup_probe() -> JSONResponse:
    """Kubernetes startup probe endpoint.

    Checks if application has started successfully.
    More lenient than readiness probe during startup.

    Returns:
        JSONResponse: Startup status

    Status Codes:
        - 200: Application has started
        - 503: Application is still starting
    """
    # Just check if database is reachable
    db_health = await check_database()

    is_started = db_health.get("status") == "healthy"

    response = {
        "status": "started" if is_started else "starting",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "database": db_health.get("status"),
    }

    status_code = status.HTTP_200_OK if is_started else status.HTTP_503_SERVICE_UNAVAILABLE

    return JSONResponse(content=response, status_code=status_code)
