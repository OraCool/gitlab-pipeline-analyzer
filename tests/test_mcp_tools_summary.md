"""
Summary of tests created for MCP tools.

Copyright (c) 2025 Siarhei Skuratovich
Licensed under the MIT License - see LICENSE file for details

This file summarizes all the comprehensive tests that have been created for the
src/gitlab_analyzer/mcp/tools directory:

## Test Files Created:

### 1. test_mcp_analysis_tools.py
- Tests for analysis tools: analyze_failed_pipeline, analyze_single_job
- Covers success scenarios, error handling, HTTP errors, empty results
- Tests pipeline analysis with multiple failed jobs
- Tests error categorization and aggregation

### 2. test_mcp_info_tools.py
- Tests for info tools: get_pipeline_jobs, get_failed_jobs, get_job_trace,
  get_cleaned_job_trace, get_pipeline_status
- Covers successful data retrieval, error scenarios, empty results
- Tests ANSI sequence cleaning functionality
- Tests project_id type conversion

### 3. test_mcp_log_tools.py
- Tests for log tools: extract_log_errors
- Covers generic log parsing vs pytest-specific parsing
- Tests error and warning extraction from various log formats
- Tests exception handling and empty log scenarios

### 4. test_mcp_pytest_tools.py
- Tests for pytest tools: extract_pytest_detailed_failures, extract_pytest_short_summary,
  extract_pytest_statistics, analyze_pytest_job_complete
- Tests _extract_pytest_errors function with detailed failures and short summaries
- Covers traceback parsing and statistics extraction
- Tests error handling and empty trace scenarios

### 5. test_mcp_utils.py
- Tests for utils module: get_gitlab_analyzer, _is_pytest_log
- Tests GitLab analyzer singleton pattern and environment variable handling
- Tests pytest log detection with various log formats
- Covers edge cases like empty logs and mixed content

### 6. test_mcp_tools_main.py
- Tests for main tools module: register_tools function
- Tests that all tool categories are properly registered
- Validates tool structure, parameters, and return types
- Tests error handling and idempotent registration

## Key Testing Patterns:

1. **Mocking Strategy**: Uses unittest.mock to mock external dependencies like GitLab analyzer
2. **Fixtures**: Provides sample data for pipelines, jobs, logs, and analysis results
3. **Error Scenarios**: Tests HTTP errors, network failures, and parsing exceptions
4. **Edge Cases**: Tests empty data, malformed input, and boundary conditions
5. **Integration**: Tests tool registration and MCP server integration

## Coverage Areas:

- All MCP tool functions are tested
- Error handling paths are covered
- Different data scenarios (success, failure, empty)
- Tool registration and server integration
- Utility functions and helper methods

## Running the Tests:

```bash
# Run all MCP tool tests
uv run pytest tests/test_mcp_*.py -v

# Run specific test file
uv run pytest tests/test_mcp_analysis_tools.py -v

# Run with coverage
uv run pytest tests/test_mcp_*.py --cov=src/gitlab_analyzer/mcp/tools
```

## Notes:

- Tests use AsyncMock for async functions
- FastMCP server tools are accessed via get_tools() method
- Some tests require environment variable mocking for GitLab configuration
- Tests are designed to be independent and can run in any order
"""
