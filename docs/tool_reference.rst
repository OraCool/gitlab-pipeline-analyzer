Tool Reference
==============

This is the comprehensive reference for all 21 MCP tools provided by the GitLab Pipeline Analyzer. Each tool is documented with complete parameter descriptions, return types, and example responses.

.. contents::
   :local:
   :depth: 2

Analysis Tools
--------------

analyze_failed_pipeline
~~~~~~~~~~~~~~~~~~~~~~~~

**Complete pipeline failure analysis with concurrent job processing and enhanced error categorization.**

Signature:
  .. code-block:: python

     @mcp.tool
     async def analyze_failed_pipeline(
         project_id: str | int,
         pipeline_id: int
     ) -> dict[str, Any]

Parameters:
  .. list-table::
     :header-rows: 1
     :widths: 15 15 10 60

     * - Parameter
       - Type
       - Required
       - Description
     * - ``project_id``
       - ``str | int``
       - Yes
       - GitLab project ID or path (e.g., "123" or "group/project")
     * - ``pipeline_id``
       - ``int``
       - Yes
       - GitLab pipeline ID to analyze

Returns:
  .. code-block:: javascript

     {
       "project_id": "123",
       "pipeline_id": 456,
       "pipeline_status": {
         "id": 456,
         "status": "failed",
         "ref": "main",
         "sha": "abc123def456",
         "created_at": "2025-01-01T10:00:00Z",
         "web_url": "https://gitlab.com/project/-/pipelines/456"
       },
       "failed_jobs_count": 3,
       "job_analyses": [
         {
           "job_id": 789,
           "job_name": "test:unit",
           "job_status": "failed",
           "errors": ["error objects"],
           "warnings": ["warning objects"],
           "error_count": 5,
           "warning_count": 2,
           "parser_type": "pytest",
           "parser_info": {
             "detected_as_pytest": true,
             "extraction_method": "pytest_specialized_parser"
           }
         }
       ],
       "detailed_errors": [
         {
           "category": "AssertionError",
           "message": "Expected 5 but got 3",
           "file_path": "tests/test_math.py",
           "line_number": 25,
           "job_id": 789,
           "job_name": "test:unit",
           "parser_used": "pytest"
         }
       ],
       "summary": {
         "total_errors": 15,
         "total_warnings": 8,
         "jobs_with_errors": 3,
         "jobs_with_warnings": 2,
         "error_categories": {
           "test_failure": ["error details"],
           "import_error": ["error details"]
         },
         "category_count": 4
       },
       "parser_analysis": {
         "usage_summary": {
           "pytest": {
             "count": 2,
             "jobs": ["job objects"],
             "total_errors": 12
           },
           "generic": {
             "count": 1,
             "jobs": ["job objects"],
             "total_errors": 3
           }
         },
         "parsing_strategy": "auto_detect_pytest_then_generic",
         "parser_types_used": ["pytest", "generic"]
       },
       "analysis_timestamp": "2025-01-01T10:30:00.123456",
       "processing_mode": "optimized_concurrent",
       "mcp_info": {
         "name": "GitLab Pipeline Analyzer",
         "version": "0.2.6",
         "tools_used": ["analyze_failed_pipeline", "get_job_trace", "extract_pytest_errors"],
         "parser_types": ["pytest", "generic"]
       }
     }

Error Response:
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

analyze_single_job
~~~~~~~~~~~~~~~~~~

**Deep analysis of a single job with automatic parser detection and structured error extraction.**

Signature:
  .. code-block:: python

     @mcp.tool
     async def analyze_single_job(
         project_id: str | int,
         job_id: int
     ) -> dict[str, Any]

Parameters:
  .. list-table::
     :header-rows: 1
     :widths: 15 15 10 60

     * - Parameter
       - Type
       - Required
       - Description
     * - ``project_id``
       - ``str | int``
       - Yes
       - GitLab project ID or path
     * - ``job_id``
       - ``int``
       - Yes
       - GitLab job ID to analyze

Returns:
  **For pytest jobs:**

  .. code-block:: javascript

     {
       "project_id": "123",
       "job_id": 789,
       "errors": [
         {
           "exception_type": "AssertionError",
           "exception_message": "Expected 5 but got 3",
           "test_file": "tests/test_math.py",
           "test_function": "test_addition",
           "line_number": 25,
           "traceback": ["traceback details"]
         }
       ],
       "warnings": [],
       "error_count": 1,
       "warning_count": 0,
       "total_entries": 45,
       "trace_length": 12450,
       "parser_type": "pytest",
       "analysis_timestamp": "2025-01-01T10:30:00.123456",
       "mcp_info": {
         "name": "GitLab Pipeline Analyzer",
         "version": "0.2.6",
         "tool_used": "analyze_single_job",
         "parser_type": "pytest"
       }
     }

  **For generic jobs:**

  .. code-block:: json

     {
       "project_id": "123",
       "job_id": 789,
       "errors": [
         {
           "level": "error",
           "message": "npm ERR! missing script: build",
           "line_number": 45,
           "timestamp": "2025-01-01T10:25:30Z",
           "context": "npm run build",
           "categorization": {
             "category": "build_error",
             "severity": "high",
             "confidence": 0.95
           }
         }
       ],
       "warnings": [],
       "error_count": 1,
       "warning_count": 0,
       "total_entries": 15,
       "trace_length": 3420,
       "parser_type": "generic",
       "analysis_timestamp": "2025-01-01T10:30:00.123456",
       "mcp_info": {
         "name": "GitLab Pipeline Analyzer",
         "version": "0.2.6",
         "tool_used": "analyze_single_job",
         "parser_type": "generic"
       }
     }

Info Tools
----------

get_pipeline_jobs
~~~~~~~~~~~~~~~~~~

**Get comprehensive list of all jobs in a pipeline with their status and metadata.**

Signature:
  .. code-block:: python

     @mcp.tool
     async def get_pipeline_jobs(
         project_id: str | int,
         pipeline_id: int
     ) -> dict[str, Any]

Parameters:
  .. list-table::
     :header-rows: 1
     :widths: 15 15 10 60

     * - Parameter
       - Type
       - Required
       - Description
     * - ``project_id``
       - ``str | int``
       - Yes
       - GitLab project ID or path
     * - ``pipeline_id``
       - ``int``
       - Yes
       - GitLab pipeline ID

Returns:
  .. code-block:: json

     {
       "project_id": "123",
       "pipeline_id": 456,
       "jobs": [
         {
           "id": 789,
           "name": "test:unit",
           "stage": "test",
           "status": "failed",
           "created_at": "2025-01-01T10:00:00Z",
           "started_at": "2025-01-01T10:01:00Z",
           "finished_at": "2025-01-01T10:05:00Z",
           "duration": 240.5,
           "web_url": "https://gitlab.com/project/-/jobs/789"
         },
         {
           "id": 790,
           "name": "build:docker",
           "stage": "build",
           "status": "success",
           "duration": 180.2
         }
       ],
       "job_count": 2,
       "analysis_timestamp": "2025-01-01T10:30:00.123456",
       "mcp_info": {
         "name": "GitLab Pipeline Analyzer",
         "version": "0.2.6",
         "tool_used": "get_pipeline_jobs"
       }
     }

get_failed_jobs
~~~~~~~~~~~~~~~

**Get filtered list of only failed jobs from a pipeline.**

Signature:
  .. code-block:: python

     @mcp.tool
     async def get_failed_jobs(
         project_id: str | int,
         pipeline_id: int
     ) -> dict[str, Any]

Parameters:
  .. list-table::
     :header-rows: 1
     :widths: 15 15 10 60

     * - Parameter
       - Type
       - Required
       - Description
     * - ``project_id``
       - ``str | int``
       - Yes
       - GitLab project ID or path
     * - ``pipeline_id``
       - ``int``
       - Yes
       - GitLab pipeline ID

Returns:
  .. code-block:: json

     {
       "project_id": "123",
       "pipeline_id": 456,
       "failed_jobs": [
         {
           "id": 789,
           "name": "test:unit",
           "stage": "test",
           "status": "failed",
           "failure_reason": "script_failure"
         }
       ],
       "failed_job_count": 1,
       "mcp_info": {
         "name": "GitLab Pipeline Analyzer",
         "version": "0.2.6",
         "tool_used": "get_failed_jobs"
       }
     }

get_pipeline_status
~~~~~~~~~~~~~~~~~~~

**Get basic pipeline status and metadata for quick assessment.**

Signature:
  .. code-block:: python

     @mcp.tool
     async def get_pipeline_status(
         project_id: str | int,
         pipeline_id: int
     ) -> dict[str, Any]

Parameters:
  .. list-table::
     :header-rows: 1
     :widths: 15 15 10 60

     * - Parameter
       - Type
       - Required
       - Description
     * - ``project_id``
       - ``str | int``
       - Yes
       - GitLab project ID or path
     * - ``pipeline_id``
       - ``int``
       - Yes
       - GitLab pipeline ID

Returns:
  .. code-block:: json

     {
       "project_id": "123",
       "pipeline_id": 456,
       "status": "failed",
       "ref": "main",
       "sha": "abc123def456",
       "created_at": "2025-01-01T10:00:00Z",
       "updated_at": "2025-01-01T10:05:00Z",
       "duration": 300,
       "web_url": "https://gitlab.com/project/-/pipelines/456",
       "mcp_info": {
         "name": "GitLab Pipeline Analyzer",
         "version": "0.2.6",
         "tool_used": "get_pipeline_status"
       }
     }

get_pipeline_info
~~~~~~~~~~~~~~~~~

**Get comprehensive pipeline information with merge request branch resolution.**

Signature:
  .. code-block:: python

     @mcp.tool
     async def get_pipeline_info(
         project_id: str | int,
         pipeline_id: int
     ) -> dict[str, Any]

Parameters:
  .. list-table::
     :header-rows: 1
     :widths: 15 15 10 60

     * - Parameter
       - Type
       - Required
       - Description
     * - ``project_id``
       - ``str | int``
       - Yes
       - GitLab project ID or path
     * - ``pipeline_id``
       - ``int``
       - Yes
       - GitLab pipeline ID

Returns:
  **For regular branch pipelines:**

  .. code-block:: json

     {
       "project_id": "123",
       "pipeline_id": 456,
       "pipeline_info": {
         "id": 456,
         "status": "failed",
         "ref": "feature-branch",
         "sha": "abc123def456"
       },
       "original_branch": "feature-branch",
       "target_branch": "feature-branch",
       "pipeline_type": "branch",
       "merge_request_info": null,
       "can_auto_fix": true,
       "analysis_timestamp": "2025-01-01T10:30:00.123456",
       "mcp_info": {
         "name": "GitLab Pipeline Analyzer",
         "version": "0.2.6",
         "tool_used": "get_pipeline_info"
       }
     }

  **For merge request pipelines:**

  .. code-block:: javascript

     {
       "project_id": "123",
       "pipeline_id": 456,
       "pipeline_info": {"status": "failed", "ref": "refs/merge-requests/42/head"},
       "original_branch": "refs/merge-requests/42/head",
       "target_branch": "feature-branch",
       "pipeline_type": "merge_request",
       "merge_request_info": {
         "iid": 42,
         "title": "Add new feature",
         "source_branch": "feature-branch",
         "target_branch_name": "main",
         "state": "opened",
         "web_url": "https://gitlab.com/project/-/merge_requests/42"
       },
       "can_auto_fix": true
     }

Log Tools
---------

get_job_trace
~~~~~~~~~~~~~

**Get raw job trace logs with original ANSI formatting intact.**

Signature:
  .. code-block:: python

     @mcp.tool
     async def get_job_trace(
         project_id: str | int,
         job_id: int
     ) -> dict[str, Any]

Parameters:
  .. list-table::
     :header-rows: 1
     :widths: 15 15 10 60

     * - Parameter
       - Type
       - Required
       - Description
     * - ``project_id``
       - ``str | int``
       - Yes
       - GitLab project ID or path
     * - ``job_id``
       - ``int``
       - Yes
       - GitLab job ID

Returns:
  .. code-block:: json

     {
       "project_id": "123",
       "job_id": 789,
       "trace": "\u001b[32mRunning with gitlab-runner...\u001b[0m\nStep 1/3\n...",
       "trace_length": 15420,
       "mcp_info": {
         "name": "GitLab Pipeline Analyzer",
         "version": "0.2.6",
         "tool_used": "get_job_trace"
       }
     }

get_cleaned_job_trace
~~~~~~~~~~~~~~~~~~~~~

**Get job trace with ANSI codes removed and cleaning statistics.**

Signature:
  .. code-block:: python

     @mcp.tool
     async def get_cleaned_job_trace(
         project_id: str | int,
         job_id: int
     ) -> dict[str, Any]

Parameters:
  .. list-table::
     :header-rows: 1
     :widths: 15 15 10 60

     * - Parameter
       - Type
       - Required
       - Description
     * - ``project_id``
       - ``str | int``
       - Yes
       - GitLab project ID or path
     * - ``job_id``
       - ``int``
       - Yes
       - GitLab job ID

Returns:
  .. code-block:: json

     {
       "project_id": "123",
       "job_id": 789,
       "cleaned_trace": "Running with gitlab-runner...\nStep 1/3\n...",
       "original_length": 15420,
       "cleaned_length": 14850,
       "bytes_removed": 570,
       "reduction_percentage": 3.7,
       "ansi_sequences_found": 45,
       "unique_ansi_types": 8,
       "analysis_timestamp": "2025-01-01T10:30:00.123456",
       "mcp_info": {
         "name": "GitLab Pipeline Analyzer",
         "version": "0.2.6",
         "tool_used": "get_cleaned_job_trace"
       }
     }

extract_log_errors
~~~~~~~~~~~~~~~~~~

**Extract structured errors and warnings from raw log text using pattern matching.**

Signature:
  .. code-block:: python

     @mcp.tool
     async def extract_log_errors(
         log_text: str
     ) -> dict[str, Any]

Parameters:
  .. list-table::
     :header-rows: 1
     :widths: 15 15 10 60

     * - Parameter
       - Type
       - Required
       - Description
     * - ``log_text``
       - ``str``
       - Yes
       - Raw log text to analyze for errors and warnings

Returns:
  .. code-block:: json

     {
       "errors": [
         {
           "level": "error",
           "message": "ModuleNotFoundError: No module named 'requests'",
           "line_number": 15,
           "context": "import requests",
           "category": "import_error"
         }
       ],
       "warnings": [
         {
           "level": "warning",
           "message": "DeprecationWarning: function is deprecated",
           "line_number": 25,
           "context": "old_function()",
           "category": "deprecation"
         }
       ],
       "error_count": 1,
       "warning_count": 1,
       "total_entries": 2,
       "mcp_info": {
         "name": "GitLab Pipeline Analyzer",
         "version": "0.2.6",
         "tool_used": "extract_log_errors"
       }
     }

Pytest Tools
------------

analyze_pytest_job_complete
~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Complete pytest analysis combining detailed failures, summary, and statistics.**

Signature:
  .. code-block:: python

     @mcp.tool
     async def analyze_pytest_job_complete(
         project_id: str | int,
         job_id: int
     ) -> dict[str, Any]

Parameters:
  .. list-table::
     :header-rows: 1
     :widths: 15 15 10 60

     * - Parameter
       - Type
       - Required
       - Description
     * - ``project_id``
       - ``str | int``
       - Yes
       - GitLab project ID or path
     * - ``job_id``
       - ``int``
       - Yes
       - GitLab job ID containing pytest output

Returns:
  .. code-block:: json

     {
       "project_id": "123",
       "job_id": 789,
       "detailed_failures": [
         {
           "test_name": "test_user_creation",
           "test_file": "tests/test_users.py",
           "test_function": "test_user_creation",
           "line_number": 25,
           "exception_type": "AssertionError",
           "exception_message": "Expected 5 but got 3",
           "traceback": [
             {
               "file_path": "tests/test_users.py",
               "line_number": 25,
               "code_line": "assert result == 5"
             }
           ],
           "full_error_text": "AssertionError: Expected 5 but got 3\n..."
         }
       ],
       "short_summary": [
         {
           "test_name": "test_user_creation",
           "error_message": "AssertionError: Expected 5 but got 3",
           "test_file": "tests/test_users.py"
         }
       ],
       "statistics": {
         "total_tests": 10,
         "passed": 8,
         "failed": 1,
         "skipped": 1,
         "errors": 0,
         "warnings": 0,
         "duration_seconds": 15.42,
         "duration_formatted": "15.42s"
       },
       "analysis_timestamp": "2025-01-01T10:30:00.123456",
       "mcp_info": {
         "name": "GitLab Pipeline Analyzer",
         "version": "0.2.6",
         "tool_used": "analyze_pytest_job_complete"
       }
     }

extract_pytest_detailed_failures
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Extract comprehensive pytest failure information with full tracebacks.**

Signature:
  .. code-block:: python

     @mcp.tool
     async def extract_pytest_detailed_failures(
         project_id: str | int,
         job_id: int
     ) -> dict[str, Any]

Parameters:
  .. list-table::
     :header-rows: 1
     :widths: 15 15 10 60

     * - Parameter
       - Type
       - Required
       - Description
     * - ``project_id``
       - ``str | int``
       - Yes
       - GitLab project ID or path
     * - ``job_id``
       - ``int``
       - Yes
       - GitLab job ID containing pytest output

Returns:
  .. code-block:: json

     {
       "project_id": "123",
       "job_id": 789,
       "detailed_failures": [
         {
           "test_name": "test_complex_calculation",
           "test_file": "tests/test_math.py",
           "test_function": "test_complex_calculation",
           "line_number": 45,
           "exception_type": "ValueError",
           "exception_message": "Invalid input value",
           "platform_info": "Python 3.11.0 on Linux",
           "traceback": [
             {
               "file_path": "src/math_utils.py",
               "line_number": 15,
               "code_line": "raise ValueError('Invalid input value')",
               "function_name": "calculate"
             },
             {
               "file_path": "tests/test_math.py",
               "line_number": 45,
               "code_line": "result = calculate(invalid_input)",
               "function_name": "test_complex_calculation"
             }
           ],
           "full_error_text": "ValueError: Invalid input value\n    File \"src/math_utils.py\", line 15..."
         }
       ],
       "failure_count": 1,
       "mcp_info": {
         "name": "GitLab Pipeline Analyzer",
         "version": "0.2.6",
         "tool_used": "extract_pytest_detailed_failures"
       }
     }

extract_pytest_short_summary
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Get concise pytest failure summary for rapid assessment.**

Signature:
  .. code-block:: python

     @mcp.tool
     async def extract_pytest_short_summary(
         project_id: str | int,
         job_id: int
     ) -> dict[str, Any]

Parameters:
  .. list-table::
     :header-rows: 1
     :widths: 15 15 10 60

     * - Parameter
       - Type
       - Required
       - Description
     * - ``project_id``
       - ``str | int``
       - Yes
       - GitLab project ID or path
     * - ``job_id``
       - ``int``
       - Yes
       - GitLab job ID containing pytest output

Returns:
  .. code-block:: json

     {
       "project_id": "123",
       "job_id": 789,
       "short_summary": [
         {
           "test_name": "test_user_creation",
           "test_file": "tests/test_users.py",
           "exception_type": "AssertionError",
           "error_message": "Expected 5 but got 3"
         },
         {
           "test_name": "test_data_validation",
           "test_file": "tests/test_validation.py",
           "exception_type": "ValueError",
           "error_message": "Invalid data format"
         }
       ],
       "summary_count": 2,
       "mcp_info": {
         "name": "GitLab Pipeline Analyzer",
         "version": "0.2.6",
         "tool_used": "extract_pytest_short_summary"
       }
     }

extract_pytest_statistics
~~~~~~~~~~~~~~~~~~~~~~~~~

**Get test execution statistics and performance metrics.**

Signature:
  .. code-block:: python

     @mcp.tool
     async def extract_pytest_statistics(
         project_id: str | int,
         job_id: int
     ) -> dict[str, Any]

Parameters:
  .. list-table::
     :header-rows: 1
     :widths: 15 15 10 60

     * - Parameter
       - Type
       - Required
       - Description
     * - ``project_id``
       - ``str | int``
       - Yes
       - GitLab project ID or path
     * - ``job_id``
       - ``int``
       - Yes
       - GitLab job ID containing pytest output

Returns:
  .. code-block:: json

     {
       "project_id": "123",
       "job_id": 789,
       "statistics": {
         "total_tests": 150,
         "passed": 142,
         "failed": 5,
         "skipped": 3,
         "errors": 0,
         "warnings": 2,
         "duration_seconds": 45.67,
         "duration_formatted": "45.67s",
         "pass_rate": 94.7,
         "failure_rate": 3.3,
         "skip_rate": 2.0
       },
       "performance_metrics": {
         "avg_test_duration": 0.304,
         "slowest_tests": [
           {
             "test_name": "test_heavy_computation",
             "duration": 2.45
           }
         ]
       },
       "mcp_info": {
         "name": "GitLab Pipeline Analyzer",
         "version": "0.2.6",
         "tool_used": "extract_pytest_statistics"
       }
     }

Pagination Tools
----------------

group_errors_by_file
~~~~~~~~~~~~~~~~~~~~

**Group errors by file path for systematic fixing approach with advanced filtering.**

Signature:
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
     ) -> dict[str, Any]

Parameters:
  .. list-table::
     :header-rows: 1
     :widths: 20 15 10 55

     * - Parameter
       - Type
       - Required
       - Description
     * - ``project_id``
       - ``str | int``
       - Yes
       - GitLab project ID or path
     * - ``pipeline_id``
       - ``int | None``
       - No*
       - Pipeline ID (required if job_id not provided)
     * - ``job_id``
       - ``int | None``
       - No*
       - Specific job ID (overrides pipeline_id)
     * - ``max_files``
       - ``int``
       - No
       - Maximum files to return (default: 10)
     * - ``max_errors_per_file``
       - ``int``
       - No
       - Maximum errors per file (default: 5)
     * - ``include_traceback``
       - ``bool``
       - No
       - Include traceback information (default: True)
     * - ``exclude_paths``
       - ``list[str] | None``
       - No
       - Path patterns to exclude from traceback
     * - ``exclude_file_patterns``
       - ``list[str] | None``
       - No
       - File path patterns to exclude from results

\*Either ``pipeline_id`` or ``job_id`` must be provided.

Returns:
  .. code-block:: json

     {
       "project_id": "123",
       "file_groups": [
         {
           "file_path": "src/users.py",
           "error_count": 5,
           "errors": [
             {
               "line_number": 25,
               "exception_type": "ValueError",
               "message": "Invalid user data",
               "job_id": 789,
               "job_name": "test:unit"
             }
           ],
           "error_types": ["ValueError", "TypeError"],
           "jobs_affected": ["test:unit", "test:integration"],
           "priority": "high"
         }
       ],
       "summary": {
         "total_files_with_errors": 15,
         "files_returned": 10,
         "total_errors": 45,
         "files_truncated": true,
         "unknown_errors_excluded": 3
       },
       "categorization": {
         "test_files": {"count": 8, "total_errors": 25},
         "source_files": {"count": 7, "total_errors": 20}
       },
       "processing_limits": {
         "max_files": 10,
         "max_errors_per_file": 5,
         "total_files_available": 15
       },
       "filtering_options": {
         "include_traceback": true,
         "exclude_paths": [".venv", "site-packages"],
         "exclude_file_patterns": ["*.pyc", "__pycache__"]
       },
       "mcp_info": {
         "name": "GitLab Pipeline Analyzer",
         "version": "0.2.6",
         "tool_used": "group_errors_by_file"
       }
     }

get_files_with_errors
~~~~~~~~~~~~~~~~~~~~~

**Get list of files containing errors without detailed error information.**

Signature:
  .. code-block:: python

     @mcp.tool
     async def get_files_with_errors(
         project_id: str | int,
         pipeline_id: int | None = None,
         job_id: int | None = None,
         max_files: int = 20,
         exclude_file_patterns: list[str] | None = None,
         response_mode: str = "balanced"
     ) -> dict[str, Any]

Parameters:
  .. list-table::
     :header-rows: 1
     :widths: 20 15 10 55

     * - Parameter
       - Type
       - Required
       - Description
     * - ``project_id``
       - ``str | int``
       - Yes
       - GitLab project ID or path
     * - ``pipeline_id``
       - ``int | None``
       - No*
       - Pipeline ID (required if job_id not provided)
     * - ``job_id``
       - ``int | None``
       - No*
       - Specific job ID (overrides pipeline_id)
     * - ``max_files``
       - ``int``
       - No
       - Maximum files to return (default: 20)
     * - ``exclude_file_patterns``
       - ``list[str] | None``
       - No
       - File path patterns to exclude
     * - ``response_mode``
       - ``str``
       - No
       - Response optimization mode (default: "balanced")

\*Either ``pipeline_id`` or ``job_id`` must be provided.

Returns:
  .. code-block:: json

     {
       "project_id": "123",
       "files_with_errors": [
         {
           "file_path": "src/users.py",
           "error_count": 5,
           "file_type": "source",
           "jobs_affected": ["test:unit"]
         },
         {
           "file_path": "tests/test_auth.py",
           "error_count": 3,
           "file_type": "test",
           "jobs_affected": ["test:integration"]
         }
       ],
       "summary": {
         "total_files_with_errors": 15,
         "files_returned": 2,
         "total_errors": 8,
         "files_truncated": true
       },
       "categorization": {
         "test_files": {"count": 1, "total_errors": 3},
         "source_files": {"count": 1, "total_errors": 5}
       }
     }

get_file_errors
~~~~~~~~~~~~~~~

**Get all errors for a specific file with advanced filtering options.**

Signature:
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
     ) -> dict[str, Any]

Parameters:
  .. list-table::
     :header-rows: 1
     :widths: 20 15 10 55

     * - Parameter
       - Type
       - Required
       - Description
     * - ``project_id``
       - ``str | int``
       - Yes
       - GitLab project ID or path
     * - ``job_id``
       - ``int``
       - Yes
       - GitLab job ID
     * - ``file_path``
       - ``str``
       - Yes
       - Specific file path to get errors for
     * - ``max_errors``
       - ``int``
       - No
       - Maximum errors to return (default: 10)
     * - ``include_traceback``
       - ``bool``
       - No
       - Include traceback information (default: True)
     * - ``exclude_paths``
       - ``list[str] | None``
       - No
       - Path patterns to exclude from traceback
     * - ``job_name``
       - ``str``
       - No
       - Optional job name for better parser detection
     * - ``job_stage``
       - ``str``
       - No
       - Optional job stage for better parser detection
     * - ``response_mode``
       - ``str``
       - No
       - Response optimization mode (default: "balanced")

Returns:
  .. code-block:: json

     {
       "project_id": "123",
       "job_id": 789,
       "file_path": "src/users.py",
       "errors": [
         {
           "line_number": 25,
           "exception_type": "ValueError",
           "exception_message": "Invalid user data",
           "test_function": "test_user_creation",
           "traceback": [
             {
               "file_path": "src/users.py",
               "line_number": 25,
               "code_line": "raise ValueError('Invalid user data')"
             }
           ]
         }
       ],
       "file_statistics": {
         "returned_errors": 1,
         "truncated": false,
         "total_error_count": 1,
         "error_types": ["ValueError"],
         "lines_with_errors": [25]
       },
       "filtering_options": {
         "include_traceback": true,
         "exclude_paths": [".venv", "site-packages"],
         "max_errors": 10
       },
       "parser_type": "pytest",
       "mcp_info": {
         "name": "GitLab Pipeline Analyzer",
         "version": "0.2.6",
         "tool_used": "get_file_errors"
       }
     }

get_error_batch
~~~~~~~~~~~~~~~

**Get paginated batch of errors from a job for handling large error lists.**

Signature:
  .. code-block:: python

     @mcp.tool
     async def get_error_batch(
         project_id: str | int,
         job_id: int,
         start_index: int = 0,
         batch_size: int = 3,
         include_traceback: bool = True,
         exclude_paths: list[str] | None = None
     ) -> dict[str, Any]

Parameters:
  .. list-table::
     :header-rows: 1
     :widths: 20 15 10 55

     * - Parameter
       - Type
       - Required
       - Description
     * - ``project_id``
       - ``str | int``
       - Yes
       - GitLab project ID or path
     * - ``job_id``
       - ``int``
       - Yes
       - GitLab job ID
     * - ``start_index``
       - ``int``
       - No
       - Starting index for batch (0-based, default: 0)
     * - ``batch_size``
       - ``int``
       - No
       - Number of errors to return (default: 3)
     * - ``include_traceback``
       - ``bool``
       - No
       - Include traceback information (default: True)
     * - ``exclude_paths``
       - ``list[str] | None``
       - No
       - Path patterns to exclude from traceback

Returns:
  .. code-block:: javascript

     {
       "project_id": "123",
       "job_id": 789,
       "errors": [
         {
           "line_number": 25,
           "exception_type": "ValueError",
           "exception_message": "Invalid input",
           "traceback": ["traceback details"]
         }
       ],
       "batch_info": {
         "start_index": 0,
         "batch_size": 3,
         "returned_count": 1,
         "total_errors": 15,
         "has_more": true,
         "next_start_index": 3
       },
       "filtering_options": {
         "include_traceback": true,
         "exclude_paths": [".venv", "site-packages"]
       },
       "parser_type": "pytest",
       "mcp_info": {
         "name": "GitLab Pipeline Analyzer",
         "version": "0.2.6",
         "tool_used": "get_error_batch"
       }
     }

analyze_failed_pipeline_summary
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Get pipeline failure overview with limited error details to prevent response truncation.**

Signature:
  .. code-block:: python

     @mcp.tool
     async def analyze_failed_pipeline_summary(
         project_id: str | int,
         pipeline_id: int
     ) -> dict[str, Any]

Parameters:
  .. list-table::
     :header-rows: 1
     :widths: 15 15 10 60

     * - Parameter
       - Type
       - Required
       - Description
     * - ``project_id``
       - ``str | int``
       - Yes
       - GitLab project ID or path
     * - ``pipeline_id``
       - ``int``
       - Yes
       - GitLab pipeline ID

Returns:
  .. code-block:: javascript

     {
       "project_id": "123",
       "pipeline_id": 456,
       "pipeline_status": {"status": "failed", "ref": "main"},
       "failed_jobs": [
         {
           "job_id": 789,
           "job_name": "test:unit",
           "error_count": 5,
           "warning_count": 2,
           "parser_type": "pytest"
         }
       ],
       "summary": {
         "total_failed_jobs": 3,
         "total_errors": 15,
         "total_warnings": 8,
         "most_errors_in_job": 7,
         "parser_distribution": {
           "pytest": 2,
           "generic": 1
         }
       },
       "mcp_info": {
         "name": "GitLab Pipeline Analyzer",
         "version": "0.2.6",
         "tool_used": "analyze_failed_pipeline_summary"
       }
     }

analyze_single_job_limited
~~~~~~~~~~~~~~~~~~~~~~~~~~

**Analyze single job with response size controls to prevent truncation.**

Signature:
  .. code-block:: python

     @mcp.tool
     async def analyze_single_job_limited(
         project_id: str | int,
         job_id: int,
         max_errors: int = 5,
         include_traceback: bool = False
     ) -> dict[str, Any]

Parameters:
  .. list-table::
     :header-rows: 1
     :widths: 20 15 10 55

     * - Parameter
       - Type
       - Required
       - Description
     * - ``project_id``
       - ``str | int``
       - Yes
       - GitLab project ID or path
     * - ``job_id``
       - ``int``
       - Yes
       - GitLab job ID
     * - ``max_errors``
       - ``int``
       - No
       - Maximum errors to return (default: 5)
     * - ``include_traceback``
       - ``bool``
       - No
       - Include traceback information (default: False)

Returns:
  .. code-block:: javascript

     {
       "project_id": "123",
       "job_id": 789,
       "errors": ["error objects"],
       "warnings": ["warning objects"],
       "error_count": 3,
       "warning_count": 1,
       "total_available_errors": 15,
       "truncated": true,
       "parser_type": "pytest",
       "limitations": {
         "max_errors": 5,
         "include_traceback": false,
         "reason": "response_size_control"
       },
       "mcp_info": {
         "name": "GitLab Pipeline Analyzer",
         "version": "0.2.6",
         "tool_used": "analyze_single_job_limited"
       }
     }

Search Tools
------------

search_repository_code
~~~~~~~~~~~~~~~~~~~~~~

**Search for keywords in repository code files with advanced filtering.**

Signature:
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
     ) -> str

Parameters:
  .. list-table::
     :header-rows: 1
     :widths: 20 15 10 55

     * - Parameter
       - Type
       - Required
       - Description
     * - ``project_id``
       - ``str | int``
       - Yes
       - GitLab project ID or path
     * - ``search_keywords``
       - ``str``
       - Yes
       - Keywords to search for in code
     * - ``branch``
       - ``str | None``
       - No
       - Specific branch to search (optional)
     * - ``filename_filter``
       - ``str | None``
       - No
       - Filter by filename pattern (supports wildcards like ``*.py``)
     * - ``path_filter``
       - ``str | None``
       - No
       - Filter by file path pattern (e.g., src/*, models/*)
     * - ``extension_filter``
       - ``str | None``
       - No
       - Filter by file extension (e.g., 'py', 'js', 'ts')
     * - ``max_results``
       - ``int``
       - No
       - Maximum number of results to return (default: 20)
     * - ``output_format``
       - ``str``
       - No
       - Output format: "text" (default)

Returns:
  **Text Output:**

  .. code-block:: text

     🔍 Code Search Results for 'async def process' in project 123
     Found 15 total matches (showing first 10)
     Branch: main

     📄 Result 1: src/processors/data_processor.py
        Line: 25 | Branch: main
        Content:
        ──────────────────────────────────────────────────
          23 | class DataProcessor:
          24 |     """Process data asynchronously"""
          25 |     async def process(self, data):
          26 |         """Main processing method"""
          27 |         return await self._process_data(data)

     📄 Result 2: src/handlers/request_handler.py
        Line: 42 | Branch: main
        Content:
        ──────────────────────────────────────────────────
          40 | class RequestHandler:
          41 |
          42 |     async def process_request(self, request):
          43 |         """Process incoming request"""
          44 |         return await self.validate_and_process(request)

     Use max_results parameter to see more results

search_repository_commits
~~~~~~~~~~~~~~~~~~~~~~~~~

**Search for keywords in repository commit messages with branch filtering.**

Signature:
  .. code-block:: python

     @mcp.tool
     async def search_repository_commits(
         project_id: str | int,
         search_keywords: str,
         branch: str | None = None,
         max_results: int = 20,
         output_format: str = "text"
     ) -> str

Parameters:
  .. list-table::
     :header-rows: 1
     :widths: 20 15 10 55

     * - Parameter
       - Type
       - Required
       - Description
     * - ``project_id``
       - ``str | int``
       - Yes
       - GitLab project ID or path
     * - ``search_keywords``
       - ``str``
       - Yes
       - Keywords to search for in commit messages
     * - ``branch``
       - ``str | None``
       - No
       - Specific branch to search (optional)
     * - ``max_results``
       - ``int``
       - No
       - Maximum number of results to return (default: 20)
     * - ``output_format``
       - ``str``
       - No
       - Output format: "text" (default)

Returns:
  **Text Output:**

  .. code-block:: text

     🔍 Commit Search Results for 'fix bug' in project 123
     Found 8 total matches (showing first 8)

     📝 Commit 1: a1b2c3d4
        Title: Fix bug in user authentication
        Author: John Doe <john@example.com>
        Date: 2025-01-01T10:00:00Z
        Message:
        ──────────────────────────────────────────────────
        Fix bug in user authentication

        - Fixed token validation logic
        - Added proper error handling
        - Updated tests for edge cases

     📝 Commit 2: e5f6g7h8
        Title: Fix bug in data processing pipeline
        Author: Jane Smith <jane@example.com>
        Date: 2025-01-01T09:30:00Z
        Message:
        ──────────────────────────────────────────────────
        Fix bug in data processing pipeline

        - Resolved memory leak in processor
        - Improved error messages

Common Response Patterns
------------------------

Response Optimization
~~~~~~~~~~~~~~~~~~~~~

Many tools support response optimization through the ``response_mode`` parameter:

- **minimal**: Essential information only, smallest response size
- **balanced**: Good balance of detail and size (default)
- **fixing**: Optimized for error fixing with guidance and context
- **full**: Complete information, largest response size

Error Responses
~~~~~~~~~~~~~~~

All tools return consistent error response structure:

.. code-block:: json

   {
     "error": "Descriptive error message",
     "project_id": "123",
     "pipeline_id": 456,  // if applicable
     "job_id": 789,       // if applicable
     "mcp_info": {
       "name": "GitLab Pipeline Analyzer",
       "version": "0.2.6",
       "tool_used": "tool_name",
       "error": true
     }
   }

MCP Info Structure
~~~~~~~~~~~~~~~~~~

All successful responses include ``mcp_info`` metadata:

.. code-block:: json

   {
     "mcp_info": {
       "name": "GitLab Pipeline Analyzer",
       "version": "0.2.6",
       "tool_used": "tool_name",
       "additional_context": "..."
     }
   }

Traceback Filtering
~~~~~~~~~~~~~~~~~~~

Tools with traceback support use ``DEFAULT_EXCLUDE_PATHS`` when ``exclude_paths`` is not specified:

.. code-block:: python

   DEFAULT_EXCLUDE_PATHS = [
       ".venv", "site-packages", ".local", "/builds/",
       "/root/.local", "/usr/lib/python", "/opt/python",
       "/__pycache__/", ".cache", "/tmp/"
   ]

This automatic filtering helps focus on application code rather than system dependencies.

Next Steps
----------

- See :doc:`examples` for practical usage examples
- Check :doc:`configuration` for advanced setup options
- Review :doc:`troubleshooting` for common issues and solutions
