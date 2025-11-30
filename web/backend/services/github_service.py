"""
GitHub Service
Handles GitHub API integration for issues
"""
import os
import logging
from github import Github, GithubException
from typing import Optional, List, Dict, Any

logger = logging.getLogger(__name__)


class GitHubService:
    """Service for interacting with GitHub API"""

    def __init__(self, token: Optional[str] = None):
        """
        Initialize GitHub service

        Args:
            token: GitHub API token (reads from env if not provided)
        """
        self.token = token or os.environ.get('GITHUB_TOKEN') or self._load_token_from_file()
        self.github = Github(self.token) if self.token else None

        if not self.github:
            logger.warning("GitHub token not configured. GitHub API features will be limited.")

    def _load_token_from_file(self) -> Optional[str]:
        """Load GitHub token from secrets file"""
        token_path = os.path.expanduser('~/.config/lazy_birtd/secrets/github_token')
        try:
            if os.path.exists(token_path):
                with open(token_path, 'r') as f:
                    return f.read().strip()
        except Exception as e:
            logger.error(f"Error loading GitHub token from file: {e}")
        return None

    def get_repository(self, repo_url: str):
        """
        Get GitHub repository object

        Args:
            repo_url: Repository URL (https://github.com/user/repo)

        Returns:
            Repository object or None
        """
        if not self.github:
            raise Exception("GitHub token not configured")

        try:
            # Extract owner/repo from URL
            parts = repo_url.rstrip('/').split('/')
            owner, repo = parts[-2], parts[-1]
            return self.github.get_repo(f"{owner}/{repo}")
        except GithubException as e:
            logger.error(f"Error getting repository {repo_url}: {e}")
            raise

    def get_issue(self, repo_url: str, issue_number: int) -> Optional[Dict[str, Any]]:
        """
        Get issue details from GitHub

        Args:
            repo_url: Repository URL
            issue_number: Issue number

        Returns:
            Issue data dict or None
        """
        try:
            repo = self.get_repository(repo_url)
            issue = repo.get_issue(issue_number)

            return {
                'number': issue.number,
                'title': issue.title,
                'body': issue.body or '',
                'state': issue.state,
                'labels': [label.name for label in issue.labels],
                'created_at': issue.created_at.isoformat(),
                'updated_at': issue.updated_at.isoformat(),
                'url': issue.html_url,
                'author': issue.user.login if issue.user else 'unknown'
            }
        except GithubException as e:
            logger.error(f"Error getting issue {issue_number} from {repo_url}: {e}")
            return None

    def list_issues(
        self,
        repo_url: str,
        state: str = 'open',
        labels: Optional[List[str]] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        List issues from GitHub repository

        Args:
            repo_url: Repository URL
            state: Issue state (open, closed, all)
            labels: Filter by labels
            limit: Maximum number of issues to return

        Returns:
            List of issue dicts
        """
        try:
            repo = self.get_repository(repo_url)

            # Build label string
            label_str = ','.join(labels) if labels else None

            issues = repo.get_issues(state=state, labels=label_str)

            result = []
            for issue in issues[:limit]:
                result.append({
                    'number': issue.number,
                    'title': issue.title,
                    'state': issue.state,
                    'labels': [label.name for label in issue.labels],
                    'created_at': issue.created_at.isoformat(),
                    'updated_at': issue.updated_at.isoformat(),
                    'url': issue.html_url
                })

            return result
        except GithubException as e:
            logger.error(f"Error listing issues from {repo_url}: {e}")
            return []

    def add_label(self, repo_url: str, issue_number: int, label: str) -> bool:
        """
        Add label to issue

        Args:
            repo_url: Repository URL
            issue_number: Issue number
            label: Label to add

        Returns:
            True if successful
        """
        try:
            repo = self.get_repository(repo_url)
            issue = repo.get_issue(issue_number)
            issue.add_to_labels(label)
            logger.info(f"Added label '{label}' to issue #{issue_number}")
            return True
        except GithubException as e:
            logger.error(f"Error adding label to issue {issue_number}: {e}")
            return False

    def remove_label(self, repo_url: str, issue_number: int, label: str) -> bool:
        """
        Remove label from issue

        Args:
            repo_url: Repository URL
            issue_number: Issue number
            label: Label to remove

        Returns:
            True if successful
        """
        try:
            repo = self.get_repository(repo_url)
            issue = repo.get_issue(issue_number)
            issue.remove_from_labels(label)
            logger.info(f"Removed label '{label}' from issue #{issue_number}")
            return True
        except GithubException as e:
            logger.error(f"Error removing label from issue {issue_number}: {e}")
            return False

    def add_comment(self, repo_url: str, issue_number: int, comment: str) -> bool:
        """
        Add comment to issue

        Args:
            repo_url: Repository URL
            issue_number: Issue number
            comment: Comment text

        Returns:
            True if successful
        """
        try:
            repo = self.get_repository(repo_url)
            issue = repo.get_issue(issue_number)
            issue.create_comment(comment)
            logger.info(f"Added comment to issue #{issue_number}")
            return True
        except GithubException as e:
            logger.error(f"Error adding comment to issue {issue_number}: {e}")
            return False

    def update_issue_status(
        self,
        repo_url: str,
        issue_number: int,
        status: str,
        add_comment: bool = True
    ) -> bool:
        """
        Update issue status using labels

        Args:
            repo_url: Repository URL
            issue_number: Issue number
            status: New status (queued, processing, testing, done, failed)
            add_comment: Whether to add a comment about the status change

        Returns:
            True if successful
        """
        try:
            repo = self.get_repository(repo_url)
            issue = repo.get_issue(issue_number)

            # Remove old status labels
            status_labels = ['queued', 'processing', 'testing', 'done', 'failed']
            for label in status_labels:
                try:
                    issue.remove_from_labels(label)
                except:
                    pass

            # Add new status label
            issue.add_to_labels(status)

            # Add comment if requested
            if add_comment:
                status_messages = {
                    'queued': '🔵 Task queued for processing',
                    'processing': '🟡 Task is being processed by agent',
                    'testing': '🟠 Running tests',
                    'done': '✅ Task completed successfully',
                    'failed': '❌ Task failed'
                }
                message = status_messages.get(status, f'Status updated to: {status}')
                issue.create_comment(message)

            logger.info(f"Updated issue #{issue_number} status to '{status}'")
            return True

        except GithubException as e:
            logger.error(f"Error updating issue {issue_number} status: {e}")
            return False
