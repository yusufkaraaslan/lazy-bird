"""Pydantic validation schemas for API endpoints.

This package contains Pydantic v2 schemas for request/response validation.
All schemas use modern Pydantic features including field validators and ConfigDict.
"""

from lazy_bird.schemas.api_key import (
    ApiKeyBase,
    ApiKeyCreate,
    ApiKeyCreateResponse,
    ApiKeyListResponse,
    ApiKeyResponse,
    ApiKeyUpdate,
)
from lazy_bird.schemas.claude_account import (
    ClaudeAccountBase,
    ClaudeAccountCreate,
    ClaudeAccountListResponse,
    ClaudeAccountResponse,
    ClaudeAccountUpdate,
)
from lazy_bird.schemas.framework_preset import (
    FrameworkPresetBase,
    FrameworkPresetCreate,
    FrameworkPresetListResponse,
    FrameworkPresetResponse,
    FrameworkPresetUpdate,
)
from lazy_bird.schemas.project import (
    ProjectBase,
    ProjectCreate,
    ProjectListResponse,
    ProjectResponse,
    ProjectUpdate,
)
from lazy_bird.schemas.task_run import (
    TaskRunListResponse,
    TaskRunQueue,
    TaskRunResponse,
    TaskRunUpdate,
)
from lazy_bird.schemas.webhook import (
    WebhookSubscriptionBase,
    WebhookSubscriptionCreate,
    WebhookSubscriptionListResponse,
    WebhookSubscriptionResponse,
    WebhookSubscriptionUpdate,
)

__all__ = [
    # Project schemas
    "ProjectBase",
    "ProjectCreate",
    "ProjectUpdate",
    "ProjectResponse",
    "ProjectListResponse",
    # ClaudeAccount schemas
    "ClaudeAccountBase",
    "ClaudeAccountCreate",
    "ClaudeAccountUpdate",
    "ClaudeAccountResponse",
    "ClaudeAccountListResponse",
    # FrameworkPreset schemas
    "FrameworkPresetBase",
    "FrameworkPresetCreate",
    "FrameworkPresetUpdate",
    "FrameworkPresetResponse",
    "FrameworkPresetListResponse",
    # TaskRun schemas
    "TaskRunQueue",
    "TaskRunUpdate",
    "TaskRunResponse",
    "TaskRunListResponse",
    # WebhookSubscription schemas
    "WebhookSubscriptionBase",
    "WebhookSubscriptionCreate",
    "WebhookSubscriptionUpdate",
    "WebhookSubscriptionResponse",
    "WebhookSubscriptionListResponse",
    # ApiKey schemas
    "ApiKeyBase",
    "ApiKeyCreate",
    "ApiKeyUpdate",
    "ApiKeyResponse",
    "ApiKeyCreateResponse",
    "ApiKeyListResponse",
]
