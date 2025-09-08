"""
Merge Request resources for MCP server

Copyright (c) 2025 Siarhei Skuratovich
Licensed under the MIT License - see LICENSE file for details
"""

import logging
from typing import Any

from mcp.types import TextResourceContents

from gitlab_analyzer.cache.mcp_cache import get_cache_manager
from gitlab_analyzer.utils.utils import get_mcp_info

from .utils import create_text_resource

logger = logging.getLogger(__name__)


async def get_merge_request_resource(project_id: str, mr_iid: str) -> dict[str, Any]:
    """Get comprehensive merge request review data from database"""
    cache_manager = get_cache_manager()

    async def compute_mr_data() -> dict[str, Any]:
        """Get MR data from database by finding associated pipeline"""
        logger.info(f"Getting MR review data from database for {project_id}/{mr_iid}")

        # Find pipeline data for this MR
        # We need to search for a pipeline with this MR IID
        pipeline_data = await cache_manager.get_pipeline_by_mr_iid(
            int(project_id), int(mr_iid)
        )

        if not pipeline_data:
            return {
                "error": "mr_not_analyzed",
                "message": f"Merge request {mr_iid} has not been analyzed yet. Please run pipeline analysis first.",
                "required_action": "Call failed_pipeline_analysis tool for associated pipeline",
                "mr_iid": int(mr_iid),
                "project_id": project_id,
                "metadata": {
                    "resource_type": "merge_request",
                    "data_source": "none",
                    "status": "not_analyzed",
                },
                "mcp_info": get_mcp_info("merge_request_resource"),
            }

        # Build comprehensive MR information
        mr_info = {
            "iid": pipeline_data.get("mr_iid"),
            "title": pipeline_data.get("mr_title"),
            "description": pipeline_data.get("mr_description"),
            "author": pipeline_data.get("mr_author"),
            "web_url": pipeline_data.get("mr_web_url"),
            "source_branch": pipeline_data.get("source_branch"),
            "target_branch": pipeline_data.get("target_branch"),
        }

        # Parse complete review summary from JSON string if available
        review_summary = None
        if pipeline_data.get("review_summary"):
            import contextlib
            import json

            with contextlib.suppress(json.JSONDecodeError, TypeError):
                review_summary = json.loads(pipeline_data["review_summary"])

        # Parse Jira tickets from JSON string
        jira_tickets = []
        if pipeline_data.get("jira_tickets"):
            from ...utils.jira_utils import parse_jira_tickets_from_storage

            jira_tickets = parse_jira_tickets_from_storage(
                pipeline_data["jira_tickets"]
            )

        # Build complete result
        result = {
            "merge_request": mr_info,
            "metadata": {
                "resource_type": "merge_request",
                "project_id": project_id,
                "mr_iid": int(mr_iid),
                "data_source": "database",
                "pipeline_id": pipeline_data.get("pipeline_id"),
            },
            "mcp_info": get_mcp_info("merge_request_resource"),
        }

        # Add Jira tickets if available
        if jira_tickets:
            result["jira_tickets"] = jira_tickets

        # Add complete code review data if available
        if review_summary and not review_summary.get("error"):
            result["code_review"] = review_summary

        return result

    return await compute_mr_data()


def register_merge_request_resources(mcp) -> None:
    """Register merge request resources with MCP server"""

    @mcp.resource("gl://mr/{project_id}/{mr_iid}")
    async def merge_request_resource(
        project_id: str, mr_iid: str
    ) -> TextResourceContents:
        """Merge request resource with comprehensive review information"""
        result = await get_merge_request_resource(project_id, mr_iid)
        return create_text_resource(f"gl://mr/{project_id}/{mr_iid}", result)

    logger.info("Merge request resources registered")
