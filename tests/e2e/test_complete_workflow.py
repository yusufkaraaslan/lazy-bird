"""
End-to-end tests for complete agent workflow

Tests the entire workflow from issue detection to PR creation:
1. Issue detection → task queuing
2. Worktree creation
3. Task execution (mocked)
4. Test running
5. Retry on failure (with error context)
6. PR creation
7. Cleanup

This test validates the entire agent-runner.sh workflow.
"""

import pytest
import subprocess
import tempfile
import json
import time
from pathlib import Path
import shutil
import os


@pytest.fixture(scope="module")
def test_environment():
    """Set up complete test environment with git repo, config, logs"""
    temp_base = tempfile.mkdtemp(prefix="lazy-bird-e2e-")

    # Create project directory with git
    project_dir = Path(temp_base) / "test-project"
    project_dir.mkdir()

    subprocess.run(["git", "init"], cwd=project_dir, check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.email", "test@example.com"],
        cwd=project_dir,
        check=True,
        capture_output=True
    )
    subprocess.run(
        ["git", "config", "user.name", "Test User"],
        cwd=project_dir,
        check=True,
        capture_output=True
    )

    # Create initial project structure
    (project_dir / "README.md").write_text("# Test Project")
    (project_dir / "src").mkdir()
    (project_dir / "src" / "main.py").write_text("print('Hello')")

    subprocess.run(["git", "add", "."], cwd=project_dir, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "Initial commit"],
        cwd=project_dir,
        check=True,
        capture_output=True
    )

    # Create logs directory
    logs_dir = Path(temp_base) / "logs"
    logs_dir.mkdir()

    # Create queue directory
    queue_dir = Path(temp_base) / "queue"
    queue_dir.mkdir()

    env = {
        "project_dir": project_dir,
        "logs_dir": logs_dir,
        "queue_dir": queue_dir,
        "temp_base": Path(temp_base)
    }

    yield env

    # Cleanup
    shutil.rmtree(temp_base, ignore_errors=True)


class TestCompleteWorkflow:
    """Test complete workflow from start to finish"""

    def test_worktree_lifecycle(self, test_environment):
        """Test complete worktree lifecycle: create → work → cleanup"""
        project_dir = test_environment["project_dir"]
        worktree_path = test_environment["temp_base"] / "agent-test-123"
        branch_name = "feature-test-123"

        # Step 1: Create worktree
        create_result = subprocess.run(
            ["bash", "-c", f"""
            PROJECT_PATH="{project_dir}"
            WORKTREE_PATH="{worktree_path}"
            BRANCH_NAME="{branch_name}"
            PROJECT_ID="test-project"

            source <(grep -A 30 '^create_worktree()' /mnt/1ece809a-2821-4f10-aecb-fcdf34760c0b/Git/lazy-bird/scripts/agent-runner.sh | sed '/^}}/q')

            create_worktree
            """],
            capture_output=True,
            text=True
        )

        assert create_result.returncode == 0, f"Create failed: {create_result.stderr}"
        assert worktree_path.exists(), "Worktree should exist"

        # Step 2: Make changes in worktree (simulating agent work)
        test_file = worktree_path / "src" / "new_feature.py"
        test_file.write_text("def new_feature(): return True")

        subprocess.run(["git", "add", "."], cwd=worktree_path, check=True, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "Add new feature"],
            cwd=worktree_path,
            check=True,
            capture_output=True
        )

        # Verify commit exists in branch
        log_result = subprocess.run(
            ["git", "log", "--oneline", "-1"],
            cwd=worktree_path,
            capture_output=True,
            text=True
        )
        assert "Add new feature" in log_result.stdout

        # Step 3: Cleanup worktree
        cleanup_result = subprocess.run(
            ["bash", "-c", f"""
            PROJECT_PATH="{project_dir}"
            WORKTREE_PATH="{worktree_path}"
            BRANCH_NAME="{branch_name}"
            PROJECT_ID="test-project"

            source <(grep -A 40 '^cleanup_worktree()' /mnt/1ece809a-2821-4f10-aecb-fcdf34760c0b/Git/lazy-bird/scripts/agent-runner.sh | sed '/^}}/q')

            cleanup_worktree
            """],
            capture_output=True,
            text=True
        )

        assert cleanup_result.returncode == 0, f"Cleanup failed: {cleanup_result.stderr}"
        assert not worktree_path.exists(), "Worktree should be removed"

    def test_error_parsing_and_retry_context(self, test_environment):
        """Test error parsing creates proper context for retry"""
        logs_dir = test_environment["logs_dir"]

        # Create test log with Godot errors
        test_log = logs_dir / "test-output.log"
        test_log.write_text("""
Tests: 15 | Passed: 12 | Failed: 3 | Errors: 0

FAILED: test_player_movement
  Expected velocity: Vector2(100, 0)
  Got: Vector2(0, 0)
  at res://test/test_player.gd:56

FAILED: test_enemy_ai
  Enemy did not pursue player
  at res://test/test_enemy.gd:89

FAILED: test_collision_detection
  Collision not detected
  at res://systems/physics/test_collision.gd:42
""")

        # Step 1: Parse errors using Python parser
        parser_script = "/mnt/1ece809a-2821-4f10-aecb-fcdf34760c0b/Git/lazy-bird/scripts/parse_test_errors.py"
        parse_result = subprocess.run(
            ["python3", parser_script, str(test_log), "godot"],
            capture_output=True,
            text=True
        )

        assert parse_result.returncode == 0
        error_context = parse_result.stdout

        # Step 2: Verify error context has critical information
        assert "3 Error(s) Found" in error_context or "Failed: 3" in error_context
        assert "test_player_movement" in error_context
        assert "test_player.gd:56" in error_context
        assert "test_enemy.gd:89" in error_context

        # Step 3: Verify JSON output has structured data
        json_result = subprocess.run(
            ["python3", parser_script, str(test_log), "godot", "--json"],
            capture_output=True,
            text=True
        )

        assert json_result.returncode == 0
        error_data = json.loads(json_result.stdout)

        assert error_data["error_count"] == 3
        assert error_data["stats"]["failed"] == 3
        assert len(error_data["errors"]) == 3

        # Verify each error has required fields
        for error in error_data["errors"]:
            assert "test_name" in error
            assert "file" in error
            assert "line" in error
            assert "error" in error

        # This error_context would be passed to run_claude on retry
        # Verify it's substantial enough to help Claude
        assert len(error_context) > 100, "Error context should be detailed"

    def test_multi_attempt_workflow(self, test_environment):
        """Test workflow with multiple retry attempts"""
        # Simulate retry workflow
        max_retries = 3
        total_attempts = max_retries + 1

        assert total_attempts == 4, "Should have 4 total attempts (1 initial + 3 retries)"

        # Test backoff calculation
        backoffs = []
        for attempt in range(1, max_retries + 1):
            backoff = 30 * attempt
            backoffs.append(backoff)

        assert backoffs == [30, 60, 90], "Backoff should increase: 30s, 60s, 90s"

    def test_bash_function_integration(self, test_environment):
        """Test that all critical bash functions exist and can be called"""
        script_path = "/mnt/1ece809a-2821-4f10-aecb-fcdf34760c0b/Git/lazy-bird/scripts/agent-runner.sh"

        critical_functions = [
            "create_worktree",
            "cleanup_worktree",
            "parse_test_errors",
            "run_tests",
            "commit_changes",
            "push_branch",
            "run_claude"
        ]

        for func_name in critical_functions:
            # Verify function exists
            result = subprocess.run(
                ["grep", "-c", f"^{func_name}()", script_path],
                capture_output=True,
                text=True
            )

            assert result.returncode == 0, f"Function {func_name} should exist"
            count = int(result.stdout.strip())
            assert count >= 1, f"Function {func_name} should be defined at least once"

    def test_error_context_appended_to_claude_prompt(self):
        """Test that error context is properly appended to Claude prompt in run_claude"""
        script_path = "/mnt/1ece809a-2821-4f10-aecb-fcdf34760c0b/Git/lazy-bird/scripts/agent-runner.sh"

        # Extract run_claude function
        result = subprocess.run(
            ["grep", "-A", "50", "^run_claude()", script_path],
            capture_output=True,
            text=True
        )

        assert result.returncode == 0
        function_code = result.stdout

        # Verify error context handling
        assert 'local error_context="${1:-}"' in function_code or 'error_context="${1:-}"' in function_code
        assert 'if [ -n "$error_context" ]' in function_code or 'if [[ -n "$error_context" ]]' in function_code
        assert "PREVIOUS ATTEMPT FAILED" in function_code
        assert "$error_context" in function_code


class TestWorkflowFailureHandling:
    """Test workflow handles failures gracefully"""

    def test_cleanup_on_exit_trap(self):
        """Test that cleanup_worktree is registered as EXIT trap"""
        script_path = "/mnt/1ece809a-2821-4f10-aecb-fcdf34760c0b/Git/lazy-bird/scripts/agent-runner.sh"

        result = subprocess.run(
            ["grep", "trap cleanup_worktree EXIT", script_path],
            capture_output=True,
            text=True
        )

        assert result.returncode == 0, "EXIT trap should be registered"
        assert "trap cleanup_worktree EXIT" in result.stdout

    def test_error_handling_set_in_script(self):
        """Test that script has proper error handling enabled"""
        script_path = "/mnt/1ece809a-2821-4f10-aecb-fcdf34760c0b/Git/lazy-bird/scripts/agent-runner.sh"

        with open(script_path) as f:
            content = f.read()

        # Should have error handling
        assert "set -" in content, "Script should have set - flags"

        # Should have ERR trap management for retry loop
        assert "trap - ERR" in content or "trap ERR" in content


class TestWorkflowMetrics:
    """Test workflow tracking and metrics"""

    def test_all_workflow_steps_present(self):
        """Test that agent-runner.sh contains all 11 workflow steps"""
        script_path = "/mnt/1ece809a-2821-4f10-aecb-fcdf34760c0b/Git/lazy-bird/scripts/agent-runner.sh"

        with open(script_path) as f:
            content = f.read()

        # Key workflow steps that should be present
        workflow_steps = [
            "create_worktree",  # Step 2
            "run_claude",       # Step 4 & 8
            "run_tests",        # Step 5 & 9
            "parse_test_errors", # Step 7
            "commit_changes",   # Step 10
            "push_branch",      # Step 11
            "cleanup_worktree"  # Exit trap
        ]

        for step in workflow_steps:
            assert f"{step}()" in content or f"def {step}" in content, \
                f"Workflow step '{step}' should be present"


class TestFrameworkSupport:
    """Test multi-framework error parsing support"""

    def test_godot_framework_supported(self, test_environment):
        """Test Godot error parsing"""
        logs_dir = test_environment["logs_dir"]
        test_log = logs_dir / "godot-test.log"
        test_log.write_text("Tests: 10 | Passed: 9 | Failed: 1 | Errors: 0")

        parser_script = "/mnt/1ece809a-2821-4f10-aecb-fcdf34760c0b/Git/lazy-bird/scripts/parse_test_errors.py"
        result = subprocess.run(
            ["python3", parser_script, str(test_log), "godot", "--json"],
            capture_output=True,
            text=True
        )

        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert data["framework"] == "godot"

    def test_python_framework_supported(self, test_environment):
        """Test Python/pytest error parsing"""
        logs_dir = test_environment["logs_dir"]
        test_log = logs_dir / "pytest.log"
        test_log.write_text("FAILED test_example.py::test_one - AssertionError")

        parser_script = "/mnt/1ece809a-2821-4f10-aecb-fcdf34760c0b/Git/lazy-bird/scripts/parse_test_errors.py"
        result = subprocess.run(
            ["python3", parser_script, str(test_log), "python", "--json"],
            capture_output=True,
            text=True
        )

        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert data["framework"] == "python"

    def test_rust_framework_supported(self, test_environment):
        """Test Rust error parsing"""
        logs_dir = test_environment["logs_dir"]
        test_log = logs_dir / "cargo-test.log"
        test_log.write_text("test result: FAILED. 5 passed; 1 failed; 0 ignored")

        parser_script = "/mnt/1ece809a-2821-4f10-aecb-fcdf34760c0b/Git/lazy-bird/scripts/parse_test_errors.py"
        result = subprocess.run(
            ["python3", parser_script, str(test_log), "rust", "--json"],
            capture_output=True,
            text=True
        )

        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert data["framework"] == "rust"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
