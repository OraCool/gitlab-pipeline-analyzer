"""
Cache management tools for GitLab Pipeline Analyzer

Copyright (c) 2025 Siarhei Skuratovich
Licensed under the MIT License - see LICENSE file for details
"""

from typing import Any

from fastmcp import FastMCP

from gitlab_analyzer.cache.mcp_cache import get_cache_manager
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
        - clear_cache("job", project_id="83") - Clear job data for project 83
        - clear_cache("old", max_age_hours=24) - Clear data older than 24 hours
        """
        try:
            cache_manager = get_cache_manager()

            if cache_type == "old":
                if max_age_hours is None:
                    max_age_hours = 168  # 7 days default

                cleared_count = await cache_manager.clear_old_entries(max_age_hours)

                return {
                    "operation": "clear_old_cache",
                    "max_age_hours": max_age_hours,
                    "cleared_entries": cleared_count,
                    "project_id": str(project_id) if project_id else "all",
                    "status": "success",
                    "mcp_info": get_mcp_info("clear_cache"),
                }

            elif cache_type == "all":
                cleared_count = await cache_manager.clear_all_cache(project_id)

                return {
                    "operation": "clear_all_cache",
                    "cleared_entries": cleared_count,
                    "project_id": str(project_id) if project_id else "all",
                    "status": "success",
                    "mcp_info": get_mcp_info("clear_cache"),
                }

            else:
                # Clear specific cache type
                cleared_count = await cache_manager.clear_cache_by_type(
                    cache_type, project_id
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
