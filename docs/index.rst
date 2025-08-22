GitLab Pipeline Analyzer MCP Server Documentation
=================================================

.. toctree::
   :maxdepth: 2
   :caption: Contents:

   installation
   mcp_tools
   tool_reference
   examples
   configuration
   deployment
   troubleshooting

Overview
--------

The **GitLab Pipeline Analyzer MCP Server** is a comprehensive `Model Context Protocol (MCP) <https://modelcontextprotocol.io>`_ server that provides AI assistants with powerful tools for analyzing GitLab CI/CD pipeline failures. Built using `FastMCP <https://github.com/jlowin/fastmcp>`_, this server exposes 21 specialized tools for extracting, parsing, and analyzing pipeline errors, job traces, and repository information.

Key Features
------------

🔍 **Comprehensive Pipeline Analysis**
   - Analyze complete failed pipelines with detailed error extraction
   - Deep-dive into individual job failures with structured error categorization
   - Support for both pytest-specific and generic log parsing

📊 **Advanced Error Management**
   - Intelligent error filtering and traceback management
   - File-based error grouping for systematic debugging
   - Pagination and batching for large error sets

🧪 **Pytest Integration**
   - Specialized pytest failure analysis with detailed tracebacks
   - Test statistics and execution metrics
   - Short summaries and detailed failure breakdowns

🔍 **Repository Search**
   - Search repository code with advanced filtering (file extensions, paths)
   - Search commit messages with branch-specific filtering
   - Contextual code snippets with line numbers

🌐 **Multiple Transport Protocols**
   - STDIO transport for local development and Claude Desktop integration
   - HTTP transport for remote deployments and web applications
   - SSE (Server-Sent Events) transport for compatibility

🛡️ **Robust Error Handling**
   - Automatic parser detection (pytest vs generic logs)
   - Response optimization modes (minimal, balanced, fixing, full)
   - Comprehensive error filtering and noise reduction

Architecture
------------

The MCP server is organized into six main tool categories:

1. **Analysis Tools** - Core pipeline and job failure analysis
2. **Info Tools** - Pipeline metadata and job information
3. **Log Tools** - Raw log processing and error extraction
4. **Pytest Tools** - Specialized pytest test failure analysis
5. **Pagination Tools** - Large dataset management and file-based error grouping
6. **Search Tools** - Repository code and commit search functionality

Quick Start
-----------

Installation::

    pip install gitlab-pipeline-analyzer

Configuration::

    export GITLAB_URL="https://gitlab.com"
    export GITLAB_TOKEN="your-access-token"

Running the server::

    # STDIO transport (default)
    gitlab-analyzer

    # HTTP transport
    gitlab-analyzer --transport http --port 8000

    # SSE transport
    gitlab-analyzer --transport sse --port 8001

Basic usage with FastMCP client:

.. code-block:: python

    from fastmcp import Client

    async def analyze_pipeline():
        async with Client("http://localhost:8000/mcp") as client:
            # Analyze a failed pipeline
            result = await client.call_tool("analyze_failed_pipeline", {
                "project_id": "123",
                "pipeline_id": 456
            })
            print(result)

Supported GitLab Instances
---------------------------

- **GitLab.com** - Public GitLab instance
- **GitLab Enterprise** - Self-hosted GitLab instances
- **GitLab Cloud** - GitLab-managed cloud instances

Requirements
------------

- Python 3.10+
- GitLab personal access token with ``api`` scope
- Network access to your GitLab instance

Getting Started
---------------

Continue to the :doc:`installation` guide to set up the MCP server, or jump to :doc:`mcp_tools` for a complete overview of available tools.
