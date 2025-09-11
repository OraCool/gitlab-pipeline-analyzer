"""
Error Service

Handles core error data retrieval and processing logic.
Responsible for:
- Retrieving error data from cache
- Processing and enhancing error information
- Coordinating between cache and formatters

Copyright (c) 2025 Siarhei Skuratovich
Licensed under the MIT License - see LICENSE file for details
"""

import json
import logging
from datetime import datetime, timezone
from typing import Any

from gitlab_analyzer.cache.mcp_cache import get_cache_manager
from gitlab_analyzer.mcp.utils.pipeline_validation import (
    check_job_analyzed,
    check_pipeline_analyzed,
)
from gitlab_analyzer.utils.utils import get_mcp_info

logger = logging.getLogger(__name__)


class ErrorService:
    """Service for handling error data retrieval and processing"""

    def __init__(self):
        self.cache_manager = get_cache_manager()

    async def get_job_errors(
        self, project_id: str, job_id: str, mode: str = "balanced"
    ) -> dict[str, Any]:
        """
        Get all errors for a specific job.

        Args:
            project_id: GitLab project ID
            job_id: GitLab job ID
            mode: Response mode (balanced, detailed, minimal)

        Returns:
            Job error data as dict
        """
        try:
            # Check if job has been analyzed using utility function
            error_response = await check_job_analyzed(project_id, job_id, "job_errors")
            if error_response:
                return error_response

            # Get errors from database (pre-analyzed data)
            job_errors = self.cache_manager.get_job_errors(int(job_id))

            # Process errors from database
            all_errors = []
            error_files = set()
            error_types = set()

            for db_error in job_errors:
                # Extract test function info from detail if available
                test_function = db_error.get("test_function", "")
                if not test_function and "detail" in db_error:
                    test_function = db_error["detail"].get("test_function", "")

                # Enhance error message with test function if available
                base_message = db_error["message"]
                if test_function:
                    enhanced_message = f"Test: {test_function} - {base_message}"
                else:
                    enhanced_message = base_message

                error_data = {
                    "id": db_error["id"],
                    "message": enhanced_message,
                    "level": "error",  # All from get_job_errors are errors
                    "line_number": db_error.get("line"),
                    "file_path": db_error.get("file_path"),
                    "exception_type": db_error.get(
                        "exception"
                    ),  # Map from 'exception' field
                    "fingerprint": db_error.get("fingerprint"),
                    "test_function": test_function,  # Add test function as separate field
                    "detail": db_error.get("detail", {}),
                }
                all_errors.append(error_data)

                # Track error files and types for statistics
                if error_data.get("file_path"):
                    error_files.add(str(error_data["file_path"]))
                if error_data.get(
                    "exception_type"
                ):  # Use exception_type for consistency
                    error_types.add(error_data["exception_type"])

            return {
                "error_analysis": {
                    "project_id": project_id,
                    "job_id": int(job_id),
                    "errors": all_errors,
                    "error_count": len(all_errors),
                    "error_statistics": {
                        "total_errors": len(all_errors),
                        "affected_files": list(error_files),
                        "affected_file_count": len(error_files),
                        "error_types": list(error_types),
                        "unique_error_types": len(error_types),
                        "error_distribution": {
                            error_type: sum(
                                1
                                for err in all_errors
                                if err.get("error_type") == error_type
                            )
                            for error_type in error_types
                        },
                    },
                },
                "resource_uri": f"gl://error/{project_id}/{job_id}?mode={mode}",
                "cached_at": datetime.now(timezone.utc).isoformat(),
                "metadata": {
                    "analysis_scope": "all-errors",
                    "source": "job_trace",
                    "response_mode": mode,
                    "coverage": "complete",
                },
                "mcp_info": get_mcp_info(
                    "get_job_trace", error=False, parser_type="resource"
                ),
            }

        except Exception as e:
            logger.error("Error getting job errors %s/%s: %s", project_id, job_id, e)
            return {
                "error": f"Failed to get job errors: {str(e)}",
                "project_id": project_id,
                "job_id": job_id,
                "resource_uri": f"gl://error/{project_id}/{job_id}?mode={mode}",
            }

    async def get_file_errors(
        self, project_id: str, job_id: str, file_path: str, mode: str = "balanced"
    ) -> dict[str, Any]:
        """
        Get errors for a specific file in a job.

        Args:
            project_id: GitLab project ID
            job_id: GitLab job ID
            file_path: Path to the specific file
            mode: Response mode (balanced, detailed, minimal)

        Returns:
            File error data as dict
        """
        try:
            # Get errors for the specific file
            file_errors = self.cache_manager.get_file_errors(int(job_id), file_path)

            enhanced_errors = []
            for error in file_errors:
                enhanced_error = {
                    "id": error["error_id"],  # Use error_id instead of id
                    "message": error["message"],
                    "line_number": error.get("line"),
                    "file_path": error.get("file"),  # Use file instead of file_path
                    "exception_type": error.get("error_type"),
                    "severity": "error",
                    "context": {
                        "job_id": int(job_id),
                        "project_id": project_id,
                        "file_path": file_path,
                    },
                    "resource_links": [
                        {
                            "type": "resource_link",
                            "resourceUri": f"gl://file/{project_id}/{job_id}/{file_path}",
                            "text": f"View full file content: {file_path}",
                        },
                        {
                            "type": "resource_link",
                            "resourceUri": f"gl://error/{project_id}/{job_id}/{error['error_id']}",
                            "text": "View detailed error analysis with fixing recommendations",
                        },
                    ],
                }
                enhanced_errors.append(enhanced_error)

            return {
                "file_path": file_path,
                "job_id": int(job_id),
                "project_id": project_id,
                "errors": enhanced_errors,
                "summary": {
                    "total_errors": len(enhanced_errors),
                    "file_path": file_path,
                    "error_types": list(
                        {e.get("exception_type", "unknown") for e in enhanced_errors}
                    ),
                },
                "resource_links": [
                    {
                        "type": "resource_link",
                        "resourceUri": f"gl://errors/{project_id}/{job_id}",
                        "text": "View all errors in this job",
                    },
                    {
                        "type": "resource_link",
                        "resourceUri": f"gl://file/{project_id}/{job_id}/{file_path}",
                        "text": f"View complete file: {file_path}",
                    },
                ],
            }

        except Exception as e:
            logger.error(
                "Error getting file errors %s/%s/%s: %s",
                project_id,
                job_id,
                file_path,
                e,
            )
            return {
                "error": f"Failed to get file errors: {str(e)}",
                "project_id": project_id,
                "job_id": job_id,
                "file_path": file_path,
                "resource_uri": f"gl://errors/{project_id}/{job_id}/{file_path}",
            }

    async def get_pipeline_errors(
        self, project_id: str, pipeline_id: str, mode: str = "balanced"
    ) -> dict[str, Any]:
        """
        Get all errors across all jobs in a pipeline.

        Args:
            project_id: GitLab project ID
            pipeline_id: GitLab pipeline ID
            mode: Response mode (balanced, detailed, minimal)

        Returns:
            Pipeline error data as dict
        """
        try:
            # Check if pipeline has been analyzed using utility function
            error_response = await check_pipeline_analyzed(
                project_id, pipeline_id, "pipeline_errors"
            )
            if error_response:
                return error_response

            # Get all failed jobs in the pipeline
            failed_jobs = self.cache_manager.get_pipeline_failed_jobs(int(pipeline_id))

            all_errors = []
            error_summary: dict[str, Any] = {
                "total_errors": 0,
                "failed_jobs": len(failed_jobs),
                "jobs_with_errors": [],
                "error_types": set(),
                "affected_files": set(),
            }

            for job in failed_jobs:
                job_id = job.get("job_id")
                if job_id is None:
                    continue
                job_errors = self.cache_manager.get_job_errors(int(job_id))

                if job_errors:
                    error_summary["jobs_with_errors"].append(
                        {
                            "job_id": job_id,
                            "job_name": job.get("name"),
                            "error_count": len(job_errors),
                        }
                    )

                    for error in job_errors:
                        enhanced_error = {
                            "id": error["id"],
                            "message": error["message"],
                            "job_id": job_id,
                            "job_name": job.get("name"),
                            "line_number": error.get("line"),
                            "file_path": error.get("file_path"),
                            "exception_type": error.get("error_type"),
                            "resource_links": [
                                {
                                    "type": "resource_link",
                                    "resourceUri": f"gl://error/{project_id}/{job_id}/{error['id']}",
                                    "text": "View detailed error with fixing recommendations",
                                },
                                {
                                    "type": "resource_link",
                                    "resourceUri": f"gl://errors/{project_id}/{job_id}",
                                    "text": f"View all errors in job {job.get('name', job_id)}",
                                },
                            ],
                        }
                        all_errors.append(enhanced_error)

                        if error.get("error_type"):
                            error_summary["error_types"].add(error["error_type"])
                        if error.get("file_path"):
                            error_summary["affected_files"].add(error["file_path"])

            error_summary["total_errors"] = len(all_errors)
            error_summary["error_types"] = list(error_summary["error_types"])
            error_summary["affected_files"] = list(error_summary["affected_files"])

            return {
                "pipeline_id": int(pipeline_id),
                "project_id": project_id,
                "errors": all_errors,
                "summary": error_summary,
                "resource_links": [
                    {
                        "type": "resource_link",
                        "resourceUri": f"gl://pipeline/{project_id}/{pipeline_id}",
                        "text": "View complete pipeline analysis",
                    },
                    {
                        "type": "resource_link",
                        "resourceUri": f"gl://jobs/{project_id}/pipeline/{pipeline_id}/failed",
                        "text": "View all failed jobs in this pipeline",
                    },
                ],
            }

        except Exception as e:
            logger.error(
                "Error getting pipeline errors %s/%s: %s", project_id, pipeline_id, e
            )
            return {
                "error": f"Failed to get pipeline errors: {str(e)}",
                "project_id": project_id,
                "pipeline_id": pipeline_id,
                "resource_uri": f"gl://errors/{project_id}/pipeline/{pipeline_id}",
            }

    async def get_individual_error(
        self, project_id: str, job_id: str, error_id: str, mode: str = "balanced"
    ) -> dict[str, Any]:
        """
        Get details for a specific individual error.

        Args:
            project_id: GitLab project ID
            job_id: GitLab job ID
            error_id: Error ID (e.g., "76474190_0")
            mode: Analysis mode (minimal, balanced, fixing, detailed)

        Returns:
            Individual error data as dict
        """
        try:
            # Get all errors for the job from database
            all_errors = self.cache_manager.get_job_errors(int(job_id))

            # Find error by ID
            target_error = None
            for err in all_errors:
                if (
                    str(err.get("error_id", "")) == error_id
                    or str(err.get("id", "")) == error_id
                ):
                    target_error = err
                    break

            if not target_error:
                return {
                    "error": "Error not found",
                    "message": f"Error {error_id} not found in job {job_id}",
                    "job_id": int(job_id),
                    "project_id": project_id,
                    "error_id": error_id,
                    "suggested_action": f"Use gl://error/{project_id}/{job_id} to view all errors",
                    "mcp_info": get_mcp_info("individual_error_resource"),
                }

            # Parse error detail if it's JSON string
            error_detail = target_error.get("detail", {})
            if isinstance(error_detail, str):
                try:
                    error_detail = json.loads(error_detail)
                except json.JSONDecodeError:
                    error_detail = {"raw_detail": error_detail}

            # Get job info for context and navigation
            job_info = await self.cache_manager.get_job_info_async(int(job_id))

            # Build enhanced error
            enhanced_error = {
                "error_id": target_error.get("error_id", error_id),
                "fingerprint": target_error.get("fingerprint"),
                "exception": target_error.get("error_type"),
                "message": target_error.get("message"),
                "file": target_error.get("file_path"),
                "line": target_error.get("line"),
                "detail": error_detail,
                "source": "database",
            }

            # Add resource links for navigation
            resource_links = []

            # Link back to file containing this error
            if target_error.get("file_path"):
                resource_links.append(
                    {
                        "type": "resource_link",
                        "resourceUri": f"gl://file/{project_id}/{job_id}/{target_error['file_path']}",
                        "text": f"View all errors in {target_error['file_path']} - complete file analysis and error context",
                    }
                )

                # Add file trace link for enhanced analysis
                if mode in ["fixing", "detailed"]:
                    resource_links.append(
                        {
                            "type": "resource_link",
                            "resourceUri": f"gl://file/{project_id}/{job_id}/{target_error['file_path']}/trace?mode=fixing&include_trace=true",
                            "text": "View enhanced file analysis with trace and fixing recommendations",
                        }
                    )

            # Link back to job
            if job_info:
                resource_links.append(
                    {
                        "type": "resource_link",
                        "resourceUri": f"gl://job/{project_id}/{job_info['pipeline_id']}/{job_id}",
                        "text": f"Return to job {job_id} overview - view all files and job execution details",
                    }
                )

                # Link back to pipeline
                resource_links.append(
                    {
                        "type": "resource_link",
                        "resourceUri": f"gl://pipeline/{project_id}/{job_info['pipeline_id']}",
                        "text": f"Navigate to pipeline {job_info['pipeline_id']} - view all jobs and pipeline status",
                    }
                )

            # Link to all errors in this job
            resource_links.append(
                {
                    "type": "resource_link",
                    "resourceUri": f"gl://error/{project_id}/{job_id}",
                    "text": f"View all errors in job {job_id} - comprehensive error analysis and statistics",
                }
            )

            return {
                "individual_error_analysis": {
                    "project_id": project_id,
                    "job_id": int(job_id),
                    "error_id": error_id,
                    "error": enhanced_error,
                    "analysis_mode": mode,
                    "data_source": "database_only",
                },
                "job_context": {
                    "job_id": int(job_id),
                    "status": job_info.get("status") if job_info else "unknown",
                    "name": job_info.get("name") if job_info else None,
                },
                "resource_uri": f"gl://error/{project_id}/{job_id}/{error_id}?mode={mode}",
                "cached_at": datetime.now(timezone.utc).isoformat(),
                "resource_links": resource_links,
                "metadata": {
                    "resource_type": "individual_error",
                    "project_id": project_id,
                    "job_id": int(job_id),
                    "error_id": error_id,
                    "analysis_mode": mode,
                    "data_source": "database",
                    "include_fix_guidance": mode in ["fixing", "detailed"],
                },
                "mcp_info": get_mcp_info("individual_error_resource"),
            }

        except Exception as e:
            logger.error(
                "Error getting individual error %s/%s/%s: %s",
                project_id,
                job_id,
                error_id,
                e,
            )
            return {
                "error": f"Failed to get individual error: {str(e)}",
                "project_id": project_id,
                "job_id": job_id,
                "error_id": error_id,
                "resource_uri": f"gl://error/{project_id}/{job_id}/{error_id}?mode={mode}",
                "mcp_info": get_mcp_info("individual_error_resource"),
            }

    async def get_limited_job_errors(
        self,
        project_id: str,
        job_id: str,
        limit: int,
        mode: str = "balanced",
        include_trace: bool = False,
    ) -> dict[str, Any]:
        """
        Get limited number of errors for a job.

        Args:
            project_id: GitLab project ID
            job_id: GitLab job ID
            limit: Maximum number of errors to return
            mode: Analysis mode (minimal, balanced, fixing, detailed)
            include_trace: Whether to include trace context

        Returns:
            Limited job error data as dict
        """
        try:
            # Get all errors for the job from database
            all_errors = self.cache_manager.get_job_errors(int(job_id))

            if not all_errors:
                return {
                    "error": "No errors found",
                    "message": f"No errors found for job {job_id}",
                    "job_id": int(job_id),
                    "project_id": project_id,
                    "limit": limit,
                    "mode": mode,
                    "include_trace": include_trace,
                    "suggested_action": f"Check if job {job_id} has been analyzed",
                    "mcp_info": get_mcp_info("limited_job_errors_resource"),
                }

            # Apply limit
            limited_errors = all_errors[:limit]

            # Basic error enhancement (formatting will be handled by formatter)
            enhanced_errors = []
            for error in limited_errors:
                enhanced_error = {
                    "id": error["id"],
                    "message": error["message"],
                    "line_number": error.get("line"),
                    "file_path": error.get("file_path"),
                    "exception_type": error.get("error_type"),
                    "severity": "error",
                    "context": {
                        "job_id": int(job_id),
                        "project_id": project_id,
                    },
                    "resource_links": [
                        {
                            "type": "resource_link",
                            "resourceUri": f"gl://error/{project_id}/{job_id}/{error['id']}",
                            "text": "View detailed error analysis with fixing recommendations",
                        }
                    ],
                }

                # Add trace context if requested and mode supports it
                if include_trace and mode in ["fixing", "detailed"]:
                    try:
                        trace_excerpt = self.cache_manager.get_job_trace_excerpt(
                            int(job_id), error["id"], mode
                        )
                        if trace_excerpt:
                            enhanced_error["trace_excerpt"] = trace_excerpt
                    except Exception as trace_error:
                        logger.warning(
                            "Failed to get trace excerpt for error %s: %s",
                            error["id"],
                            trace_error,
                        )

                enhanced_errors.append(enhanced_error)

            return {
                "job_id": int(job_id),
                "project_id": project_id,
                "limit": limit,
                "mode": mode,
                "include_trace": include_trace,
                "errors": enhanced_errors,
                "summary": {
                    "total_errors_available": len(all_errors),
                    "errors_returned": len(enhanced_errors),
                    "limit_applied": limit < len(all_errors),
                    "analysis_mode": mode,
                    "trace_included": include_trace,
                },
                "resource_links": [
                    {
                        "type": "resource_link",
                        "resourceUri": f"gl://error/{project_id}/{job_id}",
                        "text": "View all errors in this job",
                    },
                    {
                        "type": "resource_link",
                        "resourceUri": f"gl://job/{project_id}/**/{job_id}",
                        "text": "View complete job analysis",
                    },
                ],
            }

        except Exception as e:
            logger.error(
                "Error getting limited job errors %s/%s: %s", project_id, job_id, e
            )
            return {
                "error": f"Failed to get limited job errors: {str(e)}",
                "project_id": project_id,
                "job_id": job_id,
                "limit": limit,
                "mode": mode,
                "include_trace": include_trace,
                "resource_uri": f"gl://errors/{project_id}/{job_id}/limit/{limit}?mode={mode}&include_trace={include_trace}",
            }

    async def get_limited_pipeline_errors(
        self,
        project_id: str,
        pipeline_id: str,
        limit: int,
        mode: str = "balanced",
        include_trace: bool = False,
    ) -> dict[str, Any]:
        """
        Get limited number of errors across all jobs in a pipeline.

        Args:
            project_id: GitLab project ID
            pipeline_id: GitLab pipeline ID
            limit: Maximum number of errors to return
            mode: Analysis mode (minimal, balanced, fixing, detailed)
            include_trace: Whether to include trace context

        Returns:
            Limited pipeline error data as dict
        """
        try:
            # Check if pipeline has been analyzed using utility function
            error_response = await check_pipeline_analyzed(
                project_id, pipeline_id, "limited_pipeline_errors"
            )
            if error_response:
                return error_response

            # Get all failed jobs in the pipeline
            failed_jobs = self.cache_manager.get_pipeline_failed_jobs(int(pipeline_id))

            if not failed_jobs:
                return {
                    "error": "No failed jobs found",
                    "message": f"No failed jobs found for pipeline {pipeline_id}",
                    "pipeline_id": int(pipeline_id),
                    "project_id": project_id,
                    "limit": limit,
                    "mode": mode,
                    "include_trace": include_trace,
                    "suggested_action": f"Check if pipeline {pipeline_id} has been analyzed",
                    "mcp_info": get_mcp_info("limited_pipeline_errors_resource"),
                }

            # Collect all errors from all failed jobs
            all_errors = []
            jobs_processed = []

            for job in failed_jobs:
                job_id = job.get("job_id")
                if job_id is None:
                    continue

                job_errors = self.cache_manager.get_job_errors(int(job_id))
                for error in job_errors:
                    # Add job context to each error
                    error_with_job = error.copy()
                    error_with_job["job_id"] = job_id
                    error_with_job["job_name"] = job.get("name")
                    all_errors.append(error_with_job)

                if job_errors:
                    jobs_processed.append(
                        {
                            "job_id": job_id,
                            "job_name": job.get("name"),
                            "error_count": len(job_errors),
                        }
                    )

            # Apply limit to total errors
            limited_errors = all_errors[:limit]

            # Basic error enhancement (formatting will be handled by formatter)
            enhanced_errors = []
            for error in limited_errors:
                enhanced_error = {
                    "id": error["id"],
                    "message": error["message"],
                    "job_id": error["job_id"],
                    "job_name": error.get("job_name"),
                    "line_number": error.get("line"),
                    "file_path": error.get("file_path"),
                    "exception_type": error.get("error_type"),
                    "severity": "error",
                    "context": {
                        "pipeline_id": int(pipeline_id),
                        "project_id": project_id,
                    },
                    "resource_links": [
                        {
                            "type": "resource_link",
                            "resourceUri": f"gl://error/{project_id}/{error['job_id']}/{error['id']}",
                            "text": "View detailed error analysis with fixing recommendations",
                        },
                        {
                            "type": "resource_link",
                            "resourceUri": f"gl://errors/{project_id}/{error['job_id']}",
                            "text": f"View all errors in job {error.get('job_name', error['job_id'])}",
                        },
                    ],
                }

                # Add trace context if requested and mode supports it
                if include_trace and mode in ["fixing", "detailed"]:
                    try:
                        trace_excerpt = self.cache_manager.get_job_trace_excerpt(
                            int(error["job_id"]), error["id"], mode
                        )
                        if trace_excerpt:
                            enhanced_error["trace_excerpt"] = trace_excerpt
                    except Exception as trace_error:
                        logger.warning(
                            "Failed to get trace excerpt for error %s: %s",
                            error["id"],
                            trace_error,
                        )

                enhanced_errors.append(enhanced_error)

            return {
                "pipeline_id": int(pipeline_id),
                "project_id": project_id,
                "limit": limit,
                "mode": mode,
                "include_trace": include_trace,
                "errors": enhanced_errors,
                "summary": {
                    "total_errors_available": len(all_errors),
                    "errors_returned": len(enhanced_errors),
                    "limit_applied": limit < len(all_errors),
                    "failed_jobs_count": len(failed_jobs),
                    "jobs_with_errors": len(jobs_processed),
                    "analysis_mode": mode,
                    "trace_included": include_trace,
                },
                "jobs_processed": jobs_processed,
                "resource_links": [
                    {
                        "type": "resource_link",
                        "resourceUri": f"gl://errors/{project_id}/pipeline/{pipeline_id}",
                        "text": "View all errors in this pipeline",
                    },
                    {
                        "type": "resource_link",
                        "resourceUri": f"gl://pipeline/{project_id}/{pipeline_id}",
                        "text": "View complete pipeline analysis",
                    },
                    {
                        "type": "resource_link",
                        "resourceUri": f"gl://jobs/{project_id}/pipeline/{pipeline_id}/failed",
                        "text": "View all failed jobs in this pipeline",
                    },
                ],
            }

        except Exception as e:
            logger.error(
                "Error getting limited pipeline errors %s/%s: %s",
                project_id,
                pipeline_id,
                e,
            )
            return {
                "error": f"Failed to get limited pipeline errors: {str(e)}",
                "project_id": project_id,
                "pipeline_id": pipeline_id,
                "limit": limit,
                "mode": mode,
                "include_trace": include_trace,
                "resource_uri": f"gl://errors/{project_id}/pipeline/{pipeline_id}/limit/{limit}?mode={mode}&include_trace={include_trace}",
            }


# Create a singleton instance for easy import
error_service = ErrorService()
