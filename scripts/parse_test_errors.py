#!/usr/bin/env python3
"""
Advanced test error parser with structured JSON output

Extracts structured error information from test logs including:
- Test names
- File paths and line numbers
- Error messages
- Stack traces
- Test statistics

Supports: Godot (gdUnit4), Python (pytest), Rust (cargo test)
"""

import sys
import re
import json
from pathlib import Path
from typing import Dict, List, Any, Optional


class TestErrorParser:
    """Base class for test error parsing"""

    def parse(self, log_content: str) -> Dict[str, Any]:
        """Parse test log and return structured error data"""
        raise NotImplementedError


class GodotErrorParser(TestErrorParser):
    """Parser for Godot gdUnit4 test output"""

    def parse(self, log_content: str) -> Dict[str, Any]:
        """Parse Godot test errors with file/line extraction"""
        errors = []
        stats = {"total": 0, "passed": 0, "failed": 0, "errors": 0}

        # Extract test statistics
        stats_pattern = (
            r"Tests:\s*(\d+)\s*\|\s*Passed:\s*(\d+)\s*\|\s*Failed:\s*(\d+)\s*\|\s*Errors:\s*(\d+)"
        )
        stats_match = re.search(stats_pattern, log_content)
        if stats_match:
            stats = {
                "total": int(stats_match.group(1)),
                "passed": int(stats_match.group(2)),
                "failed": int(stats_match.group(3)),
                "errors": int(stats_match.group(4)),
            }

        # Extract failed tests with details
        # Pattern: FAILED: test_name ... at res://path/file.gd:42
        failed_pattern = r"FAILED:\s+(\S+)\s+(.*?)\s+at\s+(res://[^:]+):(\d+)"
        for match in re.finditer(failed_pattern, log_content, re.DOTALL):
            test_name = match.group(1)
            error_msg = match.group(2).strip()
            file_path = match.group(3)
            line_number = int(match.group(4))

            errors.append(
                {
                    "test_name": test_name,
                    "file": file_path,
                    "line": line_number,
                    "error": error_msg,
                    "type": "test_failure",
                }
            )

        # Also capture assertion failures
        assert_pattern = r"Assertion\s+failed:?\s+(.*?)\s+at\s+(res://[^:]+):(\d+)"
        for match in re.finditer(assert_pattern, log_content):
            error_msg = match.group(1).strip()
            file_path = match.group(2)
            line_number = int(match.group(3))

            errors.append(
                {
                    "test_name": "assertion",
                    "file": file_path,
                    "line": line_number,
                    "error": error_msg,
                    "type": "assertion_failure",
                }
            )

        return {"framework": "godot", "stats": stats, "errors": errors, "error_count": len(errors)}


class PythonErrorParser(TestErrorParser):
    """Parser for Python pytest output"""

    def parse(self, log_content: str) -> Dict[str, Any]:
        """Parse pytest errors with stack trace extraction"""
        errors = []
        stats = {"total": 0, "passed": 0, "failed": 0, "errors": 0}

        # Extract test statistics from summary line
        # Example: "3 failed, 10 passed in 2.5s"
        stats_pattern = r"(\d+)\s+failed.*?(\d+)\s+passed"
        stats_match = re.search(stats_pattern, log_content)
        if stats_match:
            stats["failed"] = int(stats_match.group(1))
            stats["passed"] = int(stats_match.group(2))
            stats["total"] = stats["failed"] + stats["passed"]

        # Extract failed tests with file/line info
        # Pattern: FAILED path/file.py::test_name - AssertionError: message
        failed_pattern = r"FAILED\s+([^:]+)::(\S+)\s+-\s+(.*?)$"
        for match in re.finditer(failed_pattern, log_content, re.MULTILINE):
            file_path = match.group(1)
            test_name = match.group(2)
            error_msg = match.group(3).strip()

            # Try to extract line number from stack trace
            line_number = None
            stack_pattern = rf"{re.escape(file_path)}:(\d+):"
            stack_match = re.search(stack_pattern, log_content)
            if stack_match:
                line_number = int(stack_match.group(1))

            errors.append(
                {
                    "test_name": test_name,
                    "file": file_path,
                    "line": line_number,
                    "error": error_msg,
                    "type": "test_failure",
                }
            )

        # Extract AssertionError details with line numbers
        assert_pattern = r"([^:\s]+):(\d+):\s+in\s+\S+\s+.*?AssertionError:\s+(.*?)(?:\n|$)"
        for match in re.finditer(assert_pattern, log_content):
            file_path = match.group(1)
            line_number = int(match.group(2))
            error_msg = match.group(3).strip()

            errors.append(
                {
                    "test_name": "assertion",
                    "file": file_path,
                    "line": line_number,
                    "error": error_msg,
                    "type": "assertion_error",
                }
            )

        return {"framework": "python", "stats": stats, "errors": errors, "error_count": len(errors)}


class RustErrorParser(TestErrorParser):
    """Parser for Rust cargo test output"""

    def parse(self, log_content: str) -> Dict[str, Any]:
        """Parse Rust test errors"""
        errors = []
        stats = {"total": 0, "passed": 0, "failed": 0, "errors": 0}

        # Extract test statistics
        # Example: "test result: FAILED. 10 passed; 3 failed; 0 ignored"
        stats_pattern = r"test\s+result:.*?(\d+)\s+passed;\s+(\d+)\s+failed"
        stats_match = re.search(stats_pattern, log_content)
        if stats_match:
            stats["passed"] = int(stats_match.group(1))
            stats["failed"] = int(stats_match.group(2))
            stats["total"] = stats["passed"] + stats["failed"]

        # Extract failed tests with panic info
        # Pattern: ---- tests::test_name stdout ----
        # followed by panic message and file:line
        test_pattern = r"----\s+([\w:]+)\s+stdout\s+----\s+(.*?)(?=\n\n|$)"
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

                errors.append(
                    {
                        "test_name": test_name,
                        "file": file_path,
                        "line": line_number,
                        "error": error_msg,
                        "type": "panic",
                    }
                )

        return {"framework": "rust", "stats": stats, "errors": errors, "error_count": len(errors)}


def parse_test_errors(log_path: str, project_type: str) -> Dict[str, Any]:
    """
    Parse test errors from log file based on project type

    Args:
        log_path: Path to test output log
        project_type: Type of project (godot, python, rust, etc.)

    Returns:
        Structured error data as dictionary
    """
    # Read log file
    try:
        with open(log_path, "r") as f:
            log_content = f.read()
    except FileNotFoundError:
        return {
            "framework": project_type,
            "error": "Log file not found",
            "stats": {},
            "errors": [],
            "error_count": 0,
        }

    # Select appropriate parser
    parsers = {
        "godot": GodotErrorParser(),
        "python": PythonErrorParser(),
        "rust": RustErrorParser(),
    }

    parser = parsers.get(project_type)
    if not parser:
        # Generic fallback
        return {
            "framework": project_type,
            "raw_output": log_content[-1000:],  # Last 1000 chars
            "stats": {},
            "errors": [],
            "error_count": 0,
        }

    return parser.parse(log_content)


def format_error_summary(error_data: Dict[str, Any]) -> str:
    """
    Format error data into human-readable summary for Claude

    Args:
        error_data: Structured error data from parse_test_errors

    Returns:
        Formatted error summary string
    """
    lines = []
    lines.append("**Test Error Summary:**\n")

    # Add statistics
    stats = error_data.get("stats", {})
    if stats:
        lines.append(
            f"Tests: {stats.get('total', 0)} | "
            f"Passed: {stats.get('passed', 0)} | "
            f"Failed: {stats.get('failed', 0)} | "
            f"Errors: {stats.get('errors', 0)}\n"
        )

    # Add individual errors
    errors = error_data.get("errors", [])
    if errors:
        lines.append(f"\n**{len(errors)} Error(s) Found:**\n")
        for i, error in enumerate(errors, 1):
            lines.append(f"\n{i}. **{error.get('test_name', 'unknown')}**")
            if error.get("file"):
                file_line = f"   File: `{error['file']}"
                if error.get("line"):
                    file_line += f":{error['line']}`"
                else:
                    file_line += "`"
                lines.append(file_line)
            lines.append(f"   Error: {error.get('error', 'Unknown error')}")
            lines.append("")

    return "\n".join(lines)


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: parse_test_errors.py <log_path> <project_type> [--json]")
        sys.exit(1)

    log_path = sys.argv[1]
    project_type = sys.argv[2]
    output_json = "--json" in sys.argv

    # Parse errors
    error_data = parse_test_errors(log_path, project_type)

    if output_json:
        # Output as JSON
        print(json.dumps(error_data, indent=2))
    else:
        # Output as formatted summary
        print(format_error_summary(error_data))
