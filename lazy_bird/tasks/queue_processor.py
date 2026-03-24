"""Queue processor Celery task.

This module contains the queue processor task that:
- Polls the database for queued TaskRun records
- Triggers task execution for each queued task
- Handles concurrency limits and task prioritization
- Updates task status and logs errors

The queue processor runs periodically (every 60 seconds by default)
via Celery Beat scheduler.
"""

from datetime import datetime, timezone
from typing import List

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from lazy_bird.core.config import settings
from lazy_bird.core.database import get_async_db
from lazy_bird.core.logging import get_logger
from lazy_bird.models.task_run import TaskRun
from lazy_bird.tasks import app

logger = get_logger(__name__)


@app.task(
    name="lazy_bird.tasks.queue_processor.process_queue",
    bind=True,
    max_retries=3,
    default_retry_delay=30,
)
def process_queue(self):
    """Process queued tasks and trigger execution.

    This task runs periodically to:
    1. Query database for TaskRun records with status='queued'
    2. Check concurrency limits (MAX_PARALLEL_TASKS)
    3. Trigger execute_task for each queued task
    4. Update task status to 'running'
    5. Handle errors and log results

    Returns:
        dict: Processing summary with counts
            - queued_count: Number of tasks found in queue
            - triggered_count: Number of tasks triggered
            - skipped_count: Number of tasks skipped (concurrency limit)
            - errors: List of errors encountered

    Example:
        >>> result = process_queue()
        >>> print(result)
        {
            "queued_count": 5,
            "triggered_count": 3,
            "skipped_count": 2,
            "errors": []
        }
    """
    import asyncio

    # Run async function in sync context
    return asyncio.run(_process_queue_async())


async def _process_queue_async() -> dict:
    """Async implementation of queue processing with intelligent task selection.

    Enhancements (Issue #105):
    - Respects per-project max_concurrent_tasks limits
    - Enforces daily cost limits per project
    - Complexity-based prioritization (simple tasks first)
    """
    from decimal import Decimal
    from lazy_bird.tasks.task_executor import execute_task
    from lazy_bird.models.project import Project

    summary = {
        "queued_count": 0,
        "triggered_count": 0,
        "skipped_count": 0,
        "skipped_cost_limit": 0,
        "skipped_concurrency": 0,
        "errors": [],
    }

    # Get async database session
    async for db in get_async_db():
        try:
            # Query for queued tasks (ordered by complexity ASC, created_at ASC)
            # Simple tasks first for faster throughput
            stmt = (
                select(TaskRun)
                .where(TaskRun.status == "queued")
                .order_by(
                    TaskRun.complexity.asc(),  # simple < medium < complex
                    TaskRun.created_at.asc(),  # FIFO within same complexity
                )
                .limit(100)  # Process max 100 tasks per run
            )

            result = await db.execute(stmt)
            queued_tasks: List[TaskRun] = list(result.scalars().all())
            summary["queued_count"] = len(queued_tasks)

            logger.info(
                f"Queue processor: Found {len(queued_tasks)} queued tasks",
                extra={"extra_fields": {"queued_count": len(queued_tasks)}},
            )

            if not queued_tasks:
                logger.debug("Queue processor: No queued tasks found")
                return summary

            # Check global concurrency limit
            running_stmt = select(TaskRun).where(TaskRun.status == "running")
            running_result = await db.execute(running_stmt)
            global_running_count = len(list(running_result.scalars().all()))

            max_global_parallel = settings.MAX_PARALLEL_TASKS
            global_available = max_global_parallel - global_running_count

            logger.info(
                f"Queue processor: {global_running_count} tasks running globally, "
                f"{global_available} global slots available (max: {max_global_parallel})"
            )

            if global_available <= 0:
                logger.warning(
                    f"Queue processor: No global slots available (max: {max_global_parallel})"
                )
                summary["skipped_count"] = len(queued_tasks)
                summary["skipped_concurrency"] = len(queued_tasks)
                return summary

            # Track per-project state for intelligent selection
            project_running_counts = {}
            project_daily_costs = {}
            project_configs = {}

            # Iterate through queued tasks and apply selection logic
            for task in queued_tasks:
                # Check if we've reached global limit
                if summary["triggered_count"] >= global_available:
                    summary["skipped_count"] += 1
                    summary["skipped_concurrency"] += 1
                    continue

                try:
                    # Load project config if not cached
                    if task.project_id not in project_configs:
                        project_stmt = select(Project).where(Project.id == task.project_id)
                        project_result = await db.execute(project_stmt)
                        project = project_result.scalar_one_or_none()

                        if not project:
                            logger.warning(
                                f"Project {task.project_id} not found for task {task.id}"
                            )
                            summary["skipped_count"] += 1
                            continue

                        project_configs[task.project_id] = project

                    project = project_configs[task.project_id]

                    # 1. Check per-project concurrency limit
                    if task.project_id not in project_running_counts:
                        # Query running tasks for this project
                        project_running_stmt = (
                            select(TaskRun)
                            .where(TaskRun.project_id == task.project_id)
                            .where(TaskRun.status == "running")
                        )
                        project_running_result = await db.execute(project_running_stmt)
                        project_running_counts[task.project_id] = len(
                            list(project_running_result.scalars().all())
                        )

                    project_running = project_running_counts[task.project_id]
                    if project_running >= project.max_concurrent_tasks:
                        logger.info(
                            f"Skipping task {task.id}: project {task.project_id} "
                            f"at concurrency limit ({project_running}/{project.max_concurrent_tasks})"
                        )
                        summary["skipped_count"] += 1
                        summary["skipped_concurrency"] += 1
                        continue

                    # 2. Check daily cost limit
                    if task.project_id not in project_daily_costs:
                        # Query today's cost for this project
                        from sqlalchemy import func

                        today_start = datetime.now(timezone.utc).replace(
                            hour=0, minute=0, second=0, microsecond=0
                        )

                        cost_stmt = (
                            select(func.coalesce(func.sum(TaskRun.cost_usd), Decimal("0.00")))
                            .where(TaskRun.project_id == task.project_id)
                            .where(TaskRun.started_at >= today_start)
                        )
                        cost_result = await db.execute(cost_stmt)
                        project_daily_costs[task.project_id] = cost_result.scalar()

                    daily_cost = project_daily_costs[task.project_id]
                    if daily_cost >= project.daily_cost_limit_usd:
                        logger.warning(
                            f"Skipping task {task.id}: project {task.project_id} "
                            f"hit daily cost limit (${daily_cost}/${project.daily_cost_limit_usd})"
                        )
                        summary["skipped_count"] += 1
                        summary["skipped_cost_limit"] += 1
                        continue

                    # All checks passed - trigger task
                    execute_task.delay(str(task.id))

                    # Update status to 'running' immediately to prevent double-processing
                    task.status = "running"
                    task.started_at = datetime.now(timezone.utc)
                    await db.commit()

                    # Update counters
                    summary["triggered_count"] += 1
                    project_running_counts[task.project_id] = project_running + 1

                    logger.info(
                        f"Queue processor: Triggered task {task.id}",
                        extra={
                            "extra_fields": {
                                "task_run_id": str(task.id),
                                "project_id": str(task.project_id),
                                "complexity": task.complexity,
                                "daily_cost": float(daily_cost),
                                "cost_limit": float(project.daily_cost_limit_usd),
                            }
                        },
                    )

                except Exception as e:
                    error_msg = f"Failed to process task {task.id}: {str(e)}"
                    logger.error(
                        error_msg,
                        extra={
                            "extra_fields": {
                                "task_run_id": str(task.id),
                                "error": str(e),
                            }
                        },
                        exc_info=True,
                    )
                    summary["errors"].append(error_msg)

            logger.info(
                f"Queue processor: Summary - "
                f"triggered: {summary['triggered_count']}, "
                f"skipped: {summary['skipped_count']} "
                f"(cost_limit: {summary['skipped_cost_limit']}, "
                f"concurrency: {summary['skipped_concurrency']}), "
                f"errors: {len(summary['errors'])}"
            )

            return summary

        except Exception as e:
            logger.error(
                f"Queue processor error: {str(e)}",
                extra={"extra_fields": {"error": str(e)}},
                exc_info=True,
            )
            summary["errors"].append(str(e))
            return summary


@app.task(
    name="lazy_bird.tasks.queue_processor.requeue_stale_tasks",
    bind=True,
)
def requeue_stale_tasks(self):
    """Requeue tasks that have been 'running' for too long without updates.

    This task finds TaskRuns that have been in 'running' status for longer
    than TASK_TIMEOUT_SECONDS and requeues them for execution.

    This handles edge cases where:
    - Worker crashed mid-execution
    - Task was killed without updating status
    - Network issues prevented status update

    Returns:
        dict: Summary of requeued tasks
            - stale_count: Number of stale tasks found
            - requeued_count: Number of tasks requeued
            - errors: List of errors encountered
    """
    import asyncio

    return asyncio.run(_requeue_stale_tasks_async())


async def _requeue_stale_tasks_async() -> dict:
    """Async implementation of stale task requeuing."""
    summary = {
        "stale_count": 0,
        "requeued_count": 0,
        "errors": [],
    }

    # Get async database session
    async for db in get_async_db():
        try:
            # Calculate timeout threshold
            timeout_threshold = datetime.now(timezone.utc) - timedelta(
                seconds=settings.TASK_TIMEOUT_SECONDS
            )

            # Query for stale running tasks
            stmt = (
                select(TaskRun)
                .where(TaskRun.status == "running")
                .where(TaskRun.started_at < timeout_threshold)
                .limit(50)  # Limit to prevent overwhelming system
            )

            result = await db.execute(stmt)
            stale_tasks: List[TaskRun] = list(result.scalars().all())
            summary["stale_count"] = len(stale_tasks)

            if not stale_tasks:
                logger.debug("Stale task checker: No stale tasks found")
                return summary

            logger.warning(
                f"Stale task checker: Found {len(stale_tasks)} stale tasks",
                extra={"extra_fields": {"stale_count": len(stale_tasks)}},
            )

            # Requeue stale tasks
            for task in stale_tasks:
                try:
                    # Update status back to queued
                    task.status = "queued"
                    task.started_at = None
                    task.error = (
                        "Task timed out and was automatically requeued. "
                        f"Original start time: {task.started_at}"
                    )
                    await db.commit()

                    summary["requeued_count"] += 1

                    logger.warning(
                        f"Requeued stale task {task.id}",
                        extra={
                            "extra_fields": {
                                "task_run_id": str(task.id),
                                "started_at": (
                                    task.started_at.isoformat() if task.started_at else None
                                ),
                            }
                        },
                    )

                except Exception as e:
                    error_msg = f"Failed to requeue stale task {task.id}: {str(e)}"
                    logger.error(error_msg, exc_info=True)
                    summary["errors"].append(error_msg)

            logger.info(
                f"Stale task checker: Requeued {summary['requeued_count']} of {summary['stale_count']} stale tasks"
            )

            return summary

        except Exception as e:
            logger.error(f"Stale task checker error: {str(e)}", exc_info=True)
            summary["errors"].append(str(e))
            return summary


# Import timedelta for stale task requeuing
from datetime import timedelta
