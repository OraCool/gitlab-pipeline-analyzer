# GitHub Actions PyPI Publishing Setup Guide

## 🔐 Setting Up PyPI API Tokens

### 1. Create PyPI API Tokens

#### For TestPyPI (testing):
1. Go to https://test.pypi.org/account/login/
2. Log in or create an account
3. Go to Account Settings → API tokens
4. Click "Add API token"
5. Name: `github-actions-testpypi`
6. Scope: `Entire account` (or specific project after first upload)
7. Copy the token (starts with `pypi-`)

#### For PyPI (production):
1. Go to https://pypi.org/account/login/
2. Log in or create an account
3. Go to Account Settings → API tokens  
4. Click "Add API token"
5. Name: `github-actions-pypi`
6. Scope: `Entire account` (or specific project after first upload)
7. Copy the token (starts with `pypi-`)

### 2. Add Tokens to GitHub Secrets

1. Go to your GitHub repository
2. Navigate to: **Settings** → **Secrets and variables** → **Actions**
3. Click "New repository secret" and add the following:

#### Required Secrets:
- **Name**: `TESTPYPI_API_TOKEN`
  - **Value**: `pypi-your-testpypi-token-here`

- **Name**: `PYPI_API_TOKEN`
  - **Value**: `pypi-your-pypi-token-here`

### 3. GitHub Actions Environment Protection (Optional)

For additional security, you can set up environment protection:

1. Go to **Settings** → **Environments**
2. Create environments: `testpypi` and `pypi`
3. Add protection rules (require reviews, specific branches, etc.)

## 🚀 Publishing Workflow

### Automatic Publishing:
1. **TestPyPI**: Publishes automatically on every push to main branch
2. **PyPI**: Publishes when you create a version tag (e.g., `v0.1.0`)

### Manual Publishing Process:

#### 1. Prepare Release
```bash
# Update version in pyproject.toml
# Update CHANGELOG.md
# Commit changes
git add pyproject.toml CHANGELOG.md
git commit -m "chore: bump version to 0.1.1"
git push origin main
```

#### 2. Create Release Tag
```bash
# Create and push tag
git tag v0.1.1
git push origin v0.1.1
```

#### 3. GitHub Actions will handle the release
- The workflow automatically publishes to PyPI when you push a tag
- Creates a GitHub release with release notes
- No manual approval needed (unlike GitLab)

## 📋 Pre-Publishing Checklist

- [ ] Version updated in `pyproject.toml`
- [ ] CHANGELOG.md updated
- [ ] All tests passing
- [ ] Code quality checks passing
- [ ] TestPyPI deployment successful
- [ ] Ready to create production tag

## 🔍 Monitoring

- **TestPyPI**: https://test.pypi.org/project/gitlab-pipeline-analyzer/
- **PyPI**: https://pypi.org/project/gitlab-pipeline-analyzer/
- **GitHub Actions**: Your repository → Actions tab
