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


def _make_scalars_result(items):
    """Return a mock result whose .scalars().all() returns items."""
    result = AsyncMock()
    result.scalars = MagicMock(return_value=MagicMock(all=MagicMock(return_value=items)))
    return result


def _make_scalar_one_result(value):
    """Return a mock result whose .scalar_one_or_none() returns value."""
    result = AsyncMock()
    result.scalar_one_or_none = MagicMock(return_value=value)
    return result


def _make_scalar_result(value):
    """Return a mock result whose .scalar() returns value."""
    result = AsyncMock()
    result.scalar = MagicMock(return_value=value)
    return result


class TestPerProjectConcurrency:
    """Test per-project concurrency limit enforcement."""

    @pytest.mark.asyncio
    async def test_respects_project_max_concurrent_tasks(self):
        """Should skip tasks when project is at concurrency limit."""
        from lazy_bird.tasks.queue_processor import _process_queue_async
        from lazy_bird.models.project import Project

        mock_db = AsyncMock()

        project_id = uuid.uuid4()
        mock_project = MagicMock(spec=Project)
        mock_project.id = project_id
        mock_project.max_concurrent_tasks = 2
        mock_project.daily_cost_limit_usd = Decimal("50.00")

        # 3 queued tasks for this project
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

        # 2 tasks already running globally and per-project
        running_tasks = [
            MagicMock(id=uuid.uuid4(), project_id=project_id, status="running") for _ in range(2)
        ]

        # Query sequence:
        # 1. queued tasks
        # 2. global running tasks
        # 3. project lookup (first task)
        # 4. per-project running tasks (first task)
        # tasks 2 and 3 reuse cached project + running count, so no more DB calls
        call_count = [0]

        async def mock_execute(stmt):
            call_count[0] += 1
            n = call_count[0]
            if n == 1:
                return _make_scalars_result(queued_tasks)
            elif n == 2:
                return _make_scalars_result(running_tasks)
            elif n == 3:
                return _make_scalar_one_result(mock_project)
            elif n == 4:
                # per-project running = 2 (at limit), so all 3 tasks skipped
                return _make_scalars_result(running_tasks)
            else:
                return _make_scalars_result([])

        mock_db.execute = mock_execute
        mock_db.commit = AsyncMock()

        async def mock_get_db():
            yield mock_db

        with patch("lazy_bird.tasks.queue_processor.get_async_db", mock_get_db):
            with patch("lazy_bird.tasks.task_executor.execute_task") as mock_execute_task:
                result = await _process_queue_async()

                # All 3 tasks skipped due to per-project concurrency limit (2/2)
                assert result["skipped_concurrency"] == 3
                assert result["triggered_count"] == 0
                assert mock_execute_task.delay.call_count == 0

    @pytest.mark.asyncio
    async def test_triggers_tasks_when_project_has_available_slots(self):
        """Should trigger tasks when project has available concurrency slots."""
        from lazy_bird.tasks.queue_processor import _process_queue_async
        from lazy_bird.models.project import Project

        mock_db = AsyncMock()

        project_id = uuid.uuid4()
        mock_project = MagicMock(spec=Project)
        mock_project.id = project_id
        mock_project.max_concurrent_tasks = 3
        mock_project.daily_cost_limit_usd = Decimal("50.00")

        # 2 queued tasks
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

        # 1 task already running (2 slots still available)
        running_tasks = [MagicMock(id=uuid.uuid4(), project_id=project_id, status="running")]

        # Query sequence for 2 tasks from same project:
        # 1. queued tasks
        # 2. global running
        # 3. project lookup (first task - not cached yet)
        # 4. per-project running (first task - not cached yet)
        # 5. daily cost (first task - not cached yet)
        #    -> triggers task 1
        # task 2 reuses cached project, running count, and daily cost
        # 6. daily cost again? No - project_daily_costs IS cached per project_id.
        #    So task 2 skips project lookup (cached), skips running count (cached),
        #    skips daily cost (cached) -> directly triggers.
        # So only 5 DB calls total.
        call_count = [0]

        async def mock_execute(stmt):
            call_count[0] += 1
            n = call_count[0]
            if n == 1:
                return _make_scalars_result(queued_tasks)
            elif n == 2:
                return _make_scalars_result(running_tasks)
            elif n == 3:
                return _make_scalar_one_result(mock_project)
            elif n == 4:
                return _make_scalars_result(running_tasks)
            elif n == 5:
                return _make_scalar_result(Decimal("10.00"))
            else:
                return _make_scalars_result([])

        mock_db.execute = mock_execute
        mock_db.commit = AsyncMock()

        async def mock_get_db():
            yield mock_db

        with patch("lazy_bird.tasks.queue_processor.get_async_db", mock_get_db):
            with patch("lazy_bird.tasks.task_executor.execute_task") as mock_execute_task:
                result = await _process_queue_async()

                # Both tasks triggered (3 slots available, 1 running, 2 queued)
                assert result["triggered_count"] == 2
                assert mock_execute_task.delay.call_count == 2


class TestDailyCostLimits:
    """Test daily cost limit enforcement."""

    @pytest.mark.asyncio
    async def test_skips_tasks_when_daily_cost_limit_reached(self):
        """Should skip tasks when project has reached daily cost limit."""
        from lazy_bird.tasks.queue_processor import _process_queue_async
        from lazy_bird.models.project import Project

        mock_db = AsyncMock()

        project_id = uuid.uuid4()
        mock_project = MagicMock(spec=Project)
        mock_project.id = project_id
        mock_project.max_concurrent_tasks = 3
        mock_project.daily_cost_limit_usd = Decimal("50.00")

        queued_task = MagicMock(
            id=uuid.uuid4(),
            project_id=project_id,
            status="queued",
            complexity="simple",
            priority=1,
            created_at=datetime.now(timezone.utc),
        )

        # Query sequence:
        # 1. queued tasks -> [queued_task]
        # 2. global running -> [] (no running tasks)
        # 3. project lookup -> mock_project
        # 4. per-project running -> [] (0 running)
        # 5. daily cost -> $50.00 (at limit, so skip)
        call_count = [0]

        async def mock_execute(stmt):
            call_count[0] += 1
            n = call_count[0]
            if n == 1:
                return _make_scalars_result([queued_task])
            elif n == 2:
                return _make_scalars_result([])
            elif n == 3:
                return _make_scalar_one_result(mock_project)
            elif n == 4:
                return _make_scalars_result([])
            elif n == 5:
                return _make_scalar_result(Decimal("50.00"))
            else:
                return _make_scalars_result([])

        mock_db.execute = mock_execute
        mock_db.commit = AsyncMock()

        async def mock_get_db():
            yield mock_db

        with patch("lazy_bird.tasks.queue_processor.get_async_db", mock_get_db):
            with patch("lazy_bird.tasks.task_executor.execute_task") as mock_execute_task:
                result = await _process_queue_async()

                # Task skipped due to cost limit
                assert result["skipped_cost_limit"] == 1
                assert result["triggered_count"] == 0
                assert mock_execute_task.delay.call_count == 0

    @pytest.mark.asyncio
    async def test_triggers_tasks_when_daily_cost_below_limit(self):
        """Should trigger tasks when daily cost is below limit."""
        from lazy_bird.tasks.queue_processor import _process_queue_async
        from lazy_bird.models.project import Project

        mock_db = AsyncMock()

        project_id = uuid.uuid4()
        mock_project = MagicMock(spec=Project)
        mock_project.id = project_id
        mock_project.max_concurrent_tasks = 3
        mock_project.daily_cost_limit_usd = Decimal("50.00")

        queued_task = MagicMock(
            id=uuid.uuid4(),
            project_id=project_id,
            status="queued",
            complexity="simple",
            priority=1,
            created_at=datetime.now(timezone.utc),
        )

        # Query sequence:
        # 1. queued tasks -> [queued_task]
        # 2. global running -> [] (no running tasks)
        # 3. project lookup -> mock_project
        # 4. per-project running -> [] (0 running)
        # 5. daily cost -> $25.00 (below limit, so trigger)
        call_count = [0]

        async def mock_execute(stmt):
            call_count[0] += 1
            n = call_count[0]
            if n == 1:
                return _make_scalars_result([queued_task])
            elif n == 2:
                return _make_scalars_result([])
            elif n == 3:
                return _make_scalar_one_result(mock_project)
            elif n == 4:
                return _make_scalars_result([])
            elif n == 5:
                return _make_scalar_result(Decimal("25.00"))
            else:
                return _make_scalars_result([])

        mock_db.execute = mock_execute
        mock_db.commit = AsyncMock()

        async def mock_get_db():
            yield mock_db

        with patch("lazy_bird.tasks.queue_processor.get_async_db", mock_get_db):
            with patch("lazy_bird.tasks.task_executor.execute_task") as mock_execute_task:
                result = await _process_queue_async()

                # Task triggered (cost below limit)
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

        mock_db = AsyncMock()

        project_id = uuid.uuid4()
        mock_project = MagicMock(spec=Project)
        mock_project.id = project_id
        mock_project.max_concurrent_tasks = 10
        mock_project.daily_cost_limit_usd = Decimal("100.00")

        # Tasks returned pre-sorted by the DB query (simple first)
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

        queued_tasks = [simple_task, complex_task]

        # Query sequence for 2 tasks from same project:
        # 1. queued tasks -> [simple_task, complex_task]
        # 2. global running -> []
        # 3. project lookup (first task, not cached) -> mock_project
        # 4. per-project running (first task, not cached) -> []
        # 5. daily cost (first task, not cached) -> $10.00 -> trigger simple_task
        # task 2 (complex_task): project cached, running count cached, daily cost cached
        # -> trigger complex_task (no additional DB calls)
        call_count = [0]

        async def mock_execute(stmt):
            call_count[0] += 1
            n = call_count[0]
            if n == 1:
                return _make_scalars_result(queued_tasks)
            elif n == 2:
                return _make_scalars_result([])
            elif n == 3:
                return _make_scalar_one_result(mock_project)
            elif n == 4:
                return _make_scalars_result([])
            elif n == 5:
                return _make_scalar_result(Decimal("10.00"))
            else:
                return _make_scalars_result([])

        mock_db.execute = mock_execute
        mock_db.commit = AsyncMock()

        triggered_tasks = []

        async def mock_get_db():
            yield mock_db

        def track_task(task_id):
            triggered_tasks.append(task_id)

        with patch("lazy_bird.tasks.queue_processor.get_async_db", mock_get_db):
            with patch("lazy_bird.tasks.task_executor.execute_task") as mock_execute_task:
                mock_execute_task.delay.side_effect = track_task

                result = await _process_queue_async()

                # Both tasks triggered
                assert result["triggered_count"] == 2

                # Simple task triggered first (DB returned it first)
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

        mock_db = AsyncMock()

        project_id = uuid.uuid4()
        mock_project = MagicMock(spec=Project)
        mock_project.id = project_id
        mock_project.max_concurrent_tasks = 1
        mock_project.daily_cost_limit_usd = Decimal("10.00")

        # 2 queued tasks
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

        # 1 running (so project concurrency limit = 1/1, all tasks skipped)
        running_tasks = [MagicMock(id=uuid.uuid4(), status="running")]

        # Query sequence:
        # 1. queued tasks -> 2 tasks
        # 2. global running -> 1 running (global_available = MAX - 1, assume MAX >= 2)
        # 3. project lookup (first task) -> mock_project
        # 4. per-project running (first task) -> 1 running (at limit 1/1)
        #    -> skip task 1 (concurrency)
        # task 2 reuses cached project + running count -> skip task 2 (concurrency)
        call_count = [0]

        async def mock_execute(stmt):
            call_count[0] += 1
            n = call_count[0]
            if n == 1:
                return _make_scalars_result(queued_tasks)
            elif n == 2:
                return _make_scalars_result(running_tasks)
            elif n == 3:
                return _make_scalar_one_result(mock_project)
            elif n == 4:
                return _make_scalars_result(running_tasks)
            else:
                return _make_scalars_result([])

        mock_db.execute = mock_execute
        mock_db.commit = AsyncMock()

        async def mock_get_db():
            yield mock_db

        with patch("lazy_bird.tasks.queue_processor.get_async_db", mock_get_db):
            with patch("lazy_bird.tasks.task_executor.execute_task"):
                result = await _process_queue_async()

                # Verify summary has new fields with correct types
                assert "skipped_cost_limit" in result
                assert "skipped_concurrency" in result
                assert isinstance(result["skipped_cost_limit"], int)
                assert isinstance(result["skipped_concurrency"], int)
