"""
Error resources for MCP server

Copyright (c) 2025 Siarhei Skuratovich
Licensed under the MIT License - see LICENSE file for details
"""

import json
import logging
from datetime import UTC, datetime

from gitlab_analyzer.cache.mcp_cache import get_cache_manager
from gitlab_analyzer.utils.utils import get_gitlab_analyzer, get_mcp_info

logger = logging.getLogger(__name__)


async def _get_error_analysis(
    project_id: str, job_id: str, response_mode: str = "balanced"
) -> str:
    """Internal function to get error analysis with configurable response mode."""
    try:
        cache_manager = get_cache_manager()
        analyzer = get_gitlab_analyzer()

        # Create cache key for error analysis (include response mode)
        cache_key = f"errors_{project_id}_{job_id}_{response_mode}"

        # Try to get from cache first
        cached_data = await cache_manager.get(cache_key)
        if cached_data:
            return json.dumps(cached_data, indent=2)

        # Get job trace and extract all errors
        trace = await analyzer.get_job_trace(project_id, int(job_id))

        # Extract errors from the trace using the log parser
        from gitlab_analyzer.parsers.log_parser import LogParser

        parser = LogParser()
        log_entries = parser.extract_log_entries(trace)

        # Process all errors
        all_errors = []
        error_files = set()
        error_types = set()

        for entry in log_entries:
            if entry.level == "error":
                error_data = {
                    "message": entry.message,
                    "level": entry.level,
                    "line_number": getattr(entry, "line_number", None),
                    "test_file": getattr(entry, "test_file", None),
                    "file_path": getattr(entry, "file_path", None),
                    "exception_type": getattr(entry, "exception_type", None),
                    "exception_message": getattr(entry, "exception_message", None),
                    "context": getattr(entry, "context", []),
                }
                all_errors.append(error_data)

                # Track error files and types for statistics
                if error_data.get("file_path"):
                    error_files.add(str(error_data["file_path"]))
                if error_data.get("test_file"):
                    error_files.add(str(error_data["test_file"]))
                if error_data.get("exception_type"):
                    error_types.add(error_data["exception_type"])

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
                            if err.get("exception_type") == error_type
                        )
                        for error_type in error_types
                    },
                },
            },
            "resource_uri": f"gl://error/{project_id}/{job_id}?mode={response_mode}",
            "cached_at": datetime.now(UTC).isoformat(),
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


def register_error_resources(mcp) -> None:
    """Register error resources with MCP server"""

    @mcp.resource("gl://error/{project_id}/{job_id}")
    async def get_error_resource(project_id: str, job_id: str) -> str:
        """
        Get comprehensive error analysis as a resource with caching.

        Args:
            project_id: GitLab project ID
            job_id: GitLab job ID

        Returns:
            Complete error analysis with statistics and metadata

        Note: Resources provide "balanced" mode by default for optimal agent consumption.
        For different detail levels, use error analysis tools with response_mode parameter.
        """
        return await _get_error_analysis(project_id, job_id, "balanced")

    @mcp.resource("gl://error/{project_id}/{job_id}?mode={mode}")
    async def get_error_resource_with_mode(
        project_id: str, job_id: str, mode: str
    ) -> str:
        """
        Get comprehensive error analysis as a resource with specific response mode.

        Args:
            project_id: GitLab project ID
            job_id: GitLab job ID
            mode: Response mode - "minimal", "balanced", "fixing", or "full"

        Returns:
            Error analysis optimized for the specified mode
        """
        return await _get_error_analysis(project_id, job_id, mode)

    @mcp.resource("gl://error/{project_id}/{job_id}/{error_id}")
    async def get_individual_error_resource(
        project_id: str, job_id: str, error_id: str
    ) -> str:
        """
        Get individual error details from database.

        Args:
            project_id: GitLab project ID
            job_id: GitLab job ID
            error_id: Error ID or index (e.g., "error_0", "error_1")

        Returns:
            Detailed information about a specific error with navigation links
        """
        try:
            cache_manager = get_cache_manager()

            # Get all errors for the job from database
            all_errors = cache_manager.get_job_errors(int(job_id))

            # Find error by ID or index
            target_error = None
            if error_id.startswith("error_"):
                try:
                    error_index = int(error_id.split("_")[1])
                    if 0 <= error_index < len(all_errors):
                        target_error = all_errors[error_index]
                except (ValueError, IndexError):
                    pass
            else:
                # Find by actual error ID
                target_error = next(
                    (err for err in all_errors if str(err.get("id", "")) == error_id),
                    None,
                )

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
                return json.dumps(error_result, indent=2)

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
                "error_info": {
                    "id": target_error.get("id", error_id),
                    "job_id": int(job_id),
                    "project_id": project_id,
                    "file_path": target_error.get("file_path", "unknown"),
                    "line": target_error.get("line", 0),
                    "column": target_error.get("column", 0),
                    "exception": target_error.get("exception", "Unknown"),
                    "severity": target_error.get("severity", "error"),
                },
                "error_details": target_error,
                "resource_links": resource_links,
                "metadata": {
                    "resource_type": "individual_error",
                    "project_id": project_id,
                    "job_id": int(job_id),
                    "error_id": error_id,
                    "data_source": "database",
                    "cached_at": None,
                },
                "mcp_info": get_mcp_info("individual_error_resource"),
            }

            return json.dumps(result, indent=2)

        except Exception as e:
            logger.error(
                f"Error getting individual error resource {project_id}/{job_id}/{error_id}: {e}"
            )
            error_result = {
                "error": f"Failed to get individual error resource: {str(e)}",
                "project_id": project_id,
                "job_id": job_id,
                "error_id": error_id,
                "resource_uri": f"gl://error/{project_id}/{job_id}/{error_id}",
                "mcp_info": get_mcp_info("individual_error_resource"),
            }
            return json.dumps(error_result, indent=2)

    logger.info("Error resources registered")
