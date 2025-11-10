"""
System API
Handles system status and service control
"""
from flask import Blueprint, request, jsonify
import logging
import psutil
import os
from services.systemd_service import SystemdService
from services.config_service import ConfigService

logger = logging.getLogger(__name__)

system_bp = Blueprint('system', __name__, url_prefix='/api/system')
systemd_service = SystemdService(user_mode=True)
config_service = ConfigService()


@system_bp.route('/status', methods=['GET'])
def get_system_status():
    """
    Get overall system status

    Returns:
        200: System status information
    """
    try:
        # Get service statuses
        services = systemd_service.get_all_services_status()

        # Get system resources
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')

        # Get configuration info
        try:
            config = config_service.load_config()
            phase = config.get('phase', 1)
            projects_count = len(config_service.get_projects())
        except:
            phase = 'unknown'
            projects_count = 0

        return jsonify({
            'services': services,
            'resources': {
                'cpu_percent': cpu_percent,
                'memory_percent': memory.percent,
                'memory_used_gb': round(memory.used / (1024**3), 2),
                'memory_total_gb': round(memory.total / (1024**3), 2),
                'disk_percent': disk.percent,
                'disk_free_gb': round(disk.free / (1024**3), 2),
                'disk_total_gb': round(disk.total / (1024**3), 2)
            },
            'config': {
                'phase': phase,
                'projects_count': projects_count
            }
        }), 200

    except Exception as e:
        logger.error(f"Error getting system status: {e}")
        return jsonify({'error': str(e)}), 500


@system_bp.route('/services/<service_name>', methods=['GET'])
def get_service_status(service_name):
    """
    Get status of a specific service

    Args:
        service_name: Name of the service

    Returns:
        200: Service status
        500: Server error
    """
    try:
        status = systemd_service.get_service_status(service_name)
        return jsonify(status), 200

    except Exception as e:
        logger.error(f"Error getting service status for {service_name}: {e}")
        return jsonify({'error': str(e)}), 500


@system_bp.route('/services/<service_name>/start', methods=['POST'])
def start_service(service_name):
    """
    Start a service

    Args:
        service_name: Name of the service to start

    Returns:
        200: Service started
        500: Server error
    """
    try:
        success = systemd_service.start_service(service_name)

        if success:
            status = systemd_service.get_service_status(service_name)
            return jsonify({
                'message': f"Service {service_name} started",
                'status': status
            }), 200
        else:
            return jsonify({
                'error': f"Failed to start service {service_name}"
            }), 500

    except Exception as e:
        logger.error(f"Error starting service {service_name}: {e}")
        return jsonify({'error': str(e)}), 500


@system_bp.route('/services/<service_name>/stop', methods=['POST'])
def stop_service(service_name):
    """
    Stop a service

    Args:
        service_name: Name of the service to stop

    Returns:
        200: Service stopped
        500: Server error
    """
    try:
        success = systemd_service.stop_service(service_name)

        if success:
            status = systemd_service.get_service_status(service_name)
            return jsonify({
                'message': f"Service {service_name} stopped",
                'status': status
            }), 200
        else:
            return jsonify({
                'error': f"Failed to stop service {service_name}"
            }), 500

    except Exception as e:
        logger.error(f"Error stopping service {service_name}: {e}")
        return jsonify({'error': str(e)}), 500


@system_bp.route('/services/<service_name>/restart', methods=['POST'])
def restart_service(service_name):
    """
    Restart a service

    Args:
        service_name: Name of the service to restart

    Returns:
        200: Service restarted
        500: Server error
    """
    try:
        success = systemd_service.restart_service(service_name)

        if success:
            status = systemd_service.get_service_status(service_name)
            return jsonify({
                'message': f"Service {service_name} restarted",
                'status': status
            }), 200
        else:
            return jsonify({
                'error': f"Failed to restart service {service_name}"
            }), 500

    except Exception as e:
        logger.error(f"Error restarting service {service_name}: {e}")
        return jsonify({'error': str(e)}), 500


@system_bp.route('/config', methods=['GET'])
def get_config():
    """
    Get system configuration (non-sensitive)

    Returns:
        200: System configuration
        500: Server error
    """
    try:
        config = config_service.get_system_config()
        return jsonify(config), 200

    except Exception as e:
        logger.error(f"Error getting system config: {e}")
        return jsonify({'error': str(e)}), 500


@system_bp.route('/config', methods=['PUT'])
def update_config():
    """
    Update system configuration

    Request JSON: Dictionary of config fields to update

    Returns:
        200: Configuration updated
        400: Invalid input
        500: Server error
    """
    try:
        updates = request.get_json()

        if not updates:
            return jsonify({'error': 'No data provided'}), 400

        config = config_service.update_system_config(updates)

        return jsonify({
            'message': 'Configuration updated',
            'config': config
        }), 200

    except Exception as e:
        logger.error(f"Error updating system config: {e}")
        return jsonify({'error': str(e)}), 500


@system_bp.route('/services', methods=['GET'])
def list_services():
    """
    List all service files

    Returns:
        200: List of services with metadata
        500: Server error
    """
    try:
        services = systemd_service.list_services()
        return jsonify({'services': services}), 200

    except Exception as e:
        logger.error(f"Error listing services: {e}")
        return jsonify({'error': str(e)}), 500


@system_bp.route('/services/<service_name>/file', methods=['GET'])
def get_service_file(service_name):
    """
    Get service file content

    Args:
        service_name: Name of the service

    Returns:
        200: Service file content
        404: Service not found
        500: Server error
    """
    try:
        content = systemd_service.get_service_file(service_name)

        if content is None:
            return jsonify({'error': 'Service not found'}), 404

        return jsonify({
            'name': service_name,
            'content': content
        }), 200

    except Exception as e:
        logger.error(f"Error getting service file {service_name}: {e}")
        return jsonify({'error': str(e)}), 500


@system_bp.route('/services', methods=['POST'])
def create_service():
    """
    Create a new service file

    Request JSON:
        {
            "name": "service-name",
            "content": "[Unit]\nDescription=...\n[Service]\n..."
        }

    Returns:
        201: Service created
        400: Invalid input or service exists
        500: Server error
    """
    try:
        data = request.get_json()

        if not data or 'name' not in data or 'content' not in data:
            return jsonify({'error': 'Missing name or content'}), 400

        service_name = data['name']
        content = data['content']

        # Validate service name
        if not service_name or '/' in service_name or '..' in service_name:
            return jsonify({'error': 'Invalid service name'}), 400

        success = systemd_service.create_service(service_name, content)

        if success:
            return jsonify({
                'message': f"Service {service_name} created",
                'name': service_name
            }), 201
        else:
            return jsonify({'error': 'Failed to create service (may already exist)'}), 400

    except Exception as e:
        logger.error(f"Error creating service: {e}")
        return jsonify({'error': str(e)}), 500


@system_bp.route('/services/<service_name>', methods=['PUT'])
def update_service_file(service_name):
    """
    Update an existing service file

    Request JSON:
        {
            "content": "[Unit]\nDescription=...\n[Service]\n..."
        }

    Returns:
        200: Service updated
        400: Invalid input or service doesn't exist
        500: Server error
    """
    try:
        data = request.get_json()

        if not data or 'content' not in data:
            return jsonify({'error': 'Missing content'}), 400

        content = data['content']

        success = systemd_service.update_service(service_name, content)

        if success:
            return jsonify({
                'message': f"Service {service_name} updated",
                'name': service_name
            }), 200
        else:
            return jsonify({'error': 'Failed to update service (may not exist)'}), 400

    except Exception as e:
        logger.error(f"Error updating service {service_name}: {e}")
        return jsonify({'error': str(e)}), 500


@system_bp.route('/services/<service_name>', methods=['DELETE'])
def delete_service(service_name):
    """
    Delete a service file

    Args:
        service_name: Name of the service to delete

    Returns:
        200: Service deleted
        400: Service doesn't exist
        500: Server error
    """
    try:
        success = systemd_service.delete_service(service_name)

        if success:
            return jsonify({
                'message': f"Service {service_name} deleted"
            }), 200
        else:
            return jsonify({'error': 'Failed to delete service (may not exist)'}), 400

    except Exception as e:
        logger.error(f"Error deleting service {service_name}: {e}")
        return jsonify({'error': str(e)}), 500


@system_bp.route('/services/<service_name>/enable', methods=['POST'])
def enable_service(service_name):
    """
    Enable a service to start on boot

    Args:
        service_name: Name of the service to enable

    Returns:
        200: Service enabled
        500: Server error
    """
    try:
        success = systemd_service.enable_service(service_name)

        if success:
            return jsonify({
                'message': f"Service {service_name} enabled",
                'name': service_name
            }), 200
        else:
            return jsonify({'error': f"Failed to enable service {service_name}"}), 500

    except Exception as e:
        logger.error(f"Error enabling service {service_name}: {e}")
        return jsonify({'error': str(e)}), 500


@system_bp.route('/services/<service_name>/disable', methods=['POST'])
def disable_service(service_name):
    """
    Disable a service from starting on boot

    Args:
        service_name: Name of the service to disable

    Returns:
        200: Service disabled
        500: Server error
    """
    try:
        success = systemd_service.disable_service(service_name)

        if success:
            return jsonify({
                'message': f"Service {service_name} disabled",
                'name': service_name
            }), 200
        else:
            return jsonify({'error': f"Failed to disable service {service_name}"}), 500

    except Exception as e:
        logger.error(f"Error disabling service {service_name}: {e}")
        return jsonify({'error': str(e)}), 500
