"""
Systemd Service Manager
Handles checking and controlling systemd services
"""
import subprocess
import logging
from typing import Dict, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class SystemdService:
    """Service for managing systemd services"""

    def __init__(self, user_mode: bool = True):
        """
        Initialize systemd service manager

        Args:
            user_mode: If True, use --user flag for systemctl commands
        """
        self.user_mode = user_mode
        self.systemctl_args = ['systemctl']
        if user_mode:
            self.systemctl_args.append('--user')

    def get_service_status(self, service_name: str) -> Dict[str, any]:
        """
        Get detailed status of a systemd service

        Args:
            service_name: Name of the service (e.g., 'issue-watcher')

        Returns:
            Dictionary with status information
        """
        try:
            # Check if service is active
            is_active_cmd = self.systemctl_args + ['is-active', service_name]
            result = subprocess.run(is_active_cmd, capture_output=True, text=True)
            is_active = result.stdout.strip() == 'active'

            # Get detailed status
            status_cmd = self.systemctl_args + ['status', service_name]
            status_result = subprocess.run(status_cmd, capture_output=True, text=True)

            # Parse status output for uptime (simplified)
            status_lines = status_result.stdout.split('\n')
            uptime_seconds = 0
            loaded = False

            for line in status_lines:
                if 'Loaded:' in line:
                    loaded = 'loaded' in line.lower()
                if 'Active:' in line and 'since' in line:
                    # Try to parse uptime (simplified - just return 0 for now)
                    # Full implementation would parse the timestamp
                    uptime_seconds = 0

            return {
                'name': service_name,
                'status': 'running' if is_active else 'stopped',
                'loaded': loaded,
                'uptime_seconds': uptime_seconds,
                'raw_status': status_result.stdout if is_active else None
            }

        except FileNotFoundError:
            logger.warning(f"systemctl not found - running without systemd?")
            return {
                'name': service_name,
                'status': 'unknown',
                'loaded': False,
                'uptime_seconds': 0,
                'error': 'systemd not available'
            }
        except Exception as e:
            logger.error(f"Error checking service {service_name}: {e}")
            return {
                'name': service_name,
                'status': 'error',
                'loaded': False,
                'uptime_seconds': 0,
                'error': str(e)
            }

    def start_service(self, service_name: str) -> bool:
        """
        Start a systemd service

        Args:
            service_name: Name of the service to start

        Returns:
            True if successful, False otherwise
        """
        try:
            cmd = self.systemctl_args + ['start', service_name]
            result = subprocess.run(cmd, capture_output=True, text=True)
            return result.returncode == 0
        except Exception as e:
            logger.error(f"Error starting service {service_name}: {e}")
            return False

    def stop_service(self, service_name: str) -> bool:
        """
        Stop a systemd service

        Args:
            service_name: Name of the service to stop

        Returns:
            True if successful, False otherwise
        """
        try:
            cmd = self.systemctl_args + ['stop', service_name]
            result = subprocess.run(cmd, capture_output=True, text=True)
            return result.returncode == 0
        except Exception as e:
            logger.error(f"Error stopping service {service_name}: {e}")
            return False

    def restart_service(self, service_name: str) -> bool:
        """
        Restart a systemd service

        Args:
            service_name: Name of the service to restart

        Returns:
            True if successful, False otherwise
        """
        try:
            cmd = self.systemctl_args + ['restart', service_name]
            result = subprocess.run(cmd, capture_output=True, text=True)
            return result.returncode == 0
        except Exception as e:
            logger.error(f"Error restarting service {service_name}: {e}")
            return False

    def get_all_services_status(self) -> Dict[str, Dict]:
        """
        Get status of all Lazy_Bird services

        Returns:
            Dictionary mapping service names to status info
        """
        services = ['issue-watcher', 'godot-server']
        statuses = {}

        for service in services:
            statuses[service] = self.get_service_status(service)

        return statuses
