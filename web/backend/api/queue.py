"""
Queue API
Handles task queue operations
"""
from flask import Blueprint, request, jsonify
import logging
from services.queue_service import QueueService

logger = logging.getLogger(__name__)

queue_bp = Blueprint('queue', __name__, url_prefix='/api/queue')
queue_service = QueueService()


@queue_bp.route('', methods=['GET'])
def list_tasks():
    """
    List all tasks with status

    Query params:
        project_id: Filter by project ID (optional)
        status: Filter by status (queued, in-progress, completed, failed)
        include_completed: Include completed tasks from logs (default: false)

    Returns:
        200: List of tasks with status info
        500: Server error
    """
    try:
        # Check if we should include completed tasks
        include_completed = request.args.get('include_completed', 'false').lower() == 'true'

        # Get all tasks with status
        tasks = queue_service.get_all_tasks_with_status(include_completed=include_completed)

        # Filter by project if specified
        project_id = request.args.get('project_id')
        if project_id:
            tasks = [t for t in tasks if t.get('project_id') == project_id]

        # Filter by status if specified
        status = request.args.get('status')
        if status:
            tasks = [t for t in tasks if t.get('status') == status]

        return jsonify(tasks), 200

    except Exception as e:
        logger.error(f"Error listing tasks: {e}")
        return jsonify({'error': str(e)}), 500


@queue_bp.route('/<task_id>', methods=['GET'])
def get_task(task_id):
    """
    Get a specific task

    Args:
        task_id: Task ID

    Returns:
        200: Task data
        404: Task not found
        500: Server error
    """
    try:
        task = queue_service.get_task(task_id)

        if not task:
            return jsonify({'error': f"Task '{task_id}' not found"}), 404

        return jsonify(task), 200

    except Exception as e:
        logger.error(f"Error getting task {task_id}: {e}")
        return jsonify({'error': str(e)}), 500


@queue_bp.route('/<task_id>', methods=['DELETE'])
def cancel_task(task_id):
    """
    Cancel a queued task

    Args:
        task_id: Task ID to cancel

    Returns:
        204: Task cancelled
        404: Task not found
        500: Server error
    """
    try:
        success = queue_service.delete_task(task_id)

        if success:
            return '', 204
        else:
            return jsonify({'error': f"Task '{task_id}' not found"}), 404

    except Exception as e:
        logger.error(f"Error cancelling task {task_id}: {e}")
        return jsonify({'error': str(e)}), 500


@queue_bp.route('/stats', methods=['GET'])
def get_queue_stats():
    """
    Get queue statistics

    Returns:
        200: Queue statistics
        500: Server error
    """
    try:
        stats = queue_service.get_queue_stats()
        return jsonify(stats), 200

    except Exception as e:
        logger.error(f"Error getting queue stats: {e}")
        return jsonify({'error': str(e)}), 500


@queue_bp.route('/<project_id>/<int:issue_id>/logs', methods=['GET'])
def get_task_logs(project_id, issue_id):
    """
    Get logs for a specific task

    Args:
        project_id: Project ID
        issue_id: Issue ID

    Query params:
        lines: Number of lines to return (default: all)

    Returns:
        200: Log content and metadata
        404: Log file not found
        500: Server error
    """
    try:
        lines = request.args.get('lines', type=int)
        logs = queue_service.get_task_logs(project_id, issue_id, lines=lines)

        if not logs['exists']:
            return jsonify({'error': 'Log file not found'}), 404

        return jsonify(logs), 200

    except Exception as e:
        logger.error(f"Error getting logs for {project_id}/task-{issue_id}: {e}")
        return jsonify({'error': str(e)}), 500
