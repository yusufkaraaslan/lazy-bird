"""
GitLab Service
Handles GitLab API integration for issues
"""
import os
import logging
from gitlab import Gitlab, GitlabError
from typing import Optional, List, Dict, Any

logger = logging.getLogger(__name__)


class GitLabService:
    """Service for interacting with GitLab API"""

    def __init__(self, token: Optional[str] = None, url: str = 'https://gitlab.com'):
        """
        Initialize GitLab service

        Args:
            token: GitLab API token (reads from env if not provided)
            url: GitLab instance URL (defaults to gitlab.com)
        """
        self.token = token or os.environ.get('GITLAB_TOKEN') or self._load_token_from_file()
        self.url = url
        self.gitlab = Gitlab(self.url, private_token=self.token) if self.token else None

        if not self.gitlab:
            logger.warning("GitLab token not configured. GitLab API features will be limited.")

    def _load_token_from_file(self) -> Optional[str]:
        """Load GitLab token from secrets file"""
        token_path = os.path.expanduser('~/.config/lazy_birtd/secrets/gitlab_token')
        try:
            if os.path.exists(token_path):
                with open(token_path, 'r') as f:
                    return f.read().strip()
        except Exception as e:
            logger.error(f"Error loading GitLab token from file: {e}")
        return None

    def get_project(self, repo_url: str):
        """
        Get GitLab project object

        Args:
            repo_url: Repository URL (https://gitlab.com/user/project)

        Returns:
            Project object or None
        """
        if not self.gitlab:
            raise Exception("GitLab token not configured")

        try:
            # Extract project path from URL
            parts = repo_url.rstrip('/').split('/')
            # For gitlab.com/user/project, we need user/project
            project_path = '/'.join(parts[-2:])
            return self.gitlab.projects.get(project_path)
        except GitlabError as e:
            logger.error(f"Error getting project {repo_url}: {e}")
            raise

    def get_issue(self, repo_url: str, issue_number: int) -> Optional[Dict[str, Any]]:
        """
        Get issue details from GitLab

        Args:
            repo_url: Repository URL
            issue_number: Issue IID (issue number)

        Returns:
            Issue data dict or None
        """
        try:
            project = self.get_project(repo_url)
            issue = project.issues.get(issue_number)

            return {
                'number': issue.iid,
                'title': issue.title,
                'body': issue.description or '',
                'state': issue.state,
                'labels': issue.labels,
                'created_at': issue.created_at,
                'updated_at': issue.updated_at,
                'url': issue.web_url,
                'author': issue.author.get('username', 'unknown') if issue.author else 'unknown'
            }
        except GitlabError as e:
            logger.error(f"Error getting issue {issue_number} from {repo_url}: {e}")
            return None

    def list_issues(
        self,
        repo_url: str,
        state: str = 'opened',
        labels: Optional[List[str]] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        List issues from GitLab project

        Args:
            repo_url: Repository URL
            state: Issue state (opened, closed, all)
            labels: Filter by labels
            limit: Maximum number of issues to return

        Returns:
            List of issue dicts
        """
        try:
            project = self.get_project(repo_url)

            # Build query parameters
            params = {'state': state, 'per_page': limit}
            if labels:
                params['labels'] = ','.join(labels)

            issues = project.issues.list(**params)

            result = []
            for issue in issues:
                result.append({
                    'number': issue.iid,
                    'title': issue.title,
                    'state': issue.state,
                    'labels': issue.labels,
                    'created_at': issue.created_at,
                    'updated_at': issue.updated_at,
                    'url': issue.web_url
                })

            return result
        except GitlabError as e:
            logger.error(f"Error listing issues from {repo_url}: {e}")
            return []

    def add_label(self, repo_url: str, issue_number: int, label: str) -> bool:
        """
        Add label to issue

        Args:
            repo_url: Repository URL
            issue_number: Issue IID
            label: Label to add

        Returns:
            True if successful
        """
        try:
            project = self.get_project(repo_url)
            issue = project.issues.get(issue_number)

            # Add label if not already present
            labels = issue.labels.copy() if issue.labels else []
            if label not in labels:
                labels.append(label)
                issue.labels = labels
                issue.save()
                logger.info(f"Added label '{label}' to issue #{issue_number}")
            return True
        except GitlabError as e:
            logger.error(f"Error adding label to issue {issue_number}: {e}")
            return False

    def remove_label(self, repo_url: str, issue_number: int, label: str) -> bool:
        """
        Remove label from issue

        Args:
            repo_url: Repository URL
            issue_number: Issue IID
            label: Label to remove

        Returns:
            True if successful
        """
        try:
            project = self.get_project(repo_url)
            issue = project.issues.get(issue_number)

            # Remove label if present
            labels = issue.labels.copy() if issue.labels else []
            if label in labels:
                labels.remove(label)
                issue.labels = labels
                issue.save()
                logger.info(f"Removed label '{label}' from issue #{issue_number}")
            return True
        except GitlabError as e:
            logger.error(f"Error removing label from issue {issue_number}: {e}")
            return False

    def add_comment(self, repo_url: str, issue_number: int, comment: str) -> bool:
        """
        Add note/comment to issue

        Args:
            repo_url: Repository URL
            issue_number: Issue IID
            comment: Comment text

        Returns:
            True if successful
        """
        try:
            project = self.get_project(repo_url)
            issue = project.issues.get(issue_number)
            issue.notes.create({'body': comment})
            logger.info(f"Added comment to issue #{issue_number}")
            return True
        except GitlabError as e:
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
            issue_number: Issue IID
            status: New status (queued, processing, testing, done, failed)
            add_comment: Whether to add a comment about the status change

        Returns:
            True if successful
        """
        try:
            project = self.get_project(repo_url)
            issue = project.issues.get(issue_number)

            # Remove old status labels
            status_labels = ['queued', 'processing', 'testing', 'done', 'failed']
            labels = issue.labels.copy() if issue.labels else []
            labels = [l for l in labels if l not in status_labels]

            # Add new status label
            labels.append(status)
            issue.labels = labels
            issue.save()

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
                issue.notes.create({'body': message})

            logger.info(f"Updated issue #{issue_number} status to '{status}'")
            return True

        except GitlabError as e:
            logger.error(f"Error updating issue {issue_number} status: {e}")
            return False
