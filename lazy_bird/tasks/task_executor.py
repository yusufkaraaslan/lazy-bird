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
from typing import Dict, Any
from uuid import UUID

from sqlalchemy import select

from lazy_bird.core.database import get_async_db
from lazy_bird.core.logging import get_logger
from lazy_bird.models.task_run import TaskRun
from lazy_bird.services.log_publisher import LogPublisher
from lazy_bird.tasks import app

logger = get_logger(__name__)


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
    Full implementation includes:
    - GitService integration for worktree management
    - ClaudeService integration for Claude Code CLI execution
    - TestRunner integration for test execution
    - PRService integration for pull request creation
    - LogPublisher integration for real-time logging
    - Webhook delivery for status updates
    """
    result = {
        "success": False,
        "status": "failed",
        "pr_url": None,
        "error": None,
    }

    # Create log publisher for this task
    log_publisher = LogPublisher(use_async=True)

    # Get database session
    async for db in get_async_db():
        try:
            # Load TaskRun
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

            await log_publisher.publish_log_async(
                message="Task status updated to 'running'",
                level="INFO",
                task_id=str(task_run.id),
                project_id=str(task_run.project_id),
            )

            # TODO: Step 1 - Create git worktree (GitService)
            await log_publisher.publish_log_async(
                message="Creating git worktree for isolated execution...",
                level="INFO",
                task_id=str(task_run.id),
                project_id=str(task_run.project_id),
            )
            # worktree_path, branch_name = git_service.create_worktree(...)

            # TODO: Step 2 - Run Claude Code CLI (ClaudeService)
            await log_publisher.publish_log_async(
                message="Running Claude Code CLI with task prompt...",
                level="INFO",
                task_id=str(task_run.id),
                project_id=str(task_run.project_id),
            )
            # claude_result = claude_service.execute_claude(...)

            # TODO: Step 3 - Execute tests (TestRunner)
            await log_publisher.publish_log_async(
                message="Executing tests...",
                level="INFO",
                task_id=str(task_run.id),
                project_id=str(task_run.project_id),
            )
            # test_result = test_runner.run_tests(...)

            # TODO: Step 4 - Create PR if tests pass (PRService)
            await log_publisher.publish_log_async(
                message="Creating pull request...",
                level="INFO",
                task_id=str(task_run.id),
                project_id=str(task_run.project_id),
            )
            # pr_result = pr_service.create_pull_request(...)

            # TODO: Step 5 - Cleanup worktree
            await log_publisher.publish_log_async(
                message="Cleaning up worktree...",
                level="INFO",
                task_id=str(task_run.id),
                project_id=str(task_run.project_id),
            )
            # git_service.cleanup_worktree(worktree_path)

            # Placeholder: Mark as completed (will be replaced with real logic)
            task_run.status = "completed"
            task_run.completed_at = datetime.now(timezone.utc)
            await db.commit()

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


__all__ = ["execute_task"]
