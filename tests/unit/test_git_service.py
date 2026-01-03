"""Unit tests for GitService.

Tests git worktree operations, branch management, and commit/push functionality.
"""

import subprocess
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

from lazy_bird.services.git_service import (
    GitCommandError,
    GitService,
    GitServiceError,
    WorktreeExistsError,
)


class TestGitServiceInit:
    """Test GitService initialization."""

    def test_init_with_defaults(self, tmp_path):
        """Test GitService initialization with default settings."""
        project_path = tmp_path / "project"
        project_path.mkdir()

        service = GitService(str(project_path))

        assert service.project_path == project_path
        assert service.worktree_base.exists()  # Should be created
        assert service.git_user_name == "Lazy-Bird Bot"
        assert service.git_user_email == "bot@lazy-bird.dev"

    def test_init_with_custom_settings(self, tmp_path):
        """Test GitService with custom settings."""
        project_path = tmp_path / "project"
        project_path.mkdir()
        worktree_base = tmp_path / "worktrees"

        service = GitService(
            project_path=str(project_path),
            worktree_base=str(worktree_base),
            git_user_name="Test User",
            git_user_email="test@example.com",
        )

        assert service.project_path == project_path
        assert service.worktree_base == worktree_base
        assert service.git_user_name == "Test User"
        assert service.git_user_email == "test@example.com"
        assert worktree_base.exists()  # Should be created


class TestRunGit:
    """Test _run_git helper method."""

    def test_run_git_success(self, tmp_path):
        """Test successful git command execution."""
        service = GitService(str(tmp_path))

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = subprocess.CompletedProcess(
                args=["git", "status"],
                returncode=0,
                stdout="On branch main",
                stderr="",
            )

            result = service._run_git(["status"])

            assert result.returncode == 0
            assert "On branch main" in result.stdout
            mock_run.assert_called_once()

    def test_run_git_failure(self, tmp_path):
        """Test git command failure."""
        service = GitService(str(tmp_path))

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = subprocess.CompletedProcess(
                args=["git", "invalid"],
                returncode=1,
                stdout="",
                stderr="fatal: invalid command",
            )

            with pytest.raises(GitCommandError) as exc_info:
                service._run_git(["invalid"])

            assert "fatal: invalid command" in str(exc_info.value)
            assert exc_info.value.return_code == 1

    def test_run_git_no_check(self, tmp_path):
        """Test git command with check=False doesn't raise exception."""
        service = GitService(str(tmp_path))

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = subprocess.CompletedProcess(
                args=["git", "invalid"],
                returncode=1,
                stdout="",
                stderr="error",
            )

            result = service._run_git(["invalid"], check=False)

            assert result.returncode == 1


class TestGetBaseBranch:
    """Test _get_base_branch method."""

    def test_get_base_branch_main(self, tmp_path):
        """Test detecting 'main' as base branch."""
        service = GitService(str(tmp_path))

        with patch.object(service, "_run_git") as mock_run:
            # First call (check origin/main) returns success
            mock_run.return_value = subprocess.CompletedProcess(
                args=[], returncode=0, stdout="", stderr=""
            )

            branch = service._get_base_branch()

            assert branch == "main"

    def test_get_base_branch_master(self, tmp_path):
        """Test detecting 'master' as base branch."""
        service = GitService(str(tmp_path))

        with patch.object(service, "_run_git") as mock_run:
            # First call (check origin/main) fails, second (origin/master) succeeds
            mock_run.side_effect = [
                subprocess.CompletedProcess(args=[], returncode=1, stdout="", stderr=""),
                subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr=""),
            ]

            branch = service._get_base_branch()

            assert branch == "master"

    def test_get_base_branch_not_found(self, tmp_path):
        """Test error when no base branch found."""
        service = GitService(str(tmp_path))

        with patch.object(service, "_run_git") as mock_run:
            # All checks fail
            mock_run.return_value = subprocess.CompletedProcess(
                args=[], returncode=1, stdout="", stderr=""
            )

            with pytest.raises(GitServiceError) as exc_info:
                service._get_base_branch()

            assert "neither main nor master found" in str(exc_info.value).lower()


class TestCreateWorktree:
    """Test create_worktree method."""

    def test_create_worktree_success(self, tmp_path):
        """Test successful worktree creation."""
        project_path = tmp_path / "project"
        project_path.mkdir()
        worktree_base = tmp_path / "worktrees"

        service = GitService(
            project_path=str(project_path),
            worktree_base=str(worktree_base)
        )

        with patch.object(service, "_run_git") as mock_run:
            with patch.object(service, "_get_base_branch", return_value="main"):
                # Mock all git commands to succeed
                mock_run.return_value = subprocess.CompletedProcess(
                    args=[], returncode=0, stdout="", stderr=""
                )

                worktree_path, branch_name = service.create_worktree(
                    project_id="test-proj",
                    task_id=42,
                )

                assert "test-proj" in str(worktree_path)
                assert "42" in str(worktree_path)
                assert branch_name == "feature-test-proj-42"

    def test_create_worktree_already_exists(self, tmp_path):
        """Test worktree creation when worktree already exists."""
        project_path = tmp_path / "project"
        project_path.mkdir()
        worktree_base = tmp_path / "worktrees"

        service = GitService(
            project_path=str(project_path),
            worktree_base=str(worktree_base)
        )
        existing_worktree = (
            service.worktree_base / "lazy-bird-agent-test-proj-42"
        )
        existing_worktree.mkdir(parents=True)

        with pytest.raises(WorktreeExistsError):
            service.create_worktree(project_id="test-proj", task_id=42)

    def test_create_worktree_with_force(self, tmp_path):
        """Test worktree creation with force=True."""
        project_path = tmp_path / "project"
        project_path.mkdir()
        worktree_base = tmp_path / "worktrees"

        service = GitService(
            project_path=str(project_path),
            worktree_base=str(worktree_base)
        )
        existing_worktree = (
            service.worktree_base / "lazy-bird-agent-test-proj-42"
        )
        existing_worktree.mkdir(parents=True)

        with patch.object(service, "_run_git") as mock_run:
            with patch.object(service, "_get_base_branch", return_value="main"):
                with patch.object(service, "cleanup_worktree"):
                    mock_run.return_value = subprocess.CompletedProcess(
                        args=[], returncode=0, stdout="", stderr=""
                    )

                    worktree_path, branch_name = service.create_worktree(
                        project_id="test-proj",
                        task_id=42,
                        force=True,
                    )

                    assert branch_name == "feature-test-proj-42"


class TestCommitChanges:
    """Test commit_changes method."""

    def test_commit_changes_success(self, tmp_path):
        """Test successful commit."""
        service = GitService(str(tmp_path))
        worktree_path = tmp_path / "worktree"
        worktree_path.mkdir()

        with patch("subprocess.run") as mock_run:
            # Mock git add
            mock_run.side_effect = [
                subprocess.CompletedProcess(
                    args=["git", "add", "-A"],
                    returncode=0,
                    stdout="",
                    stderr="",
                ),
                # Mock git commit
                subprocess.CompletedProcess(
                    args=["git", "commit"],
                    returncode=0,
                    stdout="",
                    stderr="",
                ),
                # Mock git rev-parse (get commit hash)
                subprocess.CompletedProcess(
                    args=["git", "rev-parse", "--short", "HEAD"],
                    returncode=0,
                    stdout="abc1234\n",
                    stderr="",
                ),
            ]

            commit_hash = service.commit_changes(
                worktree_path=worktree_path,
                message="Test commit",
            )

            assert commit_hash == "abc1234"
            assert mock_run.call_count == 3

    def test_commit_changes_with_project_id(self, tmp_path):
        """Test commit with project_id for logging."""
        service = GitService(str(tmp_path))
        worktree_path = tmp_path / "worktree"
        worktree_path.mkdir()

        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = [
                subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr=""),
                subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr=""),
                subprocess.CompletedProcess(args=[], returncode=0, stdout="abc1234", stderr=""),
            ]

            commit_hash = service.commit_changes(
                worktree_path=worktree_path,
                message="Test",
                project_id="my-project",
            )

            assert commit_hash == "abc1234"


class TestPushBranch:
    """Test push_branch method."""

    def test_push_branch_success(self, tmp_path):
        """Test successful branch push."""
        service = GitService(str(tmp_path))
        worktree_path = tmp_path / "worktree"
        worktree_path.mkdir()

        with patch.object(service, "_run_git") as mock_run:
            # First call gets branch name, second pushes
            mock_run.side_effect = [
                subprocess.CompletedProcess(
                    args=[], returncode=0, stdout="feature-test-42\n", stderr=""
                ),
                subprocess.CompletedProcess(
                    args=[], returncode=0, stdout="", stderr=""
                ),
            ]

            service.push_branch(worktree_path)

            assert mock_run.call_count == 2

    def test_push_branch_with_force(self, tmp_path):
        """Test force push."""
        service = GitService(str(tmp_path))
        worktree_path = tmp_path / "worktree"
        worktree_path.mkdir()

        with patch.object(service, "_run_git") as mock_run:
            mock_run.side_effect = [
                subprocess.CompletedProcess(
                    args=[], returncode=0, stdout="feature-test-42\n", stderr=""
                ),
                subprocess.CompletedProcess(
                    args=[], returncode=0, stdout="", stderr=""
                ),
            ]

            service.push_branch(worktree_path, force=True)

            # Check that --force-with-lease was used
            push_call = mock_run.call_args_list[1]
            assert "--force-with-lease" in push_call[0][0]


class TestCleanupWorktree:
    """Test cleanup_worktree method."""

    def test_cleanup_worktree_success(self, tmp_path):
        """Test successful worktree cleanup."""
        service = GitService(str(tmp_path))
        worktree_path = tmp_path / "worktree"
        worktree_path.mkdir()

        with patch.object(service, "_run_git") as mock_run:
            mock_run.return_value = subprocess.CompletedProcess(
                args=[], returncode=0, stdout="", stderr=""
            )

            service.cleanup_worktree(
                worktree_path=worktree_path,
                branch_name="feature-test-42",
            )

            # Should call: worktree remove, worktree prune, branch -D
            assert mock_run.call_count == 3

    def test_cleanup_worktree_fallback_to_rm(self, tmp_path):
        """Test cleanup falls back to rm -rf if git worktree remove fails."""
        service = GitService(str(tmp_path))
        worktree_path = tmp_path / "worktree"
        worktree_path.mkdir()

        with patch.object(service, "_run_git") as mock_run:
            # First call (worktree remove) raises GitCommandError
            def side_effect_fn(args, **kwargs):
                if "worktree" in args and "remove" in args:
                    raise GitCommandError(
                        command="git worktree remove",
                        return_code=1,
                        stderr="error"
                    )
                return subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr="")

            mock_run.side_effect = side_effect_fn

            with patch("lazy_bird.services.git_service.shutil.rmtree") as mock_rmtree:
                service.cleanup_worktree(
                    worktree_path=worktree_path,
                    branch_name="feature-test-42",
                )

                # Should have called shutil.rmtree as fallback
                mock_rmtree.assert_called_once()


class TestGetDiffStats:
    """Test get_diff_stats method."""

    def test_get_diff_stats_with_changes(self, tmp_path):
        """Test getting diff statistics."""
        service = GitService(str(tmp_path))
        worktree_path = tmp_path / "worktree"
        worktree_path.mkdir()

        with patch.object(service, "_run_git") as mock_run:
            mock_run.return_value = subprocess.CompletedProcess(
                args=[],
                returncode=0,
                stdout="file1.py | 10 ++++++++++\n"
                "file2.py | 5 ++---\n"
                "2 files changed, 12 insertions(+), 3 deletions(-)\n",
                stderr="",
            )

            stats = service.get_diff_stats(worktree_path)

            assert stats["files_changed"] == 2
            assert stats["insertions"] == 12
            assert stats["deletions"] == 3

    def test_get_diff_stats_no_changes(self, tmp_path):
        """Test getting diff stats when no changes."""
        service = GitService(str(tmp_path))
        worktree_path = tmp_path / "worktree"
        worktree_path.mkdir()

        with patch.object(service, "_run_git") as mock_run:
            mock_run.return_value = subprocess.CompletedProcess(
                args=[],
                returncode=0,
                stdout="",
                stderr="",
            )

            stats = service.get_diff_stats(worktree_path)

            assert stats["files_changed"] == 0
            assert stats["insertions"] == 0
            assert stats["deletions"] == 0


class TestGitServiceErrors:
    """Test GitService exception classes."""

    def test_git_command_error(self):
        """Test GitCommandError exception."""
        error = GitCommandError(
            command="git status",
            return_code=1,
            stderr="fatal: not a git repository",
        )

        assert error.command == "git status"
        assert error.return_code == 1
        assert "fatal: not a git repository" in error.stderr
        assert "git status" in str(error)

    def test_worktree_exists_error(self):
        """Test WorktreeExistsError exception."""
        error = WorktreeExistsError("Worktree exists at /tmp/worktree")

        assert "Worktree exists" in str(error)
        assert isinstance(error, GitServiceError)

    def test_git_service_error(self):
        """Test base GitServiceError."""
        error = GitServiceError("Something went wrong")

        assert "Something went wrong" in str(error)
