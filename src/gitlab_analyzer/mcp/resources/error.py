"""
Error resources for MCP server

Copyright (c) 2025 Siarhei Skuratovich
Licensed under the MIT License - see LICENSE file for details
"""

import json
import logging
from datetime import UTC, datetime

from ..cache import get_cache_manager
from ..tools.utils import get_gitlab_analyzer, get_mcp_info

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
        from ..tools.utils import optimize_tool_response

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

    logger.info("Error resources registered")
