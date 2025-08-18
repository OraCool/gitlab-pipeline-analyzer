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

````bash
```bash
gitlab-analyzer
````

Or explicitly specify the transport:

```bash
gitlab-analyzer --transport stdio
```

### 2. HTTP Transport

Recommended for web deployments and remote access:

````bash
```bash
gitlab-analyzer-http
````

Or using the main server with transport option:

```bash
gitlab-analyzer --transport http --host 127.0.0.1 --port 8000 --path /mcp
```

Or with environment variables:

```bash
MCP_TRANSPORT=http MCP_HOST=0.0.0.0 MCP_PORT=8080 gitlab-analyzer
```

The HTTP server will be available at: `http://127.0.0.1:8000/mcp`

### 3. SSE Transport

For compatibility with existing SSE clients:

````bash
```bash
gitlab-analyzer-sse
````

Or using the main server with transport option:

```bash
gitlab-analyzer --transport sse --host 127.0.0.1 --port 8000
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

### VS Code Claude Desktop Configuration

Add the following to your VS Code Claude Desktop `claude_desktop_config.json` file:

```json
{
  "servers": {
    "gitlab-pipeline-analyzer": {
      "type": "stdio",
      "command": "uvx",
      "args": [
        "--from",
        "gitlab_pipeline_analyzer==0.2.5",
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
      "args": ["run", "gitlab-analyzer"],
      "cwd": "/path/to/your/mcp/project",
      "env": {
        "GITLAB_URL": "${input:gitlab_url}",
        "GITLAB_TOKEN": "${input:gitlab_token}"
      }
    },
    "acme-gitlab-analyzer": {
      "command": "uvx",
      "args": ["--from", "gitlab-pipeline-analyzer", "gitlab-analyzer"],
      "env": {
        "GITLAB_URL": "https://gitlab.acme-corp.com",
        "GITLAB_TOKEN": "your-token-here"
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

#### Configuration Examples Explained:

1. **`gitlab-pipeline-analyzer`** - Uses the published package from PyPI with dynamic inputs
2. **`local-gitlab-analyzer`** - Uses local development version with dynamic inputs
3. **`acme-gitlab-analyzer`** - Uses the published package with hardcoded company-specific values

#### Dynamic vs Static Configuration:

- **Dynamic inputs** (using `${input:variable_name}`) prompt you each time
- **Static values** are hardcoded for convenience but less secure
- For security, consider using environment variables or VS Code settings

### Remote Server Setup

For production deployments or team usage, you can deploy the MCP server on a remote machine and connect to it via HTTP transport.

#### Server Deployment

1. **Deploy on Remote Server:**

```bash
# On your remote server (e.g., cloud instance)
git clone <your-mcp-repo>
cd mcp
uv sync

# Set environment variables
export GITLAB_URL="https://gitlab.your-company.com"
export GITLAB_TOKEN="your-gitlab-token"
export MCP_HOST="0.0.0.0"  # Listen on all interfaces
export MCP_PORT="8000"
export MCP_PATH="/mcp"

# Start HTTP server
uv run python -m gitlab_analyzer.servers.stdio_server --transport http --host 0.0.0.0 --port 8000
```

2. **Using Docker (Recommended for Production):**

```dockerfile
# Dockerfile
FROM python:3.12-slim

WORKDIR /app
COPY . .

RUN pip install uv && uv sync

EXPOSE 8000

ENV MCP_HOST=0.0.0.0
ENV MCP_PORT=8000
ENV MCP_PATH=/mcp

CMD ["uv", "run", "python", "server.py", "--transport", "http"]
```

```bash
# Build and run
docker build -t gitlab-mcp-server .
docker run -p 8000:8000 \
  -e GITLAB_URL="https://gitlab.your-company.com" \
  -e GITLAB_TOKEN="your-token" \
  gitlab-mcp-server
```

#### Client Configuration for Remote Server

**VS Code Claude Desktop Configuration:**

```json
{
  "servers": {
    "remote-gitlab-analyzer": {
      "type": "http",
      "url": "https://your-mcp-server.com:8000/mcp"
    },
    "local-stdio-analyzer": {
      "type": "stdio",
      "command": "uv",
      "args": ["run", "gitlab-analyzer"],
      "cwd": "/path/to/your/mcp/project",
      "env": {
        "GITLAB_URL": "${input:gitlab_url}",
        "GITLAB_TOKEN": "${input:gitlab_token}"
      }
    }
  },
  "inputs": [
    {
      "id": "gitlab_url",
      "type": "promptString",
      "description": "GitLab Instance URL (for local STDIO servers only)"
    },
    {
      "id": "gitlab_token",
      "type": "promptString",
      "description": "GitLab Personal Access Token (for local STDIO servers only)"
    }
  ]
}
```

**Important Notes:**

- **Remote HTTP servers**: Environment variables are configured on the server side during deployment
- **Local STDIO servers**: Environment variables are passed from the client via the `env` block
- **Your server reads `GITLAB_URL` and `GITLAB_TOKEN` from its environment at startup**
- **The client cannot change server-side environment variables for HTTP transport**

#### Current Limitations:

**Single GitLab Instance per Server:**

- Each HTTP server deployment can only connect to **one GitLab instance** with **one token**
- **No user-specific authorization** - all clients share the same GitLab credentials
- **No multi-tenant support** - cannot serve multiple GitLab instances from one server

#### Workarounds for Multi-GitLab Support:

**Option 1: Multiple Server Deployments**

```bash
# Server 1 - Company GitLab
export GITLAB_URL="https://gitlab.company.com"
export GITLAB_TOKEN="company-token"
uv run python -m gitlab_analyzer.servers.stdio_server --transport http --port 8001

# Server 2 - Personal GitLab
export GITLAB_URL="https://gitlab.com"
export GITLAB_TOKEN="personal-token"
uv run python -m gitlab_analyzer.servers.stdio_server --transport http --port 8002
```

**Option 2: Use STDIO Transport for User-Specific Auth**

```json
{
  "servers": {
    "company-gitlab": {
      "type": "stdio",
      "command": "uv",
      "args": ["run", "gitlab-analyzer"],
      "env": {
        "GITLAB_URL": "https://gitlab.company.com",
        "GITLAB_TOKEN": "company-token"
      }
    },
    "personal-gitlab": {
      "type": "stdio",
      "command": "uv",
      "args": ["run", "gitlab-analyzer"],
      "env": {
        "GITLAB_URL": "https://gitlab.com",
        "GITLAB_TOKEN": "personal-token"
      }
    }
  }
}
```

**Option 3: Future Enhancement - Multi-Tenant Server**
To support user-specific authorization, the server would need modifications to:

- Accept GitLab URL and token as **tool parameters** instead of environment variables
- Implement **per-request authentication** instead of singleton GitLab client
- Add **credential management** and **security validation**

#### Recommended Approach by Use Case:

**Single Team/Company:**

- ✅ **HTTP server** with company GitLab credentials
- Simple deployment, shared access

**Multiple GitLab Instances:**

- ✅ **STDIO transport** for user-specific credentials
- ✅ **Multiple HTTP servers** (one per GitLab instance)
- Each approach has trade-offs in complexity vs. performance

**Personal Use:**

- ✅ **STDIO transport** for maximum flexibility
- Environment variables can be changed per session

````

**Key Differences:**
- **HTTP servers** (`type: "http"`) don't use `env` - they get environment variables from their deployment
- **STDIO servers** (`type: "stdio"`) use `env` because the client spawns the server process locally
- **Remote HTTP servers** are already running with their own environment configuration

#### How Environment Variables Work:

**For Remote HTTP Servers:**
- Environment variables are set **on the server side** during deployment
- The client just connects to the HTTP endpoint
- No environment variables needed in client configuration

**For Local STDIO Servers:**
- Environment variables are passed **from client to server** via the `env` block
- The client spawns the server process with these variables
- Useful for dynamic configuration per client

**Example Server-Side Environment Setup:**
```bash
# On remote server
export GITLAB_URL="https://gitlab.company.com"
export GITLAB_TOKEN="server-side-token"
uv run python -m gitlab_analyzer.servers.stdio_server --transport http --host 0.0.0.0 --port 8000
````

**Example Client-Side for STDIO:**

```json
{
  "type": "stdio",
  "env": {
    "GITLAB_URL": "https://gitlab.personal.com",
    "GITLAB_TOKEN": "client-specific-token"
  }
}
```

**Python Client for Remote Server:**

```python
from fastmcp.client import Client

# Connect to remote HTTP MCP server
async with Client("https://your-mcp-server.com:8000/mcp") as client:
    # List available tools
    tools = await client.list_tools()

    # Analyze a pipeline
    result = await client.call_tool("analyze_pipeline", {
        "project_id": "123",
        "pipeline_id": "456"
    })
```

#### Security Considerations for Remote Deployment

1. **HTTPS/TLS:**

```bash
# Use reverse proxy (nginx/traefik) with SSL
# Example nginx config:
server {
    listen 443 ssl;
    server_name your-mcp-server.com;

    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;

    location /mcp {
        proxy_pass http://localhost:8000/mcp;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

2. **Authentication (if needed):**

```bash
# Add API key validation in your deployment
export MCP_API_KEY="your-secret-api-key"

# Client usage with API key
curl -H "Authorization: Bearer your-secret-api-key" \
     https://your-mcp-server.com:8000/mcp
```

3. **Firewall Configuration:**

```bash
# Only allow specific IPs/networks
ufw allow from 192.168.1.0/24 to any port 8000
ufw deny 8000
```

### Configuration for Multiple Servers

```python
config = {
    "mcpServers": {
        "local-gitlab": {
            "url": "http://127.0.0.1:8000/mcp",
            "transport": "http"
        },
        "remote-gitlab": {
            "url": "https://mcp-server.your-company.com:8000/mcp",
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

For maintainers preparing releases, see [DEPLOYMENT.md](DEPLOYMENT.md) for detailed deployment preparation steps.

---

**Note**: This MCP server is designed to work with GitLab CI/CD pipelines and requires appropriate API access tokens.
