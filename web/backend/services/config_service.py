"""
Configuration Service
Handles reading and writing config.yml for Lazy_Bird
"""
import os
import yaml
from pathlib import Path
from typing import Dict, List, Optional, Any


class ConfigService:
    """Service for managing Lazy_Bird configuration"""

    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize config service

        Args:
            config_path: Path to config.yml (default: ~/.config/lazy_birtd/config.yml)
        """
        if config_path:
            self.config_path = Path(config_path)
        else:
            self.config_path = Path.home() / '.config' / 'lazy_birtd' / 'config.yml'

    def load_config(self) -> Dict[str, Any]:
        """
        Load configuration from YAML file

        Returns:
            Configuration dictionary

        Raises:
            FileNotFoundError: If config file doesn't exist
            yaml.YAMLError: If YAML is invalid
        """
        if not self.config_path.exists():
            raise FileNotFoundError(f"Config file not found: {self.config_path}")

        with open(self.config_path, 'r') as f:
            config = yaml.safe_load(f)

        return config if config else {}

    def save_config(self, config: Dict[str, Any]) -> None:
        """
        Save configuration to YAML file

        Args:
            config: Configuration dictionary to save
        """
        # Create directory if it doesn't exist
        self.config_path.parent.mkdir(parents=True, exist_ok=True)

        with open(self.config_path, 'w') as f:
            yaml.safe_dump(config, f, default_flow_style=False, sort_keys=False)

    def get_projects(self) -> List[Dict[str, Any]]:
        """
        Get list of all projects from config

        Returns:
            List of project dictionaries
        """
        config = self.load_config()

        # Phase 1.1: Multi-project support
        if 'projects' in config and isinstance(config['projects'], list):
            return config['projects']

        # Legacy single-project support
        if 'project' in config:
            return [config['project']]

        return []

    def get_project(self, project_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a specific project by ID

        Args:
            project_id: Project ID to find

        Returns:
            Project dictionary or None if not found
        """
        projects = self.get_projects()
        for project in projects:
            if project.get('id') == project_id:
                return project
        return None

    def add_project(self, project: Dict[str, Any]) -> Dict[str, Any]:
        """
        Add a new project to configuration

        Args:
            project: Project dictionary to add

        Returns:
            The added project

        Raises:
            ValueError: If project ID already exists or is invalid
        """
        # Validate required fields
        required_fields = ['id', 'name', 'type', 'path', 'repository', 'git_platform']
        for field in required_fields:
            if field not in project:
                raise ValueError(f"Missing required field: {field}")

        # Check if project ID already exists
        existing_project = self.get_project(project['id'])
        if existing_project:
            raise ValueError(f"Project with ID '{project['id']}' already exists")

        # Load config
        config = self.load_config()

        # Ensure projects array exists
        if 'projects' not in config:
            config['projects'] = []

        # Set default values for optional fields
        project.setdefault('test_command', None)
        project.setdefault('build_command', None)
        project.setdefault('lint_command', None)
        project.setdefault('format_command', None)
        project.setdefault('enabled', True)

        # Add project
        config['projects'].append(project)

        # Save config
        self.save_config(config)

        return project

    def update_project(self, project_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update an existing project

        Args:
            project_id: ID of project to update
            updates: Dictionary of fields to update

        Returns:
            Updated project dictionary

        Raises:
            ValueError: If project not found
        """
        config = self.load_config()
        projects = config.get('projects', [])

        # Find and update project
        for i, project in enumerate(projects):
            if project.get('id') == project_id:
                # Update fields
                projects[i].update(updates)
                # Don't allow ID changes
                projects[i]['id'] = project_id

                # Save config
                config['projects'] = projects
                self.save_config(config)

                return projects[i]

        raise ValueError(f"Project '{project_id}' not found")

    def delete_project(self, project_id: str) -> None:
        """
        Delete a project from configuration

        Args:
            project_id: ID of project to delete

        Raises:
            ValueError: If project not found
        """
        config = self.load_config()
        projects = config.get('projects', [])

        # Find and remove project
        initial_count = len(projects)
        projects = [p for p in projects if p.get('id') != project_id]

        if len(projects) == initial_count:
            raise ValueError(f"Project '{project_id}' not found")

        config['projects'] = projects
        self.save_config(config)

    def get_system_config(self) -> Dict[str, Any]:
        """
        Get system-level configuration (non-project settings)

        Returns:
            System configuration dictionary
        """
        config = self.load_config()

        # Extract non-project settings
        system_config = {
            'poll_interval_seconds': config.get('poll_interval_seconds', 60),
            'phase': config.get('phase', 1),
            'max_concurrent_agents': config.get('max_concurrent_agents', 1),
            'memory_limit_gb': config.get('memory_limit_gb', 8),
            'retry': config.get('retry', {}),
            'notifications': config.get('notifications', {})
        }

        return system_config

    def update_system_config(self, updates: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update system-level configuration

        Args:
            updates: Dictionary of system settings to update

        Returns:
            Updated system configuration
        """
        config = self.load_config()

        # Update allowed system fields
        allowed_fields = [
            'poll_interval_seconds',
            'phase',
            'max_concurrent_agents',
            'memory_limit_gb',
            'retry',
            'notifications'
        ]

        for key, value in updates.items():
            if key in allowed_fields:
                config[key] = value

        self.save_config(config)

        return self.get_system_config()
