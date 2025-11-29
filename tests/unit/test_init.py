"""
Unit tests for lazy_bird/__init__.py module
"""

import pytest
from pathlib import Path
import lazy_bird


class TestPackageMetadata:
    """Test package metadata and version information"""

    def test_version_exists(self):
        """Test that __version__ is defined"""
        assert hasattr(lazy_bird, '__version__')
        assert isinstance(lazy_bird.__version__, str)

    def test_version_format(self):
        """Test version follows semantic versioning"""
        version = lazy_bird.__version__
        parts = version.split('.')
        assert len(parts) >= 2, "Version should have at least major.minor"
        # Test that parts are numeric (or contain numeric parts)
        assert parts[0].isdigit(), "Major version should be numeric"
        assert parts[1].isdigit(), "Minor version should be numeric"

    def test_author_exists(self):
        """Test that __author__ is defined"""
        assert hasattr(lazy_bird, '__author__')
        assert isinstance(lazy_bird.__author__, str)
        assert len(lazy_bird.__author__) > 0

    def test_license_exists(self):
        """Test that __license__ is defined"""
        assert hasattr(lazy_bird, '__license__')
        assert lazy_bird.__license__ == 'MIT'


class TestPackagePaths:
    """Test package path constants"""

    def test_package_root_exists(self):
        """Test PACKAGE_ROOT is defined and exists"""
        assert hasattr(lazy_bird, 'PACKAGE_ROOT')
        assert isinstance(lazy_bird.PACKAGE_ROOT, Path)
        assert lazy_bird.PACKAGE_ROOT.exists()

    def test_package_root_is_directory(self):
        """Test PACKAGE_ROOT points to a directory"""
        assert lazy_bird.PACKAGE_ROOT.is_dir()

    def test_scripts_dir_defined(self):
        """Test SCRIPTS_DIR is defined"""
        assert hasattr(lazy_bird, 'SCRIPTS_DIR')
        assert isinstance(lazy_bird.SCRIPTS_DIR, Path)
        assert lazy_bird.SCRIPTS_DIR == lazy_bird.PACKAGE_ROOT / 'scripts'

    def test_config_dir_defined(self):
        """Test CONFIG_DIR is defined"""
        assert hasattr(lazy_bird, 'CONFIG_DIR')
        assert isinstance(lazy_bird.CONFIG_DIR, Path)
        assert lazy_bird.CONFIG_DIR == lazy_bird.PACKAGE_ROOT / 'config'

    def test_web_dir_defined(self):
        """Test WEB_DIR is defined"""
        assert hasattr(lazy_bird, 'WEB_DIR')
        assert isinstance(lazy_bird.WEB_DIR, Path)
        assert lazy_bird.WEB_DIR == lazy_bird.PACKAGE_ROOT / 'web'

    def test_docs_dir_defined(self):
        """Test DOCS_DIR is defined"""
        assert hasattr(lazy_bird, 'DOCS_DIR')
        assert isinstance(lazy_bird.DOCS_DIR, Path)
        assert lazy_bird.DOCS_DIR == lazy_bird.PACKAGE_ROOT / 'Docs'


class TestPackageExports:
    """Test __all__ exports"""

    def test_all_defined(self):
        """Test __all__ is defined"""
        assert hasattr(lazy_bird, '__all__')
        assert isinstance(lazy_bird.__all__, list)

    def test_all_contains_version(self):
        """Test __all__ exports version info"""
        assert '__version__' in lazy_bird.__all__
        assert '__author__' in lazy_bird.__all__
        assert '__license__' in lazy_bird.__all__

    def test_all_contains_paths(self):
        """Test __all__ exports path constants"""
        assert 'PACKAGE_ROOT' in lazy_bird.__all__
        assert 'SCRIPTS_DIR' in lazy_bird.__all__
        assert 'CONFIG_DIR' in lazy_bird.__all__
        assert 'WEB_DIR' in lazy_bird.__all__
        assert 'DOCS_DIR' in lazy_bird.__all__

    def test_all_items_exist(self):
        """Test all items in __all__ actually exist"""
        for item in lazy_bird.__all__:
            assert hasattr(lazy_bird, item), f"{item} in __all__ but not defined"
