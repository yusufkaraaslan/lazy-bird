"""Unit tests for lazy_bird.api.routers.health module.

Tests health check, liveness, readiness, and startup probe endpoints.
"""

from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

from lazy_bird.api.routers.health import (
    check_celery_status,
    check_database,
    check_redis_status,
    get_system_metrics,
)


class TestCheckDatabase:
    """Test check_database helper function."""

    @pytest.mark.asyncio
    @patch("lazy_bird.api.routers.health.settings")
    @patch("lazy_bird.api.routers.health.check_db_connection")
    async def test_check_database_sync_healthy(self, mock_check, mock_settings):
        """Test sync database health check when healthy."""
        mock_settings.USE_ASYNC_DB = False
        mock_settings.DATABASE_URL = "postgresql://user:pass@localhost:5432/db"
        mock_check.return_value = True

        result = await check_database()

        assert result["status"] == "healthy"
        assert result["mode"] == "sync"

    @pytest.mark.asyncio
    @patch("lazy_bird.api.routers.health.settings")
    @patch("lazy_bird.api.routers.health.check_db_connection")
    async def test_check_database_sync_unhealthy(self, mock_check, mock_settings):
        """Test sync database health check when unhealthy."""
        mock_settings.USE_ASYNC_DB = False
        mock_settings.DATABASE_URL = "postgresql://user:pass@localhost:5432/db"
        mock_check.return_value = False

        result = await check_database()

        assert result["status"] == "unhealthy"

    @pytest.mark.asyncio
    @patch("lazy_bird.api.routers.health.settings")
    @patch("lazy_bird.api.routers.health.check_async_db_connection")
    async def test_check_database_async_healthy(self, mock_check, mock_settings):
        """Test async database health check when healthy."""
        mock_settings.USE_ASYNC_DB = True
        mock_settings.DATABASE_URL = "postgresql://user:pass@localhost:5432/db"
        mock_check.return_value = True

        result = await check_database()

        assert result["status"] == "healthy"
        assert result["mode"] == "async"

    @pytest.mark.asyncio
    @patch("lazy_bird.api.routers.health.settings")
    @patch("lazy_bird.api.routers.health.check_db_connection")
    async def test_check_database_exception(self, mock_check, mock_settings):
        """Test database health check when exception occurs."""
        mock_settings.USE_ASYNC_DB = False
        mock_check.side_effect = Exception("Connection refused")

        result = await check_database()

        assert result["status"] == "unhealthy"
        assert "error" in result


class TestCheckRedisStatus:
    """Test check_redis_status helper function."""

    @pytest.mark.asyncio
    @patch("lazy_bird.api.routers.health.settings")
    @patch("lazy_bird.api.routers.health.check_redis_connection")
    async def test_check_redis_sync_healthy(self, mock_check, mock_settings):
        """Test sync Redis health check when healthy."""
        mock_settings.USE_ASYNC_DB = False
        mock_settings.REDIS_URL = "redis://localhost:6379/0"
        mock_check.return_value = True

        result = await check_redis_status()

        assert result["status"] == "healthy"

    @pytest.mark.asyncio
    @patch("lazy_bird.api.routers.health.settings")
    @patch("lazy_bird.api.routers.health.check_redis_connection")
    async def test_check_redis_sync_unhealthy(self, mock_check, mock_settings):
        """Test sync Redis health check when unhealthy."""
        mock_settings.USE_ASYNC_DB = False
        mock_settings.REDIS_URL = "redis://localhost:6379/0"
        mock_check.return_value = False

        result = await check_redis_status()

        assert result["status"] == "unhealthy"

    @pytest.mark.asyncio
    @patch("lazy_bird.api.routers.health.settings")
    @patch("lazy_bird.api.routers.health.check_async_redis_connection")
    async def test_check_redis_async_healthy(self, mock_check, mock_settings):
        """Test async Redis health check when healthy."""
        mock_settings.USE_ASYNC_DB = True
        mock_settings.REDIS_URL = "redis://localhost:6379/0"
        mock_check.return_value = True

        result = await check_redis_status()

        assert result["status"] == "healthy"

    @pytest.mark.asyncio
    @patch("lazy_bird.api.routers.health.settings")
    async def test_check_redis_exception(self, mock_settings):
        """Test Redis health check when exception occurs."""
        mock_settings.USE_ASYNC_DB = False
        with patch(
            "lazy_bird.api.routers.health.check_redis_connection",
            side_effect=Exception("Redis down"),
        ):
            result = await check_redis_status()

        assert result["status"] == "unhealthy"
        assert "error" in result


class TestCheckCeleryStatus:
    """Test check_celery_status helper function."""

    @pytest.mark.asyncio
    async def test_check_celery_with_workers(self):
        """Test Celery health check when workers are active."""
        mock_celery = MagicMock()
        mock_inspect = MagicMock()
        mock_inspect.active.return_value = {
            "worker1@host": [{"id": "task-1"}],
            "worker2@host": [],
        }
        mock_celery.control.inspect.return_value = mock_inspect

        with patch("lazy_bird.api.routers.health.celery_app", mock_celery, create=True):
            with patch.dict("sys.modules", {"lazy_bird.tasks": MagicMock(celery_app=mock_celery)}):
                result = await check_celery_status()

        assert result["status"] == "healthy"
        assert result["workers"] == 2
        assert result["active_tasks"] == 1

    @pytest.mark.asyncio
    async def test_check_celery_no_workers(self):
        """Test Celery health check when no workers are active."""
        mock_celery = MagicMock()
        mock_inspect = MagicMock()
        mock_inspect.active.return_value = None
        mock_celery.control.inspect.return_value = mock_inspect

        with patch.dict("sys.modules", {"lazy_bird.tasks": MagicMock(celery_app=mock_celery)}):
            result = await check_celery_status()

        assert result["status"] == "degraded"
        assert result["workers"] == 0

    @pytest.mark.asyncio
    async def test_check_celery_import_error(self):
        """Test Celery health check when module not available."""
        with patch.dict("sys.modules", {"lazy_bird.tasks": None}):
            with patch(
                "builtins.__import__",
                side_effect=ImportError("No module named 'lazy_bird.tasks'"),
            ):
                result = await check_celery_status()

        assert result["status"] in ("not_configured", "unhealthy")

    @pytest.mark.asyncio
    async def test_check_celery_exception(self):
        """Test Celery health check when exception occurs."""
        mock_celery = MagicMock()
        mock_celery.control.inspect.side_effect = Exception("Connection refused")

        with patch.dict("sys.modules", {"lazy_bird.tasks": MagicMock(celery_app=mock_celery)}):
            result = await check_celery_status()

        assert result["status"] == "unhealthy"
        assert "error" in result


class TestGetSystemMetrics:
    """Test get_system_metrics function."""

    @patch("lazy_bird.api.routers.health.psutil")
    @patch("lazy_bird.api.routers.health.shutil")
    def test_get_system_metrics_success(self, mock_shutil, mock_psutil):
        """Test successful system metrics collection."""
        # Mock memory
        mock_memory = MagicMock()
        mock_memory.total = 16 * 1024 * 1024 * 1024  # 16 GB
        mock_memory.available = 8 * 1024 * 1024 * 1024
        mock_memory.used = 8 * 1024 * 1024 * 1024
        mock_memory.percent = 50.0
        mock_psutil.virtual_memory.return_value = mock_memory

        # Mock CPU
        mock_psutil.cpu_percent.return_value = 25.0
        mock_psutil.cpu_count.return_value = 8

        # Mock disk
        mock_disk = MagicMock()
        mock_disk.total = 500 * 1024 * 1024 * 1024  # 500 GB
        mock_disk.used = 200 * 1024 * 1024 * 1024
        mock_disk.free = 300 * 1024 * 1024 * 1024
        mock_shutil.disk_usage.return_value = mock_disk

        result = get_system_metrics()

        assert result["cpu"]["usage_percent"] == 25.0
        assert result["cpu"]["cores"] == 8
        assert result["memory"]["total_mb"] == 16384
        assert result["memory"]["percent"] == 50.0
        assert result["disk"]["total_gb"] == 500
        assert result["disk"]["free_gb"] == 300

    @patch("lazy_bird.api.routers.health.psutil")
    def test_get_system_metrics_exception(self, mock_psutil):
        """Test system metrics collection when exception occurs."""
        mock_psutil.virtual_memory.side_effect = Exception("Permission denied")

        result = get_system_metrics()

        assert "error" in result
