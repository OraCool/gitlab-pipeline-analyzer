MCP Tools Overview
==================

The GitLab Pipeline Analyzer MCP Server provides **21 comprehensive tools** organized into six functional categories. Each tool is implemented as a FastMCP ``@mcp.tool`` decorator and provides structured responses optimized for AI analysis.

Tool Categories
---------------

.. contents::
   :local:
   :depth: 1

Analysis Tools
--------------

Core pipeline and job failure analysis tools for understanding CI/CD failures.

🔍 analyze_failed_pipeline
~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Complete pipeline failure analysis - your go-to tool for understanding why CI/CD pipelines fail.**

.. code-block:: python

    @mcp.tool
    async def analyze_failed_pipeline(
        project_id: str | int,
        pipeline_id: int
    ) -> dict[str, Any]:

**When to Use:**
- Pipeline shows "failed" status and you need to understand all failure points
- User asks "what went wrong with pipeline X?"
- Need comprehensive error overview across all failed jobs

**What You Get:**
- Pipeline status and metadata
- List of all failed jobs with extracted errors/warnings
- Categorized error types (build, test, lint, etc.)
- Summary statistics for quick assessment
- Detailed errors with full context and traceback information

**Response Structure:**

.. code-block:: javascript

    {
      "project_id": "123",
      "pipeline_id": 456,
      "pipeline_status": {"id": 456, "status": "failed"},
      "failed_jobs_count": 3,
      "job_analyses": ["job analysis objects"],
      "detailed_errors": ["error objects"],
      "summary": {
        "total_errors": 15,
        "total_warnings": 8,
        "jobs_with_errors": 3,
        "error_categories": {"test_failure": 12, "import_error": 3}
      },
      "parser_analysis": {
        "usage_summary": {"pytest": {"count": 2}, "generic": {"count": 1}},
        "parser_types_used": ["pytest", "generic"]
      }
    }

🎯 analyze_single_job
~~~~~~~~~~~~~~~~~~~~~

**Deep dive into single job failure with extracted errors and warnings.**

.. code-block:: python

    @mcp.tool
    async def analyze_single_job(
        project_id: str | int,
        job_id: int
    ) -> dict[str, Any]:

**When to Use:**
- analyze_failed_pipeline identified a specific problematic job
- Need focused analysis of one particular job failure
- Want to drill down from pipeline overview to specific job details

**What You Get:**
- Job metadata (name, status, stage, duration)
- Extracted errors and warnings with context
- Parser type indication (pytest/generic)
- Structured error categorization

Info Tools
----------

Pipeline metadata and job information tools for understanding pipeline structure.

📋 get_pipeline_jobs
~~~~~~~~~~~~~~~~~~~~

**Get complete job list for pipeline with status and metadata.**

.. code-block:: python

    @mcp.tool
    async def get_pipeline_jobs(
        project_id: str | int,
        pipeline_id: int
    ) -> dict[str, Any]:

**What You Get:**
- Complete list of all jobs with names, status, and stage information
- Job counts and pipeline structure overview
- Basic metadata for each job (ID, duration, etc.)

📊 get_pipeline_info
~~~~~~~~~~~~~~~~~~~~

**Comprehensive pipeline metadata with MR branch resolution.**

.. code-block:: python

    @mcp.tool
    async def get_pipeline_info(
        project_id: str | int,
        pipeline_id: int
    ) -> dict[str, Any]:

**What You Get:**
- Complete pipeline information and metadata
- Pipeline status, timing, and execution details
- Git reference information (branch, commit, etc.)
- Resolved branch information (actual source branch for MR pipelines)
- Pipeline type detection (regular branch vs merge request)

📈 get_pipeline_status
~~~~~~~~~~~~~~~~~~~~~~

**Basic pipeline status and timing information for quick assessment.**

.. code-block:: python

    @mcp.tool
    async def get_pipeline_status(
        project_id: str | int,
        pipeline_id: int
    ) -> dict[str, Any]:

🚨 get_failed_jobs
~~~~~~~~~~~~~~~~~~

**Filtered list of only failed jobs for focused failure analysis.**

.. code-block:: python

    @mcp.tool
    async def get_failed_jobs(
        project_id: str | int,
        pipeline_id: int
    ) -> dict[str, Any]:

Log Tools
---------

Raw log processing and error extraction tools.

📝 get_job_trace
~~~~~~~~~~~~~~~~

**Raw job trace logs with ANSI formatting intact.**

.. code-block:: python

    @mcp.tool
    async def get_job_trace(
        project_id: str | int,
        job_id: int
    ) -> dict[str, Any]:

🧹 get_cleaned_job_trace
~~~~~~~~~~~~~~~~~~~~~~~~

**Clean, readable job traces without ANSI formatting for detailed analysis.**

.. code-block:: python

    @mcp.tool
    async def get_cleaned_job_trace(
        project_id: str | int,
        job_id: int
    ) -> dict[str, Any]:

**What You Get:**
- Complete job trace with ANSI codes removed
- Character counts and cleaning statistics
- Human-readable format suitable for AI analysis

🔧 extract_log_errors
~~~~~~~~~~~~~~~~~~~~~

**Extract errors and warnings from raw log text using advanced pattern matching.**

.. code-block:: python

    @mcp.tool
    async def extract_log_errors(
        log_text: str
    ) -> dict[str, Any]:

**What You Get:**
- Structured list of errors and warnings with context
- Error categorization (build, test, syntax, import, etc.)
- Line numbers and surrounding context for each issue
- Summary statistics (error count, warning count)

Pytest Tools
------------

Specialized pytest test failure analysis tools.

🧪 analyze_pytest_job_complete
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Complete pytest analysis combining detailed failures, summary, and statistics.**

.. code-block:: python

    @mcp.tool
    async def analyze_pytest_job_complete(
        project_id: str | int,
        job_id: int
    ) -> dict[str, Any]:

**When to Use:**
- Job name contains "test", "pytest", or shows test-related failures
- Need comprehensive test failure analysis in one call
- User asks "what tests failed and why?"

**What You Get:**
- Detailed failures: Full tracebacks, exception details, file/line info
- Short summary: Concise failure list with test names and brief errors
- Statistics: Test counts (total, passed, failed, skipped) and timing

🔬 extract_pytest_detailed_failures
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Extract comprehensive test failure information with full tracebacks.**

.. code-block:: python

    @mcp.tool
    async def extract_pytest_detailed_failures(
        project_id: str | int,
        job_id: int
    ) -> dict[str, Any]:

**What You Get:**
- Detailed failure objects with complete traceback chains
- Exception types, messages, and platform information
- File paths, line numbers, and code context
- Test parameters and function details

📄 extract_pytest_short_summary
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Get concise test failure summary for rapid assessment.**

.. code-block:: python

    @mcp.tool
    async def extract_pytest_short_summary(
        project_id: str | int,
        job_id: int
    ) -> dict[str, Any]:

📊 extract_pytest_statistics
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Get test execution statistics and performance data.**

.. code-block:: python

    @mcp.tool
    async def extract_pytest_statistics(
        project_id: str | int,
        job_id: int
    ) -> dict[str, Any]:

**What You Get:**
- Test counts (total, passed, failed, skipped, errors)
- Execution duration and timing information
- Pass rate and failure rate calculations
- Performance metrics for test suite analysis

Pagination Tools
----------------

Large dataset management and file-based error grouping tools.

📁 group_errors_by_file
~~~~~~~~~~~~~~~~~~~~~~~

**Group errors by file path for systematic fixing approach.**

.. code-block:: python

    @mcp.tool
    async def group_errors_by_file(
        project_id: str | int,
        pipeline_id: int | None = None,
        job_id: int | None = None,
        max_files: int = 10,
        max_errors_per_file: int = 5,
        include_traceback: bool = True,
        exclude_paths: list[str] | None = None,
        exclude_file_patterns: list[str] | None = None
    ) -> dict[str, Any]:

**When to Use:**
- Pipeline has errors across multiple files
- Want to fix all errors in a file at once
- Need to prioritize files with most errors
- Want to avoid processing same file multiple times

**Parameters:**
- ``project_id``: GitLab project ID or path
- ``pipeline_id``: Optional pipeline ID (required if job_id not provided)
- ``job_id``: Optional specific job ID (overrides pipeline_id)
- ``max_files``: Maximum number of files to return (default: 10)
- ``max_errors_per_file``: Maximum errors per file (default: 5)
- ``include_traceback``: Include traceback information (default: True)
- ``exclude_paths``: Path patterns to exclude from traceback
- ``exclude_file_patterns``: File path patterns to exclude from results

📂 get_files_with_errors
~~~~~~~~~~~~~~~~~~~~~~~~

**Get list of files that have errors without the error details.**

.. code-block:: python

    @mcp.tool
    async def get_files_with_errors(
        project_id: str | int,
        pipeline_id: int | None = None,
        job_id: int | None = None,
        max_files: int = 20,
        exclude_file_patterns: list[str] | None = None,
        response_mode: str = "balanced"
    ) -> dict[str, Any]:

**What You Get:**
- List of files with error counts
- File type categorization (test, source, unknown)
- Summary statistics
- No actual error details (lightweight response)

📄 get_file_errors
~~~~~~~~~~~~~~~~~~

**Get all errors for a specific file from a job.**

.. code-block:: python

    @mcp.tool
    async def get_file_errors(
        project_id: str | int,
        job_id: int,
        file_path: str,
        max_errors: int = 10,
        include_traceback: bool = True,
        exclude_paths: list[str] | None = None,
        job_name: str = "",
        job_stage: str = "",
        response_mode: str = "balanced"
    ) -> dict[str, Any]:

📦 get_error_batch
~~~~~~~~~~~~~~~~~~

**Get a specific batch of errors from a job to handle large error lists.**

.. code-block:: python

    @mcp.tool
    async def get_error_batch(
        project_id: str | int,
        job_id: int,
        start_index: int = 0,
        batch_size: int = 3,
        include_traceback: bool = True,
        exclude_paths: list[str] | None = None
    ) -> dict[str, Any]:

📈 analyze_failed_pipeline_summary
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Get pipeline failure overview with limited error details to avoid truncation.**

.. code-block:: python

    @mcp.tool
    async def analyze_failed_pipeline_summary(
        project_id: str | int,
        pipeline_id: int
    ) -> dict[str, Any]:

🎯 analyze_single_job_limited
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Analyze single job with response size controls to prevent truncation.**

.. code-block:: python

    @mcp.tool
    async def analyze_single_job_limited(
        project_id: str | int,
        job_id: int,
        max_errors: int = 5,
        include_traceback: bool = False
    ) -> dict[str, Any]:

Search Tools
------------

Repository code and commit search functionality.

🔍 search_repository_code
~~~~~~~~~~~~~~~~~~~~~~~~~

**Search for keywords in GitLab repository code files.**

.. code-block:: python

    @mcp.tool
    async def search_repository_code(
        project_id: str | int,
        search_keywords: str,
        branch: str | None = None,
        filename_filter: str | None = None,
        path_filter: str | None = None,
        extension_filter: str | None = None,
        max_results: int = 20,
        output_format: str = "text"
    ) -> str:

**When to Use:**
- Find code implementations containing specific keywords
- Locate configuration files or specific patterns
- Search for function names, class names, or variables
- Find code examples or usage patterns

**Search Features:**
- Full-text search in code files
- Branch-specific searching
- File type filtering (by extension, filename, path)
- Wildcard support in filters
- Line number and context for each match

**Parameters:**
- ``search_keywords``: Keywords to search for in code
- ``branch``: Specific branch to search (optional)
- ``filename_filter``: Filter by filename pattern (supports wildcards like ``*.py``)
- ``path_filter``: Filter by file path pattern (e.g., src/*, models/*)
- ``extension_filter``: Filter by file extension (e.g., 'py', 'js', 'ts')
- ``max_results``: Maximum number of results to return (default: 20)

**Examples:**

.. code-block:: python

    # Search for async functions in Python files
    await client.call_tool("search_repository_code", {
        "project_id": "123",
        "search_keywords": "async def process",
        "extension_filter": "py"
    })

    # Search for imports in specific directory
    await client.call_tool("search_repository_code", {
        "project_id": "123",
        "search_keywords": "import pandas",
        "path_filter": "src/*"
    })

📝 search_repository_commits
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Search for keywords in GitLab repository commit messages.**

.. code-block:: python

    @mcp.tool
    async def search_repository_commits(
        project_id: str | int,
        search_keywords: str,
        branch: str | None = None,
        max_results: int = 20,
        output_format: str = "text"
    ) -> str:

**When to Use:**
- Find commits related to specific features or bug fixes
- Locate commits by author, ticket number, or description
- Track changes related to specific functionality
- Find commits that mention specific issues or PRs

**Examples:**

.. code-block:: python

    # Find bug fix commits
    await client.call_tool("search_repository_commits", {
        "project_id": "123",
        "search_keywords": "fix bug"
    })

    # Find commits referencing a ticket
    await client.call_tool("search_repository_commits", {
        "project_id": "123",
        "search_keywords": "JIRA-123"
    })

Response Modes and Optimization
-------------------------------

Many tools support response optimization modes to control output size and detail level:

Response Modes
~~~~~~~~~~~~~~

- **minimal** - Essential information only, smallest response size
- **balanced** - Good balance of detail and size (default for most tools)
- **fixing** - Optimized for error fixing with guidance and context
- **full** - Complete information, largest response size

Traceback Filtering
~~~~~~~~~~~~~~~~~~~

Advanced filtering options for managing large traceback responses:

**Parameters:**
- ``include_traceback`` (bool, default: True): Include/exclude all traceback information
- ``exclude_paths`` (list[str], optional): Filter out specific path patterns from traceback

**Default Filtering:**
When ``exclude_paths`` is not specified, tools automatically apply ``DEFAULT_EXCLUDE_PATHS``:

.. code-block:: python

    DEFAULT_EXCLUDE_PATHS = [
        ".venv",           # Virtual environment packages
        "site-packages",   # Python package installations
        ".local",          # User-local Python installations
        "/builds/",        # CI/CD build directories
        "/root/.local",    # Root user local packages
        "/usr/lib/python", # System Python libraries
        "/opt/python",     # Optional Python installations
        "/__pycache__/",   # Python bytecode cache
        ".cache",          # Various cache directories
        "/tmp/",           # Temporary files
    ]

**Usage Examples:**

.. code-block:: python

    # Use default filtering (recommended)
    await client.call_tool("get_file_errors", {
        "project_id": "83",
        "job_id": 76474190,
        "file_path": "src/my_module.py"
    })

    # Disable traceback for clean summaries
    await client.call_tool("get_file_errors", {
        "project_id": "83",
        "job_id": 76474190,
        "file_path": "src/my_module.py",
        "include_traceback": False
    })

    # Custom filtering
    await client.call_tool("get_file_errors", {
        "project_id": "83",
        "job_id": 76474190,
        "file_path": "src/my_module.py",
        "exclude_paths": [".venv", "site-packages"]
    })

    # Get complete traceback (no filtering)
    await client.call_tool("get_file_errors", {
        "project_id": "83",
        "job_id": 76474190,
        "file_path": "src/my_module.py",
        "exclude_paths": []  # Empty list = no filtering
    })

Tool Usage Patterns
-------------------

Common Workflows
~~~~~~~~~~~~~~~~

**1. Pipeline Investigation Workflow:**

.. code-block:: python

    # Start with overview
    pipeline_summary = await client.call_tool("analyze_failed_pipeline_summary", {
        "project_id": "123", "pipeline_id": 456
    })

    # Get detailed analysis
    full_analysis = await client.call_tool("analyze_failed_pipeline", {
        "project_id": "123", "pipeline_id": 456
    })

    # Focus on specific job
    job_analysis = await client.call_tool("analyze_single_job", {
        "project_id": "123", "job_id": 789
    })

**2. File-Based Error Fixing Workflow:**

.. code-block:: python

    # Get files with errors
    files_with_errors = await client.call_tool("get_files_with_errors", {
        "project_id": "123", "pipeline_id": 456
    })

    # Group errors by file for systematic fixing
    grouped_errors = await client.call_tool("group_errors_by_file", {
        "project_id": "123", "pipeline_id": 456,
        "max_files": 5
    })

    # Get detailed errors for specific file
    file_errors = await client.call_tool("get_file_errors", {
        "project_id": "123", "job_id": 789,
        "file_path": "src/problematic_file.py"
    })

**3. Test Failure Analysis Workflow:**

.. code-block:: python

    # Complete pytest analysis
    pytest_analysis = await client.call_tool("analyze_pytest_job_complete", {
        "project_id": "123", "job_id": 789
    })

    # Get detailed failures if needed
    detailed_failures = await client.call_tool("extract_pytest_detailed_failures", {
        "project_id": "123", "job_id": 789
    })

    # Get test statistics
    test_stats = await client.call_tool("extract_pytest_statistics", {
        "project_id": "123", "job_id": 789
    })

Error Handling
~~~~~~~~~~~~~~

All tools implement consistent error handling and return structured error responses:

.. code-block:: json

    {
      "error": "Failed to analyze pipeline: HTTP 404 - Pipeline not found",
      "project_id": "123",
      "pipeline_id": 456,
      "mcp_info": {
        "name": "GitLab Pipeline Analyzer",
        "version": "0.2.6",
        "tool_used": "analyze_failed_pipeline",
        "error": true
      }
    }

Next Steps
----------

- See :doc:`tool_reference` for complete parameter and response documentation
- Check :doc:`examples` for practical usage examples
- Review :doc:`configuration` for advanced setup options
