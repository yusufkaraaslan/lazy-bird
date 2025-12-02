"""
Issues API
Handles issue/task operations with GitHub/GitLab integration
"""
from flask import Blueprint, request, jsonify
import logging
from services.queue_service import QueueService
from services.config_service import ConfigService
from services.github_service import GitHubService
from services.gitlab_service import GitLabService

logger = logging.getLogger(__name__)

issues_bp = Blueprint('issues', __name__, url_prefix='/api/issues')
queue_service = QueueService()
config_service = ConfigService()
github_service = GitHubService()
gitlab_service = GitLabService()


@issues_bp.route('', methods=['GET'])
def list_issues():
    """
    List issues with filters

    Query params:
        project_id: Filter by project ID (optional)
        status: Filter by status (queued, processing, testing, done, failed)
        complexity: Filter by complexity (simple, medium, complex)
        limit: Max results (default: 50)
        offset: Pagination offset (default: 0)

    Returns:
        200: List of issues
        500: Server error
    """
    try:
        # Get query parameters
        project_id = request.args.get('project_id')
        status = request.args.get('status')
        complexity = request.args.get('complexity')
        limit = request.args.get('limit', type=int, default=50)
        offset = request.args.get('offset', type=int, default=0)

        # Get tasks from queue service
        include_completed = status in ['done', 'failed', None]
        tasks = queue_service.get_all_tasks_with_status(include_completed=include_completed)

        # Apply filters
        if project_id:
            tasks = [t for t in tasks if t.get('project_id') == project_id]

        if status:
            tasks = [t for t in tasks if t.get('status') == status]

        if complexity:
            tasks = [t for t in tasks if t.get('complexity') == complexity]

        # Apply pagination
        total = len(tasks)
        tasks = tasks[offset:offset + limit]

        # Map task fields to match frontend Issue interface
        issues = []
        for task in tasks:
            issue = {
                'number': task.get('issue_id', 0),
                'project_id': task.get('project_id', ''),
                'title': task.get('title', ''),
                'body': task.get('body', ''),
                'state': 'open',  # Tasks in queue are open
                'status': task.get('status', 'queued'),
                'labels': [],
                'created_at': task.get('_queued_at', ''),
                'updated_at': task.get('completed_at', task.get('_queued_at', '')),
                'url': task.get('url', ''),
                'author': 'system',
                'complexity': task.get('complexity', 'unknown'),
                'progress': 0  # TODO: Add progress tracking
            }
            issues.append(issue)

        return jsonify({
            'total': total,
            'offset': offset,
            'limit': limit,
            'issues': issues
        }), 200

    except Exception as e:
        logger.error(f"Error listing issues: {e}")
        return jsonify({'error': str(e)}), 500


@issues_bp.route('/<int:issue_number>', methods=['GET'])
def get_issue(issue_number):
    """
    Get issue details from GitHub/GitLab

    Args:
        issue_number: Issue number

    Query params:
        project_id: Project ID (required)

    Returns:
        200: Issue data
        400: Missing project_id
        404: Issue not found
        500: Server error
    """
    try:
        project_id = request.args.get('project_id')
        if not project_id:
            return jsonify({'error': 'project_id query parameter required'}), 400

        # Get project configuration
        project = config_service.get_project(project_id)
        if not project:
            return jsonify({'error': f"Project '{project_id}' not found"}), 404

        # Get issue from GitHub or GitLab
        repo_url = project['repository']
        platform = project['git_platform']

        if platform == 'github':
            issue_data = github_service.get_issue(repo_url, issue_number)
        elif platform == 'gitlab':
            issue_data = gitlab_service.get_issue(repo_url, issue_number)
        else:
            return jsonify({'error': f"Unsupported platform: {platform}"}), 400

        if not issue_data:
            return jsonify({'error': f"Issue #{issue_number} not found"}), 404

        # Enrich with local queue/log data
        queue_task = queue_service.get_task(f"{project_id}-issue-{issue_number}")
        if queue_task:
            issue_data['local_status'] = queue_task.get('status')
            issue_data['queued_at'] = queue_task.get('queued_at')

        issue_data['project_id'] = project_id
        issue_data['project_name'] = project['name']

        return jsonify(issue_data), 200

    except Exception as e:
        logger.error(f"Error getting issue {issue_number}: {e}")
        return jsonify({'error': str(e)}), 500


@issues_bp.route('/<int:issue_number>/logs', methods=['GET'])
def get_issue_logs(issue_number):
    """
    Get logs for an issue

    Args:
        issue_number: Issue number

    Query params:
        project_id: Project ID (required)
        lines: Number of lines to return (optional)

    Returns:
        200: Log content
        400: Missing project_id
        404: Log not found
        500: Server error
    """
    try:
        project_id = request.args.get('project_id')
        if not project_id:
            return jsonify({'error': 'project_id query parameter required'}), 400

        lines = request.args.get('lines', type=int)
        logs = queue_service.get_task_logs(project_id, issue_number, lines=lines)

        if not logs['exists']:
            return jsonify({'error': 'Log file not found'}), 404

        return jsonify(logs), 200

    except Exception as e:
        logger.error(f"Error getting logs for issue {issue_number}: {e}")
        return jsonify({'error': str(e)}), 500


@issues_bp.route('/<int:issue_number>/retry', methods=['POST'])
def retry_issue(issue_number):
    """
    Retry a failed issue

    Args:
        issue_number: Issue number

    Request JSON:
        {
            "project_id": "project-id"
        }

    Returns:
        200: Issue re-queued
        400: Invalid input
        404: Issue not found
        500: Server error
    """
    try:
        data = request.get_json()
        if not data or 'project_id' not in data:
            return jsonify({'error': 'project_id required in request body'}), 400

        project_id = data['project_id']

        # Get project configuration
        project = config_service.get_project(project_id)
        if not project:
            return jsonify({'error': f"Project '{project_id}' not found"}), 404

        # Get issue from GitHub/GitLab to ensure it exists
        repo_url = project['repository']
        platform = project['git_platform']

        if platform == 'github':
            issue_data = github_service.get_issue(repo_url, issue_number)
        elif platform == 'gitlab':
            issue_data = gitlab_service.get_issue(repo_url, issue_number)
        else:
            return jsonify({'error': f"Unsupported platform: {platform}"}), 400

        if not issue_data:
            return jsonify({'error': f"Issue #{issue_number} not found"}), 404

        # Re-queue the task
        # TODO: Implement actual re-queueing logic
        # For now, update status in GitHub/GitLab
        if platform == 'github':
            github_service.update_issue_status(repo_url, issue_number, 'queued')
        elif platform == 'gitlab':
            gitlab_service.update_issue_status(repo_url, issue_number, 'queued')

        return jsonify({
            'message': f"Issue #{issue_number} re-queued",
            'issue_number': issue_number,
            'project_id': project_id
        }), 200

    except Exception as e:
        logger.error(f"Error retrying issue {issue_number}: {e}")
        return jsonify({'error': str(e)}), 500


@issues_bp.route('/<int:issue_number>/cancel', methods=['POST'])
def cancel_issue(issue_number):
    """
    Cancel a running issue

    Args:
        issue_number: Issue number

    Request JSON:
        {
            "project_id": "project-id"
        }

    Returns:
        200: Issue cancelled
        400: Invalid input
        404: Issue not found
        500: Server error
    """
    try:
        data = request.get_json()
        if not data or 'project_id' not in data:
            return jsonify({'error': 'project_id required in request body'}), 400

        project_id = data['project_id']

        # Delete from queue if present
        task_id = f"{project_id}-issue-{issue_number}"
        success = queue_service.delete_task(task_id)

        # Update status in GitHub/GitLab
        project = config_service.get_project(project_id)
        if project:
            repo_url = project['repository']
            platform = project['git_platform']

            if platform == 'github':
                github_service.remove_label(repo_url, issue_number, 'queued')
                github_service.remove_label(repo_url, issue_number, 'processing')
                github_service.add_comment(repo_url, issue_number, '🚫 Task cancelled by user')
            elif platform == 'gitlab':
                gitlab_service.remove_label(repo_url, issue_number, 'queued')
                gitlab_service.remove_label(repo_url, issue_number, 'processing')
                gitlab_service.add_comment(repo_url, issue_number, '🚫 Task cancelled by user')

        return jsonify({
            'message': f"Issue #{issue_number} cancelled",
            'issue_number': issue_number,
            'project_id': project_id,
            'removed_from_queue': success
        }), 200

    except Exception as e:
        logger.error(f"Error cancelling issue {issue_number}: {e}")
        return jsonify({'error': str(e)}), 500
