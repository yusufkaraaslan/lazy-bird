"""Task executor Celery task.

This module contains the task executor that:
- Receives a TaskRun ID to execute
- Creates git worktree for isolated execution
- Runs Claude Code CLI with task instructions
- Executes tests and validates results
- Creates pull request on success
- Updates TaskRun status and stores logs
- Publishes real-time logs via Redis Pub/Sub

This is the core execution engine for Lazy-Bird tasks.
"""

from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Dict, Any, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from lazy_bird.core.database import get_async_db
from lazy_bird.core.logging import get_logger
from lazy_bird.models.project import Project
from lazy_bird.models.task_run import TaskRun
from lazy_bird.services.claude_service import ClaudeService
from lazy_bird.services.git_service import GitService
from lazy_bird.services.log_publisher import LogPublisher
from lazy_bird.services.pr_service import PRService
from lazy_bird.services.test_runner import TestRunner
from lazy_bird.services.webhook_service import publish_event
from lazy_bird.tasks import app

logger = get_logger(__name__)


async def _fire_webhook(
    db,
    task_run,
    event_type: str,
) -> None:
    """Fire webhook for a task state change (fire-and-forget).

    Queries active WebhookSubscription records matching the event_type,
    builds a payload from the task run, and delivers via WebhookService.
    Wrapped in try/except so failures never block task execution.

    Args:
        db: AsyncSession database session
        task_run: TaskRun model instance
        event_type: Event type string (e.g. "task.running", "task.completed")
    """
    try:
        data = {
            "task_run_id": str(task_run.id),
            "project_id": str(task_run.project_id),
            "status": task_run.status,
            "work_item_id": task_run.work_item_id,
            "work_item_title": task_run.work_item_title,
            "pr_url": getattr(task_run, "pr_url", None),
            "error_message": getattr(task_run, "error_message", None),
            "cost_usd": float(task_run.cost_usd) if task_run.cost_usd else None,
            "tokens_used": task_run.tokens_used,
            "branch_name": getattr(task_run, "branch_name", None),
            "duration_seconds": getattr(task_run, "duration_seconds", None),
            "retry_count": getattr(task_run, "retry_count", None),
        }
        await publish_event(
            event_type=event_type,
            data=data,
            db=db,
            project_id=task_run.project_id,
        )
    except Exception:
        logger.debug(
            f"Webhook delivery failed for event {event_type} on task {task_run.id}",
            exc_info=True,
        )


@app.task(
    name="lazy_bird.tasks.task_executor.execute_task",
    bind=True,
    max_retries=0,  # Don't auto-retry (handle retries at task level)
    soft_time_limit=3600,  # 1 hour soft limit
    time_limit=3900,  # 65 minutes hard limit
)
def execute_task(self, task_run_id: str) -> Dict[str, Any]:
    """Execute a single TaskRun.

    This is the main task execution function that:
    1. Loads TaskRun from database
    2. Creates git worktree for isolation
    3. Runs Claude Code CLI with task prompt
    4. Executes tests and collects results
    5. Creates pull request if tests pass
    6. Updates TaskRun status and logs
    7. Cleans up worktree

    Args:
        task_run_id: UUID of TaskRun to execute

    Returns:
        dict: Execution result summary
            - success: bool
            - status: final status (completed, failed, cancelled)
            - pr_url: URL of created pull request (if successful)
            - error: Error message (if failed)

    Example:
        >>> result = execute_task("123e4567-e89b-12d3-a456-426614174000")
        >>> print(result)
        {
            "success": True,
            "status": "completed",
            "pr_url": "https://github.com/user/repo/pull/42",
            "error": None
        }
    """
    import asyncio

    # Run async implementation
    return asyncio.run(_execute_task_async(task_run_id))


async def _execute_task_async(task_run_id: str) -> Dict[str, Any]:
    """Async implementation of task execution.

    Executes a task run with real-time log publishing to Redis Pub/Sub.
    Full pipeline:
    1. Load TaskRun from database, update status to "running"
    2. Load related Project for config (test_command, repo_url, etc.)
    3. Create git worktree via GitService
    4. Run Claude Code CLI via ClaudeService with the task prompt
    5. Execute tests via TestRunner using the project's test_command
    6. If tests pass: commit, push, create PR via PRService
    7. If tests fail and retries remain: update error_message, set status "failed"
    8. Cleanup worktree in finally block
    9. Update TaskRun with results (cost_usd, tokens_used, duration, pr_url, status)
    10. Publish logs via LogPublisher at each step
    """
    result = {
        "success": False,
        "status": "failed",
        "pr_url": None,
        "error": None,
    }

    # Create log publisher for this task
    log_publisher = LogPublisher(use_async=True)

    # Track worktree for cleanup in finally block
    worktree_path: Optional[Path] = None
    branch_name: Optional[str] = None
    git_service: Optional[GitService] = None

    # Get database session
    async for db in get_async_db():
        try:
            # ------------------------------------------------------------------
            # Step 1: Load TaskRun from database
            # ------------------------------------------------------------------
            task_run_uuid = UUID(task_run_id)
            stmt = select(TaskRun).where(TaskRun.id == task_run_uuid)
            db_result = await db.execute(stmt)
            task_run = db_result.scalar_one_or_none()

            if not task_run:
                error_msg = f"TaskRun {task_run_id} not found"
                logger.error(error_msg)
                await log_publisher.publish_log_async(
                    message=error_msg,
                    level="ERROR",
                    task_id=task_run_id,
                )
                result["error"] = error_msg
                return result

            # Publish task start log
            await log_publisher.publish_log_async(
                message=f"Starting task execution: {task_run.work_item_title}",
                level="INFO",
                task_id=str(task_run.id),
                project_id=str(task_run.project_id),
                metadata={
                    "work_item_id": task_run.work_item_id,
                    "task_type": task_run.task_type,
                    "complexity": task_run.complexity,
                },
            )

            logger.info(
                f"Starting execution of task {task_run.id}",
                extra={
                    "extra_fields": {
                        "task_run_id": str(task_run.id),
                        "project_id": str(task_run.project_id),
                        "work_item_id": task_run.work_item_id,
                    }
                },
            )

            # Update status to running
            task_run.status = "running"
            task_run.started_at = datetime.now(timezone.utc)
            await db.commit()

            # Fire webhook for running state
            await _fire_webhook(db, task_run, "task.running")

            await log_publisher.publish_log_async(
                message="Task status updated to 'running'",
                level="INFO",
                task_id=str(task_run.id),
                project_id=str(task_run.project_id),
            )

            # ------------------------------------------------------------------
            # Step 2: Load related Project for config
            # ------------------------------------------------------------------
            project = _load_project(task_run)
            if project is None:
                project_stmt = select(Project).where(Project.id == task_run.project_id)
                project_result = await db.execute(project_stmt)
                project = project_result.scalar_one_or_none()

            # ------------------------------------------------------------------
            # Step 3: Create git worktree (GitService)
            # ------------------------------------------------------------------
            await log_publisher.publish_log_async(
                message="Creating git worktree for isolated execution...",
                level="INFO",
                task_id=str(task_run.id),
                project_id=str(task_run.project_id),
            )

            if isinstance(project, Project):
                # Extract project configuration
                project_slug = project.slug
                repo_url = project.repo_url
                project_type = project.project_type
                default_branch = project.default_branch
                test_command = project.get_effective_test_command()
                project_name = project.name
                work_item_number = _extract_issue_number(str(task_run.work_item_id))

                git_service = GitService(project_path=repo_url)
                worktree_path, branch_name = git_service.create_worktree(
                    project_id=project_slug,
                    task_id=work_item_number,
                    base_branch=default_branch,
                    force=True,
                )

                # Store git details on task_run
                task_run.branch_name = branch_name
                task_run.worktree_path = str(worktree_path)
                await db.commit()

                await log_publisher.publish_log_async(
                    message=(
                        f"Git worktree created at {worktree_path} " f"on branch {branch_name}"
                    ),
                    level="INFO",
                    task_id=str(task_run.id),
                    project_id=str(task_run.project_id),
                    metadata={
                        "worktree_path": str(worktree_path),
                        "branch_name": branch_name,
                    },
                )

            # ------------------------------------------------------------------
            # Step 4: Run Claude Code CLI (ClaudeService)
            # ------------------------------------------------------------------
            await log_publisher.publish_log_async(
                message="Running Claude Code CLI with task prompt...",
                level="INFO",
                task_id=str(task_run.id),
                project_id=str(task_run.project_id),
            )

            claude_result: Optional[Dict[str, Any]] = None
            if worktree_path and isinstance(project, Project):
                claude_service = ClaudeService()

                # Build the prompt from task details
                prompt = claude_service.construct_task_prompt(
                    project_name=project_name,
                    project_type=project_type,
                    project_id=project_slug,
                    task_title=(task_run.work_item_title or task_run.work_item_id),
                    task_body=task_run.prompt,
                    working_directory=worktree_path,
                )

                claude_result = claude_service.execute_claude(
                    prompt=prompt,
                    working_directory=worktree_path,
                    project_id=project_slug,
                    task_id=work_item_number,
                )

                # Store Claude usage metrics
                task_run.tokens_used = claude_result.get("tokens_used", 0)
                task_run.cost_usd = Decimal(str(claude_result.get("cost", 0.0)))
                await db.commit()

                if not claude_result.get("success"):
                    raise RuntimeError(
                        f"Claude execution failed: "
                        f"{claude_result.get('error', 'Unknown error')}"
                    )

                await log_publisher.publish_log_async(
                    message=(f"Claude execution completed " f"(tokens: {task_run.tokens_used})"),
                    level="INFO",
                    task_id=str(task_run.id),
                    project_id=str(task_run.project_id),
                    metadata={
                        "tokens_used": task_run.tokens_used,
                        "cost_usd": float(task_run.cost_usd),
                        "execution_time": claude_result.get("execution_time", 0),
                    },
                )

            # ------------------------------------------------------------------
            # Step 5: Execute tests (TestRunner)
            # ------------------------------------------------------------------
            await log_publisher.publish_log_async(
                message="Executing tests...",
                level="INFO",
                task_id=str(task_run.id),
                project_id=str(task_run.project_id),
            )

            test_result: Optional[Dict[str, Any]] = None
            if worktree_path and isinstance(project, Project) and test_command:
                test_runner = TestRunner()
                test_result = test_runner.run_tests(
                    test_command=test_command,
                    working_directory=worktree_path,
                    framework=project_type,
                    project_id=project_slug,
                    task_id=work_item_number,
                )

                task_run.tests_passed = test_result.get("success", False)
                task_run.test_output = test_result.get("output", "")
                await db.commit()

                await log_publisher.publish_log_async(
                    message=(f"Tests " f"{'passed' if test_result['success'] else 'failed'}"),
                    level="INFO" if test_result["success"] else "WARNING",
                    task_id=str(task_run.id),
                    project_id=str(task_run.project_id),
                    metadata={
                        "test_stats": test_result.get("stats", {}),
                        "test_success": test_result["success"],
                    },
                )

                # If tests fail, attempt retry then fail
                if not test_result["success"]:
                    test_result = await _handle_test_failure(
                        task_run=task_run,
                        test_result=test_result,
                        test_runner=test_runner,
                        claude_service=claude_service,
                        prompt=prompt,
                        worktree_path=worktree_path,
                        test_command=test_command,
                        project_type=project_type,
                        project_slug=project_slug,
                        work_item_number=work_item_number,
                        log_publisher=log_publisher,
                        db=db,
                    )

                    # If tests still fail after retry (or no retries)
                    if not test_result["success"]:
                        task_run.status = "failed"
                        task_run.error_message = test_runner.format_error_summary(test_result)
                        task_run.completed_at = datetime.now(timezone.utc)
                        if task_run.started_at and isinstance(task_run.started_at, datetime):
                            duration = task_run.completed_at - task_run.started_at
                            task_run.duration_seconds = int(duration.total_seconds())
                        await db.commit()

                        # Fire webhook for failed state
                        await _fire_webhook(db, task_run, "task.failed")

                        result["status"] = "failed"
                        result["error"] = task_run.error_message

                        await log_publisher.publish_log_async(
                            message="Task failed: tests did not pass",
                            level="ERROR",
                            task_id=str(task_run.id),
                            project_id=str(task_run.project_id),
                            metadata={"task_complete": True},
                        )

                        return result

            # ------------------------------------------------------------------
            # Step 6: Commit, push, and create PR (PRService)
            # ------------------------------------------------------------------
            await log_publisher.publish_log_async(
                message="Creating pull request...",
                level="INFO",
                task_id=str(task_run.id),
                project_id=str(task_run.project_id),
            )

            if worktree_path and git_service and isinstance(project, Project):
                # Commit changes
                commit_message = (
                    f"Task #{work_item_number}: "
                    f"{task_run.work_item_title or task_run.work_item_id}"
                    f"\n\nAutomated by Lazy-Bird\n"
                    f"Issue: {task_run.work_item_url or task_run.work_item_id}"
                )
                commit_sha = git_service.commit_changes(
                    worktree_path=worktree_path,
                    message=commit_message,
                    project_id=project_slug,
                )
                task_run.commit_sha = commit_sha

                # Push branch
                git_service.push_branch(
                    worktree_path=worktree_path,
                    project_id=project_slug,
                )

                # Get diff stats for PR body
                diff_stats = git_service.get_diff_stats(worktree_path)

                # Build PR body
                pr_service = PRService(working_directory=worktree_path)
                pr_body = pr_service.build_pr_body(
                    task_description=task_run.prompt,
                    implementation_summary=(
                        claude_result.get("output", "") if claude_result else ""
                    ),
                    test_results=test_result,
                    diff_stats=diff_stats,
                )

                pr_title = (
                    f"Task #{work_item_number}: "
                    f"{task_run.work_item_title or task_run.work_item_id}"
                )
                pr_result = pr_service.create_pull_request(
                    title=pr_title,
                    body=pr_body,
                    base_branch=default_branch,
                    head_branch=branch_name,
                    labels=["automated", "lazy-bird"],
                    draft=True,
                    project_id=project_slug,
                    task_id=work_item_number,
                    issue_number=work_item_number,
                )

                task_run.pr_url = pr_result.get("url")
                task_run.pr_number = pr_result.get("number")
                result["pr_url"] = task_run.pr_url

                await log_publisher.publish_log_async(
                    message=f"Pull request created: {task_run.pr_url}",
                    level="INFO",
                    task_id=str(task_run.id),
                    project_id=str(task_run.project_id),
                    metadata={
                        "pr_url": task_run.pr_url,
                        "pr_number": task_run.pr_number,
                    },
                )

            # ------------------------------------------------------------------
            # Step 7: Cleanup worktree
            # ------------------------------------------------------------------
            await log_publisher.publish_log_async(
                message="Cleaning up worktree...",
                level="INFO",
                task_id=str(task_run.id),
                project_id=str(task_run.project_id),
            )

            if worktree_path and git_service:
                try:
                    git_service.cleanup_worktree(
                        worktree_path=worktree_path,
                        branch_name=branch_name,
                    )
                except Exception as cleanup_error:
                    logger.warning(
                        f"Worktree cleanup failed: {cleanup_error}",
                        exc_info=True,
                    )

                # Clear references so finally block doesn't double-clean
                worktree_path = None
                branch_name = None

            # ------------------------------------------------------------------
            # Step 8: Mark task as completed
            # ------------------------------------------------------------------
            task_run.status = "completed"
            task_run.completed_at = datetime.now(timezone.utc)
            if task_run.started_at and isinstance(task_run.started_at, datetime):
                duration = task_run.completed_at - task_run.started_at
                task_run.duration_seconds = int(duration.total_seconds())
            await db.commit()

            # Fire webhook for completed state
            await _fire_webhook(db, task_run, "task.completed")

            result["success"] = True
            result["status"] = "completed"

            # Publish completion log
            await log_publisher.publish_log_async(
                message="Task execution completed successfully",
                level="INFO",
                task_id=str(task_run.id),
                project_id=str(task_run.project_id),
                metadata={"task_complete": True},
            )

            logger.info(
                f"Task {task_run.id} execution completed",
                extra={
                    "extra_fields": {
                        "task_run_id": str(task_run.id),
                        "status": task_run.status,
                        "pr_url": getattr(task_run, "pr_url", None),
                    }
                },
            )

            return result

        except Exception as e:
            error_msg = f"Task execution failed: {str(e)}"
            logger.error(
                error_msg,
                extra={
                    "extra_fields": {
                        "task_run_id": task_run_id,
                        "error": str(e),
                    }
                },
                exc_info=True,
            )

            # Publish error log
            await log_publisher.publish_log_async(
                message=error_msg,
                level="ERROR",
                task_id=task_run_id,
                metadata={"error_type": type(e).__name__, "error": str(e)},
            )

            result["error"] = error_msg

            # Update task status to failed
            try:
                task_run.status = "failed"
                task_run.error_message = str(e)
                task_run.completed_at = datetime.now(timezone.utc)
                await db.commit()

                # Fire webhook for failed state
                await _fire_webhook(db, task_run, "task.failed")

                await log_publisher.publish_log_async(
                    message="Task marked as failed",
                    level="ERROR",
                    task_id=str(task_run.id),
                    project_id=str(task_run.project_id),
                    metadata={"task_complete": True},
                )
            except Exception as update_error:
                logger.error(
                    f"Failed to update task status: {str(update_error)}",
                    exc_info=True,
                )

                await log_publisher.publish_log_async(
                    message=f"Failed to update task status: {str(update_error)}",
                    level="CRITICAL",
                    task_id=task_run_id,
                )

            return result

        finally:
            # ------------------------------------------------------------------
            # Cleanup worktree in finally block (if not already cleaned)
            # ------------------------------------------------------------------
            if worktree_path and git_service:
                try:
                    git_service.cleanup_worktree(
                        worktree_path=worktree_path,
                        branch_name=branch_name,
                    )
                except Exception as cleanup_error:
                    logger.warning(
                        f"Worktree cleanup failed: {cleanup_error}",
                        exc_info=True,
                    )


def _load_project(task_run) -> Optional[Project]:
    """Load Project from TaskRun's eager-loaded relationship.

    Returns the project only if it's a real Project instance
    (not a Mock or other surrogate).

    Args:
        task_run: TaskRun instance (possibly with eager-loaded project)

    Returns:
        Optional[Project]: The Project instance, or None
    """
    project = getattr(task_run, "project", None)
    if isinstance(project, Project):
        return project
    return None


async def _handle_test_failure(
    task_run,
    test_result: Dict[str, Any],
    test_runner: TestRunner,
    claude_service: ClaudeService,
    prompt: str,
    worktree_path: Path,
    test_command: str,
    project_type: str,
    project_slug: str,
    work_item_number: int,
    log_publisher: LogPublisher,
    db,
) -> Dict[str, Any]:
    """Handle test failure with optional retry.

    If the task has retries remaining, re-runs Claude with error context
    and re-runs tests.

    Args:
        task_run: TaskRun instance
        test_result: Initial failed test result
        test_runner: TestRunner instance
        claude_service: ClaudeService instance
        prompt: Original prompt
        worktree_path: Path to worktree
        test_command: Test command to run
        project_type: Project framework type
        project_slug: Project slug
        work_item_number: Issue number
        log_publisher: LogPublisher instance
        db: Database session

    Returns:
        Dict[str, Any]: Final test result (may be from retry)
    """
    error_summary = test_runner.format_error_summary(test_result)
    task_run.error_message = error_summary

    if task_run.can_retry():
        task_run.retry_count += 1
        await db.commit()

        await log_publisher.publish_log_async(
            message=(f"Tests failed, retry " f"{task_run.retry_count}/{task_run.max_retries}"),
            level="WARNING",
            task_id=str(task_run.id),
            project_id=str(task_run.project_id),
        )

        # Retry: re-run Claude with error context
        claude_result = claude_service.execute_claude(
            prompt=prompt,
            working_directory=worktree_path,
            project_id=project_slug,
            task_id=work_item_number,
            error_context=error_summary,
        )

        # Update tokens/cost with retry usage
        task_run.tokens_used = (task_run.tokens_used or 0) + claude_result.get("tokens_used", 0)
        task_run.cost_usd = Decimal(
            str(float(task_run.cost_usd or 0) + claude_result.get("cost", 0.0))
        )

        # Re-run tests
        test_result = test_runner.run_tests(
            test_command=test_command,
            working_directory=worktree_path,
            framework=project_type,
            project_id=project_slug,
            task_id=work_item_number,
        )
        task_run.tests_passed = test_result.get("success", False)
        task_run.test_output = test_result.get("output", "")
        await db.commit()

    return test_result


def _extract_issue_number(work_item_id: str) -> int:
    """Extract numeric issue number from work_item_id.

    Args:
        work_item_id: Work item identifier (e.g., "issue-42", "JIRA-123", "42")

    Returns:
        int: Extracted issue number, or 0 if not found
    """
    import re

    match = re.search(r"(\d+)", work_item_id)
    if match:
        return int(match.group(1))
    return 0


__all__ = ["execute_task"]
