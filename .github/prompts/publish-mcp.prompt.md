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

**Step 1: Check Tool Availability**

```bash
# Check command availability
if ! command -v fd &> /dev/null; then
    echo "❌ fd not found. Please install: brew install fd"
    exit 1
fi

if ! command -v rg &> /dev/null; then
    echo "❌ rg not found. Please install: brew install ripgrep"
    exit 1
fi

echo "✅ Modern tools available"
```

**Step 2: Clean Up Temporary Files**

```bash
# Clean up Python cache and temporary files
fd -HI -t f -e pyc -x rm -f {} 2>/dev/null || true
fd -HI -t d "__pycache__" -x rm -rf {} 2>/dev/null || true
```

```bash
# Remove temporary debug files from root only
fd -t f 'debug_.*\.py$' -d 1 -x rm -f {} 2>/dev/null || true
fd -t f 'temp_.*\.py$'  -d 1 -x rm -f {} 2>/dev/null || true
fd -t f 'demo_.*\.py$'  -d 1 -x rm -f {} 2>/dev/null || true
```

```bash
# Clean up build artifacts
rm -rf build/ dist/ .pytest_cache/ .coverage coverage.xml 2>/dev/null || true
rm -rf .mypy_cache/ .ruff_cache/ 2>/dev/null || true
```

**Step 3: Install Dependencies**

```bash
uv sync --all-extras
```

**Step 4: Code Quality Checks**

```bash
# Run code formatting and linting
uv run ruff check && uv run ruff format --check
```

```bash
# Run type checking
uv run mypy src/
```

```bash
# Run security checks
uv run bandit -r src/
```

**Step 5: Run Tests**

```bash
# Run full test suite
uv run pytest --tb=short --cov-report=term --cov-fail-under=65
```

**Step 6: Build and Validate Package**

```bash
# Build package
uv run python -m build
```

```bash
# Validate package
uv run twine check dist/*
```

**Step 7: Get Tool Count for Documentation**

```bash
# Count tools for documentation validation
TOOL_COUNT=$(rg -c '@mcp\.tool' --glob '!tests/**' --glob '!__pycache__/**' src | awk -F: '{sum+=$2} END {print sum+0}')
echo "Total tools: $TOOL_COUNT"
```

**Step 8: Build Sphinx Documentation (if present)**

```bash
# Build documentation if docs/ exists
if [ -d "docs/" ]; then
  cd docs/ && make clean && make html && cd ..
  echo "✅ Documentation build successful"
else
  echo "📝 No docs/ directory found"
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

**Step 1: Get Tool Count**

```bash
# Count total tools
TOOL_COUNT=$(fd -t f -e py -E tests -E __pycache__ . src/ -x rg -c "@mcp\.tool" | awk '{sum+=$1} END {print sum}')
echo "Total tools: $TOOL_COUNT"
```

**Step 2: Extract Tool Names**

```bash
# Extract tool names and save to file
echo "🔍 Available tools with descriptions:" > /tmp/current_tools.txt
fd -t f -e py -E tests . src/ -x rg -A 5 "@mcp\.tool" | rg "def ([a-z_]+)" -o -r '$1' | sort >> /tmp/current_tools.txt
```

**Step 3: Extract Tool Categories**

```bash
# Extract tool categories from docstrings
echo "🔍 Tool categories:" > /tmp/tool_categories.txt
fd -t f -e py -E tests . src/ -x rg -B 2 -A 10 "@mcp\.tool" | rg "[🔍📊🧪🌐🛡️📈🎯🔧📱📋]" >> /tmp/tool_categories.txt
```

**Step 4: Extract Dependencies**

```bash
# Extract dependencies
echo "🔍 Current dependencies:" > /tmp/current_deps.txt
rg -A 20 "dependencies =" pyproject.toml >> /tmp/current_deps.txt
```

**Step 5: Get Version Info**

```bash
# Extract version info
CURRENT_VERSION=$(rg '^version =' pyproject.toml | rg -o '"[^"]*"' | tr -d '"')
echo "Current version: $CURRENT_VERSION"
```

**Step 6: Review Data Summary**

```bash
# Display extracted data for review
echo "📋 Current Tool Data Summary:"
echo "- Total tools: $TOOL_COUNT"
echo "- Current version: $CURRENT_VERSION"
echo "- Tool list saved to: /tmp/current_tools.txt"
echo "- Categories saved to: /tmp/tool_categories.txt"
echo "- Dependencies saved to: /tmp/current_deps.txt"
```

**Step 7: Review Tool List**

```bash
# Show tool list for verification
cat /tmp/current_tools.txt
```

#### 4.1.1 Environment Variables Documentation Validation

**CRITICAL**: Ensure all environment variables used in the code are documented in README.md:

**Step 1: Extract environment variables from codebase**

```bash
# Extract all environment variables used in code
echo "🔍 Environment variables found in codebase:" > /tmp/env_vars_code.txt
fd -t f -e py -E tests -E __pycache__ . src/ -x rg -o "os\.getenv\(['\"]([^'\"]+)['\"]" -r '$1' | sort -u >> /tmp/env_vars_code.txt
rg -o "environ\.get\(['\"]([^'\"]+)['\"]" -r '$1' src/ | sort -u >> /tmp/env_vars_code.txt

# Show unique environment variables
sort /tmp/env_vars_code.txt | uniq
```

**Step 2: Check environment variables in README.md**

```bash
# Extract environment variables documented in README.md
echo "📖 Environment variables documented in README.md:" > /tmp/env_vars_readme.txt
rg -o "export ([A-Z_]+)=" -r '$1' README.md | sort -u >> /tmp/env_vars_readme.txt

# Show documented variables
cat /tmp/env_vars_readme.txt
```

**Step 3: Compare and validate**

```bash
# Show environment variables that might be missing from README
echo "⚠️  Checking for undocumented environment variables..."
UNDOCUMENTED=$(comm -23 <(sort /tmp/env_vars_code.txt | uniq) <(sort /tmp/env_vars_readme.txt | uniq))
if [ -n "$UNDOCUMENTED" ]; then
  echo "❌ Environment variables missing from README.md:"
  echo "$UNDOCUMENTED"
  echo "Please update README.md environment variables section"
else
  echo "✅ All environment variables are documented in README.md"
fi
```

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

  **Step 1: Check for docs directory**

  ```bash
  # Check if docs exist
  if [ -d "docs/" ]; then
    echo "📖 Found docs directory"
    cd docs/
  else
    echo "� No docs/ directory found - skipping Sphinx documentation update"
    exit 0
  fi
  ```

  **Step 2: Update tool count in documentation**

  ```bash
  # Update tool count in RST files
  echo "🔢 Updating tool count to $TOOL_COUNT in documentation..."
  fd -e rst . -x sed -i.bak "s/[0-9]\+ comprehensive tools/$TOOL_COUNT comprehensive tools/g"
  fd -e rst . -x sed -i.bak "s/[0-9]\+ specialized tools/$TOOL_COUNT specialized tools/g"
  fd -e rst . -x sed -i.bak "s/[0-9]\+ tools/$TOOL_COUNT tools/g"
  ```

  **Step 3: Validate tool documentation completeness**

  ```bash
  # Check for missing tools in mcp_tools.rst
  if [ -f "mcp_tools.rst" ]; then
    DOCUMENTED_TOOLS=$(rg -c "^[🔍📊🧪🌐🛡️📈🎯🔧📱📋📄📂📦📝🚨] " mcp_tools.rst || echo "0")
    echo "📚 Found $DOCUMENTED_TOOLS documented tools in mcp_tools.rst"
  else
    echo "⚠️  No mcp_tools.rst found - documentation may be incomplete"
  fi
  ```

  **Step 4: Check for tool count mismatch**

  ```bash
  # Warn if counts don't match
  if [ "$DOCUMENTED_TOOLS" -lt "$TOOL_COUNT" ]; then
    echo "⚠️  WARNING: mcp_tools.rst has $DOCUMENTED_TOOLS tools but codebase has $TOOL_COUNT"
    echo "   Please manually update docs/mcp_tools.rst with missing tools"
  fi
  ```

  **Step 5: Show actual tools for comparison**

  ```bash
  # Show current tools in codebase
  echo "   Current tools in codebase:"
  cd .. && fd -t f -e py . src/ -x rg -A 1 "@mcp\.tool" | rg "def " | sed 's/.*def //' | sed 's/(.*//g' | sort
  cd docs/
  ```

  **Step 6: Build documentation**

  ```bash
  # Test documentation build
  echo "🏗️  Building documentation..."
  if command -v make &> /dev/null; then
    make clean && make html
  else
    echo "⚠️  Make not available - cannot build documentation"
  fi
  ```

  **Step 7: Clean up and return**

  ```bash
  # Clean up backup files and return to root
  fd -e bak . -X rm 2>/dev/null || true
  cd ..
  echo "📚 Documentation update completed"
  ```

**Manual Documentation Updates Required:**

- [ ] **docs/mcp_tools.rst**: Verify all 21 tools are documented with current parameters and descriptions
- [ ] **docs/tool_reference.rst**: Update complete API reference for any new or changed tools
- [ ] **docs/examples.rst**: Update code examples to reflect current API signatures and new features
- [ ] **docs/index.rst**: Update overview and feature highlights with latest capabilities
- [ ] **docs/configuration.rst**: Add any new configuration options or environment variables
- [ ] **Tool categorization**: Ensure all tools are properly categorized (Analysis, Info, Log, Pytest, Pagination, Search)
- [ ] **Parameter documentation**: Verify all new parameters like `response_mode`, filtering options are documented
- [ ] **Example responses**: Update example JSON responses to match current tool output format

#### 4.3 Validate Documentation Accuracy

**⚠️ CRITICAL**: Verify all documentation matches actual implementation:

**Step 1: Check README.md tool count**

```bash
# Check README.md tool count matches actual
README_TOOL_COUNT=$(rg -o "[0-9]+ tools" README.md | head -1 | rg -o "[0-9]+")
echo "README tools: $README_TOOL_COUNT, Actual tools: $TOOL_COUNT"
```

**Step 2: Validate tool count match**

```bash
# Validate counts match
if [ "$README_TOOL_COUNT" != "$TOOL_COUNT" ]; then
  echo "❌ README.md tool count ($README_TOOL_COUNT) doesn't match actual ($TOOL_COUNT)"
  exit 1
else
  echo "✅ README.md tool count matches actual count"
fi
```

**Step 3: Extract tools from README**

```bash
# Extract tools mentioned in README
echo "🔍 Checking tool references in README..."
rg -o "analyze_[a-z_]*|get_[a-z_]*|extract_[a-z_]*|search_[a-z_]*" README.md | sort -u > /tmp/readme_tools.txt
```

**Step 4: Extract actual tools from code**

```bash
# Extract actual tools from codebase
fd -t f -e py -E tests . src/ -x rg -o "def ([a-z_]+)" -r '$1' | rg -v "^_" | rg -v "register_" | sort > /tmp/actual_tools.txt
```

**Step 5: Compare tool lists**

```bash
# Check for mismatches between README and actual tools
if ! diff /tmp/readme_tools.txt /tmp/actual_tools.txt > /dev/null; then
  echo "❌ Tool references in README don't match actual tools"
  echo "Please update README.md tool references"
  exit 1
else
  echo "✅ README tool references match actual tools"
fi
```

**Step 6: Validate docs/ folder (if present)**

```bash
# Check docs folder documentation
if [ -d "docs/" ]; then
  echo "📚 Validating docs/ folder documentation..."
else
  echo "📝 No docs/ folder found - skipping docs validation"
fi
```

**Step 7: Check docs tool count**

```bash
# Check docs tool count if docs exist
if [ -f "docs/mcp_tools.rst" ]; then
  DOCS_TOOL_COUNT=$(rg -o "[0-9]+ comprehensive tools" docs/mcp_tools.rst | head -1 | rg -o "[0-9]+")
  echo "Docs tool count: $DOCS_TOOL_COUNT"
else
  echo "No mcp_tools.rst found"
fi
```

**Step 8: Validate docs tool count**

```bash
# Validate docs tool count matches
if [ -n "$DOCS_TOOL_COUNT" ] && [ "$DOCS_TOOL_COUNT" != "$TOOL_COUNT" ]; then
  echo "❌ docs/mcp_tools.rst tool count ($DOCS_TOOL_COUNT) doesn't match actual ($TOOL_COUNT)"
  exit 1
elif [ -n "$DOCS_TOOL_COUNT" ]; then
  echo "✅ docs/mcp_tools.rst tool count matches actual ($TOOL_COUNT)"
fi
```

**Step 9: Check for broken doc references**

```bash
# Check for broken internal links in documentation
if [ -d "docs/" ]; then
  echo "🔗 Checking for broken internal references in docs..."
  BROKEN_DOCS=$(fd -e rst . docs/ -x rg ":doc:" | rg -o ":doc:\`[^\`]+\`" | rg -o "[^\`]+\`$" | rg -o "^[^\`]+" | sort -u)
  if [ -n "$BROKEN_DOCS" ]; then
    echo "📋 Found doc references (verify these files exist):"
    echo "$BROKEN_DOCS"
  fi
fi
```

**Step 10: Test documentation build**

```bash
# Test documentation build if Makefile exists
if [ -f "docs/Makefile" ]; then
  echo "🏗️  Testing documentation build..."
  cd docs/ && make html > /tmp/docs_build.log 2>&1 && cd ..
  if [ $? -eq 0 ]; then
    echo "✅ Documentation builds successfully"
  else
    echo "❌ Documentation build failed - check docs/"
    exit 1
  fi
fi
```

**Step 11: Final validation summary**

```bash
# Summary
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

**Monitor workflows using GitHub CLI**:

```bash
# Check recent workflow runs (avoids editor issues)
GH_PAGER=cat gh run list --limit 5

# Wait for workflows to complete and check again
sleep 30 && GH_PAGER=cat gh run list --limit 5

# Check specific workflow by name
GH_PAGER=cat gh run list --workflow="CI/CD Pipeline" --limit 3
```

- [ ] **If pipeline fails**:
  - Analyze failure logs in GitHub Actions
  - Fix issues locally
  - Push fixes and wait for pipeline to pass

**View detailed workflow run information**:

```bash
# Get workflow run ID from the list above, then view details
GH_PAGER=cat gh run view [WORKFLOW_RUN_ID]

# Example: GH_PAGER=cat gh run view 17435817326
# This shows job status, artifacts, and any annotations
```

### 7. 🏷️ Create Release Tag

**ONLY after CI/CD pipeline succeeds completely**:

- [ ] **Create and push version tag**:
  ```bash
  git tag v[X.Y.Z]
  git push origin v[X.Y.Z]
  ```

### 8. 🎉 Final Release Automation

The tag push will automatically trigger:

- [ ] **Production PyPI publication** (via `ci-cd.yml` workflow when tag is pushed)
- [ ] **GitHub Release creation** with:
  - Release notes from CHANGELOG.md
  - Automatic release notes generation
  - Links to PyPI package

**Monitor tag-triggered workflows**:

```bash
# Wait for tag workflows to start and complete
sleep 10 && GH_PAGER=cat gh run list --limit 3

# Check for release creation
GH_PAGER=cat gh release list --limit 3

# View release details
GH_PAGER=cat gh release view v[X.Y.Z]
```

- [ ] **Verify successful publication**:

**Check PyPI publication**:

```bash
# Verify PyPI publication using uv/python
curl -s "https://pypi.org/pypi/gitlab-pipeline-analyzer/json" | python3 -c "
import sys, json
data = json.load(sys.stdin)
print(f'Latest version: {data[\"info\"][\"version\"]}')
print(f'Release date: {data[\"releases\"][data[\"info\"][\"version\"]][0][\"upload_time\"]}')
print(f'PyPI URL: {data[\"info\"][\"project_url\"]}')
"

# Test installation with uv (recommended)
uv pip install gitlab-pipeline-analyzer==[X.Y.Z]

# Alternative: Test with pip
pip install gitlab-pipeline-analyzer==[X.Y.Z]
```

**Check GitHub Release**:

```bash
# Verify GitHub release was created
GH_PAGER=cat gh release view v[X.Y.Z]

# Check that CI/CD workflow completed successfully for the tag
GH_PAGER=cat gh run list --branch="v[X.Y.Z]" --limit 3
```

## ⚠️ Important Notes

- **Never skip quality checks** - they prevent broken releases
- **Never skip documentation validation** - README.md is the primary PyPI documentation
- **Environment variables must be documented** - All variables used in code must be in README.md
- **TestPyPI publication happens on every main push** - use for testing
- **Production PyPI publication only happens on version tags** - no rollbacks!
- **CI/CD workflow handles both TestPyPI and PyPI** - separate `release.yml` is not used for tag-based releases
- **GitHub Release is automatic** - manual editing available post-creation
- **Version must follow semver strictly** - tools and CI depend on it
- **Tool count and descriptions must be current** - users rely on accurate documentation for feature discovery
- **Use GitHub CLI with GH_PAGER=cat** - prevents editor issues when monitoring workflows
- **🚨 TERMINAL PERFORMANCE**: All bash scripts have been broken into small steps to prevent terminal freezing
- **📋 STEP-BY-STEP EXECUTION**: Run each code block separately - do not combine multiple steps into single terminal commands

## 🆘 Troubleshooting

- **Tests failing**: Check test logs, fix code, ensure 65%+ coverage
- **Build failing**: Verify `pyproject.toml` syntax, check dependencies
- **PyPI publication failing**: Check for version conflicts, ensure unique version number
- **GitHub Actions stuck**: Check workflow permissions, secrets, and API limits
- **GitHub CLI issues**:
  - If `gh` commands open editor: Use `GH_PAGER=cat` prefix to disable pager
  - If workflows not visible: Check repository permissions and authentication
  - If commands fail: Ensure GitHub CLI is installed and authenticated (`gh auth status`)
- **Documentation out of sync**: Run tool validation commands, update README.md tool lists and examples
- **Environment variables undocumented**: Use environment variable validation commands to find missing variables in README.md
- **Sphinx documentation build failing**:
  - Check for missing dependencies: `pip install sphinx sphinx_rtd_theme myst_parser`
  - Verify all referenced files exist (broken :doc: links)
  - Check RST syntax errors in .rst files
  - Ensure all new tools are documented in docs/mcp_tools.rst
  - Update version in `docs/conf.py` to match `pyproject.toml`
- **Tool count mismatches**:
  - Run tool counting validation: actual vs README.md vs docs/mcp_tools.rst
  - Update all three locations: codebase, README.md, and docs/
  - Verify new tools have proper @mcp.tool decorators
- **PyPI page looks outdated**: README.md is cached by PyPI, may take a few minutes to update after publication
- **Workflow monitoring**: Use GitHub CLI commands with proper pager settings to avoid terminal issues

## 📦 Project Context

This is the **GitLab Pipeline Analyzer MCP** - a FastMCP server for analyzing GitLab CI/CD pipeline failures. It provides 21 MCP tools for comprehensive pipeline failure analysis and AI-assisted troubleshooting. The project itself is hosted on **GitHub** and uses **GitHub Actions** for CI/CD and PyPI publishing.

**Documentation Maintenance**: The project maintains comprehensive documentation in multiple locations:

- **README.md**: Primary PyPI package description and user-facing documentation
- **docs/ folder**: Detailed Sphinx documentation with complete API reference
- **CHANGELOG.md**: Version history and release notes
- All locations must be kept synchronized for accurate tool count and feature representation.
