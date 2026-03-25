"""Issue watcher Celery task.

This module contains the issue watcher task that:
- Polls GitHub/GitLab APIs for issues labeled 'ready'
- Creates TaskRun records for new issues
- Updates issue labels (removes 'ready', adds 'processing')
- Runs periodically via Celery Beat scheduler (every 60 seconds)
"""

import re
import uuid
from typing import Any, Dict, List, Optional, Tuple

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from lazy_bird.core.config import settings
from lazy_bird.core.database import get_async_db
from lazy_bird.core.logging import get_logger
from lazy_bird.models.project import Project
from lazy_bird.models.task_run import TaskRun
from lazy_bird.tasks import app

logger = get_logger(__name__)


def _parse_github_repo(repo_url: str) -> Optional[Tuple[str, str]]:
    """Parse owner and repo from a GitHub repository URL.

    Supports formats:
    - https://github.com/owner/repo
    - https://github.com/owner/repo.git
    - git@github.com:owner/repo.git

    Args:
        repo_url: Git repository URL

    Returns:
        Tuple of (owner, repo) or None if not parseable
    """
    # HTTPS format
    match = re.match(r"https?://github\.com/([^/]+)/([^/.]+)(?:\.git)?", repo_url)
    if match:
        return match.group(1), match.group(2)

    # SSH format
    match = re.match(r"git@github\.com:([^/]+)/([^/.]+)(?:\.git)?", repo_url)
    if match:
        return match.group(1), match.group(2)

    return None


def _parse_gitlab_repo(repo_url: str) -> Optional[str]:
    """Parse project path from a GitLab repository URL.

    Supports formats:
    - https://gitlab.com/owner/repo
    - https://gitlab.com/group/subgroup/repo
    - https://gitlab.com/owner/repo.git

    Args:
        repo_url: Git repository URL

    Returns:
        URL-encoded project path or None if not parseable
    """
    match = re.match(r"https?://[^/]+/(.+?)(?:\.git)?$", repo_url)
    if match:
        return match.group(1).replace("/", "%2F")
    return None


def _detect_platform(project: Project) -> Optional[str]:
    """Detect the source platform for a project.

    Uses source_platform field first, then falls back to repo_url inspection.

    Args:
        project: Project model instance

    Returns:
        Platform string ('github' or 'gitlab') or None
    """
    if project.source_platform:
        return project.source_platform.lower()

    if project.repo_url:
        if "github.com" in project.repo_url:
            return "github"
        if "gitlab" in project.repo_url:
            return "gitlab"

    return None


async def _fetch_github_issues(
    client: httpx.AsyncClient,
    owner: str,
    repo: str,
    token: str,
) -> List[Dict[str, Any]]:
    """Fetch open issues with 'ready' label from GitHub.

    Args:
        client: httpx async client
        owner: Repository owner
        repo: Repository name
        token: GitHub API token

    Returns:
        List of issue dicts from GitHub API
    """
    url = f"https://api.github.com/repos/{owner}/{repo}/issues"
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json",
    }
    params = {
        "labels": "ready",
        "state": "open",
    }

    response = await client.get(url, headers=headers, params=params)
    response.raise_for_status()
    return response.json()


async def _update_github_labels(
    client: httpx.AsyncClient,
    owner: str,
    repo: str,
    issue_number: int,
    token: str,
) -> None:
    """Remove 'ready' label and add 'processing' label on a GitHub issue.

    Args:
        client: httpx async client
        owner: Repository owner
        repo: Repository name
        issue_number: Issue number
        token: GitHub API token
    """
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json",
    }

    # Remove 'ready' label
    remove_url = f"https://api.github.com/repos/{owner}/{repo}/issues/{issue_number}/labels/ready"
    try:
        await client.delete(remove_url, headers=headers)
    except httpx.HTTPStatusError:
        logger.warning(f"Failed to remove 'ready' label from {owner}/{repo}#{issue_number}")

    # Add 'processing' label
    add_url = f"https://api.github.com/repos/{owner}/{repo}/issues/{issue_number}/labels"
    try:
        await client.post(add_url, headers=headers, json={"labels": ["processing"]})
    except httpx.HTTPStatusError:
        logger.warning(f"Failed to add 'processing' label to {owner}/{repo}#{issue_number}")


async def _fetch_gitlab_issues(
    client: httpx.AsyncClient,
    project_path: str,
    token: str,
) -> List[Dict[str, Any]]:
    """Fetch open issues with 'ready' label from GitLab.

    Args:
        client: httpx async client
        project_path: URL-encoded project path
        token: GitLab API token

    Returns:
        List of issue dicts from GitLab API
    """
    url = f"https://gitlab.com/api/v4/projects/{project_path}/issues"
    headers = {
        "PRIVATE-TOKEN": token,
    }
    params = {
        "labels": "ready",
        "state": "opened",
    }

    response = await client.get(url, headers=headers, params=params)
    response.raise_for_status()
    return response.json()


async def _update_gitlab_labels(
    client: httpx.AsyncClient,
    project_path: str,
    issue_iid: int,
    token: str,
) -> None:
    """Remove 'ready' label and add 'processing' label on a GitLab issue.

    Args:
        client: httpx async client
        project_path: URL-encoded project path
        issue_iid: Issue IID (internal ID)
        token: GitLab API token
    """
    url = f"https://gitlab.com/api/v4/projects/{project_path}/issues/{issue_iid}"
    headers = {
        "PRIVATE-TOKEN": token,
    }
    try:
        await client.put(
            url,
            headers=headers,
            json={
                "remove_labels": "ready",
                "add_labels": "processing",
            },
        )
    except httpx.HTTPStatusError:
        logger.warning(f"Failed to update labels on GitLab issue {project_path}#{issue_iid}")


@app.task(
    name="lazy_bird.tasks.issue_watcher.watch_issues",
    bind=True,
    max_retries=3,
    default_retry_delay=30,
)
def watch_issues(self):
    """Watch for new issues with 'ready' label and create TaskRuns.

    This task runs periodically to:
    1. Query all active projects with automation_enabled=True
    2. For each project, fetch issues labeled 'ready' from GitHub/GitLab
    3. Check if a TaskRun already exists for each issue
    4. Create new TaskRun records for unprocessed issues
    5. Update issue labels (remove 'ready', add 'processing')

    Returns:
        dict: Processing summary with counts
    """
    import asyncio

    return asyncio.run(_watch_issues_async())


async def _watch_issues_async() -> dict:
    """Async implementation of issue watching."""
    summary = {
        "projects_checked": 0,
        "issues_found": 0,
        "task_runs_created": 0,
        "issues_skipped": 0,
        "errors": [],
    }

    async for db in get_async_db():
        try:
            # Query active projects with automation enabled
            stmt = (
                select(Project)
                .where(Project.automation_enabled.is_(True))
                .where(Project.deleted_at.is_(None))
            )
            result = await db.execute(stmt)
            projects: List[Project] = list(result.scalars().all())

            logger.info(
                f"Issue watcher: Found {len(projects)} active projects",
                extra={"extra_fields": {"project_count": len(projects)}},
            )

            if not projects:
                logger.debug("Issue watcher: No active projects found")
                return summary

            async with httpx.AsyncClient(timeout=30.0) as client:
                for project in projects:
                    try:
                        await _process_project_issues(client, db, project, summary)
                        summary["projects_checked"] += 1
                    except Exception as e:
                        error_msg = (
                            f"Failed to process issues for project "
                            f"{project.id} ({project.name}): {str(e)}"
                        )
                        logger.error(
                            error_msg,
                            extra={
                                "extra_fields": {
                                    "project_id": str(project.id),
                                    "error": str(e),
                                }
                            },
                            exc_info=True,
                        )
                        summary["errors"].append(error_msg)

            logger.info(
                f"Issue watcher: Summary - "
                f"projects: {summary['projects_checked']}, "
                f"issues found: {summary['issues_found']}, "
                f"created: {summary['task_runs_created']}, "
                f"skipped: {summary['issues_skipped']}, "
                f"errors: {len(summary['errors'])}"
            )

            return summary

        except Exception as e:
            logger.error(
                f"Issue watcher error: {str(e)}",
                extra={"extra_fields": {"error": str(e)}},
                exc_info=True,
            )
            summary["errors"].append(str(e))
            return summary


async def _process_project_issues(
    client: httpx.AsyncClient,
    db: AsyncSession,
    project: Project,
    summary: dict,
) -> None:
    """Process issues for a single project.

    Args:
        client: httpx async client
        db: Async database session
        project: Project to check for issues
        summary: Summary dict to update counts
    """
    platform = _detect_platform(project)

    if platform == "github":
        token = settings.GITHUB_TOKEN
        if not token:
            logger.warning(f"No GITHUB_TOKEN configured, skipping project {project.name}")
            return

        parsed = _parse_github_repo(project.repo_url)
        if not parsed:
            logger.warning(f"Could not parse GitHub repo from URL: {project.repo_url}")
            return

        owner, repo = parsed
        issues = await _fetch_github_issues(client, owner, repo, token)

        for issue in issues:
            summary["issues_found"] += 1
            issue_number = issue["number"]
            work_item_id = str(issue_number)

            # Check if TaskRun already exists for this issue
            existing_stmt = (
                select(TaskRun)
                .where(TaskRun.project_id == project.id)
                .where(TaskRun.work_item_id == work_item_id)
            )
            existing_result = await db.execute(existing_stmt)
            existing = existing_result.scalar_one_or_none()

            if existing:
                summary["issues_skipped"] += 1
                logger.debug(f"Issue #{issue_number} already has TaskRun, skipping")
                continue

            # Create new TaskRun
            task_run = TaskRun(
                id=uuid.uuid4(),
                project_id=project.id,
                work_item_id=work_item_id,
                work_item_url=issue.get("html_url"),
                work_item_title=issue.get("title"),
                work_item_description=issue.get("body"),
                prompt=issue.get("body") or issue.get("title", ""),
                status="queued",
                task_type="feature",
            )
            db.add(task_run)
            await db.commit()

            # Update issue labels
            await _update_github_labels(client, owner, repo, issue_number, token)

            summary["task_runs_created"] += 1
            logger.info(
                f"Created TaskRun for GitHub issue #{issue_number} " f"in project {project.name}",
                extra={
                    "extra_fields": {
                        "project_id": str(project.id),
                        "issue_number": issue_number,
                        "task_run_id": str(task_run.id),
                    }
                },
            )

    elif platform == "gitlab":
        token = settings.GITLAB_TOKEN
        if not token:
            logger.warning(f"No GITLAB_TOKEN configured, skipping project {project.name}")
            return

        project_path = _parse_gitlab_repo(project.repo_url)
        if not project_path:
            logger.warning(f"Could not parse GitLab project from URL: {project.repo_url}")
            return

        issues = await _fetch_gitlab_issues(client, project_path, token)

        for issue in issues:
            summary["issues_found"] += 1
            issue_iid = issue["iid"]
            work_item_id = str(issue_iid)

            # Check if TaskRun already exists
            existing_stmt = (
                select(TaskRun)
                .where(TaskRun.project_id == project.id)
                .where(TaskRun.work_item_id == work_item_id)
            )
            existing_result = await db.execute(existing_stmt)
            existing = existing_result.scalar_one_or_none()

            if existing:
                summary["issues_skipped"] += 1
                logger.debug(f"GitLab issue !{issue_iid} already has TaskRun, skipping")
                continue

            # Create new TaskRun
            task_run = TaskRun(
                id=uuid.uuid4(),
                project_id=project.id,
                work_item_id=work_item_id,
                work_item_url=issue.get("web_url"),
                work_item_title=issue.get("title"),
                work_item_description=issue.get("description"),
                prompt=issue.get("description") or issue.get("title", ""),
                status="queued",
                task_type="feature",
            )
            db.add(task_run)
            await db.commit()

            # Update issue labels
            await _update_gitlab_labels(client, project_path, issue_iid, token)

            summary["task_runs_created"] += 1
            logger.info(
                f"Created TaskRun for GitLab issue !{issue_iid} " f"in project {project.name}",
                extra={
                    "extra_fields": {
                        "project_id": str(project.id),
                        "issue_iid": issue_iid,
                        "task_run_id": str(task_run.id),
                    }
                },
            )

    else:
        logger.warning(
            f"Unknown platform for project {project.name} "
            f"(source_platform={project.source_platform}, "
            f"repo_url={project.repo_url})"
        )
