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

from gitlab_analyzer.utils.utils import get_gitlab_analyzer, get_mcp_info


async def store_pipeline_info_step(
    cache_manager, project_id: str | int, pipeline_id: int, pipeline_info: dict
) -> None:
    """Store pipeline information immediately after retrieval"""
    try:
        print(
            f"DEBUG: store_pipeline_info_step called - Project: {project_id}, Pipeline: {pipeline_id}"
        )
        print(
            f"DEBUG: Cache manager: {cache_manager}, DB path: {cache_manager.db_path}"
        )

        pipeline_data = pipeline_info.get("pipeline_info", {})
        if not pipeline_data:
            print("DEBUG: No pipeline_data found in pipeline_info")
            return

        print(f"DEBUG: Pipeline data keys: {list(pipeline_data.keys())}")

        # Extract real branch information
        pipeline_type = pipeline_info.get("pipeline_type", "branch")
        target_branch = pipeline_info.get("target_branch")
        source_branch = None

        if pipeline_type == "merge_request":
            merge_request_info = pipeline_info.get("merge_request_info", {})
            if (
                isinstance(merge_request_info, dict)
                and "error" not in merge_request_info
            ):
                source_branch = merge_request_info.get("source_branch")
                target_branch = merge_request_info.get("target_branch")
            else:
                source_branch = target_branch
                target_branch = "unknown"
        else:
            source_branch = target_branch
            target_branch = None

        print(
            f"DEBUG: About to store - Pipeline ID: {pipeline_id}, Source: {source_branch}, Target: {target_branch}"
        )

        # Store in pipelines table
        import aiosqlite

        async with aiosqlite.connect(cache_manager.db_path) as conn:
            data_to_store = (
                pipeline_id,
                int(project_id),
                pipeline_data.get("ref", ""),
                pipeline_data.get("sha", ""),
                pipeline_data.get("status", ""),
                pipeline_data.get("web_url", ""),
                pipeline_data.get("created_at", ""),
                pipeline_data.get("updated_at", ""),
                source_branch,
                target_branch,
            )
            print(f"DEBUG: Data to store: {data_to_store}")

            await conn.execute(
                """
                INSERT OR REPLACE INTO pipelines 
                (pipeline_id, project_id, ref, sha, status, web_url, created_at, updated_at, source_branch, target_branch)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                data_to_store,
            )
            await conn.commit()

            # Verify storage
            cursor = await conn.execute(
                "SELECT COUNT(*) FROM pipelines WHERE pipeline_id = ?", (pipeline_id,)
            )
            count = await cursor.fetchone()
            print(f"DEBUG: Pipeline {pipeline_id} stored - count in DB: {count[0]}")

        print("DEBUG: Pipeline info stored successfully")
    except Exception as e:
        print(f"DEBUG: Error storing pipeline info: {e}")
        import traceback

        traceback.print_exc()


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
            cache_manager = get_cache_manager() if (use_cache or store_in_db) else None

            # Create cache key for the complete analysis
            cache_key = f"comprehensive_analysis_{project_id}_{pipeline_id}"

            async def compute_analysis():
                # Step 1: Get comprehensive pipeline info with branch resolution
                print(
                    f"DEBUG: Step 1 - Getting pipeline info for {project_id}/{pipeline_id}"
                )
                pipeline_info = await get_comprehensive_pipeline_info(
                    analyzer, project_id, pipeline_id
                )

                # Store pipeline info immediately
                if store_in_db and cache_manager:
                    print("DEBUG: Storing pipeline info in database")
                    await store_pipeline_info_step(
                        cache_manager, project_id, pipeline_id, pipeline_info
                    )

                # Step 2: Analyze all jobs with intelligent parsing
                print(f"DEBUG: Step 2 - Analyzing jobs for pipeline {pipeline_id}")
                job_analysis = await analyze_pipeline_jobs(
                    analyzer,
                    project_id,
                    pipeline_id,
                    failed_jobs_only=True,
                    cache_manager=cache_manager if store_in_db else None,
                )

                # If no failed jobs found, analyze all jobs to understand pipeline failure
                if job_analysis.get("total_failed_jobs", 0) == 0:
                    print("DEBUG: No failed jobs found, analyzing all jobs for context")
                    job_analysis = await analyze_pipeline_jobs(
                        analyzer,
                        project_id,
                        pipeline_id,
                        failed_jobs_only=False,  # Analyze ALL jobs
                        cache_manager=cache_manager if store_in_db else None,
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

                print("DEBUG: Analysis completed successfully")
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
