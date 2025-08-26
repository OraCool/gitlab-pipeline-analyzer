# 🚀 Complete Guide: Publishing to PyPI with GitHub Actions

## 📋 Overview
I've set up a complete GitHub Actions workflow that will:
1. **Test** your code on every push/PR
2. **Build** packages automatically
3. **Publish to TestPyPI** on main branch pushes (for testing)
4. **Publish to PyPI** when you create version tags (automatic)
5. **Create GitHub releases** with release notes

---

## 🔧 Step 1: Set Up PyPI Accounts & Tokens

### 1.1 Create PyPI Accounts
- **TestPyPI**: https://test.pypi.org/account/register/
- **PyPI**: https://pypi.org/account/register/

### 1.2 Generate API Tokens

**For TestPyPI:**
1. Go to https://test.pypi.org/account/login/
2. Account Settings → API tokens → "Add API token"
3. Name: `github-actions-testpypi`
4. Scope: `Entire account`
5. **Copy the token** (starts with `pypi-`)

**For PyPI:**
1. Go to https://pypi.org/account/login/
2. Account Settings → API tokens → "Add API token"
3. Name: `github-actions-pypi`
4. Scope: `Entire account`
5. **Copy the token** (starts with `pypi-`)

---

## 🔐 Step 2: Configure GitHub Secrets

1. **Go to your GitHub repository**
2. **Navigate to**: Settings → Secrets and variables → Actions
3. **Click "New repository secret"** and add:

| Secret Name | Value | Notes |
|-------------|-------|-------|
| `TESTPYPI_API_TOKEN` | `pypi-your-testpypi-token` | For testing releases |
| `PYPI_API_TOKEN` | `pypi-your-pypi-token` | For production releases |

### 🛡️ Optional: Environment Protection
For extra security, you can protect your environments:

1. Go to **Settings** → **Environments**
2. Create environments: `testpypi` and `pypi`
3. Add protection rules:
   - Require review from maintainers
   - Restrict to main branch
   - Add deployment delays

---

## 🚀 Step 3: Publishing Workflow

### **Automatic Publishing:**
- ✅ **TestPyPI**: Every push to `main` branch
- ✅ **PyPI**: When you create version tags (e.g., `v0.1.0`)
- ✅ **GitHub Release**: Automatically created with each PyPI release

### **Release Process:**

#### **Method 1: Automated Script (Recommended)**
```bash
./scripts/release.sh 0.1.1
```

#### **Method 2: Manual Process**
```bash
# 1. Update version
# Edit pyproject.toml: version = "0.1.1"

# 2. Commit changes
git add pyproject.toml CHANGELOG.md
git commit -m "chore: bump version to 0.1.1"
git push origin main

# 3. Create and push tag
git tag v0.1.1
git push origin v0.1.1
```

---

## 📊 Step 4: Monitor Your Releases

### **Check Workflow Status:**
- **GitHub Actions**: Repository → Actions tab
- **Workflow runs**: See real-time progress of test/build/publish

### **Verify Published Packages:**
- **TestPyPI**: https://test.pypi.org/project/gitlab-pipeline-analyzer/
- **PyPI**: https://pypi.org/project/gitlab-pipeline-analyzer/

### **Test Installation:**
```bash
# Test from TestPyPI
pip install -i https://test.pypi.org/simple/ gitlab-pipeline-analyzer

# Test from PyPI
pip install gitlab-pipeline-analyzer
```

---

## 🔍 Step 5: Workflow Features

### **What the Workflow Does:**

#### **Test Job** (runs on all pushes/PRs):
- ✅ Code quality checks (ruff)
- ✅ Type checking (mypy)
- ✅ Security scanning (bandit)
- ✅ Unit tests with coverage
- ✅ Upload coverage to Codecov

#### **Build Job**:
- ✅ Creates wheel and source distributions
- ✅ Validates package integrity
- ✅ Stores build artifacts

#### **Publish Jobs**:
- ✅ **TestPyPI**: Automatic on main branch
- ✅ **PyPI**: Automatic on version tags

#### **Release Job**:
- ✅ Creates GitHub release with notes
- ✅ Includes installation instructions
- ✅ Links to PyPI package

### **Trigger Rules:**
- **Tests**: All pushes and pull requests
- **Build**: Main branch and version tags
- **TestPyPI**: Main branch pushes only
- **PyPI**: Version tags only (e.g., `v0.1.0`, `v1.2.3`)

---

## ⚡ Step 6: Quick Commands

```bash
# Test locally before release
uv run pytest --tb=short
uv run ruff check
uv run mypy src/

# Quick release (recommended)
./scripts/release.sh 0.1.1

# Manual release
git tag v0.1.1 && git push origin v0.1.1

# Check what would be published
uv run python -m build
uv run twine check dist/*
```

---

## 📋 Step 7: Pre-Release Checklist

Before creating a release:
- [ ] ✅ All tests pass: `uv run pytest`
- [ ] ✅ Code quality passes: `uv run ruff check`
- [ ] ✅ Version updated in `pyproject.toml`
- [ ] ✅ `CHANGELOG.md` updated
- [ ] ✅ No uncommitted changes
- [ ] ✅ PyPI tokens set in GitHub secrets
- [ ] ✅ TestPyPI working (push to main first)

---

## 🛠️ Troubleshooting

### **Common Issues:**

#### **"Invalid token" Error:**
- Check PyPI tokens in GitHub repository secrets
- Ensure token names match: `TESTPYPI_API_TOKEN` and `PYPI_API_TOKEN`

#### **"Package already exists" Error:**
- Increment version number in `pyproject.toml`
- You cannot reuse version numbers on PyPI

#### **"Workflow not triggering" Issue:**
- Check tag format: must be `v0.1.0` (with 'v' prefix)
- Ensure you push the tag: `git push origin v0.1.0`

#### **"Tests failing" Issue:**
- Fix tests before releasing
- All tests must pass for publishing to proceed

### **Useful Debug Commands:**
```bash
# Test workflow locally with act (optional)
act -j test

# Check current tags
git tag -l

# See what would be published
ls -la dist/
uv run twine check dist/*

# Clean build artifacts
rm -rf dist/ build/ *.egg-info
```

---

## 🎉 You're All Set!

Your GitHub Actions workflow is now configured for automated PyPI publishing!

### **Next Steps:**
1. ✅ **Commit and push** the new workflow files
2. ✅ **Set up PyPI tokens** in GitHub repository secrets
3. ✅ **Test with a development push** to main (triggers TestPyPI)
4. ✅ **Create your first production release!** 🚀

### **Key Advantages of GitHub Actions:**
- ✅ **Fully automated** - no manual approval needed
- ✅ **Built-in security** with GitHub secrets
- ✅ **Great integration** with GitHub releases
- ✅ **Free for public repositories**
- ✅ **Excellent logging** and debugging tools

The workflow will handle building, testing, and publishing your package safely to PyPI every time you create a release tag!
