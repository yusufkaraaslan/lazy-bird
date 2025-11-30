"""
Tests for Issues API endpoints
"""
import pytest
import json


class TestIssuesAPI:
    """Test cases for /api/issues endpoints"""

    def test_list_issues(self, client, mock_queue_service):
        """Test GET /api/issues - list issues"""
        response = client.get('/api/issues')
        assert response.status_code == 200

        data = json.loads(response.data)
        assert 'total' in data
        assert 'issues' in data
        assert isinstance(data['issues'], list)

    def test_list_issues_with_filters(self, client, mock_queue_service):
        """Test GET /api/issues with query parameters"""
        response = client.get('/api/issues?project_id=test-project&status=queued&limit=10')
        assert response.status_code == 200

        data = json.loads(response.data)
        assert data['limit'] == 10

    def test_list_issues_with_complexity_filter(self, client, mock_queue_service):
        """Test GET /api/issues with complexity filter"""
        response = client.get('/api/issues?complexity=medium')
        assert response.status_code == 200

    def test_get_issue_success_github(self, client, mock_github_service, mock_config_service, mock_queue_service):
        """Test GET /api/issues/:number - GitHub issue"""
        response = client.get('/api/issues/42?project_id=test-project')
        assert response.status_code == 200

        data = json.loads(response.data)
        assert data['number'] == 42
        assert data['title'] == 'Test Issue'
        assert data['project_id'] == 'test-project'
        assert 'local_status' in data

    def test_get_issue_missing_project_id(self, client):
        """Test GET /api/issues/:number - missing project_id"""
        response = client.get('/api/issues/42')
        assert response.status_code == 400

        data = json.loads(response.data)
        assert 'error' in data
        assert 'project_id' in data['error'].lower()

    def test_get_issue_project_not_found(self, client, mock_config_service):
        """Test GET /api/issues/:number - project not found"""
        mock_config_service.get_project.return_value = None

        response = client.get('/api/issues/42?project_id=nonexistent')
        assert response.status_code == 404

        data = json.loads(response.data)
        assert 'error' in data

    def test_get_issue_not_found(self, client, mock_github_service, mock_config_service):
        """Test GET /api/issues/:number - issue not found"""
        mock_github_service.get_issue.return_value = None

        response = client.get('/api/issues/999?project_id=test-project')
        assert response.status_code == 404

        data = json.loads(response.data)
        assert 'error' in data

    def test_get_issue_gitlab(self, client, mock_gitlab_service, mock_config_service, mock_queue_service):
        """Test GET /api/issues/:number - GitLab issue"""
        mock_config_service.get_project.return_value = {
            'id': 'test-project',
            'name': 'Test Project',
            'repository': 'https://gitlab.com/user/repo',
            'git_platform': 'gitlab'
        }

        response = client.get('/api/issues/42?project_id=test-project')
        assert response.status_code == 200

        data = json.loads(response.data)
        assert data['number'] == 42

    def test_get_issue_logs_success(self, client, mock_queue_service):
        """Test GET /api/issues/:number/logs"""
        response = client.get('/api/issues/42/logs?project_id=test-project')
        assert response.status_code == 200

        data = json.loads(response.data)
        assert data['exists'] is True
        assert 'content' in data

    def test_get_issue_logs_missing_project_id(self, client):
        """Test GET /api/issues/:number/logs - missing project_id"""
        response = client.get('/api/issues/42/logs')
        assert response.status_code == 400

    def test_get_issue_logs_not_found(self, client, mock_queue_service):
        """Test GET /api/issues/:number/logs - log not found"""
        mock_queue_service.get_task_logs.return_value = {'exists': False}

        response = client.get('/api/issues/42/logs?project_id=test-project')
        assert response.status_code == 404

    def test_retry_issue_success(self, client, mock_github_service, mock_config_service):
        """Test POST /api/issues/:number/retry"""
        response = client.post(
            '/api/issues/42/retry',
            data=json.dumps({'project_id': 'test-project'}),
            content_type='application/json'
        )
        assert response.status_code == 200

        data = json.loads(response.data)
        assert data['issue_number'] == 42
        assert 're-queued' in data['message'].lower()

    def test_retry_issue_missing_project_id(self, client):
        """Test POST /api/issues/:number/retry - missing project_id"""
        response = client.post(
            '/api/issues/42/retry',
            data=json.dumps({}),
            content_type='application/json'
        )
        assert response.status_code == 400

    def test_retry_issue_not_found(self, client, mock_github_service, mock_config_service):
        """Test POST /api/issues/:number/retry - issue not found"""
        mock_github_service.get_issue.return_value = None

        response = client.post(
            '/api/issues/42/retry',
            data=json.dumps({'project_id': 'test-project'}),
            content_type='application/json'
        )
        assert response.status_code == 404

    def test_cancel_issue_success(self, client, mock_queue_service, mock_config_service, mock_github_service):
        """Test POST /api/issues/:number/cancel"""
        response = client.post(
            '/api/issues/42/cancel',
            data=json.dumps({'project_id': 'test-project'}),
            content_type='application/json'
        )
        assert response.status_code == 200

        data = json.loads(response.data)
        assert data['issue_number'] == 42
        assert 'cancelled' in data['message'].lower()

    def test_cancel_issue_missing_project_id(self, client):
        """Test POST /api/issues/:number/cancel - missing project_id"""
        response = client.post(
            '/api/issues/42/cancel',
            data=json.dumps({}),
            content_type='application/json'
        )
        assert response.status_code == 400

    def test_cancel_issue_removes_labels(self, client, mock_queue_service, mock_config_service, mock_github_service):
        """Test POST /api/issues/:number/cancel - verifies labels removed"""
        response = client.post(
            '/api/issues/42/cancel',
            data=json.dumps({'project_id': 'test-project'}),
            content_type='application/json'
        )
        assert response.status_code == 200

        # Verify remove_label was called
        assert mock_github_service.remove_label.called
