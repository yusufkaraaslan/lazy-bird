"""
Analytics Service
Calculates metrics from queue history and logs
"""
import os
import json
import logging
import re
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from collections import defaultdict

logger = logging.getLogger(__name__)


class AnalyticsService:
    """Service for calculating analytics and metrics"""

    def __init__(self, queue_dir: Optional[str] = None, log_dir: Optional[str] = None):
        """
        Initialize analytics service

        Args:
            queue_dir: Path to queue directory
            log_dir: Path to log directory
        """
        if queue_dir:
            self.queue_dir = Path(queue_dir)
        else:
            possible_dirs = [
                Path('/var/lib/lazy_birtd/queue'),
                Path.home() / '.config' / 'lazy_birtd' / 'queue',
            ]
            self.queue_dir = None
            for dir_path in possible_dirs:
                if dir_path.exists():
                    self.queue_dir = dir_path
                    break
            if not self.queue_dir:
                self.queue_dir = possible_dirs[0]

        if log_dir:
            self.log_dir = Path(log_dir)
        else:
            self.log_dir = Path.home() / '.config' / 'lazy_birtd' / 'logs'

    def get_overall_analytics(self, time_range: str = '7d') -> Dict[str, Any]:
        """
        Get overall system analytics

        Args:
            time_range: Time range (7d, 30d, 90d, all)

        Returns:
            Analytics data dictionary
        """
        cutoff_time = self._get_cutoff_time(time_range)

        # Scan log files for completed tasks
        completed_tasks = self._get_completed_tasks(cutoff_time)
        failed_tasks = self._get_failed_tasks(cutoff_time)
        all_tasks = completed_tasks + failed_tasks

        # Calculate metrics
        total_tasks = len(all_tasks)
        success_count = len(completed_tasks)
        failure_count = len(failed_tasks)
        success_rate = (success_count / total_tasks * 100) if total_tasks > 0 else 0

        # Calculate by complexity
        by_complexity = defaultdict(lambda: {'total': 0, 'success': 0, 'failed': 0})
        for task in all_tasks:
            complexity = task.get('complexity', 'unknown')
            by_complexity[complexity]['total'] += 1
            if task.get('success'):
                by_complexity[complexity]['success'] += 1
            else:
                by_complexity[complexity]['failed'] += 1

        # Calculate average duration
        durations = [t['duration'] for t in all_tasks if t.get('duration')]
        avg_duration = sum(durations) / len(durations) if durations else 0

        return {
            'time_range': time_range,
            'total_tasks': total_tasks,
            'completed': success_count,
            'failed': failure_count,
            'success_rate': round(success_rate, 1),
            'avg_duration_minutes': round(avg_duration / 60, 1) if avg_duration else 0,
            'by_complexity': dict(by_complexity),
            'tasks_per_day': self._calculate_tasks_per_day(all_tasks, time_range)
        }

    def get_project_analytics(self, project_id: str, time_range: str = '30d') -> Dict[str, Any]:
        """
        Get project-specific analytics

        Args:
            project_id: Project ID
            time_range: Time range

        Returns:
            Project analytics dictionary
        """
        cutoff_time = self._get_cutoff_time(time_range)

        # Get tasks for this project
        completed_tasks = self._get_completed_tasks(cutoff_time, project_id=project_id)
        failed_tasks = self._get_failed_tasks(cutoff_time, project_id=project_id)
        all_tasks = completed_tasks + failed_tasks

        total_tasks = len(all_tasks)
        success_count = len(completed_tasks)
        failure_count = len(failed_tasks)
        success_rate = (success_count / total_tasks * 100) if total_tasks > 0 else 0

        # Calculate average duration
        durations = [t['duration'] for t in all_tasks if t.get('duration')]
        avg_duration = sum(durations) / len(durations) if durations else 0

        return {
            'project_id': project_id,
            'time_range': time_range,
            'total_tasks': total_tasks,
            'completed': success_count,
            'failed': failure_count,
            'success_rate': round(success_rate, 1),
            'avg_duration_minutes': round(avg_duration / 60, 1) if avg_duration else 0,
            'recent_tasks': all_tasks[:10]  # Last 10 tasks
        }

    def get_cost_analytics(self) -> Dict[str, Any]:
        """
        Get cost analytics

        Note: For Phase 1.1, this is a placeholder.
        Real cost tracking will require Claude API usage monitoring.

        Returns:
            Cost analytics dictionary
        """
        # TODO: Implement real cost tracking by parsing logs for API usage
        # For now, return placeholder data

        return {
            'today': 0.0,
            'this_week': 0.0,
            'this_month': 0.0,
            'by_project': {},
            'note': 'Cost tracking coming soon - requires Claude API usage monitoring'
        }

    def _get_cutoff_time(self, time_range: str) -> Optional[datetime]:
        """Get cutoff time for time range filter"""
        if time_range == 'all':
            return None

        range_map = {
            '7d': 7,
            '30d': 30,
            '90d': 90
        }

        days = range_map.get(time_range, 7)
        return datetime.now() - timedelta(days=days)

    def _get_completed_tasks(self, cutoff_time: Optional[datetime] = None, project_id: Optional[str] = None) -> List[Dict]:
        """Get list of completed tasks from logs"""
        tasks = []

        if not self.log_dir.exists():
            return tasks

        # Pattern: agent-{project_id}-task-{issue_id}.log
        pattern = re.compile(r'agent-(.+?)-task-(\d+)\.log')

        for log_file in self.log_dir.glob('agent-*-task-*.log'):
            match = pattern.match(log_file.name)
            if not match:
                continue

            file_project_id, issue_id = match.groups()

            # Filter by project if specified
            if project_id and file_project_id != project_id:
                continue

            # Check file modification time
            if cutoff_time:
                mtime = datetime.fromtimestamp(log_file.stat().st_mtime)
                if mtime < cutoff_time:
                    continue

            # Check if task succeeded
            try:
                with open(log_file, 'r') as f:
                    log_content = f.read()

                if 'Task completed successfully' in log_content or 'PR created' in log_content:
                    # Extract timestamps if available
                    start_time, end_time = self._extract_timestamps(log_content)
                    duration = (end_time - start_time).total_seconds() if start_time and end_time else None

                    # Extract complexity from log or queue file
                    complexity = self._extract_complexity(file_project_id, issue_id)

                    tasks.append({
                        'project_id': file_project_id,
                        'issue_id': int(issue_id),
                        'success': True,
                        'completed_at': datetime.fromtimestamp(log_file.stat().st_mtime).isoformat(),
                        'duration': duration,
                        'complexity': complexity
                    })
            except Exception as e:
                logger.error(f"Error reading log file {log_file}: {e}")

        return tasks

    def _get_failed_tasks(self, cutoff_time: Optional[datetime] = None, project_id: Optional[str] = None) -> List[Dict]:
        """Get list of failed tasks from logs"""
        tasks = []

        if not self.log_dir.exists():
            return tasks

        pattern = re.compile(r'agent-(.+?)-task-(\d+)\.log')

        for log_file in self.log_dir.glob('agent-*-task-*.log'):
            match = pattern.match(log_file.name)
            if not match:
                continue

            file_project_id, issue_id = match.groups()

            if project_id and file_project_id != project_id:
                continue

            if cutoff_time:
                mtime = datetime.fromtimestamp(log_file.stat().st_mtime)
                if mtime < cutoff_time:
                    continue

            try:
                with open(log_file, 'r') as f:
                    log_content = f.read()

                # Check for failure indicators
                if 'Task failed' in log_content or 'ERROR' in log_content:
                    if 'Task completed successfully' not in log_content:
                        start_time, end_time = self._extract_timestamps(log_content)
                        duration = (end_time - start_time).total_seconds() if start_time and end_time else None
                        complexity = self._extract_complexity(file_project_id, issue_id)

                        tasks.append({
                            'project_id': file_project_id,
                            'issue_id': int(issue_id),
                            'success': False,
                            'completed_at': datetime.fromtimestamp(log_file.stat().st_mtime).isoformat(),
                            'duration': duration,
                            'complexity': complexity
                        })
            except Exception as e:
                logger.error(f"Error reading log file {log_file}: {e}")

        return tasks

    def _extract_timestamps(self, log_content: str) -> tuple:
        """Extract start and end timestamps from log content"""
        # Look for timestamps in log
        # Format: [2025-11-30 12:34:56]
        timestamp_pattern = r'\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\]'
        matches = re.findall(timestamp_pattern, log_content)

        if len(matches) >= 2:
            try:
                start_time = datetime.strptime(matches[0], '%Y-%m-%d %H:%M:%S')
                end_time = datetime.strptime(matches[-1], '%Y-%m-%d %H:%M:%S')
                return start_time, end_time
            except:
                pass

        return None, None

    def _extract_complexity(self, project_id: str, issue_id: str) -> str:
        """Extract complexity from queue file or log"""
        # Try to read from queue file
        queue_file = self.queue_dir / f"{project_id}-issue-{issue_id}.json"
        if queue_file.exists():
            try:
                with open(queue_file, 'r') as f:
                    data = json.load(f)
                    return data.get('complexity', 'unknown')
            except:
                pass

        return 'unknown'

    def _calculate_tasks_per_day(self, tasks: List[Dict], time_range: str) -> float:
        """Calculate average tasks per day"""
        if not tasks:
            return 0.0

        range_days = {
            '7d': 7,
            '30d': 30,
            '90d': 90,
            'all': 365  # Assume max 1 year
        }

        days = range_days.get(time_range, 7)
        return round(len(tasks) / days, 2)
