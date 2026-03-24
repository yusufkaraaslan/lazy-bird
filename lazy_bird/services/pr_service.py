"""Pull Request/Merge Request service for GitHub and GitLab.

This module provides the PRService class for creating pull requests (GitHub)
and merge requests (GitLab) with templates, issue linking, and automation.
"""

import logging
import re
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List

logger = logging.getLogger(__name__)


class PRServiceError(Exception):
    """Base exception for PR service errors."""

    pass


class PRCreationError(PRServiceError):
    """Exception raised when PR/MR creation fails."""

    def __init__(self, platform: str, command: str, stderr: str):
        self.platform = platform
        self.command = command
        self.stderr = stderr
        super().__init__(
            f"{platform} PR/MR creation failed:\n" f"Command: {command}\n" f"Error: {stderr}"
        )


class PRService:
    """Service for creating pull requests and merge requests.

    Supports both GitHub (via gh CLI) and GitLab (via glab CLI).
    """

    def __init__(self, working_directory: Optional[Path] = None):
        """Initialize PRService.

        Args:
            working_directory: Directory to execute commands in (default: current)
        """
        self.working_directory = working_directory or Path.cwd()

    def create_pull_request(
        self,
        title: str,
        body: str,
        base_branch: str,
        head_branch: str,
        repository: Optional[str] = None,
        labels: Optional[List[str]] = None,
        draft: bool = False,
        project_id: Optional[str] = None,
        task_id: Optional[int] = None,
        issue_number: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Create a GitHub pull request.

        Args:
            title: PR title
            body: PR description
            base_branch: Target branch (e.g., "main")
            head_branch: Source branch with changes
            repository: Repository (e.g., "user/repo", optional if in repo)
            labels: List of labels to add
            draft: Create as draft PR
            project_id: Project identifier for logging
            task_id: Task ID for logging
            issue_number: Original issue number to link and comment

        Returns:
            dict: PR creation result
                - success: bool
                - url: str (PR URL)
                - number: int (PR number)
                - platform: str ("github")

        Raises:
            PRCreationError: If PR creation fails
        """
        logger.info(
            f"Creating GitHub pull request",
            extra={
                "extra_fields": {
                    "project_id": project_id,
                    "task_id": task_id,
                    "title": title,
                    "base": base_branch,
                    "head": head_branch,
                    "draft": draft,
                }
            },
        )

        # Build gh pr create command
        command = ["gh", "pr", "create"]

        if repository:
            command.extend(["--repo", repository])

        command.extend(
            [
                "--title",
                title,
                "--body",
                body,
                "--base",
                base_branch,
                "--head",
                head_branch,
            ]
        )

        # Add labels
        if labels:
            for label in labels:
                command.extend(["--label", label])

        # Draft PR
        if draft:
            command.append("--draft")

        try:
            # Execute gh pr create
            result = subprocess.run(
                command,
                cwd=self.working_directory,
                capture_output=True,
                text=True,
                timeout=60,
            )

            if result.returncode != 0:
                raise PRCreationError("GitHub", " ".join(command), result.stderr)

            # Extract PR URL from output
            pr_url = result.stdout.strip()

            # Get PR number from URL
            pr_number = self._extract_pr_number_from_url(pr_url)

            logger.info(
                f"Pull request created successfully",
                extra={
                    "extra_fields": {
                        "project_id": project_id,
                        "task_id": task_id,
                        "pr_url": pr_url,
                        "pr_number": pr_number,
                    }
                },
            )

            # Comment on original issue if provided
            if issue_number:
                self._comment_on_github_issue(
                    issue_number=issue_number,
                    pr_url=pr_url,
                    project_id=project_id,
                    task_id=task_id,
                    repository=repository,
                )

            return {
                "success": True,
                "url": pr_url,
                "number": pr_number,
                "platform": "github",
            }

        except subprocess.TimeoutExpired as e:
            error_msg = f"GitHub PR creation timed out after 60s"
            logger.error(error_msg, extra={"extra_fields": {"project_id": project_id}})
            raise PRServiceError(error_msg) from e

        except Exception as e:
            logger.error(
                f"GitHub PR creation failed: {str(e)}",
                extra={"extra_fields": {"project_id": project_id, "error": str(e)}},
                exc_info=True,
            )
            raise

    def create_merge_request(
        self,
        title: str,
        body: str,
        base_branch: str,
        head_branch: str,
        repository: Optional[str] = None,
        labels: Optional[List[str]] = None,
        draft: bool = False,
        project_id: Optional[str] = None,
        task_id: Optional[int] = None,
        issue_number: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Create a GitLab merge request.

        Args:
            title: MR title
            body: MR description
            base_branch: Target branch (e.g., "main")
            head_branch: Source branch with changes
            repository: Repository (e.g., "group/project", optional if in repo)
            labels: List of labels to add
            draft: Create as draft MR
            project_id: Project identifier for logging
            task_id: Task ID for logging
            issue_number: Original issue number to link and comment

        Returns:
            dict: MR creation result
                - success: bool
                - url: str (MR URL)
                - number: int (MR IID)
                - platform: str ("gitlab")

        Raises:
            PRCreationError: If MR creation fails
        """
        logger.info(
            f"Creating GitLab merge request",
            extra={
                "extra_fields": {
                    "project_id": project_id,
                    "task_id": task_id,
                    "title": title,
                    "base": base_branch,
                    "head": head_branch,
                    "draft": draft,
                }
            },
        )

        # Build glab mr create command
        command = ["glab", "mr", "create"]

        if repository:
            command.extend(["--repo", repository])

        # GitLab uses --title for draft MRs
        mr_title = f"Draft: {title}" if draft else title

        command.extend(
            [
                "--title",
                mr_title,
                "--description",
                body,
                "--target-branch",
                base_branch,
                "--source-branch",
                head_branch,
            ]
        )

        # Add labels
        if labels:
            command.extend(["--label", ",".join(labels)])

        # Set to draft
        if draft:
            command.append("--draft")

        try:
            # Execute glab mr create
            result = subprocess.run(
                command,
                cwd=self.working_directory,
                capture_output=True,
                text=True,
                timeout=60,
            )

            if result.returncode != 0:
                raise PRCreationError("GitLab", " ".join(command), result.stderr)

            # Extract MR URL from output
            mr_url = result.stdout.strip()

            # Get MR IID from URL
            mr_iid = self._extract_mr_iid_from_url(mr_url)

            logger.info(
                f"Merge request created successfully",
                extra={
                    "extra_fields": {
                        "project_id": project_id,
                        "task_id": task_id,
                        "mr_url": mr_url,
                        "mr_iid": mr_iid,
                    }
                },
            )

            # Comment on original issue if provided
            if issue_number:
                self._comment_on_gitlab_issue(
                    issue_number=issue_number,
                    mr_url=mr_url,
                    project_id=project_id,
                    task_id=task_id,
                    repository=repository,
                )

            return {
                "success": True,
                "url": mr_url,
                "number": mr_iid,
                "platform": "gitlab",
            }

        except subprocess.TimeoutExpired as e:
            error_msg = f"GitLab MR creation timed out after 60s"
            logger.error(error_msg, extra={"extra_fields": {"project_id": project_id}})
            raise PRServiceError(error_msg) from e

        except Exception as e:
            logger.error(
                f"GitLab MR creation failed: {str(e)}",
                extra={"extra_fields": {"project_id": project_id, "error": str(e)}},
                exc_info=True,
            )
            raise

    def build_pr_body(
        self,
        task_description: str,
        implementation_summary: Optional[str] = None,
        test_results: Optional[Dict[str, Any]] = None,
        diff_stats: Optional[Dict[str, int]] = None,
    ) -> str:
        """Build PR/MR body from task details.

        Args:
            task_description: Original task description
            implementation_summary: Claude's implementation summary (optional)
            test_results: Test execution results (optional)
            diff_stats: Git diff statistics (optional)

        Returns:
            str: Formatted PR/MR body
        """
        sections = []

        # Task description
        sections.append("## Task Description\n")
        sections.append(task_description)

        # Implementation summary
        if implementation_summary:
            sections.append("\n## Implementation Summary\n")
            sections.append(implementation_summary)

        # Test results
        if test_results:
            sections.append("\n## Test Results\n")
            if test_results.get("success"):
                sections.append(f"✅ All tests passed!")
                sections.append(f"\n- **Total:** {test_results['stats']['total']}")
                sections.append(f"- **Passed:** {test_results['stats']['passed']}")
                sections.append(f"- **Execution Time:** {test_results['execution_time']:.2f}s")
            else:
                sections.append(f"⚠️ Some tests failed")
                sections.append(f"\n- **Total:** {test_results['stats']['total']}")
                sections.append(f"- **Passed:** {test_results['stats']['passed']}")
                sections.append(f"- **Failed:** {test_results['stats']['failed']}")

        # Diff stats
        if diff_stats:
            sections.append("\n## Changes\n")
            sections.append(f"- **Files changed:** {diff_stats.get('files_changed', 0)}")
            sections.append(f"- **Insertions:** +{diff_stats.get('insertions', 0)}")
            sections.append(f"- **Deletions:** -{diff_stats.get('deletions', 0)}")

        # Footer
        sections.append("\n---\n")
        sections.append("🤖 **This PR was automatically generated by Lazy-Bird**\n")
        sections.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}\n")
        sections.append("\nFor issues or questions: https://github.com/yusufkaraaslan/lazy-bird")

        return "\n".join(sections)

    def _extract_pr_number_from_url(self, url: str) -> int:
        """Extract PR number from GitHub URL.

        Args:
            url: GitHub PR URL

        Returns:
            int: PR number
        """
        match = re.search(r"/pull/(\d+)", url)
        if match:
            return int(match.group(1))
        return 0

    def _extract_mr_iid_from_url(self, url: str) -> int:
        """Extract MR IID from GitLab URL.

        Args:
            url: GitLab MR URL

        Returns:
            int: MR IID (internal ID)
        """
        match = re.search(r"/-/merge_requests/(\d+)", url)
        if match:
            return int(match.group(1))
        return 0

    def _comment_on_github_issue(
        self,
        issue_number: int,
        pr_url: str,
        project_id: Optional[str] = None,
        task_id: Optional[int] = None,
        repository: Optional[str] = None,
    ) -> None:
        """Add comment to GitHub issue linking to PR.

        Args:
            issue_number: Issue number
            pr_url: Pull request URL
            project_id: Project ID for logging
            task_id: Task ID for logging
            repository: Repository (optional)
        """
        comment = f"""✅ **Implementation Complete**

**Pull Request:** {pr_url}

Please review the changes and merge if satisfied.

---
🤖 Automated by Lazy-Bird"""

        command = ["gh", "issue", "comment", str(issue_number), "--body", comment]

        if repository:
            command.extend(["--repo", repository])

        try:
            subprocess.run(
                command,
                cwd=self.working_directory,
                capture_output=True,
                text=True,
                timeout=30,
                check=True,
            )

            logger.info(
                f"Commented on GitHub issue #{issue_number}",
                extra={
                    "extra_fields": {
                        "project_id": project_id,
                        "task_id": task_id,
                        "issue_number": issue_number,
                    }
                },
            )

        except Exception as e:
            # Log error but don't fail the PR creation
            logger.warning(
                f"Failed to comment on issue #{issue_number}: {str(e)}",
                extra={"extra_fields": {"issue_number": issue_number, "error": str(e)}},
            )

    def _comment_on_gitlab_issue(
        self,
        issue_number: int,
        mr_url: str,
        project_id: Optional[str] = None,
        task_id: Optional[int] = None,
        repository: Optional[str] = None,
    ) -> None:
        """Add comment to GitLab issue linking to MR.

        Args:
            issue_number: Issue number (IID)
            mr_url: Merge request URL
            project_id: Project ID for logging
            task_id: Task ID for logging
            repository: Repository (optional)
        """
        comment = f"""✅ **Implementation Complete**

**Merge Request:** {mr_url}

Please review the changes and merge if satisfied.

---
🤖 Automated by Lazy-Bird"""

        command = ["glab", "issue", "note", str(issue_number), "--message", comment]

        if repository:
            command.extend(["--repo", repository])

        try:
            subprocess.run(
                command,
                cwd=self.working_directory,
                capture_output=True,
                text=True,
                timeout=30,
                check=True,
            )

            logger.info(
                f"Commented on GitLab issue #{issue_number}",
                extra={
                    "extra_fields": {
                        "project_id": project_id,
                        "task_id": task_id,
                        "issue_number": issue_number,
                    }
                },
            )

        except Exception as e:
            # Log error but don't fail the MR creation
            logger.warning(
                f"Failed to comment on issue #{issue_number}: {str(e)}",
                extra={"extra_fields": {"issue_number": issue_number, "error": str(e)}},
            )


__all__ = [
    "PRService",
    "PRServiceError",
    "PRCreationError",
]
