"""
Unit tests for scripts/project-manager.py module
"""

import pytest
import sys
from pathlib import Path
from unittest.mock import Mock, patch, mock_open
from io import StringIO

# Add scripts to path for import
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'scripts'))
import project_manager as pm


class TestLoadConfig:
    """Test configuration loading"""

    def test_load_config_success(self, temp_dir):
        """Test successful config loading"""
        config_file = temp_dir / 'config.yml'
        config_data = """
projects:
  - id: test-project
    name: Test Project
"""
        config_file.write_text(config_data)

        with patch('yaml.safe_load', return_value={'projects': [{'id': 'test-project'}]}):
            config = pm.load_config(config_file)
            assert 'projects' in config

    def test_load_config_not_found(self, temp_dir):
        """Test error when config file doesn't exist"""
        config_file = temp_dir / 'nonexistent.yml'

        with pytest.raises(SystemExit) as exc_info:
            pm.load_config(config_file)
        assert exc_info.value.code == 1

    def test_load_config_yaml_not_installed(self, temp_dir, monkeypatch):
        """Test error when PyYAML is not installed"""
        config_file = temp_dir / 'config.yml'
        config_file.write_text('test: data')

        def mock_import(name, *args):
            if name == 'yaml':
                raise ImportError("No module named 'yaml'")
            return __import__(name, *args)

        with pytest.raises(SystemExit):
            with patch('builtins.__import__', side_effect=mock_import):
                pm.load_config(config_file)


class TestSaveConfig:
    """Test configuration saving"""

    def test_save_config_success(self, temp_dir):
        """Test successful config save"""
        config_file = temp_dir / 'config.yml'
        config_data = {'projects': [{'id': 'test'}]}

        with patch('yaml.safe_dump') as mock_dump:
            pm.save_config(config_file, config_data)
            mock_dump.assert_called_once()

    def test_save_config_creates_backup(self, temp_dir):
        """Test backup creation when overwriting config"""
        config_file = temp_dir / 'config.yml'
        config_file.write_text('old config')

        with patch('yaml.safe_dump'):
            pm.save_config(config_file, {'new': 'config'})
            backup_file = config_file.with_suffix('.yml.backup')
            assert backup_file.exists()


class TestGetProjects:
    """Test project list retrieval"""

    def test_get_projects_with_projects(self):
        """Test getting projects from config"""
        config = {
            'projects': [
                {'id': 'project1'},
                {'id': 'project2'}
            ]
        }
        projects = pm.get_projects(config)
        assert len(projects) == 2
        assert projects[0]['id'] == 'project1'

    def test_get_projects_empty(self):
        """Test getting projects from empty config"""
        config = {'projects': []}
        projects = pm.get_projects(config)
        assert projects == []

    def test_get_projects_no_key(self):
        """Test getting projects when key doesn't exist"""
        config = {}
        projects = pm.get_projects(config)
        assert projects == []


class TestFindProject:
    """Test project finding"""

    def test_find_project_exists(self):
        """Test finding existing project"""
        projects = [
            {'id': 'project1', 'name': 'Project 1'},
            {'id': 'project2', 'name': 'Project 2'}
        ]
        project = pm.find_project(projects, 'project2')
        assert project is not None
        assert project['name'] == 'Project 2'

    def test_find_project_not_exists(self):
        """Test finding non-existent project"""
        projects = [{'id': 'project1'}]
        project = pm.find_project(projects, 'nonexistent')
        assert project is None

    def test_find_project_empty_list(self):
        """Test finding in empty project list"""
        projects = []
        project = pm.find_project(projects, 'any')
        assert project is None


class TestValidateProject:
    """Test project validation"""

    def test_validate_project_valid(self, temp_dir):
        """Test validating complete valid project"""
        project = {
            'id': 'test-project',
            'name': 'Test Project',
            'type': 'python',
            'path': str(temp_dir),
            'repository': 'user/repo',
            'git_platform': 'github',
            'test_command': 'pytest'
        }
        errors = pm.validate_project(project)
        assert len(errors) == 0

    def test_validate_project_missing_fields(self):
        """Test validation with missing required fields"""
        project = {
            'id': 'test-project',
            'name': 'Test Project'
        }
        errors = pm.validate_project(project)
        assert len(errors) > 0
        assert any('type' in err for err in errors)

    def test_validate_project_invalid_id(self):
        """Test validation with invalid project ID"""
        project = {
            'id': 'invalid id with spaces!',
            'name': 'Test',
            'type': 'python',
            'path': '/tmp',
            'repository': 'repo',
            'git_platform': 'github',
            'test_command': 'test'
        }
        errors = pm.validate_project(project)
        assert any('Invalid project ID' in err for err in errors)

    def test_validate_project_invalid_platform(self, temp_dir):
        """Test validation with invalid git platform"""
        project = {
            'id': 'test',
            'name': 'Test',
            'type': 'python',
            'path': str(temp_dir),
            'repository': 'repo',
            'git_platform': 'bitbucket',  # Invalid
            'test_command': 'test'
        }
        errors = pm.validate_project(project)
        assert any('Invalid git_platform' in err for err in errors)

    def test_validate_project_nonexistent_path(self):
        """Test validation with non-existent path"""
        project = {
            'id': 'test',
            'name': 'Test',
            'type': 'python',
            'path': '/nonexistent/path/12345',
            'repository': 'repo',
            'git_platform': 'github',
            'test_command': 'test'
        }
        errors = pm.validate_project(project)
        assert any('path does not exist' in err for err in errors)

    def test_validate_project_partial(self):
        """Test partial validation"""
        project = {
            'id': 'test-project',
            'name': 'Test'
        }
        errors = pm.validate_project(project, allow_partial=True)
        # With allow_partial, missing fields don't error
        # but invalid formats still do


class TestCmdList:
    """Test list command"""

    def test_cmd_list_with_projects(self, mock_multi_project_config, capsys):
        """Test listing projects"""
        mock_args = Mock()
        mock_args.config = Path('/tmp/config.yml')

        with patch('project_manager.load_config', return_value=mock_multi_project_config):
            pm.cmd_list(mock_args)
            captured = capsys.readouterr()
            assert 'test-project' in captured.out
            assert 'godot-game' in captured.out
            assert 'ENABLED' in captured.out
            assert 'DISABLED' in captured.out

    def test_cmd_list_no_projects(self, capsys):
        """Test listing with no projects"""
        mock_args = Mock()
        mock_args.config = Path('/tmp/config.yml')

        with patch('project_manager.load_config', return_value={}):
            pm.cmd_list(mock_args)
            captured = capsys.readouterr()
            assert 'No projects configured' in captured.out


class TestCmdShow:
    """Test show command"""

    def test_cmd_show_existing_project(self, mock_multi_project_config, capsys):
        """Test showing existing project"""
        mock_args = Mock()
        mock_args.config = Path('/tmp/config.yml')
        mock_args.project_id = 'test-project'

        with patch('project_manager.load_config', return_value=mock_multi_project_config):
            pm.cmd_show(mock_args)
            captured = capsys.readouterr()
            assert 'Test Project' in captured.out

    def test_cmd_show_nonexistent_project(self, mock_multi_project_config):
        """Test showing non-existent project"""
        mock_args = Mock()
        mock_args.config = Path('/tmp/config.yml')
        mock_args.project_id = 'nonexistent'

        with patch('project_manager.load_config', return_value=mock_multi_project_config):
            with pytest.raises(SystemExit):
                pm.cmd_show(mock_args)


class TestCmdAdd:
    """Test add command"""

    def test_cmd_add_valid_project(self, temp_dir):
        """Test adding a valid project"""
        mock_args = Mock()
        mock_args.config = Path('/tmp/config.yml')
        mock_args.id = 'new-project'
        mock_args.name = 'New Project'
        mock_args.type = 'python'
        mock_args.path = str(temp_dir)
        mock_args.repository = 'user/repo'
        mock_args.git_platform = 'github'
        mock_args.test_command = 'pytest'
        mock_args.build_command = None
        mock_args.lint_command = None
        mock_args.format_command = None

        with patch('project_manager.load_config', return_value={'projects': []}):
            with patch('project_manager.save_config') as mock_save:
                pm.cmd_add(mock_args)
                # Verify save was called with updated config
                assert mock_save.called

    def test_cmd_add_duplicate_id(self, mock_multi_project_config):
        """Test adding project with duplicate ID"""
        mock_args = Mock()
        mock_args.config = Path('/tmp/config.yml')
        mock_args.id = 'test-project'  # Already exists

        with patch('project_manager.load_config', return_value=mock_multi_project_config):
            with pytest.raises(SystemExit):
                pm.cmd_add(mock_args)

    def test_cmd_add_invalid_project(self):
        """Test adding invalid project"""
        mock_args = Mock()
        mock_args.config = Path('/tmp/config.yml')
        mock_args.id = 'invalid id!'  # Invalid ID
        mock_args.name = 'Test'
        mock_args.type = 'python'
        mock_args.path = '/nonexistent'
        mock_args.repository = 'repo'
        mock_args.git_platform = 'github'
        mock_args.test_command = 'test'
        mock_args.build_command = None
        mock_args.lint_command = None
        mock_args.format_command = None

        with patch('project_manager.load_config', return_value={'projects': []}):
            with pytest.raises(SystemExit):
                pm.cmd_add(mock_args)


class TestCmdRemove:
    """Test remove command"""

    def test_cmd_remove_with_confirmation(self, mock_multi_project_config):
        """Test removing project with confirmation"""
        mock_args = Mock()
        mock_args.config = Path('/tmp/config.yml')
        mock_args.project_id = 'test-project'
        mock_args.yes = True  # Skip confirmation

        with patch('project_manager.load_config', return_value=mock_multi_project_config):
            with patch('project_manager.save_config') as mock_save:
                pm.cmd_remove(mock_args)
                assert mock_save.called

    def test_cmd_remove_nonexistent(self, mock_multi_project_config):
        """Test removing non-existent project"""
        mock_args = Mock()
        mock_args.config = Path('/tmp/config.yml')
        mock_args.project_id = 'nonexistent'
        mock_args.yes = True

        with patch('project_manager.load_config', return_value=mock_multi_project_config):
            with pytest.raises(SystemExit):
                pm.cmd_remove(mock_args)


class TestCmdEdit:
    """Test edit command"""

    def test_cmd_edit_valid(self, mock_multi_project_config):
        """Test editing project field"""
        mock_args = Mock()
        mock_args.config = Path('/tmp/config.yml')
        mock_args.project_id = 'test-project'
        mock_args.field = 'name'
        mock_args.value = 'Updated Name'
        mock_args.force = False

        with patch('project_manager.load_config', return_value=mock_multi_project_config):
            with patch('project_manager.save_config') as mock_save:
                pm.cmd_edit(mock_args)
                assert mock_save.called

    def test_cmd_edit_nonexistent_project(self, mock_multi_project_config):
        """Test editing non-existent project"""
        mock_args = Mock()
        mock_args.config = Path('/tmp/config.yml')
        mock_args.project_id = 'nonexistent'
        mock_args.field = 'name'
        mock_args.value = 'Value'

        with patch('project_manager.load_config', return_value=mock_multi_project_config):
            with pytest.raises(SystemExit):
                pm.cmd_edit(mock_args)


class TestCmdEnable:
    """Test enable command"""

    def test_cmd_enable_disabled_project(self, mock_multi_project_config):
        """Test enabling a disabled project"""
        mock_args = Mock()
        mock_args.config = Path('/tmp/config.yml')
        mock_args.project_id = 'django-backend'  # This one is disabled

        with patch('project_manager.load_config', return_value=mock_multi_project_config):
            with patch('project_manager.save_config') as mock_save:
                pm.cmd_enable(mock_args)
                assert mock_save.called

    def test_cmd_enable_already_enabled(self, mock_multi_project_config, capsys):
        """Test enabling already enabled project"""
        mock_args = Mock()
        mock_args.config = Path('/tmp/config.yml')
        mock_args.project_id = 'test-project'  # Already enabled

        with patch('project_manager.load_config', return_value=mock_multi_project_config):
            pm.cmd_enable(mock_args)
            captured = capsys.readouterr()
            assert 'already enabled' in captured.out


class TestCmdDisable:
    """Test disable command"""

    def test_cmd_disable_enabled_project(self, mock_multi_project_config):
        """Test disabling an enabled project"""
        mock_args = Mock()
        mock_args.config = Path('/tmp/config.yml')
        mock_args.project_id = 'test-project'

        with patch('project_manager.load_config', return_value=mock_multi_project_config):
            with patch('project_manager.save_config') as mock_save:
                pm.cmd_disable(mock_args)
                assert mock_save.called

    def test_cmd_disable_already_disabled(self, mock_multi_project_config, capsys):
        """Test disabling already disabled project"""
        mock_args = Mock()
        mock_args.config = Path('/tmp/config.yml')
        mock_args.project_id = 'django-backend'  # Already disabled

        with patch('project_manager.load_config', return_value=mock_multi_project_config):
            pm.cmd_disable(mock_args)
            captured = capsys.readouterr()
            assert 'already disabled' in captured.out


class TestMainCLI:
    """Test main CLI entry point"""

    def test_main_no_args(self, capsys):
        """Test main with no arguments shows help"""
        with patch('sys.argv', ['project-manager.py']):
            pm.main()
            # Should print help and exit gracefully

    def test_main_list_command(self):
        """Test main with list command"""
        with patch('sys.argv', ['project-manager.py', 'list']):
            with patch('project_manager.load_config', return_value={}):
                pm.main()
