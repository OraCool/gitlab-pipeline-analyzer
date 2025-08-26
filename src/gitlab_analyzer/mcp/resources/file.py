"""
File resources for MCP server - Database-only version

Copyright (c) 2025 Siarhei Skuratovich
Licensed under the MIT License - see LICENSE file for details
"""

import json
import logging
from datetime import UTC, datetime
from typing import Any

from gitlab_analyzer.cache.mcp_cache import get_cache_manager

logger = logging.getLogger(__name__)


async def get_file_resource_with_trace(
    project_id: str,
    job_id: str,
    file_path: str,
    mode: str = "balanced",
    include_trace: str = "false",
) -> str:
    """Get file analysis using only database data - no live GitLab API calls."""
    try:
        cache_manager = get_cache_manager()

        # Create cache key
        cache_key = f"file_{project_id}_{job_id}_{file_path}_{mode}"

        # Try cache first
        cached_data = await cache_manager.get(cache_key)
        if cached_data:
            return json.dumps(cached_data, indent=2)

        # Get file errors from database (pre-analyzed data)
        file_errors = cache_manager.get_file_errors(int(job_id), file_path)

        # Process database errors and enhance based on mode
        all_errors = []
        for db_error in file_errors:
            enhanced_error = db_error.copy()
            enhanced_error["source"] = "database"

            # Generate fix guidance if requested
            if mode == "fixing":
                from gitlab_analyzer.utils.utils import _generate_fix_guidance

                # Map database error fields to what fix guidance generator expects
                fix_guidance_error = {
                    "exception_type": db_error.get("exception", ""),
                    "exception_message": db_error.get("message", ""),
                    "line": db_error.get("line", 0),
                    "file_path": db_error.get("file_path", ""),
                    # Include detail fields if available
                    **db_error.get("detail", {}),
                }
                enhanced_error["fix_guidance"] = _generate_fix_guidance(
                    fix_guidance_error
                )

            all_errors.append(enhanced_error)

        # Get job info for context
        job_info = await cache_manager.get_job_info_async(int(job_id))

        # Build result
        result = {
            "file_analysis": {
                "project_id": project_id,
                "job_id": int(job_id),
                "file_path": file_path,
                "errors": all_errors,
                "error_count": len(all_errors),
                "analysis_mode": mode,
                "include_trace": include_trace.lower() == "true",
                "data_source": "database_only",  # Clearly indicate data source
            },
            "job_context": {
                "job_id": int(job_id),
                "status": job_info.get("status") if job_info else "unknown",
                "name": job_info.get("name") if job_info else None,
            },
            "resource_uri": f"gl://file/{project_id}/{job_id}/{file_path}?mode={mode}&include_trace={include_trace}",
            "cached_at": datetime.now(UTC).isoformat(),
            "metadata": {
                "total_errors": len(all_errors),
                "analysis_scope": "file",
                "file_type": _classify_file_type(file_path),
                "response_mode": mode,
            },
        }

        # Cache the result
        await cache_manager.set(cache_key, result)

        return json.dumps(result, indent=2)

    except Exception as e:
        logger.error(
            f"Error getting file resource {project_id}/{job_id}/{file_path}: {e}"
        )
        error_result = {
            "error": str(e),
            "resource_uri": f"gl://file/{project_id}/{job_id}/{file_path}?mode={mode}&include_trace={include_trace}",
            "error_at": datetime.now(UTC).isoformat(),
        }
        return json.dumps(error_result, indent=2)


async def get_file_resource(
    project_id: str, job_id: str, file_path: str
) -> dict[str, Any]:
    """Get file resource using database data only."""
    cache_manager = get_cache_manager()

    cache_key = f"file_{project_id}_{job_id}_{file_path}_simple"

    async def compute_file_data() -> dict[str, Any]:
        # Get file errors from database
        file_errors = cache_manager.get_file_errors(int(job_id), file_path)

        return {
            "file_path": file_path,
            "errors": file_errors,
            "error_count": len(file_errors),
            "data_source": "database_only",
        }

    return await cache_manager.get_or_compute(
        cache_key, compute_file_data, ttl_seconds=300
    )


async def get_files_resource(
    project_id: str, job_id: str, page: int = 1, limit: int = 20
) -> dict[str, Any]:
    """Get files with errors for a job from database."""
    cache_manager = get_cache_manager()
    cache_key = f"files_{project_id}_{job_id}_{page}_{limit}"

    async def compute_files_data() -> dict[str, Any]:
        # Get all files with errors for this job
        files_with_errors = await cache_manager.get_job_files_with_errors(int(job_id))

        # Apply pagination
        start_idx = (page - 1) * limit
        end_idx = start_idx + limit
        paginated_files = files_with_errors[start_idx:end_idx]

        return {
            "files": paginated_files,
            "pagination": {
                "page": page,
                "limit": limit,
                "total": len(files_with_errors),
                "total_pages": (len(files_with_errors) + limit - 1) // limit,
            },
            "data_source": "database_only",
        }

    return await cache_manager.get_or_compute(
        cache_key, compute_files_data, ttl_seconds=300
    )


def register_file_resources(mcp) -> None:
    """Register file resources with MCP server"""

    @mcp.resource("gl://file/{project_id}/{job_id}/{file_path}")
    async def get_file_resource_handler(
        project_id: str, job_id: str, file_path: str
    ) -> str:
        """
        Get file analysis data from database only.

        Returns error analysis for a specific file in a GitLab CI job.
        Uses only pre-analyzed data from the database cache.
        """
        result = await get_file_resource(project_id, job_id, file_path)
        return json.dumps(result, indent=2)

    @mcp.resource("gl://files/{project_id}/{job_id}")
    async def get_files_resource_handler(project_id: str, job_id: str) -> str:
        """
        Get list of files with errors for a job from database only.

        Returns a list of all files that have errors in the specified job.
        Uses only pre-analyzed data from the database cache.
        """
        result = await get_files_resource(project_id, job_id)
        return json.dumps(result, indent=2)

    @mcp.resource("gl://files/{project_id}/{job_id}/page/{page}/limit/{limit}")
    async def get_files_resource_paginated(
        project_id: str, job_id: str, page: str, limit: str
    ) -> str:
        """
        Get paginated list of files with errors for a job from database only.
        """
        try:
            page_num = int(page)
            limit_num = int(limit)
        except ValueError:
            return json.dumps({"error": "Invalid page or limit parameter"}, indent=2)

        result = await get_files_resource(project_id, job_id, page_num, limit_num)
        return json.dumps(result, indent=2)

    @mcp.resource(
        "gl://file/{project_id}/{job_id}/{file_path}/trace?mode={mode}&include_trace={include_trace}"
    )
    async def get_file_resource_with_trace_handler(
        project_id: str, job_id: str, file_path: str, mode: str, include_trace: str
    ) -> str:
        """
        Get file analysis with enhanced error information from database only.

        Args:
            mode: Analysis mode (minimal, balanced, fixing, full)
            include_trace: Whether to include trace context (true/false) - Currently ignored as we use database only
        """
        return await get_file_resource_with_trace(
            project_id, job_id, file_path, mode, include_trace
        )


def _classify_file_type(file_path: str) -> str:
    """Classify file type based on path and extension"""
    if "test" in file_path.lower() or file_path.endswith(("_test.py", "test_*.py")):
        return "test"
    elif file_path.endswith(".py"):
        return "python"
    elif file_path.endswith((".js", ".ts", ".jsx", ".tsx")):
        return "javascript"
    elif file_path.endswith((".yml", ".yaml")):
        return "yaml"
    elif file_path.endswith(".json"):
        return "json"
    elif file_path.endswith((".md", ".rst", ".txt")):
        return "documentation"
    else:
        return "other"
