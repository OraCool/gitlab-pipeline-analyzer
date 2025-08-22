Installation and Setup
======================

This guide covers installing and configuring the GitLab Pipeline Analyzer MCP Server.

Prerequisites
-------------

- Python 3.10 or higher
- GitLab personal access token with ``api`` scope
- Network access to your GitLab instance

Installation
------------

Install from Source
~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

    git clone https://github.com/OraCool/gitlab-pipeline-analyzer.git
    cd gitlab-pipeline-analyzer

    # Install dependencies
    uv sync --all-extras

    # Or with pip
    pip install -e .

Configuration
-------------

Environment Variables
~~~~~~~~~~~~~~~~~~~~~

The MCP server requires the following environment variables:

**Required Variables:**

.. list-table::
   :header-rows: 1
   :widths: 20 30 50

   * - Variable
     - Example
     - Description
   * - ``GITLAB_URL``
     - ``https://gitlab.com``
     - Your GitLab instance URL
   * - ``GITLAB_TOKEN``
     - ``glpat-xxxxxxxxxxxx``
     - GitLab personal access token with ``api`` scope

**Optional Variables:**

.. list-table::
   :header-rows: 1
   :widths: 20 30 50

   * - Variable
     - Default
     - Description
   * - ``MCP_HOST``
     - ``127.0.0.1``
     - Host for HTTP/SSE transport
   * - ``MCP_PORT``
     - ``8000``
     - Port for HTTP/SSE transport
   * - ``MCP_PATH``
     - ``/mcp``
     - HTTP endpoint path

GitLab Personal Access Token
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

1. Go to your GitLab instance → **User Settings** → **Access Tokens**
2. Create a new token with the following scopes:

   - ``api`` - Required for all GitLab API operations
   - ``read_repository`` - Required for repository search functionality

3. Copy the token and set it as ``GITLAB_TOKEN`` environment variable

.. warning::
   Keep your GitLab token secure and never commit it to version control.

Setting Environment Variables
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Linux/macOS:**

.. code-block:: bash

    export GITLAB_URL="https://gitlab.com"
    export GITLAB_TOKEN="your-token"

**Windows:**

.. code-block:: batch

    set GITLAB_URL=https://gitlab.com
    set GITLAB_TOKEN=your-token

**Using .env file:**

Create a ``.env`` file in the project directory:

.. code-block:: text

    GITLAB_URL=https://gitlab.com
    GITLAB_TOKEN=your-token

    # Optional transport configuration
    MCP_HOST=127.0.0.1
    MCP_PORT=8000
    MCP_PATH=/mcp

Transport Protocols
-------------------

The MCP server supports three transport protocols provided by FastMCP:

STDIO Transport (Default)
~~~~~~~~~~~~~~~~~~~~~~~~~

Best for local development and Claude Desktop integration:

.. code-block:: bash

    gitlab-analyzer
    # or explicitly
    gitlab-analyzer --transport stdio

**Use Cases:**
- Local development and testing
- Claude Desktop integration
- Command-line tools and scripts

HTTP Transport
~~~~~~~~~~~~~~

For remote access and web integration:

.. code-block:: bash

    gitlab-analyzer --transport http --host 0.0.0.0 --port 8000

**Use Cases:**
- Remote server deployments
- Web application integration
- Multiple client access

**Endpoint:** ``http://your-server:8000/mcp``

SSE Transport
~~~~~~~~~~~~~

For Server-Sent Events compatibility:

.. code-block:: bash

    gitlab-analyzer --transport sse --host 0.0.0.0 --port 8001

**Use Cases:**
- Real-time updates
- Browser-based clients
- Event streaming

**Endpoint:** ``http://your-server:8001``

Running the Server
------------------

Local Development
~~~~~~~~~~~~~~~~~

.. code-block:: bash

    # Install dependencies
    uv sync --all-extras

    # Set environment variables
    export GITLAB_URL="https://gitlab.com"
    export GITLAB_TOKEN="your-token"

    # Run server with STDIO transport
    uv run gitlab-analyzer

With Environment File
~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

    # Create .env file with your configuration
    echo "GITLAB_URL=https://gitlab.com" > .env
    echo "GITLAB_TOKEN=your-token" >> .env

    # Run server (reads .env automatically)
    uv run gitlab-analyzer

HTTP Server
~~~~~~~~~~~

.. code-block:: bash

    # Run HTTP server on specific host/port
    uv run gitlab-analyzer --transport http --host 0.0.0.0 --port 8000

    # Or use dedicated HTTP server script
    uv run gitlab-analyzer-http

SSE Server
~~~~~~~~~~

.. code-block:: bash

    # Run SSE server
    uv run gitlab-analyzer --transport sse --host 0.0.0.0 --port 8001

    # Or use dedicated SSE server script
    uv run gitlab-analyzer-sse

Verification
------------

Test Installation
~~~~~~~~~~~~~~~~~

Verify the installation works:

.. code-block:: bash

    # Check if the server starts without errors
    uv run gitlab-analyzer --help

Test MCP Server
~~~~~~~~~~~~~~~

For HTTP transport, test the endpoint:

.. code-block:: bash

    # Test HTTP endpoint (if running HTTP transport)
    curl http://localhost:8000/mcp

For STDIO transport, use a FastMCP client:

.. code-block:: python

    import asyncio
    from fastmcp import Client

    async def test_mcp():
        # Test with subprocess (STDIO transport)
        proc = await asyncio.create_subprocess_exec(
            "uv", "run", "gitlab-analyzer",
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

        # Send MCP initialization
        init_msg = '{"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}}\n'
        proc.stdin.write(init_msg.encode())
        await proc.stdin.drain()

        # Read response
        response = await proc.stdout.readline()
        print(f"Server response: {response.decode().strip()}")

        proc.terminate()
        await proc.wait()

    asyncio.run(test_mcp())

Troubleshooting
---------------

Common Issues
~~~~~~~~~~~~~

**Token Authentication Failed:**

.. code-block:: text

    Error: GitLab authentication failed. Check your GITLAB_TOKEN.

- Verify your token has ``api`` scope
- Check token hasn't expired
- Ensure ``GITLAB_URL`` is correct

**Connection Refused:**

.. code-block:: text

    Error: Connection refused to GitLab instance

- Check network connectivity to GitLab instance
- Verify GitLab URL is accessible
- Check firewall settings

**Module Not Found:**

.. code-block:: text

    ModuleNotFoundError: No module named 'gitlab_analyzer'

- Ensure proper installation: ``uv sync --all-extras``
- Check if you're in the project directory
- Verify Python environment

Debug Mode
~~~~~~~~~~

For troubleshooting, you can run the server with verbose output by checking the FastMCP logs.

Next Steps
----------

- Review :doc:`mcp_tools` for complete tool overview
- Check :doc:`tool_reference` for detailed tool documentation
- See :doc:`examples` for usage examples
- Read :doc:`configuration` for advanced configuration options
