"""
Pytest configuration and shared fixtures for lazy-bird tests
"""

import pytest
import tempfile
import shutil
from pathlib import Path
from typing import Dict, Any
from unittest.mock import Mock, MagicMock


@pytest.fixture
def temp_dir():
    """Create a temporary directory for test files"""
    temp_path = Path(tempfile.mkdtemp())
    yield temp_path
    # Cleanup
    if temp_path.exists():
        shutil.rmtree(temp_path)


@pytest.fixture
def mock_config():
    """Mock lazy-bird configuration"""
    return {
        'project_type': 'python',
        'project_path': '/tmp/test-project',
        'git_platform': 'github',
        'repository': 'user/repo',
        'test_command': 'pytest',
        'build_command': None,
        'lint_command': 'flake8',
        'docker': {
            'enabled': True,
            'memory_limit': '2G'
        },
        'godot_server': {
            'enabled': True,
            'port': 5000,
            'host': '127.0.0.1'
        }
    }


@pytest.fixture
def mock_project_config():
    """Mock project configuration for multi-project tests"""
    return {
        'id': 'test-project',
        'name': 'Test Project',
        'type': 'python',
        'path': '/tmp/test-project',
        'repository': 'user/test-project',
        'git_platform': 'github',
        'test_command': 'pytest',
        'build_command': 'python -m build',
        'lint_command': 'flake8',
        'enabled': True
    }


@pytest.fixture
def mock_multi_project_config(mock_project_config):
    """Mock configuration with multiple projects"""
    return {
        'projects': [
            mock_project_config,
            {
                'id': 'godot-game',
                'name': 'Godot Game',
                'type': 'godot',
                'path': '/tmp/godot-game',
                'repository': 'user/godot-game',
                'git_platform': 'github',
                'test_command': 'godot --headless -s addons/gdUnit4/bin/GdUnitCmdTool.gd',
                'enabled': True
            },
            {
                'id': 'django-backend',
                'name': 'Django Backend',
                'type': 'django',
                'path': '/tmp/django-backend',
                'repository': 'user/django-backend',
                'git_platform': 'gitlab',
                'test_command': 'pytest',
                'lint_command': 'pylint',
                'enabled': False
            }
        ],
        'global': {
            'poll_interval': 60,
            'max_retries': 3,
            'timeout': 300
        }
    }


@pytest.fixture
def mock_github_issue():
    """Mock GitHub issue response"""
    return {
        'number': 42,
        'title': '[Task]: Add player health system',
        'body': '## Task Description\nAdd health tracking to player\n\n## Detailed Steps\n1. Add health variable\n2. Add take_damage method\n\n## Acceptance Criteria\n- [ ] Health starts at 100\n- [ ] Damage reduces health\n\n## Complexity\nmedium',
        'state': 'open',
        'labels': [{'name': 'ready'}],
        'created_at': '2025-11-29T10:00:00Z',
        'updated_at': '2025-11-29T10:00:00Z',
        'html_url': 'https://github.com/user/repo/issues/42'
    }


@pytest.fixture
def mock_gitlab_issue():
    """Mock GitLab issue response"""
    return {
        'iid': 42,
        'title': '[Task]: Add player health system',
        'description': '## Task Description\nAdd health tracking to player',
        'state': 'opened',
        'labels': ['ready'],
        'created_at': '2025-11-29T10:00:00Z',
        'updated_at': '2025-11-29T10:00:00Z',
        'web_url': 'https://gitlab.com/user/repo/-/issues/42'
    }


@pytest.fixture
def mock_test_job():
    """Mock Godot server test job"""
    return {
        'id': 'job-12345',
        'project_path': '/tmp/test-project',
        'test_suite': 'res://tests/test_player.gd',
        'status': 'queued',
        'created_at': '2025-11-29T10:00:00',
        'timeout': 300
    }


@pytest.fixture
def mock_flask_app():
    """Mock Flask app for testing"""
    from flask import Flask
    app = Flask(__name__)
    app.config['TESTING'] = True
    return app


@pytest.fixture
def mock_requests(monkeypatch):
    """Mock requests library"""
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {'status': 'ok'}

    mock_get = Mock(return_value=mock_response)
    mock_post = Mock(return_value=mock_response)

    monkeypatch.setattr('requests.get', mock_get)
    monkeypatch.setattr('requests.post', mock_post)

    return {
        'get': mock_get,
        'post': mock_post,
        'response': mock_response
    }


@pytest.fixture
def mock_subprocess(monkeypatch):
    """Mock subprocess calls"""
    mock_result = Mock()
    mock_result.returncode = 0
    mock_result.stdout = 'Success'
    mock_result.stderr = ''

    mock_run = Mock(return_value=mock_result)
    mock_call = Mock(return_value=0)

    monkeypatch.setattr('subprocess.run', mock_run)
    monkeypatch.setattr('subprocess.call', mock_call)

    return {
        'run': mock_run,
        'call': mock_call,
        'result': mock_result
    }


@pytest.fixture
def secrets_dir(temp_dir):
    """Create a mock secrets directory with API token"""
    secrets_path = temp_dir / '.config' / 'lazy_birtd' / 'secrets'
    secrets_path.mkdir(parents=True, exist_ok=True)

    # Create mock API token
    token_file = secrets_path / 'api_token'
    token_file.write_text('ghp_mock_token_12345')
    token_file.chmod(0o600)

    return secrets_path


@pytest.fixture
def mock_package_root(temp_dir):
    """Mock PACKAGE_ROOT directory structure"""
    # Create directory structure
    (temp_dir / 'scripts').mkdir(parents=True)
    (temp_dir / 'config').mkdir(parents=True)
    (temp_dir / 'web').mkdir(parents=True)

    # Create mock wizard script
    wizard = temp_dir / 'wizard.sh'
    wizard.write_text('#!/bin/bash\necho "Mock wizard"')
    wizard.chmod(0o755)

    # Create mock scripts
    (temp_dir / 'scripts' / 'godot-server.py').write_text('#!/usr/bin/env python3\nprint("Mock godot server")')
    (temp_dir / 'scripts' / 'issue-watcher.py').write_text('#!/usr/bin/env python3\nprint("Mock issue watcher")')
    (temp_dir / 'scripts' / 'project-manager.py').write_text('#!/usr/bin/env python3\nprint("Mock project manager")')

    return temp_dir
