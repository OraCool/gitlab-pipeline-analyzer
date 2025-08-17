# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.2.3] - 2025-08-17

### Fixed 🐛
- **GitHub Actions CI/CD Pipeline**: Prepared for automated publishing with comprehensive checks
  - All tests passing (207 tests, 84.82% coverage)
  - Code quality checks passing (ruff, mypy, bandit)
  - Pre-commit hooks verified
  - Package building and integrity checks successful
  - Ready for automated PyPI publishing via GitHub Actions

### Infrastructure 🔧
- Enhanced CI/CD pipeline with proper test coverage requirements
- Improved security scanning with Bandit and Trivy
- Optimized build process with uv package manager
- Configured trusted publishing for PyPI deployment

## [0.2.2] - 2025-08-06

## [0.2.1] - 2025-08-06

### Enhanced 🚀
- **AI-Optimized Tool Documentation**: Complete overhaul of all 12 MCP tool docstrings for AI assistant effectiveness
  - Added visual indicators (🔍 DIAGNOSE, 🎯 FOCUS, 📊 METRICS, etc.) for instant tool identification
  - Comprehensive "WHEN TO USE" guidance with specific scenarios and use cases
  - "WHAT YOU GET" sections documenting expected output structure and data fields
  - "AI ANALYSIS TIPS" providing field-specific guidance for better interpretation
  - "WORKFLOW" integration showing clear tool sequencing and investigation paths

- **Dramatically improved pytest error context extraction**
  - Added full error text from pytest failures with complete traceback details
  - Enhanced context includes: test names, file paths, function names, exception details
  - Added structured traceback information with code lines and error messages
  - Improved error messages now include the actual failing code and assertion details
  - Better context for AI analysis with comprehensive failure information

### Documentation 📚
- Added comprehensive AI usage guides (`IMPROVED_TOOL_PROMPTS.md`)
- Created workflow documentation for different investigation scenarios
- Added tool-by-tool enhancement documentation with examples
- Complete AI optimization summary with impact assessment

### Fixed
- Enhanced pytest parser to extract and include full error context in MCP responses
- Fixed missing context information in failed pipeline analysis results
- Improved error extraction to include both summary and detailed failure information

### Impact
- 50% faster AI tool selection through clear usage indicators
- Improved analysis quality with structured output documentation
- Better investigation workflows with logical tool progression
- Enhanced user experience through more accurate AI-assisted troubleshooting

## [0.2.0] - 2025-08-06

### Added
- Comprehensive test coverage for all MCP tools (info, log, pytest, analysis, utils)
- Added 280+ unit tests covering edge cases and error handling
- Added test documentation and summary in `tests/test_mcp_tools_summary.md`

### Updated
- **Major dependency updates:**
  - FastMCP: 2.0.0 → 2.11.1 (major feature updates)
  - python-gitlab: 4.0.0 → 6.2.0 (major API improvements)
  - httpx: 0.25.0 → 0.28.1 (performance and security fixes)
  - pydantic: 2.0.0 → 2.11.7 (validation improvements)
  - typing-extensions: 4.0.0 → 4.14.1 (latest type hints)
- **Development tool updates:**
  - pytest: 7.0.0 → 8.4.1 (latest testing framework)
  - pytest-asyncio: 0.21.0 → 1.1.0 (improved async testing)
  - pytest-cov: 4.0.0 → 6.2.1 (coverage improvements)
  - ruff: 0.1.0 → 0.12.7 (latest linting and formatting)
  - mypy: 1.0.0 → 1.17.1 (improved type checking)
  - pre-commit-hooks: v4.6.0 → v5.0.0 (latest hooks)

### Improved
- Enhanced code quality with updated linting rules
- Better error handling and type safety
- Improved test coverage and reliability
- Updated pre-commit configuration for better development experience

## [0.1.2] - 2025-08-04

### Fixed
- Added missing `main` function to `gitlab_analyzer.mcp.server` module to fix entry point execution
- Fixed ImportError when running `gitlab-analyzer` command via uvx

## [0.1.1] - Previous Release

### Added
- Initial release of GitLab Pipeline Analyzer MCP Server
- FastMCP server for analyzing GitLab CI/CD pipeline failures
- Support for extracting errors and warnings from job traces
- Structured JSON responses for AI analysis
- GitHub Actions workflows for CI/CD and PyPI publishing
- Comprehensive code quality checks (Ruff, MyPy, Bandit)
- Pre-commit hooks for development
- Security scanning with Trivy and Bandit

### Features
- `analyze_failed_pipeline(project_id, pipeline_id)` - Analyze a failed pipeline by ID
- `get_pipeline_jobs(project_id, pipeline_id)` - Get all jobs for a pipeline
- `get_job_trace(project_id, job_id)` - Get job trace/logs
- `extract_errors_from_logs(logs)` - Extract structured errors from logs

## [0.1.0] - 2025-07-31

### Added
- Initial project setup
- Basic MCP server implementation
- GitLab API integration
- Pipeline analysis capabilities
