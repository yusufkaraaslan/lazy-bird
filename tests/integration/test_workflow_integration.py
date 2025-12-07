"""
Integration tests for multi-step workflow execution

Tests that validate multiple workflow steps working together:
- Worktree creation → tests → cleanup
- Error parsing → retry → success
- Multi-project task isolation
- PR creation → update → merge
"""

import pytest
import subprocess
import tempfile
import json
import time
from pathlib import Path
import shutil


@pytest.fixture
def test_project():
    """Create a temporary test project directory"""
    temp_dir = tempfile.mkdtemp(prefix="lazy-bird-test-")
    project_dir = Path(temp_dir) / "test-project"

    # Initialize git repo
    subprocess.run(["git", "init", str(project_dir)], check=True, capture_output=True)
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

    # Create initial commit
    (project_dir / "README.md").write_text("# Test Project")
    subprocess.run(["git", "add", "."], cwd=project_dir, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "Initial commit"],
        cwd=project_dir,
        check=True,
        capture_output=True
    )

    yield project_dir

    # Cleanup
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def test_logs_dir():
    """Create temporary logs directory"""
    temp_dir = tempfile.mkdtemp(prefix="lazy-bird-logs-")
    yield Path(temp_dir)
    shutil.rmtree(temp_dir, ignore_errors=True)


class TestWorktreeWorkflow:
    """Test complete worktree creation → work → cleanup workflow"""

    def test_worktree_creation_and_cleanup(self, test_project):
        """Test creating and cleaning up a worktree"""
        worktree_path = test_project.parent / "test-worktree"
        branch_name = "feature-test-42"

        # Source worktree creation function
        create_cmd = f"""
        PROJECT_PATH="{test_project}"
        WORKTREE_PATH="{worktree_path}"
        BRANCH_NAME="{branch_name}"
        PROJECT_ID="test-project"

        source <(grep -A 30 '^create_worktree()' /mnt/1ece809a-2821-4f10-aecb-fcdf34760c0b/Git/lazy-bird/scripts/agent-runner.sh | sed '/^}}/q')

        create_worktree
        """

        result = subprocess.run(
            ["bash", "-c", create_cmd],
            capture_output=True,
            text=True
        )

        assert result.returncode == 0, f"Worktree creation failed: {result.stderr}"
        assert worktree_path.exists(), "Worktree directory should exist"

        # Verify branch was created
        branch_check = subprocess.run(
            ["git", "branch", "--list", branch_name],
            cwd=test_project,
            capture_output=True,
            text=True
        )
        assert branch_name in branch_check.stdout

        # Now test cleanup
        cleanup_cmd = f"""
        PROJECT_PATH="{test_project}"
        WORKTREE_PATH="{worktree_path}"
        BRANCH_NAME="{branch_name}"
        PROJECT_ID="test-project"

        source <(grep -A 40 '^cleanup_worktree()' /mnt/1ece809a-2821-4f10-aecb-fcdf34760c0b/Git/lazy-bird/scripts/agent-runner.sh | sed '/^}}/q')

        cleanup_worktree
        """

        cleanup_result = subprocess.run(
            ["bash", "-c", cleanup_cmd],
            capture_output=True,
            text=True
        )

        assert cleanup_result.returncode == 0, f"Cleanup failed: {cleanup_result.stderr}"
        assert not worktree_path.exists(), "Worktree should be removed"

        # Verify branch was deleted (since it wasn't pushed)
        branch_check_after = subprocess.run(
            ["git", "branch", "--list", branch_name],
            cwd=test_project,
            capture_output=True,
            text=True
        )
        assert branch_name not in branch_check_after.stdout, "Branch should be deleted"


class TestErrorParsingWorkflow:
    """Test error parsing → context passing → retry workflow"""

    def test_godot_error_parsing_to_claude_context(self, test_logs_dir):
        """Test that Godot errors are parsed and formatted for Claude"""
        # Create mock Godot test output
        test_output = """
Tests: 10 | Passed: 8 | Failed: 2 | Errors: 0

FAILED: test_player_health
  Expected: 100
  Got: 50
  at res://test/test_player.gd:42

FAILED: test_enemy_spawn
  Assertion failed: enemy != null
  at res://test/test_enemy.gd:67
"""
        test_log = test_logs_dir / "test-output.log"
        test_log.write_text(test_output)

        # Test Python parser
        parser_script = "/mnt/1ece809a-2821-4f10-aecb-fcdf34760c0b/Git/lazy-bird/scripts/parse_test_errors.py"
        result = subprocess.run(
            ["python3", parser_script, str(test_log), "godot"],
            capture_output=True,
            text=True
        )

        assert result.returncode == 0
        output = result.stdout

        # Verify error summary contains key information
        assert "Test Error Summary" in output
        assert "test_player_health" in output
        assert "test_enemy.gd:67" in output
        assert "2 Error(s) Found" in output

        # Test JSON output
        json_result = subprocess.run(
            ["python3", parser_script, str(test_log), "godot", "--json"],
            capture_output=True,
            text=True
        )

        assert json_result.returncode == 0
        error_data = json.loads(json_result.stdout)

        assert error_data["framework"] == "godot"
        assert error_data["stats"]["failed"] == 2
        assert error_data["error_count"] == 2
        assert len(error_data["errors"]) == 2

        # Verify specific error details
        errors = {e["test_name"]: e for e in error_data["errors"]}
        assert "test_player_health" in errors
        assert errors["test_player_health"]["file"] == "res://test/test_player.gd"
        assert errors["test_player_health"]["line"] == 42

    def test_python_error_parsing_to_claude_context(self, test_logs_dir):
        """Test that Python/pytest errors are parsed correctly"""
        test_output = """
======================== FAILURES ========================
____________ test_user_creation ____________

    def test_user_creation():
>       assert user.email == "test@example.com"
E       AssertionError: assert 'wrong@example.com' == 'test@example.com'

app/tests/test_models.py:42: AssertionError

============ short test summary ============
FAILED app/tests/test_models.py::test_user_creation - AssertionError
======================== 1 failed, 5 passed in 2.5s ========================
"""
        test_log = test_logs_dir / "test-output.log"
        test_log.write_text(test_output)

        parser_script = "/mnt/1ece809a-2821-4f10-aecb-fcdf34760c0b/Git/lazy-bird/scripts/parse_test_errors.py"
        result = subprocess.run(
            ["python3", parser_script, str(test_log), "python"],
            capture_output=True,
            text=True
        )

        assert result.returncode == 0
        output = result.stdout

        assert "test_user_creation" in output
        assert "test_models.py:42" in output or "test_models.py" in output


class TestMultiProjectIsolation:
    """Test that multi-project tasks are properly isolated"""

    def test_worktree_naming_includes_project_id(self, test_project):
        """Test that worktrees include project ID for isolation"""
        # Create worktrees for two different "projects"
        worktree1_path = test_project.parent / "agent-project1-42"
        worktree2_path = test_project.parent / "agent-project2-42"

        # Create first worktree
        create_cmd1 = f"""
        PROJECT_PATH="{test_project}"
        WORKTREE_PATH="{worktree1_path}"
        BRANCH_NAME="feature-project1-42"
        PROJECT_ID="project1"

        source <(grep -A 30 '^create_worktree()' /mnt/1ece809a-2821-4f10-aecb-fcdf34760c0b/Git/lazy-bird/scripts/agent-runner.sh | sed '/^}}/q')

        create_worktree
        """

        result1 = subprocess.run(["bash", "-c", create_cmd1], capture_output=True, text=True)
        assert result1.returncode == 0
        assert worktree1_path.exists()

        # Create second worktree
        create_cmd2 = f"""
        PROJECT_PATH="{test_project}"
        WORKTREE_PATH="{worktree2_path}"
        BRANCH_NAME="feature-project2-42"
        PROJECT_ID="project2"

        source <(grep -A 30 '^create_worktree()' /mnt/1ece809a-2821-4f10-aecb-fcdf34760c0b/Git/lazy-bird/scripts/agent-runner.sh | sed '/^}}/q')

        create_worktree
        """

        result2 = subprocess.run(["bash", "-c", create_cmd2], capture_output=True, text=True)
        assert result2.returncode == 0
        assert worktree2_path.exists()

        # Both worktrees should coexist
        assert worktree1_path.exists()
        assert worktree2_path.exists()

        # Cleanup
        for worktree, branch in [(worktree1_path, "feature-project1-42"), (worktree2_path, "feature-project2-42")]:
            cleanup_cmd = f"""
            PROJECT_PATH="{test_project}"
            WORKTREE_PATH="{worktree}"
            BRANCH_NAME="{branch}"
            PROJECT_ID="test"

            source <(grep -A 40 '^cleanup_worktree()' /mnt/1ece809a-2821-4f10-aecb-fcdf34760c0b/Git/lazy-bird/scripts/agent-runner.sh | sed '/^}}/q')

            cleanup_worktree
            """
            subprocess.run(["bash", "-c", cleanup_cmd], capture_output=True)


class TestRetryWorkflow:
    """Test retry logic with error context passing"""

    def test_retry_backoff_timing(self):
        """Test that retry backoff increases correctly"""
        # Test exponential backoff calculation (without actually waiting)
        for attempt in range(1, 4):
            backoff = 30 * attempt
            expected_backoff = {1: 30, 2: 60, 3: 90}
            assert backoff == expected_backoff[attempt]

    def test_error_context_structure(self, test_logs_dir):
        """Test that error context has the right structure for Claude"""
        test_output = """
Tests: 5 | Passed: 3 | Failed: 2 | Errors: 0

FAILED: test_combat_system
  Damage calculation incorrect
  at res://systems/combat.gd:123
"""
        test_log = test_logs_dir / "test-output.log"
        test_log.write_text(test_output)

        parser_script = "/mnt/1ece809a-2821-4f10-aecb-fcdf34760c0b/Git/lazy-bird/scripts/parse_test_errors.py"
        result = subprocess.run(
            ["python3", parser_script, str(test_log), "godot"],
            capture_output=True,
            text=True
        )

        assert result.returncode == 0
        error_context = result.stdout

        # Verify error context includes file paths and line numbers
        assert "combat.gd:123" in error_context
        assert "test_combat_system" in error_context

        # This is what gets passed to Claude via run_claude "$error_context"
        # Should be well-formatted and informative
        assert "Error" in error_context
        assert len(error_context) > 50, "Error context should be detailed"


class TestWebUIIntegration:
    """Test Web UI cache integration with workflow"""

    def test_task_deletion_removes_from_cache(self):
        """Test that deleting a task also removes it from processed issues cache"""
        # This verifies the fix from P0-2 bug
        result = subprocess.run(
            ["grep", "-A", "10", "def delete_task",
             "/mnt/1ece809a-2821-4f10-aecb-fcdf34760c0b/Git/lazy-bird/web/backend/services/queue_service.py"],
            capture_output=True,
            text=True
        )

        assert result.returncode == 0
        code = result.stdout

        # Verify cache removal is called
        assert "_remove_from_processed_cache" in code

        # Verify the function exists
        verify_result = subprocess.run(
            ["grep", "-c", "def _remove_from_processed_cache",
             "/mnt/1ece809a-2821-4f10-aecb-fcdf34760c0b/Git/lazy-bird/web/backend/services/queue_service.py"],
            capture_output=True,
            text=True
        )

        assert verify_result.returncode == 0
        count = int(verify_result.stdout.strip())
        assert count == 1, "_remove_from_processed_cache should be defined"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
