"""
File resources for MCP server

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


async def get_file_resource(
    project_id: str, job_id: str, file_path: str
) -> dict[str, Any]:
    """Get file resource data from database only"""
    cache_manager = get_cache_manager()
    cache_key = generate_cache_key(
        "file", project_id, int(job_id), file_path.replace("/", "_")
    )

    async def compute_file_data() -> dict[str, Any]:
        # Get file errors from database
        file_errors = cache_manager.get_file_errors(int(job_id), file_path)

        if not file_errors:
            return {
                "error": "File not found or no errors",
                "message": f"No errors found for file '{file_path}' in job {job_id}",
                "job_id": int(job_id),
                "project_id": project_id,
                "file_path": file_path,
                "suggested_action": f"Check if file has errors or use gl://files/{project_id}/{job_id} to list all files with errors",
                "mcp_info": get_mcp_info("file_resource"),
            }

        # Get job info for context
        job_info = await cache_manager.get_job_info_async(int(job_id))

        # Add resource links for navigation
        resource_links = []

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

        # Link to all files with errors in this job
        resource_links.append(
            {
                "type": "resource_link",
                "resourceUri": f"gl://files/{project_id}/{job_id}",
                "text": f"Browse all files with errors in job {job_id} - compare and analyze multiple files",
            }
        )

        # Add links to individual errors in this file
        for i, error in enumerate(
            file_errors[:10]
        ):  # Limit to first 10 errors to avoid too many links
            error_id = error.get("id", f"error_{i}")
            error_line = error.get("line", "unknown")
            error_type = error.get("exception", "Unknown")
            error_message = (
                error.get("message", "")[:50] + "..."
                if len(error.get("message", "")) > 50
                else error.get("message", "")
            )

            resource_links.append(
                {
                    "type": "resource_link",
                    "resourceUri": f"gl://error/{project_id}/{job_id}/{error_id}",
                    "text": f"Error at line {error_line}: {error_type} - {error_message}",
                }
            )

        if len(file_errors) > 10:
            resource_links.append(
                {
                    "type": "resource_link",
                    "resourceUri": f"gl://file/{project_id}/{job_id}/{file_path}?show_all_errors=true",
                    "text": f"View all {len(file_errors)} errors in this file - complete error analysis",
                }
            )

        # Process error statistics
        error_statistics = {
            "total_errors": len(file_errors),
            "error_types": list(
                set(error.get("exception", "Unknown") for error in file_errors)
            ),
            "line_numbers": sorted(
                set(
                    error.get("line", 0)
                    for error in file_errors
                    if error.get("line", 0) > 0
                )
            ),
            "error_fingerprints": list(
                set(error.get("fingerprint", "") for error in file_errors)
            ),
        }

        # Build complete result with comprehensive file info
        result = {
            "file_info": {
                "path": file_path,
                "job_id": int(job_id),
                "project_id": project_id,
                "file_type": _classify_file_type(file_path),
                "error_count": len(file_errors),
            },
            "errors": file_errors,
            "error_statistics": error_statistics,
            "resource_links": resource_links,
            "metadata": {
                "resource_type": "file",
                "project_id": project_id,
                "job_id": int(job_id),
                "file_path": file_path,
                "data_source": "database",
                "cached_at": None,  # TODO: Implement cache stats
            },
            "mcp_info": get_mcp_info("file_resource"),
        }

        return result

    # Use cache for the computed data
    return await cache_manager.get_or_compute(
        key=cache_key,
        compute_func=compute_file_data,
        data_type="file",
        project_id=project_id,
        job_id=int(job_id),
    )


async def get_files_resource(
    project_id: str, job_id: str, page: int = 1, limit: int = 20
) -> dict[str, Any]:
    """Get list of files with errors for a job from database only"""
    cache_manager = get_cache_manager()
    cache_key = generate_cache_key(
        "files", project_id, int(job_id), f"page_{page}_limit_{limit}"
    )

    async def compute_files_data() -> dict[str, Any]:
        # Get all files with errors for this job
        files_with_errors = await cache_manager.get_job_files_with_errors(int(job_id))

        if not files_with_errors:
            return {
                "error": "No files with errors found",
                "message": f"Job {job_id} has no files with errors in the database",
                "job_id": int(job_id),
                "project_id": project_id,
                "suggested_action": f"Check if job {job_id} has been analyzed or try gl://job/{project_id}/{{pipeline_id}}/{job_id}",
                "mcp_info": get_mcp_info("files_resource"),
            }

        # Apply pagination
        total_files = len(files_with_errors)
        start_idx = (page - 1) * limit
        end_idx = start_idx + limit
        paginated_files = files_with_errors[start_idx:end_idx]

        # Get job info for context and navigation
        job_info = await cache_manager.get_job_info_async(int(job_id))

        # Add resource links for navigation
        resource_links = []

        # Link back to job
        if job_info:
            resource_links.append(
                {
                    "type": "resource_link",
                    "resourceUri": f"gl://job/{project_id}/{job_info['pipeline_id']}/{job_id}",
                    "text": f"Return to job {job_id} summary - view job execution details and status",
                }
            )

        # Links to individual files
        for file_info in paginated_files:
            resource_links.append(
                {
                    "type": "resource_link",
                    "resourceUri": f"gl://file/{project_id}/{job_id}/{file_info['path']}",
                    "text": f"Analyze {file_info['path']} - {file_info['error_count']} errors with line numbers and context",
                }
            )

        # Pagination links
        total_pages = (total_files + limit - 1) // limit
        if page > 1:
            resource_links.append(
                {
                    "type": "resource_link",
                    "resourceUri": f"gl://files/{project_id}/{job_id}?page={page-1}&limit={limit}",
                    "text": f"Previous page of files ({page-1}/{total_pages}) - continue browsing error files",
                }
            )
        if page < total_pages:
            resource_links.append(
                {
                    "type": "resource_link",
                    "resourceUri": f"gl://files/{project_id}/{job_id}?page={page+1}&limit={limit}",
                    "text": f"Next page of files ({page+1}/{total_pages}) - more files with errors to analyze",
                }
            )

        # Build complete result
        result = {
            "files_info": {
                "job_id": int(job_id),
                "project_id": project_id,
                "total_files": total_files,
                "files_shown": len(paginated_files),
                "page": page,
                "limit": limit,
                "total_pages": total_pages,
            },
            "files": paginated_files,
            "resource_links": resource_links,
            "metadata": {
                "resource_type": "files",
                "project_id": project_id,
                "job_id": int(job_id),
                "data_source": "database",
                "pagination": {
                    "page": page,
                    "limit": limit,
                    "total": total_files,
                    "pages": total_pages,
                },
            },
            "mcp_info": get_mcp_info("files_resource"),
        }

        return result

    # Use cache for the computed data
    return await cache_manager.get_or_compute(
        key=cache_key,
        compute_func=compute_files_data,
        data_type="files",
        project_id=project_id,
        job_id=int(job_id),
    )


def register_file_resources(mcp) -> None:
    """Register file resources with MCP server"""

    @mcp.resource("gl://file/{project_id}/{job_id}/{file_path}")
    async def get_file_resource_handler(
        project_id: str, job_id: str, file_path: str
    ) -> str:
        """
        Get file error analysis from database only.

        Args:
            project_id: GitLab project ID
            job_id: GitLab job ID
            file_path: File path to analyze

        Returns:
            File error analysis with detailed errors and navigation links
        """
        try:
            result = await get_file_resource(project_id, job_id, file_path)
            return json.dumps(result, indent=2)

        except Exception as e:
            logger.error(
                f"Error getting file resource {project_id}/{job_id}/{file_path}: {e}"
            )
            error_result = {
                "error": f"Failed to get file resource: {str(e)}",
                "project_id": project_id,
                "job_id": job_id,
                "file_path": file_path,
                "resource_uri": f"gl://file/{project_id}/{job_id}/{file_path}",
                "mcp_info": get_mcp_info("file_resource"),
            }
            return json.dumps(error_result, indent=2)

    @mcp.resource("gl://files/{project_id}/{job_id}")
    async def get_files_resource_handler(project_id: str, job_id: str) -> str:
        """
        Get list of files with errors for a job from database only.

        Args:
            project_id: GitLab project ID
            job_id: GitLab job ID

        Returns:
            Paginated list of files with errors and navigation links
        """
        try:
            # Default pagination
            result = await get_files_resource(project_id, job_id, page=1, limit=20)
            return json.dumps(result, indent=2)

        except Exception as e:
            logger.error(f"Error getting files resource {project_id}/{job_id}: {e}")
            error_result = {
                "error": f"Failed to get files resource: {str(e)}",
                "project_id": project_id,
                "job_id": job_id,
                "resource_uri": f"gl://files/{project_id}/{job_id}",
                "mcp_info": get_mcp_info("files_resource"),
            }
            return json.dumps(error_result, indent=2)

    @mcp.resource("gl://files/{project_id}/{job_id}?page={page}&limit={limit}")
    async def get_files_resource_paginated(
        project_id: str, job_id: str, page: str, limit: str
    ) -> str:
        """
        Get paginated list of files with errors for a job from database only.

        Args:
            project_id: GitLab project ID
            job_id: GitLab job ID
            page: Page number (1-based)
            limit: Number of files per page

        Returns:
            Paginated list of files with errors and navigation links
        """
        try:
            page_num = int(page) if page.isdigit() else 1
            limit_num = int(limit) if limit.isdigit() else 20

            result = await get_files_resource(
                project_id, job_id, page=page_num, limit=limit_num
            )
            return json.dumps(result, indent=2)

        except Exception as e:
            logger.error(
                f"Error getting paginated files resource {project_id}/{job_id}: {e}"
            )
            error_result = {
                "error": f"Failed to get files resource: {str(e)}",
                "project_id": project_id,
                "job_id": job_id,
                "page": page,
                "limit": limit,
                "resource_uri": f"gl://files/{project_id}/{job_id}?page={page}&limit={limit}",
                "mcp_info": get_mcp_info("files_resource"),
            }
            return json.dumps(error_result, indent=2)

    logger.info("File resources registered")


def _classify_file_type(file_path: str) -> str:
    """Classify file type based on path and extension"""
    if "test" in file_path.lower() or file_path.endswith(("_test.py", "test_*.py")):
        return "test"
    elif file_path.endswith((".py", ".js", ".ts", ".java", ".cpp", ".c", ".rs")):
        return "source"
    elif file_path.endswith((".yml", ".yaml", ".json", ".toml", ".cfg", ".ini")):
        return "config"
    elif file_path.endswith((".md", ".rst", ".txt")):
        return "documentation"
    else:
        return "unknown"
