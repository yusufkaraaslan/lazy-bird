"""Unit tests for ClaudeService.

Tests Claude Code CLI execution, output parsing, token tracking, and error handling.
"""

import json
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch, mock_open

import pytest

from lazy_bird.services.claude_service import (
    ClaudeExecutionError,
    ClaudeService,
    ClaudeServiceError,
    ClaudeTimeoutError,
)


class TestClaudeServiceInit:
    """Test ClaudeService initialization."""

    def test_init_with_defaults(self):
        """Test ClaudeService initialization with default settings."""
        with patch("lazy_bird.services.claude_service._get_settings") as mock_get_settings:
            mock_settings = Mock()
            mock_settings.CLAUDE_API_KEY = "test-key"
            mock_settings.CLAUDE_MODEL = "claude-sonnet-4"
            mock_settings.CLAUDE_MAX_TOKENS = 4096
            mock_settings.CLAUDE_TEMPERATURE = 0.7
            mock_get_settings.return_value = mock_settings

            service = ClaudeService()

            assert service.api_key == "test-key"
            assert service.model == "claude-sonnet-4"
            assert service.max_tokens == 4096
            assert service.temperature == 0.7
            assert service.timeout == 600

    def test_init_with_custom_settings(self):
        """Test ClaudeService with custom settings."""
        service = ClaudeService(
            api_key="custom-key",
            model="claude-opus-4",
            max_tokens=8192,
            temperature=0.5,
            timeout=1200,
        )

        assert service.api_key == "custom-key"
        assert service.model == "claude-opus-4"
        assert service.max_tokens == 8192
        assert service.temperature == 0.5
        assert service.timeout == 1200

    def test_init_without_api_key(self):
        """Test ClaudeService fails without API key."""
        with patch("lazy_bird.services.claude_service._get_settings") as mock_get_settings:
            mock_settings = Mock()
            mock_settings.CLAUDE_API_KEY = None
            mock_settings.CLAUDE_MODEL = "claude-sonnet-4"
            mock_settings.CLAUDE_MAX_TOKENS = 4096
            mock_settings.CLAUDE_TEMPERATURE = 0.7
            mock_get_settings.return_value = mock_settings

            with pytest.raises(ClaudeServiceError) as exc_info:
                ClaudeService()

            assert "API key not configured" in str(exc_info.value)


class TestBuildPrompt:
    """Test _build_prompt method."""

    def test_build_prompt_without_error_context(self):
        """Test building prompt without error context."""
        service = ClaudeService(
            api_key="test-key",
            model="claude-sonnet-4",
            max_tokens=4096,
            temperature=0.7,
        )

        prompt = service._build_prompt("Add health system", None)

        assert prompt == "Add health system"

    def test_build_prompt_with_error_context(self):
        """Test building prompt with error context for retry."""
        service = ClaudeService(
            api_key="test-key", model="claude-sonnet-4", max_tokens=4096, temperature=0.7
        )

        error_context = "TypeError: 'NoneType' object is not callable"
        prompt = service._build_prompt("Add health system", error_context)

        assert "Add health system" in prompt
        assert "Previous Attempt Error" in prompt
        assert error_context in prompt
        assert "Please fix the issues above" in prompt


class TestBuildCommand:
    """Test _build_command method."""

    def test_build_command(self, tmp_path):
        """Test building Claude CLI command."""
        service = ClaudeService(
            api_key="test-key",
            model="claude-sonnet-4",
            max_tokens=4096,
            temperature=0.7,
        )

        command = service._build_command("Test prompt", tmp_path)

        assert command[0] == "claude"
        assert "-p" in command
        assert "Test prompt" in command
        assert "--model" in command
        assert "claude-sonnet-4" in command
        assert "--max-tokens" in command
        assert "4096" in command
        assert "--temperature" in command
        assert "0.7" in command
        assert "--output-format" in command
        assert "json" in command


class TestConstructTaskPrompt:
    """Test construct_task_prompt method."""

    def test_construct_task_prompt(self, tmp_path):
        """Test constructing detailed task prompt."""
        service = ClaudeService(
            api_key="test-key", model="claude-sonnet-4", max_tokens=4096, temperature=0.7
        )

        prompt = service.construct_task_prompt(
            project_name="My Game",
            project_type="godot",
            project_id="my-game",
            task_title="Add player health",
            task_body="Implement health system with 100 max HP",
            working_directory=tmp_path,
        )

        assert "My Game" in prompt
        assert "godot" in prompt
        assert "my-game" in prompt
        assert "Add player health" in prompt
        assert "Implement health system with 100 max HP" in prompt
        assert str(tmp_path) in prompt
        assert "DO NOT" in prompt
        assert "git commit" in prompt


class TestExtractTokens:
    """Test _extract_tokens_from_text method."""

    def test_extract_tokens_pattern_1(self):
        """Test extracting tokens from 'total tokens: 1234' pattern."""
        service = ClaudeService(
            api_key="test-key", model="claude-sonnet-4", max_tokens=4096, temperature=0.7
        )

        text = "Execution completed. Total tokens: 1234"
        tokens = service._extract_tokens_from_text(text)

        assert tokens == 1234

    def test_extract_tokens_pattern_2(self):
        """Test extracting tokens from 'tokens used: 5678' pattern."""
        service = ClaudeService(
            api_key="test-key", model="claude-sonnet-4", max_tokens=4096, temperature=0.7
        )

        text = "Usage: Tokens used: 5678"
        tokens = service._extract_tokens_from_text(text)

        assert tokens == 5678

    def test_extract_tokens_pattern_3(self):
        """Test extracting tokens from '9012 tokens' pattern."""
        service = ClaudeService(
            api_key="test-key", model="claude-sonnet-4", max_tokens=4096, temperature=0.7
        )

        text = "Processed 9012 tokens successfully"
        tokens = service._extract_tokens_from_text(text)

        assert tokens == 9012

    def test_extract_tokens_not_found(self):
        """Test extracting tokens when pattern not found."""
        service = ClaudeService(
            api_key="test-key", model="claude-sonnet-4", max_tokens=4096, temperature=0.7
        )

        text = "No token information here"
        tokens = service._extract_tokens_from_text(text)

        assert tokens == 0


class TestCalculateCost:
    """Test _calculate_cost method."""

    def test_calculate_cost_zero_tokens(self):
        """Test cost calculation with zero tokens."""
        service = ClaudeService(
            api_key="test-key", model="claude-sonnet-4", max_tokens=4096, temperature=0.7
        )

        cost = service._calculate_cost(0)

        assert cost == 0.0

    def test_calculate_cost_1000_tokens(self):
        """Test cost calculation with 1000 tokens."""
        service = ClaudeService(
            api_key="test-key", model="claude-sonnet-4", max_tokens=4096, temperature=0.7
        )

        cost = service._calculate_cost(1000)

        # Expected: (1000 / 1000) * 0.016 = 0.016
        assert cost == pytest.approx(0.016, rel=1e-3)

    def test_calculate_cost_5000_tokens(self):
        """Test cost calculation with 5000 tokens."""
        service = ClaudeService(
            api_key="test-key", model="claude-sonnet-4", max_tokens=4096, temperature=0.7
        )

        cost = service._calculate_cost(5000)

        # Expected: (5000 / 1000) * 0.016 = 0.08
        assert cost == pytest.approx(0.08, rel=1e-3)


class TestParseOutput:
    """Test _parse_output method."""

    def test_parse_output_json_format(self):
        """Test parsing JSON output from Claude."""
        service = ClaudeService(
            api_key="test-key", model="claude-sonnet-4", max_tokens=4096, temperature=0.7
        )

        result = subprocess.CompletedProcess(
            args=["claude"],
            returncode=0,
            stdout=json.dumps(
                {
                    "output": "Task completed successfully",
                    "usage": {"total_tokens": 1234},
                }
            ),
            stderr="",
        )

        from datetime import datetime, timezone

        start_time = datetime.now(timezone.utc)

        parsed = service._parse_output(result, start_time, "/tmp/test.log")

        assert parsed["success"] is True
        assert parsed["output"] == "Task completed successfully"
        assert parsed["tokens_used"] == 1234
        assert parsed["cost"] == pytest.approx(0.01974, rel=1e-3)
        assert parsed["log_file"] == "/tmp/test.log"
        assert parsed["return_code"] == 0

    def test_parse_output_plain_text(self):
        """Test parsing plain text output."""
        service = ClaudeService(
            api_key="test-key", model="claude-sonnet-4", max_tokens=4096, temperature=0.7
        )

        result = subprocess.CompletedProcess(
            args=["claude"],
            returncode=0,
            stdout="Task completed. Total tokens: 2500",
            stderr="",
        )

        from datetime import datetime, timezone

        start_time = datetime.now(timezone.utc)

        parsed = service._parse_output(result, start_time, "/tmp/test.log")

        assert parsed["success"] is True
        assert "Task completed" in parsed["output"]
        assert parsed["tokens_used"] == 2500
        assert parsed["cost"] > 0

    def test_parse_output_failure(self):
        """Test parsing output from failed execution."""
        service = ClaudeService(
            api_key="test-key", model="claude-sonnet-4", max_tokens=4096, temperature=0.7
        )

        result = subprocess.CompletedProcess(
            args=["claude"],
            returncode=1,
            stdout="",
            stderr="Error: API key invalid",
        )

        from datetime import datetime, timezone

        start_time = datetime.now(timezone.utc)

        parsed = service._parse_output(result, start_time, "/tmp/test.log")

        assert parsed["success"] is False
        assert parsed["error"] == "Error: API key invalid"
        assert parsed["return_code"] == 1


class TestWriteLog:
    """Test _write_log method."""

    def test_write_log(self, tmp_path):
        """Test writing execution log to file."""
        service = ClaudeService(
            api_key="test-key", model="claude-sonnet-4", max_tokens=4096, temperature=0.7
        )

        log_file = tmp_path / "test.log"
        command = ["claude", "-p", "Test prompt"]
        result = subprocess.CompletedProcess(
            args=command,
            returncode=0,
            stdout="Success output",
            stderr="",
        )

        from datetime import datetime, timezone

        start_time = datetime.now(timezone.utc)

        service._write_log(log_file, command, result, start_time)

        assert log_file.exists()
        content = log_file.read_text()
        assert "Claude Code CLI Execution Log" in content
        assert "Return Code: 0" in content
        assert "claude -p Test prompt" in content
        assert "Success output" in content


class TestExecuteClaude:
    """Test execute_claude method."""

    def test_execute_claude_success(self, tmp_path):
        """Test successful Claude execution."""
        service = ClaudeService(
            api_key="test-key",
            model="claude-sonnet-4",
            max_tokens=4096,
            temperature=0.7,
            timeout=10,
        )

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = subprocess.CompletedProcess(
                args=["claude"],
                returncode=0,
                stdout=json.dumps(
                    {
                        "output": "Implementation complete",
                        "usage": {"total_tokens": 1500},
                    }
                ),
                stderr="",
            )

            with patch.object(service, "_write_log"):
                result = service.execute_claude(
                    prompt="Add health system",
                    working_directory=tmp_path,
                    project_id="test-proj",
                    task_id=42,
                )

            assert result["success"] is True
            assert result["output"] == "Implementation complete"
            assert result["tokens_used"] == 1500
            assert result["cost"] > 0
            assert mock_run.called

    def test_execute_claude_with_error_context(self, tmp_path):
        """Test Claude execution with error context (retry)."""
        service = ClaudeService(
            api_key="test-key", model="claude-sonnet-4", max_tokens=4096, temperature=0.7
        )

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = subprocess.CompletedProcess(
                args=["claude"],
                returncode=0,
                stdout=json.dumps({"output": "Fixed", "usage": {"total_tokens": 800}}),
                stderr="",
            )

            with patch.object(service, "_write_log"):
                result = service.execute_claude(
                    prompt="Add health system",
                    working_directory=tmp_path,
                    error_context="TypeError: previous error",
                )

            # Verify prompt includes error context
            call_args = mock_run.call_args
            executed_command = call_args[0][0]
            prompt_index = executed_command.index("-p") + 1
            executed_prompt = executed_command[prompt_index]

            assert "Previous Attempt Error" in executed_prompt
            assert "TypeError: previous error" in executed_prompt

    def test_execute_claude_timeout(self, tmp_path):
        """Test Claude execution timeout."""
        service = ClaudeService(
            api_key="test-key",
            model="claude-sonnet-4",
            max_tokens=4096,
            temperature=0.7,
            timeout=1,
        )

        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = subprocess.TimeoutExpired(cmd="claude", timeout=1)

            with pytest.raises(ClaudeTimeoutError):
                service.execute_claude(
                    prompt="Add health system",
                    working_directory=tmp_path,
                )

    def test_execute_claude_failure(self, tmp_path):
        """Test Claude execution returning non-zero exit code."""
        service = ClaudeService(
            api_key="test-key", model="claude-sonnet-4", max_tokens=4096, temperature=0.7
        )

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = subprocess.CompletedProcess(
                args=["claude"],
                returncode=1,
                stdout="",
                stderr="API error: Rate limit exceeded",
            )

            with patch.object(service, "_write_log"):
                result = service.execute_claude(
                    prompt="Add health system",
                    working_directory=tmp_path,
                )

            assert result["success"] is False
            assert "Rate limit exceeded" in result["error"]

    def test_execute_claude_creates_log_directory(self, tmp_path):
        """Test that execute_claude creates log directory if needed."""
        service = ClaudeService(
            api_key="test-key", model="claude-sonnet-4", max_tokens=4096, temperature=0.7
        )

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = subprocess.CompletedProcess(
                args=["claude"],
                returncode=0,
                stdout=json.dumps({"output": "Done", "usage": {"total_tokens": 500}}),
                stderr="",
            )

            # Use a custom log file in tmp_path to avoid using default /tmp/lazy-bird-logs
            log_file = tmp_path / "logs" / "claude" / "test.log"

            with patch("builtins.open", mock_open()):
                result = service.execute_claude(
                    prompt="Test",
                    working_directory=tmp_path,
                    project_id="proj",
                    task_id=1,
                    log_file=log_file,
                )

            # Verify result is successful
            assert result["success"] is True


class TestClaudeServiceErrors:
    """Test ClaudeService exception classes."""

    def test_claude_execution_error(self):
        """Test ClaudeExecutionError exception."""
        error = ClaudeExecutionError(
            command="claude -p 'test'",
            return_code=1,
            stderr="API error",
            stdout="partial output",
        )

        assert error.command == "claude -p 'test'"
        assert error.return_code == 1
        assert error.stderr == "API error"
        assert error.stdout == "partial output"
        assert "claude -p 'test'" in str(error)
        assert "API error" in str(error)

    def test_claude_timeout_error(self):
        """Test ClaudeTimeoutError exception."""
        error = ClaudeTimeoutError("Execution timed out after 600s")

        assert "timed out" in str(error)
        assert isinstance(error, ClaudeServiceError)

    def test_claude_service_error(self):
        """Test base ClaudeServiceError."""
        error = ClaudeServiceError("Something went wrong")

        assert "Something went wrong" in str(error)
