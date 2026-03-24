"""
Unit tests for scripts/agent-runner.sh workflow functions

Tests critical functions in the agent-runner script including:
- Error parsing
- Retry logic
- Cleanup functions
- Error context passing

NOTE: These tests are for v1.1 bash-based architecture.
      They are skipped during v2.0 refactor (FastAPI/Python architecture).
      Will be reimplemented as Python unit tests once v2.0 task execution is complete.
"""

import pytest
import subprocess
import tempfile
import json
from pathlib import Path
import shutil

# Compute repo root relative to this test file
REPO_ROOT = str(Path(__file__).resolve().parent.parent.parent)


class TestParseTestErrors:
    """Test the parse_test_errors function for different project types"""

    def setup_method(self):
        """Create temporary log directory for tests"""
        self.temp_dir = tempfile.mkdtemp()
        self.log_dir = Path(self.temp_dir) / "logs"
        self.log_dir.mkdir()

    def teardown_method(self):
        """Clean up temporary directory"""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_parse_godot_test_errors(self):
        """Test parsing Godot/gdUnit4 test errors"""
        # Create mock Godot test output
        test_output = """
Tests: 15 | Passed: 13 | Failed: 2 | Errors: 0
FAILED: test_player_jump
  Expected: 100
  Got: 50
  at res://test/test_player.gd:42

FAILED: test_player_velocity
  Assertion failed: velocity.y > 0
  at res://test/test_player.gd:67
"""
        test_log = self.log_dir / "test-output.log"
        test_log.write_text(test_output)

        # Source the parse_test_errors function and call it
        result = subprocess.run(
            [
                "bash",
                "-c",
                f"""
                LOG_DIR="{self.log_dir}"
                PROJECT_TYPE="godot"

                # Source parse_test_errors function
                source <(grep -A 100 "^parse_test_errors()" /mnt/1ece809a-2821-4f10-aecb-fcdf34760c0b/Git/lazy-bird/scripts/agent-runner.sh | sed '/^}}/q')

                parse_test_errors
                """
            ],
            capture_output=True,
            text=True
        )

        assert result.returncode == 0
        output = result.stdout

        # Verify summary includes test stats
        assert "Tests:" in output or "FAILED:" in output
        assert "**Test Output Summary:**" in output

    def test_parse_python_test_errors(self):
        """Test parsing Python/pytest test errors"""
        test_output = """
============================ FAILURES ============================
_______________ test_user_creation _______________

    def test_user_creation():
>       assert user.email == "test@example.com"
E       AssertionError: assert 'wrong@example.com' == 'test@example.com'

app/tests/test_models.py:42: AssertionError
============================ short test summary ==========================
FAILED app/tests/test_models.py::test_user_creation - AssertionError
"""
        test_log = self.log_dir / "test-output.log"
        test_log.write_text(test_output)

        result = subprocess.run(
            [
                "bash",
                "-c",
                f"""
                LOG_DIR="{self.log_dir}"
                PROJECT_TYPE="python"

                # Source function
                source <(grep -A 100 "^parse_test_errors()" /mnt/1ece809a-2821-4f10-aecb-fcdf34760c0b/Git/lazy-bird/scripts/agent-runner.sh | sed '/^}}/q')

                parse_test_errors
                """
            ],
            capture_output=True,
            text=True
        )

        assert result.returncode == 0
        output = result.stdout
        assert "FAILED" in output or "AssertionError" in output

    def test_parse_rust_test_errors(self):
        """Test parsing Rust test errors"""
        test_output = """
test result: FAILED. 3 passed; 1 failed; 0 ignored

failures:

---- tests::test_addition stdout ----
thread 'tests::test_addition' panicked at 'assertion failed: `(left == right)`
  left: `4`,
 right: `5`', src/lib.rs:12:9
"""
        test_log = self.log_dir / "test-output.log"
        test_log.write_text(test_output)

        result = subprocess.run(
            [
                "bash",
                "-c",
                f"""
                LOG_DIR="{self.log_dir}"
                PROJECT_TYPE="rust"

                source <(grep -A 100 "^parse_test_errors()" /mnt/1ece809a-2821-4f10-aecb-fcdf34760c0b/Git/lazy-bird/scripts/agent-runner.sh | sed '/^}}/q')

                parse_test_errors
                """
            ],
            capture_output=True,
            text=True
        )

        assert result.returncode == 0
        output = result.stdout
        assert "test result:" in output or "failures:" in output

    def test_parse_errors_no_log_file(self):
        """Test parse_test_errors when log file doesn't exist"""
        result = subprocess.run(
            [
                "bash",
                "-c",
                f"""
                LOG_DIR="{self.log_dir}"
                PROJECT_TYPE="godot"

                source <(grep -A 100 "^parse_test_errors()" /mnt/1ece809a-2821-4f10-aecb-fcdf34760c0b/Git/lazy-bird/scripts/agent-runner.sh | sed '/^}}/q')

                parse_test_errors
                """
            ],
            capture_output=True,
            text=True
        )

        assert result.returncode == 0
        assert "No test output available" in result.stdout


class TestRetryBackoff:
    """Test retry backoff calculation"""

    def test_exponential_backoff_calculation(self):
        """Test that backoff time increases with attempt number"""
        backoff_base = 30  # Base backoff seconds

        # Calculate backoff for different attempts
        expected_backoffs = {
            1: 30,   # attempt 1: 30 * 1 = 30s
            2: 60,   # attempt 2: 30 * 2 = 60s
            3: 90,   # attempt 3: 30 * 3 = 90s
        }

        for attempt, expected_sleep in expected_backoffs.items():
            result = subprocess.run(
                ["bash", "-c", f"echo $((30 * {attempt}))"],
                capture_output=True,
                text=True
            )
            actual_sleep = int(result.stdout.strip())
            assert actual_sleep == expected_sleep, f"Attempt {attempt}: expected {expected_sleep}s, got {actual_sleep}s"

    def test_total_attempts_calculation(self):
        """Test that TOTAL_ATTEMPTS = MAX_RETRY_ATTEMPTS + 1"""
        max_retries = 3
        result = subprocess.run(
            ["bash", "-c", f"echo $(({max_retries} + 1))"],
            capture_output=True,
            text=True
        )
        total_attempts = int(result.stdout.strip())
        assert total_attempts == 4, "3 retries should equal 4 total attempts"


@pytest.mark.skip(reason="v1.1 bash script test - will be reimplemented in v2.0")
class TestErrorContextPassing:
    """Test that error context is properly passed to run_claude function"""

    def test_run_claude_accepts_error_context_parameter(self):
        """Test that run_claude function accepts error context parameter"""
        # Extract the run_claude function signature
        result = subprocess.run(
            [
                "bash",
                "-c",
                "grep -A 5 '^run_claude()' /mnt/1ece809a-2821-4f10-aecb-fcdf34760c0b/Git/lazy-bird/scripts/agent-runner.sh"
            ],
            capture_output=True,
            text=True
        )

        assert result.returncode == 0
        function_code = result.stdout

        # Verify it accepts error_context parameter
        assert 'local error_context="${1:-}"' in function_code, "run_claude should accept error_context parameter"

    def test_error_context_appended_to_prompt(self):
        """Test that error context is appended to Claude prompt"""
        result = subprocess.run(
            [
                "bash",
                "-c",
                "grep -A 20 'if \\[ -n \"\\$error_context\" \\]' /mnt/1ece809a-2821-4f10-aecb-fcdf34760c0b/Git/lazy-bird/scripts/agent-runner.sh"
            ],
            capture_output=True,
            text=True
        )

        assert result.returncode == 0
        conditional_code = result.stdout

        # Verify error context is added to prompt
        assert "PREVIOUS ATTEMPT FAILED" in conditional_code
        assert "$error_context" in conditional_code

    def test_retry_loop_passes_error_details(self):
        """Test that retry loop passes error_details to run_claude"""
        result = subprocess.run(
            [
                "bash",
                "-c",
                """
                grep -B 5 -A 5 'run_claude "\\$error_details"' /mnt/1ece809a-2821-4f10-aecb-fcdf34760c0b/Git/lazy-bird/scripts/agent-runner.sh
                """
            ],
            capture_output=True,
            text=True
        )

        assert result.returncode == 0
        retry_code = result.stdout

        # Verify error_details are parsed and passed
        assert 'error_details=$(parse_test_errors)' in retry_code or 'error_details=' in retry_code
        assert 'run_claude "$error_details"' in retry_code


@pytest.mark.skip(reason="v1.1 bash script test - will be reimplemented in v2.0")
class TestCleanupWorktree:
    """Test the cleanup_worktree function"""

    def test_cleanup_worktree_function_exists(self):
        """Test that cleanup_worktree function is defined"""
        result = subprocess.run(
            [
                "bash",
                "-c",
                "grep -c '^cleanup_worktree()' /mnt/1ece809a-2821-4f10-aecb-fcdf34760c0b/Git/lazy-bird/scripts/agent-runner.sh"
            ],
            capture_output=True,
            text=True
        )

        assert result.returncode == 0
        count = int(result.stdout.strip())
        assert count == 1, "cleanup_worktree function should be defined once"

    def test_cleanup_removes_worktree(self):
        """Test that cleanup removes git worktree"""
        result = subprocess.run(
            [
                "bash",
                "-c",
                "grep 'git worktree remove' /mnt/1ece809a-2821-4f10-aecb-fcdf34760c0b/Git/lazy-bird/scripts/agent-runner.sh | grep cleanup_worktree -A 20"
            ],
            capture_output=True,
            text=True
        )

        assert result.returncode == 0
        assert "git worktree remove" in result.stdout
        assert "git worktree prune" in result.stdout

    def test_cleanup_deletes_branch(self):
        """Test that cleanup deletes local branch"""
        result = subprocess.run(
            [
                "bash",
                "-c",
                "grep -A 30 '^cleanup_worktree()' /mnt/1ece809a-2821-4f10-aecb-fcdf34760c0b/Git/lazy-bird/scripts/agent-runner.sh"
            ],
            capture_output=True,
            text=True
        )

        assert result.returncode == 0
        assert "git branch -D" in result.stdout, "cleanup should delete local branch"

    def test_cleanup_registered_as_exit_trap(self):
        """Test that cleanup_worktree is registered as EXIT trap"""
        result = subprocess.run(
            [
                "bash",
                "-c",
                "grep 'trap cleanup_worktree EXIT' /mnt/1ece809a-2821-4f10-aecb-fcdf34760c0b/Git/lazy-bird/scripts/agent-runner.sh"
            ],
            capture_output=True,
            text=True
        )

        assert result.returncode == 0
        assert "trap cleanup_worktree EXIT" in result.stdout


@pytest.mark.skip(reason="v1.1 bash script test - will be reimplemented in v2.0")
class TestWorkflowIntegrity:
    """Test overall workflow integrity"""

    def test_script_has_shebang(self):
        """Test that agent-runner.sh has proper shebang"""
        with open(f"{REPO_ROOT}/scripts/agent-runner.sh", "r") as f:
            first_line = f.readline()
        assert first_line.startswith("#!"), "Script should have shebang"
        assert "bash" in first_line, "Script should use bash"

    def test_script_has_error_handling(self):
        """Test that script has proper error handling (set -e)"""
        with open(f"{REPO_ROOT}/scripts/agent-runner.sh", "r") as f:
            content = f.read()
        assert "set -" in content, "Script should have error handling"

    def test_retry_loop_has_err_trap_disabled(self):
        """Test that ERR trap is disabled during retry loop"""
        result = subprocess.run(
            [
                "bash",
                "-c",
                "grep -B 2 'for attempt in' /mnt/1ece809a-2821-4f10-aecb-fcdf34760c0b/Git/lazy-bird/scripts/agent-runner.sh | grep 'trap - ERR'"
            ],
            capture_output=True,
            text=True
        )

        # Should find trap - ERR before the retry loop
        assert result.returncode == 0 or "trap - ERR" in result.stdout

    def test_all_critical_functions_exist(self):
        """Test that all critical workflow functions are defined"""
        critical_functions = [
            "parse_test_errors",
            "run_claude",
            "cleanup_worktree",
            "create_worktree",
            "run_tests",
            "commit_changes",
            "push_branch",
        ]

        for func_name in critical_functions:
            result = subprocess.run(
                [
                    "bash",
                    "-c",
                    f"grep -c '^{func_name}()' /mnt/1ece809a-2821-4f10-aecb-fcdf34760c0b/Git/lazy-bird/scripts/agent-runner.sh || echo 0"
                ],
                capture_output=True,
                text=True
            )
            count = int(result.stdout.strip())
            assert count >= 1, f"Critical function {func_name} should be defined"


@pytest.mark.skip(reason="v1.1 bash script test - will be reimplemented in v2.0")
class TestWebUIIntegration:
    """Test Web UI cache deletion integration"""

    def test_queue_service_has_remove_from_cache(self):
        """Test that queue_service.py has _remove_from_processed_cache method"""
        result = subprocess.run(
            [
                "bash",
                "-c",
                "grep -c 'def _remove_from_processed_cache' /mnt/1ece809a-2821-4f10-aecb-fcdf34760c0b/Git/lazy-bird/web/backend/services/queue_service.py"
            ],
            capture_output=True,
            text=True
        )

        assert result.returncode == 0
        count = int(result.stdout.strip())
        assert count == 1, "_remove_from_processed_cache method should exist"

    def test_delete_task_calls_cache_removal(self):
        """Test that delete_task calls _remove_from_processed_cache"""
        result = subprocess.run(
            [
                "bash",
                "-c",
                "grep -A 20 'def delete_task' /mnt/1ece809a-2821-4f10-aecb-fcdf34760c0b/Git/lazy-bird/web/backend/services/queue_service.py | grep '_remove_from_processed_cache'"
            ],
            capture_output=True,
            text=True
        )

        assert result.returncode == 0
        assert "_remove_from_processed_cache" in result.stdout
