"""
Job resources for MCP server

Copyright (c) 2025 Siarhei Skuratovich
Licensed under the MIT License - see LICENSE file for details
"""

import json
import logging
from typing import Any

from gitlab_analyzer.cache.mcp_cache import get_cache_manager
from gitlab_analyzer.cache.models import generate_cache_key
from gitlab_analyzer.utils.utils import get_mcp_info

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
                "text": f"Pipeline {job_info['pipeline_id']} - View all jobs and pipeline details",
            }
        )

        # File error links if available
        if files_with_errors:
            total_files = len(files_with_errors)
            resource_links.append(
                {
                    "type": "resource_link",
                    "resourceUri": f"gl://files/{project_id}/{job_id}?page=1&limit=20",
                    "text": f"Files with errors (page 1 of {(total_files + 19) // 20}) - {total_files} files",
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


def register_job_resources(mcp) -> None:
    """Register job resources with MCP server"""

    @mcp.resource("gl://job/{project_id}/{pipeline_id}/{job_id}")
    async def get_job_resource_handler(
        project_id: str, pipeline_id: str, job_id: str
    ) -> str:
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
            return json.dumps(result, indent=2)

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
            return json.dumps(error_result, indent=2)

    logger.info("Job resources registered")
