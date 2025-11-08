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
    List all queued tasks

    Query params:
        project_id: Filter by project ID (optional)

    Returns:
        200: List of tasks
        500: Server error
    """
    try:
        tasks = queue_service.get_queued_tasks()

        # Filter by project if specified
        project_id = request.args.get('project_id')
        if project_id:
            tasks = [t for t in tasks if t.get('project_id') == project_id]

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
