# Lazy_Bird Test Suite

Comprehensive unit and integration tests for the lazy-bird package with 70%+ code coverage.

## Table of Contents

- [Quick Start](#quick-start)
- [Test Structure](#test-structure)
- [Running Tests](#running-tests)
- [Writing Tests](#writing-tests)
- [Coverage](#coverage)
- [Continuous Integration](#continuous-integration)

## Quick Start

```bash
# Install test dependencies
pip install pytest pytest-cov

# Run all tests
pytest

# Run with coverage report
pytest --cov=lazy_bird --cov-report=html

# Run specific test file
pytest tests/unit/test_init.py -v

# Run specific test class
pytest tests/unit/test_cli.py::TestPrintBanner -v

# Run specific test
pytest tests/unit/test_init.py::TestPackageMetadata::test_version_exists -v
```

## Test Structure

```
tests/
├── __init__.py                  # Test package initialization
├── conftest.py                  # Shared fixtures and configuration
├── README.md                    # This file
│
├── unit/                        # Unit tests (fast, isolated)
│   ├── __init__.py
│   ├── test_init.py            # Tests for lazy_bird/__init__.py
│   ├── test_cli.py             # Tests for lazy_bird/cli.py
│   ├── test_project_manager.py # Tests for project-manager.py
│   └── test_issue_watcher.py   # Tests for issue-watcher.py
│
├── integration/                 # Integration tests (slower)
│   └── __init__.py
│
└── fixtures/                    # Test data and fixtures
```

## Running Tests

### Basic Commands

```bash
# Run all tests
pytest

# Run with verbose output
pytest -v

# Run only unit tests
pytest tests/unit/

# Run only integration tests
pytest tests/integration/

# Stop at first failure
pytest -x

# Run last failed tests
pytest --lf

# Run tests matching pattern
pytest -k "test_version"
```

### Coverage Reports

```bash
# Terminal coverage report
pytest --cov=lazy_bird --cov-report=term-missing

# HTML coverage report (opens in browser)
pytest --cov=lazy_bird --cov-report=html
open htmlcov/index.html

# XML coverage report (for CI)
pytest --cov=lazy_bird --cov-report=xml

# Combined report types
pytest --cov=lazy_bird --cov-report=term --cov-report=html --cov-report=xml
```

### Test Markers

Tests are marked with categories for selective running:

```bash
# Run only unit tests
pytest -m unit

# Run only integration tests
pytest -m integration

# Run all except slow tests
pytest -m "not slow"

# Run only script tests
pytest -m scripts
```

Available markers:
- `unit`: Fast, isolated unit tests
- `integration`: Integration tests requiring services
- `slow`: Tests that take >5 seconds
- `scripts`: Tests for scripts in scripts/ directory

## Writing Tests

### Test File Naming

- Test files: `test_*.py` or `*_test.py`
- Test classes: `Test*`
- Test functions: `test_*`

### Example Unit Test

```python
import pytest
from lazy_bird import __version__

class TestVersion:
    """Test version functionality"""

    def test_version_exists(self):
        """Test that version is defined"""
        assert __version__ is not None
        assert isinstance(__version__, str)

    def test_version_format(self):
        """Test version follows semantic versioning"""
        parts = __version__.split('.')
        assert len(parts) >= 2
```

### Using Fixtures

```python
def test_with_temp_dir(temp_dir):
    """Test using temporary directory fixture"""
    test_file = temp_dir / 'test.txt'
    test_file.write_text('test content')
    assert test_file.exists()
```

Available fixtures (see `conftest.py`):
- `temp_dir`: Temporary directory (auto-cleaned)
- `mock_config`: Mock lazy-bird configuration
- `mock_project_config`: Mock project configuration
- `mock_multi_project_config`: Multi-project configuration
- `mock_github_issue`: Mock GitHub issue data
- `mock_gitlab_issue`: Mock GitLab issue data
- `mock_test_job`: Mock Godot server test job
- `secrets_dir`: Mock secrets directory with tokens
- `mock_package_root`: Mock package root structure

### Mocking External Dependencies

```python
from unittest.mock import Mock, patch

def test_with_mocked_requests(mock_requests):
    """Test using mocked requests"""
    import requests
    response = requests.get('https://api.github.com/test')
    assert response.status_code == 200
```

### Testing CLI Commands

```python
def test_cli_command(capsys):
    """Test CLI output"""
    from lazy_bird import cli
    cli.print_banner()
    captured = capsys.readouterr()
    assert 'Version:' in captured.out
```

## Coverage

### Current Coverage

Run this command to see current coverage:

```bash
pytest --cov=lazy_bird --cov-report=term-missing
```

### Coverage Goals

- **Overall Target**: 70%+ code coverage
- **Core Modules**: 80%+ coverage
  - `lazy_bird/__init__.py`: 100%
  - `lazy_bird/cli.py`: Target 80%
- **Scripts**: 70%+ coverage
  - `scripts/godot-server.py`
  - `scripts/issue-watcher.py`
  - `scripts/project-manager.py`

### Improving Coverage

1. **Identify uncovered code**:
   ```bash
   pytest --cov=lazy_bird --cov-report=html
   open htmlcov/index.html
   ```

2. **Write tests for uncovered lines**

3. **Use coverage markers** to track progress:
   ```python
   # pragma: no cover  # Exclude specific lines
   ```

## Continuous Integration

### GitHub Actions

Tests run automatically on:
- Push to `main` branch
- Pull requests
- Release tags

### Local CI Simulation

```bash
# Run full test suite as CI does
pytest --cov=lazy_bird --cov-report=xml --cov-report=term -v

# Check if coverage meets threshold
pytest --cov=lazy_bird --cov-fail-under=70
```

## Test Development Workflow

1. **Write failing test first** (TDD):
   ```bash
   pytest tests/unit/test_new_feature.py -x
   ```

2. **Implement feature**

3. **Run tests until they pass**:
   ```bash
   pytest tests/unit/test_new_feature.py -v
   ```

4. **Check coverage**:
   ```bash
   pytest tests/unit/test_new_feature.py --cov=lazy_bird.new_module
   ```

5. **Run full suite**:
   ```bash
   pytest
   ```

## Troubleshooting

### Common Issues

**Import errors**:
```bash
# Make sure lazy_bird is installed in development mode
pip install -e .
```

**Fixture not found**:
```bash
# Check conftest.py for available fixtures
pytest --fixtures
```

**Coverage not working**:
```bash
# Install pytest-cov
pip install pytest-cov

# Or on Arch Linux
sudo pacman -S python-pytest-cov
```

**Tests hang**:
```bash
# Use timeout
pytest --timeout=300

# Or run with -x to stop at first failure
pytest -x
```

### Debugging Tests

```bash
# Show print statements
pytest -s

# Start debugger on failure
pytest --pdb

# Show local variables in traceback
pytest -l

# Full traceback
pytest --tb=long
```

## Best Practices

1. **Keep tests fast**: Unit tests should run in milliseconds
2. **One assertion per test**: Focus tests on single behavior
3. **Use descriptive names**: `test_version_format()` not `test_version()`
4. **Mock external dependencies**: Don't hit real APIs in tests
5. **Clean up resources**: Use fixtures for setup/teardown
6. **Test edge cases**: Empty inputs, None values, errors
7. **Use parametrize for similar tests**:
   ```python
   @pytest.mark.parametrize("version,expected", [
       ("0.1.0", True),
       ("1.0.0", True),
       ("invalid", False),
   ])
   def test_version_validation(version, expected):
       assert validate_version(version) == expected
   ```

## Resources

- [pytest Documentation](https://docs.pytest.org/)
- [pytest-cov Documentation](https://pytest-cov.readthedocs.io/)
- [Testing Best Practices](https://docs.pytest.org/en/latest/goodpractices.html)
- [Python Testing with pytest (Book)](https://pragprog.com/titles/bopytest/python-testing-with-pytest/)

## Contributing

When contributing tests:

1. Follow the existing test structure
2. Add tests for all new features
3. Maintain or improve code coverage
4. Run full test suite before submitting PR
5. Update this README if adding new test categories

```bash
# Pre-commit checklist
pytest --cov=lazy_bird --cov-fail-under=70
pytest -v
```

---

**Last Updated**: 2025-11-29
**Test Framework**: pytest 8.4+
**Coverage Tool**: pytest-cov 6.1+
**Python Version**: 3.8+
