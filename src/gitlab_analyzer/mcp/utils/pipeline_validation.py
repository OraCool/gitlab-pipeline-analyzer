"""
Pipeline Validation Utilities

Provides reusable pipeline analysis validation functions following DRY, SOLID, and KISS principles.

Copyright (c) 2025 Siarhei Skuratovich
Licensed under the MIT License - see LICENSE file for details
"""

from typing import Any

from gitlab_analyzer.cache.mcp_cache import get_cache_manager
from gitlab_analyzer.utils.utils import get_mcp_info


async def check_pipeline_analyzed(
    project_id: str, pipeline_id: str, resource_type: str = "pipeline"
) -> dict[str, Any] | None:
    """
    Check if a pipeline has been analyzed and return error response if not.

    Args:
        project_id: GitLab project ID
        pipeline_id: GitLab pipeline ID
        resource_type: Type of resource requesting the check (for error context)

    Returns:
        None if pipeline is analyzed, error dict if not analyzed

    Example:
        error_response = await check_pipeline_analyzed("83", "1234567", "pipeline_errors")
        if error_response:
            return error_response
        # Continue with normal processing...
    """
    cache_manager = get_cache_manager()

    # Check if pipeline exists in database (has been analyzed)
    pipeline_info = await cache_manager.get_pipeline_info_async(int(pipeline_id))

    if not pipeline_info:
        return {
            "error": "pipeline_not_analyzed",
            "message": f"Pipeline {pipeline_id} has not been analyzed yet. Please run the 'failed_pipeline_analysis' tool first to populate the database with comprehensive pipeline information.",
            "required_action": "Call failed_pipeline_analysis tool",
            "pipeline_id": int(pipeline_id),
            "project_id": project_id,
            "metadata": {
                "resource_type": resource_type,
                "data_source": "none",
                "status": "not_analyzed",
            },
            "mcp_info": get_mcp_info(
                f"{resource_type}_resource", error=True, parser_type="resource"
            ),
        }

    return None


async def check_job_analyzed(
    project_id: str, job_id: str, resource_type: str = "job"
) -> dict[str, Any] | None:
    """
    Check if a job has been analyzed and return error response if not.

    Args:
        project_id: GitLab project ID
        job_id: GitLab job ID
        resource_type: Type of resource requesting the check (for error context)

    Returns:
        None if job is analyzed, error dict if not analyzed
    """
    cache_manager = get_cache_manager()

    # Check if job exists in database (has been analyzed)
    try:
        job_info = await cache_manager.get_job_info_async(int(job_id))
    except Exception:
        job_info = None

    if not job_info:
        return {
            "error": "job_not_analyzed",
            "message": f"Job {job_id} not found in cache. Run job analysis first.",
            "project_id": project_id,
            "job_id": int(job_id),
            "suggested_actions": [
                f"Use analyze_job({project_id}, {job_id}) to analyze this specific job",
                "Or use failed_pipeline_analysis() to analyze the entire pipeline containing this job",
            ],
            "resource_uri": f"gl://error/{project_id}/{job_id}",
            "mcp_info": get_mcp_info(
                f"{resource_type}_resource", error=True, parser_type="resource"
            ),
        }

    return None
