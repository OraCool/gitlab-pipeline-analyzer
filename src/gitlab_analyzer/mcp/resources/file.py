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
from gitlab_analyzer.utils.debug import (
    debug_print,
    verbose_debug_print,
    very_verbose_debug_print,
)

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
    verbose_debug_print(
        f"Getting file resource with trace: project_id={project_id}, job_id={job_id}, file_path={file_path}, mode={mode}, include_trace={include_trace}"
    )

    try:
        cache_manager = get_cache_manager()

        # Handle include_trace parameter safely
        include_trace_str = str(include_trace or "false").lower()

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

        # Deduplicate errors based on key characteristics to avoid showing identical errors
        deduplicated_errors = _deduplicate_errors(file_errors)

        # Apply error limits based on mode to prevent overwhelming responses
        limited_errors = _apply_error_limits(deduplicated_errors, mode)

        # Optimize errors based on mode (using existing utility)
        from gitlab_analyzer.utils.utils import optimize_error_response

        optimized_errors = [
            optimize_error_response(error, mode) for error in limited_errors
        ]

        # Process database errors and enhance based on mode
        all_errors = []
        for error in optimized_errors:
            enhanced_error = error.copy()
            enhanced_error["source"] = "database"

            # Include trace content if requested and available
            if include_trace_str == "true":
                # Get trace excerpt for this specific error
                error_id = error.get("error_id")
                if error_id:
                    trace_excerpt = cache_manager.get_job_trace_excerpt(
                        int(job_id), error_id
                    )
                    if trace_excerpt:
                        enhanced_error["trace_excerpt"] = trace_excerpt

            # Generate fix guidance if requested
            if mode == "fixing":
                try:
                    from gitlab_analyzer.utils.utils import _generate_fix_guidance

                    # Map database error fields to what fix guidance generator expects
                    fix_guidance_error = {
                        "exception_type": error.get(
                            "exception_type", error.get("exception", "")
                        ),
                        "exception_message": error.get(
                            "exception_message", error.get("message", "")
                        ),
                        "line": error.get("line_number", error.get("line", 0)),
                        "file_path": error.get("file_path", ""),
                    }

                    # Include detail fields if available (safely handle None case)
                    detail = error.get("detail")
                    if detail and isinstance(detail, dict):
                        fix_guidance_error.update(detail)

                    enhanced_error["fix_guidance"] = _generate_fix_guidance(
                        fix_guidance_error
                    )
                except Exception as e:
                    logger.warning(f"Failed to generate fix guidance for error: {e}")
                    enhanced_error["fix_guidance_error"] = str(e)

                # For fixing mode, also include trace context if not already included
                if include_trace_str != "true":
                    try:
                        error_id = error.get("error_id")
                        if error_id:
                            trace_excerpt = cache_manager.get_job_trace_excerpt(
                                int(job_id), error_id
                            )
                            if trace_excerpt:
                                enhanced_error["trace_excerpt"] = trace_excerpt
                    except Exception as e:
                        logger.warning(
                            f"Failed to get trace excerpt for error {error_id}: {e}"
                        )
                        enhanced_error["trace_excerpt_error"] = str(e)

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
                "total_errors_raw": len(
                    file_errors
                ),  # Original count before processing
                "total_errors_after_dedup": len(
                    deduplicated_errors
                ),  # After deduplication
                "total_errors_displayed": len(
                    all_errors
                ),  # Final count after all processing
                "errors_limited": len(limited_errors)
                < len(deduplicated_errors),  # Whether limiting was applied
                "analysis_scope": "file",
                "file_type": _classify_file_type(file_path),
                "response_mode": mode,
                "deduplication_applied": len(file_errors) > len(deduplicated_errors),
            },
        }

        # Cache the result
        await cache_manager.set(cache_key, result)

        return create_text_resource(
            f"gl://file/{project_id}/{job_id}/{file_path}/trace?mode={mode}&include_trace={include_trace_str}",
            result,
        )

    except (ValueError, KeyError, TypeError) as e:
        logger.error(
            "Error getting file resource %s/%s/%s: %s", project_id, job_id, file_path, e
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
    debug_print(
        f"Getting file resource: project_id={project_id}, job_id={job_id}, file_path={file_path}"
    )

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
    debug_print(
        f"Getting files for job: project_id={project_id}, job_id={job_id}, page={page}, limit={limit}"
    )

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


async def get_pipeline_files_resource_enhanced(
    project_id: str,
    pipeline_id: str,
    page: int = 1,
    limit: int = 20,
    mode: str = "balanced",
    include_trace: bool = False,
    max_errors_per_file: int = 5,
) -> dict[str, Any]:
    """Get all files with errors across all jobs in a pipeline with enhanced mode and trace support."""
    very_verbose_debug_print(
        f"Enhanced pipeline files analysis: project_id={project_id}, pipeline_id={pipeline_id}, page={page}, limit={limit}, mode={mode}, include_trace={include_trace}, max_errors_per_file={max_errors_per_file}"
    )

    from gitlab_analyzer.utils.utils import _generate_fix_guidance

    cache_manager = get_cache_manager()
    cache_key = f"pipeline_files_enhanced_{project_id}_{pipeline_id}_{page}_{limit}_{mode}_{include_trace}_{max_errors_per_file}"

    async def compute_enhanced_pipeline_files_data() -> dict[str, Any]:
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
                "mode": mode,
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
                "mode": mode,
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
                "mode": mode,
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
                "mode": mode,
            }

        # Get files with errors from all jobs with enhanced processing
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
                                "enhanced_errors": [],  # New: Enhanced error details
                                "file_type": _classify_file_type(
                                    file_path
                                ),  # New: File classification
                            }

                        # Process errors with enhancement based on mode
                        file_errors = file_info.get("errors", [])
                        enhanced_errors = []

                        for error in file_errors[
                            :max_errors_per_file
                        ]:  # Limit errors per file
                            enhanced_error = error.copy()

                            # Add trace information if requested
                            if include_trace:
                                error_id = error.get("error_id")
                                if error_id:
                                    trace_excerpt = cache_manager.get_job_trace_excerpt(
                                        int(job_id), error_id, mode
                                    )
                                    if trace_excerpt:
                                        enhanced_error["trace_excerpt"] = trace_excerpt

                            # Add fix guidance for fixing mode
                            if mode == "fixing":
                                fix_guidance_error = {
                                    "exception_type": error.get("exception", ""),
                                    "exception_message": error.get("message", ""),
                                    "line": error.get("line", 0),
                                    "file_path": error.get("file_path", ""),
                                    **error.get("detail", {}),
                                }
                                enhanced_error["fix_guidance"] = _generate_fix_guidance(
                                    fix_guidance_error
                                )

                            # Add job context
                            enhanced_error["job_context"] = {
                                "job_id": job_id,
                                "job_name": job.get("name"),
                                "job_stage": job.get("stage"),
                            }

                            enhanced_errors.append(enhanced_error)

                        # Aggregate error info
                        all_files_with_errors[file_path]["total_errors"] += len(
                            file_errors
                        )
                        all_files_with_errors[file_path]["enhanced_errors"].extend(
                            enhanced_errors
                        )
                        all_files_with_errors[file_path]["jobs_with_errors"].append(
                            {
                                "job_id": job_id,
                                "job_name": job.get("name"),
                                "job_stage": job.get("stage"),
                                "error_count": len(file_errors),
                            }
                        )

                        # Store first error for reference
                        if (
                            not all_files_with_errors[file_path]["first_error"]
                            and enhanced_errors
                        ):
                            all_files_with_errors[file_path]["first_error"] = (
                                enhanced_errors[0]
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
            "analysis_mode": mode,
            "include_trace": include_trace,
            "max_errors_per_file": max_errors_per_file,
            "data_source": "database_only",
        }

    return await cache_manager.get_or_compute(
        key=cache_key,
        compute_func=compute_enhanced_pipeline_files_data,
        data_type="pipeline_files_enhanced",
        project_id=project_id,
        pipeline_id=int(pipeline_id),
    )


async def get_pipeline_files_resource(
    project_id: str, pipeline_id: str, page: int = 1, limit: int = 20
) -> dict[str, Any]:
    """Get all files with errors across all jobs in a pipeline from database."""
    verbose_debug_print(
        f"Getting pipeline files: project_id={project_id}, pipeline_id={pipeline_id}, page={page}, limit={limit}"
    )

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


async def get_pipeline_file_errors_resource(
    project_id: str,
    pipeline_id: str,
    file_path: str,
    mode: str = "balanced",
    include_trace: bool = False,
) -> dict[str, Any]:
    """Get errors for a specific file across all jobs in a pipeline.

    Args:
        project_id: The GitLab project ID
        pipeline_id: The GitLab pipeline ID
        file_path: The specific file path to get errors for
        mode: Analysis mode (minimal, balanced, fixing, detailed)
        include_trace: Whether to include trace context

    Returns:
        Dict containing file errors across all pipeline jobs
    """
    from gitlab_analyzer.utils.utils import _generate_fix_guidance

    debug_print(
        f"Getting pipeline file errors for project_id={project_id}, pipeline_id={pipeline_id}, file_path={file_path}, mode={mode}, include_trace={include_trace}"
    )

    cache_manager = get_cache_manager()

    # Get all jobs in the pipeline
    pipeline_jobs = await cache_manager.get_pipeline_jobs(int(pipeline_id))
    if not pipeline_jobs:
        return {
            "error": "pipeline_not_analyzed",
            "message": f"Pipeline {pipeline_id} has not been analyzed yet.",
            "file_path": file_path,
            "pipeline_id": int(pipeline_id),
            "project_id": project_id,
        }

    # Collect errors for this file across all jobs
    all_file_errors = []
    jobs_with_file = []

    for job in pipeline_jobs:
        job_id = job["job_id"]

        # Get errors for this file in this job
        file_errors = cache_manager.get_file_errors(job_id, file_path)
        if file_errors:
            jobs_with_file.append(
                {
                    "job_id": job_id,
                    "job_name": job.get("name", f"job-{job_id}"),
                    "job_status": job.get("status", "unknown"),
                    "error_count": len(file_errors),
                }
            )

            # Add job context to each error
            for error in file_errors:
                error_with_context = dict(error)
                error_with_context["job_id"] = job_id
                error_with_context["job_name"] = job.get("name", f"job-{job_id}")
                all_file_errors.append(error_with_context)

    if not all_file_errors:
        return {
            "file_path": file_path,
            "pipeline_id": int(pipeline_id),
            "project_id": project_id,
            "total_errors": 0,
            "jobs_analyzed": len(pipeline_jobs),
            "jobs_with_errors": 0,
            "message": f"No errors found for file '{file_path}' across pipeline {pipeline_id}",
            "navigation": {
                "pipeline": f"gl://pipeline/{project_id}/{pipeline_id}",
                "all_files": f"gl://files/{project_id}/pipeline/{pipeline_id}",
            },
        }

    # Optimize errors based on mode
    from gitlab_analyzer.utils.utils import optimize_error_response

    optimized_errors = [
        optimize_error_response(error, mode) for error in all_file_errors
    ]

    # Group errors by type and severity
    error_groups: dict[str, list[dict[str, Any]]] = {}
    for error in optimized_errors:
        error_type = error.get("category", "unknown")
        if error_type not in error_groups:
            error_groups[error_type] = []
        error_groups[error_type].append(error)

    # Generate fix guidance if in fixing mode
    fix_guidance = None
    if mode == "fixing" and optimized_errors:
        # Generate fix guidance for the first error as an example
        first_error = optimized_errors[0]
        fix_guidance = _generate_fix_guidance(first_error)

    result = {
        "file_path": file_path,
        "pipeline_id": int(pipeline_id),
        "project_id": project_id,
        "mode": mode,
        "include_trace": include_trace,
        "total_errors": len(all_file_errors),
        "displayed_errors": len(optimized_errors),
        "jobs_analyzed": len(pipeline_jobs),
        "jobs_with_errors": len(jobs_with_file),
        "error_groups": error_groups,
        "errors": optimized_errors,
        "file_type": _classify_file_type(file_path),
        "navigation": {
            "pipeline": f"gl://pipeline/{project_id}/{pipeline_id}",
            "all_files": f"gl://files/{project_id}/pipeline/{pipeline_id}",
            "pipeline_errors": f"gl://errors/{project_id}/pipeline/{pipeline_id}",
            "file_jobs": f"gl://file/{project_id}/pipeline/{pipeline_id}/{file_path}/jobs",
        },
    }

    if fix_guidance:
        result["fix_guidance"] = fix_guidance

    # Add trace information if requested
    if include_trace and optimized_errors:
        trace_segments = []
        for error in optimized_errors[:5]:  # Limit trace to top 5 errors
            if "job_id" in error:
                segments = cache_manager.get_error_trace_segments(
                    error["job_id"], error.get("error_id")
                )
                if segments:
                    trace_segments.extend(segments)

        if trace_segments:
            result["trace_segments"] = trace_segments[:20]  # Limit total segments

    return result


async def get_pipeline_file_jobs_resource(
    project_id: str,
    pipeline_id: str,
    file_path: str,
) -> dict[str, Any]:
    """Get jobs that contain errors for a specific file in a pipeline.

    Args:
        project_id: The GitLab project ID
        pipeline_id: The GitLab pipeline ID
        file_path: The specific file path to get jobs for

    Returns:
        Dict containing jobs that have errors for this file
    """
    verbose_debug_print(
        f"Getting pipeline file jobs: project_id={project_id}, pipeline_id={pipeline_id}, file_path={file_path}"
    )

    cache_manager = get_cache_manager()

    # Get all jobs in the pipeline
    pipeline_jobs = await cache_manager.get_pipeline_jobs(int(pipeline_id))
    if not pipeline_jobs:
        return {
            "error": "pipeline_not_analyzed",
            "message": f"Pipeline {pipeline_id} has not been analyzed yet.",
            "file_path": file_path,
            "pipeline_id": int(pipeline_id),
            "project_id": project_id,
        }

    # Collect jobs that have errors for this file
    jobs_with_file = []

    for job in pipeline_jobs:
        job_id = job["job_id"]

        # Get errors for this file in this job
        file_errors = cache_manager.get_file_errors(job_id, file_path)
        if file_errors:
            jobs_with_file.append(
                {
                    "job_id": job_id,
                    "job_name": job.get("name", f"job-{job_id}"),
                    "job_status": job.get("status", "unknown"),
                    "error_count": len(file_errors),
                    "job_url": job.get("web_url"),
                    "stage": job.get("stage"),
                    "created_at": job.get("created_at"),
                    "finished_at": job.get("finished_at"),
                }
            )

    result = {
        "file_path": file_path,
        "pipeline_id": int(pipeline_id),
        "project_id": project_id,
        "total_jobs": len(pipeline_jobs),
        "jobs_with_file": len(jobs_with_file),
        "jobs": jobs_with_file,
        "navigation": {
            "pipeline": f"gl://pipeline/{project_id}/{pipeline_id}",
            "file_errors": f"gl://file/{project_id}/pipeline/{pipeline_id}/{file_path}",
            "all_files": f"gl://files/{project_id}/pipeline/{pipeline_id}",
        },
    }

    return result


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

    @mcp.resource(
        "gl://files/{project_id}/pipeline/{pipeline_id}/enhanced?mode={mode}&include_trace={include_trace}&max_errors_per_file={max_errors_per_file}"
    )
    async def get_pipeline_files_resource_enhanced_handler(
        project_id: str,
        pipeline_id: str,
        mode: str,
        include_trace: str,
        max_errors_per_file: str,
    ) -> TextResourceContents:
        """
        Get enhanced list of files with errors across all jobs in a pipeline.

        Args:
            mode: Analysis mode (minimal, balanced, fixing, detailed)
            include_trace: Whether to include trace context (true/false)
            max_errors_per_file: Maximum errors to show per file (number)
        """
        try:
            include_trace_bool = (include_trace or "false").lower() == "true"
            max_errors_num = int(max_errors_per_file)
        except (ValueError, AttributeError):
            return create_text_resource(
                f"gl://files/{project_id}/pipeline/{pipeline_id}/enhanced?mode={mode}&include_trace={include_trace}&max_errors_per_file={max_errors_per_file}",
                {
                    "error": "Invalid parameters: include_trace must be 'true'/'false', max_errors_per_file must be a number"
                },
            )

        result = await get_pipeline_files_resource_enhanced(
            project_id,
            pipeline_id,
            page=1,
            limit=20,
            mode=mode,
            include_trace=include_trace_bool,
            max_errors_per_file=max_errors_num,
        )
        return create_text_resource(
            f"gl://files/{project_id}/pipeline/{pipeline_id}/enhanced?mode={mode}&include_trace={include_trace}&max_errors_per_file={max_errors_per_file}",
            result,
        )

    @mcp.resource(
        "gl://files/{project_id}/pipeline/{pipeline_id}/enhanced/page/{page}/limit/{limit}?mode={mode}&include_trace={include_trace}&max_errors_per_file={max_errors_per_file}"
    )
    async def get_pipeline_files_resource_enhanced_paginated(
        project_id: str,
        pipeline_id: str,
        page: str,
        limit: str,
        mode: str,
        include_trace: str,
        max_errors_per_file: str,
    ) -> TextResourceContents:
        """
        Get enhanced paginated list of files with errors across all jobs in a pipeline.
        """
        try:
            page_num = int(page)
            limit_num = int(limit)
            include_trace_bool = (include_trace or "false").lower() == "true"
            max_errors_num = int(max_errors_per_file)
        except (ValueError, AttributeError):
            return create_text_resource(
                f"gl://files/{project_id}/pipeline/{pipeline_id}/enhanced/page/{page}/limit/{limit}?mode={mode}&include_trace={include_trace}&max_errors_per_file={max_errors_per_file}",
                {"error": "Invalid parameters"},
            )

        result = await get_pipeline_files_resource_enhanced(
            project_id,
            pipeline_id,
            page_num,
            limit_num,
            mode=mode,
            include_trace=include_trace_bool,
            max_errors_per_file=max_errors_num,
        )
        return create_text_resource(
            f"gl://files/{project_id}/pipeline/{pipeline_id}/enhanced/page/{page}/limit/{limit}?mode={mode}&include_trace={include_trace}&max_errors_per_file={max_errors_per_file}",
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

    @mcp.resource("gl://file/{project_id}/pipeline/{pipeline_id}/{file_path}")
    async def get_pipeline_file_errors_resource_handler(
        project_id: str, pipeline_id: str, file_path: str
    ) -> TextResourceContents:
        """
        Get errors for a specific file across all jobs in a pipeline.
        Supports trace requests by detecting '/trace' suffix in file_path.
        Note: Query parameters should be handled by resource_access_tools.py for proper parsing.
        """
        # Parse file path to detect trace requests
        actual_file_path = file_path
        mode = "balanced"  # Default mode
        include_trace = False  # Default trace setting

        if file_path.endswith("/trace"):
            actual_file_path = file_path[:-6]  # Remove "/trace"
            mode = "fixing"  # Use fixing mode for trace requests
            include_trace = True  # Enable trace for trace requests

        result = await get_pipeline_file_errors_resource(
            project_id, pipeline_id, actual_file_path, mode, include_trace
        )
        return create_text_resource(
            f"gl://file/{project_id}/pipeline/{pipeline_id}/{file_path}", result
        )

    @mcp.resource(
        "gl://file/{project_id}/pipeline/{pipeline_id}/{file_path}/trace?mode={mode}&include_trace={include_trace}"
    )
    async def get_pipeline_file_trace_resource_handler_with_params(
        project_id: str, pipeline_id: str, file_path: str, mode: str, include_trace: str
    ) -> TextResourceContents:
        """
        Get errors with trace for a specific file across all jobs in a pipeline.
        This handles the /trace suffix with configurable mode and trace parameters.
        """
        # Parse include_trace parameter
        include_trace_bool = str(include_trace or "true").lower() == "true"

        result = await get_pipeline_file_errors_resource(
            project_id, pipeline_id, file_path, mode or "fixing", include_trace_bool
        )
        return create_text_resource(
            f"gl://file/{project_id}/pipeline/{pipeline_id}/{file_path}/trace?mode={mode}&include_trace={include_trace}",
            result,
        )

    @mcp.resource("gl://file/{project_id}/pipeline/{pipeline_id}/{file_path}/trace")
    async def get_pipeline_file_trace_resource_handler(
        project_id: str, pipeline_id: str, file_path: str
    ) -> TextResourceContents:
        """
        Get errors with trace for a specific file across all jobs in a pipeline.
        This handles the /trace suffix explicitly with default fixing mode.
        Fallback for URIs without query parameters.
        """
        # For trace requests, use fixing mode and enable trace by default
        result = await get_pipeline_file_errors_resource(
            project_id, pipeline_id, file_path, "fixing", True
        )
        return create_text_resource(
            f"gl://file/{project_id}/pipeline/{pipeline_id}/{file_path}/trace", result
        )

    @mcp.resource("gl://file/{project_id}/pipeline/{pipeline_id}/{file_path}/jobs")
    async def get_pipeline_file_jobs_resource_handler(
        project_id: str, pipeline_id: str, file_path: str
    ) -> TextResourceContents:
        """
        Get jobs that contain errors for a specific file in a pipeline.
        """
        result = await get_pipeline_file_jobs_resource(
            project_id, pipeline_id, file_path
        )
        return create_text_resource(
            f"gl://file/{project_id}/pipeline/{pipeline_id}/{file_path}/jobs", result
        )

    # Note: Pipeline file with trace is handled by resource_access_tools.py
    # The MCP resource pattern with query parameters doesn't work reliably,
    # so we let the resource access tool parse the URI and call get_pipeline_file_errors_resource directly


def _deduplicate_errors(errors: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Remove duplicate errors based on key characteristics."""
    if not errors:
        return errors

    seen = set()
    unique_errors = []

    for error in errors:
        # Create a unique key based on error characteristics
        error_key = (
            error.get("file_path", ""),
            error.get("line", 0),
            error.get("exception", ""),
            error.get("message", ""),
            error.get("test_function", ""),
        )

        if error_key not in seen:
            seen.add(error_key)
            unique_errors.append(error)

    return unique_errors


def _apply_error_limits(
    errors: list[dict[str, Any]], mode: str
) -> list[dict[str, Any]]:
    """Apply error limits based on analysis mode to prevent overwhelming responses."""
    if not errors:
        return errors

    # Define limits based on mode
    limits = {
        "minimal": 10,  # Very focused view
        "balanced": 25,  # Good balance of detail and performance
        "fixing": 50,  # More errors for comprehensive fixing
        "detailed": 100,  # Most comprehensive view
    }

    limit = limits.get(mode, 25)  # Default to balanced mode limit

    # Sort errors by severity/importance for better prioritization
    # Prioritize errors with line numbers and specific exceptions
    def error_priority(error):
        score = 0
        if error.get("line", 0) > 0:
            score += 10  # Errors with line numbers are more actionable
        if error.get("exception"):
            score += 5  # Errors with exception types are more specific
        if error.get("test_function"):
            score += 3  # Test-related errors are often important
        return score

    sorted_errors = sorted(errors, key=error_priority, reverse=True)
    return sorted_errors[:limit]


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
