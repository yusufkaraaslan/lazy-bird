"""Unit tests for TestRunner.

Tests test execution, parsing, error handling, and result formatting.
"""

import subprocess
from pathlib import Path
from unittest.mock import Mock, patch, mock_open

import pytest

from lazy_bird.services.test_runner import (
    GenericTestParser,
    GodotTestParser,
    PythonTestParser,
    RustTestParser,
    TestExecutionError,
    TestRunner,
    TestRunnerError,
)


class TestGodotTestParser:
    """Test Godot test parser."""

    def test_parse_success(self):
        """Test parsing successful Godot test output."""
        parser = GodotTestParser()

        output = """
        Tests: 10 | Passed: 10 | Failed: 0 | Errors: 0
        All tests passed!
        """

        result = parser.parse(output)

        assert result["framework"] == "godot"
        assert result["stats"]["total"] == 10
        assert result["stats"]["passed"] == 10
        assert result["stats"]["failed"] == 0
        assert result["success"] is True
        assert result["error_count"] == 0

    def test_parse_failures(self):
        """Test parsing Godot test failures."""
        parser = GodotTestParser()

        output = """
        Tests: 10 | Passed: 8 | Failed: 2 | Errors: 0
        FAILED: test_player_health Health should start at 100 at res://tests/test_player.gd:42
        FAILED: test_damage Damage should reduce health at res://tests/test_player.gd:56
        """

        result = parser.parse(output)

        assert result["framework"] == "godot"
        assert result["stats"]["failed"] == 2
        assert result["success"] is False
        assert result["error_count"] == 2
        assert len(result["errors"]) == 2

        # Check first error
        error = result["errors"][0]
        assert error["test_name"] == "test_player_health"
        assert error["file"] == "res://tests/test_player.gd"
        assert error["line"] == 42
        assert "Health should start at 100" in error["error"]

    def test_parse_assertion_failures(self):
        """Test parsing Godot assertion failures."""
        parser = GodotTestParser()

        output = """
        Assertion failed: Expected 100, got 50 at res://player.gd:15
        """

        result = parser.parse(output)

        assert result["error_count"] == 1
        assert result["errors"][0]["type"] == "assertion_failure"
        assert result["errors"][0]["line"] == 15


class TestPythonTestParser:
    """Test Python/pytest parser."""

    def test_parse_success(self):
        """Test parsing successful pytest output."""
        parser = PythonTestParser()

        output = """
        ============================= test session starts ==============================
        collected 10 items

        tests/test_player.py .......... [100%]

        ============================== 10 passed in 1.23s ==============================
        """

        result = parser.parse(output)

        assert result["framework"] == "python"
        # Note: Success case doesn't have failed count in output
        assert result["error_count"] == 0

    def test_parse_failures(self):
        """Test parsing pytest failures."""
        parser = PythonTestParser()

        output = """
        FAILED tests/test_player.py::test_health - AssertionError: assert 50 == 100
        FAILED tests/test_player.py::test_damage - AssertionError: damage not applied

        tests/test_player.py:42: in test_health

        ============================== 2 failed, 8 passed in 2.5s ===============================
        """

        result = parser.parse(output)

        assert result["framework"] == "python"
        assert result["stats"]["failed"] == 2
        assert result["stats"]["passed"] == 8
        assert result["success"] is False
        assert result["error_count"] == 2

        # Check errors
        assert len(result["errors"]) == 2
        assert result["errors"][0]["test_name"] == "test_health"
        assert result["errors"][0]["file"] == "tests/test_player.py"


class TestRustTestParser:
    """Test Rust test parser."""

    def test_parse_success(self):
        """Test parsing successful Rust test output."""
        parser = RustTestParser()

        output = """
        running 10 tests
        test result: ok. 10 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out
        """

        result = parser.parse(output)

        assert result["framework"] == "rust"
        assert result["stats"]["passed"] == 10
        assert result["stats"]["failed"] == 0
        assert result["success"] is True

    def test_parse_failures(self):
        """Test parsing Rust test failures."""
        parser = RustTestParser()

        output = """
        ---- tests::test_health stdout ----
        thread 'tests::test_health' panicked at 'assertion failed', src/player.rs:42:5

        test result: FAILED. 8 passed; 2 failed; 0 ignored
        """

        result = parser.parse(output)

        assert result["framework"] == "rust"
        assert result["stats"]["failed"] == 2
        assert result["success"] is False
        assert result["error_count"] == 1  # Only one panic captured

        error = result["errors"][0]
        assert error["test_name"] == "tests::test_health"
        assert error["file"] == "src/player.rs"
        assert error["line"] == 42


class TestGenericTestParser:
    """Test generic test parser."""

    def test_parse_with_failures(self):
        """Test parsing generic output with failures."""
        parser = GenericTestParser()

        output = "Some tests FAILED"

        result = parser.parse(output)

        assert result["framework"] == "generic"
        assert result["success"] is False

    def test_parse_with_errors(self):
        """Test parsing generic output with errors."""
        parser = GenericTestParser()

        output = "ERROR: something went wrong"

        result = parser.parse(output)

        assert result["success"] is False

    def test_parse_success(self):
        """Test parsing generic successful output."""
        parser = GenericTestParser()

        output = "All tests completed successfully"

        result = parser.parse(output)

        assert result["success"] is True


class TestTestRunnerInit:
    """Test TestRunner initialization."""

    def test_init_default_timeout(self):
        """Test TestRunner with default timeout."""
        runner = TestRunner()

        assert runner.timeout == 600

    def test_init_custom_timeout(self):
        """Test TestRunner with custom timeout."""
        runner = TestRunner(timeout=1200)

        assert runner.timeout == 1200


class TestTestRunnerGetParser:
    """Test _get_parser method."""

    def test_get_godot_parser(self):
        """Test getting Godot parser."""
        runner = TestRunner()

        parser = runner._get_parser("godot")

        assert isinstance(parser, GodotTestParser)

    def test_get_python_parser(self):
        """Test getting Python parser."""
        runner = TestRunner()

        for framework in ["python", "pytest", "django", "flask", "fastapi"]:
            parser = runner._get_parser(framework)
            assert isinstance(parser, PythonTestParser)

    def test_get_rust_parser(self):
        """Test getting Rust parser."""
        runner = TestRunner()

        for framework in ["rust", "cargo"]:
            parser = runner._get_parser(framework)
            assert isinstance(parser, RustTestParser)

    def test_get_generic_parser(self):
        """Test fallback to generic parser."""
        runner = TestRunner()

        parser = runner._get_parser("unknown")

        assert isinstance(parser, GenericTestParser)


class TestTestRunnerRunTests:
    """Test run_tests method."""

    def test_run_tests_success(self, tmp_path):
        """Test successful test execution."""
        runner = TestRunner()

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = subprocess.CompletedProcess(
                args=["pytest"],
                returncode=0,
                stdout="10 passed in 1.5s",
                stderr="",
            )

            with patch("builtins.open", mock_open()):
                result = runner.run_tests(
                    test_command="pytest",
                    working_directory=tmp_path,
                    framework="python",
                    project_id="test-proj",
                    task_id=42,
                )

            assert result["success"] is True
            assert result["framework"] == "python"
            assert result["return_code"] == 0
            assert "execution_time" in result
            assert mock_run.called

    def test_run_tests_failure(self, tmp_path):
        """Test failed test execution."""
        runner = TestRunner()

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = subprocess.CompletedProcess(
                args=["pytest"],
                returncode=1,
                stdout="FAILED tests/test.py::test_fail - AssertionError\n2 failed, 8 passed in 2.5s",
                stderr="",
            )

            with patch("builtins.open", mock_open()):
                result = runner.run_tests(
                    test_command="pytest",
                    working_directory=tmp_path,
                    framework="python",
                )

            assert result["success"] is False
            assert result["error_count"] > 0
            assert result["stats"]["failed"] > 0

    def test_run_tests_timeout(self, tmp_path):
        """Test test execution timeout."""
        runner = TestRunner(timeout=1)

        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = subprocess.TimeoutExpired(cmd="pytest", timeout=1)

            with patch("builtins.open", mock_open()):
                result = runner.run_tests(
                    test_command="pytest",
                    working_directory=tmp_path,
                    framework="python",
                )

            assert result["success"] is False
            assert result["error_count"] == 1
            assert "timeout" in result["errors"][0]["type"]

    def test_run_tests_creates_log_file(self, tmp_path):
        """Test that run_tests creates log file."""
        runner = TestRunner()

        log_file = tmp_path / "test.log"

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = subprocess.CompletedProcess(
                args=["pytest"],
                returncode=0,
                stdout="10 passed",
                stderr="",
            )

            result = runner.run_tests(
                test_command="pytest",
                working_directory=tmp_path,
                framework="python",
                log_file=log_file,
            )

            assert log_file.exists()
            content = log_file.read_text()
            assert "Test Execution Log" in content
            assert "pytest" in content
            assert "10 passed" in content

    def test_run_tests_godot_framework(self, tmp_path):
        """Test running Godot tests."""
        runner = TestRunner()

        godot_output = "Tests: 10 | Passed: 10 | Failed: 0 | Errors: 0"

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = subprocess.CompletedProcess(
                args=["godot"],
                returncode=0,
                stdout=godot_output,
                stderr="",
            )

            with patch("builtins.open", mock_open()):
                result = runner.run_tests(
                    test_command="godot --headless -s addons/gdUnit4/bin/GdUnitCmdTool.gd",
                    working_directory=tmp_path,
                    framework="godot",
                )

            assert result["success"] is True
            assert result["framework"] == "godot"
            assert result["stats"]["passed"] == 10


class TestFormatErrorSummary:
    """Test format_error_summary method."""

    def test_format_success(self):
        """Test formatting successful test result."""
        runner = TestRunner()

        test_result = {
            "success": True,
            "framework": "python",
            "stats": {"total": 10, "passed": 10, "failed": 0, "errors": 0},
            "errors": [],
            "error_count": 0,
        }

        summary = runner.format_error_summary(test_result)

        assert "All tests passed" in summary

    def test_format_failures(self):
        """Test formatting failed test result."""
        runner = TestRunner()

        test_result = {
            "success": False,
            "framework": "python",
            "stats": {"total": 10, "passed": 8, "failed": 2, "errors": 0},
            "errors": [
                {
                    "test_name": "test_health",
                    "file": "tests/test_player.py",
                    "line": 42,
                    "error": "AssertionError: assert 50 == 100",
                },
                {
                    "test_name": "test_damage",
                    "file": "tests/test_player.py",
                    "line": 56,
                    "error": "AssertionError: damage not applied",
                },
            ],
            "error_count": 2,
        }

        summary = runner.format_error_summary(test_result)

        assert "Test Summary (python)" in summary
        assert "Total: 10" in summary
        assert "Passed: 8" in summary
        assert "Failed: 2" in summary
        assert "test_health" in summary
        assert "test_damage" in summary
        assert "AssertionError" in summary

    def test_format_many_failures(self):
        """Test formatting with many failures (truncation)."""
        runner = TestRunner()

        # Create 10 errors
        errors = [{"test_name": f"test_{i}", "error": f"Error {i}"} for i in range(10)]

        test_result = {
            "success": False,
            "framework": "python",
            "stats": {"total": 10, "passed": 0, "failed": 10, "errors": 0},
            "errors": errors,
            "error_count": 10,
        }

        summary = runner.format_error_summary(test_result)

        # Should only show first 5 errors
        assert "test_0" in summary
        assert "test_4" in summary
        assert "... and 5 more failures" in summary


class TestTestRunnerErrors:
    """Test TestRunner exception classes."""

    def test_test_execution_error(self):
        """Test TestExecutionError exception."""
        error = TestExecutionError(
            command="pytest",
            return_code=1,
            stderr="Test failed",
            stdout="",
        )

        assert error.command == "pytest"
        assert error.return_code == 1
        assert error.stderr == "Test failed"
        assert "pytest" in str(error)
        assert "Test failed" in str(error)

    def test_test_runner_error(self):
        """Test base TestRunnerError."""
        error = TestRunnerError("Something went wrong")

        assert "Something went wrong" in str(error)
