MCP Tools & Resources Reference
===============================

This comprehensive reference documents all available tools and resources in the GitLab Pipeline Analyzer MCP Server **version 0.9.0** with enhanced job analysis tools and improved error handling.

.. contents::
   :local:
   :depth: 3

Overview
--------

The GitLab Pipeline Analyzer MCP Server provides **14 essential tools** and **comprehensive MCP resources** following DRY and KISS principles. Each tool serves a specific purpose in the pipeline analysis workflow, while resources provide efficient access to cached data.

**NEW in v0.9.0**: Enhanced job analysis tools and pipeline validation checks for improved error handling.

🔧 MCP Tools (14 Essential Tools)
---------------------------------

1. Pipeline Analysis Tools
~~~~~~~~~~~~~~~~~~~~~~~~~~

**failed_pipeline_analysis**
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Purpose**: Efficient analysis focusing only on failed jobs with comprehensive merge request context

**When to use**: Pipeline shows "failed" status and you need comprehensive analysis with MR context

**Key Features**:
- **NEW in v0.8.0**: Merge request information extraction and display
- **NEW in v0.8.0**: Jira ticket detection and extraction from MR titles/descriptions
- **NEW in v0.8.0**: Smart filtering - MR data only included for actual MR pipelines
- **NEW in v0.8.0**: Advanced error deduplication between pytest and generic parsers
- Auto-detects pytest vs generic jobs
- Intelligent parser selection with hybrid parsing approach
- Real branch resolution for MR pipelines
- Complete error extraction with context
- Automatic caching for performance
- Stores results in database for resource access

**Parameters**:
- ``project_id`` (str|int): The GitLab project ID or path
- ``pipeline_id`` (int): The ID of the GitLab pipeline to analyze
- ``store_in_db`` (bool, default=True): Whether to store results in database
- ``exclude_file_patterns`` (list[str], optional): Additional file patterns to exclude
- ``disable_file_filtering`` (bool, default=False): Disable all file filtering

**NEW in v0.8.0 - Enhanced Response**:

.. code-block:: json

    {
        "pipeline_type": "merge_request",
        "merge_request": {
            "title": "PROJ-456: Fix authentication flow",
            "description": "Resolves auth issues in PROJ-456",
            "jira_tickets": ["PROJ-456"],
            "source_branch": "feature/auth-fix",
            "target_branch": "main",
            "author": "john.doe"
        },
        "analysis_summary": {
            "total_errors": 34,
            "failed_jobs": 2
        }
    }

**Example**:

.. code-block:: python

    result = await client.call_tool("failed_pipeline_analysis", {
        "project_id": "12345",
        "pipeline_id": 67890,
        "exclude_file_patterns": ["migrations/", "vendor/"]
    })

    # For MR pipelines: includes merge_request data
    # For branch pipelines: excludes merge_request data

.. note::
   **Error Deduplication**: The failed_pipeline_analysis tool uses sophisticated deduplication
   to prevent the same error from being reported multiple times when combining pytest parser
   results with generic log parser fallback. See ``ERROR_DEDUPLICATION.md`` for detailed
   technical documentation.

2. Repository Search Tools
~~~~~~~~~~~~~~~~~~~~~~~~~~

**search_repository_code**
^^^^^^^^^^^^^^^^^^^^^^^^^^

**Purpose**: Search for keywords in repository code files

**When to use**: Find code implementations, configuration files, or specific patterns

**Key Features**:
- Full-text search in code files
- Branch-specific searching
- File type filtering (extension, filename, path)
- Wildcard support in filters
- Line numbers and context for matches

**Parameters**:
- ``project_id`` (str|int): The GitLab project ID or path
- ``search_keywords`` (str): Keywords to search for in code
- ``branch`` (str, optional): Specific branch to search
- ``filename_filter`` (str, optional): Filter by filename pattern (supports wildcards)
- ``path_filter`` (str, optional): Filter by file path pattern
- ``extension_filter`` (str, optional): Filter by file extension
- ``max_results`` (int, default=20): Maximum number of results
- ``output_format`` (str, default="text"): Output format ("text" or "json")

**Examples**:

.. code-block:: python

    # Search for async functions in Python files
    result = await client.call_tool("search_repository_code", {
        "project_id": "12345",
        "search_keywords": "async def process",
        "extension_filter": "py"
    })

    # Search in specific directory
    result = await client.call_tool("search_repository_code", {
        "project_id": "12345",
        "search_keywords": "class UserModel",
        "path_filter": "models/*"
    })

**search_repository_commits**
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Purpose**: Search for keywords in repository commit messages

**When to use**: Find commits related to specific features, bug fixes, or issues

**Key Features**:
- Full-text search in commit messages
- Branch-specific searching
- Author and date information
- Commit SHA and web links

**Parameters**:
- ``project_id`` (str|int): The GitLab project ID or path
- ``search_keywords`` (str): Keywords to search for in commit messages
- ``branch`` (str, optional): Specific branch to search
- ``max_results`` (int, default=20): Maximum number of results
- ``output_format`` (str, default="text"): Output format ("text" or "json")

**Examples**:

.. code-block:: python

    # Find bug fix commits
    result = await client.call_tool("search_repository_commits", {
        "project_id": "12345",
        "search_keywords": "fix bug"
    })

    # Search for specific ticket references
    result = await client.call_tool("search_repository_commits", {
        "project_id": "12345",
        "search_keywords": "JIRA-123",
        "output_format": "json"
    })

3. Resource Access Tools
~~~~~~~~~~~~~~~~~~~~~~~~

**get_mcp_resource**
^^^^^^^^^^^^^^^^^^^^

**Purpose**: Get data from MCP resource URI without re-running analysis

**When to use**: Access previously analyzed pipeline data efficiently

**Key Features**:
- Uses cached data for fast response
- Includes navigation links to related resources
- Provides summary statistics and metadata
- Filters data based on resource type

**Parameters**:
- ``resource_uri`` (str): The MCP resource URI

**Supported Resource Patterns**:

.. code-block:: text

    # Pipeline Resources
    gl://pipeline/{project_id}/{pipeline_id}

    # Job Resources
    gl://jobs/{project_id}/pipeline/{pipeline_id}[/failed|/success|/all]
    gl://job/{project_id}/{pipeline_id}/{job_id}

    # File Resources
    gl://files/{project_id}/pipeline/{pipeline_id}[/page/{page}/limit/{limit}]
    gl://files/{project_id}/{job_id}[/page/{page}/limit/{limit}]
    gl://file/{project_id}/{job_id}/{file_path}
    gl://file/{project_id}/{job_id}/{file_path}/trace?mode={mode}&include_trace={trace}

    # Error Resources
    gl://error/{project_id}/{job_id}[?mode={mode}]
    gl://error/{project_id}/{job_id}/{error_id}
    gl://errors/{project_id}/{job_id}
    gl://errors/{project_id}/{job_id}/{file_path}
    gl://errors/{project_id}/pipeline/{pipeline_id}

    # Analysis Resources
    gl://analysis/{project_id}[?mode={mode}]
    gl://analysis/{project_id}/pipeline/{pipeline_id}[?mode={mode}]
    gl://analysis/{project_id}/job/{job_id}[?mode={mode}]

**Examples**:

.. code-block:: python

    # Get failed jobs from pipeline
    result = await client.call_tool("get_mcp_resource", {
        "resource_uri": "gl://jobs/83/pipeline/1594344/failed"
    })

    # Get specific file analysis with trace
    result = await client.call_tool("get_mcp_resource", {
        "resource_uri": "gl://file/83/76474172/src/main.py/trace?mode=detailed&include_trace=true"
    })

4. Job Trace Tools
~~~~~~~~~~~~~~~~~~

**get_clean_job_trace**
^^^^^^^^^^^^^^^^^^^^^^^

**Purpose**: Get cleaned, human-readable job trace without analysis overhead

**When to use**: Need clean trace data for debugging (ANSI sequences removed)

**Key Features**:
- Direct GitLab API access
- ANSI escape sequence cleaning for readability
- Optional file saving
- Multiple output formats

**Parameters**:
- ``project_id`` (str|int): The GitLab project ID
- ``job_id`` (int): The specific job ID to get trace for
- ``save_to_file`` (bool, default=False): Whether to save cleaned trace to file
- ``output_format`` (str, default="text"): Output format ("text" or "json")

**Examples**:

.. code-block:: python

    # Get cleaned trace
    result = await client.call_tool("get_clean_job_trace", {
        "project_id": "123",
        "job_id": 76986695
    })

    # Save trace to file
    result = await client.call_tool("get_clean_job_trace", {
        "project_id": "123",
        "job_id": 76986695,
        "save_to_file": True
    })

5. Cache Management Tools
~~~~~~~~~~~~~~~~~~~~~~~~~

**cache_stats**
^^^^^^^^^^^^^^^

**Purpose**: Get cache statistics and storage information

**When to use**: Check cache size, usage, and monitor performance

**Key Features**:
- Total cache size and entry count
- Breakdown by data type
- Cache hit/miss statistics
- Storage file information
- Memory usage details

**Parameters**: None

**Example**:

.. code-block:: python

    result = await client.call_tool("cache_stats")

**cache_health**
^^^^^^^^^^^^^^^^

**Purpose**: Check cache system health and performance

**When to use**: Verify cache is working correctly, diagnose issues

**Key Features**:
- Database connectivity checks
- Table schema integrity
- Index performance
- Storage space availability
- Cache operation timing

**Parameters**: None

**Example**:

.. code-block:: python

    result = await client.call_tool("cache_health")

**clear_cache**
^^^^^^^^^^^^^^^

**Purpose**: Clear cached data to free up space or force refresh

**When to use**: Cache maintenance, force fresh data fetch

**Key Features**:
- Selective cache clearing by type
- Project-specific clearing
- Age-based clearing
- Safety protections

**Parameters**:
- ``cache_type`` (str, default="all"): Type of cache to clear

  - "all": Clear all cached data
  - "pipeline": Clear pipeline data only
  - "job": Clear job traces and analysis
  - "analysis": Clear analysis results
  - "error": Clear error data
  - "old": Clear data older than max_age_hours

- ``project_id`` (str|int, optional): Limit clearing to specific project
- ``max_age_hours`` (int, optional): For "old" type, clear data older than this

**Examples**:

.. code-block:: python

    # Clear all cache
    result = await client.call_tool("clear_cache")

    # Clear job data for specific project
    result = await client.call_tool("clear_cache", {
        "cache_type": "job",
        "project_id": "123"
    })

    # Clear old data
    result = await client.call_tool("clear_cache", {
        "cache_type": "old",
        "max_age_hours": 24
    })

**clear_pipeline_cache**
^^^^^^^^^^^^^^^^^^^^^^^^

**Purpose**: Clear all cached data for a specific pipeline

**When to use**: Pipeline was re-run and you want fresh analysis

**Parameters**:
- ``project_id`` (str|int): The GitLab project ID
- ``pipeline_id`` (str|int): The specific pipeline ID to clear

**Example**:

.. code-block:: python

    result = await client.call_tool("clear_pipeline_cache", {
        "project_id": "123",
        "pipeline_id": "1594344"
    })

**clear_job_cache**
^^^^^^^^^^^^^^^^^^^

**Purpose**: Clear all cached data for a specific job

**When to use**: Job was re-run and you want fresh analysis

**Parameters**:
- ``project_id`` (str|int): The GitLab project ID
- ``job_id`` (str|int): The specific job ID to clear

**Example**:

.. code-block:: python

    result = await client.call_tool("clear_job_cache", {
        "project_id": "123",
        "job_id": "76474172"
    })

📦 MCP Resources (5 Resource Categories)
----------------------------------------

MCP resources provide efficient access to cached analysis data without re-running expensive operations. All resources follow the ``gl://`` URI scheme.

1. Pipeline Resources
~~~~~~~~~~~~~~~~~~~~~

**gl://pipeline/{project_id}/{pipeline_id}**
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Purpose**: Pipeline overview with comprehensive info and jobs list

**Contains**:
- Pipeline metadata (status, branch, commit info)
- Job list with status and timing
- Branch resolution for merge requests
- Related resource links

**Example**:

.. code-block:: python

    resource_uri = "gl://pipeline/83/1594344"

2. Job Resources
~~~~~~~~~~~~~~~~

**gl://jobs/{project_id}/pipeline/{pipeline_id}[/status]**
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Purpose**: Get all jobs for a pipeline, optionally filtered by status

**Status Options**:
- ``/failed`` - Only failed jobs
- ``/success`` - Only successful jobs
- ``/all`` - All jobs (default)

**Contains**:
- Job metadata for all/filtered jobs
- Timing and status information
- Links to individual job resources

**Examples**:

.. code-block:: python

    # All jobs
    resource_uri = "gl://jobs/83/pipeline/1594344"

    # Only failed jobs
    resource_uri = "gl://jobs/83/pipeline/1594344/failed"

**gl://job/{project_id}/{pipeline_id}/{job_id}**
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Purpose**: Individual job details and traces

**Contains**:
- Complete job metadata
- Job trace content
- Error analysis if available
- Links to related resources

**Example**:

.. code-block:: python

    resource_uri = "gl://job/83/1594344/76474172"

3. File Resources
~~~~~~~~~~~~~~~~~

**gl://files/{project_id}/pipeline/{pipeline_id}[/page/{page}/limit/{limit}]**
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Purpose**: Files with errors from pipeline analysis (paginated)

**Contains**:
- File paths with error counts
- Pagination information
- Links to specific file analysis

**Example**:

.. code-block:: python

    # First page, default limit
    resource_uri = "gl://files/83/pipeline/1594344"

    # Specific page and limit
    resource_uri = "gl://files/83/pipeline/1594344/page/2/limit/10"

**gl://files/{project_id}/{job_id}[/page/{page}/limit/{limit}]**
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Purpose**: Files with errors from specific job (paginated)

**Contains**:
- Job-specific file error information
- Pagination support
- File-level error summaries

**Example**:

.. code-block:: python

    resource_uri = "gl://files/83/76474172/page/1/limit/20"

**gl://file/{project_id}/{job_id}/{file_path}**
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Purpose**: Specific file analysis with error details

**Contains**:
- File-specific error list
- Error categorization
- Source code context

**Example**:

.. code-block:: python

    resource_uri = "gl://file/83/76474172/src/main.py"

**gl://file/{project_id}/{job_id}/{file_path}/trace?mode={mode}&include_trace={trace}**
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Purpose**: File analysis with trace information

**Parameters**:
- ``mode``: Analysis mode (minimal, balanced, fixing, detailed)
- ``include_trace``: Include trace content (true/false)

**Example**:

.. code-block:: python

    resource_uri = "gl://file/83/76474172/src/main.py/trace?mode=detailed&include_trace=true"

4. Error Resources
~~~~~~~~~~~~~~~~~~

**gl://error/{project_id}/{job_id}[?mode={mode}]**
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Purpose**: Job-specific error analysis

**Modes**:
- ``minimal``: Basic error info
- ``balanced``: Standard detail level (default)
- ``fixing``: Focus on actionable information
- ``detailed``: Complete error analysis

**Contains**:
- Structured error list
- Error categorization
- Fix suggestions

**Example**:

.. code-block:: python

    # Default mode
    resource_uri = "gl://error/83/76474172"

    # Detailed mode
    resource_uri = "gl://error/83/76474172?mode=detailed"

**gl://error/{project_id}/{job_id}/{error_id}**
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Purpose**: Individual error details

**Contains**:
- Complete error information
- Stack trace details
- Context and location
- Fix recommendations

**Example**:

.. code-block:: python

    resource_uri = "gl://error/83/76474172/error_123"

**gl://errors/{project_id}/{job_id}**
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Purpose**: All errors in a specific job

**Contains**:
- Complete job error list
- Error statistics
- Grouped by file/type

**Example**:

.. code-block:: python

    resource_uri = "gl://errors/83/76474172"

**gl://errors/{project_id}/{job_id}/{file_path}**
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Purpose**: File-specific errors within a job

**Contains**:
- Errors specific to one file
- File context information
- Related error patterns

**Example**:

.. code-block:: python

    resource_uri = "gl://errors/83/76474172/src/main.py"

**gl://errors/{project_id}/pipeline/{pipeline_id}**
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Purpose**: Pipeline-wide error analysis

**Contains**:
- Errors across all pipeline jobs
- Cross-job error patterns
- Pipeline-level statistics

**Example**:

.. code-block:: python

    resource_uri = "gl://errors/83/pipeline/1594344"

5. Analysis Resources
~~~~~~~~~~~~~~~~~~~~~

**gl://analysis/{project_id}[?mode={mode}]**
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Purpose**: Project-level analysis summary

**Contains**:
- Project error patterns
- Historical trends
- Common issues

**Example**:

.. code-block:: python

    resource_uri = "gl://analysis/83?mode=detailed"

**gl://analysis/{project_id}/pipeline/{pipeline_id}[?mode={mode}]**
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Purpose**: Pipeline-specific analysis

**Contains**:
- Pipeline failure analysis
- Job comparison
- Error correlations

**Example**:

.. code-block:: python

    resource_uri = "gl://analysis/83/pipeline/1594344?mode=fixing"

**gl://analysis/{project_id}/job/{job_id}[?mode={mode}]**
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Purpose**: Job-specific analysis

**Contains**:
- Job failure analysis
- Error categorization
- Fix recommendations

**Example**:

.. code-block:: python

    resource_uri = "gl://analysis/83/job/76474172?mode=detailed"

Tool Integration Patterns
-------------------------

Typical Workflow
~~~~~~~~~~~~~~~~

1. **Start with Pipeline Analysis**:

   .. code-block:: python

       # Analyze failed pipeline
       analysis = await client.call_tool("failed_pipeline_analysis", {
           "project_id": "123",
           "pipeline_id": 1594344
       })

2. **Access Specific Data via Resources**:

   .. code-block:: python

       # Get failed jobs
       failed_jobs = await client.call_tool("get_mcp_resource", {
           "resource_uri": "gl://jobs/83/pipeline/1594344/failed"
       })

3. **Investigate Specific Issues**:

   .. code-block:: python

       # Get file-specific errors
       file_errors = await client.call_tool("get_mcp_resource", {
           "resource_uri": "gl://errors/83/76474172/src/main.py"
       })

4. **Search for Solutions**:

   .. code-block:: python

       # Search for similar issues in code
       search_results = await client.call_tool("search_repository_code", {
           "project_id": "123",
           "search_keywords": "ModuleNotFoundError",
           "extension_filter": "py"
       })

Cache Management Strategy
~~~~~~~~~~~~~~~~~~~~~~~~~

1. **Monitor Cache Health**:

   .. code-block:: python

       health = await client.call_tool("cache_health")
       stats = await client.call_tool("cache_stats")

2. **Regular Maintenance**:

   .. code-block:: python

       # Clear old data weekly
       await client.call_tool("clear_cache", {
           "cache_type": "old",
           "max_age_hours": 168  # 7 days
       })

3. **Force Refresh When Needed**:

   .. code-block:: python

       # Clear specific pipeline cache after re-run
       await client.call_tool("clear_pipeline_cache", {
           "project_id": "123",
           "pipeline_id": "1594344"
       })

Best Practices
--------------

**Tool Selection**
- Use ``failed_pipeline_analysis`` for initial investigation
- Use ``get_mcp_resource`` for accessing cached data
- Use search tools for finding patterns and solutions
- Use cache tools for maintenance and optimization

**Resource Usage**
- Start with high-level resources (pipeline, jobs)
- Drill down to specific resources (files, errors) as needed
- Use pagination for large datasets
- Leverage mode parameters for appropriate detail level

**Performance Optimization**
- Enable database storage (``store_in_db=True``) for resource access
- Use appropriate analysis modes (minimal for quick checks, detailed for deep analysis)
- Monitor cache health and clear old data regularly
- Use file filtering to focus on relevant errors

**Error Investigation**
- Start with pipeline-level error overview
- Focus on specific jobs/files with highest error counts
- Use search tools to find related code patterns
- Combine multiple tools for comprehensive analysis
