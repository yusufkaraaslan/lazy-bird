"""API routers for Lazy-Bird endpoints.

This package contains all API route handlers organized by resource:
- health: Health check and monitoring endpoints
- projects: Project management
- claude_accounts: Claude account configuration
- framework_presets: Framework preset management
- task_runs: Task execution and monitoring
- webhooks: Webhook subscription management
- api_keys: API key management
- auth: Authentication endpoints
"""

from lazy_bird.api.routers.health import router as health_router
from lazy_bird.api.routers.projects import router as projects_router

__all__ = [
    "health_router",
    "projects_router",
]
