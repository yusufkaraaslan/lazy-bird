"""Celery configuration for Lazy-Bird.

This module contains all Celery configuration settings:
- Broker and result backend URLs
- Task serialization and result formats
- Task routing and queue configuration
- Worker settings and limits
- Beat schedule for periodic tasks
"""

from kombu import Queue

from lazy_bird.core.config import settings

# -----------------------------------------------------------------------------
# BROKER SETTINGS
# -----------------------------------------------------------------------------

# Redis broker URL
broker_url = settings.CELERY_BROKER_URL

# Result backend URL (separate Redis DB for results)
result_backend = settings.CELERY_RESULT_BACKEND

# Connection settings
broker_connection_retry_on_startup = True
broker_connection_retry = True
broker_connection_max_retries = 10

# -----------------------------------------------------------------------------
# TASK SETTINGS
# -----------------------------------------------------------------------------

# Task serialization
task_serializer = "json"
accept_content = ["json"]
result_serializer = "json"

# Task result settings
result_expires = 3600  # Results expire after 1 hour
result_extended = True  # Store additional metadata

# Task execution settings
task_acks_late = True  # Acknowledge tasks after execution (safer)
task_reject_on_worker_lost = True  # Reject tasks if worker dies
worker_prefetch_multiplier = 1  # Only prefetch 1 task at a time (fair distribution)

# Task time limits (prevent runaway tasks)
task_soft_time_limit = 3600  # Soft limit: 1 hour (raises exception)
task_time_limit = 3900  # Hard limit: 65 minutes (kills task)

# Task retry settings
task_autoretry_for = (Exception,)  # Auto-retry on any exception
task_retry_kwargs = {"max_retries": 3}  # Max 3 retries
task_default_retry_delay = 60  # Wait 60 seconds between retries

# Always eager in tests (execute immediately, no async)
task_always_eager = settings.CELERY_TASK_ALWAYS_EAGER
task_eager_propagates = True  # Propagate exceptions in eager mode

# -----------------------------------------------------------------------------
# QUEUE CONFIGURATION
# -----------------------------------------------------------------------------

# Define task queues with priorities
task_queues = (
    Queue(
        "default",
        routing_key="task.#",
        queue_arguments={"x-max-priority": 10},
    ),
    Queue(
        "high_priority",
        routing_key="high.#",
        queue_arguments={"x-max-priority": 10},
    ),
    Queue(
        "low_priority",
        routing_key="low.#",
        queue_arguments={"x-max-priority": 10},
    ),
)

# Default queue for tasks
task_default_queue = "default"
task_default_exchange = "tasks"
task_default_exchange_type = "topic"
task_default_routing_key = "task.default"

# Task routing (map tasks to specific queues)
task_routes = {
    # High priority: Critical workflow tasks
    "lazy_bird.tasks.task_executor.execute_task": {
        "queue": "high_priority",
        "routing_key": "high.execute",
    },
    "lazy_bird.tasks.webhook_delivery.deliver_webhook_task": {
        "queue": "high_priority",
        "routing_key": "high.webhook",
    },
    # Default priority: Regular tasks
    "lazy_bird.tasks.queue_processor.process_queue": {
        "queue": "default",
        "routing_key": "task.queue",
    },
    # Low priority: Cleanup and maintenance
    "lazy_bird.tasks.cleanup.cleanup_old_worktrees": {
        "queue": "low_priority",
        "routing_key": "low.cleanup",
    },
    "lazy_bird.tasks.cleanup.cleanup_expired_results": {
        "queue": "low_priority",
        "routing_key": "low.cleanup",
    },
}

# -----------------------------------------------------------------------------
# WORKER SETTINGS
# -----------------------------------------------------------------------------

# Worker concurrency (number of worker processes)
worker_concurrency = settings.MAX_PARALLEL_TASKS  # From config (default: 3)

# Worker pool type
worker_pool = "prefork"  # Use multiprocessing pool (can also be 'threads', 'solo')

# Worker log settings
worker_log_format = "[%(asctime)s: %(levelname)s/%(processName)s] %(message)s"
worker_task_log_format = (
    "[%(asctime)s: %(levelname)s/%(processName)s] [%(task_name)s(%(task_id)s)] %(message)s"
)

# Worker hijack root logger (integrate with lazy_bird logging)
worker_hijack_root_logger = False

# Worker send events (enable monitoring)
worker_send_task_events = True
task_send_sent_event = True

# -----------------------------------------------------------------------------
# BEAT SCHEDULE (Periodic Tasks)
# -----------------------------------------------------------------------------

# Schedule for periodic tasks (cron-like)
beat_schedule = {
    "process-queue-every-60-seconds": {
        "task": "lazy_bird.tasks.queue_processor.process_queue",
        "schedule": 60.0,  # Run every 60 seconds
        "options": {
            "queue": "default",
            "priority": 5,
        },
    },
    "cleanup-old-worktrees-daily": {
        "task": "lazy_bird.tasks.cleanup.cleanup_old_worktrees",
        "schedule": 86400.0,  # Run daily (24 hours)
        "options": {
            "queue": "low_priority",
            "priority": 1,
        },
    },
    "cleanup-expired-results-hourly": {
        "task": "lazy_bird.tasks.cleanup.cleanup_expired_results",
        "schedule": 3600.0,  # Run every hour
        "options": {
            "queue": "low_priority",
            "priority": 1,
        },
    },
}

# Timezone for beat schedule
timezone = "UTC"
enable_utc = True

# -----------------------------------------------------------------------------
# MONITORING & DEBUGGING
# -----------------------------------------------------------------------------

# Task track started (track when tasks start, not just finish)
task_track_started = True

# Task ignore result (don't store results for these tasks)
task_ignore_result = False

# Worker disable rate limits (for development)
worker_disable_rate_limits = settings.is_development

# Task store errors even if ignored
task_store_errors_even_if_ignored = True
