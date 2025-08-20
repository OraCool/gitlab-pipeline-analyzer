---
mode: "agent"
description: "Prepare and publish a new version of the GitLab Pipeline Analyzer MCP to PyPI using GitHub Actions CI/CD workflow"
---

## 🎯 Goal

Prepare and release a new version of the **GitLab Pipeline Analyzer MCP** (`gitlab-pipeline-analyzer`) to PyPI using the automated GitHub Actions CI/CD pipeline.

## 📋 Pre-Release Checklist

### 1. 🔍 Review Current State

- [ ] Examine GitHub Actions workflows (`.github/workflows/ci-cd.yml`, `.github/workflows/release.yml`)
- [ ] Check current version in `pyproject.toml` (currently `0.2.8`)
- [ ] Review recent commits and changes since last release
- [ ] Verify project is in a stable state

### 2. 📝 Version Management

- [ ] **Determine next version** following [Semantic Versioning](https://semver.org/):
  - Patch (0.2.9): Bug fixes, small improvements
  - Minor (0.3.0): New features, backward compatible
  - Major (1.0.0): Breaking changes
- [ ] **Update version in ALL locations**:
  - `pyproject.toml` - primary version declaration
  - Verify `uv.lock` gets updated automatically via `uv sync`
  - Check that no hardcoded versions exist in other files
  - Check and update fallback version in `src/gitlab_analyzer/version.py`

### 3. ✅ Quality Assurance (CRITICAL)

Run comprehensive quality checks and fix any issues:

```bash
# Clean up unnecessary files before checks
find . -name "*.pyc" -delete
find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
rm -rf build/ dist/ *.egg-info/ .pytest_cache/ .coverage coverage.xml
rm -rf .mypy_cache/ .ruff_cache/

# Clean up temporary files created by agents/debugging (excluding tests/ directory)
find . -maxdepth 1 -name "debug_*.py" -delete
find . -maxdepth 1 -name "test_*.py" ! -path "./tests/*" -delete
find . -maxdepth 1 -name "temp_*.py" -delete
find . -maxdepth 1 -name "analyze_*.py" -delete
find . -maxdepth 1 -name "demo_*.py" -delete
rm -f *.tmp *.temp *.log *.out
rm -rf temp/ tmp/ debug/

# Install dependencies
uv sync --all-extras

# Code quality checks
uv run ruff check && uv run ruff format --check
uv run mypy src/
uv run bandit -r src/

# Run full test suite
uv run pytest --tb=short --cov-report=term --cov-fail-under=70

# Build and validate package
uv run python -m build
uv run twine check dist/*
```

**If ANY checks fail**:

- Fix all issues before proceeding
- Re-run tests to ensure fixes don't break anything
- Consider if fixes require version bump adjustment

### 4. 📚 Documentation Updates

- [ ] **Update `CHANGELOG.md`**:
  - Move items from `[Unreleased]` to new version section
  - Follow existing format with categories: Added 🚀, Enhanced ✨, Fixed 🐛, Technical Improvements 🔧
  - Include date in format `[X.Y.Z] - YYYY-MM-DD`
  - Add meaningful descriptions of changes for users
- [ ] **Update `README.md`** if needed:
  - Installation instructions
  - Version references
  - New features documentation

### 5. 🚀 Release Process

- [ ] **Commit all changes**:

  ```bash
  git add .
  git commit -m "chore: prepare release v[X.Y.Z]

  - Updated version to [X.Y.Z] in pyproject.toml
  - Updated CHANGELOG.md with release notes
  - [Brief summary of key changes]
  "
  ```

- [ ] **Push to main branch**:
  ```bash
  git push origin main
  ```

### 6. 🏗️ Monitor CI/CD Pipeline

- [ ] **Watch GitHub Actions CI/CD pipeline** (`ci-cd.yml`):
  - ✅ Test and Quality Checks job must pass
  - ✅ Build Package job must pass
  - ✅ Publish to TestPyPI job should complete (auto-triggered on main push)
- [ ] **If pipeline fails**:
  - Analyze failure logs in GitHub Actions
  - Fix issues locally
  - Push fixes and wait for pipeline to pass

### 7. 🏷️ Create Release Tag

**ONLY after CI/CD pipeline succeeds completely**:

- [ ] **Create and push version tag**:
  ```bash
  git tag v[X.Y.Z]
  git push origin v[X.Y.Z]
  ```

### 8. 🎉 Final Release Automation

The tag push will automatically trigger:

- [ ] **Production PyPI publication** (via `release.yml` workflow)
- [ ] **GitHub Release creation** with:
  - Release notes from CHANGELOG.md
  - Automatic release notes generation
  - Links to PyPI package
- [ ] **Verify successful publication**:
  - Check [PyPI package page](https://pypi.org/project/gitlab-pipeline-analyzer/)
  - Confirm new version is live
  - Test installation: `pip install gitlab-pipeline-analyzer==[X.Y.Z]`

## ⚠️ Important Notes

- **Never skip quality checks** - they prevent broken releases
- **TestPyPI publication happens on every main push** - use for testing
- **Production PyPI publication only happens on version tags** - no rollbacks!
- **GitHub Release is automatic** - manual editing available post-creation
- **Version must follow semver strictly** - tools and CI depend on it

## 🆘 Troubleshooting

- **Tests failing**: Check test logs, fix code, ensure 70%+ coverage
- **Build failing**: Verify `pyproject.toml` syntax, check dependencies
- **PyPI publication failing**: Check for version conflicts, ensure unique version number
- **GitHub Actions stuck**: Check workflow permissions, secrets, and API limits

## 📦 Project Context

This is the **GitLab Pipeline Analyzer MCP** - a FastMCP server for analyzing GitLab CI/CD pipeline failures. It provides 16+ MCP tools for comprehensive pipeline failure analysis and AI-assisted troubleshooting. The project itself is hosted on **GitHub** and uses **GitHub Actions** for CI/CD and PyPI publishing.
