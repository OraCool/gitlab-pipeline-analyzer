"""
Error resources for MCP server

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


async def _get_error_analysis(
    project_id: str, job_id: str, response_mode: str = "balanced"
) -> str:
    """Internal function to get error analysis with configurable response mode."""
    try:
        cache_manager = get_cache_manager()

        # Create cache key for error analysis (include response mode)
        cache_key = f"errors_{project_id}_{job_id}_{response_mode}"

        # Try to get from cache first
        cached_data = await cache_manager.get(cache_key)
        if cached_data:
            return json.dumps(cached_data, indent=2)

        # First check if job exists in database (has been analyzed)
        job_info = await cache_manager.get_job_info_async(int(job_id))
        if not job_info:
            # Job not found in database - needs analysis first
            error_result = {
                "error": "Job not analyzed",
                "message": f"Job {job_id} not found in cache. Run pipeline analysis first.",
                "project_id": project_id,
                "job_id": int(job_id),
                "suggested_action": "Use failed_pipeline_analysis() to analyze the pipeline containing this job",
                "resource_uri": f"gl://error/{project_id}/{job_id}?mode={response_mode}",
                "mcp_info": get_mcp_info(
                    "get_job_trace", error=True, parser_type="resource"
                ),
            }
            return json.dumps(error_result, indent=2)

        # Get errors from database (pre-analyzed data)
        job_errors = cache_manager.get_job_errors(int(job_id))

        # Process errors from database
        all_errors = []
        error_files = set()
        error_types = set()

        for db_error in job_errors:
            error_data = {
                "id": db_error["id"],
                "message": db_error["message"],
                "level": "error",  # All from get_job_errors are errors
                "line_number": db_error.get("line"),
                "file_path": db_error.get("file_path"),
                "exception_type": db_error.get("error_type"),
                "fingerprint": db_error.get("fingerprint"),
                "detail": db_error.get("detail", {}),
            }
            all_errors.append(error_data)

            # Track error files and types for statistics
            if error_data.get("file_path"):
                error_files.add(str(error_data["file_path"]))
            if error_data.get("error_type"):
                error_types.add(error_data["error_type"])

        # Process the analysis data
        result = {
            "error_analysis": {
                "project_id": project_id,
                "job_id": int(job_id),
                "errors": all_errors,
                "error_count": len(all_errors),
                "error_statistics": {
                    "total_errors": len(all_errors),
                    "affected_files": list(error_files),
                    "affected_file_count": len(error_files),
                    "error_types": list(error_types),
                    "unique_error_types": len(error_types),
                    "error_distribution": {
                        error_type: sum(
                            1
                            for err in all_errors
                            if err.get("error_type") == error_type
                        )
                        for error_type in error_types
                    },
                },
            },
            "resource_uri": f"gl://error/{project_id}/{job_id}?mode={response_mode}",
            "cached_at": datetime.now(timezone.utc).isoformat(),
            "metadata": {
                "analysis_scope": "all-errors",
                "source": "job_trace",
                "response_mode": response_mode,
                "coverage": "complete",
            },
        }

        # Apply response mode optimization
        from gitlab_analyzer.utils.utils import optimize_tool_response

        result = optimize_tool_response(result, response_mode)

        mcp_info = get_mcp_info(
            tool_used="get_job_trace", error=False, parser_type="resource"
        )

        # Cache the result
        result["mcp_info"] = mcp_info
        await cache_manager.set(
            cache_key,
            result,
            data_type="job_errors",
            project_id=project_id,
            job_id=int(job_id),
        )

        return json.dumps(result, indent=2)

    except Exception as e:
        logger.error("Error getting error resource %s/%s: %s", project_id, job_id, e)
        error_result = {
            "error": f"Failed to get error resource: {str(e)}",
            "project_id": project_id,
            "job_id": job_id,
            "resource_uri": f"gl://error/{project_id}/{job_id}?mode={response_mode}",
        }
        return json.dumps(error_result, indent=2)


async def get_file_errors_resource_data(
    project_id: str, job_id: str, file_path: str, mode: str = "balanced"
) -> dict[str, Any]:
    """
    Get file-specific error resource data

    Args:
        project_id: GitLab project ID
        job_id: GitLab job ID
        file_path: Path to the specific file
        mode: Response mode (balanced, detailed, minimal)

    Returns:
        File error analysis data as dict
    """
    try:
        cache_manager = get_cache_manager()

        # Get errors for the specific file
        file_errors = cache_manager.get_file_errors(int(job_id), file_path)

        enhanced_errors = []
        for error in file_errors:
            enhanced_error = {
                "id": error["error_id"],  # Use error_id instead of id
                "message": error["message"],
                "line_number": error.get("line"),
                "file_path": error.get("file"),  # Use file instead of file_path
                "exception_type": error.get("error_type"),
                "severity": "error",
                "context": {
                    "job_id": int(job_id),
                    "project_id": project_id,
                    "file_path": file_path,
                },
                "resource_links": [
                    {
                        "type": "resource_link",
                        "resourceUri": f"gl://file/{project_id}/{job_id}/{file_path}",
                        "text": f"View full file content: {file_path}",
                    },
                    {
                        "type": "resource_link",
                        "resourceUri": f"gl://error/{project_id}/{job_id}/{error['error_id']}",  # Use error_id
                        "text": "View detailed error analysis with fixing recommendations",
                    },
                ],
            }
            enhanced_errors.append(enhanced_error)

        return {
            "file_path": file_path,
            "job_id": int(job_id),
            "project_id": project_id,
            "errors": enhanced_errors,
            "summary": {
                "total_errors": len(enhanced_errors),
                "file_path": file_path,
                "error_types": list(
                    {e.get("exception_type", "unknown") for e in enhanced_errors}
                ),
            },
            "resource_links": [
                {
                    "type": "resource_link",
                    "resourceUri": f"gl://errors/{project_id}/{job_id}",
                    "text": "View all errors in this job",
                },
                {
                    "type": "resource_link",
                    "resourceUri": f"gl://file/{project_id}/{job_id}/{file_path}",
                    "text": f"View complete file: {file_path}",
                },
            ],
        }

    except Exception as e:
        logger.error(
            "Error getting file errors %s/%s/%s: %s", project_id, job_id, file_path, e
        )
        return {
            "error": f"Failed to get file errors: {str(e)}",
            "project_id": project_id,
            "job_id": job_id,
            "file_path": file_path,
            "resource_uri": f"gl://errors/{project_id}/{job_id}/{file_path}",
        }


async def get_pipeline_errors_resource_data(
    project_id: str, pipeline_id: str, mode: str = "balanced"
) -> dict[str, Any]:
    """
    Get pipeline-level error resource data

    Args:
        project_id: GitLab project ID
        pipeline_id: GitLab pipeline ID
        mode: Response mode (balanced, detailed, minimal)

    Returns:
        Pipeline error analysis data as dict
    """
    try:
        cache_manager = get_cache_manager()

        # Get all failed jobs in the pipeline
        failed_jobs = cache_manager.get_pipeline_failed_jobs(int(pipeline_id))

        all_errors = []
        error_summary: dict[str, Any] = {
            "total_errors": 0,
            "failed_jobs": len(failed_jobs),
            "jobs_with_errors": [],
            "error_types": set(),
            "affected_files": set(),
        }

        for job in failed_jobs:
            job_id = job.get("job_id")
            if job_id is None:
                continue
            job_errors = cache_manager.get_job_errors(int(job_id))

            if job_errors:
                error_summary["jobs_with_errors"].append(
                    {
                        "job_id": job_id,
                        "job_name": job.get("name"),
                        "error_count": len(job_errors),
                    }
                )

                for error in job_errors:
                    enhanced_error = {
                        "id": error["id"],
                        "message": error["message"],
                        "job_id": job_id,
                        "job_name": job.get("name"),
                        "line_number": error.get("line"),
                        "file_path": error.get("file_path"),
                        "exception_type": error.get("error_type"),
                        "resource_links": [
                            {
                                "type": "resource_link",
                                "resourceUri": f"gl://error/{project_id}/{job_id}/{error['id']}",
                                "text": "View detailed error with fixing recommendations",
                            },
                            {
                                "type": "resource_link",
                                "resourceUri": f"gl://errors/{project_id}/{job_id}",
                                "text": f"View all errors in job {job.get('name', job_id)}",
                            },
                        ],
                    }
                    all_errors.append(enhanced_error)

                    if error.get("error_type"):
                        error_summary["error_types"].add(error["error_type"])
                    if error.get("file_path"):
                        error_summary["affected_files"].add(error["file_path"])

        error_summary["total_errors"] = len(all_errors)
        error_summary["error_types"] = list(error_summary["error_types"])
        error_summary["affected_files"] = list(error_summary["affected_files"])

        return {
            "pipeline_id": int(pipeline_id),
            "project_id": project_id,
            "errors": all_errors,
            "summary": error_summary,
            "resource_links": [
                {
                    "type": "resource_link",
                    "resourceUri": f"gl://pipeline/{project_id}/{pipeline_id}",
                    "text": "View complete pipeline analysis",
                },
                {
                    "type": "resource_link",
                    "resourceUri": f"gl://jobs/{project_id}/pipeline/{pipeline_id}/failed",
                    "text": "View all failed jobs in this pipeline",
                },
            ],
        }

    except Exception as e:
        logger.error(
            "Error getting pipeline errors %s/%s: %s", project_id, pipeline_id, e
        )
        return {
            "error": f"Failed to get pipeline errors: {str(e)}",
            "project_id": project_id,
            "pipeline_id": pipeline_id,
            "resource_uri": f"gl://errors/{project_id}/pipeline/{pipeline_id}",
        }


async def get_error_resource_data(
    project_id: str, job_id: str, mode: str = "balanced"
) -> dict[str, Any]:
    """
    Get error resource data (standalone function for resource access tool)

    Args:
        project_id: GitLab project ID
        job_id: GitLab job ID
        mode: Response mode (balanced, detailed, minimal)

    Returns:
        Error analysis data as dict
    """
    try:
        result_json = await _get_error_analysis(project_id, job_id, mode)
        return json.loads(result_json)
    except Exception as e:
        logger.error(
            "Error getting error resource data %s/%s: %s", project_id, job_id, e
        )
        return {
            "error": f"Failed to get error resource: {str(e)}",
            "project_id": project_id,
            "job_id": job_id,
            "resource_uri": f"gl://error/{project_id}/{job_id}?mode={mode}",
        }


async def _get_individual_error_with_mode(
    project_id: str, job_id: str, error_id: str, mode: str = "balanced"
) -> TextResourceContents:
    """Internal function to get individual error with specified mode."""
    try:
        cache_manager = get_cache_manager()

        # Get all errors for the job from database
        all_errors = cache_manager.get_job_errors(int(job_id))

        # Find error by ID
        target_error = None
        for err in all_errors:
            if (
                str(err.get("error_id", "")) == error_id
                or str(err.get("id", "")) == error_id
            ):
                target_error = err
                break

        if not target_error:
            error_result = {
                "error": "Error not found",
                "message": f"Error {error_id} not found in job {job_id}",
                "job_id": int(job_id),
                "project_id": project_id,
                "error_id": error_id,
                "suggested_action": f"Use gl://error/{project_id}/{job_id} to view all errors",
                "mcp_info": get_mcp_info("individual_error_resource"),
            }
            return create_text_resource(
                f"gl://error/{project_id}/{job_id}/{error_id}",
                json.dumps(error_result, indent=2),
            )

        # Parse error detail if it's JSON string
        error_detail = target_error.get("detail", {})
        if isinstance(error_detail, str):
            try:
                error_detail = json.loads(error_detail)
            except json.JSONDecodeError:
                error_detail = {"raw_detail": error_detail}

        # Enhance error with fix guidance if mode supports it
        enhanced_error = {
            "error_id": target_error.get("error_id", error_id),
            "fingerprint": target_error.get("fingerprint"),
            "exception": target_error.get("error_type"),
            "message": target_error.get("message"),
            "file": target_error.get("file_path"),
            "line": target_error.get("line"),
            "detail": error_detail,
            "source": "database",
        }

        # Add fix guidance for fixing and detailed modes
        if mode in ["fixing", "detailed"]:
            try:
                from gitlab_analyzer.utils.utils import _generate_fix_guidance

                fix_guidance_error = {
                    "exception_type": target_error.get("error_type"),
                    "exception_message": target_error.get("message"),
                    "file_path": target_error.get("file_path"),
                    "line_number": str(target_error.get("line", "")),
                    "test_function": error_detail.get("test_function"),
                    "test_name": error_detail.get("test_name"),
                    "message": target_error.get("message"),
                }
                enhanced_error["fix_guidance"] = _generate_fix_guidance(
                    fix_guidance_error
                )
            except Exception as fix_error:
                logger.warning("Failed to generate fix guidance: %s", fix_error)
                enhanced_error["fix_guidance"] = {
                    "error": "Fix guidance generation failed",
                    "message": str(fix_error),
                }

        # Get job info for context and navigation
        job_info = await cache_manager.get_job_info_async(int(job_id))

        # Add resource links for navigation
        resource_links = []

        # Link back to file containing this error
        if target_error.get("file_path"):
            resource_links.append(
                {
                    "type": "resource_link",
                    "resourceUri": f"gl://file/{project_id}/{job_id}/{target_error['file_path']}",
                    "text": f"View all errors in {target_error['file_path']} - complete file analysis and error context",
                }
            )

            # Add file trace link for enhanced analysis
            if mode in ["fixing", "detailed"]:
                resource_links.append(
                    {
                        "type": "resource_link",
                        "resourceUri": f"gl://file/{project_id}/{job_id}/{target_error['file_path']}/trace?mode=fixing&include_trace=true",
                        "text": "View enhanced file analysis with trace and fixing recommendations",
                    }
                )

        # Link back to job
        if job_info:
            resource_links.append(
                {
                    "type": "resource_link",
                    "resourceUri": f"gl://job/{project_id}/{job_info['pipeline_id']}/{job_id}",
                    "text": f"Return to job {job_id} overview - view all files and job execution details",
                }
            )

            # Link back to pipeline
            resource_links.append(
                {
                    "type": "resource_link",
                    "resourceUri": f"gl://pipeline/{project_id}/{job_info['pipeline_id']}",
                    "text": f"Navigate to pipeline {job_info['pipeline_id']} - view all jobs and pipeline status",
                }
            )

        # Link to all errors in this job
        resource_links.append(
            {
                "type": "resource_link",
                "resourceUri": f"gl://error/{project_id}/{job_id}",
                "text": f"View all errors in job {job_id} - comprehensive error analysis and statistics",
            }
        )

        # Build complete result with comprehensive error info
        result = {
            "individual_error_analysis": {
                "project_id": project_id,
                "job_id": int(job_id),
                "error_id": error_id,
                "error": enhanced_error,
                "analysis_mode": mode,
                "data_source": "database_only",
            },
            "job_context": {
                "job_id": int(job_id),
                "status": job_info.get("status") if job_info else "unknown",
                "name": job_info.get("name") if job_info else None,
            },
            "resource_uri": f"gl://error/{project_id}/{job_id}/{error_id}?mode={mode}",
            "cached_at": datetime.now(timezone.utc).isoformat(),
            "resource_links": resource_links,
            "metadata": {
                "resource_type": "individual_error",
                "project_id": project_id,
                "job_id": int(job_id),
                "error_id": error_id,
                "analysis_mode": mode,
                "data_source": "database",
                "include_fix_guidance": mode in ["fixing", "detailed"],
            },
            "mcp_info": get_mcp_info("individual_error_resource"),
        }

        return create_text_resource(
            f"gl://error/{project_id}/{job_id}/{error_id}?mode={mode}",
            json.dumps(result, indent=2),
        )

    except Exception as e:
        logger.error(
            "Error getting individual error resource %s/%s/%s: %s",
            project_id,
            job_id,
            error_id,
            e,
        )
        error_result = {
            "error": f"Failed to get individual error resource: {str(e)}",
            "project_id": project_id,
            "job_id": job_id,
            "error_id": error_id,
            "resource_uri": f"gl://error/{project_id}/{job_id}/{error_id}?mode={mode}",
            "mcp_info": get_mcp_info("individual_error_resource"),
        }
        return create_text_resource(
            f"gl://error/{project_id}/{job_id}/{error_id}?mode={mode}",
            json.dumps(error_result, indent=2),
        )


async def get_individual_error_data(
    project_id: str, job_id: str, error_id: str, mode: str = "balanced"
) -> dict:
    """
    Public function to get individual error data for use by tools.

    Args:
        project_id: GitLab project ID
        job_id: GitLab job ID
        error_id: Error ID (e.g., "76474190_0")
        mode: Analysis mode (minimal, balanced, fixing, detailed)

    Returns:
        Dictionary with individual error data
    """
    result = await _get_individual_error_with_mode(project_id, job_id, error_id, mode)
    # Extract the content from TextResourceContents and parse as JSON
    return json.loads(result.text)


def register_error_resources(mcp) -> None:
    """Register error resources with MCP server"""

    @mcp.resource("gl://error/{project_id}/{job_id}")
    async def get_error_resource(project_id: str, job_id: str) -> TextResourceContents:
        """
        Get error analysis for a specific job.

        Args:
            project_id: GitLab project ID
            job_id: GitLab job ID

        Returns:
            Comprehensive error analysis for the job
        """
        return await get_error_resource_with_mode(project_id, job_id, "balanced")

    @mcp.resource("gl://error/{project_id}/{job_id}?mode={mode}")
    async def get_error_resource_with_mode(
        project_id: str, job_id: str, mode: str
    ) -> TextResourceContents:
        """
        Get error analysis for a specific job with specified mode.

        Args:
            project_id: GitLab project ID
            job_id: GitLab job ID
            mode: Analysis mode (minimal, balanced, fixing, detailed)

        Returns:
            Mode-specific error analysis for the job
        """
        data = await get_error_resource_data(project_id, job_id, mode)
        return create_text_resource(
            f"gl://error/{project_id}/{job_id}?mode={mode}",
            json.dumps(data, indent=2),
        )

    @mcp.resource("gl://error/{project_id}/{job_id}/{error_id}")
    async def get_individual_error_resource(
        project_id: str, job_id: str, error_id: str
    ) -> TextResourceContents:
        """
        Get individual error details with basic information.

        Args:
            project_id: GitLab project ID
            job_id: GitLab job ID
            error_id: Error ID (e.g., "76474190_0")

        Returns:
            Basic information about a specific error with navigation links
        """
        return await _get_individual_error_with_mode(
            project_id, job_id, error_id, "balanced"
        )

    @mcp.resource("gl://error/{project_id}/{job_id}/{error_id}?mode={mode}")
    async def get_individual_error_resource_with_mode(
        project_id: str, job_id: str, error_id: str, mode: str
    ) -> TextResourceContents:
        """
        Get individual error details with specified mode.

        Args:
            project_id: GitLab project ID
            job_id: GitLab job ID
            error_id: Error ID (e.g., "76474190_0")
            mode: Analysis mode (minimal, balanced, fixing, detailed)

        Returns:
            Mode-specific information about a specific error with enhanced details
        """
        return await _get_individual_error_with_mode(project_id, job_id, error_id, mode)

    logger.info("Error resources registered")
