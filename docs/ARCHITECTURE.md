# GitLab Pipeline Analyzer - Project Structure

## Overview

This FastMCP server analyzes GitLab CI/CD pipeline failures and extracts structured error/warning information for AI analysis.

## Project Structure

```
mcp/
├── gitlab_analyzer.py      # Main MCP server implementation
├── config.py              # Configuration management
├── test_client.py          # Test client for development
├── example.py              # Usage examples
├── pyproject.toml          # Python project configuration
├── requirements.txt        # Python dependencies
├── Makefile               # Build and run commands
├── setup.sh               # Automated setup script
├── .env.example           # Environment template
├── .env                   # Your actual environment (create from .env.example)
└── README.md              # Main documentation
```

## Key Components

### 1. GitLab Analyzer (`gitlab_analyzer.py`)

**Main Classes:**
- `GitLabAnalyzer`: GitLab API client for fetching pipeline/job data
- `LogParser`: Extracts errors/warnings from CI/CD logs using regex patterns
- `JobInfo`, `LogEntry`, `PipelineAnalysis`: Pydantic models for structured data

**MCP Tools:**
- `analyze_failed_pipeline(pipeline_id)`: Complete pipeline failure analysis
- `get_pipeline_jobs(pipeline_id)`: Get all jobs for a pipeline
- `get_job_trace(job_id)`: Get trace log for a specific job
- `extract_log_errors(log_text)`: Extract errors/warnings from raw log text
- `get_pipeline_status(pipeline_id)`: Get basic pipeline status

### 2. Log Parsing Patterns

**Error Patterns:**
- Python exceptions (Error, Exception, Traceback)
- Test failures (FAILED, FAIL, AssertionError)
- Build errors (fatal error, ERROR)
- Linting errors (pylint, flake8, mypy)
- Process exit codes

**Warning Patterns:**
- General warnings (Warning, WARNING, WARN)
- Python warnings (DeprecationWarning, UserWarning, FutureWarning)

### 3. Configuration (`config.py`)

**Environment Variables:**
- `GITLAB_URL`: GitLab instance URL (default: https://gitlab.com)
- `GITLAB_TOKEN`: Personal access token (required)
- `GITLAB_PROJECT_ID`: Target project ID (required)

### 4. Usage Examples

**Python Client:**
```python
from fastmcp import Client

async with Client("gitlab_analyzer.py") as client:
    result = await client.call_tool("analyze_failed_pipeline", {
        "pipeline_id": 12345
    })
```

**FastMCP CLI:**
```bash
fastmcp run gitlab_analyzer.py:mcp
```

## Supported CI/CD Stages

The analyzer is optimized for Python projects with these common stages:
- **Lint Stage**: Code quality checks (pylint, flake8, mypy)
- **Test Stage**: Unit tests, integration tests (pytest, unittest)
- **Build Stage**: Package building, compilation

## Error Extraction Features

- **Contextual Information**: Provides surrounding lines for better understanding
- **Line Numbers**: Precise location of errors in logs
- **Categorization**: Separates errors from warnings
- **Pattern Matching**: Extensible regex-based pattern system
- **Structured Output**: JSON format suitable for AI analysis

## API Response Format

**Pipeline Analysis Response:**
```json
{
  "pipeline_id": 12345,
  "pipeline_status": "failed",
  "pipeline_url": "https://gitlab.com/project/pipelines/12345",
  "failed_jobs": [
    {
      "id": 67890,
      "name": "test",
      "status": "failed",
      "stage": "test",
      "failure_reason": "script_failure"
    }
  ],
  "analysis": {
    "test": [
      {
        "level": "error",
        "message": "FAILED: test_user_login - AssertionError: Expected True, got False",
        "line_number": 42,
        "context": "..."
      }
    ]
  },
  "summary": {
    "total_jobs": 5,
    "failed_jobs_count": 2,
    "total_errors": 8,
    "total_warnings": 3,
    "failed_stages": ["lint", "test"]
  }
}
```

## Development

**Setup:**
```bash
./setup.sh
make setup
make install
```

**Testing:**
```bash
make test
python example.py
```

**Running:**
```bash
make run              # Python script
make run-cli          # FastMCP CLI
```

This structure provides a comprehensive foundation for GitLab CI/CD pipeline analysis that can be easily extended for additional error patterns and CI/CD systems.
