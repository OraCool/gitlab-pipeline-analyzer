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


async def get_file_resource_with_trace(
    project_id: str,
    job_id: str,
    file_path: str,
    mode: str = "balanced",
    include_trace: bool = True,
) -> dict[str, Any]:
    """Get file resource data with trace analysis and different modes"""
    cache_manager = get_cache_manager()
    cache_key = generate_cache_key(
        "file_trace", project_id, int(job_id), file_path.replace("/", "_"), mode
    )

    async def compute_file_trace_data() -> dict[str, Any]:
        # Get database errors first
        file_errors = cache_manager.get_file_errors(int(job_id), file_path)

        if not file_errors and not include_trace:
            return {
                "error": "File not found or no errors",
                "message": f"No errors found for file '{file_path}' in job {job_id}",
                "job_id": int(job_id),
                "project_id": project_id,
                "file_path": file_path,
                "suggested_action": f"Try with include_trace=true or use gl://files/{project_id}/{job_id}",
                "mcp_info": get_mcp_info("file_trace_resource"),
            }

        # Get trace-based analysis if requested and enhance each error with trace records
        trace_context = []
        enhanced_errors = []

        if include_trace:
            try:
                from gitlab_analyzer.utils.utils import get_gitlab_analyzer
                from gitlab_analyzer.parsers.log_parser import LogParser

                analyzer = get_gitlab_analyzer()
                trace = await analyzer.get_job_trace(project_id, int(job_id))

                parser = LogParser()
                log_entries = parser.extract_log_entries(trace)

                # Filter trace entries related to this specific file
                file_trace_entries = []
                for entry in log_entries:
                    # Check multiple ways to match the file
                    entry_file = getattr(entry, "file_path", None)
                    if not entry_file:
                        # Try to extract file path from message
                        import re

                        file_match = re.search(
                            rf"{re.escape(file_path.split('/')[-1])}", entry.message
                        )
                        if file_match or file_path in entry.message:
                            entry_file = file_path

                    if entry_file and (
                        file_path in str(entry_file) or str(entry_file) in file_path
                    ):
                        file_trace_entries.append(entry)

                        # Collect context entries for debugging modes
                        if entry.level != "error" and mode in ["fixing", "full"]:
                            context_entry = {
                                "message": entry.message,
                                "level": entry.level,
                                "line_number": entry.line_number,
                                "file_path": entry_file,
                                "source": "trace_context",
                            }
                            trace_context.append(context_entry)

                # Now enhance each database error with matching trace records and fix guidance
                for db_error in file_errors:
                    enhanced_error = db_error.copy()
                    enhanced_error["source"] = "database"
                    enhanced_error["trace_records"] = []

                    # Generate fix guidance FIRST using original database error structure
                    if mode == "fixing":
                        from gitlab_analyzer.utils.utils import _generate_fix_guidance

                        # Map database error fields to what fix guidance generator expects
                        fix_guidance_error = {
                            "exception_type": db_error.get("exception", ""),
                            "exception_message": db_error.get("message", ""),
                            "line": db_error.get("line", 0),
                            "file_path": db_error.get("file", ""),
                            # Also include detail fields if available
                            **db_error.get("detail", {}),
                        }
                        enhanced_error["fix_guidance"] = _generate_fix_guidance(
                            fix_guidance_error
                        )

                    # Find matching trace entries for this specific error
                    db_line = db_error.get("line", 0)
                    db_message = db_error.get("message", "").lower()
                    db_exception = db_error.get("exception", "").lower()

                    matching_traces = []
                    for trace_entry in file_trace_entries:
                        if trace_entry.level == "error":
                            trace_line = trace_entry.line_number
                            trace_message = trace_entry.message.lower()

                            # Match by line number (exact or close)
                            line_match = False
                            if db_line and trace_line:
                                line_match = (
                                    abs(int(db_line) - int(trace_line)) <= 2
                                )  # Allow 2 line variance

                            # Match by error content
                            content_match = False
                            if db_exception and db_exception in trace_message:
                                content_match = True
                            elif any(
                                word in trace_message
                                for word in db_message.split()[:3]
                                if len(word) > 3
                            ):
                                content_match = True

                            # Include if either line or content matches
                            if line_match or content_match:
                                trace_record = {
                                    "message": trace_entry.message,
                                    "level": trace_entry.level,
                                    "line_number": trace_entry.line_number,
                                    "context": trace_entry.context,
                                    "match_reason": ("line_match" if line_match else "")
                                    + (
                                        "_content_match"
                                        if content_match
                                        else "content_match"
                                    ),
                                    "source": "trace",
                                }
                                matching_traces.append(trace_record)

                    # Add trace records to this error
                    enhanced_error["trace_records"] = matching_traces
                    enhanced_error["trace_count"] = len(matching_traces)
                    enhanced_errors.append(enhanced_error)

                # Also add any trace errors that didn't match database errors
                unmatched_trace_errors = []
                for trace_entry in file_trace_entries:
                    if trace_entry.level == "error":
                        # Check if this trace error was already matched
                        is_matched = False
                        for enhanced_error in enhanced_errors:
                            for trace_record in enhanced_error.get("trace_records", []):
                                if (
                                    trace_record["message"] == trace_entry.message
                                    and trace_record["line_number"]
                                    == trace_entry.line_number
                                ):
                                    is_matched = True
                                    break
                            if is_matched:
                                break

                        if not is_matched:
                            trace_only_error = {
                                "message": trace_entry.message,
                                "level": trace_entry.level,
                                "line_number": trace_entry.line_number,
                                "file_path": file_path,
                                "exception_type": (
                                    _extract_exception_type_from_message(
                                        trace_entry.message
                                    )
                                    if trace_entry.message
                                    else None
                                ),
                                "context": trace_entry.context,
                                "source": "trace_only",
                                "trace_records": [
                                    {
                                        "message": trace_entry.message,
                                        "level": trace_entry.level,
                                        "line_number": trace_entry.line_number,
                                        "context": trace_entry.context,
                                        "match_reason": "trace_only",
                                        "source": "trace",
                                    }
                                ],
                                "trace_count": 1,
                            }
                            unmatched_trace_errors.append(trace_only_error)

                # Combine enhanced database errors with unmatched trace errors
                all_errors = enhanced_errors + unmatched_trace_errors

            except Exception as e:
                logger.warning(
                    f"Could not get trace analysis for file {file_path}: {e}"
                )
                # Fall back to database errors without trace enhancement
                all_errors = []
                for db_error in file_errors:
                    enhanced_error = db_error.copy()
                    enhanced_error["source"] = "database"
                    enhanced_error["trace_records"] = []
                    enhanced_error["trace_count"] = 0
                    enhanced_error["trace_error"] = str(e)
                    all_errors.append(enhanced_error)
        else:
            # No trace analysis requested - just add source info to database errors
            all_errors = []
            for db_error in file_errors:
                enhanced_error = db_error.copy()
                enhanced_error["source"] = "database"
                enhanced_error["trace_records"] = []
                enhanced_error["trace_count"] = 0

                # Generate fix guidance for fixing mode even without trace
                if mode == "fixing":
                    from gitlab_analyzer.utils.utils import _generate_fix_guidance

                    # Map database error fields to what fix guidance generator expects
                    fix_guidance_error = {
                        "exception_type": db_error.get("exception", ""),
                        "exception_message": db_error.get("message", ""),
                        "line": db_error.get("line", 0),
                        "file_path": db_error.get("file", ""),
                        # Also include detail fields if available
                        **db_error.get("detail", {}),
                    }
                    enhanced_error["fix_guidance"] = _generate_fix_guidance(
                        fix_guidance_error
                    )

                all_errors.append(enhanced_error)

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

        # Add mode-specific links
        if mode != "full":
            resource_links.append(
                {
                    "type": "resource_link",
                    "resourceUri": f"gl://file/{project_id}/{job_id}/{file_path}?mode=full&include_trace=true",
                    "text": f"Get complete trace analysis for {file_path} - maximum detail and context",
                }
            )

        if not include_trace:
            resource_links.append(
                {
                    "type": "resource_link",
                    "resourceUri": f"gl://file/{project_id}/{job_id}/{file_path}?mode={mode}&include_trace=true",
                    "text": f"Include trace analysis for {file_path} - trace-based error detection",
                }
            )

        # Add links to individual errors (from database)
        for i, error in enumerate(file_errors[:5]):  # Limit to first 5 errors
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
                    "text": f"Database error at line {error_line}: {error_type} - {error_message}",
                }
            )

        # Apply mode filtering
        from gitlab_analyzer.utils.utils import optimize_tool_response

        # Process error statistics
        error_statistics = {
            "total_errors": len(all_errors),
            "database_errors": len(
                [e for e in all_errors if e.get("source") == "database"]
            ),
            "trace_errors": len(
                [e for e in all_errors if e.get("source") in ["trace", "trace_only"]]
            ),
            "error_types": list(
                {
                    error.get("exception", error.get("exception_type", "Unknown"))
                    for error in all_errors
                }
            ),
            "line_numbers": sorted(
                {
                    error.get("line", error.get("line_number", 0))
                    for error in all_errors
                    if error.get("line", error.get("line_number", 0)) > 0
                }
            ),
            "error_sources": list(
                {error.get("source", "database") for error in all_errors}
            ),
        }

        # Build complete result with comprehensive file info
        result = {
            "file_info": {
                "path": file_path,
                "job_id": int(job_id),
                "project_id": project_id,
                "file_type": _classify_file_type(file_path),
                "error_count": len(all_errors),
                "analysis_mode": mode,
                "includes_trace": include_trace,
            },
            "errors": all_errors,
            "error_statistics": error_statistics,
            "resource_links": resource_links,
            "metadata": {
                "resource_type": "file_with_trace",
                "project_id": project_id,
                "job_id": int(job_id),
                "file_path": file_path,
                "mode": mode,
                "include_trace": include_trace,
                "data_sources": ["database"] + (["trace"] if include_trace else []),
                "cached_at": None,
            },
            "mcp_info": get_mcp_info("file_trace_resource"),
        }

        # Apply mode-specific optimization, but preserve fix guidance for fixing mode
        if mode == "fixing":
            # For fixing mode, don't optimize the errors as we need complete fix guidance
            # Just add the optimization metadata
            result["optimization"] = {
                "response_mode": mode,
                "original_error_count": len(all_errors),
                "optimized_for": "code_fixing_with_sufficient_context",
            }
        elif mode in ["minimal", "balanced", "full"]:
            result = optimize_tool_response(result, mode)

        # Add trace context for debugging modes
        if mode in ["fixing", "full"] and trace_context:
            result["trace_context"] = trace_context[:20]  # Limit context entries

        return result

    # Use cache for the computed data
    return await cache_manager.get_or_compute(
        key=cache_key,
        compute_func=compute_file_trace_data,
        data_type="file_trace",
        project_id=project_id,
        job_id=int(job_id),
    )


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

    @mcp.resource(
        "gl://file/{project_id}/{job_id}/{file_path}?mode={mode}&include_trace={include_trace}"
    )
    async def get_file_resource_with_trace_handler(
        project_id: str, job_id: str, file_path: str, mode: str, include_trace: str
    ) -> str:
        """
        Get file error analysis with trace analysis and different modes.

        Args:
            project_id: GitLab project ID
            job_id: GitLab job ID
            file_path: File path to analyze
            mode: Analysis mode - "minimal", "balanced", "fixing", or "full"
            include_trace: Whether to include trace analysis - "true" or "false"

        Returns:
            File error analysis with trace context and mode-specific detail levels
        """
        try:
            include_trace_bool = include_trace.lower() == "true"
            result = await get_file_resource_with_trace(
                project_id, job_id, file_path, mode, include_trace_bool
            )
            return json.dumps(result, indent=2)

        except Exception as e:
            logger.error(
                f"Error getting file trace resource {project_id}/{job_id}/{file_path}: {e}"
            )
            error_result = {
                "error": f"Failed to get file trace resource: {str(e)}",
                "project_id": project_id,
                "job_id": job_id,
                "file_path": file_path,
                "mode": mode,
                "include_trace": include_trace,
                "resource_uri": f"gl://file/{project_id}/{job_id}/{file_path}?mode={mode}&include_trace={include_trace}",
                "mcp_info": get_mcp_info("file_trace_resource"),
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


def _extract_exception_type_from_message(message: str) -> str | None:
    """Extract exception type from error message"""
    import re

    # Look for common exception patterns
    patterns = [
        r"(\w+Error):",
        r"(\w+Exception):",
        r"^(\w+):",
        r"E\s+(\w+Error)",
        r"E\s+(\w+Exception)",
    ]

    for pattern in patterns:
        match = re.search(pattern, message)
        if match:
            return match.group(1)

    return None
