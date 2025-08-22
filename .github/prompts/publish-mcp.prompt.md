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
  - Check current version in git and compare with `pyproject.toml`
  - Decide whether the update of the version is needed (do not update in case already changed)
    - Patch (0.2.9): Bug fixes, small improvements
    - Minor (0.3.0): New features, backward compatible
    - Major (1.0.0): Breaking changes
- [ ] **Update version in ALL locations**:
  - `pyproject.toml` - primary version declaration
  - Verify `uv.lock` gets updated automatically via `uv sync`
  - Check that no hardcoded versions exist in other files
  - Check that no hardcoded versions exist in README.md
  - Check and update fallback version in `src/gitlab_analyzer/version.py`

### 3. ✅ Quality Assurance (CRITICAL)

⚠️ **SAFETY NOTE**: The cleanup commands below have been carefully designed to preserve ALL legitimate test files in the `tests/` directory and any `pytest_*.py` files. Only temporary debug files from the root directory are removed.

Run comprehensive quality checks and fix any issues:

```bash
# Check command availability and set up aliases for compatibility
echo "🔧 Checking available commands..."

# Check for find vs fd
if command -v fd &> /dev/null; then
    echo "✅ Using fd (modern file finder)"
    FIND_CMD="fd"
    FIND_TYPE="-t f"
    FIND_EXEC="-x"
    FIND_DELETE="-X rm"
    FIND_NAME=""  # fd uses patterns directly
else
    echo "✅ Using find (traditional)"
    FIND_CMD="find"
    FIND_TYPE="-type f"
    FIND_EXEC="-exec"
    FIND_DELETE="-delete"
    FIND_NAME="-name"
fi

# Check for grep vs rg (ripgrep)
if command -v rg &> /dev/null; then
    echo "✅ Using rg (ripgrep)"
    GREP_CMD="rg"
    GREP_COUNT="-c"
    GREP_OUTPUT="-o"
    GREP_REPLACE="-r"
else
    echo "✅ Using grep (traditional)"
    GREP_CMD="grep"
    GREP_COUNT="-c"
    GREP_OUTPUT="-o"
    GREP_REPLACE="s///"  # Will need sed for replacements
fi

# Clean up unnecessary files before checks
echo "🧹 Cleaning up unnecessary files..."

# ⚠️  CRITICAL SAFETY NOTE:
# This cleanup ONLY removes temporary/debug files from the root directory.
# NEVER delete legitimate test files from tests/ directory or pytest_*.py files!
# The patterns below are carefully designed to preserve all legitimate test files.

# Safety check: Verify we're not about to delete legitimate test files
echo "🔍 Safety check: Verifying test file preservation..."
if [ -d "tests/" ]; then
    if [ "$FIND_CMD" = "fd" ]; then
        TEST_FILE_COUNT=$(fd -t f "test_.*\.py$" tests/ | wc -l)
    else
        TEST_FILE_COUNT=$(find tests/ -name "test_*.py" | wc -l)
    fi
    echo "✅ Found $TEST_FILE_COUNT legitimate test files in tests/ directory (will be preserved)"
else
    echo "⚠️  No tests/ directory found"
fi

if [ "$FIND_CMD" = "fd" ]; then
    # Modern fd syntax - only clean up obvious temporary/debug files
    fd -t f -e pyc -X rm 2>/dev/null || true
    fd -t d -n __pycache__ -X rm -rf 2>/dev/null || true
    # Only remove obvious temporary/debug files from root directory, not legitimate test files
    fd -t f "debug_.*\.py$" --max-depth 1 -X rm 2>/dev/null || true
    fd -t f "temp_.*\.py$" --max-depth 1 -X rm 2>/dev/null || true
    fd -t f "demo_.*\.py$" --max-depth 1 -X rm 2>/dev/null || true
    fd -t f "analyze_.*\.py$" --max-depth 1 -X rm 2>/dev/null || true
    # Remove only very specific temporary test files (not legitimate test_*.py files)
    fd -t f "simple_test.*\.py$" --max-depth 1 -X rm 2>/dev/null || true
    fd -t f "quick_test.*\.py$" --max-depth 1 -X rm 2>/dev/null || true
    # Remove backup and temporary files
    fd -t f ".*_old\..*$" -X rm 2>/dev/null || true
    fd -t f ".*_clean\..*$" -X rm 2>/dev/null || true
    fd -t f ".*\.bak$" -X rm 2>/dev/null || true
    fd -t d ".*\.egg-info$" -X rm -rf 2>/dev/null || true
else
    # Traditional find syntax - only clean up obvious temporary/debug files
    find . -name "*.pyc" -delete 2>/dev/null || true
    find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
    # Only remove obvious temporary/debug files from root directory, not legitimate test files
    find . -maxdepth 1 -name "debug_*.py" -delete 2>/dev/null || true
    find . -maxdepth 1 -name "temp_*.py" -delete 2>/dev/null || true
    find . -maxdepth 1 -name "demo_*.py" -delete 2>/dev/null || true
    find . -maxdepth 1 -name "analyze_*.py" -delete 2>/dev/null || true
    # Remove only very specific temporary test files (not legitimate test_*.py files)
    find . -maxdepth 1 -name "simple_test*.py" -delete 2>/dev/null || true
    find . -maxdepth 1 -name "quick_test*.py" -delete 2>/dev/null || true
    find . -name "*_old.*" -delete 2>/dev/null || true
    find . -name "*_clean.*" -delete 2>/dev/null || true
    find . -name "*.bak" -delete 2>/dev/null || true
    find . -name "*.egg-info" -type d -exec rm -rf {} + 2>/dev/null || true
fi

# Common cleanup regardless of tools
rm -rf build/ dist/ .pytest_cache/ .coverage coverage.xml 2>/dev/null || true
rm -rf .mypy_cache/ .ruff_cache/ 2>/dev/null || true
rm -f *.tmp *.temp *.log *.out 2>/dev/null || true
rm -rf temp/ tmp/ debug/ 2>/dev/null || true
# Note: *.egg-info directories can be in src/ or root, handled by find/fd commands above

# ⚠️  IMPORTANT: The cleanup above ONLY removes temporary/debug files from the root directory.
# Legitimate test files in tests/ directory and pytest_*.py files are preserved!
# Do NOT delete test_*.py files from tests/ directory - they are essential for the project.

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

# Validate documentation accuracy (CRITICAL for PyPI)
echo "📚 Validating documentation accuracy..."
echo "🔍 Current tool count:"

# Count tools with available commands
if [ "$FIND_CMD" = "fd" ] && [ "$GREP_CMD" = "rg" ]; then
    # Modern tools
    TOOL_COUNT=$(fd -t f -e py -E tests -E __pycache__ . src/ -x rg -c "@mcp\.tool" | awk '{sum+=$1} END {print sum}')
elif [ "$FIND_CMD" = "find" ] && [ "$GREP_CMD" = "grep" ]; then
    # Traditional tools
    TOOL_COUNT=$(find src/ -name "*tools.py" -exec grep -c "@mcp.tool" {} \; | awk '{sum+=$1} END {print sum}')
else
    # Mixed environment
    TOOL_COUNT=$(find src/ -name "*tools.py" -exec grep -c "@mcp.tool" {} \; 2>/dev/null | awk '{sum+=$1} END {print sum}')
fi

echo "Total tools: $TOOL_COUNT"

echo "🔍 Available tools:"
# Extract tool names with available commands
if [ "$FIND_CMD" = "fd" ] && [ "$GREP_CMD" = "rg" ]; then
    fd -t f -e py -E tests . src/ -x rg -o "def ([a-z_]+)" -r '$1' | rg -v "^_" | rg -v "register_" | sort | head -20
else
    find src/ -name "*tools.py" -exec grep -h "def " {} \; | grep -v "def _" | grep -v "register_" | sed 's/.*def //' | sed 's/(.*//g' | sort | head -20
fi

echo "⚠️  Verify README.md 'Available tools' section matches the above list"

# Build and validate Sphinx documentation if present
if [ -d "docs/" ]; then
  echo "📖 Building Sphinx documentation..."
  cd docs/
  make clean && make html
  if [ $? -eq 0 ]; then
    echo "✅ Documentation build successful"
  else
    echo "❌ Documentation build failed - fix warnings before release"
    cd ..
    exit 1
  fi
  cd ..
fi
```

**If ANY checks fail**:

- Fix all issues before proceeding
- Re-run tests to ensure fixes don't break anything
- Consider if fixes require version bump adjustment
- **Re-run documentation validation** after any code changes that affect tool APIs

### 4. 📚 Documentation Updates (CRITICAL)

**⚠️ CRITICAL**: README.md is displayed on PyPI and is the primary documentation users see. Outdated tool lists, examples, or feature descriptions directly impact adoption and user experience.

#### 4.1 Generate Current Tool Data

**FIRST**: Extract actual tool data from the codebase to ensure documentation accuracy:

````bash
```bash
# Check command availability first
if command -v fd &> /dev/null && command -v rg &> /dev/null; then
    echo "✅ Using modern tools (fd + rg)"
    USE_MODERN=true
else
    echo "✅ Using traditional tools (find + grep)"
    USE_MODERN=false
fi

# Generate current tool count and list
echo "🔍 Generating current tool data..."

# Count total tools with available commands
if [ "$USE_MODERN" = true ]; then
    TOOL_COUNT=$(fd -t f -e py -E tests -E __pycache__ . src/ -x rg -c "@mcp\.tool" | awk '{sum+=$1} END {print sum}')
else
    TOOL_COUNT=$(find src/ -name "*tools.py" -exec grep -c "@mcp.tool" {} \; | awk '{sum+=$1} END {print sum}')
fi
echo "Total tools: $TOOL_COUNT"

# Extract tool names and descriptions
echo "🔍 Available tools with descriptions:" > /tmp/current_tools.txt
if [ "$USE_MODERN" = true ]; then
    fd -t f -e py -E tests . src/ -x rg -A 5 "@mcp\.tool" | \
    rg "def ([a-z_]+)" -o -r '$1' | \
    sort >> /tmp/current_tools.txt
else
    find src/ -name "*tools.py" -exec grep -A 5 "@mcp.tool" {} \; | \
    grep -E "(async def|def )" | \
    sed 's/.*def //' | \
    sed 's/(.*//g' | \
    sort >> /tmp/current_tools.txt
fi

# Extract tool categories from docstrings
echo "🔍 Tool categories:" > /tmp/tool_categories.txt
if [ "$USE_MODERN" = true ]; then
    fd -t f -e py -E tests . src/ -x rg -B 2 -A 10 "@mcp\.tool" | \
    rg "[🔍📊🧪🌐🛡️📈🎯🔧📱📋]" >> /tmp/tool_categories.txt
else
    find src/ -name "*tools.py" -exec grep -B 2 -A 10 "@mcp.tool" {} \; | \
    grep -E "[🔍📊🧪🌐🛡️📈🎯🔧📱📋]" >> /tmp/tool_categories.txt
fi

# Extract FastMCP version and dependencies
echo "🔍 Current dependencies:" > /tmp/current_deps.txt
if [ "$USE_MODERN" = true ]; then
    rg -A 20 "dependencies =" pyproject.toml >> /tmp/current_deps.txt
else
    grep -A 20 "dependencies =" pyproject.toml >> /tmp/current_deps.txt
fi

# Extract version info
if [ "$USE_MODERN" = true ]; then
    CURRENT_VERSION=$(rg '^version =' pyproject.toml | rg -o '"[^"]*"' | tr -d '"')
else
    CURRENT_VERSION=$(grep '^version =' pyproject.toml | sed 's/version = "//' | sed 's/"//')
fi
echo "Current version: $CURRENT_VERSION"

# Display extracted data for review
echo "📋 Current Tool Data Summary:"
echo "- Total tools: $TOOL_COUNT"
echo "- Current version: $CURRENT_VERSION"
echo "- Tool list saved to: /tmp/current_tools.txt"
echo "- Categories saved to: /tmp/tool_categories.txt"
echo "- Dependencies saved to: /tmp/current_deps.txt"

cat /tmp/current_tools.txt
````

````

#### 4.2 Update Documentation Files

- [ ] **Update `CHANGELOG.md`** with actual data:
  - Move items from `[Unreleased]` to new version section
  - Include actual tool count if it changed: "Now includes $TOOL_COUNT MCP tools"
  - Follow existing format with categories: Added 🚀, Enhanced ✨, Fixed 🐛, Technical Improvements 🔧
  - Include date in format `[X.Y.Z] - YYYY-MM-DD`
  - Add meaningful descriptions of changes for users

- [ ] **Update `README.md`** (CRITICAL for PyPI visibility) with current data:

  **Tool Statistics Update**:
  ```bash
  # Update tool count in README.md introduction
  sed -i.bak "s/[0-9]\+ specialized tools/$TOOL_COUNT specialized tools/g" README.md
  sed -i.bak "s/[0-9]\+ comprehensive tools/$TOOL_COUNT comprehensive tools/g" README.md
````

**Manual Updates Required**:

- [ ] **Complete tools list**: Update "Available tools" section with current tool names from `/tmp/current_tools.txt`
- [ ] **Tool categories**: Update tool organization with actual categories from `/tmp/tool_categories.txt`
- [ ] **Feature descriptions**: Update tool descriptions with latest parameters and capabilities
- [ ] **Version references**: Update any version-specific examples or installation commands
- [ ] **New features documentation**: Add documentation for new features/tools added in this release
- [ ] **Installation instructions**: Verify pip install commands and dependency requirements
- [ ] **Examples and usage**: Update code examples to reflect current API signatures
- [ ] **Feature matrix**: Update any feature comparison tables or capability lists

- [ ] **Update Sphinx Documentation** (if present):
  ```bash
  # Check if docs exist and update them
  if [ -d "docs/" ]; then
    cd docs/
    # Update tool count in documentation with available commands
    if command -v rg &> /dev/null; then
      find . -name "*.rst" -exec sed -i.bak "s/[0-9]\+ tools/$TOOL_COUNT tools/g" {} \;
    else
      find . -name "*.rst" -exec sed -i.bak "s/[0-9]\+ tools/$TOOL_COUNT tools/g" {} \;
    fi
    # Rebuild documentation to check for warnings
    make clean && make html
    cd ..
  fi
  ```

#### 4.3 Validate Documentation Accuracy

**⚠️ CRITICAL**: Verify all documentation matches actual implementation:

```bash
# Check command availability for validation
if command -v rg &> /dev/null; then
    echo "✅ Using rg for validation"
    GREP_VALIDATE="rg"
else
    echo "✅ Using grep for validation"
    GREP_VALIDATE="grep"
fi

# Validate tool documentation accuracy
echo "📚 Validating documentation accuracy..."

# Check README.md tool count matches actual
if [ "$GREP_VALIDATE" = "rg" ]; then
    README_TOOL_COUNT=$(rg -o "[0-9]+ tools" README.md | head -1 | rg -o "[0-9]+")
else
    README_TOOL_COUNT=$(grep -o "[0-9]\+ tools" README.md | head -1 | grep -o "[0-9]\+")
fi

if [ "$README_TOOL_COUNT" != "$TOOL_COUNT" ]; then
  echo "❌ README.md tool count ($README_TOOL_COUNT) doesn't match actual ($TOOL_COUNT)"
  exit 1
fi

# Verify all tools mentioned in README exist in code
echo "🔍 Checking tool references in README..."

if [ "$GREP_VALIDATE" = "rg" ] && command -v fd &> /dev/null; then
    # Modern tools
    rg -o "analyze_[a-z_]*|get_[a-z_]*|extract_[a-z_]*|search_[a-z_]*" README.md | \
    sort -u > /tmp/readme_tools.txt

    fd -t f -e py -E tests . src/ -x rg -o "def ([a-z_]+)" -r '$1' | \
    rg -v "^_" | rg -v "register_" | \
    sort > /tmp/actual_tools.txt
else
    # Traditional tools
    grep -o "analyze_[a-z_]*\|get_[a-z_]*\|extract_[a-z_]*\|search_[a-z_]*" README.md | \
    sort -u > /tmp/readme_tools.txt

    find src/ -name "*tools.py" -exec grep -h "def " {} \; | \
    grep -v "def _" | grep -v "register_" | \
    sed 's/.*def //' | sed 's/(.*//g' | \
    sort > /tmp/actual_tools.txt
fi

# Check for mismatches
if ! diff /tmp/readme_tools.txt /tmp/actual_tools.txt > /dev/null; then
  echo "❌ Tool references in README don't match actual tools"
  echo "README tools:"
  cat /tmp/readme_tools.txt
  echo "Actual tools:"
  cat /tmp/actual_tools.txt
  echo "Please update README.md tool references"
  exit 1
fi

echo "✅ Documentation validation passed"
```

#### 4.4 Update Examples with Current Data

- [ ] **Code examples validation**:

  ```bash
  # Extract and validate code examples from README
  echo "🔍 Validating code examples..."

  # Check if example project IDs and pipeline IDs are realistic using rg
  rg -o "project_id.*[0-9]+" README.md
  rg -o "pipeline_id.*[0-9]+" README.md

  # Verify example responses match current tool output format
  echo "⚠️  Manually verify example responses in README match current tool output"
  ```

- [ ] **Update feature descriptions with actual capabilities**:
  - Verify search tools support both code and commit search
  - Confirm pytest integration features are accurately described
  - Update response mode descriptions (minimal, balanced, full)
  - Verify error filtering and pagination features are current

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
- **Never skip documentation validation** - README.md is the primary PyPI documentation
- **TestPyPI publication happens on every main push** - use for testing
- **Production PyPI publication only happens on version tags** - no rollbacks!
- **GitHub Release is automatic** - manual editing available post-creation
- **Version must follow semver strictly** - tools and CI depend on it
- **Tool count and descriptions must be current** - users rely on accurate documentation for feature discovery

## 🆘 Troubleshooting

- **Tests failing**: Check test logs, fix code, ensure 70%+ coverage
- **Build failing**: Verify `pyproject.toml` syntax, check dependencies
- **PyPI publication failing**: Check for version conflicts, ensure unique version number
- **GitHub Actions stuck**: Check workflow permissions, secrets, and API limits
- **Documentation out of sync**: Run tool validation commands, update README.md tool lists and examples
- **PyPI page looks outdated**: README.md is cached by PyPI, may take a few minutes to update after publication

## 📦 Project Context

This is the **GitLab Pipeline Analyzer MCP** - a FastMCP server for analyzing GitLab CI/CD pipeline failures. It provides 18+ MCP tools for comprehensive pipeline failure analysis and AI-assisted troubleshooting. The project itself is hosted on **GitHub** and uses **GitHub Actions** for CI/CD and PyPI publishing.

**Documentation Maintenance**: The project maintains detailed tool documentation in README.md which serves as the primary PyPI package description. Keeping this current is crucial for user adoption and accurate feature representation.
