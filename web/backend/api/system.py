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
