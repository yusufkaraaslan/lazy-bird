"""
Systemd Service Manager
Handles checking and controlling systemd services
"""
import subprocess
import logging
import os
from pathlib import Path
from typing import Dict, Optional, List
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
            self.service_dir = Path.home() / '.config' / 'systemd' / 'user'
        else:
            self.service_dir = Path('/etc/systemd/system')

        # Ensure service directory exists
        self.service_dir.mkdir(parents=True, exist_ok=True)

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
        Get status of all Lazy_Bird services (dynamically scans filesystem)

        Returns:
            Dictionary mapping service names to status info
        """
        # Get list of actual service files from filesystem
        service_files = self.list_services()
        statuses = {}

        for service_info in service_files:
            service_name = service_info['name']
            statuses[service_name] = self.get_service_status(service_name)

        return statuses

    def list_services(self) -> List[Dict[str, any]]:
        """
        List all service files in the systemd directory

        Returns:
            List of dictionaries with service information
        """
        services = []
        try:
            for service_file in self.service_dir.glob('*.service'):
                service_name = service_file.stem

                # Get enabled status
                is_enabled_cmd = self.systemctl_args + ['is-enabled', service_name]
                result = subprocess.run(is_enabled_cmd, capture_output=True, text=True)
                enabled = result.stdout.strip() == 'enabled'

                services.append({
                    'name': service_name,
                    'filename': service_file.name,
                    'path': str(service_file),
                    'enabled': enabled
                })

            return services
        except Exception as e:
            logger.error(f"Error listing services: {e}")
            return []

    def get_service_file(self, service_name: str) -> Optional[str]:
        """
        Read service file content

        Args:
            service_name: Name of the service (without .service extension)

        Returns:
            Service file content as string, or None if not found
        """
        try:
            service_file = self.service_dir / f"{service_name}.service"
            if service_file.exists():
                return service_file.read_text()
            return None
        except Exception as e:
            logger.error(f"Error reading service file {service_name}: {e}")
            return None

    def create_service(self, service_name: str, content: str) -> bool:
        """
        Create a new service file

        Args:
            service_name: Name of the service (without .service extension)
            content: Service file content

        Returns:
            True if successful, False otherwise
        """
        try:
            service_file = self.service_dir / f"{service_name}.service"

            # Don't overwrite existing service
            if service_file.exists():
                logger.error(f"Service {service_name} already exists")
                return False

            service_file.write_text(content)
            service_file.chmod(0o644)

            # Reload systemd daemon
            reload_cmd = self.systemctl_args + ['daemon-reload']
            subprocess.run(reload_cmd, check=True)

            logger.info(f"Created service {service_name}")
            return True
        except Exception as e:
            logger.error(f"Error creating service {service_name}: {e}")
            return False

    def update_service(self, service_name: str, content: str) -> bool:
        """
        Update an existing service file

        Args:
            service_name: Name of the service (without .service extension)
            content: New service file content

        Returns:
            True if successful, False otherwise
        """
        try:
            service_file = self.service_dir / f"{service_name}.service"

            # Service must exist
            if not service_file.exists():
                logger.error(f"Service {service_name} does not exist")
                return False

            service_file.write_text(content)
            service_file.chmod(0o644)

            # Reload systemd daemon
            reload_cmd = self.systemctl_args + ['daemon-reload']
            subprocess.run(reload_cmd, check=True)

            logger.info(f"Updated service {service_name}")
            return True
        except Exception as e:
            logger.error(f"Error updating service {service_name}: {e}")
            return False

    def delete_service(self, service_name: str) -> bool:
        """
        Delete a service file

        Args:
            service_name: Name of the service (without .service extension)

        Returns:
            True if successful, False otherwise
        """
        try:
            service_file = self.service_dir / f"{service_name}.service"

            if not service_file.exists():
                logger.error(f"Service {service_name} does not exist")
                return False

            # Stop service if running
            self.stop_service(service_name)

            # Disable if enabled
            self.disable_service(service_name)

            # Delete file
            service_file.unlink()

            # Reload systemd daemon
            reload_cmd = self.systemctl_args + ['daemon-reload']
            subprocess.run(reload_cmd, check=True)

            logger.info(f"Deleted service {service_name}")
            return True
        except Exception as e:
            logger.error(f"Error deleting service {service_name}: {e}")
            return False

    def enable_service(self, service_name: str) -> bool:
        """
        Enable a service to start on boot

        Args:
            service_name: Name of the service

        Returns:
            True if successful, False otherwise
        """
        try:
            cmd = self.systemctl_args + ['enable', service_name]
            result = subprocess.run(cmd, capture_output=True, text=True)
            return result.returncode == 0
        except Exception as e:
            logger.error(f"Error enabling service {service_name}: {e}")
            return False

    def disable_service(self, service_name: str) -> bool:
        """
        Disable a service from starting on boot

        Args:
            service_name: Name of the service

        Returns:
            True if successful, False otherwise
        """
        try:
            cmd = self.systemctl_args + ['disable', service_name]
            result = subprocess.run(cmd, capture_output=True, text=True)
            return result.returncode == 0
        except Exception as e:
            logger.error(f"Error disabling service {service_name}: {e}")
            return False
