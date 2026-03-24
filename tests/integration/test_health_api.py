"""Integration tests for Health API endpoints.

Tests all 4 health check endpoints (comprehensive, liveness, readiness, startup).
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from lazy_bird.api.main import app


class TestHealthCheck:
    """Test GET /api/v1/health endpoint (comprehensive check)."""

    def test_health_check_success(self, test_client):
        """Test comprehensive health check when all services are healthy."""
        with patch("lazy_bird.api.routers.health.check_database") as mock_db, patch(
            "lazy_bird.api.routers.health.check_redis_status"
        ) as mock_redis, patch(
            "lazy_bird.api.routers.health.check_celery_status"
        ) as mock_celery, patch(
            "lazy_bird.api.routers.health.get_system_metrics"
        ) as mock_metrics:

            # Mock all services as healthy
            mock_db.return_value = {"status": "healthy", "mode": "async"}
            mock_redis.return_value = {"status": "healthy"}
            mock_celery.return_value = {"status": "not_configured"}
            mock_metrics.return_value = {
                "cpu": {"usage_percent": 25.5, "cores": 8},
                "memory": {"total_mb": 16384, "used_mb": 8192, "percent": 50.0},
                "disk": {"total_gb": 500, "used_gb": 250, "percent": 50.0},
            }

            response = test_client.get("/api/v1/health")

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "healthy"
            assert "timestamp" in data
            assert "version" in data
            assert "environment" in data
            assert "services" in data
            assert data["services"]["database"]["status"] == "healthy"
            assert data["services"]["redis"]["status"] == "healthy"
            assert "system" in data
            assert "cpu" in data["system"]
            assert "memory" in data["system"]
            assert "disk" in data["system"]

    def test_health_check_database_unhealthy(self, test_client):
        """Test health check when database is unhealthy."""
        with patch("lazy_bird.api.routers.health.check_database") as mock_db, patch(
            "lazy_bird.api.routers.health.check_redis_status"
        ) as mock_redis, patch(
            "lazy_bird.api.routers.health.check_celery_status"
        ) as mock_celery, patch(
            "lazy_bird.api.routers.health.get_system_metrics"
        ) as mock_metrics:

            mock_db.return_value = {"status": "unhealthy", "error": "Connection refused"}
            mock_redis.return_value = {"status": "healthy"}
            mock_celery.return_value = {"status": "not_configured"}
            mock_metrics.return_value = {"cpu": {}, "memory": {}, "disk": {}}

            response = test_client.get("/api/v1/health")

            assert response.status_code == 503  # Service Unavailable
            data = response.json()
            assert data["status"] == "unhealthy"
            assert data["services"]["database"]["status"] == "unhealthy"

    def test_health_check_redis_unhealthy(self, test_client):
        """Test health check when Redis is unhealthy."""
        with patch("lazy_bird.api.routers.health.check_database") as mock_db, patch(
            "lazy_bird.api.routers.health.check_redis_status"
        ) as mock_redis, patch(
            "lazy_bird.api.routers.health.check_celery_status"
        ) as mock_celery, patch(
            "lazy_bird.api.routers.health.get_system_metrics"
        ) as mock_metrics:

            mock_db.return_value = {"status": "healthy"}
            mock_redis.return_value = {"status": "unhealthy", "error": "Connection timeout"}
            mock_celery.return_value = {"status": "not_configured"}
            mock_metrics.return_value = {"cpu": {}, "memory": {}, "disk": {}}

            response = test_client.get("/api/v1/health")

            assert response.status_code == 503
            data = response.json()
            assert data["status"] == "unhealthy"
            assert data["services"]["redis"]["status"] == "unhealthy"

    def test_health_check_celery_degraded(self, test_client):
        """Test health check when Celery is degraded (still returns 200)."""
        with patch("lazy_bird.api.routers.health.check_database") as mock_db, patch(
            "lazy_bird.api.routers.health.check_redis_status"
        ) as mock_redis, patch(
            "lazy_bird.api.routers.health.check_celery_status"
        ) as mock_celery, patch(
            "lazy_bird.api.routers.health.get_system_metrics"
        ) as mock_metrics:

            mock_db.return_value = {"status": "healthy"}
            mock_redis.return_value = {"status": "healthy"}
            mock_celery.return_value = {
                "status": "degraded",
                "workers": 0,
                "message": "No active workers",
            }
            mock_metrics.return_value = {"cpu": {}, "memory": {}, "disk": {}}

            response = test_client.get("/api/v1/health")

            assert response.status_code == 200  # Degraded Celery is OK
            data = response.json()
            assert data["status"] == "healthy"
            assert data["services"]["celery"]["status"] == "degraded"

    def test_health_check_with_trailing_slash(self, test_client):
        """Test health check with trailing slash."""
        with patch("lazy_bird.api.routers.health.check_database") as mock_db, patch(
            "lazy_bird.api.routers.health.check_redis_status"
        ) as mock_redis, patch(
            "lazy_bird.api.routers.health.check_celery_status"
        ) as mock_celery, patch(
            "lazy_bird.api.routers.health.get_system_metrics"
        ) as mock_metrics:

            mock_db.return_value = {"status": "healthy"}
            mock_redis.return_value = {"status": "healthy"}
            mock_celery.return_value = {"status": "not_configured"}
            mock_metrics.return_value = {"cpu": {}, "memory": {}, "disk": {}}

            response = test_client.get("/api/v1/health/")

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "healthy"


class TestLivenessProbe:
    """Test GET /api/v1/health/live endpoint."""

    def test_liveness_probe_success(self, test_client):
        """Test liveness probe always returns success."""
        response = test_client.get("/api/v1/health/live")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "alive"
        assert "timestamp" in data

    def test_liveness_probe_no_authentication(self, test_client):
        """Test liveness probe doesn't require authentication."""
        # No API key header provided
        response = test_client.get("/api/v1/health/live")

        assert response.status_code == 200  # Should still work


class TestReadinessProbe:
    """Test GET /api/v1/health/ready endpoint."""

    def test_readiness_probe_ready(self, test_client):
        """Test readiness probe when services are ready."""
        with patch("lazy_bird.api.routers.health.check_database") as mock_db, patch(
            "lazy_bird.api.routers.health.check_redis_status"
        ) as mock_redis:

            mock_db.return_value = {"status": "healthy"}
            mock_redis.return_value = {"status": "healthy"}

            response = test_client.get("/api/v1/health/ready")

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "ready"
            assert data["services"]["database"] == "healthy"
            assert data["services"]["redis"] == "healthy"

    def test_readiness_probe_not_ready_database(self, test_client):
        """Test readiness probe when database is not ready."""
        with patch("lazy_bird.api.routers.health.check_database") as mock_db, patch(
            "lazy_bird.api.routers.health.check_redis_status"
        ) as mock_redis:

            mock_db.return_value = {"status": "unhealthy"}
            mock_redis.return_value = {"status": "healthy"}

            response = test_client.get("/api/v1/health/ready")

            assert response.status_code == 503
            data = response.json()
            assert data["status"] == "not_ready"

    def test_readiness_probe_not_ready_redis(self, test_client):
        """Test readiness probe when Redis is not ready."""
        with patch("lazy_bird.api.routers.health.check_database") as mock_db, patch(
            "lazy_bird.api.routers.health.check_redis_status"
        ) as mock_redis:

            mock_db.return_value = {"status": "healthy"}
            mock_redis.return_value = {"status": "unhealthy"}

            response = test_client.get("/api/v1/health/ready")

            assert response.status_code == 503
            data = response.json()
            assert data["status"] == "not_ready"

    def test_readiness_probe_no_celery_check(self, test_client):
        """Test that readiness probe doesn't check Celery (only critical services)."""
        with patch("lazy_bird.api.routers.health.check_database") as mock_db, patch(
            "lazy_bird.api.routers.health.check_redis_status"
        ) as mock_redis, patch("lazy_bird.api.routers.health.check_celery_status") as mock_celery:

            mock_db.return_value = {"status": "healthy"}
            mock_redis.return_value = {"status": "healthy"}
            # Celery check should not be called
            mock_celery.return_value = {"status": "unhealthy"}

            response = test_client.get("/api/v1/health/ready")

            assert response.status_code == 200  # Still ready even if Celery is down
            # Celery should not be called
            mock_celery.assert_not_called()


class TestStartupProbe:
    """Test GET /api/v1/health/startup endpoint."""

    def test_startup_probe_started(self, test_client):
        """Test startup probe when application has started."""
        with patch("lazy_bird.api.routers.health.check_database") as mock_db:
            mock_db.return_value = {"status": "healthy"}

            response = test_client.get("/api/v1/health/startup")

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "started"
            assert data["database"] == "healthy"

    def test_startup_probe_starting(self, test_client):
        """Test startup probe when application is still starting."""
        with patch("lazy_bird.api.routers.health.check_database") as mock_db:
            mock_db.return_value = {"status": "unhealthy", "error": "Starting up"}

            response = test_client.get("/api/v1/health/startup")

            assert response.status_code == 503
            data = response.json()
            assert data["status"] == "starting"

    def test_startup_probe_only_checks_database(self, test_client):
        """Test that startup probe only checks database (most lenient)."""
        with patch("lazy_bird.api.routers.health.check_database") as mock_db, patch(
            "lazy_bird.api.routers.health.check_redis_status"
        ) as mock_redis:

            mock_db.return_value = {"status": "healthy"}
            # Redis check should not be called
            mock_redis.return_value = {"status": "unhealthy"}

            response = test_client.get("/api/v1/health/startup")

            assert response.status_code == 200  # Started even if Redis is down
            # Redis should not be called
            mock_redis.assert_not_called()


class TestHealthProbeHierarchy:
    """Test the hierarchy of health probes."""

    def test_startup_most_lenient(self, test_client):
        """Test that startup probe is the most lenient (only needs DB)."""
        with patch("lazy_bird.api.routers.health.check_database") as mock_db:
            mock_db.return_value = {"status": "healthy"}

            response = test_client.get("/api/v1/health/startup")

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "started"

    def test_readiness_checks_db_and_redis(self, test_client):
        """Test that readiness probe needs both DB and Redis."""
        with patch("lazy_bird.api.routers.health.check_database") as mock_db, patch(
            "lazy_bird.api.routers.health.check_redis_status"
        ) as mock_redis:

            mock_db.return_value = {"status": "healthy"}
            mock_redis.return_value = {"status": "healthy"}

            response = test_client.get("/api/v1/health/ready")

            assert response.status_code == 200
            # Both checks should be called
            mock_db.assert_called_once()
            mock_redis.assert_called_once()

    def test_comprehensive_checks_all_services(self, test_client):
        """Test that comprehensive health check verifies all services."""
        with patch("lazy_bird.api.routers.health.check_database") as mock_db, patch(
            "lazy_bird.api.routers.health.check_redis_status"
        ) as mock_redis, patch(
            "lazy_bird.api.routers.health.check_celery_status"
        ) as mock_celery, patch(
            "lazy_bird.api.routers.health.get_system_metrics"
        ) as mock_metrics:

            mock_db.return_value = {"status": "healthy"}
            mock_redis.return_value = {"status": "healthy"}
            mock_celery.return_value = {"status": "not_configured"}
            mock_metrics.return_value = {"cpu": {}, "memory": {}, "disk": {}}

            response = test_client.get("/api/v1/health")

            assert response.status_code == 200
            # All checks should be called
            mock_db.assert_called_once()
            mock_redis.assert_called_once()
            mock_celery.assert_called_once()
            mock_metrics.assert_called_once()


class TestKubernetesIntegration:
    """Test Kubernetes probe integration patterns."""

    def test_startup_then_liveness_then_readiness(self, test_client):
        """Test typical Kubernetes probe sequence."""
        with patch("lazy_bird.api.routers.health.check_database") as mock_db, patch(
            "lazy_bird.api.routers.health.check_redis_status"
        ) as mock_redis:

            # Step 1: Startup probe (database initializing)
            mock_db.return_value = {"status": "unhealthy"}
            startup_response = test_client.get("/api/v1/health/startup")
            assert startup_response.status_code == 503

            # Step 2: Startup probe (database ready)
            mock_db.return_value = {"status": "healthy"}
            startup_response = test_client.get("/api/v1/health/startup")
            assert startup_response.status_code == 200

            # Step 3: Liveness probe (always alive)
            liveness_response = test_client.get("/api/v1/health/live")
            assert liveness_response.status_code == 200

            # Step 4: Readiness probe (Redis not ready yet)
            mock_redis.return_value = {"status": "unhealthy"}
            readiness_response = test_client.get("/api/v1/health/ready")
            assert readiness_response.status_code == 503

            # Step 5: Readiness probe (all services ready)
            mock_redis.return_value = {"status": "healthy"}
            readiness_response = test_client.get("/api/v1/health/ready")
            assert readiness_response.status_code == 200

    def test_liveness_failure_indicates_restart_needed(self, test_client):
        """Test that liveness probe failure (if it ever fails) indicates restart."""
        # Liveness probe should always return 200
        # This test documents the behavior
        response = test_client.get("/api/v1/health/live")

        assert response.status_code == 200
        assert response.json()["status"] == "alive"
