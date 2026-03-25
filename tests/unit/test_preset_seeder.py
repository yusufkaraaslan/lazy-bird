"""Unit tests for preset_seeder service.

Tests seeding of framework presets from YAML into the database.
Uses mocking to avoid actual database/file dependencies.
"""

import os
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, mock_open, patch

import pytest
import yaml

from lazy_bird.models.framework_preset import FrameworkPreset
from lazy_bird.services.preset_seeder import (
    PRESET_METADATA,
    _get_presets_yaml_path,
    _load_presets_from_yaml,
    _yaml_preset_to_model_kwargs,
    seed_framework_presets,
)

# ---------------------------------------------------------------------------
# Sample YAML data for tests
# ---------------------------------------------------------------------------

SAMPLE_PRESETS_YAML = {
    "presets": {
        "godot": {
            "name": "Godot Engine",
            "description": "GDScript game engine with gdUnit4 testing",
            "test_command": "godot --headless -s addons/gdUnit4/bin/GdUnitCmdTool.gd",
            "build_command": None,
            "lint_command": None,
            "format_command": None,
            "file_extensions": [".gd", ".tscn", ".tres", ".godot"],
            "ignore_patterns": [".godot/", ".import/", "*.import"],
            "docs_url": "https://godotengine.org/",
        },
        "django": {
            "name": "Django",
            "description": "Python web framework",
            "test_command": "python manage.py test",
            "build_command": None,
            "lint_command": "flake8 .",
            "format_command": "black .",
            "file_extensions": [".py", ".html", ".css", ".js"],
            "ignore_patterns": ["__pycache__/", "*.pyc"],
            "docs_url": "https://www.djangoproject.com/",
        },
    }
}


class TestGetPresetsYamlPath:
    """Tests for _get_presets_yaml_path."""

    def test_default_path(self):
        """Test default path resolution relative to project root."""
        with patch.dict(os.environ, {}, clear=False):
            # Remove env var if it exists
            os.environ.pop("LAZY_BIRD_PRESETS_PATH", None)
            path = _get_presets_yaml_path()
            assert path.name == "framework-presets.yml"
            assert "config" in str(path)

    def test_env_var_override(self):
        """Test that LAZY_BIRD_PRESETS_PATH env var overrides default."""
        with patch.dict(os.environ, {"LAZY_BIRD_PRESETS_PATH": "/custom/path.yml"}):
            path = _get_presets_yaml_path()
            assert path == Path("/custom/path.yml")


class TestLoadPresetsFromYaml:
    """Tests for _load_presets_from_yaml."""

    def test_load_valid_yaml(self, tmp_path):
        """Test loading a valid YAML file returns presets dict."""
        yaml_file = tmp_path / "presets.yml"
        yaml_file.write_text(yaml.dump(SAMPLE_PRESETS_YAML))

        result = _load_presets_from_yaml(yaml_file)
        assert "godot" in result
        assert "django" in result
        assert result["godot"]["name"] == "Godot Engine"

    def test_load_empty_yaml(self, tmp_path):
        """Test loading YAML with no presets key returns empty dict."""
        yaml_file = tmp_path / "empty.yml"
        yaml_file.write_text("other_key: value\n")

        result = _load_presets_from_yaml(yaml_file)
        assert result == {}

    def test_load_nonexistent_file(self):
        """Test loading a nonexistent file raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            _load_presets_from_yaml(Path("/nonexistent/path.yml"))


class TestYamlPresetToModelKwargs:
    """Tests for _yaml_preset_to_model_kwargs."""

    def test_godot_preset_mapping(self):
        """Test mapping of godot preset to model kwargs."""
        preset_data = SAMPLE_PRESETS_YAML["presets"]["godot"]
        kwargs = _yaml_preset_to_model_kwargs("godot", preset_data)

        assert kwargs["name"] == "godot"
        assert kwargs["display_name"] == "Godot Engine"
        assert kwargs["description"] == "GDScript game engine with gdUnit4 testing"
        assert kwargs["framework_type"] == "game_engine"
        assert kwargs["language"] == "gdscript"
        assert kwargs["test_command"] == "godot --headless -s addons/gdUnit4/bin/GdUnitCmdTool.gd"
        assert kwargs["build_command"] is None
        assert kwargs["lint_command"] is None
        assert kwargs["format_command"] is None
        assert kwargs["is_builtin"] is True
        assert ".gd" in kwargs["config_files"]["file_extensions"]

    def test_django_preset_mapping(self):
        """Test mapping of django preset to model kwargs."""
        preset_data = SAMPLE_PRESETS_YAML["presets"]["django"]
        kwargs = _yaml_preset_to_model_kwargs("django", preset_data)

        assert kwargs["name"] == "django"
        assert kwargs["framework_type"] == "backend"
        assert kwargs["language"] == "python"
        assert kwargs["test_command"] == "python manage.py test"
        assert kwargs["lint_command"] == "flake8 ."
        assert kwargs["format_command"] == "black ."
        assert kwargs["is_builtin"] is True

    def test_unknown_preset_gets_default_metadata(self):
        """Test that an unknown preset key gets default framework_type and language."""
        kwargs = _yaml_preset_to_model_kwargs(
            "unknown_framework",
            {"name": "Unknown", "test_command": "test"},
        )
        assert kwargs["framework_type"] == "language"
        assert kwargs["language"] == "other"
        assert kwargs["is_builtin"] is True

    def test_is_builtin_always_true(self):
        """Test that is_builtin flag is always set to True for seeded presets."""
        for key in ["godot", "django", "react", "python"]:
            preset_data = {"name": key.title(), "test_command": "test"}
            kwargs = _yaml_preset_to_model_kwargs(key, preset_data)
            assert kwargs["is_builtin"] is True


class TestPresetMetadata:
    """Tests for PRESET_METADATA completeness."""

    def test_all_yaml_presets_have_metadata(self):
        """Test that all presets in the real YAML file have metadata entries."""
        yaml_path = (
            Path(__file__).resolve().parent.parent.parent / "config" / "framework-presets.yml"
        )
        if not yaml_path.exists():
            pytest.skip("framework-presets.yml not found")

        presets_data = _load_presets_from_yaml(yaml_path)
        for key in presets_data:
            assert key in PRESET_METADATA, f"Preset '{key}' in YAML has no entry in PRESET_METADATA"

    def test_metadata_values_are_valid(self):
        """Test that all metadata entries have valid framework_type values."""
        valid_types = {"game_engine", "backend", "frontend", "language"}
        for key, (fw_type, lang) in PRESET_METADATA.items():
            assert fw_type in valid_types, f"Preset '{key}' has invalid framework_type: {fw_type}"
            assert (
                isinstance(lang, str) and len(lang) > 0
            ), f"Preset '{key}' has invalid language: {lang}"


@pytest.mark.asyncio
class TestSeedFrameworkPresets:
    """Tests for seed_framework_presets async function."""

    @staticmethod
    def _make_mock_session(execute_return=None):
        """Create a mock async session with sync add() method."""
        mock_session = AsyncMock()
        # db.add() is synchronous in SQLAlchemy, so use MagicMock
        mock_session.add = MagicMock()
        if execute_return is not None:
            mock_session.execute.return_value = execute_return
        return mock_session

    async def test_seed_into_empty_database(self, tmp_path):
        """Test seeding into an empty database creates all presets."""
        yaml_file = tmp_path / "presets.yml"
        yaml_file.write_text(yaml.dump(SAMPLE_PRESETS_YAML))

        # Simulate no existing presets (empty DB)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session = self._make_mock_session(mock_result)

        with patch(
            "lazy_bird.services.preset_seeder._get_presets_yaml_path",
            return_value=yaml_file,
        ):
            created, updated = await seed_framework_presets(mock_session)

        assert created == 2  # godot + django
        assert updated == 0
        # Verify db.add was called for each new preset
        assert mock_session.add.call_count == 2
        # Verify commit was called
        mock_session.commit.assert_awaited_once()

    async def test_seed_is_idempotent(self, tmp_path):
        """Test running seed twice doesn't duplicate presets."""
        yaml_file = tmp_path / "presets.yml"
        yaml_file.write_text(yaml.dump(SAMPLE_PRESETS_YAML))

        # Mock session where all presets already exist
        existing_preset = MagicMock(spec=FrameworkPreset)
        existing_preset.name = "godot"
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = existing_preset
        mock_session = self._make_mock_session(mock_result)

        with patch(
            "lazy_bird.services.preset_seeder._get_presets_yaml_path",
            return_value=yaml_file,
        ):
            created, updated = await seed_framework_presets(mock_session)

        assert created == 0
        assert updated == 2  # Both should be updated, not created
        # db.add should NOT be called (no new presets)
        mock_session.add.assert_not_called()
        mock_session.commit.assert_awaited_once()

    async def test_presets_match_yaml_data(self, tmp_path):
        """Test that created presets have correct data from YAML."""
        yaml_file = tmp_path / "presets.yml"
        yaml_file.write_text(yaml.dump(SAMPLE_PRESETS_YAML))

        created_presets = []

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session = self._make_mock_session(mock_result)

        def capture_add(preset):
            created_presets.append(preset)

        mock_session.add.side_effect = capture_add

        with patch(
            "lazy_bird.services.preset_seeder._get_presets_yaml_path",
            return_value=yaml_file,
        ):
            await seed_framework_presets(mock_session)

        assert len(created_presets) == 2

        # Find the godot preset
        godot = next(p for p in created_presets if p.name == "godot")
        assert godot.display_name == "Godot Engine"
        assert godot.framework_type == "game_engine"
        assert godot.language == "gdscript"
        assert godot.test_command == "godot --headless -s addons/gdUnit4/bin/GdUnitCmdTool.gd"
        assert godot.is_builtin is True

        # Find the django preset
        django = next(p for p in created_presets if p.name == "django")
        assert django.display_name == "Django"
        assert django.framework_type == "backend"
        assert django.language == "python"
        assert django.test_command == "python manage.py test"
        assert django.lint_command == "flake8 ."
        assert django.is_builtin is True

    async def test_is_builtin_flag_set(self, tmp_path):
        """Test that all seeded presets have is_builtin=True."""
        yaml_file = tmp_path / "presets.yml"
        yaml_file.write_text(yaml.dump(SAMPLE_PRESETS_YAML))

        created_presets = []
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session = self._make_mock_session(mock_result)
        mock_session.add.side_effect = lambda p: created_presets.append(p)

        with patch(
            "lazy_bird.services.preset_seeder._get_presets_yaml_path",
            return_value=yaml_file,
        ):
            await seed_framework_presets(mock_session)

        for preset in created_presets:
            assert preset.is_builtin is True, f"Preset '{preset.name}' should have is_builtin=True"

    async def test_missing_yaml_file_returns_zero(self):
        """Test that a missing YAML file returns (0, 0) without error."""
        mock_session = AsyncMock()

        with patch(
            "lazy_bird.services.preset_seeder._get_presets_yaml_path",
            return_value=Path("/nonexistent/presets.yml"),
        ):
            created, updated = await seed_framework_presets(mock_session)

        assert created == 0
        assert updated == 0
        mock_session.commit.assert_not_awaited()

    async def test_malformed_yaml_returns_zero(self, tmp_path):
        """Test that malformed YAML returns (0, 0) without crashing."""
        yaml_file = tmp_path / "bad.yml"
        yaml_file.write_text("{{invalid yaml: [")

        mock_session = AsyncMock()

        with patch(
            "lazy_bird.services.preset_seeder._get_presets_yaml_path",
            return_value=yaml_file,
        ):
            created, updated = await seed_framework_presets(mock_session)

        assert created == 0
        assert updated == 0

    async def test_update_existing_preset_fields(self, tmp_path):
        """Test that existing presets get their fields updated."""
        yaml_file = tmp_path / "presets.yml"
        # Only one preset for simplicity
        single_preset = {
            "presets": {
                "django": {
                    "name": "Django Updated",
                    "description": "Updated description",
                    "test_command": "pytest --new-flag",
                    "build_command": None,
                    "lint_command": "ruff check .",
                    "format_command": "ruff format .",
                    "file_extensions": [".py"],
                    "ignore_patterns": [],
                    "docs_url": "https://www.djangoproject.com/",
                },
            }
        }
        yaml_file.write_text(yaml.dump(single_preset))

        existing_preset = MagicMock(spec=FrameworkPreset)
        existing_preset.name = "django"
        existing_preset.display_name = "Django Old"
        existing_preset.test_command = "python manage.py test"

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = existing_preset
        mock_session = self._make_mock_session(mock_result)

        with patch(
            "lazy_bird.services.preset_seeder._get_presets_yaml_path",
            return_value=yaml_file,
        ):
            created, updated = await seed_framework_presets(mock_session)

        assert created == 0
        assert updated == 1
        # Verify fields were updated via setattr
        assert existing_preset.display_name == "Django Updated"
        assert existing_preset.test_command == "pytest --new-flag"
        assert existing_preset.lint_command == "ruff check ."
        assert existing_preset.is_builtin is True
