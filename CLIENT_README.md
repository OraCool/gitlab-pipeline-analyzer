# GitLab Job Result Analyzer - MCP Client Scripts

This directory contains Python scripts that use the FastMCP client to connect to the GitLab Pipeline Analyzer MCP server and retrieve job results, analyze failed pipelines, and extract errors/warnings.

## Scripts

### 1. `get_job_result.py` - Full-Featured CLI Tool

A comprehensive command-line interface for analyzing GitLab CI/CD jobs and pipelines.

**Features:**
- Analyze single jobs with error/warning extraction
- Get raw job trace logs
- Analyze failed pipelines with complete error analysis
- Get all jobs or only failed jobs for a pipeline
- Get pipeline status information
- JSON output support
- Formatted console output with emojis and summaries

**Usage Examples:**

```bash
# Analyze a single job
python get_job_result.py --project-id 12345 --job-id 67890

# Get raw trace for a job
python get_job_result.py --project-id 12345 --job-id 67890 --trace-only

# Analyze failed pipeline (full analysis with errors)
python get_job_result.py --project-id 12345 --pipeline-id 11111 --analyze-failures

# Get all jobs in a pipeline
python get_job_result.py --project-id 12345 --pipeline-id 11111 --all-jobs

# Get only failed jobs
python get_job_result.py --project-id 12345 --pipeline-id 11111 --failed-jobs-only

# Get pipeline status only
python get_job_result.py --project-id 12345 --pipeline-id 11111 --status-only

# Output as JSON
python get_job_result.py --project-id 12345 --job-id 67890 --json
```

**Command Line Options:**

```
--project-id        GitLab project ID or path (required)
--job-id           GitLab job ID to analyze
--trace-only       Get only raw trace log (requires --job-id)
--pipeline-id      GitLab pipeline ID to analyze
--analyze-failures Full pipeline analysis with error extraction
--all-jobs         Get all jobs in pipeline
--failed-jobs-only Get only failed jobs in pipeline
--status-only      Get pipeline status only
--json             Output results as JSON
--server-script    Path to MCP server script (default: server.py)
```

### 2. `example_client.py` - Simple Usage Examples

A simple script demonstrating basic usage patterns for the MCP client.

**Features:**
- Shows how to connect to MCP server
- Demonstrates all available MCP tools
- Simple error handling
- Easy to understand code examples

**Usage:**
```bash
python example_client.py
```

## Prerequisites

### Environment Setup

1. **Environment Variables:**
   ```bash
   export GITLAB_URL="https://your-gitlab-instance.com"
   export GITLAB_TOKEN="your-gitlab-token"
   ```

2. **Python Dependencies:**
   ```bash
   pip install fastmcp>=2.0.0
   ```

3. **MCP Server:**
   Ensure the MCP server script (`server.py`) is available in the same directory or specify its path using `--server-script`.

### VS Code Claude Desktop Setup

For VS Code with Claude Desktop, add this configuration to your `claude_desktop_config.json`:

```json
{
    "servers": {
        "gitlab-pipeline-analyzer": {
            "type": "stdio",
            "command": "uvx",
            "args": [
                "--from",
                "gitlab_pipeline_analyzer==0.1.2",
                "gitlab-analyzer",
                "--transport",
                "${input:mcp_transport}"
            ],
            "env": {
                "GITLAB_URL": "${input:gitlab_url}",
                "GITLAB_TOKEN": "${input:gitlab_token}"
            }
        },
        "local-gitlab-analyzer": {
            "type": "stdio",
            "command": "uv",
            "args": [
                "run",
                "gitlab-analyzer"
            ],
            "cwd": "/path/to/your/mcp/project",
            "env": {
                "GITLAB_URL": "${input:gitlab_url}",
                "GITLAB_TOKEN": "${input:gitlab_token}"
            }
        },
        "enterprise-gitlab": {
            "command": "uvx",
            "args": ["--from", "gitlab-pipeline-analyzer", "gitlab-analyzer"],
            "env": {
                "GITLAB_URL": "https://gitlab.enterprise-corp.com",
                "GITLAB_TOKEN": "your-enterprise-token"
            }
        }
    },
    "inputs": [
        {
            "id": "mcp_transport",
            "type": "promptString",
            "description": "MCP Transport (stdio/http/sse)"
        },
        {
            "id": "gitlab_url",
            "type": "promptString",
            "description": "GitLab Instance URL"
        },
        {
            "id": "gitlab_token",
            "type": "promptString",
            "description": "GitLab Personal Access Token"
        }
    ]
}
```

**Configuration Options:**
- **Dynamic Setup**: Uses input prompts for flexible configuration
- **Local Development**: Points to your local development environment
- **Enterprise Setup**: Hardcoded values for specific company instances

### GitLab Token Permissions

Your GitLab token needs the following scopes:
- `read_api` - To access GitLab API
- `read_repository` - To access project information

## Available MCP Tools

The scripts use these MCP tools provided by the GitLab Pipeline Analyzer server:

1. **`analyze_single_job`** - Analyze a single job with error/warning extraction
2. **`get_job_trace`** - Get raw trace log for a specific job
3. **`get_pipeline_jobs`** - Get all jobs for a pipeline
4. **`get_failed_jobs`** - Get only failed jobs for a pipeline
5. **`analyze_failed_pipeline`** - Complete analysis of failed pipeline with errors
6. **`get_pipeline_status`** - Get pipeline status and basic information

## Output Examples

### Single Job Analysis
```
📊 Job Analysis Summary
   Job ID: 67890
   Job URL: https://gitlab.com/-/jobs/67890
   Errors: 3
   Warnings: 1
   Log entries: 45
   Has trace: True

🔴 Errors found:
   1. Build failed: missing dependency 'numpy'
   2. Test failed: assertion error in test_function()
   3. Deployment failed: connection timeout

🟡 Warnings found:
   1. Deprecated function usage in module.py:25
```

### Pipeline Analysis
```
📊 Pipeline Analysis Summary
   Pipeline ID: 11111
   Status: failed
   Failed jobs: 2
   Total errors: 5
   Total warnings: 3
   Failed stages: build, test

❌ Failed Jobs:
   • build_job (Stage: build, Reason: script_failure)
   • test_job (Stage: test, Reason: unknown_failure)
```

### JSON Output
```json
{
  "project_id": "12345",
  "job_id": 67890,
  "job_url": "https://gitlab.com/-/jobs/67890",
  "analysis": {
    "errors": [
      {
        "level": "error",
        "message": "Build failed: missing dependency 'numpy'",
        "line_number": 45,
        "timestamp": "2025-01-01T12:00:00"
      }
    ],
    "warnings": []
  },
  "summary": {
    "total_errors": 1,
    "total_warnings": 0,
    "total_log_entries": 45,
    "has_trace": true,
    "trace_length": 12845,
    "analysis_timestamp": "2025-01-01T12:30:00.123456"
  }
}
```

## Error Handling

Both scripts include comprehensive error handling:

- **Environment validation** - Checks for required environment variables
- **Server connectivity** - Validates MCP server script exists and is accessible
- **API errors** - Handles GitLab API errors gracefully
- **Network issues** - Catches and reports connection problems
- **Invalid parameters** - Validates command line arguments

## Development

### Adding New Functionality

To add new MCP tool usage:

1. Add the tool call in the analyzer class:
   ```python
   async def new_analysis_method(self, params):
       client = Client(self.server_script)
       async with client:
           result = await client.call_tool("new_tool_name", params)
           return result
   ```

2. Add CLI arguments if needed
3. Add result formatting in the main function

### Testing

Test the scripts with your GitLab instance:

```bash
# Test environment
python -c "import os; print('URL:', os.getenv('GITLAB_URL')); print('Token set:', bool(os.getenv('GITLAB_TOKEN')))"

# Test simple job analysis
python get_job_result.py --project-id YOUR_PROJECT_ID --job-id YOUR_JOB_ID

# Test with verbose output
python example_client.py
```

## Troubleshooting

### Common Issues

1. **"GITLAB_TOKEN environment variable is required"**
   - Set the `GITLAB_TOKEN` environment variable with a valid GitLab token

2. **"MCP server script not found: server.py"**
   - Ensure `server.py` exists in the current directory
   - Or specify the correct path with `--server-script`

3. **"Failed to analyze job: 404 Not Found"**
   - Check that the project ID and job ID are correct
   - Ensure your token has access to the project

4. **Connection timeouts**
   - Check your network connection to GitLab
   - Verify the GitLab URL is correct
   - Try increasing timeout values in the client

### Debug Mode

For debugging, you can modify the scripts to add more verbose logging:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## License

Copyright (c) 2025 Siarhei Skuratovich
Licensed under the MIT License
