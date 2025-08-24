"""
Pipeline resources for MCP server

Copyright (c) 2025 Siarhei Skurato        mcp_info = get_mcp_info(
            tool_used="get_pipeline_jobs",
            error=False,
            parser_type="resource"
        )ich
Licensed under the MIT License - see LICENSE file for details
"""

import logging
from typing import Any

from ...cache.mcp_cache import get_cache_manager
from ...cache.models import generate_cache_key
from ..tools.utils import get_gitlab_analyzer, get_mcp_info

logger = logging.getLogger(__name__)


async def get_pipeline_resource(project_id: str, pipeline_id: str) -> dict[str, Any]:
    """Get pipeline resource data with caching"""
    cache_manager = get_cache_manager()
    cache_key = generate_cache_key("pipeline", project_id, int(pipeline_id))

    async def compute_pipeline_data() -> dict[str, Any]:
        """Compute pipeline data from GitLab API"""
        logger.info(f"Computing pipeline data for {project_id}/{pipeline_id}")

        analyzer = get_gitlab_analyzer()

        # Get pipeline info
        pipeline_info = await analyzer.get_pipeline(project_id, int(pipeline_id))

        # Get all jobs for the pipeline
        jobs = await analyzer.get_pipeline_jobs(project_id, int(pipeline_id))

        # Transform jobs data for better readability
        jobs_summary = []
        for job in jobs:
            jobs_summary.append(
                {
                    "id": job.id,
                    "name": job.name,
                    "stage": job.stage,
                    "status": job.status,
                    "duration": getattr(job, "duration", None),
                    "created_at": job.created_at,
                    "finished_at": job.finished_at,
                    "web_url": job.web_url,
                    "failure_reason": job.failure_reason,
                }
            )

        # Get pipeline status and metadata
        result = {
            "pipeline_info": {
                "id": pipeline_info.get("id"),
                "project_id": pipeline_info.get("project_id"),
                "ref": pipeline_info.get("ref"),
                "sha": pipeline_info.get("sha"),
                "status": pipeline_info.get("status"),
                "source": pipeline_info.get("source"),
                "created_at": pipeline_info.get("created_at"),
                "updated_at": pipeline_info.get("updated_at"),
                "finished_at": pipeline_info.get("finished_at"),
                "duration": pipeline_info.get("duration"),
                "web_url": pipeline_info.get("web_url"),
            },
            "jobs": jobs_summary,
            "jobs_count": len(jobs_summary),
            "failed_jobs_count": len(
                [j for j in jobs_summary if j["status"] == "failed"]
            ),
            "metadata": {
                "resource_type": "pipeline",
                "project_id": project_id,
                "pipeline_id": int(pipeline_id),
                "cached_at": (
                    cache_manager._stats.newest_entry.isoformat()
                    if cache_manager._stats.newest_entry
                    else None
                ),
            },
            "mcp_info": get_mcp_info("pipeline_resource"),
        }

        return result

    return await cache_manager.get_or_compute(
        key=cache_key,
        compute_func=compute_pipeline_data,
        data_type="pipeline",
        project_id=project_id,
        pipeline_id=int(pipeline_id),
    )


def register_pipeline_resources(mcp) -> None:
    """Register pipeline resources with MCP server"""

    @mcp.resource("gl://pipeline/{project_id}/{pipeline_id}")
    async def pipeline_resource(project_id: str, pipeline_id: str) -> dict[str, Any]:
        """Pipeline resource with comprehensive info and jobs list"""
        return await get_pipeline_resource(project_id, pipeline_id)

    logger.info("Pipeline resources registered")
