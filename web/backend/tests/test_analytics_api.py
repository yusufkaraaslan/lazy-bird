"""
Tests for Analytics API endpoints
"""
import pytest
import json


class TestAnalyticsAPI:
    """Test cases for /api/analytics endpoints"""

    def test_get_overall_analytics_default(self, client, mock_analytics_service):
        """Test GET /api/analytics/overall - default 7d range"""
        response = client.get('/api/analytics/overall')
        assert response.status_code == 200

        data = json.loads(response.data)
        assert data['time_range'] == '7d'
        assert 'total_tasks' in data
        assert 'completed' in data
        assert 'failed' in data
        assert 'success_rate' in data
        assert 'by_complexity' in data

    def test_get_overall_analytics_7d(self, client, mock_analytics_service):
        """Test GET /api/analytics/overall?range=7d"""
        response = client.get('/api/analytics/overall?range=7d')
        assert response.status_code == 200

        data = json.loads(response.data)
        assert data['time_range'] == '7d'
        assert data['total_tasks'] == 10
        assert data['completed'] == 8
        assert data['failed'] == 2
        assert data['success_rate'] == 80.0

    def test_get_overall_analytics_30d(self, client, mock_analytics_service):
        """Test GET /api/analytics/overall?range=30d"""
        mock_analytics_service.get_overall_analytics.return_value = {
            'time_range': '30d',
            'total_tasks': 50,
            'completed': 45,
            'failed': 5,
            'success_rate': 90.0,
            'avg_duration_minutes': 12.0,
            'by_complexity': {},
            'tasks_per_day': 1.67
        }

        response = client.get('/api/analytics/overall?range=30d')
        assert response.status_code == 200

        data = json.loads(response.data)
        assert data['time_range'] == '30d'
        assert data['total_tasks'] == 50

    def test_get_overall_analytics_90d(self, client, mock_analytics_service):
        """Test GET /api/analytics/overall?range=90d"""
        response = client.get('/api/analytics/overall?range=90d')
        assert response.status_code == 200

    def test_get_overall_analytics_all(self, client, mock_analytics_service):
        """Test GET /api/analytics/overall?range=all"""
        response = client.get('/api/analytics/overall?range=all')
        assert response.status_code == 200

    def test_get_overall_analytics_invalid_range(self, client):
        """Test GET /api/analytics/overall?range=invalid"""
        response = client.get('/api/analytics/overall?range=invalid')
        assert response.status_code == 400

        data = json.loads(response.data)
        assert 'error' in data
        assert 'invalid' in data['error'].lower()

    def test_get_overall_analytics_by_complexity(self, client, mock_analytics_service):
        """Test GET /api/analytics/overall - verify complexity breakdown"""
        response = client.get('/api/analytics/overall')
        assert response.status_code == 200

        data = json.loads(response.data)
        assert 'by_complexity' in data
        by_complexity = data['by_complexity']

        assert 'simple' in by_complexity
        assert 'medium' in by_complexity
        assert 'complex' in by_complexity

        # Verify structure
        simple = by_complexity['simple']
        assert simple['total'] == 3
        assert simple['success'] == 3
        assert simple['failed'] == 0

    def test_get_project_analytics_default(self, client, mock_analytics_service):
        """Test GET /api/analytics/project/:id - default 30d range"""
        response = client.get('/api/analytics/project/test-project')
        assert response.status_code == 200

        data = json.loads(response.data)
        assert data['project_id'] == 'test-project'
        assert data['time_range'] == '30d'
        assert 'total_tasks' in data
        assert 'completed' in data
        assert 'success_rate' in data

    def test_get_project_analytics_with_range(self, client, mock_analytics_service):
        """Test GET /api/analytics/project/:id?range=7d"""
        response = client.get('/api/analytics/project/test-project?range=7d')
        assert response.status_code == 200

        data = json.loads(response.data)
        assert data['project_id'] == 'test-project'

    def test_get_project_analytics_invalid_range(self, client):
        """Test GET /api/analytics/project/:id?range=invalid"""
        response = client.get('/api/analytics/project/test-project?range=bad')
        assert response.status_code == 400

    def test_get_project_analytics_recent_tasks(self, client, mock_analytics_service):
        """Test GET /api/analytics/project/:id - includes recent tasks"""
        response = client.get('/api/analytics/project/test-project')
        assert response.status_code == 200

        data = json.loads(response.data)
        assert 'recent_tasks' in data
        assert isinstance(data['recent_tasks'], list)

    def test_get_cost_analytics(self, client, mock_analytics_service):
        """Test GET /api/analytics/costs"""
        response = client.get('/api/analytics/costs')
        assert response.status_code == 200

        data = json.loads(response.data)
        assert 'today' in data
        assert 'this_week' in data
        assert 'this_month' in data
        assert 'by_project' in data
        assert 'note' in data

    def test_get_cost_analytics_structure(self, client, mock_analytics_service):
        """Test GET /api/analytics/costs - verify data structure"""
        response = client.get('/api/analytics/costs')
        assert response.status_code == 200

        data = json.loads(response.data)
        assert data['today'] == 0.0
        assert data['this_week'] == 0.0
        assert data['this_month'] == 0.0
        assert isinstance(data['by_project'], dict)
        assert 'coming soon' in data['note'].lower()
