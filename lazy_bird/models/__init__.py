"""Database models for Lazy-Bird.

This package contains all SQLAlchemy ORM models for the application.
All models inherit from Base and are registered with Alembic for migrations.

Models:
- Project: Project configurations and settings
- ClaudeAccount: Claude API credentials and settings
- FrameworkPreset: Framework-specific command presets
- TaskRun: Task execution records
- TaskRunLog: Detailed execution logs
- WebhookSubscription: Webhook endpoint registrations
- DailyUsage: Daily usage tracking and billing
- ApiKey: API authentication tokens
"""

from lazy_bird.models.api_key import ApiKey
from lazy_bird.models.claude_account import ClaudeAccount
from lazy_bird.models.daily_usage import DailyUsage
from lazy_bird.models.framework_preset import FrameworkPreset
from lazy_bird.models.project import Project
from lazy_bird.models.task_run import TaskRun
from lazy_bird.models.task_run_log import TaskRunLog
from lazy_bird.models.webhook_subscription import WebhookSubscription

__all__ = [
    "Project",
    "ClaudeAccount",
    "FrameworkPreset",
    "TaskRun",
    "TaskRunLog",
    "WebhookSubscription",
    "DailyUsage",
    "ApiKey",
]
