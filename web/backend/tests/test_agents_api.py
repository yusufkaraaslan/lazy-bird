"""
Tests for Agents API endpoints
"""
import pytest
import json


class TestAgentsAPI:
    """Test cases for /api/agents endpoints"""

    def test_list_agents(self, client, mock_psutil):
        """Test GET /api/agents - list active agents"""
        response = client.get('/api/agents')
        assert response.status_code == 200

        data = json.loads(response.data)
        assert 'total' in data
        assert 'agents' in data
        assert 'worktrees' in data
        assert isinstance(data['agents'], list)

    def test_list_agents_finds_claude_processes(self, client, mock_psutil):
        """Test GET /api/agents - finds Claude processes"""
        response = client.get('/api/agents')
        assert response.status_code == 200

        data = json.loads(response.data)
        assert data['total'] >= 1
        assert len(data['agents']) >= 1

        # Check agent structure
        agent = data['agents'][0]
        assert 'agent_id' in agent
        assert 'pid' in agent
        assert 'name' in agent
        assert 'status' in agent
        assert 'cpu_percent' in agent
        assert 'memory_mb' in agent
        assert 'uptime_seconds' in agent

    def test_get_agent_success(self, client, mock_psutil):
        """Test GET /api/agents/:id - get agent details"""
        response = client.get('/api/agents/agent-1234')
        assert response.status_code == 200

        data = json.loads(response.data)
        assert data['agent_id'] == 'agent-1234'
        assert data['pid'] == 1234
        assert data['name'] == 'claude'
        assert 'working_directory' in data
        assert 'cpu_percent' in data
        assert 'memory_mb' in data

    def test_get_agent_invalid_format(self, client):
        """Test GET /api/agents/:id - invalid agent_id format"""
        response = client.get('/api/agents/invalid-id')
        assert response.status_code == 400

        data = json.loads(response.data)
        assert 'error' in data
        assert 'invalid' in data['error'].lower()

    def test_get_agent_not_found(self, client, mock_psutil):
        """Test GET /api/agents/:id - agent not found"""
        mock_psutil.Process.side_effect = mock_psutil.NoSuchProcess

        response = client.get('/api/agents/agent-9999')
        assert response.status_code == 404

        data = json.loads(response.data)
        assert 'error' in data
        assert 'not found' in data['error'].lower()

    def test_get_agent_status_success(self, client, mock_psutil):
        """Test GET /api/agents/:id/status - real-time status"""
        response = client.get('/api/agents/agent-1234/status')
        assert response.status_code == 200

        data = json.loads(response.data)
        assert data['agent_id'] == 'agent-1234'
        assert data['status'] == 'working'
        assert 'cpu_percent' in data
        assert 'memory_mb' in data
        assert 'num_threads' in data
        assert 'timestamp' in data

    def test_get_agent_status_invalid_format(self, client):
        """Test GET /api/agents/:id/status - invalid format"""
        response = client.get('/api/agents/bad-format/status')
        assert response.status_code == 400

    def test_get_agent_status_not_found(self, client, mock_psutil):
        """Test GET /api/agents/:id/status - agent not found"""
        mock_psutil.Process.side_effect = mock_psutil.NoSuchProcess

        response = client.get('/api/agents/agent-9999/status')
        assert response.status_code == 404

    def test_stop_agent_terminate(self, client, mock_psutil):
        """Test POST /api/agents/:id/stop - SIGTERM"""
        response = client.post(
            '/api/agents/agent-1234/stop',
            data=json.dumps({'force': False}),
            content_type='application/json'
        )
        assert response.status_code == 200

        data = json.loads(response.data)
        assert data['agent_id'] == 'agent-1234'
        assert data['method'] == 'terminated'
        assert 'terminated' in data['message'].lower()

        # Verify terminate() was called, not kill()
        mock_process = mock_psutil.Process.return_value
        mock_process.terminate.assert_called_once()

    def test_stop_agent_kill(self, client, mock_psutil):
        """Test POST /api/agents/:id/stop - SIGKILL"""
        response = client.post(
            '/api/agents/agent-1234/stop',
            data=json.dumps({'force': True}),
            content_type='application/json'
        )
        assert response.status_code == 200

        data = json.loads(response.data)
        assert data['method'] == 'killed'

        # Verify kill() was called
        mock_process = mock_psutil.Process.return_value
        mock_process.kill.assert_called()

    def test_stop_agent_default_no_force(self, client, mock_psutil):
        """Test POST /api/agents/:id/stop - default to SIGTERM"""
        response = client.post(
            '/api/agents/agent-1234/stop',
            data=json.dumps({}),
            content_type='application/json'
        )
        assert response.status_code == 200

        data = json.loads(response.data)
        assert data['method'] == 'terminated'

    def test_stop_agent_invalid_format(self, client):
        """Test POST /api/agents/:id/stop - invalid format"""
        response = client.post(
            '/api/agents/bad-id/stop',
            data=json.dumps({}),
            content_type='application/json'
        )
        assert response.status_code == 400

    def test_stop_agent_not_found(self, client, mock_psutil):
        """Test POST /api/agents/:id/stop - agent not found"""
        mock_psutil.Process.side_effect = mock_psutil.NoSuchProcess

        response = client.post(
            '/api/agents/agent-9999/stop',
            data=json.dumps({}),
            content_type='application/json'
        )
        assert response.status_code == 404
