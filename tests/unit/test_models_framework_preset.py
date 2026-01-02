"""Unit tests for FrameworkPreset model.

Tests FrameworkPreset model fields, methods, and built-in presets.
"""

from datetime import datetime, timezone
from uuid import uuid4

import pytest

from lazy_bird.models.framework_preset import FrameworkPreset


class TestFrameworkPresetCreation:
    """Test FrameworkPreset model creation and initialization."""

    def test_basic_creation(self):
        """Test creating a preset with minimum required fields."""
        preset = FrameworkPreset(
            name="custom-framework",
            display_name="Custom Framework",
            framework_type="backend",
            test_command="npm test",
        )

        assert preset.name == "custom-framework"
        assert preset.display_name == "Custom Framework"
        assert preset.framework_type == "backend"
        assert preset.test_command == "npm test"

    def test_creation_with_all_fields(self):
        """Test creating a preset with all fields."""
        preset_id = uuid4()

        preset = FrameworkPreset(
            id=preset_id,
            name="full-preset",
            display_name="Full Preset",
            description="A complete preset with all fields",
            framework_type="frontend",
            language="typescript",
            test_command="jest",
            build_command="webpack",
            lint_command="eslint .",
            format_command="prettier --write .",
            config_files={"package": "package.json", "tsconfig": "tsconfig.json"},
            is_builtin=True,
        )

        assert preset.id == preset_id
        assert preset.description == "A complete preset with all fields"
        assert preset.language == "typescript"
        assert preset.build_command == "webpack"
        assert preset.lint_command == "eslint ."
        assert preset.format_command == "prettier --write ."
        assert preset.config_files == {"package": "package.json", "tsconfig": "tsconfig.json"}
        assert preset.is_builtin is True

    def test_default_values(self):
        """Test that default values are set correctly when explicitly provided."""
        preset = FrameworkPreset(
            name="default-preset",
            display_name="Default Preset",
            framework_type="backend",
            test_command="pytest",
            is_builtin=False,
        )

        # Default value should be set as provided
        assert preset.is_builtin is False


class TestFrameworkPresetCommandCheckers:
    """Test has_*_command() methods."""

    def test_has_build_command_true(self):
        """Test has_build_command() returns True when command is set."""
        preset = FrameworkPreset(
            name="with-build",
            display_name="With Build",
            framework_type="backend",
            test_command="pytest",
            build_command="python setup.py build",
        )

        assert preset.has_build_command() is True

    def test_has_build_command_false_none(self):
        """Test has_build_command() returns False when command is None."""
        preset = FrameworkPreset(
            name="no-build",
            display_name="No Build",
            framework_type="backend",
            test_command="pytest",
            build_command=None,
        )

        assert preset.has_build_command() is False

    def test_has_build_command_false_empty_string(self):
        """Test has_build_command() returns False when command is empty string."""
        preset = FrameworkPreset(
            name="empty-build",
            display_name="Empty Build",
            framework_type="backend",
            test_command="pytest",
            build_command="   ",  # Whitespace only
        )

        assert preset.has_build_command() is False

    def test_has_lint_command_true(self):
        """Test has_lint_command() returns True when command is set."""
        preset = FrameworkPreset(
            name="with-lint",
            display_name="With Lint",
            framework_type="backend",
            test_command="pytest",
            lint_command="flake8 .",
        )

        assert preset.has_lint_command() is True

    def test_has_lint_command_false(self):
        """Test has_lint_command() returns False when command is None."""
        preset = FrameworkPreset(
            name="no-lint",
            display_name="No Lint",
            framework_type="backend",
            test_command="pytest",
            lint_command=None,
        )

        assert preset.has_lint_command() is False

    def test_has_format_command_true(self):
        """Test has_format_command() returns True when command is set."""
        preset = FrameworkPreset(
            name="with-format",
            display_name="With Format",
            framework_type="backend",
            test_command="pytest",
            format_command="black .",
        )

        assert preset.has_format_command() is True

    def test_has_format_command_false(self):
        """Test has_format_command() returns False when command is None."""
        preset = FrameworkPreset(
            name="no-format",
            display_name="No Format",
            framework_type="backend",
            test_command="pytest",
            format_command=None,
        )

        assert preset.has_format_command() is False


class TestFrameworkPresetConfigFiles:
    """Test config file getter/setter methods."""

    def test_get_config_file_existing_key(self):
        """Test get_config_file() returns value for existing key."""
        preset = FrameworkPreset(
            name="test-preset",
            display_name="Test Preset",
            framework_type="backend",
            test_command="pytest",
            config_files={"python": "pyproject.toml", "django": "manage.py"},
        )

        assert preset.get_config_file("python") == "pyproject.toml"
        assert preset.get_config_file("django") == "manage.py"

    def test_get_config_file_missing_key(self):
        """Test get_config_file() returns None for missing key."""
        preset = FrameworkPreset(
            name="test-preset",
            display_name="Test Preset",
            framework_type="backend",
            test_command="pytest",
            config_files={"python": "pyproject.toml"},
        )

        assert preset.get_config_file("missing") is None

    def test_get_config_file_with_default(self):
        """Test get_config_file() returns default for missing key."""
        preset = FrameworkPreset(
            name="test-preset",
            display_name="Test Preset",
            framework_type="backend",
            test_command="pytest",
            config_files={"python": "pyproject.toml"},
        )

        assert preset.get_config_file("missing", "default.txt") == "default.txt"

    def test_get_config_file_none_config_files(self):
        """Test get_config_file() returns default when config_files is None."""
        preset = FrameworkPreset(
            name="test-preset",
            display_name="Test Preset",
            framework_type="backend",
            test_command="pytest",
            config_files=None,
        )

        assert preset.get_config_file("any_key") is None
        assert preset.get_config_file("any_key", "default.txt") == "default.txt"

    def test_set_config_file_new_key(self):
        """Test set_config_file() adds new key to empty config_files."""
        preset = FrameworkPreset(
            name="test-preset",
            display_name="Test Preset",
            framework_type="backend",
            test_command="pytest",
            config_files=None,
        )

        preset.set_config_file("python", "pyproject.toml")

        assert preset.config_files == {"python": "pyproject.toml"}

    def test_set_config_file_update_existing(self):
        """Test set_config_file() updates existing key."""
        preset = FrameworkPreset(
            name="test-preset",
            display_name="Test Preset",
            framework_type="backend",
            test_command="pytest",
            config_files={"python": "setup.py"},
        )

        preset.set_config_file("python", "pyproject.toml")

        assert preset.config_files["python"] == "pyproject.toml"

    def test_set_config_file_add_to_existing(self):
        """Test set_config_file() adds to existing config_files."""
        preset = FrameworkPreset(
            name="test-preset",
            display_name="Test Preset",
            framework_type="backend",
            test_command="pytest",
            config_files={"python": "pyproject.toml"},
        )

        preset.set_config_file("django", "manage.py")

        assert preset.config_files == {"python": "pyproject.toml", "django": "manage.py"}


class TestFrameworkPresetToDictMethod:
    """Test to_dict() method."""

    def test_to_dict_minimal(self):
        """Test to_dict() with minimum fields."""
        preset = FrameworkPreset(
            name="minimal",
            display_name="Minimal Preset",
            framework_type="backend",
            test_command="pytest",
        )

        data = preset.to_dict()

        assert "name" in data
        assert data["name"] == "minimal"
        assert "display_name" in data
        assert data["display_name"] == "Minimal Preset"
        assert "test_command" in data
        assert data["test_command"] == "pytest"
        assert "config_files" in data
        assert data["config_files"] == {}  # Empty dict, not None

    def test_to_dict_complete(self):
        """Test to_dict() with all fields."""
        preset = FrameworkPreset(
            name="complete",
            display_name="Complete Preset",
            description="Full preset",
            framework_type="backend",
            language="python",
            test_command="pytest",
            build_command="python setup.py build",
            lint_command="flake8 .",
            format_command="black .",
            config_files={"python": "pyproject.toml"},
            is_builtin=True,
        )

        data = preset.to_dict()

        assert data["name"] == "complete"
        assert data["description"] == "Full preset"
        assert data["language"] == "python"
        assert data["build_command"] == "python setup.py build"
        assert data["lint_command"] == "flake8 ."
        assert data["format_command"] == "black ."
        assert data["config_files"] == {"python": "pyproject.toml"}
        assert data["is_builtin"] is True

    def test_to_dict_null_config_files(self):
        """Test to_dict() returns empty dict for None config_files."""
        preset = FrameworkPreset(
            name="test",
            display_name="Test",
            framework_type="backend",
            test_command="pytest",
            config_files=None,
        )

        data = preset.to_dict()

        assert data["config_files"] == {}  # Should be empty dict, not None


class TestFrameworkPresetRepr:
    """Test __repr__() method."""

    def test_repr(self):
        """Test __repr__() method."""
        preset = FrameworkPreset(
            name="godot",
            display_name="Godot Engine 4.x",
            framework_type="game_engine",
            test_command="godot --headless ...",
            is_builtin=True,
        )

        repr_string = repr(preset)

        assert "FrameworkPreset" in repr_string
        assert "godot" in repr_string
        assert "Godot Engine 4.x" in repr_string
        assert "game_engine" in repr_string
        assert "builtin=True" in repr_string


class TestFrameworkPresetBuiltinPresets:
    """Test built-in preset creation."""

    def test_create_builtin_presets_count(self):
        """Test create_builtin_presets() returns correct number of presets."""
        presets = FrameworkPreset.create_builtin_presets()

        # Should have 14 presets (as defined in the model)
        # 3 game engines + 4 backend + 4 frontend + 3 language = 14
        assert len(presets) >= 14  # At least 14, may be more

    def test_create_builtin_presets_all_builtin(self):
        """Test all presets from create_builtin_presets() are marked builtin."""
        presets = FrameworkPreset.create_builtin_presets()

        for preset in presets:
            assert preset.is_builtin is True

    def test_create_builtin_presets_unique_names(self):
        """Test all preset names are unique."""
        presets = FrameworkPreset.create_builtin_presets()

        names = [p.name for p in presets]
        assert len(names) == len(set(names))  # No duplicates

    def test_godot_preset_exists(self):
        """Test Godot preset exists and has correct values."""
        presets = FrameworkPreset.create_builtin_presets()

        godot_preset = next((p for p in presets if p.name == "godot"), None)

        assert godot_preset is not None
        assert godot_preset.display_name == "Godot Engine 4.x"
        assert godot_preset.framework_type == "game_engine"
        assert godot_preset.language == "gdscript"
        assert "gdUnit4" in godot_preset.test_command
        assert godot_preset.config_files.get("godot") == "project.godot"
        assert godot_preset.is_builtin is True

    def test_django_preset_exists(self):
        """Test Django preset exists and has correct values."""
        presets = FrameworkPreset.create_builtin_presets()

        django_preset = next((p for p in presets if p.name == "django"), None)

        assert django_preset is not None
        assert django_preset.display_name == "Django"
        assert django_preset.framework_type == "backend"
        assert django_preset.language == "python"
        assert django_preset.test_command == "pytest"
        assert django_preset.has_lint_command() is True
        assert django_preset.has_format_command() is True

    def test_react_preset_exists(self):
        """Test React preset exists and has correct values."""
        presets = FrameworkPreset.create_builtin_presets()

        react_preset = next((p for p in presets if p.name == "react"), None)

        assert react_preset is not None
        assert react_preset.display_name == "React + Vite"
        assert react_preset.framework_type == "frontend"
        assert react_preset.language == "javascript"
        assert react_preset.test_command == "npm test"
        assert react_preset.has_build_command() is True

    def test_rust_preset_exists(self):
        """Test Rust preset exists and has correct values."""
        presets = FrameworkPreset.create_builtin_presets()

        rust_preset = next((p for p in presets if p.name == "rust"), None)

        assert rust_preset is not None
        assert rust_preset.display_name == "Rust"
        assert rust_preset.framework_type == "language"
        assert rust_preset.language == "rust"
        assert rust_preset.test_command == "cargo test"
        assert rust_preset.has_lint_command() is True  # cargo clippy
        assert rust_preset.has_format_command() is True  # cargo fmt
