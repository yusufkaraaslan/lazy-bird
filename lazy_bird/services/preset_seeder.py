"""Seed framework presets from config/framework-presets.yml into the database.

This module reads the YAML preset definitions and upserts them into the
framework_presets table on application startup, ensuring the database
always reflects the latest preset configurations.
"""

import os
from pathlib import Path
from typing import Any, Dict, Tuple

import yaml
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from lazy_bird.core.logging import get_logger
from lazy_bird.models.framework_preset import FrameworkPreset

logger = get_logger(__name__)

# Mapping from YAML preset key to (framework_type, language)
PRESET_METADATA: Dict[str, Tuple[str, str]] = {
    # Game Engines
    "godot": ("game_engine", "gdscript"),
    "unity": ("game_engine", "csharp"),
    "unreal": ("game_engine", "cpp"),
    "bevy": ("game_engine", "rust"),
    # Backend Frameworks
    "django": ("backend", "python"),
    "flask": ("backend", "python"),
    "fastapi": ("backend", "python"),
    "express": ("backend", "javascript"),
    "rails": ("backend", "ruby"),
    # Frontend Frameworks
    "react": ("frontend", "javascript"),
    "vue": ("frontend", "javascript"),
    "angular": ("frontend", "typescript"),
    "svelte": ("frontend", "javascript"),
    # Languages
    "python": ("language", "python"),
    "rust": ("language", "rust"),
    "go": ("language", "go"),
    "nodejs": ("language", "javascript"),
    "cpp": ("language", "cpp"),
    "java": ("language", "java"),
    # Custom
    "custom": ("language", "other"),
}


def _get_presets_yaml_path() -> Path:
    """Resolve the path to framework-presets.yml.

    Looks relative to the project root (two levels up from this file's
    package directory), falling back to a LAZY_BIRD_PRESETS_PATH env var.

    Returns:
        Path to the framework-presets.yml file.
    """
    env_path = os.environ.get("LAZY_BIRD_PRESETS_PATH")
    if env_path:
        return Path(env_path)

    # Default: <project_root>/config/framework-presets.yml
    project_root = Path(__file__).resolve().parent.parent.parent
    return project_root / "config" / "framework-presets.yml"


def _load_presets_from_yaml(yaml_path: Path) -> Dict[str, Dict[str, Any]]:
    """Load and parse the framework presets YAML file.

    Args:
        yaml_path: Path to the YAML file.

    Returns:
        Dictionary of preset_key -> preset_data.

    Raises:
        FileNotFoundError: If the YAML file does not exist.
        yaml.YAMLError: If the YAML is malformed.
    """
    with open(yaml_path, "r") as f:
        data = yaml.safe_load(f)
    return data.get("presets", {})


def _yaml_preset_to_model_kwargs(key: str, preset_data: Dict[str, Any]) -> Dict[str, Any]:
    """Convert a YAML preset entry to FrameworkPreset constructor kwargs.

    Args:
        key: The preset identifier key from YAML (e.g. 'godot', 'django').
        preset_data: The preset data dictionary from YAML.

    Returns:
        Dictionary of keyword arguments for FrameworkPreset.
    """
    framework_type, language = PRESET_METADATA.get(key, ("language", "other"))

    return {
        "name": key,
        "display_name": preset_data.get("name", key.title()),
        "description": preset_data.get("description"),
        "framework_type": framework_type,
        "language": language,
        "test_command": preset_data.get("test_command", "make test"),
        "build_command": preset_data.get("build_command"),
        "lint_command": preset_data.get("lint_command"),
        "format_command": preset_data.get("format_command"),
        "config_files": {
            "file_extensions": preset_data.get("file_extensions", []),
            "ignore_patterns": preset_data.get("ignore_patterns", []),
            "docs_url": preset_data.get("docs_url"),
        },
        "is_builtin": True,
    }


async def seed_framework_presets(db: AsyncSession) -> Tuple[int, int]:
    """Seed framework presets from YAML into the database.

    For each preset in the YAML file:
    - If it does not exist (by name), create a new FrameworkPreset with is_builtin=True.
    - If it already exists, update its fields to match the YAML (upsert).

    Args:
        db: An async SQLAlchemy session.

    Returns:
        Tuple of (created_count, updated_count).
    """
    yaml_path = _get_presets_yaml_path()

    if not yaml_path.exists():
        logger.warning(f"Framework presets YAML not found at {yaml_path}, skipping seed")
        return (0, 0)

    try:
        presets_data = _load_presets_from_yaml(yaml_path)
    except Exception as e:
        logger.error(f"Failed to load framework presets YAML: {e}")
        return (0, 0)

    if not presets_data:
        logger.warning("No presets found in YAML file")
        return (0, 0)

    created = 0
    updated = 0

    for key, preset_data in presets_data.items():
        kwargs = _yaml_preset_to_model_kwargs(key, preset_data)

        # Check if preset already exists by name
        result = await db.execute(select(FrameworkPreset).where(FrameworkPreset.name == key))
        existing = result.scalar_one_or_none()

        if existing is None:
            # Create new preset
            preset = FrameworkPreset(**kwargs)
            db.add(preset)
            created += 1
            logger.debug(f"Created preset: {key}")
        else:
            # Update existing preset fields
            for field, value in kwargs.items():
                if field != "name":  # Don't update the key itself
                    setattr(existing, field, value)
            updated += 1
            logger.debug(f"Updated preset: {key}")

    await db.commit()

    logger.info(
        f"Framework presets seeded: {created} created, {updated} updated "
        f"(total: {len(presets_data)} presets in YAML)"
    )

    return (created, updated)
