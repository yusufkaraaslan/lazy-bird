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

from lazy_bird.api.routers.api_keys import router as api_keys_router
from lazy_bird.api.routers.auth import router as auth_router
from lazy_bird.api.routers.claude_accounts import router as claude_accounts_router
from lazy_bird.api.routers.framework_presets import router as framework_presets_router
from lazy_bird.api.routers.health import router as health_router
from lazy_bird.api.routers.projects import router as projects_router
from lazy_bird.api.routers.task_runs import router as task_runs_router
from lazy_bird.api.routers.webhooks import router as webhooks_router

__all__ = [
    "api_keys_router",
    "auth_router",
    "claude_accounts_router",
    "framework_presets_router",
    "health_router",
    "projects_router",
    "task_runs_router",
    "webhooks_router",
]
