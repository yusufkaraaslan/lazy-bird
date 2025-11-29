# CI/CD Setup Guide

Complete guide for setting up and configuring the lazy-bird CI/CD pipeline.

## Overview

The lazy-bird project uses GitHub Actions for continuous integration and deployment with three main workflows:

1. **Tests** (`test.yml`) - Automated testing on Python 3.8-3.12
2. **Code Quality** (`lint.yml`) - Linting, formatting, and security checks
3. **Publish** (`publish.yml`) - Automated PyPI releases

## Workflows

### 1. Tests Workflow

**File**: `.github/workflows/test.yml`

**Triggers**:
- Push to `main` or `develop` branches
- Pull requests to `main` or `develop`
- Manual dispatch

**Matrix Testing**:
- Python versions: 3.8, 3.9, 3.10, 3.11, 3.12
- OS: Ubuntu Latest

**Steps**:
1. Checkout code
2. Setup Python with pip caching
3. Install dependencies
4. Run pytest with coverage
5. Upload coverage to Codecov (Python 3.11 only)
6. Verify 70%+ coverage threshold

### 2. Code Quality Workflow

**File**: `.github/workflows/lint.yml`

**Checks**:
- **Black**: Code formatting
- **Flake8**: Style guide enforcement
- **Mypy**: Static type checking (optional)
- **Bandit**: Security vulnerability scanning

**Jobs**:
- `lint`: Formatting and linting checks
- `security`: Security scanning with bandit

### 3. Publish Workflow

**File**: `.github/workflows/publish.yml`

**Triggers**:
- GitHub Release published
- Manual dispatch (with TestPyPI option)

**Jobs**:
1. `build`: Build distribution packages
2. `publish-to-pypi`: Publish to PyPI (on release)
3. `publish-to-test-pypi`: Publish to TestPyPI (manual)
4. `github-release`: Upload artifacts to GitHub Release

## Required Secrets

Configure these secrets in GitHub repository settings:

### Codecov Token

1. Go to https://codecov.io/
2. Sign in with GitHub
3. Add repository: `yusufkaraaslan/lazy-bird`
4. Copy the repository token
5. Add to GitHub Secrets:
   - Name: `CODECOV_TOKEN`
   - Value: `<your-codecov-token>`

### PyPI API Token

1. Go to https://pypi.org/manage/account/
2. Create API token:
   - Name: `lazy-bird-github-actions`
   - Scope: `Project: lazy-bird`
3. Copy the token (starts with `pypi-`)
4. Add to GitHub Secrets:
   - Name: `PYPI_API_TOKEN`
   - Value: `<your-pypi-token>`

### TestPyPI API Token (Optional)

1. Go to https://test.pypi.org/manage/account/
2. Create API token for testing
3. Add to GitHub Secrets:
   - Name: `TEST_PYPI_API_TOKEN`
   - Value: `<your-test-pypi-token>`

## Setting Up Codecov

### Initial Setup

```bash
# 1. Visit Codecov
https://codecov.io/gh/yusufkaraaslan/lazy-bird

# 2. Enable repository

# 3. Copy repository token

# 4. Add to GitHub Secrets
```

### Codecov Configuration

Create `.codecov.yml` in repository root:

```yaml
coverage:
  status:
    project:
      default:
        target: 70%
        threshold: 2%
    patch:
      default:
        target: 70%

comment:
  layout: "header, diff, flags, files"
  behavior: default
```

### Badge Setup

Already added to README.md:
```markdown
[![codecov](https://codecov.io/gh/yusufkaraaslan/lazy-bird/branch/main/graph/badge.svg)](https://codecov.io/gh/yusufkaraaslan/lazy-bird)
```

## Branch Protection Rules

Recommended settings for `main` branch:

### Navigate to Settings > Branches > Add Rule

**Branch name pattern**: `main`

**Protect matching branches**:
- ✅ Require a pull request before merging
  - ✅ Require approvals: 1 (for team projects)
  - ✅ Dismiss stale pull request approvals when new commits are pushed
- ✅ Require status checks to pass before merging
  - ✅ Require branches to be up to date before merging
  - **Required checks**:
    - `test (3.8, ubuntu-latest)`
    - `test (3.9, ubuntu-latest)`
    - `test (3.10, ubuntu-latest)`
    - `test (3.11, ubuntu-latest)`
    - `test (3.12, ubuntu-latest)`
    - `lint`
    - `security`
- ✅ Require conversation resolution before merging
- ✅ Include administrators (optional for solo projects)

## Manual Workflow Triggers

### Run Tests Manually

```bash
# Via GitHub UI:
Actions → Tests → Run workflow

# Via gh CLI:
gh workflow run test.yml
```

### Publish to TestPyPI

```bash
# Via GitHub UI:
Actions → Publish to PyPI → Run workflow
Select: "Publish to TestPyPI instead of PyPI" ✅

# Via gh CLI:
gh workflow run publish.yml -f test-pypi=true
```

### Create a Release

```bash
# Create and push tag
git tag -a v0.2.0 -m "Release version 0.2.0"
git push origin v0.2.0

# Create GitHub release (triggers publish workflow)
gh release create v0.2.0 \
  --title "Version 0.2.0" \
  --notes "Release notes here" \
  --generate-notes
```

## Monitoring Workflows

### GitHub Actions Tab

https://github.com/yusufkaraaslan/lazy-bird/actions

### View Logs

```bash
# List workflow runs
gh run list --workflow=test.yml

# View specific run
gh run view <run-id>

# Download logs
gh run download <run-id>
```

### Status Checks

All badges in README.md update automatically:
- Tests badge: Shows pass/fail status
- Code Quality badge: Shows lint status
- Codecov badge: Shows coverage percentage

## Troubleshooting

### Tests Fail on Specific Python Version

```bash
# Test locally with specific Python version
pyenv install 3.8.18
pyenv local 3.8.18
pytest

# Or use tox
pip install tox
tox -e py38
```

### Coverage Upload Fails

1. Verify `CODECOV_TOKEN` is set correctly
2. Check Codecov dashboard for errors
3. Ensure coverage.xml is generated:
   ```bash
   pytest --cov=lazy_bird --cov-report=xml
   ls -la coverage.xml
   ```

### PyPI Publish Fails

1. Check `PYPI_API_TOKEN` is valid
2. Verify version in `pyproject.toml` doesn't already exist on PyPI
3. Ensure distribution builds successfully:
   ```bash
   python -m build
   twine check dist/*
   ```

### Black Formatting Fails

```bash
# Fix formatting automatically
black lazy_bird/ tests/

# Check what would change
black --check --diff lazy_bird/ tests/
```

### Flake8 Errors

```bash
# Run locally
flake8 lazy_bird/ tests/

# Auto-fix with autopep8
pip install autopep8
autopep8 --in-place --aggressive --aggressive -r lazy_bird/
```

## Local Development Workflow

### Pre-commit Checks

Run these before committing:

```bash
# Format code
black lazy_bird/ tests/

# Check linting
flake8 lazy_bird/ tests/

# Run tests with coverage
pytest --cov=lazy_bird --cov-fail-under=70

# Type check (optional)
mypy lazy_bird/

# Security scan
bandit -r lazy_bird/
```

### Pre-push Checks

```bash
# Run full test matrix locally (requires tox)
tox

# Or test on multiple Python versions with pyenv
for version in 3.8.18 3.9.18 3.10.13 3.11.7 3.12.1; do
  pyenv local $version
  pytest
done
```

## Continuous Deployment Flow

### Development → Release

1. **Feature branch** → Open PR
2. **CI runs** → Tests + Lint on PR
3. **Review** → Code review + status checks pass
4. **Merge** → Merge to `main`
5. **Tag** → Create version tag (`v0.x.x`)
6. **Release** → Create GitHub Release
7. **Auto-deploy** → CI publishes to PyPI
8. **Verify** → Check PyPI page

### Version Bumping

```bash
# Update version in pyproject.toml
# Example: 0.1.0 → 0.2.0

# Commit version bump
git add pyproject.toml
git commit -m "Bump version to 0.2.0"
git push

# Create and push tag
git tag -a v0.2.0 -m "Release 0.2.0"
git push origin v0.2.0

# Create release (triggers PyPI publish)
gh release create v0.2.0 --generate-notes
```

## GitHub Environments

### Setup Environments (Optional)

For additional security, configure environments:

**Settings → Environments → New Environment**

1. **Environment**: `pypi`
   - Required reviewers: Add yourself
   - Deployment branches: `main` only
   - Secrets: `PYPI_API_TOKEN`

2. **Environment**: `testpypi`
   - Secrets: `TEST_PYPI_API_TOKEN`

## Workflow Permissions

The workflows use these permissions:

- `id-token: write` - For PyPI trusted publishing
- `contents: write` - For GitHub Release artifact upload
- Default permissions for reading repository

## Cost Considerations

GitHub Actions is free for public repositories with:
- 2,000 CI/CD minutes/month
- Unlimited storage for artifacts (1GB limit per workflow)

Current usage per commit:
- Tests workflow: ~5-10 minutes (Python 3.8-3.12 matrix)
- Lint workflow: ~2-3 minutes
- Publish workflow: ~3-5 minutes (only on release)

## Support

For issues with CI/CD:
1. Check workflow run logs in Actions tab
2. Review this setup guide
3. Open issue: https://github.com/yusufkaraaslan/lazy-bird/issues

---

**Last Updated**: 2025-11-29
**Workflows**: test.yml, lint.yml, publish.yml
**Python Versions**: 3.8, 3.9, 3.10, 3.11, 3.12
