GitLab Pipeline Analyzer MCP Server Documentation
=================================================

.. toctree::
   :maxdepth: 2
   :caption: Contents:

   installation
   environment_variables
   tools_and_resources
   prompts
   examples
   configuration
   troubleshooting

Overview
--------

The **GitLab Pipeline Analyzer MCP Server** is a comprehensive `Model Context Protocol (MCP) <https://modelcontextprotocol.io>`_ server that provides AI assistants with powerful tools for analyzing GitLab CI/CD pipeline failures. Built using `FastMCP <https://github.com/jlowin/fastmcp>`_, this server exposes 14 streamlined tools and 13+ intelligent prompts following DRY and KISS principles for pipeline analysis, repository search, cache management, and guided workflows.

**Version 0.11.0** introduces AI-powered root cause analysis with intelligent error pattern detection and dynamic error grouping.

Key Features
------------

🧠 **NEW in v0.11.0: AI-Powered Root Cause Analysis**
   - Intelligent error pattern detection with dynamic learning capabilities
   - Automated error grouping and classification with confidence scoring
   - Root cause analysis results available through MCP resources with advanced filtering
   - Impact scoring to prioritize most critical issues first
   - Pattern-based error deduplication to reduce noise and improve clarity

🚀 **NEW in v0.8.0: Merge Request Integration**
   - Comprehensive merge request information extraction and display
   - Jira ticket detection and extraction from MR titles and descriptions
   - Smart filtering: MR data only included for actual merge request pipelines
   - Enhanced pipeline context awareness with automatic branch resolution

� **Intelligent Prompts & Workflows**
   - 13+ specialized prompts across 5 categories (Investigation, Performance, Educational, Advanced, Original)
   - Role-based investigation wizards with progressive complexity
   - Pipeline comparison and regression analysis capabilities
   - Performance optimization and resource efficiency guidance
   - Educational pathways and team mentoring support

�🔍 **Comprehensive Pipeline Analysis**
   - Analyze complete failed pipelines with detailed error extraction and MR context
   - Deep-dive into individual job failures with structured error categorization
   - Support for both pytest-specific and generic log parsing
   - Conditional information display based on pipeline type (branch vs merge request)

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

🛡️ **Robust Configuration & Management**
   - Comprehensive environment variable configuration for all aspects
   - Database path configuration (``MCP_DATABASE_PATH``)
   - Auto-cleanup configuration (interval, age, enable/disable)
   - Server configuration (transport, host, port, path)
   - GitLab connectivity configuration (URL, token)
   - Multiple deployment scenarios (development, production, testing, Docker)

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

The MCP server follows a streamlined architecture with 14 focused tools and 13+ intelligent prompts:

**Core Tools:**
1. **Pipeline Analysis** - ``failed_pipeline_analysis`` with intelligent parsing
2. **Repository Search** - ``search_repository_code``, ``search_repository_commits``
3. **Resource Access** - ``get_mcp_resource`` with comprehensive URI patterns
4. **Job Trace Access** - ``get_clean_job_trace`` for direct trace retrieval
5. **Cache Management** - ``cache_stats``, ``cache_health``, ``clear_cache``, ``clear_pipeline_cache``, ``clear_job_cache``

**Comprehensive Resources:**
- **Pipeline Resources** - Complete pipeline and job metadata
- **File Resources** - File-specific error analysis with pagination
- **Error Resources** - Structured error data with multiple access patterns
- **Analysis Resources** - Deep analysis summaries with configurable detail modes

**Intelligent Prompts:**
- **Investigation Workflows** - Multi-step guided analysis and debugging
- **Performance Optimization** - Pipeline efficiency and resource optimization
- **Educational & Learning** - Skill development and knowledge sharing
- **Advanced Analytics** - Complex analysis and comparison workflows

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
--------------------------

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
