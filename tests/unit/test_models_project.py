"""Unit tests for Project model.

Tests Project model fields, methods, and business logic.
"""

from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4

import pytest

from lazy_bird.models.framework_preset import FrameworkPreset
from lazy_bird.models.project import Project


class TestProjectCreation:
    """Test Project model creation and initialization."""

    def test_basic_creation(self):
        """Test creating a project with minimum required fields."""
        project = Project(
            name="Test Project",
            slug="test-project",
            repo_url="https://github.com/user/test-project",
            default_branch="main",
            project_type="python",
        )

        assert project.name == "Test Project"
        assert project.slug == "test-project"
        assert project.repo_url == "https://github.com/user/test-project"
        assert project.default_branch == "main"
        assert project.project_type == "python"

    def test_creation_with_all_fields(self):
        """Test creating a project with all fields."""
        project_id = uuid4()
        preset_id = uuid4()
        claude_account_id = uuid4()

        project = Project(
            id=project_id,
            name="Full Project",
            slug="full-project",
            repo_url="https://github.com/user/full-project",
            default_branch="develop",
            framework_preset_id=preset_id,
            project_type="nodejs",
            test_command="npm test",
            build_command="npm run build",
            lint_command="npm run lint",
            format_command="npm run format",
            automation_enabled=True,
            ready_state_name="Ready",
            in_progress_state_name="In Progress",
            review_state_name="Review",
            done_state_name="Done",
            max_concurrent_tasks=3,
            task_timeout_seconds=3600,
            max_cost_per_task_usd=Decimal("5.00"),
            daily_cost_limit_usd=Decimal("50.00"),
            github_installation_id=12345,
            source_platform="github",
            source_platform_url="https://github.com/user/full-project",
            claude_account_id=claude_account_id,
        )

        assert project.id == project_id
        assert project.framework_preset_id == preset_id
        assert project.test_command == "npm test"
        assert project.automation_enabled is True
        assert project.max_concurrent_tasks == 3
        assert project.max_cost_per_task_usd == Decimal("5.00")

    def test_default_values(self):
        """Test that default values are set correctly when explicitly provided."""
        project = Project(
            name="Default Project",
            slug="default-project",
            repo_url="https://github.com/user/default",
            default_branch="main",
            project_type="python",
            automation_enabled=True,
            max_concurrent_tasks=3,
            task_timeout_seconds=3600,
        )

        # Values should be set as provided
        assert project.automation_enabled is True
        assert project.max_concurrent_tasks == 3
        assert project.task_timeout_seconds == 3600


class TestProjectMethods:
    """Test Project model methods."""

    def test_is_active_when_not_deleted(self):
        """Test is_active() returns True when deleted_at is None."""
        project = Project(
            name="Active Project",
            slug="active-project",
            repo_url="https://github.com/user/active",
            default_branch="main",
            project_type="python",
            deleted_at=None,
        )

        assert project.is_active() is True

    def test_is_active_when_deleted(self):
        """Test is_active() returns False when deleted_at is set."""
        project = Project(
            name="Deleted Project",
            slug="deleted-project",
            repo_url="https://github.com/user/deleted",
            default_branch="main",
            project_type="python",
            deleted_at=datetime.now(timezone.utc),
        )

        assert project.is_active() is False

    def test_soft_delete(self):
        """Test soft_delete() sets deleted_at timestamp."""
        project = Project(
            name="To Delete",
            slug="to-delete",
            repo_url="https://github.com/user/to-delete",
            default_branch="main",
            project_type="python",
        )

        assert project.deleted_at is None
        assert project.is_active() is True

        project.soft_delete()

        assert project.deleted_at is not None
        assert project.is_active() is False

    def test_restore(self):
        """Test restore() clears deleted_at timestamp."""
        project = Project(
            name="To Restore",
            slug="to-restore",
            repo_url="https://github.com/user/to-restore",
            default_branch="main",
            project_type="python",
            deleted_at=datetime.now(timezone.utc),
        )

        assert project.is_active() is False

        project.restore()

        assert project.deleted_at is None
        assert project.is_active() is True

    def test_repr(self):
        """Test __repr__() method."""
        project = Project(
            name="Repr Test",
            slug="repr-test",
            repo_url="https://github.com/user/repr-test",
            default_branch="main",
            project_type="python",
        )

        repr_string = repr(project)

        assert "Project" in repr_string
        assert "repr-test" in repr_string


class TestProjectCommandGetters:
    """Test get_effective_*_command() methods."""

    def test_get_effective_test_command_custom(self):
        """Test get_effective_test_command() returns custom command when set."""
        project = Project(
            name="Test",
            slug="test",
            repo_url="https://github.com/user/test",
            default_branch="main",
            project_type="python",
            test_command="pytest --custom",
        )

        assert project.get_effective_test_command() == "pytest --custom"

    def test_get_effective_test_command_from_preset(self):
        """Test get_effective_test_command() returns preset command when no custom."""
        preset = FrameworkPreset(
            name="python-preset",
            display_name="Python Preset",
            framework_type="python",
            test_command="pytest",
        )

        project = Project(
            name="Test",
            slug="test",
            repo_url="https://github.com/user/test",
            default_branch="main",
            project_type="python",
        )
        project.framework_preset = preset

        assert project.get_effective_test_command() == "pytest"

    def test_get_effective_test_command_none(self):
        """Test get_effective_test_command() returns None when neither custom nor preset."""
        project = Project(
            name="Test",
            slug="test",
            repo_url="https://github.com/user/test",
            default_branch="main",
            project_type="python",
        )

        assert project.get_effective_test_command() is None

    def test_get_effective_build_command_custom(self):
        """Test get_effective_build_command() returns custom command when set."""
        project = Project(
            name="Test",
            slug="test",
            repo_url="https://github.com/user/test",
            default_branch="main",
            project_type="nodejs",
            build_command="npm run custom-build",
        )

        assert project.get_effective_build_command() == "npm run custom-build"

    def test_get_effective_lint_command_from_preset(self):
        """Test get_effective_lint_command() returns preset command."""
        preset = FrameworkPreset(
            name="python-preset",
            display_name="Python Preset",
            framework_type="python",
            test_command="pytest",
            lint_command="flake8",
        )

        project = Project(
            name="Test",
            slug="test",
            repo_url="https://github.com/user/test",
            default_branch="main",
            project_type="python",
        )
        project.framework_preset = preset

        assert project.get_effective_lint_command() == "flake8"

    def test_get_effective_format_command_custom_overrides_preset(self):
        """Test custom format command overrides preset."""
        preset = FrameworkPreset(
            name="python-preset",
            display_name="Python Preset",
            framework_type="python",
            test_command="pytest",
            format_command="black .",
        )

        project = Project(
            name="Test",
            slug="test",
            repo_url="https://github.com/user/test",
            default_branch="main",
            project_type="python",
            format_command="ruff format",
        )
        project.framework_preset = preset

        # Custom command should override preset
        assert project.get_effective_format_command() == "ruff format"


class TestProjectValidation:
    """Test Project model validation logic."""

    def test_slug_must_be_unique(self):
        """Test that slug should be unique (enforced by database)."""
        # This would typically be tested with database integration
        # For now, just verify the field exists
        project = Project(
            name="Test",
            slug="unique-slug",
            repo_url="https://github.com/user/test",
            default_branch="main",
            project_type="python",
        )

        assert project.slug == "unique-slug"

    def test_decimal_precision(self):
        """Test that decimal fields handle precision correctly."""
        project = Project(
            name="Test",
            slug="test",
            repo_url="https://github.com/user/test",
            default_branch="main",
            project_type="python",
            max_cost_per_task_usd=Decimal("5.1234"),
            daily_cost_limit_usd=Decimal("50.5678"),
        )

        # Should maintain precision
        assert project.max_cost_per_task_usd == Decimal("5.1234")
        assert project.daily_cost_limit_usd == Decimal("50.5678")


class TestProjectPlatformIntegration:
    """Test platform-specific integration fields."""

    def test_github_integration(self):
        """Test GitHub-specific fields."""
        project = Project(
            name="GitHub Project",
            slug="github-project",
            repo_url="https://github.com/user/repo",
            default_branch="main",
            project_type="python",
            source_platform="github",
            source_platform_url="https://github.com/user/repo",
            github_installation_id=12345,
        )

        assert project.source_platform == "github"
        assert project.github_installation_id == 12345
        assert project.gitlab_project_id is None

    def test_gitlab_integration(self):
        """Test GitLab-specific fields."""
        project = Project(
            name="GitLab Project",
            slug="gitlab-project",
            repo_url="https://gitlab.com/user/repo",
            default_branch="main",
            project_type="python",
            source_platform="gitlab",
            source_platform_url="https://gitlab.com/user/repo",
            gitlab_project_id=67890,
        )

        assert project.source_platform == "gitlab"
        assert project.gitlab_project_id == 67890
        assert project.github_installation_id is None
