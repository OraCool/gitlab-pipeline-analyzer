Configuration Guide
===================

This guide covers configuration options for the GitLab Pipeline Analyzer MCP Server.

.. contents::
   :local:
   :depth: 2

Environment Variables
---------------------

Required Configuration
~~~~~~~~~~~~~~~~~~~~~~

**GITLAB_TOKEN**
    Your GitLab personal access token with ``api`` scope.

    .. code-block:: bash

        export GITLAB_TOKEN="glpat-xxxxxxxxxxxxxxxxxxxx"

**GITLAB_URL** (Optional)
    Your GitLab instance URL. Defaults to ``https://gitlab.com`` if not specified.

    .. code-block:: bash

        export GITLAB_URL="https://gitlab.company.com"

Transport Configuration
-----------------------

The server supports three transport protocols via FastMCP:

STDIO Transport (Default)
~~~~~~~~~~~~~~~~~~~~~~~~~~

Used by Claude Desktop and local development:

.. code-block:: bash

    gitlab-analyzer

This is the default mode and requires no additional configuration.

HTTP Transport
~~~~~~~~~~~~~~

For web applications and remote access:

.. code-block:: bash

    gitlab-analyzer --transport http --host 0.0.0.0 --port 8000

**Options:**

- ``--host``: Host to bind to (default: ``127.0.0.1``)
- ``--port``: Port number (default: ``8000``)

**Access URL:** ``http://localhost:8000/mcp``

SSE Transport
~~~~~~~~~~~~~

For Server-Sent Events compatibility:

.. code-block:: bash

    gitlab-analyzer --transport sse --port 8001

**Options:**

- ``--port``: Port number (default: ``8001``)

GitLab Token Setup
------------------

Token Requirements
~~~~~~~~~~~~~~~~~~

Your GitLab token must have the following scopes:

- **api** - Required for all GitLab API access
- **read_repository** - Optional, for repository search features

Token Types
~~~~~~~~~~~

**Personal Access Token** (Recommended)
    For individual use:

    1. Go to GitLab → User Settings → Access Tokens
    2. Create token with ``api`` scope
    3. Set expiration date (recommended: 90 days)
    4. Copy the token value

**Project Access Token**
    For project-specific access:

    1. Go to Project → Settings → Access Tokens
    2. Create token with ``api`` and ``read_repository`` scopes
    3. Set role to ``Developer`` or higher

**Group Access Token**
    For multiple projects in a group:

    1. Go to Group → Settings → Access Tokens
    2. Create token with ``api`` scope
    3. Set role to ``Developer`` or higher

Client Configuration
--------------------

Claude Desktop Integration
~~~~~~~~~~~~~~~~~~~~~~~~~~~

Add to your ``claude_desktop_config.json``:

.. code-block:: json

    {
      "mcpServers": {
        "gitlab-pipeline-analyzer": {
          "command": "uv",
          "args": ["run", "gitlab-analyzer"],
          "env": {
            "GITLAB_URL": "https://gitlab.com",
            "GITLAB_TOKEN": "your-token-here"
          }
        }
      }
    }

**Alternative using pip installation:**

.. code-block:: json

    {
      "mcpServers": {
        "gitlab-pipeline-analyzer": {
          "command": "gitlab-analyzer",
          "env": {
            "GITLAB_URL": "https://gitlab.com",
            "GITLAB_TOKEN": "your-token-here"
          }
        }
      }
    }

HTTP Client Configuration
~~~~~~~~~~~~~~~~~~~~~~~~~

For HTTP transport, connect to: ``http://localhost:8000/mcp``

**Python FastMCP Client:**

.. code-block:: python

    from fastmcp import Client

    async def main():
        async with Client("http://localhost:8000/mcp") as client:
            tools = await client.list_tools()
            print(f"Available tools: {len(tools)}")

**cURL Testing:**

.. code-block:: bash

    curl -X POST http://localhost:8000/mcp \
         -H "Content-Type: application/json" \
         -d '{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}'

Configuration Files
-------------------

Environment File
~~~~~~~~~~~~~~~~

Create a ``.env`` file for environment variables:

.. code-block:: bash

    # GitLab Configuration
    GITLAB_URL=https://gitlab.company.com
    GITLAB_TOKEN=glpat-your-token-here

**Loading the environment file:**

.. code-block:: bash

    # Using source
    source .env
    gitlab-analyzer

    # Using env command
    env $(cat .env | xargs) gitlab-analyzer

**Security note:** Set proper file permissions:

.. code-block:: bash

    chmod 600 .env

Command Line Options
--------------------

Full command syntax:

.. code-block:: bash

    gitlab-analyzer [OPTIONS]

**Available Options:**

.. list-table::
   :header-rows: 1
   :widths: 20 15 65

   * - Option
     - Default
     - Description
   * - ``--transport``
     - ``stdio``
     - Transport protocol: ``stdio``, ``http``, or ``sse``
   * - ``--host``
     - ``127.0.0.1``
     - Host to bind (HTTP/SSE only)
   * - ``--port``
     - ``8000``
     - Port number (HTTP/SSE)
   * - ``--help``
     -
     - Show help message

**Examples:**

.. code-block:: bash

    # Default STDIO transport
    gitlab-analyzer

    # HTTP on custom port
    gitlab-analyzer --transport http --port 9000

    # HTTP accessible from network
    gitlab-analyzer --transport http --host 0.0.0.0 --port 8000

    # SSE transport
    gitlab-analyzer --transport sse --port 8001

Tool Configuration
------------------

Error Handling Options
~~~~~~~~~~~~~~~~~~~~~~

Many tools support response optimization modes:

**Response Modes:**

- ``minimal``: Essential error info only (~200 bytes per error)
- ``balanced``: Essential + limited context (~500 bytes per error) [Default]
- ``full``: Complete details including full traceback (~2000+ bytes per error)

**Example usage:**

.. code-block:: python

    result = await client.call_tool("get_file_errors", {
        "project_id": "123",
        "job_id": 456,
        "file_path": "src/main.py",
        "response_mode": "minimal"  # or "balanced" or "full"
    })

Path Filtering
~~~~~~~~~~~~~~

Default exclusions (automatically applied):

- ``/opt/hostedtoolcache/``
- ``/usr/local/lib/python``
- ``site-packages/``
- ``.venv/``
- ``venv/``

**Custom exclusions:**

.. code-block:: python

    result = await client.call_tool("get_file_errors", {
        "project_id": "123",
        "job_id": 456,
        "file_path": "src/main.py",
        "exclude_paths": [".mypy_cache", ".tox"],
        "exclude_file_patterns": ["*.pyc", "test_*"]
    })

Pagination Settings
~~~~~~~~~~~~~~~~~~~

For tools that return large datasets:

.. code-block:: python

    # Limit results
    result = await client.call_tool("get_files_with_errors", {
        "project_id": "123",
        "pipeline_id": 456,
        "max_files": 10
    })

    # Batch processing
    batch = await client.call_tool("get_error_batch", {
        "project_id": "123",
        "job_id": 789,
        "start_index": 0,
        "batch_size": 5
    })

Security Configuration
----------------------

Token Security
~~~~~~~~~~~~~~

**Best Practices:**

1. **Use project-specific tokens** when possible
2. **Set appropriate expiration dates** (90 days recommended)
3. **Rotate tokens regularly**
4. **Never commit tokens to version control**
5. **Use environment variables** or secure secret management

**File Permissions:**

.. code-block:: bash

    # Secure environment file
    chmod 600 .env

    # Verify permissions
    ls -la .env

Network Security
~~~~~~~~~~~~~~~~

**For HTTP transport in production:**

1. **Use reverse proxy** with HTTPS
2. **Configure firewall** for server port
3. **Implement authentication** at proxy level
4. **Monitor access logs**

**Example nginx configuration:**

.. code-block:: nginx

    server {
        listen 443 ssl;
        server_name gitlab-analyzer.company.com;

        location /mcp {
            proxy_pass http://127.0.0.1:8000/mcp;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
        }
    }

Troubleshooting Configuration
-----------------------------

Validation Steps
~~~~~~~~~~~~~~~~

**1. Test GitLab connectivity:**

.. code-block:: bash

    curl -I "$GITLAB_URL"

**2. Test token authentication:**

.. code-block:: bash

    curl -H "Authorization: Bearer $GITLAB_TOKEN" \
         "$GITLAB_URL/api/v4/user"

**3. Test server startup:**

.. code-block:: bash

    gitlab-analyzer --transport http &
    sleep 2
    curl http://localhost:8000/mcp

**4. Verify environment variables:**

.. code-block:: bash

    echo "URL: $GITLAB_URL"
    echo "Token set: $([ -n "$GITLAB_TOKEN" ] && echo "Yes" || echo "No")"

Common Issues
~~~~~~~~~~~~~

**Token authentication fails:**

.. code-block:: bash

    # Check token scopes
    curl -H "Authorization: Bearer $GITLAB_TOKEN" \
         "$GITLAB_URL/api/v4/personal_access_tokens"

**Port already in use:**

.. code-block:: bash

    # Find process using port
    lsof -i :8000

    # Use different port
    gitlab-analyzer --transport http --port 8001

**Environment variables not loaded:**

.. code-block:: bash

    # Check current environment
    env | grep GITLAB

    # Source .env file manually
    source .env
