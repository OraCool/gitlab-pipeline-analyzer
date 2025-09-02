"""
Resource access tools for MCP server

Provides direct access to MCP resources without needing to re-run analysis.
This allows agents to retrieve cached pipeline data efficiently.

URL Encoding for File Paths:
File paths in URIs should be URL-encoded to handle special characters,
spaces, and Unicode characters properly. For example:
- "src/main.py" becomes "src%2Fmain.py"
- "path with spaces/file.py" becomes "path%20with%20spaces%2Ffile.py"

Copyright (c) 2025 Siarhei Skuratovich
Licensed under the MIT License - see LICENSE file for details
"""

import json
import logging
import time
from typing import Any
from urllib.parse import unquote

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
from gitlab_analyzer.utils.debug import debug_print, error_print, verbose_debug_print

logger = logging.getLogger(__name__)


def _parse_resource_uri(resource_uri: str) -> tuple[str, dict[str, str]]:
    """Parse resource URI into path and query parameters."""
    if not resource_uri.startswith("gl://"):
        raise ValueError(f"Invalid resource URI format: {resource_uri}")

    # Remove the scheme and split the path
    path = resource_uri[5:]  # Remove "gl://"

    # Parse query parameters if present
    query_params = {}
    if "?" in path:
        path, query_string = path.split("?", 1)
        verbose_debug_print(f"🔧 Found query string: {query_string}")
        for param in query_string.split("&"):
            if "=" in param:
                key, value = param.split("=", 1)
                query_params[key] = value

    return path, query_params


def _parse_file_path(file_path: str) -> tuple[str, bool]:
    """
    Parse file path to extract actual file path and detect trace requests.

    Returns:
        tuple: (actual_file_path, is_trace_request)
    """
    # First decode the entire path to handle URL encoding properly
    decoded_file_path = unquote(file_path)

    # Check if it's a trace request - look for either /trace? or ending with /trace
    if "/trace?" in decoded_file_path:
        # Parse trace parameters: src/main.py/trace?mode=detailed&include_trace=true
        file_parts = decoded_file_path.split("/trace?")
        actual_file_path = file_parts[0]  # Already decoded
        return actual_file_path, True
    elif decoded_file_path.endswith("/trace"):
        # Remove the /trace suffix
        actual_file_path = decoded_file_path[:-6]  # Remove "/trace"
        return actual_file_path, True
    else:
        return decoded_file_path, False


async def _handle_pipeline_resource(parts: list[str]) -> dict[str, Any]:
    """Handle pipeline resource requests."""
    if len(parts) >= 3:
        project_id = parts[1]
        pipeline_id = parts[2]
        debug_print(f"🔍 Accessing pipeline {pipeline_id} in project {project_id}")
        result = await get_pipeline_resource(project_id, pipeline_id)
        verbose_debug_print("✅ Pipeline resource retrieved successfully")
        return result
    else:
        raise ValueError("Invalid pipeline URI format - insufficient parts")


async def _handle_jobs_resource(parts: list[str]) -> dict[str, Any]:
    """Handle jobs resource requests."""
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
        result = await get_pipeline_jobs_resource(project_id, pipeline_id, status)
        verbose_debug_print("✅ Jobs resource retrieved successfully")
        return result
    else:
        raise ValueError("Invalid jobs URI format - expected jobs/project/pipeline/id")


async def _handle_job_resource(parts: list[str]) -> dict[str, Any]:
    """Handle individual job resource requests."""
    if len(parts) >= 4:
        project_id = parts[1]
        pipeline_id = parts[2]
        job_id = parts[3]
        debug_print(
            f"🔍 Accessing job {job_id} in pipeline {pipeline_id} in project {project_id}"
        )
        result = await get_job_resource(project_id, pipeline_id, job_id)
        verbose_debug_print("✅ Job resource retrieved successfully")
        return result
    else:
        raise ValueError("Invalid job URI format - expected job/project/pipeline/job")


async def _handle_files_resource(
    parts: list[str], query_params: dict[str, str]
) -> dict[str, Any]:
    """Handle files resource requests."""
    if len(parts) >= 3:
        project_id = parts[1]
        if len(parts) >= 4 and parts[2] == "pipeline":
            # gl://files/123/pipeline/123 or gl://files/123/pipeline/123/page/2/limit/50
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
            verbose_debug_print("✅ Pipeline files resource retrieved successfully")
            return result
        else:
            # gl://files/123/456 (job files) - support query parameters
            job_id = parts[2]
            page = int(query_params.get("page", 1))
            limit = int(query_params.get("limit", 20))
            debug_print(
                f"🔍 Accessing job files for job {job_id} in project {project_id} (page={page}, limit={limit})"
            )
            result = await get_files_resource(project_id, job_id, page, limit)
            verbose_debug_print("✅ Job files resource retrieved successfully")
            return result
    else:
        raise ValueError("Invalid files URI format - insufficient parts")


async def _handle_file_resource(
    parts: list[str], query_params: dict[str, str]
) -> dict[str, Any]:
    """Handle individual file resource requests."""
    if len(parts) >= 5:
        project_id = parts[1]
        job_id = parts[2]
        file_path = "/".join(parts[3:])
        debug_print(
            f"🔍 Accessing file '{file_path}' in job {job_id} in project {project_id}"
        )

        # Parse file path and check for trace request
        actual_file_path, is_trace_request = _parse_file_path(file_path)
        debug_print(f"📁 Actual file path: {actual_file_path}")

        if is_trace_request:
            verbose_debug_print("🔍 Detected trace request in file URI")

            # Get query parameters for trace
            mode = query_params.get("mode", "balanced")
            include_trace = query_params.get("include_trace", "false")
            debug_print(f"⚙️ Trace options: mode={mode}, include_trace={include_trace}")

            # The function returns TextResourceContents, so we need to handle it differently
            trace_result = await get_file_resource_with_trace(
                project_id, job_id, actual_file_path, mode, include_trace
            )
            # Convert TextResourceContents to dict for consistency
            result = json.loads(trace_result.text)
            verbose_debug_print("✅ File resource with trace retrieved successfully")
            return result
        else:
            result = await get_file_resource(project_id, job_id, actual_file_path)
            verbose_debug_print("✅ File resource retrieved successfully")
            return result
    else:
        raise ValueError("Invalid file URI format - expected file/project/job/path")


async def _handle_error_resource(
    parts: list[str], query_params: dict[str, str]
) -> dict[str, Any]:
    """Handle error resource requests."""
    if len(parts) >= 3:
        project_id = parts[1]
        job_id = parts[2]

        # Use global query parameters for mode
        mode = query_params.get("mode", "balanced")

        if len(parts) >= 4:
            # gl://error/123/456/123_0
            error_id = parts[3]
            debug_print(
                f"🔍 Accessing individual error {error_id} in job {job_id} in project {project_id} (mode={mode})"
            )
            result = await get_individual_error_data(project_id, job_id, error_id, mode)
            verbose_debug_print("✅ Individual error resource retrieved successfully")
            return result
        else:
            # gl://error/123/456
            debug_print(
                f"🔍 Accessing all errors in job {job_id} in project {project_id} (mode={mode})"
            )
            result = await get_error_resource_data(project_id, job_id, mode)
            verbose_debug_print("✅ Job errors resource retrieved successfully")
            return result
    else:
        raise ValueError("Invalid error URI format - expected error/project/job")


async def _handle_errors_resource(parts: list[str]) -> dict[str, Any]:
    """Handle errors collection resource requests."""
    if len(parts) >= 3:
        project_id = parts[1]
        if len(parts) >= 4 and parts[2] == "pipeline":
            # gl://errors/123/pipeline/123
            pipeline_id = parts[3]
            debug_print(
                f"🔍 Accessing pipeline errors for pipeline {pipeline_id} in project {project_id}"
            )
            result = await get_pipeline_errors_resource_data(project_id, pipeline_id)
            verbose_debug_print("✅ Pipeline errors resource retrieved successfully")
            return result
        else:
            # gl://errors/123/456/src/main.py
            job_id = parts[2]
            file_path = "/".join(parts[3:]) if len(parts) > 3 else ""
            # URL decode the file path
            if file_path:
                file_path = unquote(file_path)
                debug_print(
                    f"🔍 Accessing file-specific errors for '{file_path}' in job {job_id} in project {project_id}"
                )
            else:
                debug_print(
                    f"🔍 Accessing all errors in job {job_id} in project {project_id}"
                )
            result = await get_file_errors_resource_data(project_id, job_id, file_path)
            verbose_debug_print("✅ Job/file errors resource retrieved successfully")
            return result
    else:
        raise ValueError("Invalid errors URI format - expected errors/project/...")


async def _handle_analysis_resource(
    parts: list[str], query_params: dict[str, str]
) -> dict[str, Any]:
    """Handle analysis resource requests."""
    if len(parts) >= 2:
        project_id = parts[1]
        pipeline_id = None
        job_id = None
        mode = query_params.get("mode", "balanced")

        # Parse additional path components
        if len(parts) >= 4:
            if parts[2] == "pipeline":
                # gl://analysis/123/pipeline/123?mode=detailed
                pipeline_id = parts[3]
                debug_print(
                    f"🔍 Accessing pipeline analysis for pipeline {pipeline_id} in project {project_id} (mode={mode})"
                )
            elif parts[2] == "job":
                # gl://analysis/123/job/456?mode=minimal
                job_id = parts[3]
                debug_print(
                    f"🔍 Accessing job analysis for job {job_id} in project {project_id} (mode={mode})"
                )
        else:
            debug_print(
                f"🔍 Accessing project analysis for project {project_id} (mode={mode})"
            )

        result = await get_analysis_resource_data(project_id, pipeline_id, job_id, mode)
        verbose_debug_print("✅ Analysis resource retrieved successfully")
        return result
    else:
        raise ValueError("Invalid analysis URI format - expected analysis/project")


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

    try:
        path, query_params = _parse_resource_uri(resource_uri)
        verbose_debug_print(f"📋 Parsed query parameters: {query_params}")
        debug_print(f"🎯 Final path for processing: {path}")

        # Split path into parts for routing
        parts = path.split("/")
        verbose_debug_print(f"📊 URI parts: {parts}")

        # Route to appropriate handler based on resource type
        if path.startswith("pipeline/"):
            debug_print("🏗️  Processing pipeline resource request")
            result = await _handle_pipeline_resource(parts)
        elif path.startswith("jobs/"):
            debug_print("👥 Processing jobs resource request")
            result = await _handle_jobs_resource(parts)
        elif path.startswith("job/"):
            debug_print("🔧 Processing individual job resource request")
            result = await _handle_job_resource(parts)
        elif path.startswith("files/"):
            debug_print("📁 Processing files resource request")
            result = await _handle_files_resource(parts, query_params)
        elif path.startswith("file/"):
            debug_print("📄 Processing individual file resource request")
            result = await _handle_file_resource(parts, query_params)
        elif path.startswith("error/"):
            debug_print("⚠️  Processing error resource request")
            result = await _handle_error_resource(parts, query_params)
        elif path.startswith("errors/"):
            debug_print("⚠️📋 Processing errors collection resource request")
            result = await _handle_errors_resource(parts)
        elif path.startswith("analysis/"):
            debug_print("📊 Processing analysis resource request")
            result = await _handle_analysis_resource(parts, query_params)
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

    except ValueError as e:
        # Handle URI parsing errors specifically
        error_print(f"❌ Resource URI parsing error: {e}")
        return {
            "error": str(e),
            "mcp_info": get_mcp_info("get_mcp_resource", error=True),
            "auto_cleanup": cleanup_status,
        }
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
        - gl://analysis/{project_id}/job/{job_id}[?mode={mode}] - Job analysis

        RESOURCE FEATURES:
        - Uses cached data for fast response
        - Includes navigation links to related resources
        - Provides summary statistics and metadata
        - Filters data based on resource type

        Args:
            resource_uri: The MCP resource URI (e.g., "gl://jobs/123/pipeline/1594344/failed")

        Returns:
            Resource data with navigation links and metadata

        EXAMPLES:
        - get_mcp_resource("gl://jobs/123/pipeline/1594344/failed") - Get failed jobs
        - get_mcp_resource("gl://pipeline/123/1594344") - Get pipeline analysis
        - get_mcp_resource("gl://files/123/pipeline/1594344") - Get files with errors
        - get_mcp_resource("gl://error/123/76474172") - Get job error analysis
        - get_mcp_resource("gl://errors/123/76474172/src/main.py") - Get file-specific errors
        - get_mcp_resource("gl://errors/123/pipeline/1594344") - Get pipeline-wide errors
        - get_mcp_resource("gl://file/123/76474172/src/main.py/trace?mode=detailed&include_trace=true") - Get file with traceback
        - get_mcp_resource("gl://analysis/123/pipeline/1594344?mode=detailed") - Detailed analysis
        - get_mcp_resource("gl://file/123/76474172/src/main.py") - Specific file analysis
        """
        # Delegate to the implementation function
        return await get_mcp_resource_impl(resource_uri)

    debug_print("🔗 Resource access tools registered successfully")
