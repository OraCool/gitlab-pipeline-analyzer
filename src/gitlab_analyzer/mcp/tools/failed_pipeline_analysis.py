"""
Failed Pipeline Analysis Tool - Focused on analyzing only failed pipeline jobs

This module provides efficient analysis by focusing specifically on failed jobs:
1. Gets pipeline info and stores in database
2. Gets only failed jobs using get_failed_pipeline_jobs (more efficient)
3. Stores failed job data for further analysis

Copyright (c) 2025 Siarhei Skuratovich
Licensed under the MIT License - see LICENSE file for details
"""

from typing import Any

from fastmcp import FastMCP

from gitlab_analyzer.cache.mcp_cache import get_cache_manager
from gitlab_analyzer.core.pipeline_info import get_comprehensive_pipeline_info

from .utils import get_gitlab_analyzer, get_mcp_info


def register_failed_pipeline_analysis_tools(mcp: FastMCP) -> None:
    """Register failed pipeline analysis tools"""

    @mcp.tool
    async def failed_pipeline_analysis(
        project_id: str | int,
        pipeline_id: int,
        use_cache: bool = True,
        store_in_db: bool = True,
    ) -> dict[str, Any]:
        """
        🚨 FAILED PIPELINE ANALYSIS: Efficient analysis focusing only on failed jobs.

        This tool provides targeted analysis by:
        1. Gets pipeline information with branch resolution
        2. Analyzes ONLY failed jobs using get_failed_pipeline_jobs (more efficient)
        3. Stores results in database for resource access
        4. Uses caching for performance
        5. Provides structured output for failed job investigation

        WHEN TO USE:
        - Pipeline shows "failed" status and you want to focus on failures
        - More efficient than comprehensive analysis when only failures matter
        - Need failed job data stored for resource-based access
        - Want targeted investigation of specific failures

        SMART FEATURES:
        - Uses get_failed_pipeline_jobs for efficient API calls
        - Filters out non-failed jobs automatically
        - Resolves real branch names for merge request pipelines
        - Caches results for repeated access
        - Stores analysis in database for resources

        WHAT YOU GET:
        - Complete pipeline metadata with resolved branches
        - Only failed jobs analyzed (no wasted time on successful jobs)
        - Structured error and failure reason data
        - Analysis summary and statistics focused on failures
        - Resource URIs for detailed investigation

        Args:
            project_id: The GitLab project ID or path
            pipeline_id: The ID of the GitLab pipeline to analyze
            use_cache: Whether to use cached results if available
            store_in_db: Whether to store results in database for resources

        Returns:
            Failed pipeline analysis with efficient failed-job-only parsing and caching

        WORKFLOW: Primary failed analysis tool → use resources for specific data access
        """

        try:
            analyzer = get_gitlab_analyzer()
            cache_manager = get_cache_manager()

            # Step 1: Get comprehensive pipeline info and store it
            print(f"📋 Step 1: Getting pipeline information for {pipeline_id}...")
            pipeline_info = await get_comprehensive_pipeline_info(
                analyzer=analyzer, project_id=project_id, pipeline_id=pipeline_id
            )

            if store_in_db:
                print("💾 Storing pipeline info in database...")
                await cache_manager.store_pipeline_info_async(
                    project_id=project_id,
                    pipeline_id=pipeline_id,
                    pipeline_info=pipeline_info,
                )
                print("✅ Pipeline info stored successfully")

            # Step 2: Get only failed jobs (more efficient than all jobs)
            print("🚨 Step 2: Getting failed jobs only...")
            failed_jobs = await analyzer.get_failed_pipeline_jobs(
                project_id=project_id, pipeline_id=pipeline_id
            )

            print(f"📊 Found {len(failed_jobs)} failed jobs")

            # Step 3: Store basic failed job info in database using cache manager
            if store_in_db and failed_jobs:
                await cache_manager.store_failed_jobs_basic(
                    project_id=project_id,
                    pipeline_id=pipeline_id,
                    failed_jobs=failed_jobs,
                    pipeline_info=pipeline_info,
                )

            # Prepare analysis results
            failed_stages = list(set(job.stage for job in failed_jobs))
            failure_reasons = list(
                set(job.failure_reason for job in failed_jobs if job.failure_reason)
            )

            result = {
                "pipeline_info": pipeline_info,
                "failed_jobs_count": len(failed_jobs),
                "failed_jobs": [
                    {
                        "id": job.id,
                        "name": job.name,
                        "status": job.status,
                        "stage": job.stage,
                        "failure_reason": job.failure_reason,
                        "web_url": job.web_url,
                        "created_at": job.created_at,
                        "started_at": job.started_at,
                        "finished_at": job.finished_at,
                    }
                    for job in failed_jobs
                ],
                "summary": {
                    "pipeline_id": pipeline_id,
                    "pipeline_status": pipeline_info.get("status"),
                    "pipeline_ref": pipeline_info.get("ref"),
                    "pipeline_web_url": pipeline_info.get("web_url"),
                    "failed_jobs_count": len(failed_jobs),
                    "failed_stages": failed_stages,
                    "failure_reasons": failure_reasons,
                    "analysis_type": "failed_jobs_only",
                    "efficiency_note": f"Analyzed only {len(failed_jobs)} failed jobs instead of all pipeline jobs",
                },
                "resources": {
                    "pipeline": f"gl://pipeline/{project_id}/{pipeline_id}",
                    "jobs": f"gl://jobs/{project_id}/{pipeline_id}",
                    "analysis": f"gl://analysis/{project_id}/{pipeline_id}",
                },
            }

            # Add MCP info
            result["mcp_info"] = get_mcp_info("failed_pipeline_analysis")

            print("✅ Failed pipeline analysis completed successfully")
            return result

        except Exception as e:
            print(f"❌ Error in failed pipeline analysis: {e}")
            return {
                "error": str(e),
                "pipeline_id": pipeline_id,
                "project_id": project_id,
                "mcp_info": get_mcp_info("failed_pipeline_analysis", error=True),
            }
