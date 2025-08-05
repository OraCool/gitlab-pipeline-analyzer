# Deployment Preparation Guide

This guide provides detailed steps to prepare the GitLab Pipeline Analyzer MCP Server for deployment.

## Prerequisites

- Python 3.10+ installed
- Git configured with your credentials
- GitHub repository access with appropriate permissions
- PyPI account with trusted publishing configured (for production releases)

## Step-by-Step Deployment Preparation

### 1. Verify Tox and Fix All Issues

Tox runs all quality checks including tests, linting, type checking, formatting, and security scans.

```bash
# Navigate to project directory
cd /path/to/gitlab-pipeline-analyzer

# Run all tox environments
uv run tox
```

**Common Issues and Fixes:**

#### Type Annotation Errors (MyPy)
```bash
# Check specific type errors
uv run mypy src/

# Fix example: Add type annotations for variables
# Before: entries = []
# After: entries: list[LogEntry] = []
```

#### Test Coverage Below Threshold
```bash
# Check current coverage
uv run pytest --cov=src --cov-report=term-missing

# Options to fix:
# 1. Add more tests for uncovered code
# 2. Temporarily lower coverage threshold in pytest.ini
```

#### Linting Issues
```bash
# Check and auto-fix linting issues
uv run ruff check . --fix
uv run ruff format .

# Verify format consistency (same as CI)
uv run ruff check --output-format=github .
uv run ruff format --check .
```

#### Security Issues
```bash
# Check for security vulnerabilities
uv run bandit -r src/
```

### 2. Verify Pre-commit and Fix All Issues

Pre-commit hooks ensure code quality before commits.

```bash
# Install pre-commit hooks (if not already installed)
uv run pre-commit install

# Run pre-commit on all files
uv run pre-commit run --all-files
```

**Common Pre-commit Fixes:**
- **Trailing whitespace**: Automatically fixed by the hook
- **End of file fixes**: Automatically fixed by the hook
- **YAML/TOML validation**: Check syntax in configuration files
- **Code formatting**: Ruff formats code automatically

### 3. Update Version

Update the version number in the appropriate files:

#### 3.1 Update pyproject.toml
```toml
[project]
name = "gitlab-pipeline-analyzer"
version = "X.Y.Z"  # Update this line
```

#### 3.2 Update README.md
Find and update version references in README.md:
```markdown
# Before
"gitlab_pipeline_analyzer==0.1.2"

# After
"gitlab_pipeline_analyzer==0.1.3"
```

#### 3.3 Verify Version Updates
```bash
# Search for old version references
grep -r "0.1.2" . --exclude-dir=.git --exclude-dir=.venv --exclude-dir=.tox
```

### 4. Commit and Push Changes

#### 4.1 Pre-Commit Verification
Run the exact same checks as CI to catch issues early:

```bash
# Run all CI checks locally
uv run ruff check --output-format=github .
uv run ruff format --check .
uv run mypy src/
uv run bandit -r src/
uv run pytest tests/ -v --cov=src/ --cov-report=term-missing

# If any checks fail, fix them before proceeding
```

#### 4.2 Review Changes
```bash
# Check current status
git status

# Review specific changes
git diff
```

#### 4.3 Stage and Commit
```bash
# Stage all changes
git add .

# Commit with descriptive message
git commit -m "Prepare for vX.Y.Z release

- Fix type annotations for mypy compliance
- Resolve pre-commit issues
- Update version to X.Y.Z
- [Any other specific changes]"
```

#### 4.4 Push Changes
```bash
# Push to remote repository
git push origin main
```

### 5. Add Tag and Push

#### 5.1 Create Git Tag
```bash
# Create annotated tag
git tag -a vX.Y.Z -m "Release version X.Y.Z"

# Example:
git tag -a v0.1.3 -m "Release version 0.1.3"
```

#### 5.2 Push Tag
```bash
# Push the tag to remote
git push origin vX.Y.Z

# Example:
git push origin v0.1.3

# Or push all tags
git push --tags
```

### 6. Verify GitHub Actions

After pushing the tag, GitHub Actions will automatically trigger:

#### 6.1 Monitor Release Workflow
1. Go to your GitHub repository
2. Navigate to **Actions** tab
3. Check the **Release** workflow status
4. Verify all jobs complete successfully

#### 6.2 Workflow Jobs Include:
- **Build**: Package creation and validation
- **Test**: Run test suite across Python versions
- **Security**: Security scans and vulnerability checks
- **Publish**: Automatic PyPI publishing (for production)

### 7. Post-Deployment Verification

#### 7.1 Verify PyPI Publication
```bash
# Check if package is available on PyPI
pip index versions gitlab-pipeline-analyzer

# Install and test the published package
pip install gitlab-pipeline-analyzer==X.Y.Z
```

#### 7.2 Test Installation
```bash
# Test the CLI entry point
gitlab-analyzer --help

# Test with uvx (recommended)
uvx --from gitlab-pipeline-analyzer==X.Y.Z gitlab-analyzer --help
```

## Troubleshooting

### Common Deployment Issues

#### 1. Tox Failures
```bash
# Run specific tox environment
uv run tox -e lint    # Only linting
uv run tox -e type    # Only type checking
uv run tox -e py312   # Only tests

# Clean tox cache
rm -rf .tox/
```

#### 2. Pre-commit Failures
```bash
# Update pre-commit hooks
uv run pre-commit autoupdate

# If there are version conflicts between pre-commit and project tools:
# 1. Check tool versions
uv run ruff --version
uv run mypy --version

# 2. Update .pre-commit-config.yaml to match project versions
# 3. Clean and reinstall pre-commit hooks
uv run pre-commit clean
uv run pre-commit install --install-hooks

# Skip specific hook if needed (not recommended)
SKIP=mypy uv run pre-commit run --all-files
```

#### 3. Version Conflicts
```bash
# Find all version references
find . -name "*.py" -o -name "*.md" -o -name "*.toml" | xargs grep -l "0\.1\.2"

# Update systematically
sed -i 's/0\.1\.2/0\.1\.3/g' filename
```

#### 4. GitHub Actions Failures

##### Common CI Errors and Fixes:

**Ruff Formatting Error (Persistent CI Issue):**
```
Error: Would reformat: tests/test_mcp_tools_coverage.py
1 file would be reformatted, 31 files already formatted
```
**Fix:**
```bash
# Common cause: Version mismatch between pre-commit ruff and project ruff
# or cached CI state with outdated file versions

# Check versions
uv run ruff --version
# Compare with .pre-commit-config.yaml ruff rev

# Fix version mismatch in .pre-commit-config.yaml
# Update rev to match project version (e.g., v0.12.7)

# Clean and reinstall pre-commit
uv run pre-commit clean
uv run pre-commit install --install-hooks

# Format all files to match CI expectations
uv run ruff format .

# Verify formatting matches CI locally
uv run ruff format --check .
uv run ruff check --output-format=github .

# If the issue persists in CI despite passing locally:
# Force a new commit to refresh CI cache
touch .format-trigger && git add . && git commit -m "Force format refresh"
```

**Type Checking Failures:**
```
src/file.py:123: error: Need type annotation for "variable"
```
**Fix:**
```bash
# Run mypy locally to see all type errors
uv run mypy src/

# Add proper type annotations
# Before: entries = []
# After: entries: list[LogEntry] = []
```

**Test Coverage Failures:**
```
FAIL Required test coverage of 70% not reached. Total coverage: 68%
```
**Fix:**
```bash
# Check coverage details
uv run pytest --cov=src --cov-report=term-missing

# Options:
# 1. Add more tests for uncovered code
# 2. Lower coverage threshold in pytest.ini temporarily
```

**General Troubleshooting:**
- Check the Actions tab for detailed error logs
- Verify environment secrets are configured
- Check PyPI trusted publishing setup
- Ensure branch protection rules allow the release
- Re-run failed jobs if they seem transient

### Emergency Rollback

If issues are discovered after deployment:

```bash
# Delete problematic tag locally and remotely
git tag -d vX.Y.Z
git push origin :refs/tags/vX.Y.Z

# Revert to previous version
git revert HEAD
git push origin main
```

## Release Checklist

Use this checklist to ensure all steps are completed:

- [ ] All tox environments pass (`uv run tox`)
- [ ] All pre-commit hooks pass (`uv run pre-commit run --all-files`)
- [ ] **Pre-commit CI verification**: All CI checks pass locally:
  - [ ] `uv run ruff check --output-format=github .`
  - [ ] `uv run ruff format --check .`
  - [ ] `uv run mypy src/`
  - [ ] `uv run bandit -r src/`
  - [ ] `uv run pytest tests/ -v --cov=src/ --cov-report=term-missing`
- [ ] Version updated in `pyproject.toml`
- [ ] Version updated in `README.md`
- [ ] All other version references updated
- [ ] Changes committed with descriptive message
- [ ] Changes pushed to remote repository
- [ ] Git tag created and pushed
- [ ] GitHub Actions workflows complete successfully
- [ ] Package published to PyPI (if applicable)
- [ ] Installation verified (`uvx --from gitlab-pipeline-analyzer==X.Y.Z gitlab-analyzer`)

## Version Numbering Strategy

This project follows [Semantic Versioning](https://semver.org/):

- **MAJOR** (X.0.0): Breaking changes
- **MINOR** (0.Y.0): New features, backward compatible
- **PATCH** (0.0.Z): Bug fixes, backward compatible

Example progression:
- `0.1.2` → `0.1.3` (patch: bug fixes)
- `0.1.3` → `0.2.0` (minor: new features)
- `0.2.0` → `1.0.0` (major: breaking changes)

## Automated Deployment (Future Enhancement)

Consider setting up automated deployment for patch releases:

```yaml
# .github/workflows/auto-release.yml
name: Auto Release
on:
  push:
    branches: [main]
    paths: ['src/**', 'pyproject.toml']

jobs:
  auto-release:
    if: contains(github.event.head_commit.message, '[auto-release]')
    # ... automation logic
```

---

**Note**: Always test in a staging environment before production deployment. Keep backups of critical configurations and data.
