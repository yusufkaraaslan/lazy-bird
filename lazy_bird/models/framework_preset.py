"""FrameworkPreset model - Framework-specific command presets.

This module defines the FrameworkPreset model which stores predefined
configurations for different frameworks (Godot, Django, React, etc.).
"""

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import Boolean, Column, DateTime, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from lazy_bird.core.database import Base


class FrameworkPreset(Base):
    """FrameworkPreset model for framework-specific configurations.

    A FrameworkPreset defines default commands and settings for a specific
    framework (e.g., Godot, Django, React). Lazy-Bird includes built-in
    presets for 15+ frameworks, and users can create custom presets.

    Attributes:
        id: Unique preset identifier (UUID)
        name: Internal preset name (unique, lowercase)
        display_name: Human-readable display name
        description: Preset description

        framework_type: Framework category (game_engine, backend, frontend, language)
        language: Programming language (gdscript, python, javascript, rust, etc.)

        test_command: Command to run tests (required)
        build_command: Command to build project (optional)
        lint_command: Command to lint code (optional)
        format_command: Command to format code (optional)

        config_files: JSON object with framework-specific configuration file paths

        is_builtin: Whether this is a built-in preset (cannot be deleted)
        created_at: Creation timestamp
        updated_at: Last update timestamp

        projects: Relationship to Project models using this preset
    """

    __tablename__ = "framework_presets"

    # -------------------------------------------------------------------------
    # PRIMARY KEY
    # -------------------------------------------------------------------------

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.gen_random_uuid(),
        nullable=False,
    )

    # -------------------------------------------------------------------------
    # BASIC INFORMATION
    # -------------------------------------------------------------------------

    name: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        nullable=False,
        comment="Internal preset name (lowercase, unique)"
    )

    display_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Human-readable display name"
    )

    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Preset description"
    )

    # -------------------------------------------------------------------------
    # FRAMEWORK DETAILS
    # -------------------------------------------------------------------------

    framework_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,  # idx_framework_presets_type
        comment="Framework category: game_engine, backend, frontend, language"
    )

    language: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        comment="Programming language: gdscript, python, javascript, rust, etc."
    )

    # -------------------------------------------------------------------------
    # DEFAULT COMMANDS
    # -------------------------------------------------------------------------

    test_command: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
        comment="Command to run tests (required)"
    )

    build_command: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
        comment="Command to build project (optional)"
    )

    lint_command: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
        comment="Command to lint code (optional)"
    )

    format_command: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
        comment="Command to format code (optional)"
    )

    # -------------------------------------------------------------------------
    # ADDITIONAL CONFIGURATION
    # -------------------------------------------------------------------------

    config_files: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=True,
        comment="JSON object with framework-specific config file paths"
    )

    # -------------------------------------------------------------------------
    # METADATA
    # -------------------------------------------------------------------------

    is_builtin: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default="false",
        default=False,
        index=True,  # idx_framework_presets_builtin
        comment="Built-in preset (cannot be deleted)"
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.current_timestamp(),
        default=func.current_timestamp(),
        comment="Creation timestamp"
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.current_timestamp(),
        default=func.current_timestamp(),
        onupdate=func.current_timestamp(),
        comment="Last update timestamp"
    )

    # -------------------------------------------------------------------------
    # RELATIONSHIPS
    # -------------------------------------------------------------------------

    # Projects using this preset (one-to-many)
    projects: Mapped[List["Project"]] = relationship(
        "Project",
        back_populates="framework_preset",
        foreign_keys="Project.framework_preset_id",
        lazy="dynamic",  # Return query object for filtering
    )

    # -------------------------------------------------------------------------
    # TABLE ARGUMENTS (indexes, constraints)
    # -------------------------------------------------------------------------

    __table_args__ = (
        # Index on framework_type (auto-created by index=True)
        # Index on is_builtin (auto-created by index=True)

        # Table comment
        {"comment": "Framework-specific command presets and configurations"},
    )

    # -------------------------------------------------------------------------
    # METHODS
    # -------------------------------------------------------------------------

    def __repr__(self) -> str:
        """String representation of FrameworkPreset."""
        return (
            f"<FrameworkPreset(id={self.id}, name='{self.name}', "
            f"display_name='{self.display_name}', type='{self.framework_type}', "
            f"builtin={self.is_builtin})>"
        )

    def has_build_command(self) -> bool:
        """Check if preset has a build command.

        Returns:
            bool: True if build_command is set, False otherwise
        """
        return self.build_command is not None and self.build_command.strip() != ""

    def has_lint_command(self) -> bool:
        """Check if preset has a lint command.

        Returns:
            bool: True if lint_command is set, False otherwise
        """
        return self.lint_command is not None and self.lint_command.strip() != ""

    def has_format_command(self) -> bool:
        """Check if preset has a format command.

        Returns:
            bool: True if format_command is set, False otherwise
        """
        return self.format_command is not None and self.format_command.strip() != ""

    def get_config_file(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """Get a specific config file path from config_files JSON.

        Args:
            key: Config file key (e.g., 'godot', 'python', 'package_json')
            default: Default value if key not found

        Returns:
            Optional[str]: Config file path or default

        Example:
            >>> preset.config_files = {"godot": "project.godot", "python": "pyproject.toml"}
            >>> preset.get_config_file("godot")
            'project.godot'
            >>> preset.get_config_file("missing", "default.txt")
            'default.txt'
        """
        if not self.config_files:
            return default
        return self.config_files.get(key, default)

    def set_config_file(self, key: str, value: str) -> None:
        """Set a config file path in config_files JSON.

        Args:
            key: Config file key
            value: File path

        Example:
            >>> preset.set_config_file("godot", "project.godot")
            >>> preset.config_files
            {"godot": "project.godot"}
        """
        if self.config_files is None:
            self.config_files = {}
        self.config_files[key] = value
        # Mark as modified for SQLAlchemy to detect change
        # (JSONB columns need special handling)
        from sqlalchemy.orm.attributes import flag_modified
        from sqlalchemy import inspect

        # Only flag if object is in session
        session = inspect(self).session
        if session:
            flag_modified(self, "config_files")

    def to_dict(self) -> dict:
        """Convert preset to dictionary for API responses.

        Returns:
            dict: Preset data as dictionary

        Example:
            >>> preset.to_dict()
            {
                'id': '123e4567-e89b-12d3-a456-426614174000',
                'name': 'godot',
                'display_name': 'Godot Engine 4.x',
                'framework_type': 'game_engine',
                'test_command': 'godot --headless -s ...',
                ...
            }
        """
        return {
            "id": str(self.id),
            "name": self.name,
            "display_name": self.display_name,
            "description": self.description,
            "framework_type": self.framework_type,
            "language": self.language,
            "test_command": self.test_command,
            "build_command": self.build_command,
            "lint_command": self.lint_command,
            "format_command": self.format_command,
            "config_files": self.config_files or {},
            "is_builtin": self.is_builtin,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    @staticmethod
    def create_builtin_presets() -> List["FrameworkPreset"]:
        """Create list of built-in framework presets.

        Returns:
            List[FrameworkPreset]: All built-in presets

        Example:
            >>> from lazy_bird.core import SessionLocal
            >>> from lazy_bird.models import FrameworkPreset
            >>>
            >>> with SessionLocal() as db:
            ...     presets = FrameworkPreset.create_builtin_presets()
            ...     db.add_all(presets)
            ...     db.commit()
        """
        return [
            # ================================================================
            # GAME ENGINES
            # ================================================================
            FrameworkPreset(
                name="godot",
                display_name="Godot Engine 4.x",
                description="Open-source game engine with GDScript",
                framework_type="game_engine",
                language="gdscript",
                test_command="godot --headless -s addons/gdUnit4/bin/GdUnitCmdTool.gd --test-suite all",
                build_command='godot --headless --export-release "Linux/X11" build/game.x86_64',
                config_files={"godot": "project.godot"},
                is_builtin=True,
            ),
            FrameworkPreset(
                name="unity",
                display_name="Unity",
                description="Popular game engine with C# scripting",
                framework_type="game_engine",
                language="csharp",
                test_command="unity-editor -runTests -batchmode -projectPath .",
                build_command="unity-editor -quit -batchmode -projectPath . -buildLinux64Player build/game",
                config_files={"unity": "ProjectSettings/ProjectSettings.asset"},
                is_builtin=True,
            ),
            FrameworkPreset(
                name="bevy",
                display_name="Bevy Engine",
                description="Rust game engine",
                framework_type="game_engine",
                language="rust",
                test_command="cargo test",
                build_command="cargo build --release",
                config_files={"cargo": "Cargo.toml"},
                is_builtin=True,
            ),
            # ================================================================
            # BACKEND FRAMEWORKS
            # ================================================================
            FrameworkPreset(
                name="django",
                display_name="Django",
                description="Python web framework",
                framework_type="backend",
                language="python",
                test_command="pytest",
                build_command="python manage.py collectstatic --noinput",
                lint_command="pylint *.py",
                format_command="black .",
                config_files={"python": "pyproject.toml", "django": "manage.py"},
                is_builtin=True,
            ),
            FrameworkPreset(
                name="fastapi",
                display_name="FastAPI",
                description="Modern Python API framework",
                framework_type="backend",
                language="python",
                test_command="pytest",
                lint_command="flake8 .",
                format_command="black .",
                config_files={"python": "pyproject.toml"},
                is_builtin=True,
            ),
            FrameworkPreset(
                name="flask",
                display_name="Flask",
                description="Lightweight Python web framework",
                framework_type="backend",
                language="python",
                test_command="pytest",
                lint_command="flake8 .",
                format_command="black .",
                config_files={"python": "pyproject.toml"},
                is_builtin=True,
            ),
            FrameworkPreset(
                name="rails",
                display_name="Ruby on Rails",
                description="Ruby web framework",
                framework_type="backend",
                language="ruby",
                test_command="rails test",
                lint_command="rubocop",
                config_files={"ruby": "Gemfile"},
                is_builtin=True,
            ),
            # ================================================================
            # FRONTEND FRAMEWORKS
            # ================================================================
            FrameworkPreset(
                name="react",
                display_name="React + Vite",
                description="React with Vite build tool",
                framework_type="frontend",
                language="javascript",
                test_command="npm test",
                build_command="npm run build",
                lint_command="npm run lint",
                format_command="npm run format",
                config_files={"package": "package.json", "vite": "vite.config.js"},
                is_builtin=True,
            ),
            FrameworkPreset(
                name="vue",
                display_name="Vue.js",
                description="Progressive JavaScript framework",
                framework_type="frontend",
                language="javascript",
                test_command="npm test",
                build_command="npm run build",
                lint_command="npm run lint",
                config_files={"package": "package.json"},
                is_builtin=True,
            ),
            FrameworkPreset(
                name="angular",
                display_name="Angular",
                description="TypeScript-based web framework",
                framework_type="frontend",
                language="typescript",
                test_command="ng test",
                build_command="ng build --prod",
                lint_command="ng lint",
                config_files={"package": "package.json", "angular": "angular.json"},
                is_builtin=True,
            ),
            FrameworkPreset(
                name="svelte",
                display_name="Svelte",
                description="Compiler-based JavaScript framework",
                framework_type="frontend",
                language="javascript",
                test_command="npm test",
                build_command="npm run build",
                lint_command="npm run lint",
                config_files={"package": "package.json", "svelte": "svelte.config.js"},
                is_builtin=True,
            ),
            # ================================================================
            # LANGUAGES (generic)
            # ================================================================
            FrameworkPreset(
                name="python",
                display_name="Python (Generic)",
                description="Generic Python project",
                framework_type="language",
                language="python",
                test_command="pytest",
                lint_command="flake8 .",
                format_command="black .",
                config_files={"python": "pyproject.toml"},
                is_builtin=True,
            ),
            FrameworkPreset(
                name="rust",
                display_name="Rust",
                description="Rust programming language",
                framework_type="language",
                language="rust",
                test_command="cargo test",
                build_command="cargo build --release",
                lint_command="cargo clippy",
                format_command="cargo fmt",
                config_files={"cargo": "Cargo.toml"},
                is_builtin=True,
            ),
            FrameworkPreset(
                name="nodejs",
                display_name="Node.js",
                description="JavaScript runtime",
                framework_type="language",
                language="javascript",
                test_command="npm test",
                lint_command="npm run lint",
                format_command="npm run format",
                config_files={"package": "package.json"},
                is_builtin=True,
            ),
            FrameworkPreset(
                name="go",
                display_name="Go",
                description="Go programming language",
                framework_type="language",
                language="go",
                test_command="go test ./...",
                build_command="go build",
                lint_command="golangci-lint run",
                format_command="go fmt ./...",
                config_files={"go": "go.mod"},
                is_builtin=True,
            ),
        ]
