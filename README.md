# GitLab Pipeline Analyzer MCP Server

A FastMCP server that analyzes GitLab CI/CD pipeline failures, extracts errors and warnings from job traces, and returns structured JSON responses.

## Features

- Analyze failed GitLab CI/CD pipelines by pipeline ID
- Extract failed jobs from pipelines
- Retrieve and parse job traces
- Extract errors and warnings from logs
- Return structured JSON responses for AI analysis
- Support for Python projects with lint, test, and build stages

## Installation

```bash
# Install dependencies
uv pip install -e .

# Or with pip
pip install -e .
```

## Configuration

Set the following environment variables:

```bash
export GITLAB_URL="https://gitlab.com"  # Your GitLab instance URL
export GITLAB_TOKEN="your-access-token"  # Your GitLab personal access token
```

Note: Project ID is now passed as a parameter to each tool, making the server more flexible.

## Usage

### Running the server

```bash
# Run with Python
python gitlab_analyzer.py

# Or with FastMCP CLI
fastmcp run gitlab_analyzer.py:mcp
```

### Available tools

1. **analyze_failed_pipeline(project_id, pipeline_id)** - Analyze a failed pipeline by ID
2. **get_pipeline_jobs(project_id, pipeline_id)** - Get all jobs for a pipeline
3. **get_job_trace(project_id, job_id)** - Get trace log for a specific job
4. **extract_log_errors(log_text)** - Extract errors and warnings from log text
5. **get_pipeline_status(project_id, pipeline_id)** - Get basic pipeline status

## Example

```python
import asyncio
from fastmcp import Client

async def analyze_pipeline():
    client = Client("gitlab_analyzer.py")
    async with client:
        result = await client.call_tool("analyze_failed_pipeline", {
            "project_id": "19133",  # Your GitLab project ID
            "pipeline_id": 12345
        })
        print(result)

asyncio.run(analyze_pipeline())
```

## Environment Setup

Create a `.env` file with your GitLab configuration:

```env
GITLAB_URL=https://gitlab.com
GITLAB_TOKEN=your-personal-access-token
```
