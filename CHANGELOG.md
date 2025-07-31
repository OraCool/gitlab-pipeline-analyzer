# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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
