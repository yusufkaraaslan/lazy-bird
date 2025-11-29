"""
Unit tests for scripts/issue-watcher.py module
"""

import pytest
import sys
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

# Add scripts to path for import
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'scripts'))
import issue_watcher as iw


class TestProjectWatcher:
    """Test ProjectWatcher class"""

    def test_init(self, mock_project_config, mock_config, secrets_dir, monkeypatch):
        """Test ProjectWatcher initialization"""
        monkeypatch.setenv('HOME', str(secrets_dir.parent.parent.parent))

        watcher = iw.ProjectWatcher(mock_project_config, mock_config)

        assert watcher.project_id == 'test-project'
        assert watcher.project_name == 'Test Project'
        assert watcher.project_type == 'python'
        assert watcher.platform == 'github'
        assert watcher.repository == 'user/test-project'

    def test_load_token_from_api_token(self, mock_project_config, mock_config, secrets_dir, monkeypatch):
        """Test loading token from api_token file"""
        monkeypatch.setenv('HOME', str(secrets_dir.parent.parent.parent))

        watcher = iw.ProjectWatcher(mock_project_config, mock_config)
        assert watcher.token == 'ghp_mock_token_12345'

    def test_load_token_not_found(self, mock_project_config, mock_config, temp_dir, monkeypatch):
        """Test error when token file doesn't exist"""
        monkeypatch.setenv('HOME', str(temp_dir))

        with pytest.raises(FileNotFoundError):
            iw.ProjectWatcher(mock_project_config, mock_config)

    def test_load_token_empty_file(self, mock_project_config, mock_config, secrets_dir, monkeypatch):
        """Test error when token file is empty"""
        monkeypatch.setenv('HOME', str(secrets_dir.parent.parent.parent))

        # Create empty token file
        token_file = secrets_dir / 'api_token'
        token_file.write_text('')

        with pytest.raises(ValueError):
            iw.ProjectWatcher(mock_project_config, mock_config)


class TestFetchGitHubIssues:
    """Test GitHub issue fetching"""

    def test_fetch_github_issues_success(self, mock_project_config, mock_config, secrets_dir, monkeypatch, mock_github_issue):
        """Test successful GitHub issue fetch"""
        monkeypatch.setenv('HOME', str(secrets_dir.parent.parent.parent))

        watcher = iw.ProjectWatcher(mock_project_config, mock_config)

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = [mock_github_issue]

        with patch('requests.get', return_value=mock_response):
            issues = watcher.fetch_github_issues()

            assert len(issues) == 1
            assert issues[0]['id'] == 42
            assert issues[0]['title'] == '[Task]: Add player health system'
            assert 'ready' in issues[0]['labels']

    def test_fetch_github_issues_skip_pull_requests(self, mock_project_config, mock_config, secrets_dir, monkeypatch, mock_github_issue):
        """Test that pull requests are skipped"""
        monkeypatch.setenv('HOME', str(secrets_dir.parent.parent.parent))

        watcher = iw.ProjectWatcher(mock_project_config, mock_config)

        # Add pull_request field to simulate PR
        pr_issue = mock_github_issue.copy()
        pr_issue['pull_request'] = {'url': 'https://api.github.com/...'}

        mock_response = Mock()
        mock_response.json.return_value = [pr_issue, mock_github_issue]

        with patch('requests.get', return_value=mock_response):
            issues = watcher.fetch_github_issues()

            # Should only return the non-PR issue
            assert len(issues) == 1
            assert issues[0]['id'] == 42

    def test_fetch_github_issues_empty_body(self, mock_project_config, mock_config, secrets_dir, monkeypatch):
        """Test handling of issues with no body"""
        monkeypatch.setenv('HOME', str(secrets_dir.parent.parent.parent))

        watcher = iw.ProjectWatcher(mock_project_config, mock_config)

        issue_data = {
            'number': 1,
            'title': 'Test',
            'body': None,  # No body
            'labels': [{'name': 'ready'}],
            'html_url': 'https://github.com/user/repo/issues/1',
            'created_at': '2025-11-29T10:00:00Z'
        }

        mock_response = Mock()
        mock_response.json.return_value = [issue_data]

        with patch('requests.get', return_value=mock_response):
            issues = watcher.fetch_github_issues()
            assert issues[0]['body'] == ''

    def test_fetch_github_issues_api_error(self, mock_project_config, mock_config, secrets_dir, monkeypatch):
        """Test handling of API errors"""
        monkeypatch.setenv('HOME', str(secrets_dir.parent.parent.parent))

        watcher = iw.ProjectWatcher(mock_project_config, mock_config)

        with patch('requests.get', side_effect=Exception("API Error")):
            issues = watcher.fetch_ready_issues()
            assert issues == []


class TestFetchGitLabIssues:
    """Test GitLab issue fetching"""

    def test_fetch_gitlab_issues_success(self, secrets_dir, monkeypatch, mock_gitlab_issue):
        """Test successful GitLab issue fetch"""
        monkeypatch.setenv('HOME', str(secrets_dir.parent.parent.parent))

        project_config = {
            'id': 'gitlab-project',
            'name': 'GitLab Project',
            'type': 'python',
            'path': '/tmp/project',
            'repository': 'user/gitlab-project',
            'git_platform': 'gitlab',
            'project_id': 12345  # GitLab project ID
        }

        watcher = iw.ProjectWatcher(project_config, {})

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = [mock_gitlab_issue]

        with patch('requests.get', return_value=mock_response):
            issues = watcher.fetch_gitlab_issues()

            assert len(issues) == 1
            assert issues[0]['id'] == 42
            assert 'ready' in issues[0]['labels']

    def test_fetch_gitlab_issues_without_project_id(self, secrets_dir, monkeypatch):
        """Test fetching GitLab issues when project_id needs to be resolved"""
        monkeypatch.setenv('HOME', str(secrets_dir.parent.parent.parent))

        project_config = {
            'id': 'gitlab-project',
            'name': 'GitLab Project',
            'type': 'python',
            'path': '/tmp/project',
            'repository': 'https://gitlab.com/user/project',
            'git_platform': 'gitlab'
            # No project_id
        }

        watcher = iw.ProjectWatcher(project_config, {})

        # Mock both API calls: first for project ID, second for issues
        project_response = Mock()
        project_response.status_code = 200
        project_response.json.return_value = {'id': 12345}

        issues_response = Mock()
        issues_response.status_code = 200
        issues_response.json.return_value = []

        with patch('requests.get', side_effect=[project_response, issues_response]):
            issues = watcher.fetch_gitlab_issues()
            assert isinstance(issues, list)


class TestParseIssue:
    """Test issue parsing"""

    def test_parse_issue_complete(self, mock_project_config, mock_config, secrets_dir, monkeypatch):
        """Test parsing complete issue"""
        monkeypatch.setenv('HOME', str(secrets_dir.parent.parent.parent))

        watcher = iw.ProjectWatcher(mock_project_config, mock_config)

        issue = {
            'id': 42,
            'title': '[Task]: Add health system',
            'body': '## Task Description\nAdd health tracking\n\n## Detailed Steps\n1. Add health variable\n2. Add methods\n\n## Acceptance Criteria\n- [ ] Tests pass',
            'labels': ['ready', 'medium'],
            'url': 'https://github.com/user/repo/issues/42'
        }

        parsed = watcher.parse_issue(issue)

        assert parsed['issue_id'] == 42
        assert parsed['title'] == '[Task]: Add health system'
        assert parsed['complexity'] == 'medium'
        assert parsed['project_id'] == 'test-project'
        assert parsed['project_type'] == 'python'
        assert 'test_command' in parsed

    def test_parse_issue_default_complexity(self, mock_project_config, mock_config, secrets_dir, monkeypatch):
        """Test that complexity defaults to medium"""
        monkeypatch.setenv('HOME', str(secrets_dir.parent.parent.parent))

        watcher = iw.ProjectWatcher(mock_project_config, mock_config)

        issue = {
            'id': 1,
            'title': 'Test',
            'body': 'Test body',
            'labels': ['ready'],  # No complexity label
            'url': 'https://github.com/user/repo/issues/1'
        }

        parsed = watcher.parse_issue(issue)
        assert parsed['complexity'] == 'medium'

    def test_parse_issue_extracts_complexity_from_labels(self, mock_project_config, mock_config, secrets_dir, monkeypatch):
        """Test complexity extraction from labels"""
        monkeypatch.setenv('HOME', str(secrets_dir.parent.parent.parent))

        watcher = iw.ProjectWatcher(mock_project_config, mock_config)

        for complexity_label in ['simple', 'complex']:
            issue = {
                'id': 1,
                'title': 'Test',
                'body': 'Body',
                'labels': ['ready', complexity_label],
                'url': 'https://test.com'
            }

            parsed = watcher.parse_issue(issue)
            assert parsed['complexity'] == complexity_label


class TestParseMarkdownSections:
    """Test markdown section parsing"""

    def test_parse_markdown_sections_complete(self, mock_project_config, mock_config, secrets_dir, monkeypatch):
        """Test parsing markdown with multiple sections"""
        monkeypatch.setenv('HOME', str(secrets_dir.parent.parent.parent))

        watcher = iw.ProjectWatcher(mock_project_config, mock_config)

        markdown = """
## Task Description
This is a description

## Detailed Steps
1. First step
2. Second step
3. Third step

## Acceptance Criteria
- [ ] Criterion 1
- [ ] Criterion 2

## Notes
* Note 1
* Note 2
"""

        sections = watcher.parse_markdown_sections(markdown)

        assert 'Task Description' in sections
        assert 'Detailed Steps' in sections
        assert 'Acceptance Criteria' in sections
        assert 'Notes' in sections

        assert len(sections['Detailed Steps']) == 3
        assert '1. First step' in sections['Detailed Steps']
        assert len(sections['Acceptance Criteria']) == 2

    def test_parse_markdown_sections_empty(self, mock_project_config, mock_config, secrets_dir, monkeypatch):
        """Test parsing empty markdown"""
        monkeypatch.setenv('HOME', str(secrets_dir.parent.parent.parent))

        watcher = iw.ProjectWatcher(mock_project_config, mock_config)

        sections = watcher.parse_markdown_sections('')
        assert sections == {}

    def test_parse_markdown_sections_no_lists(self, mock_project_config, mock_config, secrets_dir, monkeypatch):
        """Test parsing sections without list items"""
        monkeypatch.setenv('HOME', str(secrets_dir.parent.parent.parent))

        watcher = iw.ProjectWatcher(mock_project_config, mock_config)

        markdown = """
## Task Description
Just some text without list items
More text here
"""

        sections = watcher.parse_markdown_sections(markdown)
        assert 'Task Description' in sections
        # No list items, so should be empty
        assert len(sections['Task Description']) == 0

    def test_parse_markdown_sections_various_list_formats(self, mock_project_config, mock_config, secrets_dir, monkeypatch):
        """Test parsing different list item formats"""
        monkeypatch.setenv('HOME', str(secrets_dir.parent.parent.parent))

        watcher = iw.ProjectWatcher(mock_project_config, mock_config)

        markdown = """
## Steps
1. Numbered item
2. Another numbered
- Bullet item
* Another bullet
[ ] Unchecked checkbox
[x] Checked checkbox
"""

        sections = watcher.parse_markdown_sections(markdown)
        assert len(sections['Steps']) == 6


class TestFetchReadyIssues:
    """Test main fetch_ready_issues method"""

    def test_fetch_ready_issues_github(self, mock_project_config, mock_config, secrets_dir, monkeypatch, mock_github_issue):
        """Test fetching from GitHub"""
        monkeypatch.setenv('HOME', str(secrets_dir.parent.parent.parent))

        watcher = iw.ProjectWatcher(mock_project_config, mock_config)

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = [mock_github_issue]

        with patch('requests.get', return_value=mock_response):
            issues = watcher.fetch_ready_issues()
            assert len(issues) == 1

    def test_fetch_ready_issues_gitlab(self, secrets_dir, monkeypatch, mock_gitlab_issue):
        """Test fetching from GitLab"""
        monkeypatch.setenv('HOME', str(secrets_dir.parent.parent.parent))

        project_config = {
            'id': 'gitlab-proj',
            'name': 'GitLab',
            'type': 'python',
            'path': '/tmp',
            'repository': 'user/repo',
            'git_platform': 'gitlab',
            'project_id': 123
        }

        watcher = iw.ProjectWatcher(project_config, {})

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = [mock_gitlab_issue]

        with patch('requests.get', return_value=mock_response):
            issues = watcher.fetch_ready_issues()
            assert len(issues) == 1

    def test_fetch_ready_issues_unsupported_platform(self, secrets_dir, monkeypatch):
        """Test handling of unsupported platform"""
        monkeypatch.setenv('HOME', str(secrets_dir.parent.parent.parent))

        project_config = {
            'id': 'test',
            'name': 'Test',
            'type': 'python',
            'path': '/tmp',
            'repository': 'user/repo',
            'git_platform': 'bitbucket'  # Unsupported
        }

        watcher = iw.ProjectWatcher(project_config, {})

        issues = watcher.fetch_ready_issues()
        assert issues == []

    def test_fetch_ready_issues_network_error(self, mock_project_config, mock_config, secrets_dir, monkeypatch):
        """Test handling of network errors"""
        monkeypatch.setenv('HOME', str(secrets_dir.parent.parent.parent))

        watcher = iw.ProjectWatcher(mock_project_config, mock_config)

        import requests
        with patch('requests.get', side_effect=requests.exceptions.RequestException("Network error")):
            issues = watcher.fetch_ready_issues()
            assert issues == []


class TestProjectWatcherIntegration:
    """Integration tests for ProjectWatcher"""

    def test_full_workflow_github(self, mock_project_config, mock_config, secrets_dir, monkeypatch, mock_github_issue):
        """Test complete workflow from fetch to parse"""
        monkeypatch.setenv('HOME', str(secrets_dir.parent.parent.parent))

        watcher = iw.ProjectWatcher(mock_project_config, mock_config)

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = [mock_github_issue]

        with patch('requests.get', return_value=mock_response):
            # Fetch issues
            issues = watcher.fetch_ready_issues()
            assert len(issues) > 0

            # Parse first issue
            parsed = watcher.parse_issue(issues[0])
            assert parsed['project_id'] == 'test-project'
            assert parsed['issue_id'] == 42
            assert 'test_command' in parsed

    def test_multi_project_context(self, secrets_dir, monkeypatch):
        """Test that project context is properly included"""
        monkeypatch.setenv('HOME', str(secrets_dir.parent.parent.parent))

        project_configs = [
            {
                'id': 'godot-game',
                'name': 'Godot Game',
                'type': 'godot',
                'path': '/tmp/godot',
                'repository': 'user/godot',
                'git_platform': 'github',
                'test_command': 'godot --headless'
            },
            {
                'id': 'python-api',
                'name': 'Python API',
                'type': 'python',
                'path': '/tmp/python',
                'repository': 'user/python',
                'git_platform': 'github',
                'test_command': 'pytest'
            }
        ]

        # Create watchers for each project
        watchers = []
        for config in project_configs:
            watcher = iw.ProjectWatcher(config, {})
            watchers.append(watcher)

        # Verify each has unique context
        assert watchers[0].project_id == 'godot-game'
        assert watchers[0].test_command == 'godot --headless'
        assert watchers[1].project_id == 'python-api'
        assert watchers[1].test_command == 'pytest'
