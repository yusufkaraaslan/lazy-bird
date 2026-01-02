"""Unit tests for PRService.

Tests GitHub PR creation, GitLab MR creation, and PR body building.
"""

import subprocess
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from lazy_bird.services.pr_service import (
    PRCreationError,
    PRService,
    PRServiceError,
)


class TestPRServiceInit:
    """Test PRService initialization."""

    def test_init_default_directory(self):
        """Test PRService with default working directory."""
        service = PRService()

        assert service.working_directory == Path.cwd()

    def test_init_custom_directory(self, tmp_path):
        """Test PRService with custom working directory."""
        service = PRService(working_directory=tmp_path)

        assert service.working_directory == tmp_path


class TestCreatePullRequest:
    """Test create_pull_request method for GitHub."""

    def test_create_pr_success(self, tmp_path):
        """Test successful GitHub PR creation."""
        service = PRService(working_directory=tmp_path)

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = subprocess.CompletedProcess(
                args=["gh", "pr", "create"],
                returncode=0,
                stdout="https://github.com/user/repo/pull/42\n",
                stderr="",
            )

            result = service.create_pull_request(
                title="Add feature",
                body="Implementation details",
                base_branch="main",
                head_branch="feature-42",
                project_id="test-proj",
                task_id=42,
            )

            assert result["success"] is True
            assert result["url"] == "https://github.com/user/repo/pull/42"
            assert result["number"] == 42
            assert result["platform"] == "github"
            assert mock_run.called

    def test_create_pr_with_labels(self, tmp_path):
        """Test PR creation with labels."""
        service = PRService(working_directory=tmp_path)

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = subprocess.CompletedProcess(
                args=["gh", "pr", "create"],
                returncode=0,
                stdout="https://github.com/user/repo/pull/42\n",
                stderr="",
            )

            result = service.create_pull_request(
                title="Add feature",
                body="Details",
                base_branch="main",
                head_branch="feature-42",
                labels=["automated", "enhancement"],
            )

            # Check that labels were added to command
            call_args = mock_run.call_args[0][0]
            assert "--label" in call_args
            assert "automated" in call_args

    def test_create_pr_draft(self, tmp_path):
        """Test creating draft PR."""
        service = PRService(working_directory=tmp_path)

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = subprocess.CompletedProcess(
                args=["gh", "pr", "create"],
                returncode=0,
                stdout="https://github.com/user/repo/pull/42\n",
                stderr="",
            )

            result = service.create_pull_request(
                title="Add feature",
                body="Details",
                base_branch="main",
                head_branch="feature-42",
                draft=True,
            )

            # Check that --draft was added
            call_args = mock_run.call_args[0][0]
            assert "--draft" in call_args

    def test_create_pr_with_repository(self, tmp_path):
        """Test PR creation with explicit repository."""
        service = PRService(working_directory=tmp_path)

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = subprocess.CompletedProcess(
                args=["gh", "pr", "create"],
                returncode=0,
                stdout="https://github.com/user/repo/pull/42\n",
                stderr="",
            )

            result = service.create_pull_request(
                title="Add feature",
                body="Details",
                base_branch="main",
                head_branch="feature-42",
                repository="user/repo",
            )

            # Check that --repo was added
            call_args = mock_run.call_args[0][0]
            assert "--repo" in call_args
            assert "user/repo" in call_args

    def test_create_pr_with_issue_comment(self, tmp_path):
        """Test PR creation with issue commenting."""
        service = PRService(working_directory=tmp_path)

        with patch("subprocess.run") as mock_run:
            # First call: create PR, second call: comment on issue
            mock_run.side_effect = [
                subprocess.CompletedProcess(
                    args=["gh", "pr", "create"],
                    returncode=0,
                    stdout="https://github.com/user/repo/pull/42\n",
                    stderr="",
                ),
                subprocess.CompletedProcess(
                    args=["gh", "issue", "comment"],
                    returncode=0,
                    stdout="",
                    stderr="",
                ),
            ]

            result = service.create_pull_request(
                title="Add feature",
                body="Details",
                base_branch="main",
                head_branch="feature-42",
                issue_number=10,
            )

            # Should have called gh twice: create PR + comment on issue
            assert mock_run.call_count == 2

    def test_create_pr_failure(self, tmp_path):
        """Test failed PR creation."""
        service = PRService(working_directory=tmp_path)

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = subprocess.CompletedProcess(
                args=["gh", "pr", "create"],
                returncode=1,
                stdout="",
                stderr="Error: PR already exists",
            )

            with pytest.raises(PRCreationError) as exc_info:
                service.create_pull_request(
                    title="Add feature",
                    body="Details",
                    base_branch="main",
                    head_branch="feature-42",
                )

            assert "GitHub" in str(exc_info.value)
            assert "PR already exists" in str(exc_info.value)

    def test_create_pr_timeout(self, tmp_path):
        """Test PR creation timeout."""
        service = PRService(working_directory=tmp_path)

        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = subprocess.TimeoutExpired(cmd="gh", timeout=60)

            with pytest.raises(PRServiceError) as exc_info:
                service.create_pull_request(
                    title="Add feature",
                    body="Details",
                    base_branch="main",
                    head_branch="feature-42",
                )

            assert "timed out" in str(exc_info.value)


class TestCreateMergeRequest:
    """Test create_merge_request method for GitLab."""

    def test_create_mr_success(self, tmp_path):
        """Test successful GitLab MR creation."""
        service = PRService(working_directory=tmp_path)

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = subprocess.CompletedProcess(
                args=["glab", "mr", "create"],
                returncode=0,
                stdout="https://gitlab.com/user/repo/-/merge_requests/42\n",
                stderr="",
            )

            result = service.create_merge_request(
                title="Add feature",
                body="Implementation details",
                base_branch="main",
                head_branch="feature-42",
                project_id="test-proj",
                task_id=42,
            )

            assert result["success"] is True
            assert result["url"] == "https://gitlab.com/user/repo/-/merge_requests/42"
            assert result["number"] == 42
            assert result["platform"] == "gitlab"

    def test_create_mr_draft(self, tmp_path):
        """Test creating draft MR."""
        service = PRService(working_directory=tmp_path)

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = subprocess.CompletedProcess(
                args=["glab", "mr", "create"],
                returncode=0,
                stdout="https://gitlab.com/user/repo/-/merge_requests/42\n",
                stderr="",
            )

            result = service.create_merge_request(
                title="Add feature",
                body="Details",
                base_branch="main",
                head_branch="feature-42",
                draft=True,
            )

            # Check that title has "Draft:" prefix and --draft flag
            call_args = mock_run.call_args[0][0]
            title_index = call_args.index("--title") + 1
            assert call_args[title_index].startswith("Draft:")
            assert "--draft" in call_args

    def test_create_mr_with_labels(self, tmp_path):
        """Test MR creation with labels."""
        service = PRService(working_directory=tmp_path)

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = subprocess.CompletedProcess(
                args=["glab", "mr", "create"],
                returncode=0,
                stdout="https://gitlab.com/user/repo/-/merge_requests/42\n",
                stderr="",
            )

            result = service.create_merge_request(
                title="Add feature",
                body="Details",
                base_branch="main",
                head_branch="feature-42",
                labels=["automated", "enhancement"],
            )

            # Check that labels were joined with comma
            call_args = mock_run.call_args[0][0]
            assert "--label" in call_args
            label_index = call_args.index("--label") + 1
            assert "automated,enhancement" in call_args[label_index]

    def test_create_mr_failure(self, tmp_path):
        """Test failed MR creation."""
        service = PRService(working_directory=tmp_path)

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = subprocess.CompletedProcess(
                args=["glab", "mr", "create"],
                returncode=1,
                stdout="",
                stderr="Error: MR already exists",
            )

            with pytest.raises(PRCreationError) as exc_info:
                service.create_merge_request(
                    title="Add feature",
                    body="Details",
                    base_branch="main",
                    head_branch="feature-42",
                )

            assert "GitLab" in str(exc_info.value)
            assert "MR already exists" in str(exc_info.value)


class TestBuildPRBody:
    """Test build_pr_body method."""

    def test_build_pr_body_minimal(self):
        """Test building PR body with minimal info."""
        service = PRService()

        body = service.build_pr_body(task_description="Add health system")

        assert "Task Description" in body
        assert "Add health system" in body
        assert "Lazy-Bird" in body

    def test_build_pr_body_with_summary(self):
        """Test building PR body with implementation summary."""
        service = PRService()

        body = service.build_pr_body(
            task_description="Add health system",
            implementation_summary="Implemented Player.health with take_damage() method",
        )

        assert "Implementation Summary" in body
        assert "Implemented Player.health" in body

    def test_build_pr_body_with_test_results_success(self):
        """Test building PR body with successful test results."""
        service = PRService()

        test_results = {
            "success": True,
            "stats": {"total": 10, "passed": 10, "failed": 0},
            "execution_time": 2.5,
        }

        body = service.build_pr_body(
            task_description="Add health system",
            test_results=test_results,
        )

        assert "Test Results" in body
        assert "All tests passed" in body
        assert "Total:** 10" in body
        assert "2.50s" in body

    def test_build_pr_body_with_test_results_failure(self):
        """Test building PR body with failed test results."""
        service = PRService()

        test_results = {
            "success": False,
            "stats": {"total": 10, "passed": 8, "failed": 2},
            "execution_time": 3.2,
        }

        body = service.build_pr_body(
            task_description="Add health system",
            test_results=test_results,
        )

        assert "Test Results" in body
        assert "Some tests failed" in body
        assert "Failed:** 2" in body

    def test_build_pr_body_with_diff_stats(self):
        """Test building PR body with diff statistics."""
        service = PRService()

        diff_stats = {
            "files_changed": 3,
            "insertions": 150,
            "deletions": 20,
        }

        body = service.build_pr_body(
            task_description="Add health system",
            diff_stats=diff_stats,
        )

        assert "Changes" in body
        assert "Files changed:** 3" in body
        assert "+150" in body
        assert "-20" in body


class TestExtractNumbers:
    """Test PR/MR number extraction methods."""

    def test_extract_pr_number_from_url(self):
        """Test extracting PR number from GitHub URL."""
        service = PRService()

        url = "https://github.com/user/repo/pull/42"
        number = service._extract_pr_number_from_url(url)

        assert number == 42

    def test_extract_pr_number_invalid_url(self):
        """Test extracting PR number from invalid URL."""
        service = PRService()

        url = "https://github.com/user/repo"
        number = service._extract_pr_number_from_url(url)

        assert number == 0

    def test_extract_mr_iid_from_url(self):
        """Test extracting MR IID from GitLab URL."""
        service = PRService()

        url = "https://gitlab.com/user/repo/-/merge_requests/42"
        iid = service._extract_mr_iid_from_url(url)

        assert iid == 42

    def test_extract_mr_iid_invalid_url(self):
        """Test extracting MR IID from invalid URL."""
        service = PRService()

        url = "https://gitlab.com/user/repo"
        iid = service._extract_mr_iid_from_url(url)

        assert iid == 0


class TestPRServiceErrors:
    """Test PRService exception classes."""

    def test_pr_creation_error(self):
        """Test PRCreationError exception."""
        error = PRCreationError(
            platform="GitHub",
            command="gh pr create",
            stderr="Error: PR already exists",
        )

        assert error.platform == "GitHub"
        assert error.command == "gh pr create"
        assert error.stderr == "Error: PR already exists"
        assert "GitHub" in str(error)
        assert "PR already exists" in str(error)

    def test_pr_service_error(self):
        """Test base PRServiceError."""
        error = PRServiceError("Something went wrong")

        assert "Something went wrong" in str(error)
