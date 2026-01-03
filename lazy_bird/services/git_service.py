"""Git service for worktree and repository operations.

This module provides git operations for Lazy-Bird task execution:
- Creating isolated git worktrees for task execution
- Committing changes made by Claude
- Pushing branches to remote
- Cleaning up worktrees after task completion

All operations use subprocess to run git commands and include
comprehensive error handling and logging.
"""

import os
import shutil
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from lazy_bird.core.config import settings
from lazy_bird.core.logging import get_logger

logger = get_logger(__name__)


class GitServiceError(Exception):
    """Base exception for GitService errors."""

    pass


class WorktreeExistsError(GitServiceError):
    """Worktree already exists error."""

    pass


class GitCommandError(GitServiceError):
    """Git command execution failed."""

    def __init__(self, command: str, return_code: int, stderr: str):
        self.command = command
        self.return_code = return_code
        self.stderr = stderr
        super().__init__(
            f"Git command failed (exit {return_code}): {command}\n{stderr}"
        )


class GitService:
    """Service for git repository and worktree operations.

    This service handles all git operations required for task execution:
    - Worktree creation and cleanup
    - Branch management
    - Committing changes
    - Pushing to remote

    Attributes:
        project_path: Path to the project repository
        worktree_base: Base directory for worktrees (from settings.WORKTREE_BASE_PATH)
        git_user_name: Git user name for commits
        git_user_email: Git user email for commits

    Example:
        >>> service = GitService("/path/to/project")
        >>> worktree_path = service.create_worktree(
        ...     project_id="my-project",
        ...     task_id=42
        ... )
        >>> service.commit_changes(
        ...     worktree_path=worktree_path,
        ...     message="Task #42: Add feature"
        ... )
        >>> service.push_branch(worktree_path)
        >>> service.cleanup_worktree(worktree_path)
    """

    def __init__(
        self,
        project_path: str,
        worktree_base: Optional[str] = None,
        git_user_name: Optional[str] = None,
        git_user_email: Optional[str] = None,
    ):
        """Initialize GitService.

        Args:
            project_path: Path to the main project repository
            worktree_base: Base directory for worktrees (default: from settings)
            git_user_name: Git user name for commits (default: from settings)
            git_user_email: Git user email for commits (default: from settings)
        """
        self.project_path = Path(project_path).resolve()
        self.worktree_base = Path(worktree_base or settings.WORKTREE_BASE_PATH)
        self.git_user_name = git_user_name or settings.GIT_USER_NAME
        self.git_user_email = git_user_email or settings.GIT_USER_EMAIL

        # Ensure worktree base directory exists
        self.worktree_base.mkdir(parents=True, exist_ok=True)

        logger.debug(
            f"GitService initialized: project={self.project_path}, "
            f"worktree_base={self.worktree_base}"
        )

    def _run_git(
        self,
        args: List[str],
        cwd: Optional[Path] = None,
        check: bool = True,
        capture_output: bool = True,
    ) -> subprocess.CompletedProcess:
        """Run a git command.

        Args:
            args: Git command arguments (without 'git' prefix)
            cwd: Working directory for command (default: project_path)
            check: Raise exception on non-zero exit code
            capture_output: Capture stdout/stderr

        Returns:
            CompletedProcess instance

        Raises:
            GitCommandError: If command fails and check=True
        """
        cmd = ["git"] + args
        cwd = cwd or self.project_path

        logger.debug(f"Running git command: {' '.join(cmd)} (cwd={cwd})")

        try:
            result = subprocess.run(
                cmd,
                cwd=str(cwd),
                capture_output=capture_output,
                text=True,
                check=False,  # We'll check manually for better error messages
            )

            if check and result.returncode != 0:
                raise GitCommandError(
                    command=" ".join(cmd),
                    return_code=result.returncode,
                    stderr=result.stderr.strip() if result.stderr else "",
                )

            return result

        except FileNotFoundError:
            raise GitServiceError("git command not found - is git installed?")
        except Exception as e:
            if isinstance(e, GitCommandError):
                raise
            raise GitServiceError(f"Failed to execute git command: {str(e)}") from e

    def _get_base_branch(self) -> str:
        """Determine the base branch (main or master).

        Returns:
            Name of base branch (e.g., 'main' or 'master')

        Raises:
            GitServiceError: If neither main nor master exists
        """
        # Check if remote main exists
        result = self._run_git(
            ["show-ref", "--verify", "--quiet", "refs/remotes/origin/main"],
            check=False,
        )
        if result.returncode == 0:
            return "main"

        # Check if remote master exists
        result = self._run_git(
            ["show-ref", "--verify", "--quiet", "refs/remotes/origin/master"],
            check=False,
        )
        if result.returncode == 0:
            return "master"

        # Fallback to local branches
        result = self._run_git(
            ["show-ref", "--verify", "--quiet", "refs/heads/main"],
            check=False,
        )
        if result.returncode == 0:
            return "main"

        result = self._run_git(
            ["show-ref", "--verify", "--quiet", "refs/heads/master"],
            check=False,
        )
        if result.returncode == 0:
            return "master"

        raise GitServiceError(
            "Could not determine base branch - neither main nor master found"
        )

    def create_worktree(
        self,
        project_id: str,
        task_id: int,
        base_branch: Optional[str] = None,
        force: bool = False,
    ) -> Tuple[Path, str]:
        """Create a git worktree for task execution.

        Creates an isolated git worktree with a feature branch for the task.
        If a worktree already exists at the target path, it can be forcefully
        recreated if force=True.

        Args:
            project_id: Project identifier (e.g., "my-project")
            task_id: Task/issue number
            base_branch: Base branch to branch from (default: auto-detect main/master)
            force: Force recreation if worktree exists

        Returns:
            Tuple of (worktree_path, branch_name)

        Raises:
            WorktreeExistsError: If worktree exists and force=False
            GitServiceError: If git operations fail

        Example:
            >>> worktree_path, branch_name = service.create_worktree("proj", 42)
            >>> print(worktree_path)
            /tmp/lazy-bird-worktrees/lazy-bird-agent-proj-42
            >>> print(branch_name)
            feature-proj-42
        """
        branch_name = f"feature-{project_id}-{task_id}"
        worktree_path = self.worktree_base / f"lazy-bird-agent-{project_id}-{task_id}"

        logger.info(
            f"[{project_id}] Creating worktree: {worktree_path}",
            extra={
                "extra_fields": {
                    "project_id": project_id,
                    "task_id": task_id,
                    "branch_name": branch_name,
                    "worktree_path": str(worktree_path),
                }
            },
        )

        # Check if worktree already exists
        if worktree_path.exists():
            if force:
                logger.warning(
                    f"[{project_id}] Worktree exists, forcing removal: {worktree_path}"
                )
                self.cleanup_worktree(worktree_path, branch_name)
            else:
                raise WorktreeExistsError(
                    f"Worktree already exists: {worktree_path}. Use force=True to recreate."
                )

        # Check if branch exists and delete it
        result = self._run_git(
            ["show-ref", "--verify", "--quiet", f"refs/heads/{branch_name}"],
            check=False,
        )
        if result.returncode == 0:
            logger.warning(
                f"[{project_id}] Branch exists, deleting: {branch_name}"
            )
            self._run_git(["branch", "-D", branch_name], check=False)

        # Fetch latest from remote
        logger.info(f"[{project_id}] Fetching latest from remote...")
        try:
            self._run_git(["fetch", "origin"])
            logger.debug(f"[{project_id}] Fetched latest from origin")
        except GitCommandError as e:
            logger.warning(
                f"[{project_id}] Failed to fetch from origin: {e.stderr}"
            )

        # Determine base branch
        if not base_branch:
            base_branch = self._get_base_branch()
            logger.debug(f"[{project_id}] Using base branch: {base_branch}")

        # Create worktree with new branch
        logger.debug(
            f"[{project_id}] Creating worktree from origin/{base_branch}"
        )
        self._run_git(
            [
                "worktree",
                "add",
                "-b",
                branch_name,
                str(worktree_path),
                f"origin/{base_branch}",
            ]
        )

        logger.info(
            f"[{project_id}] Worktree created successfully",
            extra={
                "extra_fields": {
                    "worktree_path": str(worktree_path),
                    "branch_name": branch_name,
                }
            },
        )

        return worktree_path, branch_name

    def commit_changes(
        self,
        worktree_path: Path,
        message: str,
        project_id: Optional[str] = None,
        allow_empty: bool = False,
    ) -> str:
        """Commit all changes in the worktree.

        Stages all changes (including deletions) and creates a commit.

        Args:
            worktree_path: Path to the worktree
            message: Commit message
            project_id: Project ID for logging (optional)
            allow_empty: Allow empty commits

        Returns:
            str: Commit hash (short SHA)

        Raises:
            GitServiceError: If commit fails

        Example:
            >>> commit_hash = service.commit_changes(
            ...     worktree_path=Path("/tmp/worktree"),
            ...     message="Task #42: Add feature\\n\\nImplemented by Lazy-Bird"
            ... )
            >>> print(commit_hash)
            abc1234
        """
        prefix = f"[{project_id}] " if project_id else ""

        logger.info(
            f"{prefix}Committing changes in {worktree_path}",
            extra={
                "extra_fields": {
                    "worktree_path": str(worktree_path),
                    "project_id": project_id,
                }
            },
        )

        # Stage all changes
        self._run_git(["add", "-A"], cwd=worktree_path)
        logger.debug(f"{prefix}Staged all changes")

        # Create commit
        cmd_args = ["commit", "-m", message]
        if allow_empty:
            cmd_args.append("--allow-empty")

        # Set git user for this commit
        env = os.environ.copy()
        env["GIT_AUTHOR_NAME"] = self.git_user_name
        env["GIT_AUTHOR_EMAIL"] = self.git_user_email
        env["GIT_COMMITTER_NAME"] = self.git_user_name
        env["GIT_COMMITTER_EMAIL"] = self.git_user_email

        try:
            result = subprocess.run(
                ["git"] + cmd_args,
                cwd=str(worktree_path),
                env=env,
                capture_output=True,
                text=True,
                check=True,
            )
        except subprocess.CalledProcessError as e:
            raise GitCommandError(
                command=" ".join(["git"] + cmd_args),
                return_code=e.returncode,
                stderr=e.stderr.strip() if e.stderr else "",
            )

        # Get commit hash
        result = self._run_git(["rev-parse", "--short", "HEAD"], cwd=worktree_path)
        commit_hash = result.stdout.strip()

        logger.info(
            f"{prefix}Committed changes: {commit_hash}",
            extra={"extra_fields": {"commit_hash": commit_hash}},
        )

        return commit_hash

    def push_branch(
        self,
        worktree_path: Path,
        remote: str = "origin",
        force: bool = False,
        project_id: Optional[str] = None,
    ) -> None:
        """Push the branch to remote repository.

        Args:
            worktree_path: Path to the worktree
            remote: Remote name (default: "origin")
            force: Use --force-with-lease for force push
            project_id: Project ID for logging (optional)

        Raises:
            GitServiceError: If push fails

        Example:
            >>> service.push_branch(Path("/tmp/worktree"))
        """
        prefix = f"[{project_id}] " if project_id else ""

        logger.info(
            f"{prefix}Pushing branch to {remote}",
            extra={
                "extra_fields": {
                    "worktree_path": str(worktree_path),
                    "remote": remote,
                    "force": force,
                }
            },
        )

        # Get current branch name
        result = self._run_git(
            ["rev-parse", "--abbrev-ref", "HEAD"], cwd=worktree_path
        )
        branch_name = result.stdout.strip()

        # Build push command
        cmd_args = ["push", "-u", remote, branch_name]
        if force:
            cmd_args.insert(2, "--force-with-lease")

        # Push branch
        self._run_git(cmd_args, cwd=worktree_path)

        logger.info(
            f"{prefix}Pushed branch {branch_name} to {remote}",
            extra={"extra_fields": {"branch_name": branch_name}},
        )

    def cleanup_worktree(
        self,
        worktree_path: Path,
        branch_name: Optional[str] = None,
        project_id: Optional[str] = None,
    ) -> None:
        """Clean up a git worktree and associated branch.

        Removes the worktree and optionally deletes the local branch.

        Args:
            worktree_path: Path to the worktree to remove
            branch_name: Branch name to delete (if None, won't delete branch)
            project_id: Project ID for logging (optional)

        Raises:
            GitServiceError: If cleanup fails

        Example:
            >>> service.cleanup_worktree(
            ...     Path("/tmp/worktree"),
            ...     "feature-proj-42"
            ... )
        """
        prefix = f"[{project_id}] " if project_id else ""

        logger.info(
            f"{prefix}Cleaning up worktree: {worktree_path}",
            extra={
                "extra_fields": {
                    "worktree_path": str(worktree_path),
                    "branch_name": branch_name,
                }
            },
        )

        # Remove worktree
        if worktree_path.exists():
            try:
                self._run_git(
                    ["worktree", "remove", str(worktree_path), "--force"],
                    check=False,
                )
                logger.debug(f"{prefix}Removed worktree via git")
            except Exception as e:
                logger.warning(
                    f"{prefix}git worktree remove failed, using rm -rf: {e}"
                )
                shutil.rmtree(worktree_path, ignore_errors=True)

        # Prune worktree list
        try:
            self._run_git(["worktree", "prune"], check=False)
        except Exception as e:
            logger.warning(f"{prefix}Failed to prune worktrees: {e}")

        # Delete local branch if specified
        if branch_name:
            try:
                self._run_git(["branch", "-D", branch_name], check=False)
                logger.debug(f"{prefix}Deleted local branch: {branch_name}")
            except Exception as e:
                logger.warning(f"{prefix}Failed to delete branch: {e}")

        logger.info(
            f"{prefix}Worktree cleanup complete",
            extra={"extra_fields": {"worktree_path": str(worktree_path)}},
        )

    def get_diff_stats(self, worktree_path: Path) -> Dict[str, int]:
        """Get statistics about changes in the worktree.

        Args:
            worktree_path: Path to the worktree

        Returns:
            dict: Statistics with keys:
                - files_changed: Number of files changed
                - insertions: Number of lines inserted
                - deletions: Number of lines deleted

        Example:
            >>> stats = service.get_diff_stats(Path("/tmp/worktree"))
            >>> print(stats)
            {"files_changed": 5, "insertions": 120, "deletions": 30}
        """
        # Get diff statistics
        result = self._run_git(
            ["diff", "--stat", "--cached"], cwd=worktree_path
        )

        # Parse statistics (last line usually contains summary)
        lines = result.stdout.strip().split("\n")
        if not lines or len(lines) < 2:
            return {"files_changed": 0, "insertions": 0, "deletions": 0}

        # Parse summary line (e.g., "5 files changed, 120 insertions(+), 30 deletions(-)")
        summary = lines[-1]
        stats = {"files_changed": 0, "insertions": 0, "deletions": 0}

        import re

        if match := re.search(r"(\d+) files? changed", summary):
            stats["files_changed"] = int(match.group(1))
        if match := re.search(r"(\d+) insertions?", summary):
            stats["insertions"] = int(match.group(1))
        if match := re.search(r"(\d+) deletions?", summary):
            stats["deletions"] = int(match.group(1))

        return stats


__all__ = [
    "GitService",
    "GitServiceError",
    "WorktreeExistsError",
    "GitCommandError",
]
