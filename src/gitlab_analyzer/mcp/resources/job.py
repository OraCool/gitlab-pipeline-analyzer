"""
Job resources for MCP server

Copyright (c) 2025 Siarhei Skuratovich
Licensed under the MIT License - see LICENSE file for details
"""

import json
import logging
from datetime import UTC, datetime

from ..cache import get_cache_manager
from ..tools.utils import get_gitlab_analyzer, get_mcp_info

logger = logging.getLogger(__name__)


def register_job_resources(mcp) -> None:
    """Register job resources with MCP server"""

    @mcp.resource("gl://job/{project_id}/{job_id}")
    async def get_job_resource(project_id: str, job_id: str) -> str:
        """
        Get job trace as a resource with caching.

        Args:
            project_id: GitLab project ID
            job_id: GitLab job ID

        Returns:
            Job trace with metadata and MCP info
        """
        try:
            cache_manager = get_cache_manager()
            analyzer = get_gitlab_analyzer()

            # Create cache key for job trace
            cache_key = f"job_trace_{project_id}_{job_id}"

            # Try to get from cache first
            cached_data = await cache_manager.get(cache_key)
            if cached_data:
                return json.dumps(cached_data, indent=2)

            # Get job trace from GitLab
            trace = await analyzer.get_job_trace(project_id, int(job_id))

            # Process the trace data
            result = {
                "job_trace": {
                    "project_id": project_id,
                    "job_id": int(job_id),
                    "trace": trace,
                    "trace_length": len(trace),
                    "has_content": bool(trace.strip()),
                },
                "resource_uri": f"gl://job/{project_id}/{job_id}",
                "cached_at": datetime.now(UTC).isoformat(),
            }

            mcp_info = get_mcp_info(
                tool_used="get_job_trace", error=False, parser_type="resource"
            )

            # Cache the result
            result["mcp_info"] = mcp_info
            await cache_manager.set(
                cache_key,
                result,
                data_type="job",
                project_id=project_id,
                job_id=int(job_id),
            )

            return json.dumps(result, indent=2)

        except Exception as e:
            logger.error(f"Error getting job resource {project_id}/{job_id}: {e}")
            error_result = {
                "error": f"Failed to get job resource: {str(e)}",
                "project_id": project_id,
                "job_id": job_id,
                "resource_uri": f"gl://job/{project_id}/{job_id}",
            }
            return json.dumps(error_result, indent=2)

    logger.info("Job resources registered")
