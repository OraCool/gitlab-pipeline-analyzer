"""
Job resources for MCP server

Copyright (c) 2025 Siarhei Skuratovich
Licensed under the MIT License - see LICENSE file for details
"""

import json
import logging
from typing import Any

from mcp.types import TextResourceContents

from gitlab_analyzer.cache.mcp_cache import get_cache_manager
from gitlab_analyzer.cache.models import generate_cache_key
from gitlab_analyzer.utils.utils import get_mcp_info

from .utils import create_text_resource

logger = logging.getLogger(__name__)


async def get_job_resource(
    project_id: str, pipeline_id: str, job_id: str
) -> dict[str, Any]:
    """Get job resource data from database only"""
    cache_manager = get_cache_manager()
    cache_key = generate_cache_key("job", project_id, int(job_id))

    async def compute_job_data() -> dict[str, Any]:
        # Get job info from database
        job_info = await cache_manager.get_job_info_async(int(job_id))

        if not job_info:
            return {
                "error": "Job not found in database",
                "message": "Job has not been analyzed yet. Run failed_pipeline_analysis first.",
                "job_id": int(job_id),
                "project_id": project_id,
                "pipeline_id": pipeline_id,
                "suggested_action": f"Use failed_pipeline_analysis tool on pipeline {pipeline_id}",
                "mcp_info": get_mcp_info("job_resource"),
            }

        # Validate that the job belongs to the specified pipeline
        if str(job_info["pipeline_id"]) != pipeline_id:
            return {
                "error": "Job does not belong to specified pipeline",
                "message": f"Job {job_id} belongs to pipeline {job_info['pipeline_id']}, not {pipeline_id}",
                "job_id": int(job_id),
                "project_id": project_id,
                "pipeline_id": pipeline_id,
                "actual_pipeline_id": job_info["pipeline_id"],
                "suggested_action": f"Use gl://job/{project_id}/{job_info['pipeline_id']}/{job_id}",
                "mcp_info": get_mcp_info("job_resource"),
            }

        # Get files with errors for this job
        files_with_errors = await cache_manager.get_job_files_with_errors(int(job_id))

        # Add resource links for navigation
        resource_links = []

        # Link back to pipeline
        resource_links.append(
            {
                "type": "resource_link",
                "resourceUri": f"gl://pipeline/{project_id}/{job_info['pipeline_id']}",
                "text": f"View pipeline {job_info['pipeline_id']} overview - all jobs, status, and branch information",
            }
        )

        # File error links if available
        if files_with_errors:
            total_files = len(files_with_errors)
            resource_links.append(
                {
                    "type": "resource_link",
                    "resourceUri": f"gl://files/{project_id}/{job_id}?page=1&limit=20",
                    "text": f"Investigate {total_files} files with errors - detailed error analysis, line numbers, and code context",
                }
            )

        # Build complete result with comprehensive job info
        result = {
            "job_info": job_info,
            "files_with_errors": (
                {
                    "count": len(files_with_errors),
                    "files": files_with_errors[:5],  # Show first 5 files for preview
                    "has_more": len(files_with_errors) > 5,
                }
                if files_with_errors
                else None
            ),
            "resource_links": resource_links,
            "metadata": {
                "resource_type": "job",
                "project_id": project_id,
                "job_id": int(job_id),
                "data_source": "database",
                "cached_at": None,  # TODO: Implement cache stats
            },
            "mcp_info": get_mcp_info("job_resource"),
        }

        return result

    # Use cache for the computed data
    return await cache_manager.get_or_compute(
        key=cache_key,
        compute_func=compute_job_data,
        data_type="job",
        project_id=project_id,
        job_id=int(job_id),
    )


async def get_pipeline_jobs_resource(
    project_id: str, pipeline_id: str, status_filter: str = "all"
) -> dict[str, Any]:
    """Get jobs for a pipeline with optional status filtering"""
    cache_manager = get_cache_manager()
    cache_key = generate_cache_key("pipeline_jobs", project_id, int(pipeline_id))

    async def compute_pipeline_jobs_data() -> dict[str, Any]:
        if status_filter == "failed":
            # Get only failed jobs
            jobs = cache_manager.get_pipeline_failed_jobs(int(pipeline_id))
        else:
            # Get all jobs
            jobs = await cache_manager.get_pipeline_jobs(int(pipeline_id))

            # Apply status filter if specified
            if status_filter != "all":
                jobs = [job for job in jobs if job.get("status") == status_filter]

        # Enhance job data with resource links
        enhanced_jobs = []
        for job in jobs:
            job_id = job.get("job_id")
            enhanced_job = job.copy()

            # Add resource links for navigation
            enhanced_job["resource_links"] = [
                {
                    "type": "resource_link",
                    "resourceUri": f"gl://job/{project_id}/{pipeline_id}/{job_id}",
                    "text": f"View detailed job analysis for {job.get('name', job_id)} - logs, errors, and files",
                }
            ]

            # Add files link if job has errors
            if job.get("status") == "failed":
                enhanced_job["resource_links"].append(
                    {
                        "type": "resource_link",
                        "resourceUri": f"gl://files/{project_id}/{job_id}",
                        "text": f"View files with errors in job {job.get('name', job_id)}",
                    }
                )

            enhanced_jobs.append(enhanced_job)

        # Get pipeline info for context
        pipeline_info = await cache_manager.get_pipeline_info_async(int(pipeline_id))

        return {
            "pipeline_info": {
                "pipeline_id": int(pipeline_id),
                "project_id": project_id,
                "status": pipeline_info.get("status") if pipeline_info else "unknown",
                "branch": pipeline_info.get("branch") if pipeline_info else None,
            },
            "jobs": enhanced_jobs,
            "summary": {
                "total_jobs": len(enhanced_jobs),
                "status_filter": status_filter,
                "failed_jobs": len(
                    [j for j in enhanced_jobs if j.get("status") == "failed"]
                ),
                "successful_jobs": len(
                    [j for j in enhanced_jobs if j.get("status") == "success"]
                ),
                "other_status_jobs": len(
                    [
                        j
                        for j in enhanced_jobs
                        if j.get("status") not in ["failed", "success"]
                    ]
                ),
            },
            "resource_links": [
                {
                    "type": "resource_link",
                    "resourceUri": f"gl://pipeline/{project_id}/{pipeline_id}",
                    "text": "View full pipeline analysis - all jobs, status, and branch information",
                },
                {
                    "type": "resource_link",
                    "resourceUri": f"gl://files/{project_id}/pipeline/{pipeline_id}",
                    "text": "View all files with errors across the entire pipeline",
                },
            ],
            "metadata": {
                "resource_type": "pipeline_jobs",
                "project_id": project_id,
                "pipeline_id": int(pipeline_id),
                "data_source": "database",
                "cached_at": None,
            },
            "mcp_info": get_mcp_info("pipeline_jobs_resource"),
        }

    # Use cache for the computed data
    return await cache_manager.get_or_compute(
        key=cache_key,
        compute_func=compute_pipeline_jobs_data,
        data_type="pipeline_jobs",
        project_id=project_id,
        pipeline_id=int(pipeline_id),
    )


def register_job_resources(mcp) -> None:
    """Register job resources with MCP server"""

    @mcp.resource("gl://job/{project_id}/{pipeline_id}/{job_id}")
    async def get_job_resource_handler(
        project_id: str, pipeline_id: str, job_id: str
    ) -> TextResourceContents:
        """
        Get job resource data from database only.

        Args:
            project_id: GitLab project ID
            pipeline_id: GitLab pipeline ID
            job_id: GitLab job ID

        Returns:
            Job information with files, errors, and navigation links
        """
        try:
            result = await get_job_resource(project_id, pipeline_id, job_id)
            return create_text_resource(
                "gl://job/{project_id}/{pipeline_id}/{job_id}",
                json.dumps(result, indent=2),
            )

        except Exception as e:
            logger.error(
                f"Error getting job resource {project_id}/{pipeline_id}/{job_id}: {e}"
            )
            error_result = {
                "error": f"Failed to get job resource: {str(e)}",
                "project_id": project_id,
                "pipeline_id": pipeline_id,
                "job_id": job_id,
                "resource_uri": f"gl://job/{project_id}/{pipeline_id}/{job_id}",
                "mcp_info": get_mcp_info("job_resource"),
            }
            return create_text_resource(
                "gl://job/{project_id}/{pipeline_id}/{job_id}",
                json.dumps(error_result, indent=2),
            )

    @mcp.resource("gl://jobs/{project_id}/pipeline/{pipeline_id}")
    async def get_pipeline_jobs_resource_handler(
        project_id: str, pipeline_id: str
    ) -> TextResourceContents:
        """Get all jobs for a pipeline"""
        data = await get_pipeline_jobs_resource(project_id, pipeline_id, "all")
        return create_text_resource(
            f"gl://jobs/{project_id}/pipeline/{pipeline_id}", json.dumps(data, indent=2)
        )

    @mcp.resource("gl://jobs/{project_id}/pipeline/{pipeline_id}/failed")
    async def get_pipeline_failed_jobs_resource_handler(
        project_id: str, pipeline_id: str
    ) -> TextResourceContents:
        """Get only failed jobs for a pipeline"""
        data = await get_pipeline_jobs_resource(project_id, pipeline_id, "failed")
        return create_text_resource(
            f"gl://jobs/{project_id}/pipeline/{pipeline_id}/failed",
            json.dumps(data, indent=2),
        )

    @mcp.resource("gl://jobs/{project_id}/pipeline/{pipeline_id}/success")
    async def get_pipeline_success_jobs_resource_handler(
        project_id: str, pipeline_id: str
    ) -> TextResourceContents:
        """Get only successful jobs for a pipeline"""
        data = await get_pipeline_jobs_resource(project_id, pipeline_id, "success")
        return create_text_resource(
            f"gl://jobs/{project_id}/pipeline/{pipeline_id}/success",
            json.dumps(data, indent=2),
        )

    logger.info("Job resources registered")
