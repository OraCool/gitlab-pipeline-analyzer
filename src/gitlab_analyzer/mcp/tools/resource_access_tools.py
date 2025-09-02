"""
Resource access tools for MCP server

Provides direct access to MCP resources without needing to re-run analysis.
This allows agents to retrieve cached pipeline data efficiently.

Copyright (c) 2025 Siarhei Skuratovich
Licensed under the MIT License - see LICENSE file for details
"""

import json
import logging
import time
from typing import Any

from fastmcp import FastMCP

from gitlab_analyzer.mcp.resources.analysis import get_analysis_resource_data
from gitlab_analyzer.mcp.resources.error import (
    get_error_resource_data,
    get_file_errors_resource_data,
    get_individual_error_data,
    get_pipeline_errors_resource_data,
)
from gitlab_analyzer.mcp.resources.file import (
    get_file_resource,
    get_file_resource_with_trace,
    get_files_resource,
    get_pipeline_files_resource,
)
from gitlab_analyzer.mcp.resources.job import (
    get_job_resource,
    get_pipeline_jobs_resource,
)
from gitlab_analyzer.mcp.resources.pipeline import get_pipeline_resource
from gitlab_analyzer.utils import get_mcp_info
from gitlab_analyzer.utils.debug import debug_print, verbose_debug_print, error_print

logger = logging.getLogger(__name__)


async def get_mcp_resource_impl(resource_uri: str) -> dict[str, Any]:
    """
    Implementation of get_mcp_resource that can be imported for testing.
    This is the same implementation as the @mcp.tool decorated version.
    """
    start_time = time.time()
    debug_print(f"🔗 Starting resource access for URI: {resource_uri}")

    # Store cleanup status to add to final response
    cleanup_status = {}

    try:
        verbose_debug_print("📋 Triggering automatic cache cleanup check...")
        # Trigger automatic cache cleanup if needed (runs in background)
        from gitlab_analyzer.cache.auto_cleanup import get_auto_cleanup_manager

        auto_cleanup = get_auto_cleanup_manager()
        cleanup_status = await auto_cleanup.trigger_cleanup_if_needed()
        verbose_debug_print(f"✅ Cleanup check completed: {cleanup_status}")

    except Exception as e:
        error_print(f"❌ Auto-cleanup failed during resource access: {e}")
        cleanup_status = {"status": "failed", "reason": str(e)}

    # Parse resource URI
    verbose_debug_print(f"🔍 Parsing resource URI: {resource_uri}")
    if not resource_uri.startswith("gl://"):
        error_print(
            f"❌ Invalid resource URI format - missing gl:// scheme: {resource_uri}"
        )
        return {
            "error": f"Invalid resource URI format: {resource_uri}",
            "mcp_info": get_mcp_info("get_mcp_resource", error=True),
            "auto_cleanup": cleanup_status,
        }

    try:
        # Remove the scheme and split the path
        path = resource_uri[5:]  # Remove "gl://"
        debug_print(f"📍 Extracted URI path: {path}")

        # Parse query parameters if present
        query_params = {}
        if "?" in path:
            path, query_string = path.split("?", 1)
            verbose_debug_print(f"🔧 Found query string: {query_string}")
            for param in query_string.split("&"):
                if "=" in param:
                    key, value = param.split("=", 1)
                    query_params[key] = value
            verbose_debug_print(f"📋 Parsed query parameters: {query_params}")

        debug_print(f"🎯 Final path for processing: {path}")

        # Handle different resource types
        if path.startswith("pipeline/"):
            debug_print("🏗️  Processing pipeline resource request")
            # Parse: gl://pipeline/83/123 -> project_id=83, pipeline_id=123
            parts = path.split("/")
            verbose_debug_print(f"📊 Pipeline URI parts: {parts}")
            if len(parts) >= 3:
                project_id = parts[1]
                pipeline_id = parts[2]
                debug_print(
                    f"🔍 Accessing pipeline {pipeline_id} in project {project_id}"
                )
                result = await get_pipeline_resource(project_id, pipeline_id)
                verbose_debug_print("✅ Pipeline resource retrieved successfully")
            else:
                error_print(
                    f"❌ Invalid pipeline URI format - insufficient parts: {resource_uri}"
                )
                return {
                    "error": f"Invalid pipeline URI format: {resource_uri}",
                    "mcp_info": get_mcp_info("get_mcp_resource", error=True),
                    "auto_cleanup": cleanup_status,
                }
        elif path.startswith("jobs/"):
            debug_print("👥 Processing jobs resource request")
            # Parse: gl://jobs/83/pipeline/123 or gl://jobs/83/pipeline/123/failed
            parts = path.split("/")
            verbose_debug_print(f"📊 Jobs URI parts: {parts}")
            if len(parts) >= 4 and parts[2] == "pipeline":
                project_id = parts[1]
                pipeline_id = parts[3]
                # Check for status filter (e.g., /failed)
                status = "all"
                if len(parts) > 4:
                    status = parts[4]  # e.g., "failed"
                debug_print(
                    f"🔍 Accessing jobs for pipeline {pipeline_id} in project {project_id} with status filter: {status}"
                )
                result = await get_pipeline_jobs_resource(
                    project_id, pipeline_id, status
                )
                verbose_debug_print("✅ Jobs resource retrieved successfully")
            else:
                error_print(
                    f"❌ Invalid jobs URI format - expected jobs/project/pipeline/id: {resource_uri}"
                )
                return {
                    "error": f"Invalid jobs URI format: {resource_uri}",
                    "mcp_info": get_mcp_info("get_mcp_resource", error=True),
                    "auto_cleanup": cleanup_status,
                }
        elif path.startswith("job/"):
            debug_print("🔧 Processing individual job resource request")
            # Parse: gl://job/83/123/456 -> project_id=83, pipeline_id=123, job_id=456
            parts = path.split("/")
            verbose_debug_print(f"📊 Job URI parts: {parts}")
            if len(parts) >= 4:
                project_id = parts[1]
                pipeline_id = parts[2]
                job_id = parts[3]
                debug_print(
                    f"🔍 Accessing job {job_id} in pipeline {pipeline_id} in project {project_id}"
                )
                result = await get_job_resource(project_id, pipeline_id, job_id)
                verbose_debug_print("✅ Job resource retrieved successfully")
            else:
                error_print(
                    f"❌ Invalid job URI format - expected job/project/pipeline/job: {resource_uri}"
                )
                return {
                    "error": f"Invalid job URI format: {resource_uri}",
                    "mcp_info": get_mcp_info("get_mcp_resource", error=True),
                    "auto_cleanup": cleanup_status,
                }
        elif path.startswith("files/"):
            debug_print("📁 Processing files resource request")
            # Parse: gl://files/83/pipeline/123 or gl://files/83/456
            parts = path.split("/")
            verbose_debug_print(f"📊 Files URI parts: {parts}")
            if len(parts) >= 3:
                project_id = parts[1]
                if len(parts) >= 4 and parts[2] == "pipeline":
                    # gl://files/83/pipeline/123 or gl://files/83/pipeline/123/page/2/limit/50
                    pipeline_id = parts[3]
                    # Check for pagination parameters from query string or path
                    page = int(query_params.get("page", 1))
                    limit = int(query_params.get("limit", 20))
                    # Also support path-based pagination for backward compatibility
                    if len(parts) >= 6 and parts[4] == "page":
                        page = int(parts[5])
                    if len(parts) >= 8 and parts[6] == "limit":
                        limit = int(parts[7])
                    debug_print(
                        f"🔍 Accessing pipeline files for pipeline {pipeline_id} in project {project_id} (page={page}, limit={limit})"
                    )
                    result = await get_pipeline_files_resource(
                        project_id, pipeline_id, page, limit
                    )
                    verbose_debug_print(
                        "✅ Pipeline files resource retrieved successfully"
                    )
                else:
                    # gl://files/83/456 (job files) - support query parameters
                    job_id = parts[2]
                    page = int(query_params.get("page", 1))
                    limit = int(query_params.get("limit", 20))
                    debug_print(
                        f"🔍 Accessing job files for job {job_id} in project {project_id} (page={page}, limit={limit})"
                    )
                    result = await get_files_resource(project_id, job_id, page, limit)
                    verbose_debug_print("✅ Job files resource retrieved successfully")
            else:
                error_print(
                    f"❌ Invalid files URI format - insufficient parts: {resource_uri}"
                )
                return {
                    "error": f"Invalid files URI format: {resource_uri}",
                    "mcp_info": get_mcp_info("get_mcp_resource", error=True),
                    "auto_cleanup": cleanup_status,
                }
        elif path.startswith("file/"):
            debug_print("📄 Processing individual file resource request")
            # Parse: gl://file/83/456/src/main.py or gl://file/83/456/src/main.py/trace?...
            parts = path.split("/")
            verbose_debug_print(f"📊 File URI parts: {parts}")
            if len(parts) >= 5:
                project_id = parts[1]
                job_id = parts[2]
                file_path = "/".join(parts[3:])
                debug_print(
                    f"🔍 Accessing file '{file_path}' in job {job_id} in project {project_id}"
                )

                # Check if it's a trace request
                if "/trace?" in file_path:
                    verbose_debug_print("🔍 Detected trace request in file URI")
                    # Parse trace parameters: src/main.py/trace?mode=detailed&include_trace=true
                    file_parts = file_path.split("/trace?")
                    actual_file_path = file_parts[0]
                    debug_print(f"📁 Actual file path: {actual_file_path}")

                    # Parse query parameters
                    mode = "balanced"
                    include_trace = "false"
                    if len(file_parts) > 1:
                        trace_query_params = file_parts[1]
                        verbose_debug_print(
                            f"🔧 Trace query params: {trace_query_params}"
                        )
                        for param in trace_query_params.split("&"):
                            if "=" in param:
                                key, value = param.split("=", 1)
                                if key == "mode":
                                    mode = value
                                elif key == "include_trace":
                                    include_trace = value
                    debug_print(
                        f"⚙️ Trace options: mode={mode}, include_trace={include_trace}"
                    )

                    # The function returns TextResourceContents, so we need to handle it differently
                    trace_result = await get_file_resource_with_trace(
                        project_id, job_id, actual_file_path, mode, include_trace
                    )
                    # Convert TextResourceContents to dict for consistency
                    result = json.loads(trace_result.text)
                    verbose_debug_print(
                        "✅ File resource with trace retrieved successfully"
                    )
                else:
                    result = await get_file_resource(project_id, job_id, file_path)
                    verbose_debug_print("✅ File resource retrieved successfully")
            else:
                error_print(
                    f"❌ Invalid file URI format - expected file/project/job/path: {resource_uri}"
                )
                return {
                    "error": f"Invalid file URI format: {resource_uri}",
                    "mcp_info": get_mcp_info("get_mcp_resource", error=True),
                    "auto_cleanup": cleanup_status,
                }
        elif path.startswith("error/"):
            debug_print("⚠️  Processing error resource request")
            # Parse: gl://error/83/456 or gl://error/83/456/123_0 or gl://error/83/456?mode=detailed
            parts = path.split("/")
            verbose_debug_print(f"📊 Error URI parts: {parts}")
            if len(parts) >= 3:
                project_id = parts[1]
                job_id_with_query = parts[2]

                # Parse query parameters
                mode = "balanced"
                if "?" in job_id_with_query:
                    job_id, query_string = job_id_with_query.split("?", 1)
                    verbose_debug_print(f"🔧 Error query params: {query_string}")
                    for param in query_string.split("&"):
                        if "=" in param:
                            key, value = param.split("=", 1)
                            if key == "mode":
                                mode = value
                else:
                    job_id = job_id_with_query

                if len(parts) >= 4:
                    # gl://error/83/456/123_0
                    error_id = parts[3]
                    debug_print(
                        f"🔍 Accessing individual error {error_id} in job {job_id} in project {project_id} (mode={mode})"
                    )
                    result = await get_individual_error_data(
                        project_id, job_id, error_id, mode
                    )
                    verbose_debug_print(
                        "✅ Individual error resource retrieved successfully"
                    )
                else:
                    # gl://error/83/456
                    debug_print(
                        f"🔍 Accessing all errors in job {job_id} in project {project_id} (mode={mode})"
                    )
                    result = await get_error_resource_data(project_id, job_id, mode)
                    verbose_debug_print("✅ Job errors resource retrieved successfully")
            else:
                error_print(
                    f"❌ Invalid error URI format - expected error/project/job: {resource_uri}"
                )
                return {
                    "error": f"Invalid error URI format: {resource_uri}",
                    "mcp_info": get_mcp_info("get_mcp_resource", error=True),
                    "auto_cleanup": cleanup_status,
                }
        elif path.startswith("errors/"):
            debug_print("⚠️📋 Processing errors collection resource request")
            # Parse: gl://errors/83/pipeline/123 or gl://errors/83/456/src/main.py
            parts = path.split("/")
            verbose_debug_print(f"📊 Errors URI parts: {parts}")
            if len(parts) >= 3:
                project_id = parts[1]
                if len(parts) >= 4 and parts[2] == "pipeline":
                    # gl://errors/83/pipeline/123
                    pipeline_id = parts[3]
                    debug_print(
                        f"🔍 Accessing pipeline errors for pipeline {pipeline_id} in project {project_id}"
                    )
                    result = await get_pipeline_errors_resource_data(
                        project_id, pipeline_id
                    )
                    verbose_debug_print(
                        "✅ Pipeline errors resource retrieved successfully"
                    )
                else:
                    # gl://errors/83/456/src/main.py
                    job_id = parts[2]
                    file_path = "/".join(parts[3:]) if len(parts) > 3 else ""
                    if file_path:
                        debug_print(
                            f"🔍 Accessing file-specific errors for '{file_path}' in job {job_id} in project {project_id}"
                        )
                    else:
                        debug_print(
                            f"🔍 Accessing all errors in job {job_id} in project {project_id}"
                        )
                    result = await get_file_errors_resource_data(
                        project_id, job_id, file_path
                    )
                    verbose_debug_print(
                        "✅ Job/file errors resource retrieved successfully"
                    )
            else:
                error_print(
                    f"❌ Invalid errors URI format - expected errors/project/...: {resource_uri}"
                )
                return {
                    "error": f"Invalid errors URI format: {resource_uri}",
                    "mcp_info": get_mcp_info("get_mcp_resource", error=True),
                    "auto_cleanup": cleanup_status,
                }
        elif path.startswith("analysis/"):
            debug_print("📊 Processing analysis resource request")
            # Parse: gl://analysis/83, gl://analysis/83/pipeline/123, gl://analysis/83/job/456
            parts = path.split("/")
            verbose_debug_print(f"📊 Analysis URI parts: {parts}")
            if len(parts) >= 2:
                project_id = parts[1]
                pipeline_id = None
                job_id = None
                mode = "balanced"

                # Parse additional path components
                if len(parts) >= 4:
                    if parts[2] == "pipeline":
                        # gl://analysis/83/pipeline/123?mode=detailed
                        pipeline_id_with_query = parts[3]
                        if "?" in pipeline_id_with_query:
                            pipeline_id, query_string = pipeline_id_with_query.split(
                                "?", 1
                            )
                            verbose_debug_print(
                                f"🔧 Analysis query params: {query_string}"
                            )
                            for param in query_string.split("&"):
                                if "=" in param:
                                    key, value = param.split("=", 1)
                                    if key == "mode":
                                        mode = value
                        else:
                            pipeline_id = pipeline_id_with_query
                        debug_print(
                            f"🔍 Accessing pipeline analysis for pipeline {pipeline_id} in project {project_id} (mode={mode})"
                        )
                    elif parts[2] == "job":
                        # gl://analysis/83/job/456?mode=minimal
                        job_id_with_query = parts[3]
                        if "?" in job_id_with_query:
                            job_id, query_string = job_id_with_query.split("?", 1)
                            verbose_debug_print(
                                f"🔧 Analysis query params: {query_string}"
                            )
                            for param in query_string.split("&"):
                                if "=" in param:
                                    key, value = param.split("=", 1)
                                    if key == "mode":
                                        mode = value
                        else:
                            job_id = job_id_with_query
                        debug_print(
                            f"🔍 Accessing job analysis for job {job_id} in project {project_id} (mode={mode})"
                        )
                else:
                    debug_print(
                        f"🔍 Accessing project analysis for project {project_id} (mode={mode})"
                    )

                result = await get_analysis_resource_data(
                    project_id, pipeline_id, job_id, mode
                )
                verbose_debug_print("✅ Analysis resource retrieved successfully")
            else:
                error_print(
                    f"❌ Invalid analysis URI format - expected analysis/project: {resource_uri}"
                )
                return {
                    "error": f"Invalid analysis URI format: {resource_uri}",
                    "mcp_info": get_mcp_info("get_mcp_resource", error=True),
                    "auto_cleanup": cleanup_status,
                }
        else:
            error_print(f"❌ Unsupported resource URI pattern: {resource_uri}")
            return {
                "error": f"Unsupported resource URI pattern: {resource_uri}",
                "mcp_info": get_mcp_info("get_mcp_resource", error=True),
                "auto_cleanup": cleanup_status,
                "available_patterns": [
                    "gl://pipeline/{project_id}/{pipeline_id}",
                    "gl://jobs/{project_id}/pipeline/{pipeline_id}[/failed|/success]",
                    "gl://job/{project_id}/{pipeline_id}/{job_id}",
                    "gl://files/{project_id}/pipeline/{pipeline_id}[/page/{page}/limit/{limit}]",
                    "gl://files/{project_id}/{job_id}[/page/{page}/limit/{limit}]",
                    "gl://file/{project_id}/{job_id}/{file_path}",
                    "gl://file/{project_id}/{job_id}/{file_path}/trace?mode={mode}&include_trace={trace}",
                    "gl://error/{project_id}/{job_id}[?mode={mode}]",
                    "gl://error/{project_id}/{job_id}/{error_id}",
                    "gl://errors/{project_id}/{job_id}",
                    "gl://errors/{project_id}/{job_id}/{file_path}",
                    "gl://errors/{project_id}/pipeline/{pipeline_id}",
                    "gl://analysis/{project_id}[?mode={mode}]",
                    "gl://analysis/{project_id}/pipeline/{pipeline_id}[?mode={mode}]",
                    "gl://analysis/{project_id}/job/{job_id}[?mode={mode}]",
                ],
            }

        # Add auto-cleanup status to the result
        if isinstance(result, dict):
            result["auto_cleanup"] = cleanup_status

        # Add timing information
        end_time = time.time()
        duration = end_time - start_time
        verbose_debug_print(f"⏱️ Resource access completed in {duration:.3f}s")
        if isinstance(result, dict):
            result["debug_timing"] = {"duration_seconds": round(duration, 3)}

        debug_print(f"✅ Resource access completed successfully for {resource_uri}")
        return result

    except Exception as e:
        end_time = time.time()
        duration = end_time - start_time
        error_print(
            f"❌ Error accessing resource {resource_uri} after {duration:.3f}s: {e}"
        )
        return {
            "error": f"Failed to access resource: {str(e)}",
            "mcp_info": get_mcp_info("get_mcp_resource", error=True),
            "auto_cleanup": cleanup_status,
            "resource_uri": resource_uri,
            "debug_timing": {"duration_seconds": round(duration, 3)},
        }


# Create an alias for backward compatibility
get_mcp_resource = get_mcp_resource_impl


def register_resource_access_tools(mcp: FastMCP) -> None:
    """Register resource access tools with MCP server"""

    @mcp.tool
    async def get_mcp_resource(resource_uri: str) -> dict[str, Any]:
        """
        🔗 RESOURCE ACCESS: Get data from MCP resource URI without re-running analysis.

        WHEN TO USE:
        - Access previously analyzed pipeline data
        - Retrieve cached results efficiently
        - Navigate between related resources
        - Avoid unnecessary re-analysis

        SUPPORTED RESOURCE PATTERNS:
        - gl://pipeline/{project_id}/{pipeline_id} - Pipeline analysis
        - gl://jobs/{project_id}/pipeline/{pipeline_id}[/failed|/success] - Pipeline jobs
        - gl://job/{project_id}/{pipeline_id}/{job_id} - Individual job analysis
        - gl://files/{project_id}/pipeline/{pipeline_id}[/page/{page}/limit/{limit}] - Pipeline files
        - gl://files/{project_id}/{job_id}[/page/{page}/limit/{limit}] - Job files
        - gl://file/{project_id}/{job_id}/{file_path} - Specific file analysis
        - gl://file/{project_id}/{job_id}/{file_path}/trace?mode={mode}&include_trace={trace} - File with trace
        - gl://error/{project_id}/{job_id} - Job-specific error analysis
        - gl://error/{project_id}/{job_id}?mode={mode} - Job errors with mode
        - gl://error/{project_id}/{job_id}/{error_id} - Individual error details
        - gl://errors/{project_id}/{job_id} - All errors in job
        - gl://errors/{project_id}/{job_id}/{file_path} - File-specific errors
        - gl://errors/{project_id}/pipeline/{pipeline_id} - Pipeline-wide errors
        - gl://error/{project_id}/{job_id}/{error_id} - Specific error details
        - gl://analysis/{project_id}[?mode={mode}] - Project-level analysis
        - gl://analysis/{project_id}/pipeline/{pipeline_id}[?mode={mode}] - Pipeline analysis
        - gl://analysis/{project_id}/job/{job_id}[?mode={mode}] - Job analysis        RESOURCE FEATURES:
        - Uses cached data for fast response
        - Includes navigation links to related resources
        - Provides summary statistics and metadata
        - Filters data based on resource type

        Args:
            resource_uri: The MCP resource URI (e.g., "gl://jobs/83/pipeline/1594344/failed")

        Returns:
            Resource data with navigation links and metadata

        EXAMPLES:
        - get_mcp_resource("gl://jobs/83/pipeline/1594344/failed") - Get failed jobs
        - get_mcp_resource("gl://pipeline/83/1594344") - Get pipeline analysis
        - get_mcp_resource("gl://files/83/pipeline/1594344") - Get files with errors
        - get_mcp_resource("gl://error/83/76474172") - Get job error analysis
        - get_mcp_resource("gl://errors/83/76474172/src/main.py") - Get file-specific errors
        - get_mcp_resource("gl://errors/83/pipeline/1594344") - Get pipeline-wide errors
        - get_mcp_resource("gl://file/83/76474172/src/main.py/trace?mode=detailed&include_trace=true") - Get file with traceback
        - get_mcp_resource("gl://analysis/83/pipeline/1594344?mode=detailed") - Detailed analysis
        - get_mcp_resource("gl://file/83/76474172/src/main.py") - Specific file analysis
        """
        # Delegate to the implementation function
        return await get_mcp_resource_impl(resource_uri)

        # try:
        #     # Trigger automatic cache cleanup if needed (runs in background)
        #     from gitlab_analyzer.cache.auto_cleanup import get_auto_cleanup_manager

        #     auto_cleanup = get_auto_cleanup_manager()
        #     cleanup_status = await auto_cleanup.trigger_cleanup_if_needed()

        #     logger.info(f"Accessing MCP resource: {resource_uri}")
        #     if cleanup_status["cleanup_triggered"]:
        #         logger.info(
        #             f"🧹 Background cache cleanup triggered (max_age: {cleanup_status['max_age_hours']}h)"
        #         )

        #     # Parse the resource URI
        #     if not resource_uri.startswith("gl://"):
        #         raise ValueError(f"Invalid resource URI format: {resource_uri}")

        #     uri_path = resource_uri[5:]  # Remove "gl://" prefix

        #     # Store the result to add cleanup status later
        #     result = None

        #     # Pipeline analysis: gl://pipeline/{project_id}/{pipeline_id}
        #     pipeline_match = re.match(r"^pipeline/(\w+)/(\d+)$", uri_path)
        #     if pipeline_match:
        #         project_id, pipeline_id = pipeline_match.groups()
        #         result = await get_pipeline_resource(project_id, pipeline_id)
        #         # Add auto-cleanup status to result
        #         if isinstance(result, dict):
        #             result["auto_cleanup"] = cleanup_status
        #         return result

        #     # Pipeline jobs: gl://jobs/{project_id}/pipeline/{pipeline_id}[/status]
        #     jobs_match = re.match(
        #         r"^jobs/(\w+)/pipeline/(\d+)(?:/(failed|success|all))?$", uri_path
        #     )
        #     if jobs_match:
        #         project_id, pipeline_id, status_filter = jobs_match.groups()
        #         status_filter = status_filter or "all"
        #         result = await get_pipeline_jobs_resource(
        #             project_id, pipeline_id, status_filter
        #         )
        #         # Add auto-cleanup status to result
        #         if isinstance(result, dict):
        #             result["auto_cleanup"] = cleanup_status
        #         return result

        #     # Individual job: gl://job/{project_id}/{pipeline_id}/{job_id}
        #     job_match = re.match(r"^job/(\w+)/(\d+)/(\d+)$", uri_path)
        #     if job_match:
        #         project_id, pipeline_id, job_id = job_match.groups()
        #         return await get_job_resource(project_id, pipeline_id, job_id)

        #     # Pipeline files: gl://files/{project_id}/pipeline/{pipeline_id}[/page/{page}/limit/{limit}]
        #     pipeline_files_match = re.match(
        #         r"^files/(\w+)/pipeline/(\d+)(?:/page/(\d+)/limit/(\d+))?$", uri_path
        #     )
        #     if pipeline_files_match:
        #         project_id, pipeline_id, page, limit = pipeline_files_match.groups()
        #         page = int(page) if page else 1
        #         limit = int(limit) if limit else 20
        #         return await get_pipeline_files_resource(
        #             project_id, pipeline_id, page, limit
        #         )

        #     # Job files: gl://files/{project_id}/{job_id}[/page/{page}/limit/{limit}]
        #     job_files_match = re.match(
        #         r"^files/(\w+)/(\d+)(?:/page/(\d+)/limit/(\d+))?$", uri_path
        #     )
        #     if job_files_match:
        #         project_id, job_id, page, limit = job_files_match.groups()
        #         return await get_file_resource(
        #             project_id, job_id, ""
        #         )  # Empty file_path for all files

        #     # Specific file: gl://file/{project_id}/{job_id}/{file_path}
        #     file_match = re.match(r"^file/(\w+)/(\d+)/(.+)$", uri_path)
        #     if file_match:
        #         project_id, job_id, file_path = file_match.groups()
        #         # Check if it's a trace request
        #         if "/trace?" in file_path:
        #             # Parse trace parameters: file_path/trace?mode=X&include_trace=Y
        #             trace_match = re.match(r"^(.+)/trace\?(.+)$", file_path)
        #             if trace_match:
        #                 actual_file_path, params = trace_match.groups()
        #                 # Parse query parameters
        #                 params_dict = {}
        #                 for param in params.split("&"):
        #                     if "=" in param:
        #                         key, value = param.split("=", 1)
        #                         params_dict[key] = value

        #                 mode = params_dict.get("mode", "balanced")
        #                 include_trace_str = params_dict.get(
        #                     "include_trace", "true"
        #                 ).lower()

        #                 return await get_file_resource_with_trace(  # type: ignore
        #                     project_id,
        #                     job_id,
        #                     actual_file_path,
        #                     mode,
        #                     include_trace_str,
        #                 )

        #         # Regular file request
        #         return await get_file_resource(project_id, job_id, file_path)

        #     # Job errors: gl://error/{project_id}/{job_id}[?mode={mode}] or gl://error/{project_id}/{job_id}/{error_id}
        #     error_match = re.match(
        #         r"^error/(\w+)/(\d+)(?:/([^/?]+))?(?:\?mode=(\w+))?$", uri_path
        #     )
        #     if error_match:
        #         project_id, job_id, error_id, mode = error_match.groups()
        #         mode = mode or "balanced"

        #         if error_id:
        #             # Individual error - use the dedicated function
        #             return await get_individual_error_data(
        #                 project_id, job_id, error_id, mode
        #             )
        #         else:
        #             # All job errors
        #             return await get_error_resource_data(project_id, job_id, mode)

        #     # New error patterns: gl://errors/{project_id}/{job_id}[/{file_path}] or gl://errors/{project_id}/pipeline/{pipeline_id}
        #     errors_match = re.match(
        #         r"^errors/(\w+)/(?:(\d+)(?:/(.+))?|pipeline/(\d+))$", uri_path
        #     )
        #     if errors_match:
        #         project_id, job_id, file_path, pipeline_id = errors_match.groups()

        #         if pipeline_id:
        #             # Pipeline errors: gl://errors/{project_id}/pipeline/{pipeline_id}
        #             return await get_pipeline_errors_resource_data(
        #                 project_id, pipeline_id
        #             )
        #         elif file_path:
        #             # File-specific errors: gl://errors/{project_id}/{job_id}/{file_path}
        #             return await get_file_errors_resource_data(
        #                 project_id, job_id, file_path
        #             )
        #         else:
        #             # All job errors: gl://errors/{project_id}/{job_id}
        #             return await get_error_resource_data(project_id, job_id, "balanced")

        #     # Analysis resources: gl://analysis/{project_id}[/pipeline/{pipeline_id}|/job/{job_id}][?mode={mode}]
        #     analysis_match = re.match(
        #         r"^analysis/(\w+)(?:/(?:(pipeline)/(\d+)|(job)/(\d+)))?(?:\?mode=(\w+))?$",
        #         uri_path,
        #     )
        #     if analysis_match:
        #         project_id, pipeline_type, pipeline_id, job_type, job_id, mode = (
        #             analysis_match.groups()
        #         )
        #         mode = mode or "balanced"

        #         if pipeline_type and pipeline_id:
        #             # Pipeline analysis
        #             return await get_analysis_resource_data(
        #                 project_id, pipeline_id, None, mode
        #             )
        #         elif job_type and job_id:
        #             # Job analysis
        #             return await get_analysis_resource_data(
        #                 project_id, None, job_id, mode
        #             )
        #         else:
        #             # Project analysis
        #             return await get_analysis_resource_data(
        #                 project_id, None, None, mode
        #             )

        #     # If no pattern matches
        #     raise ValueError(f"Unsupported resource URI pattern: {resource_uri}")

        # except Exception as e:
        # logger.error(f"Error accessing resource {resource_uri}: {e}")
        # return {
        #     "error": f"Failed to access resource: {str(e)}",
        #     "resource_uri": resource_uri,
        #     "available_patterns": [
        #         "gl://pipeline/{project_id}/{pipeline_id}",
        #         "gl://jobs/{project_id}/pipeline/{pipeline_id}[/failed|/success]",
        #         "gl://job/{project_id}/{pipeline_id}/{job_id}",
        #         "gl://files/{project_id}/pipeline/{pipeline_id}[/page/{page}/limit/{limit}]",
        #         "gl://files/{project_id}/{job_id}[/page/{page}/limit/{limit}]",
        #         "gl://file/{project_id}/{job_id}/{file_path}",
        #         "gl://file/{project_id}/{job_id}/{file_path}/trace?mode={mode}&include_trace={trace}",
        #         "gl://error/{project_id}/{job_id}[?mode={mode}]",
        #         "gl://error/{project_id}/{job_id}/{error_id}",
        #         "gl://errors/{project_id}/{job_id}",
        #         "gl://errors/{project_id}/{job_id}/{file_path}",
        #         "gl://errors/{project_id}/pipeline/{pipeline_id}",
        #         "gl://analysis/{project_id}[?mode={mode}]",
        #         "gl://analysis/{project_id}/pipeline/{pipeline_id}[?mode={mode}]",
        #         "gl://analysis/{project_id}/job/{job_id}[?mode={mode}]",
        #     ],
        # }

    debug_print("🔗 Resource access tools registered successfully")
