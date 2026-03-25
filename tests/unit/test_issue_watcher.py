"""Tests for issue watcher Celery task.

Tests for lazy_bird/tasks/issue_watcher.py:
- Finds ready issues and creates TaskRuns
- Skips already-processed issues (existing TaskRun)
- Handles API errors gracefully
- Skips inactive projects
"""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


def _make_scalars_result(items):
    """Return a mock result whose .scalars().all() returns items."""
    result = AsyncMock()
    result.scalars = MagicMock(return_value=MagicMock(all=MagicMock(return_value=items)))
    return result


def _make_scalar_one_result(value):
    """Return a mock result whose .scalar_one_or_none() returns value."""
    result = AsyncMock()
    result.scalar_one_or_none = MagicMock(return_value=value)
    return result


class TestParseGithubRepo:
    """Test GitHub repo URL parsing."""

    def test_parse_https_url(self):
        from lazy_bird.tasks.issue_watcher import _parse_github_repo

        result = _parse_github_repo("https://github.com/owner/repo")
        assert result == ("owner", "repo")

    def test_parse_https_url_with_git(self):
        from lazy_bird.tasks.issue_watcher import _parse_github_repo

        result = _parse_github_repo("https://github.com/owner/repo.git")
        assert result == ("owner", "repo")

    def test_parse_ssh_url(self):
        from lazy_bird.tasks.issue_watcher import _parse_github_repo

        result = _parse_github_repo("git@github.com:owner/repo.git")
        assert result == ("owner", "repo")

    def test_parse_invalid_url(self):
        from lazy_bird.tasks.issue_watcher import _parse_github_repo

        result = _parse_github_repo("https://gitlab.com/owner/repo")
        assert result is None


class TestParseGitlabRepo:
    """Test GitLab repo URL parsing."""

    def test_parse_simple_url(self):
        from lazy_bird.tasks.issue_watcher import _parse_gitlab_repo

        result = _parse_gitlab_repo("https://gitlab.com/owner/repo")
        assert result == "owner%2Frepo"

    def test_parse_url_with_git(self):
        from lazy_bird.tasks.issue_watcher import _parse_gitlab_repo

        result = _parse_gitlab_repo("https://gitlab.com/group/subgroup/repo.git")
        assert result == "group%2Fsubgroup%2Frepo"


class TestDetectPlatform:
    """Test platform detection logic."""

    def test_detect_from_source_platform(self):
        from lazy_bird.tasks.issue_watcher import _detect_platform

        project = MagicMock()
        project.source_platform = "github"
        project.repo_url = "https://example.com/repo"
        assert _detect_platform(project) == "github"

    def test_detect_from_repo_url_github(self):
        from lazy_bird.tasks.issue_watcher import _detect_platform

        project = MagicMock()
        project.source_platform = None
        project.repo_url = "https://github.com/owner/repo"
        assert _detect_platform(project) == "github"

    def test_detect_from_repo_url_gitlab(self):
        from lazy_bird.tasks.issue_watcher import _detect_platform

        project = MagicMock()
        project.source_platform = None
        project.repo_url = "https://gitlab.com/owner/repo"
        assert _detect_platform(project) == "gitlab"

    def test_detect_unknown(self):
        from lazy_bird.tasks.issue_watcher import _detect_platform

        project = MagicMock()
        project.source_platform = None
        project.repo_url = "https://bitbucket.org/owner/repo"
        assert _detect_platform(project) is None


class TestWatchIssuesGithub:
    """Test watch_issues with GitHub projects."""

    @pytest.mark.asyncio
    async def test_finds_ready_issues_and_creates_task_runs(self):
        """Should create TaskRuns for new ready issues."""
        from lazy_bird.tasks.issue_watcher import _watch_issues_async

        project_id = uuid.uuid4()
        mock_project = MagicMock()
        mock_project.id = project_id
        mock_project.name = "test-project"
        mock_project.source_platform = "github"
        mock_project.repo_url = "https://github.com/owner/repo"
        mock_project.automation_enabled = True
        mock_project.deleted_at = None

        mock_db = AsyncMock()

        call_count = [0]

        async def mock_execute(stmt):
            call_count[0] += 1
            if call_count[0] == 1:
                # Active projects query
                return _make_scalars_result([mock_project])
            elif call_count[0] == 2:
                # Existing TaskRun check - none found
                return _make_scalar_one_result(None)
            return AsyncMock()

        mock_db.execute = mock_execute
        mock_db.add = MagicMock()
        mock_db.commit = AsyncMock()

        github_issues = [
            {
                "number": 42,
                "title": "Add health system",
                "body": "## Description\nImplement health tracking...",
                "html_url": "https://github.com/owner/repo/issues/42",
                "labels": [{"name": "ready"}],
            }
        ]

        mock_response = MagicMock()
        mock_response.json.return_value = github_issues
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.delete = AsyncMock()
        mock_client.post = AsyncMock()

        with (
            patch(
                "lazy_bird.tasks.issue_watcher.get_async_db",
                return_value=_async_gen(mock_db),
            ),
            patch(
                "lazy_bird.tasks.issue_watcher.httpx.AsyncClient",
            ) as mock_client_cls,
            patch(
                "lazy_bird.tasks.issue_watcher.settings",
            ) as mock_settings,
        ):
            mock_settings.GITHUB_TOKEN = "ghp_test_token"
            mock_settings.GITLAB_TOKEN = None

            # Make AsyncClient context manager return our mock
            mock_client_ctx = AsyncMock()
            mock_client_ctx.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client_ctx.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_client_ctx

            result = await _watch_issues_async()

        assert result["projects_checked"] == 1
        assert result["issues_found"] == 1
        assert result["task_runs_created"] == 1
        assert result["issues_skipped"] == 0
        assert result["errors"] == []
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called()

    @pytest.mark.asyncio
    async def test_skips_already_processed_issues(self):
        """Should skip issues that already have a TaskRun."""
        from lazy_bird.tasks.issue_watcher import _watch_issues_async

        project_id = uuid.uuid4()
        mock_project = MagicMock()
        mock_project.id = project_id
        mock_project.name = "test-project"
        mock_project.source_platform = "github"
        mock_project.repo_url = "https://github.com/owner/repo"
        mock_project.automation_enabled = True
        mock_project.deleted_at = None

        mock_db = AsyncMock()

        existing_task_run = MagicMock()
        existing_task_run.id = uuid.uuid4()

        call_count = [0]

        async def mock_execute(stmt):
            call_count[0] += 1
            if call_count[0] == 1:
                return _make_scalars_result([mock_project])
            elif call_count[0] == 2:
                # Existing TaskRun found
                return _make_scalar_one_result(existing_task_run)
            return AsyncMock()

        mock_db.execute = mock_execute
        mock_db.add = MagicMock()
        mock_db.commit = AsyncMock()

        github_issues = [
            {
                "number": 42,
                "title": "Add health system",
                "body": "Implement health",
                "html_url": "https://github.com/owner/repo/issues/42",
                "labels": [{"name": "ready"}],
            }
        ]

        mock_response = MagicMock()
        mock_response.json.return_value = github_issues
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)

        with (
            patch(
                "lazy_bird.tasks.issue_watcher.get_async_db",
                return_value=_async_gen(mock_db),
            ),
            patch(
                "lazy_bird.tasks.issue_watcher.httpx.AsyncClient",
            ) as mock_client_cls,
            patch(
                "lazy_bird.tasks.issue_watcher.settings",
            ) as mock_settings,
        ):
            mock_settings.GITHUB_TOKEN = "ghp_test_token"
            mock_settings.GITLAB_TOKEN = None

            mock_client_ctx = AsyncMock()
            mock_client_ctx.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client_ctx.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_client_ctx

            result = await _watch_issues_async()

        assert result["issues_found"] == 1
        assert result["task_runs_created"] == 0
        assert result["issues_skipped"] == 1
        mock_db.add.assert_not_called()

    @pytest.mark.asyncio
    async def test_handles_api_errors_gracefully(self):
        """Should handle API errors without crashing."""
        from lazy_bird.tasks.issue_watcher import _watch_issues_async

        project_id = uuid.uuid4()
        mock_project = MagicMock()
        mock_project.id = project_id
        mock_project.name = "test-project"
        mock_project.source_platform = "github"
        mock_project.repo_url = "https://github.com/owner/repo"
        mock_project.automation_enabled = True
        mock_project.deleted_at = None

        mock_db = AsyncMock()

        call_count = [0]

        async def mock_execute(stmt):
            call_count[0] += 1
            if call_count[0] == 1:
                return _make_scalars_result([mock_project])
            return AsyncMock()

        mock_db.execute = mock_execute

        # Client raises HTTP error
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = Exception("API rate limit exceeded")
        mock_client.get = AsyncMock(return_value=mock_response)

        with (
            patch(
                "lazy_bird.tasks.issue_watcher.get_async_db",
                return_value=_async_gen(mock_db),
            ),
            patch(
                "lazy_bird.tasks.issue_watcher.httpx.AsyncClient",
            ) as mock_client_cls,
            patch(
                "lazy_bird.tasks.issue_watcher.settings",
            ) as mock_settings,
        ):
            mock_settings.GITHUB_TOKEN = "ghp_test_token"
            mock_settings.GITLAB_TOKEN = None

            mock_client_ctx = AsyncMock()
            mock_client_ctx.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client_ctx.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_client_ctx

            result = await _watch_issues_async()

        # Should not crash, should record error
        assert len(result["errors"]) == 1
        assert "API rate limit exceeded" in result["errors"][0]

    @pytest.mark.asyncio
    async def test_skips_inactive_projects(self):
        """Should return early when no active projects found."""
        from lazy_bird.tasks.issue_watcher import _watch_issues_async

        mock_db = AsyncMock()
        mock_db.execute = AsyncMock(return_value=_make_scalars_result([]))

        with patch(
            "lazy_bird.tasks.issue_watcher.get_async_db",
            return_value=_async_gen(mock_db),
        ):
            result = await _watch_issues_async()

        assert result["projects_checked"] == 0
        assert result["issues_found"] == 0
        assert result["task_runs_created"] == 0
        assert result["errors"] == []

    @pytest.mark.asyncio
    async def test_skips_project_without_token(self):
        """Should skip projects when no token is configured."""
        from lazy_bird.tasks.issue_watcher import _watch_issues_async

        mock_project = MagicMock()
        mock_project.id = uuid.uuid4()
        mock_project.name = "test-project"
        mock_project.source_platform = "github"
        mock_project.repo_url = "https://github.com/owner/repo"

        mock_db = AsyncMock()
        mock_db.execute = AsyncMock(return_value=_make_scalars_result([mock_project]))

        mock_client = AsyncMock()

        with (
            patch(
                "lazy_bird.tasks.issue_watcher.get_async_db",
                return_value=_async_gen(mock_db),
            ),
            patch(
                "lazy_bird.tasks.issue_watcher.httpx.AsyncClient",
            ) as mock_client_cls,
            patch(
                "lazy_bird.tasks.issue_watcher.settings",
            ) as mock_settings,
        ):
            mock_settings.GITHUB_TOKEN = None
            mock_settings.GITLAB_TOKEN = None

            mock_client_ctx = AsyncMock()
            mock_client_ctx.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client_ctx.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_client_ctx

            result = await _watch_issues_async()

        assert result["projects_checked"] == 1
        assert result["issues_found"] == 0
        assert result["task_runs_created"] == 0


class TestWatchIssuesGitlab:
    """Test watch_issues with GitLab projects."""

    @pytest.mark.asyncio
    async def test_finds_gitlab_issues_and_creates_task_runs(self):
        """Should create TaskRuns for new ready GitLab issues."""
        from lazy_bird.tasks.issue_watcher import _watch_issues_async

        project_id = uuid.uuid4()
        mock_project = MagicMock()
        mock_project.id = project_id
        mock_project.name = "gitlab-project"
        mock_project.source_platform = "gitlab"
        mock_project.repo_url = "https://gitlab.com/owner/repo"
        mock_project.automation_enabled = True
        mock_project.deleted_at = None

        mock_db = AsyncMock()

        call_count = [0]

        async def mock_execute(stmt):
            call_count[0] += 1
            if call_count[0] == 1:
                return _make_scalars_result([mock_project])
            elif call_count[0] == 2:
                return _make_scalar_one_result(None)
            return AsyncMock()

        mock_db.execute = mock_execute
        mock_db.add = MagicMock()
        mock_db.commit = AsyncMock()

        gitlab_issues = [
            {
                "iid": 10,
                "title": "Fix login page",
                "description": "The login page has a bug...",
                "web_url": "https://gitlab.com/owner/repo/-/issues/10",
                "labels": ["ready"],
            }
        ]

        mock_response = MagicMock()
        mock_response.json.return_value = gitlab_issues
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.put = AsyncMock()

        with (
            patch(
                "lazy_bird.tasks.issue_watcher.get_async_db",
                return_value=_async_gen(mock_db),
            ),
            patch(
                "lazy_bird.tasks.issue_watcher.httpx.AsyncClient",
            ) as mock_client_cls,
            patch(
                "lazy_bird.tasks.issue_watcher.settings",
            ) as mock_settings,
        ):
            mock_settings.GITHUB_TOKEN = None
            mock_settings.GITLAB_TOKEN = "glpat-test-token"

            mock_client_ctx = AsyncMock()
            mock_client_ctx.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client_ctx.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_client_ctx

            result = await _watch_issues_async()

        assert result["projects_checked"] == 1
        assert result["issues_found"] == 1
        assert result["task_runs_created"] == 1
        assert result["issues_skipped"] == 0
        assert result["errors"] == []
        mock_db.add.assert_called_once()


# -------------------------------------------------------------------------
# HELPERS
# -------------------------------------------------------------------------


async def _async_gen(value):
    """Create an async generator that yields a single value."""
    yield value
