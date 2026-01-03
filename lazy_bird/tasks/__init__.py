"""Celery application for background task processing.

This module initializes the Celery application for Lazy-Bird's background tasks:
- Queue processing (polling for queued TaskRuns)
- Task execution (running Claude Code, git operations, tests)
- Webhook delivery with retry logic
- Periodic cleanup tasks

Usage:
    # Start Celery worker
    celery -A lazy_bird.tasks worker --loglevel=info

    # Start Celery beat (for periodic tasks)
    celery -A lazy_bird.tasks beat --loglevel=info

    # Start both worker and beat
    celery -A lazy_bird.tasks worker --beat --loglevel=info
"""

from celery import Celery

from lazy_bird.core.config import settings

# Create Celery app instance
app = Celery("lazy_bird")

# Load configuration from celeryconfig module
app.config_from_object("lazy_bird.tasks.celeryconfig")

# Auto-discover tasks in these modules
app.autodiscover_tasks(
    [
        "lazy_bird.tasks",
    ]
)


@app.task(bind=True)
def debug_task(self):
    """Debug task to test Celery is working."""
    print(f"Request: {self.request!r}")
    return {
        "status": "ok",
        "celery_version": self.app.VERSION if hasattr(self.app, "VERSION") else "unknown",
        "task_id": self.request.id,
    }


__all__ = ["app", "debug_task"]
