"""
FastMCP resource handlers for cache-first serving.

This implements the serving phase with cache-first resources:
- gl://job/{proj}/{job}/problems
- gl://file/{proj}/{job}/{path}/errors
- gl://error/{proj}/{job}/{err}/trace/{mode}
- gl://pipeline/{proj}/{pipe}/failed_jobs
"""

import logging
from typing import Any
from urllib.parse import unquote

from fastmcp import FastMCP

from ...cache.mcp_cache import McpCache
from ...webhook.processor import process_webhook_event
from ..tools.utils import get_mcp_info, get_gitlab_analyzer


logger = logging.getLogger(__name__)


class CacheFirstResourceHandler:
    """
    Cache-first resource handler for analyzed pipeline data.

    Resources follow the recommended URI pattern:
    - gl://job/{project_id}/{job_id}/problems
    - gl://file/{project_id}/{job_id}/{file_path}/errors
    - gl://error/{project_id}/{job_id}/{error_id}/trace/{mode}
    - gl://pipeline/{project_id}/{pipeline_id}/failed_jobs
    """

    def __init__(self, cache: McpCache | None = None):
        self.cache = cache or McpCache()

    async def handle_pipeline_info_resource(
        self, project_id: str, pipeline_id: int
    ) -> dict[str, Any]:
        """
        Resource: gl://pipeline/{project_id}/{pipeline_id}/info

        Returns pipeline information including resolved branches from cache.
        """
        try:
            pipeline_info = self.cache.get_pipeline_info(pipeline_id)

            if pipeline_info is None:
                return {
                    "status": "not_cached",
                    "pipeline_id": pipeline_id,
                    "project_id": project_id,
                    "message": "Pipeline not found in cache. Trigger webhook analysis first.",
                    "suggested_action": f"POST webhook with project_id={project_id}, pipeline_id={pipeline_id}",
                }

            return {
                "status": "success",
                "pipeline_id": pipeline_id,
                "project_id": project_id,
                "pipeline_info": pipeline_info,
                "source": "cache",
                "mcp_info": get_mcp_info("pipeline_info_resource"),
            }

        except Exception as e:
            logger.error(f"Error getting pipeline info for {pipeline_id}: {e}")
            return {
                "status": "error",
                "pipeline_id": pipeline_id,
                "project_id": project_id,
                "error": str(e),
                "error_type": type(e).__name__,
            }

    async def handle_job_problems_resource(
        self, project_id: str, job_id: int
    ) -> dict[str, Any]:
        """
        Resource: gl://job/{project_id}/{job_id}/problems

        Returns full parsed problems for a job from cache.
        No parsing - direct JSON return from cache.
        """
        try:
            problems = self.cache.get_job_problems(job_id)

            if problems is None:
                # Job not in cache - might need webhook processing
                return {
                    "status": "not_cached",
                    "job_id": job_id,
                    "project_id": project_id,
                    "message": "Job not found in cache. Trigger webhook analysis first.",
                    "suggested_action": f"POST webhook with project_id={project_id}, pipeline_id=<pipeline_id>",
                }

            return {
                "status": "success",
                "job_id": job_id,
                "project_id": project_id,
                "problems": problems,
                "source": "cache",
                "mcp_info": get_mcp_info("job_problems_resource"),
            }

        except Exception as e:
            logger.error(f"Error getting job problems for {job_id}: {e}")
            return {
                "status": "error",
                "job_id": job_id,
                "project_id": project_id,
                "error": str(e),
                "error_type": type(e).__name__,
            }

    async def handle_file_errors_resource(
        self, project_id: str, job_id: int, file_path: str
    ) -> dict[str, Any]:
        """
        Resource: gl://file/{project_id}/{job_id}/{file_path}/errors

        Returns errors for a specific file from cache.
        Fast file-based filtering using file_index table.
        """
        try:
            # Decode URL-encoded file path
            decoded_path = unquote(file_path)

            errors = self.cache.get_file_errors(job_id, decoded_path)

            return {
                "status": "success",
                "job_id": job_id,
                "project_id": project_id,
                "file_path": decoded_path,
                "errors": errors,
                "error_count": len(errors),
                "source": "cache",
                "mcp_info": get_mcp_info("file_errors_resource"),
            }

        except Exception as e:
            logger.error(f"Error getting file errors for {file_path}: {e}")
            return {
                "status": "error",
                "job_id": job_id,
                "project_id": project_id,
                "file_path": file_path,
                "error": str(e),
                "error_type": type(e).__name__,
            }

    async def handle_error_trace_resource(
        self, project_id: str, job_id: int, error_id: str, mode: str = "balanced"
    ) -> dict[str, Any]:
        """
        Resource: gl://error/{project_id}/{job_id}/{error_id}/trace/{mode}

        Returns trace excerpt for specific error.
        Modes: minimal, balanced, full
        """
        try:
            trace_excerpt = self.cache.get_job_trace_excerpt(job_id, error_id, mode)

            if trace_excerpt is None:
                return {
                    "status": "not_found",
                    "job_id": job_id,
                    "project_id": project_id,
                    "error_id": error_id,
                    "message": "Error or trace not found in cache",
                }

            return {
                "status": "success",
                "job_id": job_id,
                "project_id": project_id,
                "error_id": error_id,
                "mode": mode,
                "trace_excerpt": trace_excerpt,
                "source": "cache",
                "mcp_info": get_mcp_info("error_trace_resource"),
            }

        except Exception as e:
            logger.error(f"Error getting trace excerpt for {error_id}: {e}")
            return {
                "status": "error",
                "job_id": job_id,
                "project_id": project_id,
                "error_id": error_id,
                "mode": mode,
                "error": str(e),
                "error_type": type(e).__name__,
            }

    async def handle_pipeline_failed_jobs_resource(
        self, project_id: str, pipeline_id: int
    ) -> dict[str, Any]:
        """
        Resource: gl://pipeline/{project_id}/{pipeline_id}/failed_jobs

        Returns failed jobs for a pipeline from cache.
        Pure DB query - very fast.
        """
        try:
            failed_jobs = self.cache.get_pipeline_failed_jobs(pipeline_id)

            return {
                "status": "success",
                "project_id": project_id,
                "pipeline_id": pipeline_id,
                "failed_jobs": failed_jobs,
                "failed_job_count": len(failed_jobs),
                "source": "cache",
                "mcp_info": get_mcp_info("pipeline_failed_jobs_resource"),
            }

        except Exception as e:
            logger.error(f"Error getting failed jobs for pipeline {pipeline_id}: {e}")
            return {
                "status": "error",
                "project_id": project_id,
                "pipeline_id": pipeline_id,
                "error": str(e),
                "error_type": type(e).__name__,
            }


# Initialize global handler
_resource_handler = CacheFirstResourceHandler()


def register_cache_resources(app: FastMCP):
    """Register cache-first resources with FastMCP"""

    @app.resource("gl://pipeline/{project_id}/{pipeline_id}/info")
    async def pipeline_info_resource(project_id: str, pipeline_id: int):
        """Get pipeline information including branch resolution"""
        return await _resource_handler.handle_pipeline_info_resource(
            project_id, pipeline_id
        )

    @app.resource("gl://job/{project_id}/{job_id}/problems")
    async def job_problems_resource(project_id: str, job_id: int):
        """Get full parsed problems for a job"""
        return await _resource_handler.handle_job_problems_resource(project_id, job_id)

    @app.resource("gl://file/{project_id}/{job_id}/{file_path:path}/errors")
    async def file_errors_resource(project_id: str, job_id: int, file_path: str):
        """Get errors for a specific file"""
        return await _resource_handler.handle_file_errors_resource(
            project_id, job_id, file_path
        )

    @app.resource("gl://error/{project_id}/{job_id}/{error_id}/trace/{mode}")
    async def error_trace_resource(
        project_id: str, job_id: int, error_id: str, mode: str
    ):
        """Get trace excerpt for specific error"""
        return await _resource_handler.handle_error_trace_resource(
            project_id, job_id, error_id, mode
        )

    @app.resource("gl://pipeline/{project_id}/{pipeline_id}/failed_jobs")
    async def pipeline_failed_jobs_resource(project_id: str, pipeline_id: int):
        """Get failed jobs for a pipeline"""
        return await _resource_handler.handle_pipeline_failed_jobs_resource(
            project_id, pipeline_id
        )


def register_webhook_tools(app: FastMCP):
    """Register webhook processing tools"""

    @app.tool()
    async def trigger_pipeline_analysis(
        project_id: str, pipeline_id: int
    ) -> dict[str, Any]:
        """
        Trigger webhook-style analysis for a pipeline.

        This processes the pipeline like a webhook would:
        1. Fetch failed jobs
        2. Parse traces
        3. Cache results
        4. Return processing summary
        """
        try:
            gitlab_analyzer = get_gitlab_analyzer()
            result = await process_webhook_event(
                project_id, pipeline_id, gitlab_analyzer
            )

            # Add resource URIs for accessing cached data
            if result.get("status") == "success":
                resource_uris = []
                for job_id in result.get("processed_job_ids", []):
                    resource_uris.extend(
                        [
                            f"gl://job/{project_id}/{job_id}/problems",
                            f"gl://error/{project_id}/{job_id}/*/trace/balanced",
                        ]
                    )

                result["available_resources"] = resource_uris
                result["cache_info"] = {
                    "cache_type": "sqlite",
                    "parser_version": _resource_handler.cache.parser_version,
                    "immutable_records": True,
                }

            return result

        except Exception as e:
            logger.error(f"Failed to trigger pipeline analysis: {e}")
            return {
                "status": "error",
                "project_id": project_id,
                "pipeline_id": pipeline_id,
                "error": str(e),
                "error_type": type(e).__name__,
            }

    @app.tool()
    async def get_cache_status(project_id: str, pipeline_id: int) -> dict[str, Any]:
        """
        Get cache status for a pipeline.

        Shows what's cached and what resources are available.
        """
        try:
            failed_jobs = _resource_handler.cache.get_pipeline_failed_jobs(pipeline_id)

            available_resources = []
            for job in failed_jobs:
                job_id = job["job_id"]
                available_resources.extend(
                    [
                        f"gl://job/{project_id}/{job_id}/problems",
                        f"gl://pipeline/{project_id}/{pipeline_id}/failed_jobs",
                    ]
                )

            return {
                "status": "success",
                "project_id": project_id,
                "pipeline_id": pipeline_id,
                "cache_summary": {
                    "failed_jobs_cached": len(failed_jobs),
                    "parser_version": _resource_handler.cache.parser_version,
                    "cache_type": "sqlite",
                },
                "available_resources": available_resources,
                "mcp_info": get_mcp_info("cache_status"),
            }

        except Exception as e:
            logger.error(f"Failed to get cache status: {e}")
            return {
                "status": "error",
                "project_id": project_id,
                "pipeline_id": pipeline_id,
                "error": str(e),
                "error_type": type(e).__name__,
            }
