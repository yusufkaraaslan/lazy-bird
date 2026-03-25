"""Initial v2.0 schema

Revision ID: eaf8e2359e19
Revises:
Create Date: 2026-03-25 00:00:00.000000

Creates all 8 tables for Lazy-Bird v2.0:
  1. framework_presets  - Framework-specific command presets
  2. claude_accounts    - Claude API credentials and settings
  3. projects           - Project configurations and settings
  4. task_runs          - Task execution records
  5. task_run_logs      - Detailed task execution logs
  6. webhook_subscriptions - Webhook endpoint registrations
  7. daily_usage        - Daily usage tracking and billing
  8. api_keys           - API authentication tokens
"""

from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "eaf8e2359e19"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # =========================================================================
    # 1. framework_presets (no FKs, referenced by projects)
    # =========================================================================
    op.create_table(
        "framework_presets",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column(
            "name",
            sa.String(100),
            nullable=False,
            comment="Internal preset name (lowercase, unique)",
        ),
        sa.Column(
            "display_name", sa.String(255), nullable=False, comment="Human-readable display name"
        ),
        sa.Column("description", sa.Text(), nullable=True, comment="Preset description"),
        sa.Column(
            "framework_type",
            sa.String(50),
            nullable=False,
            comment="Framework category: game_engine, backend, frontend, language",
        ),
        sa.Column(
            "language",
            sa.String(50),
            nullable=True,
            comment="Programming language: gdscript, python, javascript, rust, etc.",
        ),
        sa.Column(
            "test_command",
            sa.String(500),
            nullable=False,
            comment="Command to run tests (required)",
        ),
        sa.Column(
            "build_command",
            sa.String(500),
            nullable=True,
            comment="Command to build project (optional)",
        ),
        sa.Column(
            "lint_command", sa.String(500), nullable=True, comment="Command to lint code (optional)"
        ),
        sa.Column(
            "format_command",
            sa.String(500),
            nullable=True,
            comment="Command to format code (optional)",
        ),
        sa.Column(
            "config_files",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
            comment="JSON object with framework-specific config file paths",
        ),
        sa.Column(
            "is_builtin",
            sa.Boolean(),
            server_default="false",
            nullable=False,
            comment="Built-in preset (cannot be deleted)",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
            comment="Creation timestamp",
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
            comment="Last update timestamp",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
        comment="Framework-specific command presets and configurations",
    )
    op.create_index("ix_framework_presets_framework_type", "framework_presets", ["framework_type"])
    op.create_index("ix_framework_presets_is_builtin", "framework_presets", ["is_builtin"])

    # =========================================================================
    # 2. claude_accounts (no FKs, referenced by projects & task_runs)
    # =========================================================================
    op.create_table(
        "claude_accounts",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("name", sa.String(255), nullable=False, comment="Human-readable account name"),
        sa.Column(
            "account_type",
            sa.String(50),
            nullable=False,
            comment="Account type: api or subscription",
        ),
        sa.Column(
            "api_key",
            sa.String(500),
            nullable=True,
            comment="Anthropic API key (encrypted at application layer)",
        ),
        sa.Column(
            "config_directory",
            sa.String(500),
            nullable=True,
            comment="Config directory path for subscription mode",
        ),
        sa.Column(
            "session_token",
            sa.String(500),
            nullable=True,
            comment="Session token for subscription mode (encrypted at application layer)",
        ),
        sa.Column(
            "model",
            sa.String(100),
            server_default="claude-sonnet-4-5",
            nullable=False,
            comment="Claude model identifier",
        ),
        sa.Column(
            "max_tokens",
            sa.Integer(),
            server_default="8000",
            nullable=False,
            comment="Maximum tokens per request",
        ),
        sa.Column(
            "temperature",
            sa.Numeric(3, 2),
            server_default="0.7",
            nullable=False,
            comment="Model temperature (0.00-1.00)",
        ),
        sa.Column(
            "monthly_budget_usd",
            sa.Numeric(10, 2),
            nullable=True,
            comment="Monthly spending limit in USD",
        ),
        sa.Column(
            "is_active",
            sa.Boolean(),
            server_default="true",
            nullable=False,
            comment="Whether account is active and can be used",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
            comment="Creation timestamp",
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
            comment="Last update timestamp",
        ),
        sa.Column(
            "last_used_at",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="Last time this account was used for a task",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint("account_type IN ('api', 'subscription')", name="check_account_type"),
        sa.CheckConstraint(
            "(account_type = 'api' AND api_key IS NOT NULL) OR "
            "(account_type = 'subscription' AND config_directory IS NOT NULL)",
            name="check_api_key_required",
        ),
        sa.CheckConstraint(
            "temperature >= 0.0 AND temperature <= 1.0", name="check_temperature_range"
        ),
        sa.CheckConstraint("max_tokens > 0", name="check_max_tokens_positive"),
        sa.CheckConstraint(
            "monthly_budget_usd IS NULL OR monthly_budget_usd > 0",
            name="check_monthly_budget_positive",
        ),
        comment="Claude API credentials and configuration",
    )
    op.create_index("ix_claude_accounts_account_type", "claude_accounts", ["account_type"])
    op.create_index("ix_claude_accounts_is_active", "claude_accounts", ["is_active"])

    # =========================================================================
    # 3. projects (FKs to framework_presets, claude_accounts)
    # =========================================================================
    op.create_table(
        "projects",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("name", sa.String(255), nullable=False, comment="Human-readable project name"),
        sa.Column("slug", sa.String(100), nullable=False, comment="URL-safe unique identifier"),
        sa.Column(
            "repo_url",
            sa.String(500),
            nullable=False,
            comment="Git repository URL (GitHub, GitLab, etc.)",
        ),
        sa.Column(
            "default_branch",
            sa.String(100),
            server_default="main",
            nullable=False,
            comment="Default git branch for task execution",
        ),
        sa.Column(
            "framework_preset_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("framework_presets.id", ondelete="SET NULL"),
            nullable=True,
            comment="Reference to framework preset (optional)",
        ),
        sa.Column(
            "project_type",
            sa.String(50),
            nullable=False,
            comment="Project type: python, nodejs, rust, godot, etc.",
        ),
        sa.Column(
            "test_command",
            sa.String(500),
            nullable=True,
            comment="Custom test command (overrides preset)",
        ),
        sa.Column(
            "build_command",
            sa.String(500),
            nullable=True,
            comment="Custom build command (overrides preset)",
        ),
        sa.Column(
            "lint_command",
            sa.String(500),
            nullable=True,
            comment="Custom lint command (overrides preset)",
        ),
        sa.Column(
            "format_command",
            sa.String(500),
            nullable=True,
            comment="Custom format command (overrides preset)",
        ),
        sa.Column(
            "automation_enabled",
            sa.Boolean(),
            server_default="false",
            nullable=False,
            comment="Whether automation is active for this project",
        ),
        sa.Column(
            "ready_state_name",
            sa.String(100),
            nullable=True,
            comment="State name for ready tasks (e.g., 'Ready', 'To Do')",
        ),
        sa.Column(
            "in_progress_state_name",
            sa.String(100),
            server_default="In Progress",
            nullable=False,
            comment="State name for running tasks",
        ),
        sa.Column(
            "review_state_name",
            sa.String(100),
            server_default="In Review",
            nullable=False,
            comment="State name for tasks in review",
        ),
        sa.Column(
            "done_state_name",
            sa.String(100),
            server_default="Done",
            nullable=False,
            comment="State name for completed tasks",
        ),
        sa.Column(
            "max_concurrent_tasks",
            sa.Integer(),
            server_default="3",
            nullable=False,
            comment="Maximum number of parallel task executions",
        ),
        sa.Column(
            "task_timeout_seconds",
            sa.Integer(),
            server_default="1800",
            nullable=False,
            comment="Task execution timeout in seconds",
        ),
        sa.Column(
            "max_cost_per_task_usd",
            sa.Numeric(10, 2),
            server_default="5.00",
            nullable=False,
            comment="Maximum cost per task in USD",
        ),
        sa.Column(
            "daily_cost_limit_usd",
            sa.Numeric(10, 2),
            server_default="50.00",
            nullable=False,
            comment="Daily total cost limit in USD",
        ),
        sa.Column(
            "github_installation_id",
            sa.BigInteger(),
            nullable=True,
            comment="GitHub App installation ID for this project",
        ),
        sa.Column(
            "gitlab_project_id",
            sa.BigInteger(),
            nullable=True,
            comment="GitLab project ID for this project",
        ),
        sa.Column(
            "source_platform",
            sa.String(50),
            nullable=True,
            comment="Source platform: github, gitlab, plane, etc.",
        ),
        sa.Column(
            "source_platform_url",
            sa.String(500),
            nullable=True,
            comment="Platform URL for web UI integration",
        ),
        sa.Column(
            "claude_account_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("claude_accounts.id", ondelete="SET NULL"),
            nullable=True,
            comment="Reference to Claude API account",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
            comment="Creation timestamp",
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
            comment="Last update timestamp",
        ),
        sa.Column(
            "deleted_at",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="Soft delete timestamp (NULL if active)",
        ),
        sa.Column(
            "search_vector",
            postgresql.TSVECTOR(),
            nullable=True,
            comment="Full-text search vector (auto-generated from name + repo_url)",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug"),
        comment="Project configurations and automation settings",
    )
    op.create_index("ix_projects_slug", "projects", ["slug"])
    op.create_index("ix_projects_automation_enabled", "projects", ["automation_enabled"])
    op.create_index("ix_projects_source_platform", "projects", ["source_platform"])
    op.create_index(
        "idx_projects_search",
        "projects",
        ["search_vector"],
        postgresql_using="gin",
    )
    op.create_index(
        "idx_projects_deleted_at",
        "projects",
        ["deleted_at"],
        postgresql_where=sa.text("deleted_at IS NULL"),
    )

    # =========================================================================
    # 4. task_runs (FKs to projects, claude_accounts)
    # =========================================================================
    op.create_table(
        "task_runs",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column(
            "project_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=False,
            comment="Reference to project (cascade delete)",
        ),
        sa.Column(
            "claude_account_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("claude_accounts.id", ondelete="SET NULL"),
            nullable=True,
            comment="Reference to Claude account used for execution",
        ),
        sa.Column(
            "work_item_id",
            sa.String(255),
            nullable=False,
            comment="External work item ID (e.g., 'issue-42', 'JIRA-123')",
        ),
        sa.Column(
            "work_item_url", sa.String(500), nullable=True, comment="URL to work item on platform"
        ),
        sa.Column("work_item_title", sa.String(500), nullable=True, comment="Work item title"),
        sa.Column(
            "work_item_description", sa.Text(), nullable=True, comment="Work item description/body"
        ),
        sa.Column(
            "task_type",
            sa.String(50),
            server_default="feature",
            nullable=False,
            comment="Task type: feature, bugfix, refactor, docs, etc.",
        ),
        sa.Column(
            "complexity",
            sa.String(20),
            nullable=True,
            comment="Task complexity: simple, medium, complex",
        ),
        sa.Column(
            "prompt", sa.Text(), nullable=False, comment="Prompt sent to Claude for task execution"
        ),
        sa.Column(
            "status",
            sa.String(50),
            server_default="queued",
            nullable=False,
            comment="Execution status: queued, running, success, failed, cancelled, timeout",
        ),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="When task execution started",
        ),
        sa.Column(
            "completed_at",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="When task execution completed",
        ),
        sa.Column(
            "duration_seconds",
            sa.Integer(),
            nullable=True,
            comment="Total execution time in seconds (auto-calculated)",
        ),
        sa.Column(
            "retry_count",
            sa.Integer(),
            server_default="0",
            nullable=False,
            comment="Number of retries attempted",
        ),
        sa.Column(
            "max_retries",
            sa.Integer(),
            server_default="3",
            nullable=False,
            comment="Maximum retries allowed",
        ),
        sa.Column(
            "branch_name",
            sa.String(255),
            nullable=True,
            comment="Git branch name created for this task",
        ),
        sa.Column("worktree_path", sa.String(500), nullable=True, comment="Path to git worktree"),
        sa.Column("commit_sha", sa.String(40), nullable=True, comment="Git commit SHA"),
        sa.Column("pr_url", sa.String(500), nullable=True, comment="URL to created pull request"),
        sa.Column(
            "pr_number", sa.Integer(), nullable=True, comment="Pull request number on platform"
        ),
        sa.Column(
            "tests_passed",
            sa.Boolean(),
            nullable=True,
            comment="Whether tests passed (NULL if not run)",
        ),
        sa.Column("test_output", sa.Text(), nullable=True, comment="Test execution output"),
        sa.Column(
            "error_message", sa.Text(), nullable=True, comment="Error message if task failed"
        ),
        sa.Column(
            "tokens_used", sa.Integer(), nullable=True, comment="Total tokens consumed by Claude"
        ),
        sa.Column("cost_usd", sa.Numeric(10, 4), nullable=True, comment="Total cost in USD"),
        sa.Column(
            "task_metadata",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default="{}",
            nullable=True,
            comment="Additional task metadata as JSON",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
            comment="Creation timestamp",
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
            comment="Last update timestamp",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint(
            "status IN ('queued', 'running', 'success', 'failed', 'cancelled', 'timeout')",
            name="check_status",
        ),
        sa.CheckConstraint(
            "complexity IS NULL OR complexity IN ('simple', 'medium', 'complex')",
            name="check_complexity",
        ),
        comment="Task execution records and results",
    )
    op.create_index("ix_task_runs_project_id", "task_runs", ["project_id"])
    op.create_index("ix_task_runs_work_item_id", "task_runs", ["work_item_id"])
    op.create_index("ix_task_runs_status", "task_runs", ["status"])
    op.create_index("idx_task_runs_project_status", "task_runs", ["project_id", "status"])
    op.create_index("idx_task_runs_created_at", "task_runs", [sa.text("created_at DESC")])

    # =========================================================================
    # 5. task_run_logs (FK to task_runs)
    # =========================================================================
    op.create_table(
        "task_run_logs",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column(
            "task_run_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("task_runs.id", ondelete="CASCADE"),
            nullable=False,
            comment="Reference to task run (cascade delete)",
        ),
        sa.Column(
            "level",
            sa.String(20),
            nullable=False,
            comment="Log level: debug, info, warning, error, critical",
        ),
        sa.Column("message", sa.Text(), nullable=False, comment="Log message text"),
        sa.Column(
            "step",
            sa.String(100),
            nullable=True,
            comment="Execution step: init, planning, implementation, testing, etc.",
        ),
        sa.Column(
            "tool_name",
            sa.String(50),
            nullable=True,
            comment="Claude tool name: Read, Write, Edit, Bash, Grep, etc.",
        ),
        sa.Column(
            "log_metadata",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default="{}",
            nullable=True,
            comment="Additional log metadata as JSON",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
            comment="Log timestamp",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint(
            "level IN ('debug', 'info', 'warning', 'error', 'critical')",
            name="check_level",
        ),
        comment="Detailed task execution logs",
    )
    op.create_index("ix_task_run_logs_task_run_id", "task_run_logs", ["task_run_id"])
    op.create_index("ix_task_run_logs_level", "task_run_logs", ["level"])
    op.create_index("ix_task_run_logs_created_at", "task_run_logs", ["created_at"])
    op.create_index(
        "idx_task_run_logs_task_run_created", "task_run_logs", ["task_run_id", "created_at"]
    )

    # =========================================================================
    # 6. webhook_subscriptions (FK to projects)
    # =========================================================================
    op.create_table(
        "webhook_subscriptions",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("url", sa.String(500), nullable=False, comment="Webhook endpoint URL"),
        sa.Column(
            "secret",
            sa.String(255),
            nullable=False,
            comment="Secret for HMAC signature verification",
        ),
        sa.Column(
            "project_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=True,
            comment="Project ID (NULL for global subscriptions)",
        ),
        sa.Column(
            "events",
            postgresql.ARRAY(sa.Text()),
            nullable=False,
            comment="Array of event types",
        ),
        sa.Column(
            "is_active",
            sa.Boolean(),
            server_default="true",
            nullable=False,
            comment="Whether subscription is active",
        ),
        sa.Column(
            "last_triggered_at",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="Last webhook delivery time",
        ),
        sa.Column(
            "failure_count",
            sa.Integer(),
            server_default="0",
            nullable=False,
            comment="Number of consecutive failures",
        ),
        sa.Column(
            "last_failure_at",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="Last failure timestamp",
        ),
        sa.Column("description", sa.Text(), nullable=True, comment="Subscription description"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint("url ~ '^https?://'", name="check_url_format"),
        comment="Client webhook endpoint registrations",
    )
    op.create_index("ix_webhook_subscriptions_project_id", "webhook_subscriptions", ["project_id"])
    op.create_index("ix_webhook_subscriptions_is_active", "webhook_subscriptions", ["is_active"])
    op.create_index(
        "idx_webhook_subscriptions_events",
        "webhook_subscriptions",
        ["events"],
        postgresql_using="gin",
    )

    # =========================================================================
    # 7. daily_usage (FK to projects)
    # =========================================================================
    op.create_table(
        "daily_usage",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column(
            "project_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("tasks_queued", sa.Integer(), server_default="0", nullable=False),
        sa.Column("tasks_completed", sa.Integer(), server_default="0", nullable=False),
        sa.Column("tasks_failed", sa.Integer(), server_default="0", nullable=False),
        sa.Column("total_tokens_used", sa.BigInteger(), server_default="0", nullable=False),
        sa.Column("total_cost_usd", sa.Numeric(10, 4), server_default="0", nullable=False),
        sa.Column("total_duration_seconds", sa.BigInteger(), server_default="0", nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("project_id", "date", name="uq_daily_usage_project_date"),
        comment="Daily usage tracking and billing",
    )
    op.create_index(
        "idx_daily_usage_project_date", "daily_usage", ["project_id", sa.text("date DESC")]
    )
    op.create_index("idx_daily_usage_date", "daily_usage", [sa.text("date DESC")])

    # =========================================================================
    # 8. api_keys (FK to projects)
    # =========================================================================
    op.create_table(
        "api_keys",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column(
            "key_hash",
            sa.String(64),
            nullable=False,
            comment="SHA-256 hash of actual key",
        ),
        sa.Column(
            "key_prefix",
            sa.String(10),
            nullable=False,
            comment="First 8 chars for identification",
        ),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column(
            "project_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=True,
            comment="Project ID (NULL for organization-level)",
        ),
        sa.Column(
            "scopes",
            postgresql.ARRAY(sa.String()),
            server_default=sa.text("'{read}'"),
            nullable=False,
        ),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by", sa.String(255), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("key_hash"),
        sa.CheckConstraint(
            "scopes <@ ARRAY['read', 'write', 'admin']::VARCHAR[]",
            name="check_scopes",
        ),
        comment="API authentication tokens",
    )
    op.create_index("ix_api_keys_key_hash", "api_keys", ["key_hash"])
    op.create_index("ix_api_keys_key_prefix", "api_keys", ["key_prefix"])
    op.create_index("ix_api_keys_project_id", "api_keys", ["project_id"])
    op.create_index("ix_api_keys_is_active", "api_keys", ["is_active"])


def downgrade() -> None:
    # Drop in reverse dependency order
    op.drop_table("api_keys")
    op.drop_table("daily_usage")
    op.drop_table("webhook_subscriptions")
    op.drop_table("task_run_logs")
    op.drop_table("task_runs")
    op.drop_table("projects")
    op.drop_table("claude_accounts")
    op.drop_table("framework_presets")
