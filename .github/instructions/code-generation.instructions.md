---
applyTo: "**"
---

Provide project context and coding guidelines that AI should follow when generating code, answering questions, or reviewing changes.

## Command Line Tools Preferences

- **Always use `uv`** when running Python files, scripts, or packages instead of `pip` or `python`
- **Use modern tools**: Prefer `fd` over `find` and `rg` over `grep` for better performance and cleaner output
- **Check tool availability**: Before using `fd` or `rg`, verify they're available in the environment
- **Avoid freezing terminals**:
  - Do not create excessively long terminal commands
  - Break complex operations into smaller, manageable steps
  - Use `head`, `tail`, or `limit` parameters to control output size
- **File viewing**: Use `read_file` tool instead of `cat` commands that don't return to terminal

## Python Development Guidelines

- **Use Pylance MCP server** for Python-based script commands, syntax checking, and code analysis
- **Package management**: Always use `uv` for Python package installation and management
- **Testing**: Use `uv run pytest` for running tests
- **Code formatting**: Use `uv run ruff` for linting and formatting
- **Type checking**: Use `uv run mypy` for type checking

## File Management and Cleanup

- **Always ensure proper cleanup** of unneeded files before commits
- **Use appropriate tools**:
  - `fd` for file searching with patterns
  - `rg` for text searching and pattern matching
  - `uv` for all Python-related operations
- **Respect .gitignore**: Don't commit temporary files, build artifacts, or cache files

## Terminal Command Best Practices

- **Small, focused commands**: Break large operations into multiple smaller commands
- **Use limits and filters**: Apply `--limit`, `head`, `tail` to prevent overwhelming output
- **Error handling**: Use `|| true` for non-critical cleanup operations
- **Pager management**: Use `GH_PAGER=cat` for GitHub CLI to avoid editor issues
- **Complex operations**: For non-Python commands that are large or complex, write them to temporary files and execute:

  ```bash
  # Example: Create temporary script for complex operations
  cat > /tmp/cleanup_script.sh << 'EOF'
  #!/bin/bash
  fd -HI -t f -e pyc -x rm -f {} 2>/dev/null || true
  fd -HI -t d "__pycache__" -x rm -rf {} 2>/dev/null || true
  rm -rf build/ dist/ .pytest_cache/ .coverage coverage.xml 2>/dev/null || true
  EOF

  chmod +x /tmp/cleanup_script.sh
  /tmp/cleanup_script.sh
  rm /tmp/cleanup_script.sh
  ```

## GitHub CLI Usage

- **Workflow monitoring**: Use `GH_PAGER=cat gh run list --limit 5` to monitor CI/CD pipelines
- **Release management**: Use `gh release list` and `gh release view` for release verification
- **Avoid editor conflicts**: Always prefix GitHub CLI commands with `GH_PAGER=cat`

## Documentation Standards

- **Environment variables**: Ensure all environment variables used in code are documented in README.md
- **Version synchronization**: Keep versions consistent across `pyproject.toml`, `docs/conf.py`, and other files
- **Tool counts**: Validate that documentation reflects actual number of tools in codebase
