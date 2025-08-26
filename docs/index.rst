GitLab Pipeline Analyzer MCP Server Documentation
=================================================

.. toctree::
   :maxdepth: 2
   :caption: Contents:

   installation
   examples
   configuration
   troubleshooting

Overview
--------

The **GitLab Pipeline Analyzer MCP Server** is a comprehensive `Model Context Protocol (MCP) <https://modelcontextprotocol.io>`_ server that provides AI assistants with powerful tools for analyzing GitLab CI/CD pipeline failures. Built using `FastMCP <https://github.com/jlowin/fastmcp>`_, this server exposes 6 streamlined tools following DRY and KISS principles for pipeline analysis, repository search, and cache management.

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

The MCP server follows a streamlined architecture with 6 focused tools:

1. **Pipeline Analysis** - Complete pipeline failure analysis with intelligent parsing
2. **Repository Search** - Code and commit search functionality
3. **Cache Management** - Cache operations and health monitoring

All detailed data is accessed via resource URIs following DRY and KISS principles.

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
            result = await client.call_tool("comprehensive_pipeline_analysis", {
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

Continue to the :doc:`installation` guide to set up the MCP server, or check the ``streamlined_tools.md`` file for complete tool documentation.
