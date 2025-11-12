"""
Queue Service
Handles reading task queue files
"""
import json
import os
import re
from pathlib import Path
from typing import List, Dict, Optional, Any
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class QueueService:
    """Service for managing task queue"""

    def __init__(self, queue_dir: Optional[str] = None, log_dir: Optional[str] = None):
        """
        Initialize queue service

        Args:
            queue_dir: Path to queue directory (default: ~/.config/lazy_birtd/queue/)
            log_dir: Path to log directory (default: ~/.config/lazy_birtd/logs/)
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

        # Set up log directory
        if log_dir:
            self.log_dir = Path(log_dir)
        else:
            self.log_dir = Path.home() / '.config' / 'lazy_birtd' / 'logs'

        self.log_dir.mkdir(parents=True, exist_ok=True)

    def _get_task_status(self, project_id: str, issue_id: int) -> Dict[str, Any]:
        """
        Get task status by checking log files

        Args:
            project_id: Project ID
            issue_id: Issue ID

        Returns:
            Dictionary with status info
        """
        log_file = self.log_dir / f"agent-{project_id}-task-{issue_id}.log"

        # Default status
        status_info = {
            'status': 'queued',
            'log_file': None,
            'log_excerpt': None,
            'completed_at': None,
            'failed': False,
            'success': False
        }

        if log_file.exists():
            status_info['log_file'] = str(log_file)

            try:
                # Read last 100 lines of log
                with open(log_file, 'r') as f:
                    lines = f.readlines()
                    last_lines = lines[-100:] if len(lines) > 100 else lines
                    log_content = ''.join(last_lines)

                    status_info['log_excerpt'] = log_content

                    # Check for success/failure patterns
                    if '[SUCCESS]' in log_content and 'PR created' in log_content:
                        status_info['status'] = 'completed'
                        status_info['success'] = True
                    elif '[ERROR]' in log_content or 'Tests failed' in log_content:
                        status_info['status'] = 'failed'
                        status_info['failed'] = True
                    elif '[INFO]' in log_content and 'Running Claude Code' in log_content:
                        status_info['status'] = 'in-progress'
                    elif 'No changes detected' in log_content:
                        status_info['status'] = 'completed-no-changes'
                        status_info['success'] = True

                    # Get modification time
                    stat = log_file.stat()
                    status_info['completed_at'] = datetime.fromtimestamp(stat.st_mtime).isoformat()

            except Exception as e:
                logger.error(f"Error reading log file {log_file}: {e}")

        return status_info

    def get_all_tasks_with_status(self, include_completed: bool = False) -> List[Dict[str, Any]]:
        """
        Get all tasks (queued, in-progress, completed) with their status

        Args:
            include_completed: If True, include completed/failed tasks from logs (default: False)

        Returns:
            List of task dictionaries with status info
        """
        tasks = []

        # Get queued tasks
        queued_tasks = self.get_queued_tasks()
        for task in queued_tasks:
            project_id = task.get('project_id', 'unknown')
            issue_id = task.get('issue_id', 0)
            status_info = self._get_task_status(project_id, issue_id)
            task.update(status_info)
            tasks.append(task)

        # Also check for completed tasks in logs (no queue file) - only if requested
        if include_completed and self.log_dir.exists():
            for log_file in self.log_dir.glob('agent-*-task-*.log'):
                # Parse filename: agent-{project_id}-task-{issue_id}.log
                match = re.match(r'agent-(.+?)-task-(\d+)\.log', log_file.name)
                if match:
                    project_id, issue_id = match.groups()
                    issue_id = int(issue_id)

                    # Check if this task is already in queued tasks
                    if any(t.get('issue_id') == issue_id and t.get('project_id') == project_id for t in queued_tasks):
                        continue  # Already included

                    # This is a completed/failed task
                    status_info = self._get_task_status(project_id, issue_id)

                    # Try to read basic info from log
                    task_data = {
                        'issue_id': issue_id,
                        'project_id': project_id,
                        'title': f'Task #{issue_id}',  # Placeholder
                        'complexity': 'unknown',
                        '_file': None,
                        '_from_log': True
                    }
                    task_data.update(status_info)
                    tasks.append(task_data)

        return tasks

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

    def get_task_logs(self, project_id: str, issue_id: int, lines: int = None) -> Dict[str, Any]:
        """
        Get logs for a specific task

        Args:
            project_id: Project ID
            issue_id: Issue ID
            lines: Number of lines to return (None = all lines)

        Returns:
            Dictionary with log content and metadata
        """
        log_file = self.log_dir / f"agent-{project_id}-task-{issue_id}.log"

        result = {
            'log_file': str(log_file),
            'exists': log_file.exists(),
            'content': None,
            'size_bytes': None,
            'lines_count': None,
            'modified_at': None
        }

        if not log_file.exists():
            return result

        try:
            # Get file stats
            stat = log_file.stat()
            result['size_bytes'] = stat.st_size
            result['modified_at'] = datetime.fromtimestamp(stat.st_mtime).isoformat()

            # Read log file
            with open(log_file, 'r') as f:
                log_lines = f.readlines()
                result['lines_count'] = len(log_lines)

                # Return requested number of lines or all
                if lines:
                    log_lines = log_lines[-lines:] if len(log_lines) > lines else log_lines

                result['content'] = ''.join(log_lines)

        except Exception as e:
            logger.error(f"Error reading log file {log_file}: {e}")
            result['error'] = str(e)

        return result
