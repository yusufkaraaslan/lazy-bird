"""
Agents API
Handles agent status and control

For Phase 1.1, agents are Claude processes working in git worktrees.
We track them via process table and worktree locations.
"""
from flask import Blueprint, request, jsonify
import logging
import psutil
import os
from pathlib import Path
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

agents_bp = Blueprint('agents', __name__, url_prefix='/api/agents')


def _find_claude_processes() -> List[Dict[str, Any]]:
    """
    Find running Claude processes (agents)

    Returns:
        List of process info dictionaries
    """
    claude_processes = []

    for proc in psutil.process_iter(['pid', 'name', 'cmdline', 'create_time', 'cpu_percent', 'memory_info']):
        try:
            # Look for claude or claude-code processes
            if proc.info['name'] and 'claude' in proc.info['name'].lower():
                # Extract task info from command line if available
                cmdline = proc.info['cmdline'] or []
                cmdline_str = ' '.join(cmdline)

                # Try to extract issue number from command line
                issue_number = None
                project_id = None
                for arg in cmdline:
                    if 'issue' in arg.lower() and '#' in arg:
                        try:
                            issue_number = int(arg.split('#')[1].split()[0])
                        except:
                            pass

                # Get resource usage
                cpu_percent = proc.info['cpu_percent'] or 0
                memory_mb = proc.info['memory_info'].rss / (1024 * 1024) if proc.info['memory_info'] else 0

                claude_processes.append({
                    'agent_id': f"agent-{proc.info['pid']}",
                    'pid': proc.info['pid'],
                    'name': proc.info['name'],
                    'status': 'working',
                    'current_task': f"Issue #{issue_number}" if issue_number else 'Unknown task',
                    'cpu_percent': round(cpu_percent, 2),
                    'memory_mb': round(memory_mb, 2),
                    'uptime_seconds': int(psutil.time.time() - proc.info['create_time']),
                    'cmdline': cmdline_str[:200]  # Truncate for display
                })
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue

    return claude_processes


def _find_worktrees() -> List[Dict[str, Any]]:
    """
    Find git worktrees that may contain running agents

    Returns:
        List of worktree info dictionaries
    """
    worktrees = []

    # Check common worktree locations
    worktree_dirs = [
        Path('/tmp/agents'),
        Path.home() / 'tmp' / 'agents',
    ]

    for worktree_dir in worktree_dirs:
        if not worktree_dir.exists():
            continue

        try:
            for worktree_path in worktree_dir.iterdir():
                if not worktree_path.is_dir():
                    continue

                # Extract info from worktree name
                # Format: feature-{project_id}-{issue_number}
                worktree_name = worktree_path.name

                worktrees.append({
                    'worktree_path': str(worktree_path),
                    'worktree_name': worktree_name,
                    'exists': True
                })
        except Exception as e:
            logger.error(f"Error scanning worktree directory {worktree_dir}: {e}")

    return worktrees


@agents_bp.route('', methods=['GET'])
def list_agents():
    """
    List all active agents

    Returns:
        200: List of agents
        500: Server error
    """
    try:
        # Find Claude processes
        claude_processes = _find_claude_processes()

        # Find worktrees (may indicate agents even if process not found)
        worktrees = _find_worktrees()

        # Combine info
        agents = claude_processes

        # Add idle agents from worktrees without processes
        # (worktrees exist but no Claude process running)
        for wt in worktrees:
            # This is a simplified approach - in production you'd correlate better
            pass

        return jsonify({
            'total': len(agents),
            'agents': agents,
            'worktrees': worktrees
        }), 200

    except Exception as e:
        logger.error(f"Error listing agents: {e}")
        return jsonify({'error': str(e)}), 500


@agents_bp.route('/<agent_id>', methods=['GET'])
def get_agent(agent_id):
    """
    Get details for a specific agent

    Args:
        agent_id: Agent ID (format: agent-{pid})

    Returns:
        200: Agent details
        404: Agent not found
        500: Server error
    """
    try:
        # Extract PID from agent_id
        if not agent_id.startswith('agent-'):
            return jsonify({'error': 'Invalid agent_id format'}), 400

        try:
            pid = int(agent_id.split('-')[1])
        except:
            return jsonify({'error': 'Invalid agent_id format'}), 400

        # Find the process
        try:
            proc = psutil.Process(pid)
            proc_info = proc.as_dict(attrs=['pid', 'name', 'cmdline', 'create_time', 'cpu_percent', 'memory_info', 'cwd'])

            # Extract task info
            cmdline_str = ' '.join(proc_info['cmdline'] or [])

            cpu_percent = proc_info['cpu_percent'] or 0
            memory_mb = proc_info['memory_info'].rss / (1024 * 1024) if proc_info['memory_info'] else 0

            return jsonify({
                'agent_id': agent_id,
                'pid': pid,
                'name': proc_info['name'],
                'status': 'working',
                'cpu_percent': round(cpu_percent, 2),
                'memory_mb': round(memory_mb, 2),
                'uptime_seconds': int(psutil.time.time() - proc_info['create_time']),
                'working_directory': proc_info['cwd'],
                'cmdline': cmdline_str
            }), 200

        except psutil.NoSuchProcess:
            return jsonify({'error': f"Agent {agent_id} not found"}), 404

    except Exception as e:
        logger.error(f"Error getting agent {agent_id}: {e}")
        return jsonify({'error': str(e)}), 500


@agents_bp.route('/<agent_id>/status', methods=['GET'])
def get_agent_status(agent_id):
    """
    Get real-time status of an agent

    Args:
        agent_id: Agent ID

    Returns:
        200: Agent status
        404: Agent not found
        500: Server error
    """
    try:
        # Extract PID
        if not agent_id.startswith('agent-'):
            return jsonify({'error': 'Invalid agent_id format'}), 400

        try:
            pid = int(agent_id.split('-')[1])
        except:
            return jsonify({'error': 'Invalid agent_id format'}), 400

        # Get process info
        try:
            proc = psutil.Process(pid)

            # Get current resource usage
            cpu_percent = proc.cpu_percent(interval=0.5)
            memory_info = proc.memory_info()
            memory_mb = memory_info.rss / (1024 * 1024)

            return jsonify({
                'agent_id': agent_id,
                'status': 'working',
                'cpu_percent': round(cpu_percent, 2),
                'memory_mb': round(memory_mb, 2),
                'num_threads': proc.num_threads(),
                'timestamp': psutil.time.time()
            }), 200

        except psutil.NoSuchProcess:
            return jsonify({'error': f"Agent {agent_id} not found"}), 404

    except Exception as e:
        logger.error(f"Error getting agent status {agent_id}: {e}")
        return jsonify({'error': str(e)}), 500


@agents_bp.route('/<agent_id>/stop', methods=['POST'])
def stop_agent(agent_id):
    """
    Stop an agent (terminate Claude process)

    Args:
        agent_id: Agent ID

    Request JSON (optional):
        {
            "force": false  # Use SIGKILL instead of SIGTERM
        }

    Returns:
        200: Agent stopped
        404: Agent not found
        500: Server error
    """
    try:
        # Extract PID
        if not agent_id.startswith('agent-'):
            return jsonify({'error': 'Invalid agent_id format'}), 400

        try:
            pid = int(agent_id.split('-')[1])
        except:
            return jsonify({'error': 'Invalid agent_id format'}), 400

        # Get request data
        data = request.get_json() or {}
        force = data.get('force', False)

        # Terminate process
        try:
            proc = psutil.Process(pid)

            if force:
                proc.kill()  # SIGKILL
                method = 'killed'
            else:
                proc.terminate()  # SIGTERM
                method = 'terminated'

            logger.info(f"Agent {agent_id} (PID {pid}) {method}")

            return jsonify({
                'message': f"Agent {agent_id} {method}",
                'agent_id': agent_id,
                'pid': pid,
                'method': method
            }), 200

        except psutil.NoSuchProcess:
            return jsonify({'error': f"Agent {agent_id} not found"}), 404

    except Exception as e:
        logger.error(f"Error stopping agent {agent_id}: {e}")
        return jsonify({'error': str(e)}), 500
