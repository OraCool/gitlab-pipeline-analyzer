"""
Cache management tools for GitLab Pipeline Analyzer

Copyright (c) 2025 Siarhei Skuratovich
Licensed under the MIT License - see LICENSE file for details
"""

from typing import Any

from fastmcp import FastMCP

from gitlab_analyzer.cache.mcp_cache import get_cache_manager
from gitlab_analyzer.utils.debug import debug_print, verbose_debug_print
from gitlab_analyzer.utils.utils import get_mcp_info


def register_cache_tools(mcp: FastMCP) -> None:
    """Register cache management tools"""

    @mcp.tool
    async def clear_cache(
        cache_type: str = "all",
        project_id: str | int | None = None,
        max_age_hours: int | None = None,
    ) -> dict[str, Any]:
        """
        🧹 CLEANUP: Clear cached data to free up space or force refresh.

        WHEN TO USE:
        - Cache is taking up too much space
        - Need to force fresh data fetch from GitLab
        - Data seems stale or incorrect
        - Regular maintenance cleanup

        CACHE TYPES:
        - "all": Clear all cached data
        - "pipeline": Clear pipeline data only
        - "job": Clear job traces and analysis
        - "analysis": Clear analysis results
        - "error": Clear error data
        - "old": Clear data older than max_age_hours

        SAFETY:
        - Never clears pipeline data (immutable)
        - Can target specific projects
        - Can filter by age

        Args:
            cache_type: Type of cache to clear ("all", "pipeline", "job", "analysis", "error", "old")
            project_id: Optional project ID to limit clearing to specific project
            max_age_hours: For cache_type="old", clear data older than this (default: 168 hours = 7 days)

        Returns:
            Summary of cache clearing operation

        EXAMPLES:
        - clear_cache() - Clear all cache
        - clear_cache("job", project_id="123") - Clear job data for project 123
        - clear_cache("old", max_age_hours=24) - Clear data older than 24 hours
        """
        try:
            debug_print(
                f"🧹 [TOOL] Starting cache clearing: type={cache_type}, project_id={project_id}, max_age_hours={max_age_hours}"
            )

            cache_manager = get_cache_manager()

            if cache_type == "old":
                if max_age_hours is None:
                    max_age_hours = 168  # 7 days default

                verbose_debug_print(
                    f"🧹 [TOOL] Clearing old cache entries older than {max_age_hours} hours"
                )
                cleared_count = await cache_manager.clear_old_entries(max_age_hours)
                debug_print(f"✅ [TOOL] Cleared {cleared_count} old cache entries")

                return {
                    "operation": "clear_old_cache",
                    "max_age_hours": max_age_hours,
                    "cleared_entries": cleared_count,
                    "project_id": str(project_id) if project_id else "all",
                    "status": "success",
                    "mcp_info": get_mcp_info("clear_cache"),
                }

            elif cache_type == "all":
                verbose_debug_print(
                    f"🧹 [TOOL] Clearing all cache data for project_id={project_id or 'all'}"
                )
                cleared_count = await cache_manager.clear_all_cache(project_id)
                debug_print(f"✅ [TOOL] Cleared {cleared_count} total cache entries")

                return {
                    "operation": "clear_all_cache",
                    "cleared_entries": cleared_count,
                    "project_id": str(project_id) if project_id else "all",
                    "status": "success",
                    "mcp_info": get_mcp_info("clear_cache"),
                }

            else:
                # Clear specific cache type
                verbose_debug_print(
                    f"🧹 [TOOL] Clearing {cache_type} cache for project_id={project_id or 'all'}"
                )
                cleared_count = await cache_manager.clear_cache_by_type(
                    cache_type, project_id
                )
                debug_print(
                    f"✅ [TOOL] Cleared {cleared_count} {cache_type} cache entries"
                )

                return {
                    "operation": f"clear_{cache_type}_cache",
                    "cache_type": cache_type,
                    "cleared_entries": cleared_count,
                    "project_id": str(project_id) if project_id else "all",
                    "status": "success",
                    "mcp_info": get_mcp_info("clear_cache"),
                }

        except Exception as e:
            return {
                "operation": "clear_cache",
                "error": f"Failed to clear cache: {str(e)}",
                "cache_type": cache_type,
                "project_id": str(project_id) if project_id else "all",
                "status": "error",
                "mcp_info": get_mcp_info("clear_cache", error=True),
            }

    @mcp.tool
    async def clear_pipeline_cache(
        project_id: str | int,
        pipeline_id: str | int,
    ) -> dict[str, Any]:
        """
        🗑️ PIPELINE CLEANUP: Clear all cached data for a specific pipeline.

        WHEN TO USE:
        - Need to refresh data for a specific pipeline
        - Pipeline was re-run and you want fresh analysis
        - Clear stale pipeline data without affecting other pipelines
        - Debug pipeline-specific cache issues

        WHAT GETS CLEARED:
        - Pipeline metadata
        - All jobs in the pipeline
        - All errors from pipeline jobs
        - All file index entries from pipeline jobs
        - All trace segments from pipeline jobs

        Args:
            project_id: The GitLab project ID
            pipeline_id: The specific pipeline ID to clear

        Returns:
            Summary of cleared entries by table

        EXAMPLES:
        - clear_pipeline_cache("123", "1594344") - Clear specific pipeline
        """
        try:
            debug_print(
                f"🧹 [TOOL] Starting pipeline cache clearing: project_id={project_id}, pipeline_id={pipeline_id}"
            )

            cache_manager = get_cache_manager()
            counts = await cache_manager.clear_cache_by_pipeline(
                project_id, pipeline_id
            )

            # Calculate total cleared if no error
            if isinstance(counts, dict) and "error" not in counts:
                total_cleared = sum(
                    count for count in counts.values() if isinstance(count, int)
                )
                debug_print(
                    f"✅ [TOOL] Successfully cleared pipeline {pipeline_id}: {total_cleared} total entries"
                )

            return {
                "operation": "clear_pipeline_cache",
                "project_id": str(project_id),
                "pipeline_id": str(pipeline_id),
                "cleared_counts": counts,
                "total_cleared": sum(counts.values()) if "error" not in counts else 0,
                "status": "success" if "error" not in counts else "error",
                "mcp_info": get_mcp_info("clear_pipeline_cache"),
            }

        except Exception as e:
            return {
                "operation": "clear_pipeline_cache",
                "error": f"Failed to clear pipeline cache: {str(e)}",
                "project_id": str(project_id),
                "pipeline_id": str(pipeline_id),
                "status": "error",
                "mcp_info": get_mcp_info("clear_pipeline_cache", error=True),
            }

    @mcp.tool
    async def clear_job_cache(
        project_id: str | int,
        job_id: str | int,
    ) -> dict[str, Any]:
        """
        🗑️ JOB CLEANUP: Clear all cached data for a specific job.

        WHEN TO USE:
        - Need to refresh data for a specific job
        - Job was re-run and you want fresh analysis
        - Clear stale job data without affecting other jobs
        - Debug job-specific cache issues

        WHAT GETS CLEARED:
        - Job metadata
        - All errors from the job
        - All file index entries from the job
        - All trace segments from the job

        Args:
            project_id: The GitLab project ID
            job_id: The specific job ID to clear

        Returns:
            Summary of cleared entries by table

        EXAMPLES:
        - clear_job_cache("123", "76474172") - Clear specific job
        """
        try:
            debug_print(
                f"🧹 [TOOL] Starting job cache clearing: project_id={project_id}, job_id={job_id}"
            )

            cache_manager = get_cache_manager()
            counts = await cache_manager.clear_cache_by_job(project_id, job_id)

            # Calculate total cleared if no error
            total_cleared = 0
            if isinstance(counts, dict) and "error" not in counts:
                total_cleared = sum(
                    count for count in counts.values() if isinstance(count, int)
                )
                debug_print(
                    f"✅ [TOOL] Successfully cleared job {job_id}: {total_cleared} total entries"
                )

            return {
                "operation": "clear_job_cache",
                "project_id": str(project_id),
                "job_id": str(job_id),
                "cleared_counts": counts,
                "total_cleared": total_cleared,
                "status": "success" if "error" not in counts else "error",
                "mcp_info": get_mcp_info("clear_job_cache"),
            }

        except Exception as e:
            return {
                "operation": "clear_job_cache",
                "error": f"Failed to clear job cache: {str(e)}",
                "project_id": str(project_id),
                "job_id": str(job_id),
                "status": "error",
                "mcp_info": get_mcp_info("clear_job_cache", error=True),
            }

    @mcp.tool
    async def cache_stats() -> dict[str, Any]:
        """
        📊 INFO: Get cache statistics and storage information.

        WHEN TO USE:
        - Check cache size and usage
        - Monitor cache performance
        - Understand what's stored in cache
        - Debug cache-related issues

        WHAT YOU GET:
        - Total cache size and entry count
        - Breakdown by data type
        - Cache hit/miss statistics
        - Storage file information
        - Memory usage details

        Returns:
            Comprehensive cache statistics

        WORKFLOW: Use to monitor cache health → leads to clear_cache if needed
        """
        try:
            cache_manager = get_cache_manager()
            stats = await cache_manager.get_cache_stats()

            return {
                "operation": "cache_stats",
                "stats": stats,
                "status": "success",
                "mcp_info": get_mcp_info("cache_stats"),
            }

        except Exception as e:
            return {
                "operation": "cache_stats",
                "error": f"Failed to get cache stats: {str(e)}",
                "status": "error",
                "mcp_info": get_mcp_info("cache_stats", error=True),
            }

    @mcp.tool
    async def cache_health() -> dict[str, Any]:
        """
        🏥 HEALTH: Check cache system health and performance.

        WHEN TO USE:
        - Verify cache is working correctly
        - Diagnose performance issues
        - Check for corruption or errors
        - Regular health monitoring

        HEALTH CHECKS:
        - Database connectivity
        - Table schema integrity
        - Index performance
        - Storage space availability
        - Cache operation timing

        Returns:
            Cache health report with recommendations

        WORKFLOW: Use for diagnostics → leads to clear_cache if issues found
        """
        try:
            cache_manager = get_cache_manager()
            health = await cache_manager.check_health()

            return {
                "operation": "cache_health",
                "health": health,
                "status": "success",
                "mcp_info": get_mcp_info("cache_health"),
            }

        except Exception as e:
            return {
                "operation": "cache_health",
                "error": f"Failed to check cache health: {str(e)}",
                "status": "error",
                "mcp_info": get_mcp_info("cache_health", error=True),
            }
