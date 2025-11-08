"""
Queue Service
Handles reading task queue files
"""
import json
import os
from pathlib import Path
from typing import List, Dict, Optional, Any
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class QueueService:
    """Service for managing task queue"""

    def __init__(self, queue_dir: Optional[str] = None):
        """
        Initialize queue service

        Args:
            queue_dir: Path to queue directory (default: ~/.config/lazy_birtd/queue/)
        """
        if queue_dir:
            self.queue_dir = Path(queue_dir)
        else:
            # Try multiple possible locations
            possible_dirs = [
                Path('/var/lib/lazy_birtd/queue'),
                Path.home() / '.config' / 'lazy_birtd' / 'queue',
                Path.home() / '.local' / 'share' / 'lazy_birtd' / 'queue'
            ]

            self.queue_dir = None
            for dir_path in possible_dirs:
                if dir_path.exists():
                    self.queue_dir = dir_path
                    break

            # Default to first option if none exist
            if not self.queue_dir:
                self.queue_dir = possible_dirs[0]

        # Create directory if it doesn't exist
        self.queue_dir.mkdir(parents=True, exist_ok=True)

    def get_queued_tasks(self) -> List[Dict[str, Any]]:
        """
        Get all queued tasks

        Returns:
            List of task dictionaries
        """
        tasks = []

        if not self.queue_dir.exists():
            return tasks

        # Read all .json files in queue directory
        for task_file in self.queue_dir.glob('task-*.json'):
            try:
                with open(task_file, 'r') as f:
                    task = json.load(f)

                # Add file metadata
                stat = task_file.stat()
                task['_file'] = task_file.name
                task['_queued_at'] = datetime.fromtimestamp(stat.st_ctime).isoformat()
                task['_size_bytes'] = stat.st_size

                tasks.append(task)
            except Exception as e:
                logger.error(f"Error reading task file {task_file}: {e}")
                continue

        # Sort by queued time (oldest first)
        tasks.sort(key=lambda t: t.get('_queued_at', ''))

        return tasks

    def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a specific task by ID

        Args:
            task_id: Task ID to find

        Returns:
            Task dictionary or None if not found
        """
        # Task files are usually named like: task-{project-id}-{issue-number}.json
        # or task-{issue-number}.json (legacy)
        possible_files = [
            self.queue_dir / f"task-{task_id}.json",
        ]

        # Also try pattern matching
        for task_file in self.queue_dir.glob(f'*{task_id}*.json'):
            possible_files.append(task_file)

        for task_file in possible_files:
            if task_file.exists():
                try:
                    with open(task_file, 'r') as f:
                        task = json.load(f)

                    # Add file metadata
                    stat = task_file.stat()
                    task['_file'] = task_file.name
                    task['_queued_at'] = datetime.fromtimestamp(stat.st_ctime).isoformat()
                    task['_size_bytes'] = stat.st_size

                    return task
                except Exception as e:
                    logger.error(f"Error reading task file {task_file}: {e}")
                    continue

        return None

    def delete_task(self, task_id: str) -> bool:
        """
        Delete a task from the queue (cancel it)

        Args:
            task_id: Task ID to delete

        Returns:
            True if successful, False otherwise
        """
        # Find task file
        possible_files = [
            self.queue_dir / f"task-{task_id}.json",
        ]

        # Also try pattern matching
        for task_file in self.queue_dir.glob(f'*{task_id}*.json'):
            possible_files.append(task_file)

        for task_file in possible_files:
            if task_file.exists():
                try:
                    task_file.unlink()
                    logger.info(f"Deleted task file: {task_file}")
                    return True
                except Exception as e:
                    logger.error(f"Error deleting task file {task_file}: {e}")
                    return False

        logger.warning(f"Task file not found for ID: {task_id}")
        return False

    def get_queue_stats(self) -> Dict[str, Any]:
        """
        Get queue statistics

        Returns:
            Dictionary with queue stats
        """
        tasks = self.get_queued_tasks()

        # Group by project
        projects = {}
        for task in tasks:
            project_id = task.get('project_id', 'unknown')
            if project_id not in projects:
                projects[project_id] = 0
            projects[project_id] += 1

        # Group by complexity
        complexity = {'simple': 0, 'medium': 0, 'complex': 0, 'unknown': 0}
        for task in tasks:
            c = task.get('complexity', 'unknown')
            if c in complexity:
                complexity[c] += 1
            else:
                complexity['unknown'] += 1

        return {
            'total_tasks': len(tasks),
            'by_project': projects,
            'by_complexity': complexity,
            'queue_dir': str(self.queue_dir)
        }
