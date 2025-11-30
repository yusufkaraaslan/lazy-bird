"""
Pytest configuration and fixtures for backend API tests
"""
import pytest
import sys
import os
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch

# Add parent directory to path so we can import the app
sys.path.insert(0, str(Path(__file__).parent.parent))


@pytest.fixture
def app():
    """Create Flask app for testing"""
    from app import app as flask_app
    flask_app.config['TESTING'] = True
    return flask_app


@pytest.fixture
def client(app):
    """Create Flask test client"""
    return app.test_client()


@pytest.fixture
def mock_github_service():
    """Mock GitHub service"""
    with patch('api.issues.github_service') as mock:
        mock.get_issue.return_value = {
            'number': 42,
            'title': 'Test Issue',
            'body': 'Test body',
            'state': 'open',
            'labels': ['bug'],
            'created_at': '2025-11-30T00:00:00Z',
            'updated_at': '2025-11-30T00:00:00Z',
            'url': 'https://github.com/user/repo/issues/42',
            'author': 'testuser'
        }
        mock.list_issues.return_value = []
        mock.add_label.return_value = True
        mock.remove_label.return_value = True
        mock.add_comment.return_value = True
        mock.update_issue_status.return_value = True
        yield mock


@pytest.fixture
def mock_gitlab_service():
    """Mock GitLab service"""
    with patch('api.issues.gitlab_service') as mock:
        mock.get_issue.return_value = {
            'number': 42,
            'title': 'Test Issue',
            'body': 'Test body',
            'state': 'opened',
            'labels': ['bug'],
            'created_at': '2025-11-30T00:00:00Z',
            'updated_at': '2025-11-30T00:00:00Z',
            'url': 'https://gitlab.com/user/repo/-/issues/42',
            'author': 'testuser'
        }
        yield mock


@pytest.fixture
def mock_config_service():
    """Mock ConfigService"""
    with patch('api.issues.config_service') as mock:
        mock.get_project.return_value = {
            'id': 'test-project',
            'name': 'Test Project',
            'repository': 'https://github.com/user/repo',
            'git_platform': 'github'
        }
        mock.get_all_projects.return_value = [
            {
                'id': 'test-project',
                'name': 'Test Project',
                'repository': 'https://github.com/user/repo',
                'git_platform': 'github'
            }
        ]
        yield mock


@pytest.fixture
def mock_queue_service():
    """Mock QueueService"""
    with patch('api.issues.queue_service') as mock:
        mock.get_all_tasks_with_status.return_value = [
            {
                'task_id': 'test-project-issue-42',
                'project_id': 'test-project',
                'issue_id': 42,
                'title': 'Test Issue',
                'status': 'queued',
                'complexity': 'medium',
                'queued_at': '2025-11-30T00:00:00Z'
            }
        ]
        mock.get_task.return_value = {
            'task_id': 'test-project-issue-42',
            'status': 'queued',
            'queued_at': '2025-11-30T00:00:00Z'
        }
        mock.get_task_logs.return_value = {
            'exists': True,
            'content': 'Task log content',
            'lines': 100
        }
        mock.delete_task.return_value = True
        yield mock


@pytest.fixture
def mock_analytics_service():
    """Mock AnalyticsService"""
    with patch('api.analytics.analytics_service') as mock:
        mock.get_overall_analytics.return_value = {
            'time_range': '7d',
            'total_tasks': 10,
            'completed': 8,
            'failed': 2,
            'success_rate': 80.0,
            'avg_duration_minutes': 15.5,
            'by_complexity': {
                'simple': {'total': 3, 'success': 3, 'failed': 0},
                'medium': {'total': 5, 'success': 4, 'failed': 1},
                'complex': {'total': 2, 'success': 1, 'failed': 1}
            },
            'tasks_per_day': 1.43
        }
        mock.get_project_analytics.return_value = {
            'project_id': 'test-project',
            'time_range': '30d',
            'total_tasks': 5,
            'completed': 4,
            'failed': 1,
            'success_rate': 80.0,
            'avg_duration_minutes': 12.0,
            'recent_tasks': []
        }
        mock.get_cost_analytics.return_value = {
            'today': 0.0,
            'this_week': 0.0,
            'this_month': 0.0,
            'by_project': {},
            'note': 'Cost tracking coming soon'
        }
        yield mock


@pytest.fixture
def mock_psutil():
    """Mock psutil for agent tests"""
    with patch('api.agents.psutil') as mock:
        # Mock process info
        mock_proc = MagicMock()
        mock_proc.info = {
            'pid': 1234,
            'name': 'claude',
            'cmdline': ['claude', '-p', 'test'],
            'create_time': 1700000000,
            'cpu_percent': 25.5,
            'memory_info': MagicMock(rss=500 * 1024 * 1024)  # 500MB
        }

        mock.process_iter.return_value = [mock_proc]
        mock.time.time.return_value = 1700001000

        # Mock Process class
        mock_process = MagicMock()
        mock_process.as_dict.return_value = {
            'pid': 1234,
            'name': 'claude',
            'cmdline': ['claude', '-p', 'test'],
            'create_time': 1700000000,
            'cpu_percent': 25.5,
            'memory_info': MagicMock(rss=500 * 1024 * 1024),
            'cwd': '/tmp/test'
        }
        mock_process.cpu_percent.return_value = 25.5
        mock_process.memory_info.return_value = MagicMock(rss=500 * 1024 * 1024)
        mock_process.num_threads.return_value = 4
        mock_process.terminate.return_value = None
        mock_process.kill.return_value = None

        mock.Process.return_value = mock_process
        mock.NoSuchProcess = Exception
        mock.AccessDenied = Exception

        yield mock
