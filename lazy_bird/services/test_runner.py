"""Test runner service for executing and parsing tests across frameworks.

This module provides the TestRunner class for executing tests for different
frameworks (Godot, Python, Rust, etc.), parsing results, and handling failures.
"""

import json
import logging
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, Optional, List

logger = logging.getLogger(__name__)


class TestRunnerError(Exception):
    """Base exception for test runner errors."""

    pass


class TestExecutionError(TestRunnerError):
    """Exception raised when test execution fails unexpectedly."""

    def __init__(self, command: str, return_code: int, stderr: str, stdout: str = ""):
        self.command = command
        self.return_code = return_code
        self.stderr = stderr
        self.stdout = stdout
        super().__init__(
            f"Test execution failed with code {return_code}:\n"
            f"Command: {command}\n"
            f"Error: {stderr}"
        )


class TestParser:
    """Base class for test output parsing."""

    def parse(self, log_content: str) -> Dict[str, Any]:
        """Parse test log and return structured results."""
        raise NotImplementedError


class GodotTestParser(TestParser):
    """Parser for Godot gdUnit4 test output."""

    def parse(self, log_content: str) -> Dict[str, Any]:
        """Parse Godot test errors with file/line extraction."""
        errors = []
        stats = {"total": 0, "passed": 0, "failed": 0, "errors": 0}

        # Extract test statistics
        stats_pattern = r'Tests:\s*(\d+)\s*\|\s*Passed:\s*(\d+)\s*\|\s*Failed:\s*(\d+)\s*\|\s*Errors:\s*(\d+)'
        stats_match = re.search(stats_pattern, log_content)
        if stats_match:
            stats = {
                "total": int(stats_match.group(1)),
                "passed": int(stats_match.group(2)),
                "failed": int(stats_match.group(3)),
                "errors": int(stats_match.group(4)),
            }

        # Extract failed tests with details
        failed_pattern = r'FAILED:\s+(\S+)\s+(.*?)\s+at\s+(res://[^:]+):(\d+)'
        for match in re.finditer(failed_pattern, log_content, re.DOTALL):
            test_name = match.group(1)
            error_msg = match.group(2).strip()
            file_path = match.group(3)
            line_number = int(match.group(4))

            errors.append({
                "test_name": test_name,
                "file": file_path,
                "line": line_number,
                "error": error_msg,
                "type": "test_failure",
            })

        # Capture assertion failures
        assert_pattern = r'Assertion\s+failed:?\s+(.*?)\s+at\s+(res://[^:]+):(\d+)'
        for match in re.finditer(assert_pattern, log_content):
            error_msg = match.group(1).strip()
            file_path = match.group(2)
            line_number = int(match.group(3))

            errors.append({
                "test_name": "assertion",
                "file": file_path,
                "line": line_number,
                "error": error_msg,
                "type": "assertion_failure",
            })

        return {
            "framework": "godot",
            "stats": stats,
            "errors": errors,
            "error_count": len(errors),
            "success": stats["failed"] == 0 and stats["errors"] == 0,
        }


class PythonTestParser(TestParser):
    """Parser for Python pytest output."""

    def parse(self, log_content: str) -> Dict[str, Any]:
        """Parse pytest errors with stack trace extraction."""
        errors = []
        stats = {"total": 0, "passed": 0, "failed": 0, "errors": 0}

        # Extract test statistics
        stats_pattern = r'(\d+)\s+failed.*?(\d+)\s+passed'
        stats_match = re.search(stats_pattern, log_content)
        if stats_match:
            stats["failed"] = int(stats_match.group(1))
            stats["passed"] = int(stats_match.group(2))
            stats["total"] = stats["failed"] + stats["passed"]

        # Extract failed tests
        failed_pattern = r'FAILED\s+([^:]+)::(\S+)\s+-\s+(.*?)$'
        for match in re.finditer(failed_pattern, log_content, re.MULTILINE):
            file_path = match.group(1)
            test_name = match.group(2)
            error_msg = match.group(3).strip()

            # Try to extract line number from stack trace
            line_number = None
            stack_pattern = rf'{re.escape(file_path)}:(\d+):'
            stack_match = re.search(stack_pattern, log_content)
            if stack_match:
                line_number = int(stack_match.group(1))

            errors.append({
                "test_name": test_name,
                "file": file_path,
                "line": line_number,
                "error": error_msg,
                "type": "test_failure",
            })

        return {
            "framework": "python",
            "stats": stats,
            "errors": errors,
            "error_count": len(errors),
            "success": stats["failed"] == 0,
        }


class RustTestParser(TestParser):
    """Parser for Rust cargo test output."""

    def parse(self, log_content: str) -> Dict[str, Any]:
        """Parse Rust test errors."""
        errors = []
        stats = {"total": 0, "passed": 0, "failed": 0, "errors": 0}

        # Extract test statistics
        stats_pattern = r'test\s+result:.*?(\d+)\s+passed;\s+(\d+)\s+failed'
        stats_match = re.search(stats_pattern, log_content)
        if stats_match:
            stats["passed"] = int(stats_match.group(1))
            stats["failed"] = int(stats_match.group(2))
            stats["total"] = stats["passed"] + stats["failed"]

        # Extract failed tests with panic info
        test_pattern = r'----\s+([\w:]+)\s+stdout\s+----\s+(.*?)(?=\n\n|$)'
        for match in re.finditer(test_pattern, log_content, re.DOTALL):
            test_name = match.group(1)
            output = match.group(2)

            # Extract file and line from panic
            panic_pattern = r"panicked at '([^']+)',\s+([^:]+):(\d+):\d+"
            panic_match = re.search(panic_pattern, output)

            if panic_match:
                error_msg = panic_match.group(1)
                file_path = panic_match.group(2)
                line_number = int(panic_match.group(3))

                errors.append({
                    "test_name": test_name,
                    "file": file_path,
                    "line": line_number,
                    "error": error_msg,
                    "type": "panic",
                })

        return {
            "framework": "rust",
            "stats": stats,
            "errors": errors,
            "error_count": len(errors),
            "success": stats["failed"] == 0,
        }


class GenericTestParser(TestParser):
    """Generic parser for unknown frameworks."""

    def parse(self, log_content: str) -> Dict[str, Any]:
        """Basic parsing - just check for common failure patterns."""
        # Look for common failure indicators
        has_failures = any([
            re.search(r'\bFAILED\b', log_content, re.IGNORECASE),
            re.search(r'\bERROR\b', log_content, re.IGNORECASE),
            re.search(r'\bFAIL\b', log_content),
        ])

        return {
            "framework": "generic",
            "stats": {"total": 0, "passed": 0, "failed": 0, "errors": 0},
            "errors": [],
            "error_count": 0,
            "success": not has_failures,
            "raw_output": log_content,
        }


class TestRunner:
    """Service for running tests across different frameworks.

    Executes test commands, parses output, and handles failures.
    """

    # Map framework types to parsers
    PARSERS = {
        "godot": GodotTestParser(),
        "python": PythonTestParser(),
        "pytest": PythonTestParser(),
        "django": PythonTestParser(),
        "flask": PythonTestParser(),
        "fastapi": PythonTestParser(),
        "rust": RustTestParser(),
        "cargo": RustTestParser(),
    }

    def __init__(self, timeout: int = 600):
        """Initialize TestRunner.

        Args:
            timeout: Test execution timeout in seconds (default: 600)
        """
        self.timeout = timeout

    def run_tests(
        self,
        test_command: str,
        working_directory: Path,
        framework: str,
        project_id: Optional[str] = None,
        task_id: Optional[int] = None,
        log_file: Optional[Path] = None,
    ) -> Dict[str, Any]:
        """Execute tests and parse results.

        Args:
            test_command: Command to execute tests
            working_directory: Directory to run tests in
            framework: Framework type (godot, python, rust, etc.)
            project_id: Project identifier for logging
            task_id: Task ID for logging
            log_file: Path to save test output

        Returns:
            dict: Test results
                - success: bool
                - framework: str
                - stats: dict (total, passed, failed, errors)
                - errors: list of error details
                - output: str (test command output)
                - execution_time: float (seconds)
                - log_file: str (path to log file)

        Raises:
            TestExecutionError: If test execution fails unexpectedly
        """
        start_time = datetime.now(timezone.utc)

        # Determine log file path
        if log_file is None:
            log_dir = Path("/tmp/lazy-bird-logs") / "tests"
            log_dir.mkdir(parents=True, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            prefix = f"{project_id}-{task_id}" if project_id and task_id else "test"
            log_file = log_dir / f"{prefix}_{timestamp}.log"

        logger.info(
            f"Running tests",
            extra={
                "extra_fields": {
                    "project_id": project_id,
                    "task_id": task_id,
                    "framework": framework,
                    "command": test_command,
                    "working_directory": str(working_directory),
                    "log_file": str(log_file),
                }
            },
        )

        try:
            # Execute test command
            result = subprocess.run(
                test_command,
                cwd=working_directory,
                shell=True,
                capture_output=True,
                text=True,
                timeout=self.timeout,
            )

            # Write output to log file
            with open(log_file, "w") as f:
                f.write("=" * 80 + "\n")
                f.write("Test Execution Log\n")
                f.write("=" * 80 + "\n\n")
                f.write(f"Command: {test_command}\n")
                f.write(f"Working Directory: {working_directory}\n")
                f.write(f"Framework: {framework}\n")
                f.write(f"Start Time: {start_time.isoformat()}\n")
                f.write(f"Return Code: {result.returncode}\n\n")
                f.write("=" * 80 + "\n")
                f.write("STDOUT:\n")
                f.write("=" * 80 + "\n")
                f.write(result.stdout + "\n\n")
                f.write("=" * 80 + "\n")
                f.write("STDERR:\n")
                f.write("=" * 80 + "\n")
                f.write(result.stderr + "\n")

            # Parse test output
            parser = self._get_parser(framework)
            parsed_result = parser.parse(result.stdout + "\n" + result.stderr)

            # Calculate execution time
            end_time = datetime.now(timezone.utc)
            execution_time = (end_time - start_time).total_seconds()

            # Build final result
            test_result = {
                **parsed_result,
                "command": test_command,
                "return_code": result.returncode,
                "output": result.stdout,
                "stderr": result.stderr,
                "execution_time": execution_time,
                "log_file": str(log_file),
            }

            # Log result
            log_level = "info" if test_result["success"] else "error"
            getattr(logger, log_level)(
                f"Tests {'passed' if test_result['success'] else 'failed'}",
                extra={
                    "extra_fields": {
                        "project_id": project_id,
                        "task_id": task_id,
                        "framework": framework,
                        "success": test_result["success"],
                        "stats": test_result["stats"],
                        "error_count": test_result["error_count"],
                        "execution_time": execution_time,
                    }
                },
            )

            return test_result

        except subprocess.TimeoutExpired as e:
            error_msg = f"Test execution timed out after {self.timeout}s"
            logger.error(
                error_msg,
                extra={
                    "extra_fields": {
                        "project_id": project_id,
                        "task_id": task_id,
                        "framework": framework,
                        "timeout": self.timeout,
                    }
                },
            )
            return {
                "success": False,
                "framework": framework,
                "stats": {"total": 0, "passed": 0, "failed": 0, "errors": 1},
                "errors": [{"error": error_msg, "type": "timeout"}],
                "error_count": 1,
                "output": "",
                "stderr": error_msg,
                "execution_time": self.timeout,
                "log_file": str(log_file),
            }

        except Exception as e:
            error_msg = f"Unexpected test execution error: {str(e)}"
            logger.error(
                error_msg,
                extra={
                    "extra_fields": {
                        "project_id": project_id,
                        "task_id": task_id,
                        "framework": framework,
                        "error": str(e),
                    }
                },
                exc_info=True,
            )
            raise TestRunnerError(error_msg) from e

    def _get_parser(self, framework: str) -> TestParser:
        """Get appropriate parser for framework.

        Args:
            framework: Framework type

        Returns:
            TestParser: Parser instance
        """
        # Normalize framework name
        framework_lower = framework.lower()

        # Return specific parser or generic fallback
        return self.PARSERS.get(framework_lower, GenericTestParser())

    def format_error_summary(self, test_result: Dict[str, Any]) -> str:
        """Format test errors into a human-readable summary.

        Args:
            test_result: Test result from run_tests()

        Returns:
            str: Formatted error summary for Claude retry context
        """
        if test_result["success"]:
            return "All tests passed!"

        summary_lines = []
        summary_lines.append(f"Test Summary ({test_result['framework']}):")
        summary_lines.append(f"  Total: {test_result['stats']['total']}")
        summary_lines.append(f"  Passed: {test_result['stats']['passed']}")
        summary_lines.append(f"  Failed: {test_result['stats']['failed']}")

        if test_result["errors"]:
            summary_lines.append("\nTest Failures:")
            for i, error in enumerate(test_result["errors"][:5], 1):  # Limit to 5
                summary_lines.append(f"\n{i}. {error.get('test_name', 'Unknown test')}")
                if error.get("file"):
                    summary_lines.append(f"   File: {error['file']}")
                    if error.get("line"):
                        summary_lines.append(f"   Line: {error['line']}")
                summary_lines.append(f"   Error: {error.get('error', 'Unknown error')}")

            if len(test_result["errors"]) > 5:
                summary_lines.append(f"\n... and {len(test_result['errors']) - 5} more failures")

        return "\n".join(summary_lines)


__all__ = [
    "TestRunner",
    "TestRunnerError",
    "TestExecutionError",
    "GodotTestParser",
    "PythonTestParser",
    "RustTestParser",
    "GenericTestParser",
]
