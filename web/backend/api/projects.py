"""
Projects API
Handles project CRUD operations
"""
from flask import Blueprint, request, jsonify
import logging
from services.config_service import ConfigService

logger = logging.getLogger(__name__)

projects_bp = Blueprint('projects', __name__, url_prefix='/api/projects')
config_service = ConfigService()


@projects_bp.route('', methods=['GET'])
def list_projects():
    """
    List all projects

    Returns:
        200: List of projects
        500: Server error
    """
    try:
        projects = config_service.get_projects()
        return jsonify(projects), 200
    except Exception as e:
        logger.error(f"Error listing projects: {e}")
        return jsonify({'error': str(e)}), 500


@projects_bp.route('/<project_id>', methods=['GET'])
def get_project(project_id):
    """
    Get a specific project

    Args:
        project_id: Project ID

    Returns:
        200: Project data
        404: Project not found
        500: Server error
    """
    try:
        project = config_service.get_project(project_id)
        if not project:
            return jsonify({'error': f"Project '{project_id}' not found"}), 404

        return jsonify(project), 200
    except Exception as e:
        logger.error(f"Error getting project {project_id}: {e}")
        return jsonify({'error': str(e)}), 500


@projects_bp.route('', methods=['POST'])
def add_project():
    """
    Add a new project

    Request JSON:
        {
            "id": "my-project",
            "name": "My Project",
            "type": "godot",
            "path": "/path/to/project",
            "repository": "https://github.com/user/repo",
            "git_platform": "github",
            "test_command": "godot --headless ...",
            "build_command": null,
            "lint_command": null,
            "format_command": null,
            "enabled": true
        }

    Returns:
        201: Project created
        400: Invalid input
        500: Server error
    """
    try:
        project_data = request.get_json()

        if not project_data:
            return jsonify({'error': 'No data provided'}), 400

        # Validate required fields
        required_fields = ['id', 'name', 'type', 'path', 'repository', 'git_platform']
        missing_fields = [f for f in required_fields if f not in project_data]

        if missing_fields:
            return jsonify({
                'error': f"Missing required fields: {', '.join(missing_fields)}"
            }), 400

        # Add project
        project = config_service.add_project(project_data)

        return jsonify(project), 201

    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logger.error(f"Error adding project: {e}")
        return jsonify({'error': str(e)}), 500


@projects_bp.route('/<project_id>', methods=['PUT'])
def update_project(project_id):
    """
    Update an existing project

    Args:
        project_id: Project ID to update

    Request JSON: Dictionary of fields to update

    Returns:
        200: Project updated
        400: Invalid input
        404: Project not found
        500: Server error
    """
    try:
        updates = request.get_json()

        if not updates:
            return jsonify({'error': 'No data provided'}), 400

        # Don't allow ID changes
        if 'id' in updates and updates['id'] != project_id:
            return jsonify({'error': 'Cannot change project ID'}), 400

        # Update project
        project = config_service.update_project(project_id, updates)

        return jsonify(project), 200

    except ValueError as e:
        return jsonify({'error': str(e)}), 404
    except Exception as e:
        logger.error(f"Error updating project {project_id}: {e}")
        return jsonify({'error': str(e)}), 500


@projects_bp.route('/<project_id>', methods=['DELETE'])
def delete_project(project_id):
    """
    Delete a project

    Args:
        project_id: Project ID to delete

    Returns:
        204: Project deleted
        404: Project not found
        500: Server error
    """
    try:
        config_service.delete_project(project_id)
        return '', 204

    except ValueError as e:
        return jsonify({'error': str(e)}), 404
    except Exception as e:
        logger.error(f"Error deleting project {project_id}: {e}")
        return jsonify({'error': str(e)}), 500


@projects_bp.route('/<project_id>/enable', methods=['POST'])
def enable_project(project_id):
    """
    Enable a project

    Args:
        project_id: Project ID to enable

    Returns:
        200: Project enabled
        404: Project not found
        500: Server error
    """
    try:
        project = config_service.update_project(project_id, {'enabled': True})
        return jsonify(project), 200

    except ValueError as e:
        return jsonify({'error': str(e)}), 404
    except Exception as e:
        logger.error(f"Error enabling project {project_id}: {e}")
        return jsonify({'error': str(e)}), 500


@projects_bp.route('/<project_id>/disable', methods=['POST'])
def disable_project(project_id):
    """
    Disable a project

    Args:
        project_id: Project ID to disable

    Returns:
        200: Project disabled
        404: Project not found
        500: Server error
    """
    try:
        project = config_service.update_project(project_id, {'enabled': False})
        return jsonify(project), 200

    except ValueError as e:
        return jsonify({'error': str(e)}), 404
    except Exception as e:
        logger.error(f"Error disabling project {project_id}: {e}")
        return jsonify({'error': str(e)}), 500
