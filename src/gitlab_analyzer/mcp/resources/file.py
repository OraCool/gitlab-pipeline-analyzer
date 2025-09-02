"""
File resources for MCP server - Database-only version

Copyright (c) 2025 Siarhei Skuratovich
Licensed under the MIT License - see LICENSE file for details
"""

import logging
from datetime import datetime, timezone
from typing import Any

from mcp.types import TextResourceContents

from gitlab_analyzer.cache.mcp_cache import get_cache_manager

from .utils import create_text_resource

logger = logging.getLogger(__name__)


async def get_file_resource_with_trace(
    project_id: str,
    job_id: str,
    file_path: str,
    mode: str = "balanced",
    include_trace: str = "false",
) -> TextResourceContents:
    """Get file analysis using only database data - no live GitLab API calls."""
    try:
        cache_manager = get_cache_manager()

        # Handle include_trace parameter
        include_trace_str = str(include_trace).lower()

        # Create cache key
        cache_key = f"file_{project_id}_{job_id}_{file_path}_{mode}"

        # Try cache first
        cached_data = await cache_manager.get(cache_key)
        if cached_data:
            return create_text_resource(
                f"gl://file/{project_id}/{job_id}/{file_path}/trace?mode={mode}&include_trace={include_trace_str}",
                cached_data,
            )

        # Get file errors from database (pre-analyzed data)
        file_errors = cache_manager.get_file_errors(int(job_id), file_path)

        # Process database errors and enhance based on mode
        all_errors = []
        for db_error in file_errors:
            enhanced_error = db_error.copy()
            enhanced_error["source"] = "database"

            # Include trace content if requested and available
            if include_trace_str == "true":
                # Get trace excerpt for this specific error
                error_id = db_error.get("error_id")
                if error_id:
                    trace_excerpt = cache_manager.get_job_trace_excerpt(
                        int(job_id), error_id
                    )
                    if trace_excerpt:
                        enhanced_error["trace_excerpt"] = trace_excerpt

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

                # For fixing mode, also include trace context if not already included
                if include_trace_str != "true":
                    error_id = db_error.get("error_id")
                    if error_id:
                        trace_excerpt = cache_manager.get_job_trace_excerpt(
                            int(job_id), error_id
                        )
                        if trace_excerpt:
                            enhanced_error["trace_excerpt"] = trace_excerpt

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
                "include_trace": include_trace_str == "true",
                "data_source": "database_only",  # Clearly indicate data source
            },
            "job_context": {
                "job_id": int(job_id),
                "status": job_info.get("status") if job_info else "unknown",
                "name": job_info.get("name") if job_info else None,
            },
            "resource_uri": f"gl://file/{project_id}/{job_id}/{file_path}?mode={mode}&include_trace={include_trace_str}",
            "cached_at": datetime.now(timezone.utc).isoformat(),
            "metadata": {
                "total_errors": len(all_errors),
                "analysis_scope": "file",
                "file_type": _classify_file_type(file_path),
                "response_mode": mode,
            },
        }

        # Cache the result
        await cache_manager.set(cache_key, result)

        return create_text_resource(
            f"gl://file/{project_id}/{job_id}/{file_path}/trace?mode={mode}&include_trace={include_trace_str}",
            result,
        )

    except Exception as e:
        logger.error(
            f"Error getting file resource {project_id}/{job_id}/{file_path}: {e}"
        )
        error_result = {
            "error": str(e),
            "resource_uri": f"gl://file/{project_id}/{job_id}/{file_path}?mode={mode}&include_trace={include_trace_str}",
            "error_at": datetime.now(timezone.utc).isoformat(),
        }
        return create_text_resource(
            f"gl://file/{project_id}/{job_id}/{file_path}/trace?mode={mode}&include_trace={include_trace_str}",
            error_result,
        )


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
        key=cache_key,
        compute_func=compute_file_data,
        data_type="file_analysis",
        project_id=project_id,
        job_id=int(job_id),
    )


async def get_files_resource(
    project_id: str, job_id: str, page: int = 1, limit: int = 20
) -> dict[str, Any]:
    """Get files with errors for a job from database."""
    cache_manager = get_cache_manager()
    cache_key = f"files_{project_id}_{job_id}_{page}_{limit}"

    async def compute_files_data() -> dict[str, Any]:
        # Check if job exists in database first
        import aiosqlite

        async with aiosqlite.connect(cache_manager.db_path) as db:
            cursor = await db.execute(
                "SELECT job_id, pipeline_id, status FROM jobs WHERE job_id = ?",
                (int(job_id),),
            )
            job_row = await cursor.fetchone()

            if not job_row:
                return {
                    "files": [],
                    "pagination": {
                        "page": page,
                        "limit": limit,
                        "total": 0,
                        "total_pages": 0,
                    },
                    "error": f"Job {job_id} not found in database",
                    "recommendation": f"Job {job_id} has not been analyzed. Run failed_pipeline_analysis for the pipeline containing this job.",
                    "suggested_action": f"failed_pipeline_analysis(project_id={project_id}, pipeline_id=<pipeline_id>)",
                    "data_source": "database_only",
                }

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
        key=cache_key,
        compute_func=compute_files_data,
        data_type="job_files",
        project_id=project_id,
        job_id=int(job_id),
    )


async def get_pipeline_files_resource(
    project_id: str, pipeline_id: str, page: int = 1, limit: int = 20
) -> dict[str, Any]:
    """Get all files with errors across all jobs in a pipeline from database."""
    cache_manager = get_cache_manager()
    cache_key = f"pipeline_files_{project_id}_{pipeline_id}_{page}_{limit}"

    async def compute_pipeline_files_data() -> dict[str, Any]:
        # Check pipeline analysis status first
        analysis_status = await cache_manager.check_pipeline_analysis_status(
            int(project_id), int(pipeline_id)
        )

        if not analysis_status["pipeline_exists"]:
            return {
                "files": [],
                "pagination": {
                    "page": page,
                    "limit": limit,
                    "total": 0,
                    "total_pages": 0,
                },
                "error": "Pipeline not found in database",
                "recommendation": analysis_status["recommendation"],
                "suggested_action": analysis_status["suggested_action"],
                "data_source": "database_only",
            }

        if analysis_status["jobs_count"] == 0:
            return {
                "files": [],
                "pagination": {
                    "page": page,
                    "limit": limit,
                    "total": 0,
                    "total_pages": 0,
                },
                "warning": "No jobs found for this pipeline",
                "recommendation": analysis_status["recommendation"],
                "suggested_action": analysis_status["suggested_action"],
                "analysis_status": analysis_status,
                "data_source": "database_only",
            }

        if analysis_status["files_count"] == 0:
            return {
                "files": [],
                "pagination": {
                    "page": page,
                    "limit": limit,
                    "total": 0,
                    "total_pages": 0,
                },
                "info": f"Pipeline has {analysis_status['jobs_count']} jobs and {analysis_status['errors_count']} errors, but no files with errors found",
                "recommendation": analysis_status["recommendation"],
                "analysis_status": analysis_status,
                "data_source": "database_only",
            }

        # Get all jobs for this pipeline
        pipeline_jobs = await cache_manager.get_pipeline_jobs(int(pipeline_id))

        if not pipeline_jobs:
            return {
                "files": [],
                "pagination": {
                    "page": page,
                    "limit": limit,
                    "total": 0,
                    "total_pages": 0,
                },
                "jobs_analyzed": 0,
                "data_source": "database_only",
            }

        # Get files with errors from all jobs
        all_files_with_errors = {}  # Use dict to deduplicate by file path
        jobs_with_errors = 0

        for job in pipeline_jobs:
            job_id = job.get("job_id")
            if not job_id:
                continue

            job_files = await cache_manager.get_job_files_with_errors(int(job_id))
            if job_files:
                jobs_with_errors += 1
                for file_info in job_files:
                    file_path = file_info.get("file_path")
                    if file_path:
                        if file_path not in all_files_with_errors:
                            all_files_with_errors[file_path] = {
                                "file_path": file_path,
                                "total_errors": 0,
                                "jobs_with_errors": [],
                                "first_error": None,
                            }

                        # Aggregate error info
                        file_errors = file_info.get("errors", [])
                        all_files_with_errors[file_path]["total_errors"] += len(
                            file_errors
                        )
                        all_files_with_errors[file_path]["jobs_with_errors"].append(
                            {
                                "job_id": job_id,
                                "job_name": job.get("name"),
                                "error_count": len(file_errors),
                            }
                        )

                        # Store first error for reference
                        if (
                            not all_files_with_errors[file_path]["first_error"]
                            and file_errors
                        ):
                            all_files_with_errors[file_path]["first_error"] = (
                                file_errors[0]
                            )

        # Convert to list and sort by total errors (most problematic first)
        files_list = list(all_files_with_errors.values())
        files_list.sort(key=lambda x: x["total_errors"], reverse=True)

        # Apply pagination
        start_idx = (page - 1) * limit
        end_idx = start_idx + limit
        paginated_files = files_list[start_idx:end_idx]

        return {
            "files": paginated_files,
            "pagination": {
                "page": page,
                "limit": limit,
                "total": len(files_list),
                "total_pages": (len(files_list) + limit - 1) // limit,
            },
            "summary": {
                "total_files_with_errors": len(files_list),
                "total_jobs_in_pipeline": len(pipeline_jobs),
                "jobs_with_errors": jobs_with_errors,
                "total_errors": sum(f["total_errors"] for f in files_list),
            },
            "data_source": "database_only",
        }

    return await cache_manager.get_or_compute(
        key=cache_key,
        compute_func=compute_pipeline_files_data,
        data_type="pipeline_files",
        project_id=project_id,
        pipeline_id=int(pipeline_id),
    )


def register_file_resources(mcp) -> None:
    """Register file resources with MCP server"""

    @mcp.resource("gl://files/{project_id}/pipeline/{pipeline_id}")
    async def get_pipeline_files_resource_handler(
        project_id: str, pipeline_id: str
    ) -> TextResourceContents:
        """
        Get all files with errors across all jobs in a pipeline from database only.

        Returns a comprehensive list of files that have errors in any job within the pipeline,
        aggregated with error counts and job information.
        Uses only pre-analyzed data from the database cache.
        """
        result = await get_pipeline_files_resource(project_id, pipeline_id)
        return create_text_resource(
            f"gl://files/{project_id}/pipeline/{pipeline_id}", result
        )

    @mcp.resource(
        "gl://files/{project_id}/pipeline/{pipeline_id}/page/{page}/limit/{limit}"
    )
    async def get_pipeline_files_resource_paginated(
        project_id: str, pipeline_id: str, page: str, limit: str
    ) -> TextResourceContents:
        """
        Get paginated list of files with errors across all jobs in a pipeline from database only.
        """
        try:
            page_num = int(page)
            limit_num = int(limit)
        except ValueError:
            return create_text_resource(
                f"gl://files/{project_id}/pipeline/{pipeline_id}/page/{page}/limit/{limit}",
                {"error": "Invalid page or limit parameter"},
            )

        result = await get_pipeline_files_resource(
            project_id, pipeline_id, page_num, limit_num
        )
        return create_text_resource(
            f"gl://files/{project_id}/pipeline/{pipeline_id}/page/{page}/limit/{limit}",
            result,
        )

    @mcp.resource("gl://file/{project_id}/{job_id}/{file_path}")
    async def get_file_resource_handler(
        project_id: str, job_id: str, file_path: str
    ) -> TextResourceContents:
        """
        Get file analysis data from database only.

        Returns error analysis for a specific file in a GitLab CI job.
        Uses only pre-analyzed data from the database cache.
        """
        result = await get_file_resource(project_id, job_id, file_path)
        return create_text_resource(
            f"gl://file/{project_id}/{job_id}/{file_path}", result
        )

    @mcp.resource("gl://files/{project_id}/{job_id}")
    async def get_files_resource_handler(
        project_id: str, job_id: str
    ) -> TextResourceContents:
        """
        Get list of files with errors for a job from database only.

        Returns a list of all files that have errors in the specified job.
        Uses only pre-analyzed data from the database cache.
        """
        result = await get_files_resource(project_id, job_id)
        return create_text_resource(f"gl://files/{project_id}/{job_id}", result)

    @mcp.resource("gl://files/{project_id}/{job_id}/page/{page}/limit/{limit}")
    async def get_files_resource_paginated(
        project_id: str, job_id: str, page: str, limit: str
    ) -> TextResourceContents:
        """
        Get paginated list of files with errors for a job from database only.
        """
        try:
            page_num = int(page)
            limit_num = int(limit)
        except ValueError:
            return create_text_resource(
                f"gl://files/{project_id}/{job_id}/page/{page}/limit/{limit}",
                {"error": "Invalid page or limit parameter"},
            )

        result = await get_files_resource(project_id, job_id, page_num, limit_num)
        return create_text_resource(
            f"gl://files/{project_id}/{job_id}/page/{page}/limit/{limit}", result
        )

    @mcp.resource(
        "gl://file/{project_id}/{job_id}/{file_path}/trace?mode={mode}&include_trace={include_trace}"
    )
    async def get_file_resource_with_trace_handler(
        project_id: str, job_id: str, file_path: str, mode: str, include_trace: str
    ) -> TextResourceContents:
        """
        Get file analysis with enhanced error information from database.

        Args:
            mode: Analysis mode (minimal, balanced, fixing, full)
            include_trace: Whether to include trace context (true/false) - retrieves stored trace segments
        """
        result = await get_file_resource_with_trace(
            project_id, job_id, file_path, mode, include_trace
        )
        return result


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
