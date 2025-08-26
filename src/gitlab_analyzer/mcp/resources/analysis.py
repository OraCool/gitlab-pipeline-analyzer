"""
Analysis resources for MCP server

Copyright (c) 2025 Siarhei Skuratovich
Licensed under the MIT License - see LICENSE file for details
"""

import json
import logging
from datetime import datetime, timezone
from typing import Any

from mcp.types import TextResourceContents

from gitlab_analyzer.cache.mcp_cache import get_cache_manager
from gitlab_analyzer.utils.utils import get_mcp_info

from .utils import create_text_resource

logger = logging.getLogger(__name__)


async def _get_comprehensive_analysis(
    project_id: str,
    pipeline_id: str | None = None,
    job_id: str | None = None,
    response_mode: str = "balanced",
) -> str:
    """Internal function to get comprehensive analysis with configurable response mode."""
    try:
        cache_manager = get_cache_manager()

        # Determine analysis scope and create appropriate cache key
        if job_id:
            scope = "job"
            cache_key = f"analysis_{project_id}_{job_id}_{response_mode}"
            resource_uri = (
                f"gl://analysis/{project_id}/job/{job_id}?mode={response_mode}"
            )
        elif pipeline_id:
            scope = "pipeline"
            cache_key = f"analysis_{project_id}_{pipeline_id}_{response_mode}"
            resource_uri = f"gl://analysis/{project_id}/pipeline/{pipeline_id}?mode={response_mode}"
        else:
            scope = "project"
            cache_key = f"analysis_{project_id}_{response_mode}"
            resource_uri = f"gl://analysis/{project_id}?mode={response_mode}"

        # Try to get from cache first
        cached_data = await cache_manager.get(cache_key)
        if cached_data:
            return json.dumps(cached_data, indent=2)

        # Get analysis data based on scope
        analysis_data = {}

        if scope == "job":
            # Single job analysis using database data
            if job_id is None:
                raise ValueError("job_id is required for job scope")

            # Get job errors and job info from database
            job_errors = cache_manager.get_job_errors(int(job_id))
            job_info = await cache_manager.get_job_info_async(int(job_id))

            analysis_data = {
                "scope": "job",
                "job_id": int(job_id),
                "job_info": job_info,
                "summary": {
                    "error_count": len(job_errors),
                    "success": len(job_errors) == 0,
                    "data_source": "database_only",
                },
                "errors": job_errors,
                "error_analysis": _analyze_database_errors(job_errors),
                "patterns": _identify_error_patterns(job_errors),
            }

        elif scope == "pipeline":
            # Pipeline-wide analysis using database data
            if pipeline_id is None:
                raise ValueError("pipeline_id is required for pipeline scope")

            # Get pipeline data from database
            pipeline_info = cache_manager.get_pipeline_info(int(pipeline_id))
            jobs = await cache_manager.get_pipeline_jobs(int(pipeline_id))
            failed_jobs = cache_manager.get_pipeline_failed_jobs(int(pipeline_id))

            analysis_data = {
                "scope": "pipeline",
                "pipeline_id": int(pipeline_id),
                "pipeline_info": pipeline_info,
                "summary": {
                    "total_jobs": len(jobs),
                    "failed_jobs": len(failed_jobs),
                    "success_rate": (
                        (len(jobs) - len(failed_jobs)) / len(jobs) if jobs else 0
                    ),
                    "status": (
                        pipeline_info.get("status") if pipeline_info else "unknown"
                    ),
                    "data_source": "database_only",
                },
                "job_analysis": {
                    "jobs": jobs,
                    "failed_jobs": failed_jobs,
                },
                "patterns": _identify_pipeline_patterns(jobs),
            }

        else:
            # Project-level analysis (placeholder for future implementation)
            analysis_data = {
                "scope": "project",
                "summary": {
                    "message": "Project-level analysis not yet implemented",
                    "suggestion": "Use pipeline or job-specific analysis",
                },
            }

        # Process the analysis result
        result = {
            "comprehensive_analysis": {
                "project_id": project_id,
                **analysis_data,
            },
            "resource_uri": resource_uri,
            "cached_at": datetime.now(timezone.utc).isoformat(),
            "metadata": {
                "analysis_scope": scope,
                "source": "multiple_endpoints",
                "response_mode": response_mode,
                "coverage": "comprehensive",
            },
        }

        # Apply response mode optimization
        from gitlab_analyzer.utils.utils import optimize_tool_response

        result = optimize_tool_response(result, response_mode)

        mcp_info = get_mcp_info(
            tool_used="comprehensive_analysis", error=False, parser_type="resource"
        )

        # Cache the result
        result["mcp_info"] = mcp_info
        await cache_manager.set(
            cache_key,
            result,
            data_type="analysis",
            project_id=project_id,
            job_id=int(job_id) if job_id else None,
            pipeline_id=int(pipeline_id) if pipeline_id else None,
        )

        return json.dumps(result, indent=2)

    except Exception as e:
        logger.error("Error getting analysis resource %s: %s", project_id, e)
        error_result = {
            "error": f"Failed to get analysis resource: {str(e)}",
            "project_id": project_id,
            "resource_uri": (
                resource_uri
                if "resource_uri" in locals()
                else f"gl://analysis/{project_id}"
            ),
        }
        return json.dumps(error_result, indent=2)


def _analyze_database_errors(db_errors):
    """Analyze error patterns from database error data"""
    if not db_errors:
        return {"message": "No errors found"}

    error_types = {}
    error_files = set()
    total_errors = len(db_errors)

    for error in db_errors:
        # Count error types
        exception_type = error.get("exception", "UnknownError")
        error_types[exception_type] = error_types.get(exception_type, 0) + 1

        # Track affected files
        if error.get("file_path"):
            error_files.add(error["file_path"])

    return {
        "total_errors": total_errors,
        "unique_error_types": len(error_types),
        "error_types": error_types,
        "most_common_error": (
            max(error_types.items(), key=lambda x: x[1])[0] if error_types else None
        ),
        "affected_files": list(error_files),
        "affected_file_count": len(error_files),
        "errors_per_file": total_errors / len(error_files) if error_files else 0,
    }


def _identify_error_patterns(db_errors):
    """Identify common patterns in database error data"""
    patterns = []

    if not db_errors:
        return patterns

    # Check for common failure patterns based on exception types
    exception_counts = {}
    for error in db_errors:
        exception_type = error.get("exception", "")
        exception_counts[exception_type] = exception_counts.get(exception_type, 0) + 1

    # Identify patterns
    for exception_type, count in exception_counts.items():
        if count > 1:
            patterns.append(f"Multiple {exception_type} errors ({count} occurrences)")

    # Check for file-specific patterns
    file_errors = {}
    for error in db_errors:
        file_path = error.get("file_path", "")
        if file_path:
            file_errors[file_path] = file_errors.get(file_path, 0) + 1

    for file_path, count in file_errors.items():
        if count > 1:
            patterns.append(f"Multiple errors in {file_path} ({count} errors)")

    return patterns


def _analyze_errors(errors):
    """Analyze error patterns and provide insights"""
    if not errors:
        return {"message": "No errors found"}

    error_types = {}
    file_errors = {}

    for error in errors:
        error_type = getattr(error, "exception_type", "unknown")
        error_types[error_type] = error_types.get(error_type, 0) + 1

        file_path = getattr(error, "file_path", None) or getattr(
            error, "test_file", None
        )
        if file_path:
            file_errors[str(file_path)] = file_errors.get(str(file_path), 0) + 1

    return {
        "total_errors": len(errors),
        "error_types": error_types,
        "most_common_error": (
            max(error_types.items(), key=lambda x: x[1])[0] if error_types else None
        ),
        "files_with_errors": file_errors,
        "most_problematic_file": (
            max(file_errors.items(), key=lambda x: x[1])[0] if file_errors else None
        ),
    }


def _analyze_warnings(warnings):
    """Analyze warning patterns"""
    if not warnings:
        return {"message": "No warnings found"}

    return {
        "total_warnings": len(warnings),
        "warning_messages": [
            getattr(w, "message", "") for w in warnings[:5]
        ],  # First 5 warnings
    }


def _identify_patterns(log_entries):
    """Identify common patterns in log entries"""
    patterns = []

    # Check for common failure patterns
    messages = [getattr(entry, "message", "") for entry in log_entries]

    if any("timeout" in msg.lower() for msg in messages):
        patterns.append("timeout_issues")
    if any("connection" in msg.lower() for msg in messages):
        patterns.append("connection_issues")
    if any("import" in msg.lower() and "error" in msg.lower() for msg in messages):
        patterns.append("import_errors")
    if any("syntax" in msg.lower() for msg in messages):
        patterns.append("syntax_errors")

    return patterns


def _group_jobs_by_status(jobs):
    """Group jobs by their status"""
    status_groups = {}
    for job in jobs:
        status = job.status if hasattr(job, "status") else "unknown"
        status_groups[status] = status_groups.get(status, 0) + 1
    return status_groups


def _identify_pipeline_patterns(jobs):
    """Identify patterns across pipeline jobs"""
    patterns = []

    # Check for stage-specific failures
    failed_stages = set()
    for job in jobs:
        if hasattr(job, "status") and job.status == "failed":
            stage = job.stage if hasattr(job, "stage") else "unknown"
            failed_stages.add(stage)

    if len(failed_stages) > 1:
        patterns.append("multiple_stage_failures")
    elif len(failed_stages) == 1:
        patterns.append(f"stage_specific_failure_{list(failed_stages)[0]}")

    return patterns


async def get_analysis_resource_data(
    project_id: str,
    pipeline_id: str | None = None,
    job_id: str | None = None,
    mode: str = "balanced",
) -> dict[str, Any]:
    """
    Get analysis resource data (standalone function for resource access tool)

    Args:
        project_id: GitLab project ID
        pipeline_id: Pipeline ID (optional)
        job_id: Job ID (optional)
        mode: Response mode (minimal, balanced, detailed, etc.)

    Returns:
        Analysis data as dict
    """
    try:
        result_json = await _get_comprehensive_analysis(
            project_id, pipeline_id, job_id, mode
        )
        return json.loads(result_json)
    except Exception as e:
        logger.error(
            "Error getting analysis resource data %s/%s/%s: %s",
            project_id,
            pipeline_id,
            job_id,
            e,
        )
        uri_parts = [f"gl://analysis/{project_id}"]
        if pipeline_id:
            uri_parts.append(f"pipeline/{pipeline_id}")
        if job_id:
            uri_parts.append(f"job/{job_id}")

        resource_uri = "/".join(uri_parts)
        if mode != "balanced":
            resource_uri += f"?mode={mode}"

        return {
            "error": f"Failed to get analysis resource: {str(e)}",
            "project_id": project_id,
            "pipeline_id": pipeline_id,
            "job_id": job_id,
            "resource_uri": resource_uri,
        }


def register_analysis_resources(mcp) -> None:
    """Register analysis resources with MCP server"""

    @mcp.resource("gl://analysis/{project_id}")
    async def get_project_analysis_resource(project_id: str) -> TextResourceContents:
        """
        Get project-level analysis as a resource with caching.

        Args:
            project_id: GitLab project ID

        Returns:
            Project-level analysis with metadata

        Note: Resources provide "balanced" mode by default for optimal agent consumption.
        """
        result = await _get_comprehensive_analysis(project_id, response_mode="balanced")
        return create_text_resource("gl://analysis/{project_id}", result)

    @mcp.resource("gl://analysis/{project_id}?mode={mode}")
    async def get_project_analysis_resource_with_mode(
        project_id: str, mode: str
    ) -> TextResourceContents:
        """
        Get project-level analysis as a resource with specific response mode.

        Args:
            project_id: GitLab project ID
            mode: Response mode - "minimal", "balanced", "fixing", or "full"

        Returns:
            Project-level analysis optimized for the specified mode
        """
        result = await _get_comprehensive_analysis(project_id, response_mode=mode)
        return create_text_resource("gl://analysis/{project_id}?mode={mode}", result)

    @mcp.resource("gl://analysis/{project_id}/pipeline/{pipeline_id}")
    async def get_pipeline_analysis_resource(
        project_id: str, pipeline_id: str
    ) -> TextResourceContents:
        """
        Get pipeline-level analysis as a resource with caching.

        Args:
            project_id: GitLab project ID
            pipeline_id: GitLab pipeline ID

        Returns:
            Pipeline-level analysis with metadata
        """
        result = await _get_comprehensive_analysis(
            project_id, pipeline_id, response_mode="balanced"
        )
        return create_text_resource(
            "gl://analysis/{project_id}/pipeline/{pipeline_id}", result
        )

    @mcp.resource("gl://analysis/{project_id}/pipeline/{pipeline_id}?mode={mode}")
    async def get_pipeline_analysis_resource_with_mode(
        project_id: str, pipeline_id: str, mode: str
    ) -> TextResourceContents:
        """
        Get pipeline-level analysis as a resource with specific response mode.

        Args:
            project_id: GitLab project ID
            pipeline_id: GitLab pipeline ID
            mode: Response mode - "minimal", "balanced", "fixing", or "full"

        Returns:
            Pipeline-level analysis optimized for the specified mode
        """
        result = await _get_comprehensive_analysis(
            project_id, pipeline_id, response_mode=mode
        )
        return create_text_resource(
            "gl://analysis/{project_id}/pipeline/{pipeline_id}?mode={mode}",
            result,
        )

    @mcp.resource("gl://analysis/{project_id}/job/{job_id}")
    async def get_job_analysis_resource(
        project_id: str, job_id: str
    ) -> TextResourceContents:
        """
        Get job-level analysis as a resource with caching.

        Args:
            project_id: GitLab project ID
            job_id: GitLab job ID

        Returns:
            Job-level analysis with metadata
        """
        result = await _get_comprehensive_analysis(
            project_id, job_id=job_id, response_mode="balanced"
        )
        return create_text_resource("gl://analysis/{project_id}/job/{job_id}", result)

    @mcp.resource("gl://analysis/{project_id}/job/{job_id}?mode={mode}")
    async def get_job_analysis_resource_with_mode(
        project_id: str, job_id: str, mode: str
    ) -> TextResourceContents:
        """
        Get job-level analysis as a resource with specific response mode.

        Args:
            project_id: GitLab project ID
            job_id: GitLab job ID
            mode: Response mode - "minimal", "balanced", "fixing", or "full"

        Returns:
            Job-level analysis optimized for the specified mode
        """
        result = await _get_comprehensive_analysis(
            project_id, job_id=job_id, response_mode=mode
        )
        return create_text_resource(
            "gl://analysis/{project_id}/job/{job_id}?mode={mode}", result
        )

    logger.info("Analysis resources registered")
