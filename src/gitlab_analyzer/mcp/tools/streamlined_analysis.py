"""
Streamlined analysis tools for GitLab Pipeline Analyzer.

This module contains only the essential analysis tool that handles comprehensive
pipeline analysis with smart parser selection and caching.

Copyright (c) 2025 Siarhei Skuratovich
Licensed under the MIT License - see LICENSE file for details
"""

from datetime import datetime
from typing import Any

import httpx
from fastmcp import FastMCP

from gitlab_analyzer.cache.mcp_cache import get_cache_manager
from gitlab_analyzer.core.analysis import analyze_pipeline_jobs
from gitlab_analyzer.core.pipeline_info import get_comprehensive_pipeline_info

from .utils import get_gitlab_analyzer, get_mcp_info


def register_streamlined_analysis_tools(mcp: FastMCP) -> None:
    """Register streamlined analysis tools"""

    @mcp.tool
    async def comprehensive_pipeline_analysis(
        project_id: str | int,
        pipeline_id: int,
        use_cache: bool = True,
        store_in_db: bool = True,
    ) -> dict[str, Any]:
        """
        🎯 COMPREHENSIVE: Complete pipeline failure analysis with intelligent parser selection.

        This is the main analysis tool that:
        1. Gets pipeline information with branch resolution
        2. Analyzes all failed jobs with optimal parsers (pytest vs generic)
        3. Stores results in database for resource access
        4. Uses caching for performance
        5. Provides structured output for further investigation

        WHEN TO USE:
        - Pipeline shows "failed" status and you need complete analysis
        - Want comprehensive overview with intelligent parsing
        - Need data stored for resource-based access
        - First step in any pipeline investigation

        SMART FEATURES:
        - Auto-detects pytest jobs and uses specialized parser
        - Filters out meaningless errors automatically
        - Resolves real branch names for merge request pipelines
        - Caches results for repeated access
        - Stores analysis in database for resources

        WHAT YOU GET:
        - Complete pipeline metadata with resolved branches
        - All failed jobs analyzed with appropriate parsers
        - Structured error and warning data
        - Analysis summary and statistics
        - Resource URIs for detailed investigation

        Args:
            project_id: The GitLab project ID or path
            pipeline_id: The ID of the GitLab pipeline to analyze
            use_cache: Whether to use cached results if available
            store_in_db: Whether to store results in database for resources

        Returns:
            Comprehensive pipeline analysis with intelligent parsing and caching

        WORKFLOW: Primary analysis tool → use resources for specific data access
        """
        try:
            analyzer = get_gitlab_analyzer()
            cache_manager = get_cache_manager() if use_cache else None

            # Create cache key for the complete analysis
            cache_key = f"comprehensive_analysis_{project_id}_{pipeline_id}"

            async def compute_analysis():
                # Get comprehensive pipeline info with branch resolution
                pipeline_info = await get_comprehensive_pipeline_info(
                    analyzer, project_id, pipeline_id
                )

                # Analyze all jobs with intelligent parsing
                job_analysis = await analyze_pipeline_jobs(
                    analyzer, project_id, pipeline_id, failed_jobs_only=True
                )

                # Combine results
                result = {
                    "pipeline_info": pipeline_info,
                    "job_analysis": job_analysis,
                    "analysis_summary": {
                        "pipeline_type": pipeline_info.get("pipeline_type"),
                        "target_branch": pipeline_info.get("target_branch"),
                        "total_failed_jobs": job_analysis.get("total_failed_jobs", 0),
                        "total_errors": job_analysis.get("total_errors", 0),
                        "total_warnings": job_analysis.get("total_warnings", 0),
                        "parser_breakdown": job_analysis.get("analysis_summary", {}),
                    },
                    "analysis_timestamp": datetime.now().isoformat(),
                    "used_cache": False,
                    "stored_in_db": store_in_db,
                }

                # Store in database if requested
                if store_in_db and cache_manager:
                    print(
                        f"DEBUG: About to store pipeline analysis for {project_id}/{pipeline_id}"
                    )
                    await cache_manager.store_pipeline_analysis(
                        project_id, pipeline_id, result
                    )
                    print(f"DEBUG: Pipeline analysis storage completed")

                return result

            # Use cache if enabled
            if cache_manager and use_cache:
                result = await cache_manager.get_or_compute(
                    key=cache_key,
                    compute_func=compute_analysis,
                    data_type="comprehensive_analysis",
                    project_id=str(project_id),
                    pipeline_id=pipeline_id,
                )
                result["used_cache"] = True
            else:
                result = await compute_analysis()

            # Add resource URIs for further investigation
            result["resource_uris"] = {
                "pipeline": f"gl://pipeline/{project_id}/{pipeline_id}",
                "analysis": f"gl://analysis/{project_id}/pipeline/{pipeline_id}",
                # Note: job and error resources require specific job_id, not pipeline_id
                # These will be available per job in the job_analysis section
            }

            # Add MCP metadata
            result["mcp_info"] = get_mcp_info("comprehensive_pipeline_analysis")

            return result

        except (httpx.HTTPError, httpx.RequestError, ValueError, KeyError) as e:
            return {
                "error": f"Failed to analyze pipeline: {str(e)}",
                "project_id": str(project_id),
                "pipeline_id": pipeline_id,
                "analysis_timestamp": datetime.now().isoformat(),
                "mcp_info": get_mcp_info("comprehensive_pipeline_analysis", error=True),
            }
