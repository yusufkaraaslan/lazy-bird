"""Tests for intelligent task selection logic (Issue #105).

Tests for queue_processor.py enhancements:
- Per-project concurrency limits
- Daily cost limit enforcement
- Complexity-based prioritization
"""

import uuid
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestPerProjectConcurrency:
    """Test per-project concurrency limit enforcement."""

    @pytest.mark.asyncio
    async def test_respects_project_max_concurrent_tasks(self):
        """Should skip tasks when project is at concurrency limit."""
        from lazy_bird.tasks.queue_processor import _process_queue_async
        from lazy_bird.models.project import Project
        from lazy_bird.models.task_run import TaskRun

        # Mock database
        mock_db = AsyncMock()

        # Create mock project with max_concurrent_tasks=2
        project_id = uuid.uuid4()
        mock_project = MagicMock(spec=Project)
        mock_project.id = project_id
        mock_project.max_concurrent_tasks = 2
        mock_project.daily_cost_limit_usd = Decimal("50.00")

        # Create 3 queued tasks for this project
        queued_tasks = [
            MagicMock(
                id=uuid.uuid4(),
                project_id=project_id,
                status="queued",
                complexity="simple",
                created_at=datetime.now(timezone.utc),
            )
            for _ in range(3)
        ]

        # 2 tasks already running for this project
        running_tasks = [
            MagicMock(id=uuid.uuid4(), project_id=project_id, status="running")
            for _ in range(2)
        ]

        # Mock database queries
        async def mock_execute(stmt):
            stmt_str = str(stmt)
            result = AsyncMock()

            if 'status = "queued"' in stmt_str or "status = 'queued'" in stmt_str:
                # Return queued tasks
                result.scalars = MagicMock(
                    return_value=MagicMock(all=MagicMock(return_value=queued_tasks))
                )
            elif "status = 'running'" in stmt_str and "project_id" in stmt_str:
                # Return project's running tasks
                result.scalars = MagicMock(
                    return_value=MagicMock(all=MagicMock(return_value=running_tasks))
                )
            elif "status = 'running'" in stmt_str:
                # Global running count
                result.scalars = MagicMock(
                    return_value=MagicMock(all=MagicMock(return_value=running_tasks))
                )
            elif "projects.id" in stmt_str:
                # Return project
                result.scalar_one_or_none = MagicMock(return_value=mock_project)
            elif "coalesce" in stmt_str.lower():
                # Daily cost query
                result.scalar = MagicMock(return_value=Decimal("10.00"))
            else:
                result.scalars = MagicMock(
                    return_value=MagicMock(all=MagicMock(return_value=[]))
                )

            return result

        mock_db.execute = mock_execute
        mock_db.commit = AsyncMock()

        # Mock get_async_db to yield our mock
        async def mock_get_db():
            yield mock_db

        with patch("lazy_bird.tasks.queue_processor.get_async_db", mock_get_db):
            with patch(
                "lazy_bird.tasks.task_executor.execute_task"
            ) as mock_execute_task:
                result = await _process_queue_async()

                # Should skip all tasks due to concurrency limit (2/2 running)
                assert result["skipped_concurrency"] == 3
                assert result["triggered_count"] == 0
                assert mock_execute_task.delay.call_count == 0

    @pytest.mark.asyncio
    async def test_triggers_tasks_when_project_has_available_slots(self):
        """Should trigger tasks when project has available concurrency slots."""
        from lazy_bird.tasks.queue_processor import _process_queue_async
        from lazy_bird.models.project import Project
        from lazy_bird.models.task_run import TaskRun

        # Mock database
        mock_db = AsyncMock()

        # Create mock project with max_concurrent_tasks=3
        project_id = uuid.uuid4()
        mock_project = MagicMock(spec=Project)
        mock_project.id = project_id
        mock_project.max_concurrent_tasks = 3
        mock_project.daily_cost_limit_usd = Decimal("50.00")

        # Create 2 queued tasks
        queued_tasks = [
            MagicMock(
                id=uuid.uuid4(),
                project_id=project_id,
                status="queued",
                complexity="simple",
                created_at=datetime.now(timezone.utc),
            )
            for _ in range(2)
        ]

        # 1 task running (so 2 slots available)
        running_tasks = [
            MagicMock(id=uuid.uuid4(), project_id=project_id, status="running")
        ]

        # Mock database queries
        async def mock_execute(stmt):
            stmt_str = str(stmt)
            result = AsyncMock()

            if 'status = "queued"' in stmt_str or "status = 'queued'" in stmt_str:
                result.scalars = MagicMock(
                    return_value=MagicMock(all=MagicMock(return_value=queued_tasks))
                )
            elif "status = 'running'" in stmt_str and "project_id" in stmt_str:
                result.scalars = MagicMock(
                    return_value=MagicMock(all=MagicMock(return_value=running_tasks))
                )
            elif "status = 'running'" in stmt_str:
                result.scalars = MagicMock(
                    return_value=MagicMock(all=MagicMock(return_value=running_tasks))
                )
            elif "projects.id" in stmt_str:
                result.scalar_one_or_none = MagicMock(return_value=mock_project)
            elif "coalesce" in stmt_str.lower():
                result.scalar = MagicMock(return_value=Decimal("10.00"))
            else:
                result.scalars = MagicMock(
                    return_value=MagicMock(all=MagicMock(return_value=[]))
                )

            return result

        mock_db.execute = mock_execute
        mock_db.commit = AsyncMock()

        async def mock_get_db():
            yield mock_db

        with patch("lazy_bird.tasks.queue_processor.get_async_db", mock_get_db):
            with patch(
                "lazy_bird.tasks.task_executor.execute_task"
            ) as mock_execute_task:
                result = await _process_queue_async()

                # Should trigger both tasks (2 slots available)
                assert result["triggered_count"] == 2
                assert mock_execute_task.delay.call_count == 2


class TestDailyCostLimits:
    """Test daily cost limit enforcement."""

    @pytest.mark.asyncio
    async def test_skips_tasks_when_daily_cost_limit_reached(self):
        """Should skip tasks when project has reached daily cost limit."""
        from lazy_bird.tasks.queue_processor import _process_queue_async
        from lazy_bird.models.project import Project

        # Mock database
        mock_db = AsyncMock()

        # Create mock project with $50 daily limit
        project_id = uuid.uuid4()
        mock_project = MagicMock(spec=Project)
        mock_project.id = project_id
        mock_project.max_concurrent_tasks = 3
        mock_project.daily_cost_limit_usd = Decimal("50.00")

        # Create queued task
        queued_task = MagicMock(
            id=uuid.uuid4(),
            project_id=project_id,
            status="queued",
            complexity="simple",
            priority=1,
            created_at=datetime.now(timezone.utc),
        )

        # Mock database queries
        async def mock_execute(stmt):
            stmt_str = str(stmt)
            result = AsyncMock()

            if 'status = "queued"' in stmt_str or "status = 'queued'" in stmt_str:
                result.scalars = MagicMock(
                    return_value=MagicMock(all=MagicMock(return_value=[queued_task]))
                )
            elif "status = 'running'" in stmt_str:
                result.scalars = MagicMock(
                    return_value=MagicMock(all=MagicMock(return_value=[]))
                )
            elif "projects.id" in stmt_str:
                result.scalar_one_or_none = MagicMock(return_value=mock_project)
            elif "coalesce" in stmt_str.lower():
                # Daily cost is $50.00 (at limit)
                result.scalar = MagicMock(return_value=Decimal("50.00"))
            else:
                result.scalars = MagicMock(
                    return_value=MagicMock(all=MagicMock(return_value=[]))
                )

            return result

        mock_db.execute = mock_execute
        mock_db.commit = AsyncMock()

        async def mock_get_db():
            yield mock_db

        with patch("lazy_bird.tasks.queue_processor.get_async_db", mock_get_db):
            with patch(
                "lazy_bird.tasks.task_executor.execute_task"
            ) as mock_execute_task:
                result = await _process_queue_async()

                # Should skip task due to cost limit
                assert result["skipped_cost_limit"] == 1
                assert result["triggered_count"] == 0
                assert mock_execute_task.delay.call_count == 0

    @pytest.mark.asyncio
    async def test_triggers_tasks_when_daily_cost_below_limit(self):
        """Should trigger tasks when daily cost is below limit."""
        from lazy_bird.tasks.queue_processor import _process_queue_async
        from lazy_bird.models.project import Project

        # Mock database
        mock_db = AsyncMock()

        # Create mock project with $50 daily limit
        project_id = uuid.uuid4()
        mock_project = MagicMock(spec=Project)
        mock_project.id = project_id
        mock_project.max_concurrent_tasks = 3
        mock_project.daily_cost_limit_usd = Decimal("50.00")

        # Create queued task
        queued_task = MagicMock(
            id=uuid.uuid4(),
            project_id=project_id,
            status="queued",
            complexity="simple",
            priority=1,
            created_at=datetime.now(timezone.utc),
        )

        # Mock database queries
        async def mock_execute(stmt):
            stmt_str = str(stmt)
            result = AsyncMock()

            if 'status = "queued"' in stmt_str or "status = 'queued'" in stmt_str:
                result.scalars = MagicMock(
                    return_value=MagicMock(all=MagicMock(return_value=[queued_task]))
                )
            elif "status = 'running'" in stmt_str:
                result.scalars = MagicMock(
                    return_value=MagicMock(all=MagicMock(return_value=[]))
                )
            elif "projects.id" in stmt_str:
                result.scalar_one_or_none = MagicMock(return_value=mock_project)
            elif "coalesce" in stmt_str.lower():
                # Daily cost is $25.00 (below limit)
                result.scalar = MagicMock(return_value=Decimal("25.00"))
            else:
                result.scalars = MagicMock(
                    return_value=MagicMock(all=MagicMock(return_value=[]))
                )

            return result

        mock_db.execute = mock_execute
        mock_db.commit = AsyncMock()

        async def mock_get_db():
            yield mock_db

        with patch("lazy_bird.tasks.queue_processor.get_async_db", mock_get_db):
            with patch(
                "lazy_bird.tasks.task_executor.execute_task"
            ) as mock_execute_task:
                result = await _process_queue_async()

                # Should trigger task (cost below limit)
                assert result["triggered_count"] == 1
                assert result["skipped_cost_limit"] == 0
                assert mock_execute_task.delay.call_count == 1


class TestComplexityPrioritization:
    """Test complexity-based task prioritization."""

    @pytest.mark.asyncio
    async def test_simple_tasks_prioritized_over_complex(self):
        """Should prioritize simple tasks over complex ones."""
        from lazy_bird.tasks.queue_processor import _process_queue_async
        from lazy_bird.models.project import Project

        # Mock database
        mock_db = AsyncMock()

        project_id = uuid.uuid4()
        mock_project = MagicMock(spec=Project)
        mock_project.id = project_id
        mock_project.max_concurrent_tasks = 10
        mock_project.daily_cost_limit_usd = Decimal("100.00")

        # Create tasks with different complexities (will be sorted by query)
        # In real implementation, database sorts them
        simple_task = MagicMock(
            id=uuid.uuid4(),
            project_id=project_id,
            status="queued",
            complexity="simple",
            created_at=datetime.now(timezone.utc),
        )
        complex_task = MagicMock(
            id=uuid.uuid4(),
            project_id=project_id,
            status="queued",
            complexity="complex",
            created_at=datetime.now(timezone.utc),
        )

        # Tasks returned in correct order (simple first)
        queued_tasks = [simple_task, complex_task]

        triggered_tasks = []

        # Mock database queries
        async def mock_execute(stmt):
            stmt_str = str(stmt)
            result = AsyncMock()

            if 'status = "queued"' in stmt_str or "status = 'queued'" in stmt_str:
                result.scalars = MagicMock(
                    return_value=MagicMock(all=MagicMock(return_value=queued_tasks))
                )
            elif "status = 'running'" in stmt_str:
                result.scalars = MagicMock(
                    return_value=MagicMock(all=MagicMock(return_value=[]))
                )
            elif "projects.id" in stmt_str:
                result.scalar_one_or_none = MagicMock(return_value=mock_project)
            elif "coalesce" in stmt_str.lower():
                result.scalar = MagicMock(return_value=Decimal("10.00"))
            else:
                result.scalars = MagicMock(
                    return_value=MagicMock(all=MagicMock(return_value=[]))
                )

            return result

        mock_db.execute = mock_execute
        mock_db.commit = AsyncMock()

        async def mock_get_db():
            yield mock_db

        def track_task(task_id):
            triggered_tasks.append(task_id)

        with patch("lazy_bird.tasks.queue_processor.get_async_db", mock_get_db):
            with patch(
                "lazy_bird.tasks.task_executor.execute_task"
            ) as mock_execute_task:
                mock_execute_task.delay.side_effect = track_task

                result = await _process_queue_async()

                # Both tasks should be triggered
                assert result["triggered_count"] == 2

                # Simple task should be triggered first
                assert triggered_tasks[0] == str(simple_task.id)
                assert triggered_tasks[1] == str(complex_task.id)


class TestTaskDependencies:
    """Test task dependency checking (future enhancement)."""

    def test_depends_on_field_documentation(self):
        """Document that depends_on field requires database migration."""
        # This is a placeholder test documenting that task dependencies
        # require adding a depends_on UUID field to TaskRun model
        # and a database migration.
        #
        # Implementation notes:
        # 1. Add depends_on field to TaskRun:
        #    depends_on: Mapped[Optional[uuid.UUID]] = mapped_column(
        #        UUID(as_uuid=True),
        #        ForeignKey("task_runs.id", ondelete="SET NULL"),
        #        nullable=True,
        #        comment="Reference to dependent task (must complete first)"
        #    )
        #
        # 2. Add check in queue_processor.py:
        #    if task.depends_on:
        #        dep_stmt = select(TaskRun).where(TaskRun.id == task.depends_on)
        #        dep_result = await db.execute(dep_stmt)
        #        dep_task = dep_result.scalar_one_or_none()
        #        if not dep_task or dep_task.status != "success":
        #            logger.info(f"Skipping task {task.id}: dependency not ready")
        #            continue
        #
        # 3. Create Alembic migration for new field
        #
        # Deferred to Phase 3 as per project roadmap.

        assert True  # Placeholder


class TestSummaryReporting:
    """Test enhanced summary reporting."""

    @pytest.mark.asyncio
    async def test_summary_includes_skip_reasons(self):
        """Summary should include breakdown of skip reasons."""
        from lazy_bird.tasks.queue_processor import _process_queue_async
        from lazy_bird.models.project import Project

        # Mock database
        mock_db = AsyncMock()

        project_id = uuid.uuid4()
        mock_project = MagicMock(spec=Project)
        mock_project.id = project_id
        mock_project.max_concurrent_tasks = 1
        mock_project.daily_cost_limit_usd = Decimal("10.00")

        # Create 2 queued tasks
        queued_tasks = [
            MagicMock(
                id=uuid.uuid4(),
                project_id=project_id,
                status="queued",
                complexity="simple",
                created_at=datetime.now(timezone.utc),
            )
            for _ in range(2)
        ]

        # 1 running (so concurrency limit hit)
        running_tasks = [MagicMock(id=uuid.uuid4(), status="running")]

        async def mock_execute(stmt):
            stmt_str = str(stmt)
            result = AsyncMock()

            if 'status = "queued"' in stmt_str or "status = 'queued'" in stmt_str:
                result.scalars = MagicMock(
                    return_value=MagicMock(all=MagicMock(return_value=queued_tasks))
                )
            elif "status = 'running'" in stmt_str:
                result.scalars = MagicMock(
                    return_value=MagicMock(all=MagicMock(return_value=running_tasks))
                )
            elif "projects.id" in stmt_str:
                result.scalar_one_or_none = MagicMock(return_value=mock_project)
            elif "coalesce" in stmt_str.lower():
                result.scalar = MagicMock(return_value=Decimal("5.00"))
            else:
                result.scalars = MagicMock(
                    return_value=MagicMock(all=MagicMock(return_value=[]))
                )

            return result

        mock_db.execute = mock_execute
        mock_db.commit = AsyncMock()

        async def mock_get_db():
            yield mock_db

        with patch("lazy_bird.tasks.queue_processor.get_async_db", mock_get_db):
            with patch("lazy_bird.tasks.task_executor.execute_task"):
                result = await _process_queue_async()

                # Verify summary has new fields
                assert "skipped_cost_limit" in result
                assert "skipped_concurrency" in result
                assert isinstance(result["skipped_cost_limit"], int)
                assert isinstance(result["skipped_concurrency"], int)
