# Contributing to Lazy_Bird

Thank you for your interest in contributing to Lazy_Bird! This document provides guidelines and instructions for contributing.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [How Can I Contribute?](#how-can-i-contribute)
- [Development Setup](#development-setup)
- [Pull Request Process](#pull-request-process)
- [Coding Standards](#coding-standards)
- [Adding Framework Presets](#adding-framework-presets)
- [Testing](#testing)
- [CI/CD Pipeline](#cicd-pipeline)
- [Pre-push Checklist](#pre-push-checklist)
- [Documentation](#documentation)

## Code of Conduct

This project and everyone participating in it is governed by the [Lazy_Bird Code of Conduct](CODE_OF_CONDUCT.md). By participating, you are expected to uphold this code.

## How Can I Contribute?

### Reporting Bugs

Before creating bug reports, please check existing issues to avoid duplicates. When creating a bug report, include:

- **Clear title and description**
- **Steps to reproduce**
- **Expected vs actual behavior**
- **Environment details** (OS, Lazy_Bird version, framework, etc.)
- **Logs and error messages**
- **Screenshots** (if applicable)

**Use the bug report template when available.**

### Suggesting Enhancements

Enhancement suggestions are tracked as GitHub issues. When creating an enhancement suggestion:

- **Use a clear and descriptive title**
- **Provide detailed description** of the suggested enhancement
- **Explain why this enhancement would be useful**
- **List examples** of how it would be used
- **Mention alternatives** you've considered

### Adding Framework Support

Want to add support for a new framework? Great!

1. **Check if it's already requested** in Issues or Discussions
2. **Create an issue** describing the framework
3. **Add a preset** to `config/framework-presets.yml`
4. **Test thoroughly** with a real project
5. **Update documentation**
6. **Submit a PR** (see below)

See [Adding Framework Presets](#adding-framework-presets) for details.

### Improving Documentation

Documentation improvements are always welcome!

- Fix typos or unclear instructions
- Add examples and use cases
- Improve existing guides
- Translate documentation
- Add framework-specific guides

## Development Setup

### Prerequisites

- Git 2.30+
- Bash 4.0+ (or compatible shell)
- Python 3.8+ (for testing)
- Claude Code CLI (optional, for testing)
- Your framework's tools (Godot, Rust, Node.js, etc.)

### Setup Steps

```bash
# 1. Fork the repository on GitHub

# 2. Clone your fork
git clone https://github.com/YOUR_USERNAME/lazy-bird.git
cd lazy-bird

# 3. Add upstream remote
git remote add upstream https://github.com/yusufkaraaslan/lazy-bird.git

# 4. Create a branch for your changes
git checkout -b feature/your-feature-name

# 5. Make your changes

# 6. Test your changes
./tests/phase0/validate-all.sh /path/to/test-project --type <framework>

# 7. Commit and push
git add .
git commit -m "Description of changes"
git push origin feature/your-feature-name

# 8. Create a Pull Request on GitHub
```

## Pull Request Process

### Before Submitting

1. **Run the [Pre-push Checklist](#pre-push-checklist)** - Verify all checks pass locally
2. **Test your changes** thoroughly
3. **Update documentation** if needed
4. **Follow coding standards** (see below)
5. **Ensure tests pass** and coverage meets minimum 10%
6. **Update CHANGELOG** (if significant change)
7. **Rebase on latest main** if needed

### PR Requirements

- **Clear title** describing the change
- **Detailed description** of what and why
- **Link to related issues** (`Fixes #123`, `Closes #456`)
- **List of changes** (bullet points)
- **Testing done** (how you verified it works)
- **Screenshots** (for UI changes)

### PR Template

```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update
- [ ] Framework preset addition

## Related Issues
Fixes #(issue number)

## Changes Made
- Change 1
- Change 2
- Change 3

## Testing
- Test scenario 1
- Test scenario 2

## Checklist
- [ ] Code follows project style
- [ ] Documentation updated
- [ ] Tests added/updated
- [ ] All tests passing
- [ ] Commit messages are clear
```

### Review Process

1. Maintainers will review your PR
2. Address any requested changes
3. Once approved, maintainers will merge
4. Your contribution will be in the next release!

## Coding Standards

### Bash Scripts

```bash
#!/bin/bash
# Script description

set -euo pipefail  # Always include this

# Use meaningful variable names
PROJECT_PATH="/path/to/project"

# Add comments for complex logic
# This function does X because Y
function do_something() {
    local input="$1"
    # Function body
}

# Error handling
if [ ! -f "$CONFIG_FILE" ]; then
    echo "Error: Config file not found" >&2
    exit 1
fi
```

### Python Scripts

```python
"""Module description."""

import sys
from typing import List, Dict


def function_name(param: str) -> bool:
    """
    Function description.

    Args:
        param: Parameter description

    Returns:
        Return value description
    """
    # Implementation
    pass
```

### YAML Files

```yaml
# Comments explaining the section
framework_name:
  name: "Display Name"
  description: "Brief description"
  test_command: "command to run tests"
  build_command: null  # or actual command
  lint_command: null   # optional
```

## Adding Framework Presets

### Step 1: Research

1. Identify the framework's standard test/build commands
2. Check official documentation
3. Test commands in a real project
4. Note any special requirements or flags

### Step 2: Create Preset

Edit `config/framework-presets.yml`:

```yaml
your_framework:
  name: "Framework Name"
  description: "Brief description (e.g., 'Python web framework')"
  test_command: "command to run tests"
  build_command: "command to build (or null)"
  lint_command: "command to lint (or null)"
  format_command: "command to format (or null)"
  file_extensions: [".ext1", ".ext2"]
  ignore_patterns: ["pattern1/", "pattern2/"]
  docs_url: "https://framework-website.com/"
```

### Step 3: Test

```bash
# Test with a real project
./tests/phase0/validate-all.sh /path/to/test-project --type your_framework

# Test wizard integration
./wizard.sh
# Select your framework
# Verify config generated correctly
```

### Step 4: Document

Add your framework to:
- `README.md` - Framework list and examples
- `Docs/` - Framework-specific guide (optional)
- `CHANGELOG.md` - Note the addition

### Step 5: Submit PR

Create a PR with:
- Framework preset added
- Tests passing
- Documentation updated
- Example project (optional but helpful)

## Testing

### Running Tests Locally

Lazy_Bird uses pytest for automated testing. All tests must pass before submitting a PR.

```bash
# Run all tests
pytest

# Run with verbose output
pytest -v

# Run specific test directory
pytest tests/unit/

# Run specific test file
pytest tests/unit/test_init.py

# Run tests matching a pattern
pytest -k "test_version"
```

### Running Tests with Coverage

We aim for 70%+ code coverage. Currently, CI requires minimum 10% coverage.

```bash
# Run tests with coverage report
pytest --cov=lazy_bird --cov-report=term

# Generate detailed HTML coverage report
pytest --cov=lazy_bird --cov-report=html
# Open htmlcov/index.html in your browser

# Check if coverage meets threshold
pytest --cov=lazy_bird --cov-fail-under=10

# Generate coverage XML for CI
pytest --cov=lazy_bird --cov-report=xml
```

### Test Markers

Tests are organized with markers for selective execution:

```bash
# Run only unit tests (fast, isolated)
pytest -m unit

# Run only integration tests (slower, may require services)
pytest -m integration

# Run slow tests
pytest -m slow

# Run script tests
pytest -m scripts

# Skip slow tests
pytest -m "not slow"
```

See `pytest.ini` for marker definitions.

### Writing Tests

Tests use fixtures defined in `tests/conftest.py`. Example:

```python
"""tests/unit/test_example.py"""
import lazy_bird

class TestExample:
    """Test suite for example functionality."""

    def test_basic_function(self, temp_dir):
        """Test basic functionality using temp directory fixture."""
        # temp_dir is provided by conftest.py
        test_file = temp_dir / "test.txt"
        test_file.write_text("test content")

        assert test_file.exists()
        assert test_file.read_text() == "test content"

    def test_with_config(self, mock_config):
        """Test using mock configuration fixture."""
        # mock_config provides a complete configuration
        assert mock_config['project_type'] == 'python'
        assert 'project_path' in mock_config
```

### Test File Organization

```
tests/
├── conftest.py           # Shared fixtures and configuration
├── unit/                 # Unit tests (fast, isolated)
│   ├── test_init.py     # Package metadata tests
│   └── test_*.py        # Add your unit tests here
├── integration/          # Integration tests (slower)
│   └── test_*.py        # Add integration tests here
└── fixtures/             # Test data and mock files
```

### Coverage Requirements

- **Current minimum:** 10% (enforced in CI)
- **Target:** 70%+ coverage
- **New code:** Aim for 80%+ coverage on new features
- **Critical paths:** 100% coverage on core functionality

Coverage is tracked via Codecov and reported on every PR.

### Example Test Files

Reference these for writing your own tests:
- [`tests/unit/test_init.py`](tests/unit/test_init.py) - Package metadata tests
- [`tests/conftest.py`](tests/conftest.py) - Shared fixtures

### Manual Testing

```bash
# Phase 0 validation
./tests/phase0/validate-all.sh /path/to/project --type framework

# Full workflow test
# 1. Set up config
# 2. Create test issue
# 3. Verify automation works
# 4. Check PR creation
```

## CI/CD Pipeline

Lazy_Bird uses GitHub Actions for continuous integration and deployment. All PRs and commits to `main` trigger automated checks.

### Workflows

#### Tests Workflow (`.github/workflows/test.yml`)

Runs on every push and PR to `main` or `develop` branches.

**What it does:**
- Tests across Python versions: 3.8, 3.9, 3.10, 3.11, 3.12
- Runs on Ubuntu Latest
- Installs dependencies from `pyproject.toml`
- Executes pytest with coverage
- Uploads coverage to Codecov (Python 3.11 only)
- Enforces 10% minimum coverage threshold

**Viewing results:**
```bash
# View recent workflow runs
gh run list --limit 5

# View specific run details
gh run view <run-id>

# Download run logs
gh run download <run-id>
```

#### Code Quality Workflow (`.github/workflows/lint.yml`)

Runs code quality checks on every push and PR.

**Checks performed:**
1. **Black** - Code formatting (PEP 8 compliance)
2. **Flake8** - Linting and style guide enforcement
3. **Mypy** - Static type checking (informational)
4. **Bandit** - Security vulnerability scanning

**All checks must pass** for the PR to be mergeable.

#### Publish Workflow (`.github/workflows/publish.yml`)

Automatically publishes to PyPI when a GitHub Release is created.

**Steps:**
1. Builds distribution packages (`sdist` and `wheel`)
2. Publishes to PyPI (on release)
3. Uploads artifacts to GitHub Release
4. Manual dispatch option for TestPyPI

### Codecov Integration

Code coverage is tracked and reported on every commit.

**Features:**
- **Project coverage:** Must maintain 10% minimum
- **Patch coverage:** Informational (won't block builds)
- **Coverage badge:** Shows current coverage in README
- **PR comments:** Codecov bot comments on PRs with coverage changes

**Viewing coverage:**
- Badge in README: Shows overall project coverage
- Codecov dashboard: https://codecov.io/gh/yusufkaraaslan/lazy-bird
- PR comments: Detailed coverage diff for changes

### Viewing CI Results

**On GitHub:**
1. Go to your PR or commit
2. Scroll to bottom to see status checks
3. Click "Details" on any check to view logs

**Via CLI:**
```bash
# List recent runs
gh run list

# Watch a running workflow
gh run watch

# View run details
gh run view <run-id> --log
```

### When CI Fails

#### Test Failures
```bash
# Run the same tests locally
pytest --cov=lazy_bird --cov-report=term

# Run specific failing test
pytest tests/unit/test_init.py::TestPackageMetadata::test_version_exists -v

# Check coverage threshold
pytest --cov=lazy_bird --cov-fail-under=10
```

#### Black Formatting Failures
```bash
# Check what would change
black --check --diff lazy_bird/ tests/

# Auto-fix formatting
black lazy_bird/ tests/

# Commit fixes
git add -A
git commit -m "Fix code formatting with black"
```

#### Flake8 Linting Failures
```bash
# Run flake8 locally
flake8 lazy_bird/ tests/

# View only critical errors
flake8 lazy_bird/ tests/ --select=E9,F63,F7,F82
```

#### Mypy Type Checking Issues
```bash
# Run mypy locally
mypy lazy_bird/ --ignore-missing-imports

# Note: Mypy failures are informational and won't block PRs
```

### CI Configuration Files

- `.github/workflows/test.yml` - Test automation
- `.github/workflows/lint.yml` - Code quality checks
- `.github/workflows/publish.yml` - PyPI publishing
- `.codecov.yml` - Coverage configuration
- `pytest.ini` - Pytest configuration
- `pyproject.toml` - Project dependencies and tool configs

## Pre-push Checklist

Before pushing your changes, run these checks locally to avoid CI failures:

```bash
# 1. Run all tests
pytest

# 2. Check code formatting
black --check --diff lazy_bird/ tests/

# 3. Run linter
flake8 lazy_bird/ tests/

# 4. Check types (optional but recommended)
mypy lazy_bird/ --ignore-missing-imports

# 5. Verify coverage threshold
pytest --cov=lazy_bird --cov-fail-under=10

# 6. Run security scan (optional)
bandit -r lazy_bird/
```

### Quick Fix Commands

If checks fail, fix them quickly:

```bash
# Auto-fix formatting
black lazy_bird/ tests/

# Run tests with verbose output to identify failures
pytest -v

# Generate coverage report to see what's missing
pytest --cov=lazy_bird --cov-report=html
open htmlcov/index.html
```

### Recommended: Pre-commit Hook

Create `.git/hooks/pre-commit` to run checks automatically:

```bash
#!/bin/bash
# Run tests and formatting before commit

echo "Running pre-commit checks..."

# Format code
black lazy_bird/ tests/

# Run tests
pytest --cov=lazy_bird --cov-fail-under=10

if [ $? -ne 0 ]; then
    echo "❌ Tests failed. Commit aborted."
    exit 1
fi

echo "✅ All checks passed!"
```

Make it executable:
```bash
chmod +x .git/hooks/pre-commit
```

## Documentation

### Documentation Standards

- **Clear and concise**: Avoid jargon
- **Examples included**: Show, don't just tell
- **Up to date**: Update docs with code changes
- **Well structured**: Use headers and sections
- **Screenshots**: For UI or visual changes

### Documentation Locations

- `README.md` - Main documentation
- `CLAUDE.md` - Developer guide
- `Docs/Design/` - Architecture and design docs
- Code comments - Complex logic explanation

### Writing Style

- Use **present tense** ("Lazy_Bird creates..." not "will create...")
- Use **active voice** ("Run the command" not "The command should be run")
- Be **specific** ("Set test_command to 'pytest'" not "Configure testing")
- Add **examples** for every major feature

## Questions?

- **Discussions**: https://github.com/yusufkaraaslan/lazy-bird/discussions
- **Issues**: https://github.com/yusufkaraaslan/lazy-bird/issues
- **Email**: Check GitHub profile for contact info

## Recognition

Contributors are recognized in:
- GitHub contributors page
- Release notes (for significant contributions)
- Special thanks in major releases

## Thank You!

Every contribution, no matter how small, is valuable and appreciated. Thank you for helping make Lazy_Bird better!

---

🤖 Built with [Claude Code](https://claude.com/claude-code)
