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

from mcp.types import TextResourceContents

from gitlab_analyzer.cache.mcp_cache import get_cache_manager
from gitlab_analyzer.cache.models import generate_cache_key
from gitlab_analyzer.utils.utils import get_mcp_info

from .utils import create_text_resource

logger = logging.getLogger(__name__)


async def get_pipeline_resource(project_id: str, pipeline_id: str) -> dict[str, Any]:
    """Get pipeline resource data from database only"""
    cache_manager = get_cache_manager()
    cache_key = generate_cache_key("pipeline", project_id, int(pipeline_id))

    async def compute_pipeline_data() -> dict[str, Any]:
        """Get pipeline data from database only"""
        logger.info(
            f"Getting pipeline data from database for {project_id}/{pipeline_id}"
        )

        # Get comprehensive pipeline data from database only
        pipeline_db_data = await cache_manager.get_pipeline_info_async(int(pipeline_id))

        if not pipeline_db_data:
            # Database is empty - analysis tool should be called first
            return {
                "error": "pipeline_not_analyzed",
                "message": f"Pipeline {pipeline_id} has not been analyzed yet. Please run the 'failed_pipeline_analysis' tool first to populate the database with comprehensive pipeline information.",
                "required_action": "Call failed_pipeline_analysis tool",
                "pipeline_id": int(pipeline_id),
                "project_id": project_id,
                "metadata": {
                    "resource_type": "pipeline",
                    "data_source": "none",
                    "status": "not_analyzed",
                },
                "mcp_info": get_mcp_info("pipeline_resource"),
            }

        # Use database data with all fields including resolved branches
        pipeline_info = {
            "id": pipeline_db_data["pipeline_id"],
            "project_id": pipeline_db_data["project_id"],
            "ref": pipeline_db_data["ref"],
            "sha": pipeline_db_data["sha"],
            "status": pipeline_db_data["status"],
            "web_url": pipeline_db_data["web_url"],
            "created_at": pipeline_db_data["created_at"],
            "updated_at": pipeline_db_data["updated_at"],
            # Additional resolved fields from database
            "source_branch": pipeline_db_data.get("source_branch"),
            "target_branch": pipeline_db_data.get("target_branch"),
            "pipeline_type": (
                "merge_request"
                if pipeline_db_data["ref"].startswith("refs/merge-requests/")
                else "branch"
            ),
        }

        # Determine if this is a merge request pipeline
        is_merge_request_pipeline = pipeline_db_data["ref"].startswith(
            "refs/merge-requests/"
        )

        # Add MR information only if this is a merge request pipeline
        mr_info = None
        jira_tickets = []
        review_summary = None

        if is_merge_request_pipeline and pipeline_db_data.get("mr_iid") is not None:
            mr_info = {
                "iid": pipeline_db_data.get("mr_iid"),
                "title": pipeline_db_data.get("mr_title"),
                "description": pipeline_db_data.get("mr_description"),
                "author": pipeline_db_data.get("mr_author"),
                "web_url": pipeline_db_data.get("mr_web_url"),
            }

            # Parse review summary from JSON string if available
            if pipeline_db_data.get("review_summary"):
                import contextlib
                import json

                with contextlib.suppress(json.JSONDecodeError, TypeError):
                    review_summary = json.loads(pipeline_db_data["review_summary"])
                    # Only add unresolved discussions to pipeline resource
                    if review_summary and not review_summary.get("error"):
                        mr_info["review_statistics"] = review_summary.get(
                            "review_statistics", {}
                        )
                        mr_info["unresolved_discussions_count"] = pipeline_db_data.get(
                            "unresolved_discussions_count", 0
                        )
                        mr_info["review_comments_count"] = pipeline_db_data.get(
                            "review_comments_count", 0
                        )

                        # Only include unresolved discussions for pipeline resource
                        if review_summary.get("unresolved_discussions"):
                            mr_info["unresolved_discussions"] = review_summary.get(
                                "unresolved_discussions", []
                            )

                        # Parse approval status if available
                        if pipeline_db_data.get("approval_status"):
                            with contextlib.suppress(json.JSONDecodeError, TypeError):
                                mr_info["approval_status"] = json.loads(
                                    pipeline_db_data["approval_status"]
                                )  # Parse Jira tickets from JSON string only for MR pipelines
            if pipeline_db_data.get("jira_tickets"):
                from ...utils.jira_utils import parse_jira_tickets_from_storage

                jira_tickets = parse_jira_tickets_from_storage(
                    pipeline_db_data["jira_tickets"]
                )

        # Get jobs data from database
        jobs_summary = await cache_manager.get_pipeline_jobs(int(pipeline_id))

        # Add resource links to each job
        jobs_with_links = []
        for job in jobs_summary:
            job_id = job.get("job_id")
            job_status = job.get("status", "unknown")

            # Base resource links for all jobs
            resource_links = [
                {
                    "type": "resource_link",
                    "resourceUri": f"gl://job/{project_id}/{pipeline_id}/{job_id}",
                    "text": f"Analyze job {job_id} details - status: {job_status}, trace logs, and error details",
                }
            ]

            # Additional links for failed jobs - link to files with errors
            if job_status == "failed" and job_id is not None:
                # Get files with errors for this job from database
                files_with_errors = await cache_manager.get_job_files_with_errors(
                    int(job_id)
                )

                if files_with_errors:
                    # Add link to files resource with pagination
                    total_files = len(files_with_errors)
                    resource_links.append(
                        {
                            "type": "resource_link",
                            "resourceUri": f"gl://files/{project_id}/{job_id}?page=1&limit=20",
                            "text": f"Browse {total_files} files with errors in job {job_id} - detailed error analysis and code locations",
                        }
                    )
                else:
                    # Fallback to analysis if no files with errors found
                    resource_links.append(
                        {
                            "type": "resource_link",
                            "resourceUri": f"gl://analysis/{project_id}/job/{job_id}",
                            "text": f"Get comprehensive analysis of job {job_id} failures - detailed error reports and recommendations",
                        }
                    )

            job_data = {
                **job,  # Copy all existing job data
                "resource_links": resource_links,
            }
            jobs_with_links.append(job_data)

        # Build complete result with comprehensive pipeline info
        result = {
            "pipeline_info": pipeline_info,
            "jobs": jobs_with_links,
            "jobs_count": len(jobs_with_links),
            "failed_jobs_count": len(
                [j for j in jobs_with_links if j.get("status") == "failed"]
            ),
            "metadata": {
                "resource_type": "pipeline",
                "project_id": project_id,
                "pipeline_id": int(pipeline_id),
                "data_source": "database",
                "cached_at": None,  # TODO: Implement cache stats
            },
            "mcp_info": get_mcp_info("pipeline_resource"),
        }

        # Add MR information if available
        if mr_info:
            result["merge_request"] = mr_info

        # Add Jira tickets if available
        if jira_tickets:
            result["jira_tickets"] = jira_tickets

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
    async def pipeline_resource(
        project_id: str, pipeline_id: str
    ) -> TextResourceContents:
        """Pipeline resource with comprehensive info and jobs list"""
        result = await get_pipeline_resource(project_id, pipeline_id)
        return create_text_resource(f"gl://pipeline/{project_id}/{pipeline_id}", result)

    logger.info("Pipeline resources registered")
