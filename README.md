# GitLab Pipeline Analyzer MCP Server

A FastMCP server that analyzes GitLab CI/CD pipeline failures, extracts errors and warnings from job traces, and returns structured JSON responses.

## Features

- Analyze failed GitLab CI/CD pipelines by pipeline ID
- Extract failed jobs from pipelines
- Retrieve and parse job traces
- Extract errors and warnings from logs
- Return structured JSON responses for AI analysis
- Support for Python projects with lint, test, and build stages
- Multiple transport protocols: STDIO, HTTP, and SSE

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

# Optional: Configure transport settings
export MCP_HOST="127.0.0.1"  # Host for HTTP/SSE transport (default: 127.0.0.1)
export MCP_PORT="8000"       # Port for HTTP/SSE transport (default: 8000)
export MCP_PATH="/mcp"       # Path for HTTP transport (default: /mcp)
```

Note: Project ID is now passed as a parameter to each tool, making the server more flexible.

## Running the Server

The server supports three transport protocols:

### 1. STDIO Transport (Default)

Best for local tools and command-line scripts:

```bash
# Default STDIO transport
python server.py

# Or explicitly specify
python server.py --transport stdio
```

### 2. HTTP Transport

Recommended for web deployments and remote access:

```bash
# Start HTTP server
python http_server.py

# Or using the main server script
python server.py --transport http --host 127.0.0.1 --port 8000 --path /mcp

# Or using environment variables
MCP_TRANSPORT=http MCP_HOST=0.0.0.0 MCP_PORT=8080 python server.py
```

The HTTP server will be available at: `http://127.0.0.1:8000/mcp`

### 3. SSE Transport

For compatibility with existing SSE clients:

```bash
# Start SSE server
python sse_server.py

# Or using the main server script
python server.py --transport sse --host 127.0.0.1 --port 8000
```

The SSE server will be available at: `http://127.0.0.1:8000`

## Using with MCP Clients

### HTTP Transport Client Example

```python
from fastmcp.client import Client

# Connect to HTTP MCP server
async with Client("http://127.0.0.1:8000/mcp") as client:
    # List available tools
    tools = await client.list_tools()

    # Analyze a pipeline
    result = await client.call_tool("analyze_pipeline", {
        "project_id": "123",
        "pipeline_id": "456"
    })
```

### Configuration for Multiple Servers

```python
config = {
    "mcpServers": {
        "gitlab": {
            "url": "http://127.0.0.1:8000/mcp",
            "transport": "http"
        }
    }
}

async with Client(config) as client:
    result = await client.call_tool("gitlab_analyze_pipeline", {
        "project_id": "123",
        "pipeline_id": "456"
    })
```

## Development

### Setup

```bash
# Install dependencies
uv sync --all-extras

# Install pre-commit hooks
uv run pre-commit install
```

### Running tests

```bash
# Run all tests
uv run pytest

# Run tests with coverage
uv run pytest --cov=gitlab_analyzer --cov-report=html

# Run security scans
uv run bandit -r src/
```

### Code quality

```bash
# Format code
uv run ruff format

# Lint code
uv run ruff check --fix

# Type checking
uv run mypy src/
```

## GitHub Actions

This project includes comprehensive CI/CD workflows:

### CI Workflow (`.github/workflows/ci.yml`)
- **Triggers**: Push to `main`/`develop`, Pull requests
- **Features**:
  - Tests across Python 3.10, 3.11, 3.12
  - Code formatting with Ruff
  - Linting with Ruff
  - Type checking with MyPy
  - Security scanning with Bandit
  - Test coverage reporting
  - Build validation

### Release Workflow (`.github/workflows/release.yml`)
- **Triggers**: GitHub releases, Manual dispatch
- **Features**:
  - Automated PyPI publishing with trusted publishing
  - Support for TestPyPI deployment
  - Build artifacts validation
  - Secure publishing without API tokens

### Security Workflow (`.github/workflows/security.yml`)
- **Triggers**: Push, Pull requests, Weekly schedule
- **Features**:
  - Bandit security scanning
  - Trivy vulnerability scanning
  - SARIF upload to GitHub Security tab
  - Automated dependency scanning

### Setting up PyPI Publishing

1. **Configure PyPI Trusted Publishing**:
   - Go to [PyPI](https://pypi.org/manage/account/publishing/) or [TestPyPI](https://test.pypi.org/manage/account/publishing/)
   - Add a new trusted publisher with:
     - PyPI project name: `gitlab-pipeline-analyzer`
     - Owner: `your-github-username`
     - Repository name: `your-repo-name`
     - Workflow name: `release.yml`
     - Environment name: `pypi` (or `testpypi`)

2. **Create GitHub Environment**:
   - Go to repository Settings → Environments
   - Create environments named `pypi` and `testpypi`
   - Configure protection rules as needed

3. **Publishing**:
   - **TestPyPI**: Use workflow dispatch in Actions tab
   - **PyPI**: Create a GitHub release to trigger automatic publishing

### Pre-commit Hooks

The project uses pre-commit hooks for code quality:

```bash
# Install hooks
uv run pre-commit install

# Run hooks manually
uv run pre-commit run --all-files
```

Hooks include:
- Trailing whitespace removal
- End-of-file fixing
- YAML/TOML validation
- Ruff formatting and linting
- MyPy type checking
- Bandit security scanning

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

## Development

```bash
# Install development dependencies
uv sync

# Run tests
uv run pytest

# Run linting and type checking
uv run tox -e lint,type

# Run all quality checks
uv run tox
```

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Author

**Siarhei Skuratovich**

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run the test suite
5. Submit a pull request

---

**Note**: This MCP server is designed to work with GitLab CI/CD pipelines and requires appropriate API access tokens.
