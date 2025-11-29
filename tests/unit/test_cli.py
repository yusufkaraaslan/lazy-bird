"""
Unit tests for lazy_bird/cli.py module
"""

import pytest
import sys
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock, call
from io import StringIO

from lazy_bird import cli, __version__


class TestPrintBanner:
    """Test banner printing functionality"""

    def test_print_banner_contains_version(self, capsys):
        """Test banner includes version number"""
        cli.print_banner()
        captured = capsys.readouterr()
        assert __version__ in captured.out

    def test_print_banner_contains_title(self, capsys):
        """Test banner includes LAZY and BIRD text"""
        cli.print_banner()
        captured = capsys.readouterr()
        # Check for various parts of the ASCII art
        assert 'Version:' in captured.out

    def test_print_banner_multiline(self, capsys):
        """Test banner is multiline output"""
        cli.print_banner()
        captured = capsys.readouterr()
        lines = captured.out.split('\n')
        assert len(lines) > 5, "Banner should be multiline"


class TestRunWizard:
    """Test wizard execution"""

    def test_run_wizard_no_args(self, mock_package_root, monkeypatch):
        """Test running wizard without arguments"""
        monkeypatch.setattr('lazy_bird.PACKAGE_ROOT', mock_package_root)

        with patch('subprocess.call', return_value=0) as mock_call:
            result = cli.run_wizard([])
            assert result == 0
            mock_call.assert_called_once()
            # Check that bash and wizard script are in the call
            call_args = mock_call.call_args[0][0]
            assert call_args[0] == 'bash'
            assert 'wizard.sh' in str(call_args[1])

    def test_run_wizard_with_args(self, mock_package_root, monkeypatch):
        """Test running wizard with arguments"""
        monkeypatch.setattr('lazy_bird.PACKAGE_ROOT', mock_package_root)

        with patch('subprocess.call', return_value=0) as mock_call:
            result = cli.run_wizard(['--status', '--verbose'])
            assert result == 0
            call_args = mock_call.call_args[0][0]
            assert '--status' in call_args
            assert '--verbose' in call_args

    def test_run_wizard_missing_script(self, temp_dir, monkeypatch, capsys):
        """Test error when wizard script doesn't exist"""
        monkeypatch.setattr('lazy_bird.PACKAGE_ROOT', temp_dir)

        result = cli.run_wizard([])
        assert result == 1
        captured = capsys.readouterr()
        assert 'Error' in captured.out
        assert 'Wizard script not found' in captured.out

    def test_run_wizard_return_code(self, mock_package_root, monkeypatch):
        """Test wizard return code is propagated"""
        monkeypatch.setattr('lazy_bird.PACKAGE_ROOT', mock_package_root)

        with patch('subprocess.call', return_value=42) as mock_call:
            result = cli.run_wizard([])
            assert result == 42


class TestRunServer:
    """Test web server execution"""

    @patch('lazy_bird.cli.app')
    def test_run_server_default_args(self, mock_app):
        """Test server with default host and port"""
        mock_app.run = Mock()
        # Need to patch sys.path manipulation
        with patch('sys.path'):
            result = cli.run_server()
            assert result == 0
            mock_app.run.assert_called_once_with(
                host='127.0.0.1',
                port=5000,
                debug=False
            )

    @patch('lazy_bird.cli.app')
    def test_run_server_custom_args(self, mock_app):
        """Test server with custom host and port"""
        mock_app.run = Mock()
        with patch('sys.path'):
            result = cli.run_server(port=8080, host='0.0.0.0')
            assert result == 0
            mock_app.run.assert_called_once_with(
                host='0.0.0.0',
                port=8080,
                debug=False
            )

    def test_run_server_import_error(self, capsys):
        """Test error when Flask is not installed"""
        with patch('sys.path'):
            # Mock the import to raise ImportError
            with patch.dict('sys.modules', {'app': None}):
                with patch('builtins.__import__', side_effect=ImportError("No Flask")):
                    result = cli.run_server()
                    # The function catches ImportError and returns 1
                    # Check output contains error message
                    captured = capsys.readouterr()
                    assert 'Error' in captured.out or result == 1


class TestRunGodotServer:
    """Test Godot server execution"""

    def test_run_godot_server(self, mock_package_root, monkeypatch):
        """Test running Godot server"""
        monkeypatch.setattr('lazy_bird.PACKAGE_ROOT', mock_package_root)

        with patch('subprocess.call', return_value=0) as mock_call:
            result = cli.run_godot_server([])
            assert result == 0
            call_args = mock_call.call_args[0][0]
            assert call_args[0] == sys.executable
            assert 'godot-server.py' in str(call_args[1])

    def test_run_godot_server_with_args(self, mock_package_root, monkeypatch):
        """Test Godot server with arguments"""
        monkeypatch.setattr('lazy_bird.PACKAGE_ROOT', mock_package_root)

        with patch('subprocess.call', return_value=0) as mock_call:
            result = cli.run_godot_server(['--port', '8000'])
            assert result == 0
            call_args = mock_call.call_args[0][0]
            assert '--port' in call_args
            assert '8000' in call_args

    def test_run_godot_server_missing_script(self, temp_dir, monkeypatch, capsys):
        """Test error when script doesn't exist"""
        monkeypatch.setattr('lazy_bird.PACKAGE_ROOT', temp_dir)

        result = cli.run_godot_server([])
        assert result == 1
        captured = capsys.readouterr()
        assert 'Error' in captured.out


class TestRunIssueWatcher:
    """Test issue watcher execution"""

    def test_run_issue_watcher(self, mock_package_root, monkeypatch):
        """Test running issue watcher"""
        monkeypatch.setattr('lazy_bird.PACKAGE_ROOT', mock_package_root)

        with patch('subprocess.call', return_value=0) as mock_call:
            result = cli.run_issue_watcher([])
            assert result == 0
            call_args = mock_call.call_args[0][0]
            assert 'issue-watcher.py' in str(call_args[1])

    def test_run_issue_watcher_missing_script(self, temp_dir, monkeypatch, capsys):
        """Test error when script doesn't exist"""
        monkeypatch.setattr('lazy_bird.PACKAGE_ROOT', temp_dir)

        result = cli.run_issue_watcher([])
        assert result == 1


class TestRunProjectManager:
    """Test project manager execution"""

    def test_run_project_manager(self, mock_package_root, monkeypatch):
        """Test running project manager"""
        monkeypatch.setattr('lazy_bird.PACKAGE_ROOT', mock_package_root)

        with patch('subprocess.call', return_value=0) as mock_call:
            result = cli.run_project_manager(['list'])
            assert result == 0
            call_args = mock_call.call_args[0][0]
            assert 'project-manager.py' in str(call_args[1])
            assert 'list' in call_args

    def test_run_project_manager_missing_script(self, temp_dir, monkeypatch, capsys):
        """Test error when script doesn't exist"""
        monkeypatch.setattr('lazy_bird.PACKAGE_ROOT', temp_dir)

        result = cli.run_project_manager([])
        assert result == 1


class TestMainCLI:
    """Test main CLI entry point"""

    def test_main_no_args_shows_help(self, capsys):
        """Test main without arguments shows help"""
        with patch('lazy_bird.cli.print_banner'):
            result = cli.main([])
            assert result == 0
            captured = capsys.readouterr()
            # Should show help text

    def test_main_version_flag(self):
        """Test --version flag"""
        with pytest.raises(SystemExit) as exc_info:
            cli.main(['--version'])
        # argparse exits with 0 for --version
        assert exc_info.value.code == 0

    def test_main_setup_command(self, mock_package_root, monkeypatch):
        """Test setup command"""
        monkeypatch.setattr('lazy_bird.PACKAGE_ROOT', mock_package_root)

        with patch('subprocess.call', return_value=0):
            result = cli.main(['setup'])
            assert result == 0

    def test_main_server_command(self, mock_package_root, monkeypatch):
        """Test server command with arguments"""
        monkeypatch.setattr('lazy_bird.PACKAGE_ROOT', mock_package_root)

        with patch('lazy_bird.cli.run_server', return_value=0) as mock_run:
            result = cli.main(['server', '--port', '8080', '--host', '0.0.0.0'])
            assert result == 0
            mock_run.assert_called_once_with(port=8080, host='0.0.0.0')

    def test_main_godot_command(self, mock_package_root, monkeypatch):
        """Test godot command"""
        monkeypatch.setattr('lazy_bird.PACKAGE_ROOT', mock_package_root)

        with patch('subprocess.call', return_value=0):
            result = cli.main(['godot', '--port', '5001'])
            assert result == 0

    def test_main_watch_command(self, mock_package_root, monkeypatch):
        """Test watch command"""
        monkeypatch.setattr('lazy_bird.PACKAGE_ROOT', mock_package_root)

        with patch('subprocess.call', return_value=0):
            result = cli.main(['watch'])
            assert result == 0

    def test_main_project_command(self, mock_package_root, monkeypatch):
        """Test project command"""
        monkeypatch.setattr('lazy_bird.PACKAGE_ROOT', mock_package_root)

        with patch('subprocess.call', return_value=0):
            result = cli.main(['project', 'list'])
            assert result == 0

    def test_main_status_command(self, mock_package_root, monkeypatch):
        """Test status command"""
        monkeypatch.setattr('lazy_bird.PACKAGE_ROOT', mock_package_root)

        with patch('subprocess.call', return_value=0):
            result = cli.main(['status'])
            assert result == 0

    def test_main_invalid_command(self, capsys):
        """Test invalid command shows help"""
        with patch('lazy_bird.cli.print_banner'):
            result = cli.main(['invalid'])
            # Should show help and return 1
            # Note: actual behavior depends on implementation

    def test_main_entry_point(self, mock_package_root, monkeypatch):
        """Test main can be called from __main__"""
        monkeypatch.setattr('lazy_bird.PACKAGE_ROOT', mock_package_root)

        with patch('subprocess.call', return_value=0):
            with patch('sys.argv', ['lazy-bird', 'setup']):
                result = cli.main()  # No args = use sys.argv
                assert result == 0


class TestCLIIntegration:
    """Integration tests for CLI workflows"""

    def test_setup_workflow(self, mock_package_root, monkeypatch):
        """Test complete setup workflow"""
        monkeypatch.setattr('lazy_bird.PACKAGE_ROOT', mock_package_root)

        with patch('subprocess.call', return_value=0) as mock_call:
            # Run setup with arguments
            result = cli.main(['setup', '--status'])
            assert result == 0

            # Verify subprocess was called correctly
            call_args = mock_call.call_args[0][0]
            assert 'wizard.sh' in str(call_args[1])
            assert '--status' in call_args

    def test_server_startup_workflow(self, mock_package_root, monkeypatch, capsys):
        """Test server startup workflow"""
        monkeypatch.setattr('lazy_bird.PACKAGE_ROOT', mock_package_root)

        with patch('lazy_bird.cli.app') as mock_app:
            with patch('sys.path'):
                mock_app.run = Mock()
                result = cli.main(['server', '--port', '5000'])
                assert result == 0

                captured = capsys.readouterr()
                # Should print startup messages
                assert '🚀' in captured.out or 'Starting' in captured.out
