"""Additional unit tests for ClaudeService execute_claude edge cases.

Covers lines 220-232 (generic exception handling in execute_claude).
"""

import subprocess
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

from lazy_bird.services.claude_service import (
    ClaudeService,
    ClaudeServiceError,
)


class TestExecuteClaudeGenericException:
    """Test execute_claude generic exception path (lines 220-232)."""

    def test_execute_claude_generic_exception(self, tmp_path):
        """Test that generic exceptions are wrapped in ClaudeServiceError."""
        service = ClaudeService(
            api_key="test-key",
            model="claude-sonnet-4",
            max_tokens=4096,
            temperature=0.7,
        )

        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = OSError("No such file or directory: 'claude'")

            with pytest.raises(ClaudeServiceError) as exc_info:
                service.execute_claude(
                    prompt="Add health system",
                    working_directory=tmp_path,
                    project_id="test-proj",
                    task_id=42,
                )

            assert "Unexpected error" in str(exc_info.value)
            assert "No such file or directory" in str(exc_info.value)

    def test_execute_claude_permission_error(self, tmp_path):
        """Test that PermissionError is wrapped in ClaudeServiceError."""
        service = ClaudeService(
            api_key="test-key",
            model="claude-sonnet-4",
            max_tokens=4096,
            temperature=0.7,
        )

        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = PermissionError("Permission denied")

            with pytest.raises(ClaudeServiceError) as exc_info:
                service.execute_claude(
                    prompt="test",
                    working_directory=tmp_path,
                )

            assert "Unexpected error" in str(exc_info.value)


class TestGetSettings:
    """Test _get_settings lazy import."""

    def test_get_settings_returns_settings(self):
        """Test that _get_settings returns the settings singleton."""
        from lazy_bird.services.claude_service import _get_settings

        settings = _get_settings()

        # Should return the settings object
        assert settings is not None
        assert hasattr(settings, "CLAUDE_API_KEY")
