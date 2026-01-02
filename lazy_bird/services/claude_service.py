"""Claude Code CLI service.

This module provides the ClaudeService class for executing Claude Code CLI
commands, parsing output, tracking token usage, and handling errors.
"""

import json
import logging
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, Optional, List, TYPE_CHECKING

if TYPE_CHECKING:
    from lazy_bird.core.config import Settings

logger = logging.getLogger(__name__)


def _get_settings():
    """Lazy import settings to avoid circular dependencies."""
    from lazy_bird.core.config import settings
    return settings


class ClaudeServiceError(Exception):
    """Base exception for Claude service errors."""

    pass


class ClaudeExecutionError(ClaudeServiceError):
    """Exception raised when Claude Code CLI execution fails."""

    def __init__(self, command: str, return_code: int, stderr: str, stdout: str = ""):
        self.command = command
        self.return_code = return_code
        self.stderr = stderr
        self.stdout = stdout
        super().__init__(
            f"Claude execution failed with code {return_code}:\n"
            f"Command: {command}\n"
            f"Error: {stderr}"
        )


class ClaudeTimeoutError(ClaudeServiceError):
    """Exception raised when Claude execution times out."""

    pass


class ClaudeService:
    """Service for executing Claude Code CLI commands.

    Handles Claude Code CLI execution, output parsing, token tracking,
    and cost calculation.

    Attributes:
        api_key: Claude API key from settings
        model: Claude model to use (default from settings)
        max_tokens: Maximum tokens per request
        temperature: Temperature setting for Claude
        timeout: Execution timeout in seconds
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        timeout: Optional[int] = None,
    ):
        """Initialize ClaudeService.

        Args:
            api_key: Claude API key (defaults to settings.CLAUDE_API_KEY)
            model: Model name (defaults to settings.CLAUDE_MODEL)
            max_tokens: Max tokens (defaults to settings.CLAUDE_MAX_TOKENS)
            temperature: Temperature (defaults to settings.CLAUDE_TEMPERATURE)
            timeout: Timeout in seconds (defaults to 600)
        """
        # Only load settings if any param is not provided
        if not all([api_key, model, max_tokens, temperature is not None]):
            settings = _get_settings()
            self.api_key = api_key or settings.CLAUDE_API_KEY
            self.model = model or settings.CLAUDE_MODEL
            self.max_tokens = max_tokens or settings.CLAUDE_MAX_TOKENS
            self.temperature = temperature if temperature is not None else settings.CLAUDE_TEMPERATURE
        else:
            self.api_key = api_key
            self.model = model
            self.max_tokens = max_tokens
            self.temperature = temperature

        self.timeout = timeout or 600  # Default 10 minutes

        if not self.api_key:
            raise ClaudeServiceError("Claude API key not configured")

    def execute_claude(
        self,
        prompt: str,
        working_directory: Path,
        project_id: Optional[str] = None,
        task_id: Optional[int] = None,
        error_context: Optional[str] = None,
        log_file: Optional[Path] = None,
    ) -> Dict[str, Any]:
        """Execute Claude Code CLI with the given prompt.

        Args:
            prompt: Task prompt for Claude
            working_directory: Directory to execute Claude in
            project_id: Project identifier for logging
            task_id: Task ID for logging
            error_context: Previous error context for retry attempts
            log_file: Path to log file for Claude output

        Returns:
            dict: Execution result
                - success: bool
                - output: str (Claude's output)
                - error: str (error message if failed)
                - tokens_used: int
                - cost: float
                - execution_time: float (seconds)
                - log_file: str (path to log file)

        Raises:
            ClaudeExecutionError: If Claude execution fails
            ClaudeTimeoutError: If execution times out
        """
        start_time = datetime.now(timezone.utc)

        # Build full prompt with error context if retry
        full_prompt = self._build_prompt(prompt, error_context)

        # Determine log file path
        if log_file is None:
            # Use /tmp/lazy-bird-logs as default log directory
            log_dir = Path("/tmp/lazy-bird-logs") / "claude"
            log_dir.mkdir(parents=True, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            prefix = f"{project_id}-{task_id}" if project_id and task_id else "claude"
            log_file = log_dir / f"{prefix}_{timestamp}.log"

        logger.info(
            f"Executing Claude Code CLI",
            extra={
                "extra_fields": {
                    "project_id": project_id,
                    "task_id": task_id,
                    "working_directory": str(working_directory),
                    "log_file": str(log_file),
                    "has_error_context": error_context is not None,
                }
            },
        )

        # Build command
        command = self._build_command(full_prompt, working_directory)

        # Execute Claude
        try:
            result = subprocess.run(
                command,
                cwd=working_directory,
                capture_output=True,
                text=True,
                timeout=self.timeout,
                env={**subprocess.os.environ, "ANTHROPIC_API_KEY": self.api_key},
            )

            # Write output to log file
            self._write_log(log_file, command, result, start_time)

            # Parse output
            execution_result = self._parse_output(
                result, start_time, str(log_file), project_id, task_id
            )

            # Log result
            log_level = "info" if execution_result["success"] else "error"
            getattr(logger, log_level)(
                f"Claude execution {'succeeded' if execution_result['success'] else 'failed'}",
                extra={
                    "extra_fields": {
                        "project_id": project_id,
                        "task_id": task_id,
                        "success": execution_result["success"],
                        "tokens_used": execution_result["tokens_used"],
                        "cost": execution_result["cost"],
                        "execution_time": execution_result["execution_time"],
                    }
                },
            )

            return execution_result

        except subprocess.TimeoutExpired as e:
            error_msg = f"Claude execution timed out after {self.timeout}s"
            logger.error(
                error_msg,
                extra={
                    "extra_fields": {
                        "project_id": project_id,
                        "task_id": task_id,
                        "timeout": self.timeout,
                    }
                },
            )
            raise ClaudeTimeoutError(error_msg) from e

        except Exception as e:
            logger.error(
                f"Claude execution failed: {str(e)}",
                extra={
                    "extra_fields": {
                        "project_id": project_id,
                        "task_id": task_id,
                        "error": str(e),
                    }
                },
                exc_info=True,
            )
            raise ClaudeServiceError(f"Unexpected error: {str(e)}") from e

    def _build_prompt(self, base_prompt: str, error_context: Optional[str] = None) -> str:
        """Build full prompt with optional error context.

        Args:
            base_prompt: Base task prompt
            error_context: Previous error context for retry

        Returns:
            str: Full prompt
        """
        if error_context:
            return f"{base_prompt}\n\n## Previous Attempt Error\n\n{error_context}\n\nPlease fix the issues above and try again."
        return base_prompt

    def _build_command(self, prompt: str, working_directory: Path) -> List[str]:
        """Build Claude Code CLI command.

        Args:
            prompt: Full prompt
            working_directory: Working directory

        Returns:
            list: Command as list of strings
        """
        command = [
            "claude",
            "-p",
            prompt,
            "--model",
            self.model,
            "--max-tokens",
            str(self.max_tokens),
            "--temperature",
            str(self.temperature),
        ]

        # Add output format for easier parsing
        command.extend(["--output-format", "json"])

        return command

    def _write_log(
        self,
        log_file: Path,
        command: List[str],
        result: subprocess.CompletedProcess,
        start_time: datetime,
    ) -> None:
        """Write execution log to file.

        Args:
            log_file: Path to log file
            command: Command that was executed
            result: Subprocess result
            start_time: Execution start time
        """
        end_time = datetime.now(timezone.utc)
        duration = (end_time - start_time).total_seconds()

        with open(log_file, "w") as f:
            f.write("=" * 80 + "\n")
            f.write("Claude Code CLI Execution Log\n")
            f.write("=" * 80 + "\n\n")
            f.write(f"Start Time: {start_time.isoformat()}\n")
            f.write(f"End Time: {end_time.isoformat()}\n")
            f.write(f"Duration: {duration:.2f}s\n")
            f.write(f"Return Code: {result.returncode}\n\n")
            f.write("Command:\n")
            f.write(" ".join(command) + "\n\n")
            f.write("=" * 80 + "\n")
            f.write("STDOUT:\n")
            f.write("=" * 80 + "\n")
            f.write(result.stdout + "\n\n")
            f.write("=" * 80 + "\n")
            f.write("STDERR:\n")
            f.write("=" * 80 + "\n")
            f.write(result.stderr + "\n")

    def _parse_output(
        self,
        result: subprocess.CompletedProcess,
        start_time: datetime,
        log_file: str,
        project_id: Optional[str] = None,
        task_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Parse Claude output and extract token usage.

        Args:
            result: Subprocess result
            start_time: Execution start time
            log_file: Path to log file
            project_id: Project ID for logging
            task_id: Task ID for logging

        Returns:
            dict: Parsed result with success, output, tokens, cost
        """
        end_time = datetime.now(timezone.utc)
        execution_time = (end_time - start_time).total_seconds()

        # Check if execution succeeded
        success = result.returncode == 0

        # Try to parse JSON output
        tokens_used = 0
        output = result.stdout

        try:
            # Claude CLI may output JSON with usage stats
            json_output = json.loads(result.stdout)
            if "usage" in json_output:
                tokens_used = json_output["usage"].get("total_tokens", 0)
            if "output" in json_output:
                output = json_output["output"]
        except (json.JSONDecodeError, KeyError):
            # Fallback: try to extract from plain text output
            tokens_used = self._extract_tokens_from_text(result.stdout + result.stderr)

        # Calculate cost (example rates, adjust based on actual pricing)
        cost = self._calculate_cost(tokens_used)

        return {
            "success": success,
            "output": output,
            "error": result.stderr if not success else "",
            "tokens_used": tokens_used,
            "cost": cost,
            "execution_time": execution_time,
            "log_file": log_file,
            "return_code": result.returncode,
        }

    def _extract_tokens_from_text(self, text: str) -> int:
        """Extract token count from plain text output.

        Args:
            text: Output text

        Returns:
            int: Token count (0 if not found)
        """
        # Look for patterns like "tokens used: 1234" or "total tokens: 1234"
        patterns = [
            r"total[_\s]+tokens[:\s]+(\d+)",
            r"tokens[_\s]+used[:\s]+(\d+)",
            r"(\d+)[_\s]+tokens",
        ]

        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return int(match.group(1))

        return 0

    def _calculate_cost(self, tokens: int) -> float:
        """Calculate cost based on token usage.

        Args:
            tokens: Number of tokens used

        Returns:
            float: Cost in USD

        Note:
            Pricing is approximate and should be updated based on actual API pricing.
            Current rates (example):
            - Input: $0.008 / 1K tokens
            - Output: $0.024 / 1K tokens
            - Using average of $0.016 / 1K tokens
        """
        if tokens == 0:
            return 0.0

        # Average rate per 1K tokens
        rate_per_1k = 0.016

        return (tokens / 1000) * rate_per_1k

    def construct_task_prompt(
        self,
        project_name: str,
        project_type: str,
        project_id: str,
        task_title: str,
        task_body: str,
        working_directory: Path,
    ) -> str:
        """Construct detailed task prompt for Claude.

        Args:
            project_name: Project name
            project_type: Project type (e.g., "godot", "python")
            project_id: Project identifier
            task_title: Task title
            task_body: Task description
            working_directory: Working directory path

        Returns:
            str: Formatted prompt
        """
        prompt = f"""# Task for {project_name}

**Project Type:** {project_type}
**Project ID:** {project_id}
**Working Directory:** {working_directory}

## Task: {task_title}

{task_body}

## Important Instructions

- You are working in the directory: {working_directory}
- This is a git worktree - changes will be committed automatically
- **DO NOT** run git commit commands - the automation system handles all git operations
- Focus on implementing the task requirements
- Write tests if applicable
- Ensure code follows project conventions
- The task will be validated by automated tests

Please implement the requested changes."""

        return prompt


__all__ = [
    "ClaudeService",
    "ClaudeServiceError",
    "ClaudeExecutionError",
    "ClaudeTimeoutError",
]
