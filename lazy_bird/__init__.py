"""
Lazy_Bird - Automate development projects with Claude Code

A progressive automation system that enables Claude Code instances to work
on software development tasks autonomously. Supports 15+ frameworks including
Godot, Unity, Python, Rust, React, Django, and more.
"""

__version__ = "0.1.0"
__author__ = "Yusuf Karaaslan"
__license__ = "MIT"

from pathlib import Path

# Package root directory
PACKAGE_ROOT = Path(__file__).parent.parent

# Common directories
SCRIPTS_DIR = PACKAGE_ROOT / "scripts"
CONFIG_DIR = PACKAGE_ROOT / "config"
WEB_DIR = PACKAGE_ROOT / "web"
DOCS_DIR = PACKAGE_ROOT / "Docs"

__all__ = [
    "__version__",
    "__author__",
    "__license__",
    "PACKAGE_ROOT",
    "SCRIPTS_DIR",
    "CONFIG_DIR",
    "WEB_DIR",
    "DOCS_DIR",
]
