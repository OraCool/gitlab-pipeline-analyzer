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

import logging
import time
from typing import Any
from urllib.parse import unquote

from fastmcp import FastMCP

from gitlab_analyzer.mcp.resources.analysis import get_analysis_resource_data
from gitlab_analyzer.mcp.resources.job import (
    get_job_resource,
    get_pipeline_jobs_resource,
)
from gitlab_analyzer.mcp.resources.merge_request import get_merge_request_resource
from gitlab_analyzer.mcp.resources.pipeline import get_pipeline_resource
from gitlab_analyzer.mcp.services.error_service import error_service
from gitlab_analyzer.mcp.services.file_analysis_service import get_file_analysis_service
from gitlab_analyzer.mcp.services.file_service import get_file_service
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


def _parse_file_path(file_path: str) -> tuple[str, str]:
    """
    Parse file path to extract actual file path and detect special requests.

    Returns:
        tuple: (actual_file_path, request_type)
        request_type can be: "normal", "trace", "jobs"
    """
    # First decode the entire path to handle URL encoding properly
    decoded_file_path = unquote(file_path)

    # Check for special endpoints
    if "/jobs?" in decoded_file_path or decoded_file_path.endswith("/jobs"):
        # Parse jobs request: src/main.py/jobs or src/main.py/jobs?param=value
        if "/jobs?" in decoded_file_path:
            file_parts = decoded_file_path.split("/jobs?")
            actual_file_path = file_parts[0]
        else:
            actual_file_path = decoded_file_path[:-5]  # Remove "/jobs"
        return actual_file_path, "jobs"
    elif "/trace?" in decoded_file_path:
        # Parse trace parameters: src/main.py/trace?mode=detailed&include_trace=true
        file_parts = decoded_file_path.split("/trace?")
        actual_file_path = file_parts[0]  # Already decoded
        return actual_file_path, "trace"
    elif decoded_file_path.endswith("/trace"):
        # Remove the /trace suffix
        actual_file_path = decoded_file_path[:-6]  # Remove "/trace"
        return actual_file_path, "trace"
    else:
        return decoded_file_path, "normal"


async def _handle_merge_request_resource(parts: list[str]) -> dict[str, Any]:
    """Handle merge request resource requests."""
    if len(parts) >= 3:
        project_id = parts[1]
        mr_iid = parts[2]
        debug_print(f"🔍 Accessing merge request {mr_iid} in project {project_id}")
        result = await get_merge_request_resource(project_id, mr_iid)
        verbose_debug_print("✅ Merge request resource retrieved successfully")
        return result
    else:
        raise ValueError("Invalid merge request URI format - insufficient parts")


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

        # Check for status filter and limit
        status = "all"
        limit = None

        if len(parts) > 4:
            # Check patterns like:
            # gl://jobs/123/pipeline/456/failed
            # gl://jobs/123/pipeline/456/failed/limit/5
            # gl://jobs/123/pipeline/456/limit/10

            if parts[4] in ["failed", "success"]:
                status = parts[4]
                if len(parts) > 6 and parts[5] == "limit":
                    try:
                        limit = int(parts[6])
                    except (ValueError, IndexError):
                        raise ValueError("Invalid limit parameter in jobs URI")
            elif parts[4] == "limit":
                try:
                    limit = int(parts[5])
                except (ValueError, IndexError):
                    raise ValueError("Invalid limit parameter in jobs URI")
            else:
                status = parts[4]  # fallback for other status types

        debug_print(
            f"🔍 Accessing jobs for pipeline {pipeline_id} in project {project_id} with status filter: {status}, limit: {limit}"
        )

        if limit is not None:
            # Import limited function
            from gitlab_analyzer.mcp.resources.job import (
                get_limited_pipeline_jobs_resource,
            )

            result = await get_limited_pipeline_jobs_resource(
                project_id, pipeline_id, status, limit
            )
        else:
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
            # or gl://files/123/pipeline/123/enhanced?mode=detailed&include_trace=true
            pipeline_id = parts[3]

            # Check if this is the enhanced version
            if len(parts) >= 5 and parts[4] == "enhanced":
                # Enhanced pipeline files with mode and trace support
                mode = query_params.get("mode", "balanced")
                include_trace_str = (
                    query_params.get("include_trace", "false") or "false"
                )
                include_trace = str(include_trace_str).lower() == "true"
                max_errors_per_file = int(query_params.get("max_errors", "5"))
                page = int(query_params.get("page", "1"))
                limit = int(query_params.get("limit", "20"))

                debug_print(
                    f"🔍 Accessing enhanced pipeline files for pipeline {pipeline_id} in project {project_id} "
                    f"(mode={mode}, include_trace={include_trace}, max_errors={max_errors_per_file}, page={page}, limit={limit})"
                )
                file_analysis_service = get_file_analysis_service()
                result = await file_analysis_service.get_enhanced_pipeline_files(
                    project_id,
                    pipeline_id,
                    mode=mode,
                    include_trace=str(include_trace).lower(),
                    max_errors=max_errors_per_file,
                )
                verbose_debug_print(
                    "✅ Enhanced pipeline files resource retrieved successfully"
                )
                return result
            else:
                # Standard pipeline files
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
                file_service = get_file_service()
                result = await file_service.get_pipeline_files(
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
            file_service = get_file_service()
            result = await file_service.get_files_for_job(
                project_id, job_id, page, limit
            )
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

        # Check if this is a pipeline-wide file request
        if parts[2] == "pipeline" and len(parts) >= 5:
            # gl://file/123/pipeline/456/path/to/file.py or gl://file/123/pipeline/456/path/to/file.py/trace
            pipeline_id = parts[3]
            file_path = "/".join(parts[4:])
            debug_print(
                f"🔍 Accessing file '{file_path}' across pipeline {pipeline_id} in project {project_id}"
            )

            # Parse file path and check for special requests
            actual_file_path, request_type = _parse_file_path(file_path)
            debug_print(f"📁 Actual file path: {actual_file_path}")
            debug_print(f"🔧 Request type: {request_type}")

            if request_type == "jobs":
                # Handle jobs request for pipeline file
                debug_print("👥 Getting jobs for file in pipeline")
                file_service = get_file_service()
                result = await file_service.get_file_jobs_in_pipeline(
                    project_id, pipeline_id, actual_file_path
                )
                verbose_debug_print(
                    "✅ Pipeline file jobs resource retrieved successfully"
                )
                return result
            elif request_type == "trace":
                # Get query parameters for trace
                mode = query_params.get("mode", "fixing")  # Default to fixing for trace
                include_trace_str = (
                    query_params.get("include_trace", "true") or "true"
                )  # Default to true for trace
                include_trace = str(include_trace_str).lower() == "true"
                debug_print(
                    f"⚙️ Pipeline file trace options: mode={mode}, include_trace={include_trace}"
                )

                file_service = get_file_service()
                result = await file_service.get_file_errors_in_pipeline(
                    project_id, pipeline_id, actual_file_path
                )
                verbose_debug_print(
                    "✅ Pipeline file resource with trace retrieved successfully"
                )
                return result
            else:
                # Normal file request - check for query parameters
                mode = query_params.get("mode", "balanced")  # Default mode
                include_trace_str = (
                    query_params.get("include_trace", "false") or "false"
                )
                include_trace = str(include_trace_str).lower() == "true"
                debug_print(
                    f"⚙️ Pipeline file options: mode={mode}, include_trace={include_trace}"
                )

                file_service = get_file_service()
                result = await file_service.get_file_errors_in_pipeline(
                    project_id, pipeline_id, actual_file_path
                )
                verbose_debug_print("✅ Pipeline file resource retrieved successfully")
                return result
        else:
            # Original job-specific file request: gl://file/123/456/path/to/file.py
            job_id = parts[2]
            file_path = "/".join(parts[3:])
            debug_print(
                f"🔍 Accessing file '{file_path}' in job {job_id} in project {project_id}"
            )

            # Parse file path and check for special requests
            actual_file_path, request_type = _parse_file_path(file_path)
            debug_print(f"📁 Actual file path: {actual_file_path}")

            if request_type == "trace":
                verbose_debug_print("🔍 Detected trace request in file URI")

                # Get query parameters for trace
                mode = query_params.get("mode", "balanced")
                include_trace_str = query_params.get("include_trace", "false")
                debug_print(
                    f"⚙️ Trace options: mode={mode}, include_trace={include_trace_str}"
                )

                # Use file analysis service for trace functionality
                file_analysis_service = get_file_analysis_service()
                result = await file_analysis_service.get_file_with_trace(
                    project_id, job_id, actual_file_path, mode, include_trace_str
                )
                verbose_debug_print(
                    "✅ File resource with trace retrieved successfully"
                )
                return result
            else:
                file_service = get_file_service()
                result = await file_service.get_file_data(
                    project_id, job_id, actual_file_path
                )
                verbose_debug_print("✅ File resource retrieved successfully")
                return result
    else:
        raise ValueError(
            "Invalid file URI format - expected file/project/job/path or file/project/pipeline/id/path"
        )


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
            result = await error_service.get_individual_error(
                project_id, job_id, error_id, mode
            )
            verbose_debug_print("✅ Individual error resource retrieved successfully")
            return result
        else:
            # gl://error/123/456
            debug_print(
                f"🔍 Accessing all errors in job {job_id} in project {project_id} (mode={mode})"
            )
            result = await error_service.get_job_errors(project_id, job_id, mode)
            verbose_debug_print("✅ Job errors resource retrieved successfully")
            return result
    else:
        raise ValueError("Invalid error URI format - expected error/project/job")


async def _handle_errors_resource(
    parts: list[str], query_params: dict[str, str] | None = None
) -> dict[str, Any]:
    """Handle errors collection resource requests."""
    if query_params is None:
        query_params = {}

    if len(parts) >= 3:
        project_id = parts[1]
        if len(parts) >= 4 and parts[2] == "pipeline":
            # gl://errors/123/pipeline/123 or gl://errors/123/pipeline/123/limit/5
            pipeline_id = parts[3]

            # Check for limit parameter
            limit = None
            if len(parts) > 5 and parts[4] == "limit":
                try:
                    limit = int(parts[5])
                except (ValueError, IndexError):
                    raise ValueError("Invalid limit parameter in errors URI")

            if limit is not None:
                # Limited pipeline errors
                mode = query_params.get("mode", "balanced")
                include_trace_str = query_params.get("include_trace", "false")
                include_trace = include_trace_str.lower() == "true"

                debug_print(
                    f"🔍 Accessing limited pipeline errors (limit={limit}) for pipeline {pipeline_id} in project {project_id}"
                )

                result = await error_service.get_limited_pipeline_errors(
                    project_id, pipeline_id, limit, mode, include_trace
                )
            else:
                # All pipeline errors
                debug_print(
                    f"🔍 Accessing pipeline errors for pipeline {pipeline_id} in project {project_id}"
                )
                result = await error_service.get_pipeline_errors(
                    project_id, pipeline_id
                )

            verbose_debug_print("✅ Pipeline errors resource retrieved successfully")
            return result
        else:
            # gl://errors/123/456/src/main.py or gl://errors/123/456/limit/5
            job_id = parts[2]

            # Check for limit parameter
            limit = None
            if len(parts) > 4 and parts[3] == "limit":
                try:
                    limit = int(parts[4])
                except (ValueError, IndexError):
                    raise ValueError("Invalid limit parameter in errors URI")
                file_path = ""  # No file path when using limit
            else:
                file_path = "/".join(parts[3:]) if len(parts) > 3 else ""
                # URL decode the file path
                if file_path:
                    file_path = unquote(file_path)

            if limit is not None:
                # Limited job errors
                mode = query_params.get("mode", "balanced")
                include_trace_str = query_params.get("include_trace", "false")
                include_trace = include_trace_str.lower() == "true"

                debug_print(
                    f"🔍 Accessing limited job errors (limit={limit}) for job {job_id} in project {project_id}"
                )

                result = await error_service.get_limited_job_errors(
                    project_id, job_id, limit, mode, include_trace
                )
            elif file_path:
                # File-specific errors
                debug_print(
                    f"🔍 Accessing file-specific errors for '{file_path}' in job {job_id} in project {project_id}"
                )
                result = await error_service.get_file_errors(
                    project_id, job_id, file_path
                )
            else:
                # All job errors
                debug_print(
                    f"🔍 Accessing all errors in job {job_id} in project {project_id}"
                )
                result = await error_service.get_job_errors(
                    project_id, job_id, "balanced"
                )

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


async def _handle_root_cause_resource(
    parts: list[str], query_params: dict[str, str]
) -> dict[str, Any]:
    """Handle root-cause resource requests with filtering support for both pipeline and job analysis."""
    if len(parts) >= 3:
        project_id = parts[1]
        mode = query_params.get(
            "mode", "minimal"
        )  # Default to minimal for AI optimization

        # Extract filtering parameters from query string
        limit = None
        severity_filter = query_params.get("severity")
        category_filter = query_params.get("category")
        min_confidence = None

        # Parse limit parameter
        if "limit" in query_params:
            try:
                limit = int(query_params["limit"])
                debug_print(f"🔢 Limit filter: {limit}")
            except (ValueError, TypeError):
                debug_print("⚠️ Invalid limit parameter, ignoring")

        # Parse confidence parameter
        if "confidence" in query_params:
            try:
                min_confidence = float(query_params["confidence"])
                debug_print(f"� Confidence filter: {min_confidence}")
            except (ValueError, TypeError):
                debug_print("⚠️ Invalid confidence parameter, ignoring")

        # Check if this is a job-specific or pipeline-specific request
        if len(parts) >= 4 and parts[2] == "job":
            # gl://root-cause/123/job/456 - Job root cause analysis
            job_id = parts[3]
            debug_print(
                f"🔍 Accessing job root cause analysis for job {job_id} in project {project_id}"
            )
            debug_print(f"⚙️ Mode: {mode}")
            if severity_filter:
                debug_print(f"🎯 Severity filter: {severity_filter}")
            if category_filter:
                debug_print(f"📂 Category filter: {category_filter}")

            # Import the job root cause analysis function
            import json

            from gitlab_analyzer.mcp.resources.analysis import (
                _get_job_root_cause_analysis,
            )

            result_json = await _get_job_root_cause_analysis(
                project_id,
                job_id,
                mode,
                limit=limit,
                severity_filter=severity_filter,
                category_filter=category_filter,
                min_confidence=min_confidence,
            )
            result = (
                json.loads(result_json) if isinstance(result_json, str) else result_json
            )

            verbose_debug_print(
                "✅ Job root cause analysis resource retrieved successfully"
            )
            return result
        else:
            # gl://root-cause/123/456 - Pipeline root cause analysis
            pipeline_id = parts[2]

            debug_print(
                f"🔍 Accessing pipeline root cause analysis for pipeline {pipeline_id} in project {project_id}"
            )
            debug_print(f"⚙️ Mode: {mode}")
            if severity_filter:
                debug_print(f"🎯 Severity filter: {severity_filter}")
            if category_filter:
                debug_print(f"📂 Category filter: {category_filter}")

            # Import the pipeline root cause analysis function
            import json

            from gitlab_analyzer.mcp.resources.analysis import _get_root_cause_analysis

            result_json = await _get_root_cause_analysis(
                project_id,
                pipeline_id,
                mode,
                limit=limit,
                severity_filter=severity_filter,
                category_filter=category_filter,
                min_confidence=min_confidence,
            )
            result = (
                json.loads(result_json) if isinstance(result_json, str) else result_json
            )

            verbose_debug_print(
                "✅ Pipeline root cause analysis resource retrieved successfully"
            )
            return result
    else:
        raise ValueError(
            "Invalid root-cause URI format - expected root-cause/project/pipeline or root-cause/project/job/id"
        )


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

    except (RuntimeError, ValueError, ImportError) as e:
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
        elif path.startswith("mr/"):
            debug_print("📋 Processing merge request resource request")
            result = await _handle_merge_request_resource(parts)
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
            result = await _handle_errors_resource(parts, query_params)
        elif path.startswith("analysis/"):
            debug_print("📊 Processing analysis resource request")
            result = await _handle_analysis_resource(parts, query_params)
        elif path.startswith("root-cause/"):
            debug_print(
                "🔍 Processing AI-optimized root cause analysis resource request"
            )
            result = await _handle_root_cause_resource(parts, query_params)
        else:
            error_print(f"❌ Unsupported resource URI pattern: {resource_uri}")
            return {
                "error": f"Unsupported resource URI pattern: {resource_uri}",
                "mcp_info": get_mcp_info("get_mcp_resource", error=True),
                "auto_cleanup": cleanup_status,
                "available_patterns": [
                    "gl://pipeline/{project_id}/{pipeline_id}",
                    "gl://mr/{project_id}/{mr_iid}",
                    "gl://jobs/{project_id}/pipeline/{pipeline_id}[/failed|/success]",
                    "gl://job/{project_id}/{pipeline_id}/{job_id}",
                    "gl://files/{project_id}/pipeline/{pipeline_id}[/page/{page}/limit/{limit}]",
                    "gl://files/{project_id}/pipeline/{pipeline_id}/enhanced[?mode={mode}&include_trace={trace}&max_errors={max}]",
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
                    "gl://root-cause/{project_id}/{pipeline_id}[?mode={mode}]",
                    "gl://root-cause/{project_id}/{pipeline_id}?limit={N}",
                    "gl://root-cause/{project_id}/{pipeline_id}?severity={level}",
                    "gl://root-cause/{project_id}/{pipeline_id}?category={type}",
                    "gl://root-cause/{project_id}/{pipeline_id}?confidence={min_confidence}",
                    "gl://root-cause/{project_id}/{pipeline_id}?limit={N}&severity={level}&confidence={min}",
                    "gl://root-cause/{project_id}/job/{job_id}[?mode={mode}]",
                    "gl://root-cause/{project_id}/job/{job_id}?limit={N}",
                    "gl://root-cause/{project_id}/job/{job_id}?severity={level}",
                    "gl://root-cause/{project_id}/job/{job_id}?category={type}",
                    "gl://root-cause/{project_id}/job/{job_id}?confidence={min_confidence}",
                    "gl://root-cause/{project_id}/job/{job_id}?limit={N}&severity={level}&confidence={min}",
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
    except (KeyError, TypeError, AttributeError) as e:
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
    except Exception as e:
        # Handle any other unexpected exceptions
        end_time = time.time()
        duration = end_time - start_time
        error_print(
            f"❌ Unexpected error accessing resource {resource_uri} after {duration:.3f}s: {e}"
        )
        return {
            "error": f"Failed to access resource: {str(e)}",
            "mcp_info": get_mcp_info("get_mcp_resource", error=True),
            "auto_cleanup": cleanup_status,
            "resource_uri": resource_uri,
            "debug_timing": {"duration_seconds": round(duration, 3)},
        }


def register_resource_access_tools(mcp: FastMCP) -> None:
    """Register resource access tools with MCP server"""

    @mcp.tool
    async def get_mcp_resource(resource_uri: str) -> dict[str, Any]:
        """
        🔗 RESOURCE ACCESS: Get data from MCP resource URI without re-running analysis.

        ⭐ ALWAYS TRY THIS FIRST for any pipeline/job/error data requests!

        WHEN TO USE:
        - Get pipeline info, job details, errors (try before analysis tools)
        - Access previously analyzed pipeline data
        - Retrieve cached results efficiently
        - Navigate between related resources
        - Avoid unnecessary re-analysis

        WORKFLOW:
        1. Try get_mcp_resource first
        2. If returns "pipeline_not_analyzed" → use failed_pipeline_analysis
        3. Then use get_mcp_resource again for efficient access

        SUPPORTED RESOURCE PATTERNS:
        - gl://pipeline/{project_id}/{pipeline_id} - Pipeline analysis
        - gl://mr/{project_id}/{mr_iid} - Merge request code review data
        - gl://jobs/{project_id}/pipeline/{pipeline_id}[/failed|/success] - Pipeline jobs
        - gl://job/{project_id}/{pipeline_id}/{job_id} - Individual job analysis
        - gl://files/{project_id}/pipeline/{pipeline_id}[/page/{page}/limit/{limit}] - Pipeline files
        - gl://files/{project_id}/pipeline/{pipeline_id}/enhanced[?mode={mode}&include_trace={trace}&max_errors={max}] - Enhanced pipeline files
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
        - gl://root-cause/{project_id}/{pipeline_id}[?mode={mode}] - AI-optimized root cause analysis
        - gl://root-cause/{project_id}/{pipeline_id}?limit={N} - Limited root cause results
        - gl://root-cause/{project_id}/{pipeline_id}?severity={level} - Filter by severity
        - gl://root-cause/{project_id}/{pipeline_id}?category={type} - Filter by category
        - gl://root-cause/{project_id}/{pipeline_id}?confidence={min_confidence} - Filter by confidence
        - gl://root-cause/{project_id}/{pipeline_id}?limit={N}&severity={level}&confidence={min} - Combined filters
        - gl://root-cause/{project_id}/job/{job_id}[?mode={mode}] - Job root cause analysis
        - gl://root-cause/{project_id}/job/{job_id}?limit={N} - Limited job root cause results
        - gl://root-cause/{project_id}/job/{job_id}?severity={level} - Filter job errors by severity
        - gl://root-cause/{project_id}/job/{job_id}?category={type} - Filter job errors by category
        - gl://root-cause/{project_id}/job/{job_id}?confidence={min_confidence} - Filter job errors by confidence
        - gl://root-cause/{project_id}/job/{job_id}?limit={N}&severity={level}&confidence={min} - Combined job filters

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
        - get_mcp_resource("gl://mr/123/456") - Get comprehensive merge request review data
        - get_mcp_resource("gl://files/123/pipeline/1594344") - Get files with errors
        - get_mcp_resource("gl://files/123/pipeline/1594344/enhanced?mode=detailed&include_trace=true") - Enhanced files with trace
        - get_mcp_resource("gl://error/123/76474172") - Get job error analysis
        - get_mcp_resource("gl://errors/123/76474172/src/main.py") - Get file-specific errors
        - get_mcp_resource("gl://errors/123/pipeline/1594344") - Get pipeline-wide errors
        - get_mcp_resource("gl://file/123/76474172/src/main.py/trace?mode=detailed&include_trace=true") - Get file with traceback
        - get_mcp_resource("gl://analysis/123/pipeline/1594344?mode=detailed") - Detailed analysis
        - get_mcp_resource("gl://file/123/76474172/src/main.py") - Specific file analysis
        - get_mcp_resource("gl://root-cause/123/1621656") - AI-optimized root cause analysis
        - get_mcp_resource("gl://root-cause/123/1621656?limit=3") - Get top 3 root causes
        - get_mcp_resource("gl://root-cause/123/1621656?severity=critical") - Get critical severity only
        - get_mcp_resource("gl://root-cause/123/1621656?category=syntax") - Get syntax-related issues
        - get_mcp_resource("gl://root-cause/123/1621656?confidence=0.8") - Get high-confidence issues
        - get_mcp_resource("gl://root-cause/123/1621656?limit=2&severity=high&confidence=0.7") - Combined filters
        - get_mcp_resource("gl://root-cause/123/job/78317505") - Job-specific root cause analysis
        - get_mcp_resource("gl://root-cause/123/job/78317505?limit=3") - Get top 3 job root causes
        - get_mcp_resource("gl://root-cause/123/job/78317505?severity=high") - Get high severity job errors
        - get_mcp_resource("gl://root-cause/123/job/78317505?category=test") - Get test-related job issues
        """
        # Delegate to the implementation function
        return await get_mcp_resource_impl(resource_uri)

    debug_print("🔗 Resource access tools registered successfully")


# Export the implementation function for testing and direct usage
get_mcp_resource = get_mcp_resource_impl
