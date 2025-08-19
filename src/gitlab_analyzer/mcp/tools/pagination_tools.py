"""
Pagination and response limiting tools for handling large pipeline analysis responses

Copyright (c) 2025 Siarhei Skuratovich
Licensed under the MIT License - see LICENSE file for details
"""

from datetime import datetime
from typing import Any

import httpx
from fastmcp import FastMCP

from gitlab_analyzer.parsers.log_parser import LogParser
from gitlab_analyzer.version import get_version

from .pytest_tools import _extract_pytest_errors
from .utils import _is_pytest_log, get_gitlab_analyzer


def _extract_file_path_from_message(message: str) -> str | None:
    """Extract file path from error message - testable helper function"""
    import re

    # Pattern: "path/to/file.py:line_number"
    file_match = re.search(r"([^\s:]+\.py):\d+", message)
    if file_match:
        return file_match.group(1)

    # Pattern: "File 'path/to/file.py'"
    file_match = re.search(r"File ['\"]([^'\"]+\.py)['\"]", message)
    if file_match:
        return file_match.group(1)

    return None


def _process_file_groups(
    file_groups: dict[str, dict], max_files: int, max_errors_per_file: int
) -> list[dict]:
    """Process and limit file groups for response - testable helper function"""
    # Sort files by error count (descending) and limit
    sorted_files = sorted(
        file_groups.values(), key=lambda x: x["error_count"], reverse=True
    )[:max_files]

    # Limit errors per file and convert sets to lists
    for file_group in sorted_files:
        # Limit errors per file
        file_group["errors"] = file_group["errors"][:max_errors_per_file]
        file_group["truncated"] = file_group["error_count"] > max_errors_per_file

        # Convert sets to lists for JSON serialization
        if "jobs_affected" in file_group:
            file_group["jobs_affected"] = list(file_group["jobs_affected"])
        file_group["parser_types"] = list(file_group["parser_types"])
        file_group["error_types"] = list(file_group["error_types"])

    return sorted_files


def _categorize_files_by_type(sorted_files: list[dict]) -> dict[str, dict]:
    """Categorize files by type (test, source, unknown) - testable helper function"""
    test_files = [
        f
        for f in sorted_files
        if any(
            indicator in f["file_path"].lower()
            for indicator in ["test_", "tests/", "_test.", "/test/", "conftest"]
        )
    ]

    source_files = [
        f for f in sorted_files if f not in test_files and f["file_path"] != "unknown"
    ]

    unknown_files = [f for f in sorted_files if f["file_path"] == "unknown"]

    return {
        "test_files": {
            "count": len(test_files),
            "total_errors": sum(f["error_count"] for f in test_files),
            "files": [
                {
                    "file_path": f["file_path"],
                    "error_count": f["error_count"],
                }
                for f in test_files
            ],
        },
        "source_files": {
            "count": len(source_files),
            "total_errors": sum(f["error_count"] for f in source_files),
            "files": [
                {
                    "file_path": f["file_path"],
                    "error_count": f["error_count"],
                }
                for f in source_files
            ],
        },
        "unknown_files": {
            "count": len(unknown_files),
            "total_errors": sum(f["error_count"] for f in unknown_files),
            "files": [
                {
                    "file_path": f["file_path"],
                    "error_count": f["error_count"],
                }
                for f in unknown_files
            ],
        },
    }


def _create_batch_info(
    start_index: int, batch_size: int, batch_errors: list, all_errors: list
) -> dict[str, Any]:
    """Create batch information for error retrieval - testable helper function"""
    end_index = min(start_index + batch_size, len(all_errors))

    return {
        "start_index": start_index,
        "end_index": end_index,
        "batch_size": len(batch_errors),
        "requested_size": batch_size,
        "total_errors": len(all_errors),
        "has_more": end_index < len(all_errors),
        "next_start_index": (end_index if end_index < len(all_errors) else None),
    }


def _extract_error_context_from_generic_entry(entry: Any) -> dict[str, Any]:
    """Extract error context from generic log entry - testable helper function"""
    return {
        "level": entry.level,
        "message": entry.message,
        "line_number": entry.line_number,
        "timestamp": entry.timestamp,
        "context": entry.context,
        "categorization": LogParser.categorize_error(
            entry.message, entry.context or ""
        ),
        "test_file": "unknown",  # Generic parser doesn't extract test file
    }


def _extract_errors_from_trace(trace: str) -> tuple[list[dict], str]:
    """Extract errors from trace and return errors with parser type - testable helper function"""
    if _is_pytest_log(trace):
        pytest_result = _extract_pytest_errors(trace)
        errors = pytest_result.get("errors", [])
        parser_type = "pytest"
    else:
        entries = LogParser.extract_log_entries(trace)
        errors = [
            _extract_error_context_from_generic_entry(entry)
            for entry in entries
            if entry.level == "error"
        ]
        parser_type = "generic"

    return errors, parser_type


def _create_file_statistics_summary(file_errors: list[dict]) -> dict[str, Any]:
    """Create file statistics summary - testable helper function"""
    return {
        "total_errors": len(file_errors),
        "error_types": list(
            {
                error.get(
                    "exception_type",
                    error.get("categorization", {}).get("category", "unknown"),
                )
                for error in file_errors
            }
        ),
        "line_numbers": [
            error.get("line_number")
            for error in file_errors
            if error.get("line_number")
        ],
    }


def _create_error_response_base(
    project_id: str | int, job_id: int | None = None, pipeline_id: int | None = None
) -> dict[str, Any]:
    """Create base error response structure - testable helper function"""
    response: dict[str, Any] = {
        "project_id": str(project_id),
        "analysis_timestamp": datetime.now().isoformat(),
        "mcp_info": {
            "name": "GitLab Pipeline Analyzer",
            "version": get_version(),
        },
    }

    if job_id is not None:
        response["job_id"] = job_id

    if pipeline_id is not None:
        response["pipeline_id"] = pipeline_id

    return response


def _filter_file_specific_errors(all_errors: list[dict], file_path: str) -> list[dict]:
    """Filter errors for a specific file path - testable helper function"""
    file_errors = []
    for error in all_errors:
        error_file = None

        # For pytest errors
        if "test_file" in error and error["test_file"]:
            error_file = error["test_file"]
        # For generic errors, extract from message
        elif "message" in error:
            error_file = _extract_file_path_from_message(error["message"])

        # Check if this error belongs to the requested file
        if error_file == file_path:
            file_errors.append(error)

    return file_errors


def _analyze_job_error_count(
    trace: str, job_id: int, job_name: str, job_status: str
) -> dict[str, Any]:
    """Extract error count and metadata from job trace - testable helper function"""
    try:
        if _is_pytest_log(trace):
            pytest_result = _extract_pytest_errors(trace)
            error_count = len(pytest_result.get("errors", []))
            warning_count = len(pytest_result.get("warnings", []))
            parser_type = "pytest"
        else:
            entries = LogParser.extract_log_entries(trace)
            error_count = len([e for e in entries if e.level == "error"])
            warning_count = len([e for e in entries if e.level == "warning"])
            parser_type = "generic"

        return {
            "job_id": job_id,
            "job_name": job_name,
            "job_status": job_status,
            "error_count": error_count,
            "warning_count": warning_count,
            "parser_type": parser_type,
            "trace_length": len(trace),
        }
    except Exception:
        return {
            "job_id": job_id,
            "job_name": job_name,
            "job_status": job_status,
            "error_count": 0,
            "warning_count": 0,
            "parser_type": "error",
            "trace_length": 0,
        }


def _aggregate_job_statistics(job_summaries: list[dict[str, Any]]) -> dict[str, Any]:
    """Aggregate statistics from job summaries - testable helper function"""
    total_errors = sum(job["error_count"] for job in job_summaries)
    total_warnings = sum(job["warning_count"] for job in job_summaries)

    # Group by parser type
    parser_usage = {}
    for job in job_summaries:
        parser_type = job["parser_type"]
        if parser_type not in parser_usage:
            parser_usage[parser_type] = {"count": 0, "total_errors": 0}
        parser_usage[parser_type]["count"] += 1
        parser_usage[parser_type]["total_errors"] += job["error_count"]

    return {
        "total_errors": total_errors,
        "total_warnings": total_warnings,
        "jobs_with_errors": len([j for j in job_summaries if j["error_count"] > 0]),
        "jobs_with_warnings": len([j for j in job_summaries if j["warning_count"] > 0]),
        "parser_usage": parser_usage,
    }


def _create_pipeline_summary(
    project_id: str | int,
    pipeline_id: int,
    pipeline_status: Any,
    failed_jobs: list[Any],
    job_summaries: list[dict[str, Any]],
) -> dict[str, Any]:
    """Create pipeline summary from components - testable helper function"""
    summary_stats = _aggregate_job_statistics(job_summaries)

    return {
        "project_id": str(project_id),
        "pipeline_id": pipeline_id,
        "pipeline_status": pipeline_status,
        "failed_jobs_count": len(failed_jobs),
        "job_summaries": job_summaries,
        "summary": summary_stats,
        "metadata": {
            "timestamp": datetime.now().isoformat(),
            "analysis_type": "pipeline_summary",
            "version": get_version(),
        },
    }


def _limit_pytest_errors(
    pytest_result: dict[str, Any], max_errors: int, include_traceback: bool
) -> dict[str, Any]:
    """Limit pytest errors and optionally remove traceback data - testable helper function"""
    all_errors = pytest_result.get("errors", [])

    limited_errors = []
    for i, error in enumerate(all_errors):
        if i >= max_errors:
            break

        limited_error = error.copy()
        if not include_traceback:
            # Remove large fields to reduce size
            limited_error.pop("full_error_text", None)
            limited_error.pop("traceback", None)
            limited_error.pop("context", None)
            # Keep only essential fields
            limited_error = {
                "level": limited_error.get("level"),
                "message": limited_error.get("message"),
                "line_number": limited_error.get("line_number"),
                "test_name": limited_error.get("test_name"),
                "test_file": limited_error.get("test_file"),
                "exception_type": limited_error.get("exception_type"),
                "exception_message": limited_error.get("exception_message"),
            }

        limited_errors.append(limited_error)

    return {
        "errors": limited_errors,
        "total_errors": len(all_errors),
        "returned_errors": len(limited_errors),
        "truncated": len(all_errors) > max_errors,
    }


def _limit_generic_errors(entries: list[Any], max_errors: int) -> dict[str, Any]:
    """Limit generic log entries - testable helper function"""
    error_entries = [e for e in entries if e.level == "error"]
    warning_entries = [e for e in entries if e.level == "warning"]

    limited_errors = error_entries[:max_errors]

    # Convert to dict format for consistency
    formatted_errors = []
    for entry in limited_errors:
        formatted_errors.append(
            {
                "level": entry.level,
                "message": entry.message,
                "line_number": entry.line_number,
                "timestamp": entry.timestamp.isoformat() if entry.timestamp else None,
                "context": (
                    entry.context[:200] if entry.context else None
                ),  # Limit context size
            }
        )

    return {
        "errors": formatted_errors,
        "total_errors": len(error_entries),
        "total_warnings": len(warning_entries),
        "returned_errors": len(formatted_errors),
        "truncated": len(error_entries) > max_errors,
    }


def _create_job_analysis_response(
    project_id: str | int,
    job_id: int,
    trace: str,
    error_data: dict[str, Any],
    parser_type: str,
    max_errors: int,
    include_traceback: bool,
) -> dict[str, Any]:
    """Create standardized job analysis response - testable helper function"""
    base_response = {
        "project_id": str(project_id),
        "job_id": job_id,
        "trace_length": len(trace),
        "parser_type": parser_type,
        "response_limits": {
            "max_errors": max_errors,
            "include_traceback": include_traceback,
            "total_available": error_data.get("total_errors", 0),
        },
        "analysis_timestamp": datetime.now().isoformat(),
        "mcp_info": {
            "name": "GitLab Pipeline Analyzer",
            "version": get_version(),
            "tool_used": "analyze_single_job_limited",
            "parser_type": parser_type,
        },
    }

    # Merge error data
    base_response.update(error_data)
    return base_response


def register_pagination_tools(mcp: FastMCP) -> None:
    """Register pagination and response limiting tools"""

    @mcp.tool
    async def analyze_failed_pipeline_summary(
        project_id: str | int, pipeline_id: int
    ) -> dict[str, Any]:
        """
        📊 SUMMARY: Get pipeline failure overview with limited error details to avoid truncation.

        WHEN TO USE:
        - Pipeline has many failed jobs and full analysis is too large
        - Need quick overview before drilling down to specific jobs
        - Want to avoid response truncation issues

        WHAT YOU GET:
        - Pipeline status and basic metadata
        - Failed jobs list with counts only
        - Error summary statistics without full details
        - Parser analysis overview

        Returns:
            Compact pipeline analysis focused on overview rather than details
        """
        try:
            analyzer = get_gitlab_analyzer()

            # Get pipeline status and failed jobs
            import asyncio

            pipeline_status, failed_jobs = await asyncio.gather(
                analyzer.get_pipeline(project_id, pipeline_id),
                analyzer.get_failed_pipeline_jobs(project_id, pipeline_id),
            )

            # Get error counts per job without full details
            async def get_job_error_count(job: Any) -> dict[str, Any]:
                try:
                    trace = await analyzer.get_job_trace(project_id, job.id)
                    return _analyze_job_error_count(trace, job.id, job.name, job.status)
                except Exception:
                    return _analyze_job_error_count("", job.id, job.name, job.status)

            # Process jobs with concurrency limit
            semaphore = asyncio.Semaphore(5)

            async def analyze_with_semaphore(job: Any) -> dict[str, Any]:
                async with semaphore:
                    return await get_job_error_count(job)

            job_summaries = await asyncio.gather(
                *[analyze_with_semaphore(job) for job in failed_jobs]
            )

            return _create_pipeline_summary(
                project_id, pipeline_id, pipeline_status, failed_jobs, job_summaries
            )

        except (httpx.HTTPError, httpx.RequestError, ValueError, KeyError) as e:
            return {
                "error": f"Failed to analyze pipeline summary: {str(e)}",
                "project_id": str(project_id),
                "pipeline_id": pipeline_id,
                "mcp_info": {
                    "name": "GitLab Pipeline Analyzer",
                    "version": get_version(),
                    "tool_used": "analyze_failed_pipeline_summary",
                },
            }

    @mcp.tool
    async def analyze_single_job_limited(
        project_id: str | int,
        job_id: int,
        max_errors: int = 5,
        include_traceback: bool = False,
    ) -> dict[str, Any]:
        """
        🎯 LIMITED: Analyze single job with response size controls to prevent truncation.

        WHEN TO USE:
        - Job has many errors and full analysis would be truncated
        - Need quick error overview without overwhelming detail
        - Want to control response size

        WHAT YOU GET:
        - Job metadata (name, status, stage, duration)
        - Limited number of errors (configurable)
        - Optional traceback inclusion
        - Error summary statistics

        Args:
            project_id: The GitLab project ID or path
            job_id: The ID of the specific job to analyze
            max_errors: Maximum number of errors to return (default: 5)
            include_traceback: Whether to include full tracebacks (default: False)

        Returns:
            Limited analysis of the single job to prevent response truncation
        """
        try:
            analyzer = get_gitlab_analyzer()
            trace = await analyzer.get_job_trace(project_id, job_id)

            if _is_pytest_log(trace):
                pytest_result = _extract_pytest_errors(trace)
                error_data = _limit_pytest_errors(
                    pytest_result, max_errors, include_traceback
                )
                return _create_job_analysis_response(
                    project_id,
                    job_id,
                    trace,
                    error_data,
                    "pytest",
                    max_errors,
                    include_traceback,
                )
            else:
                # Use generic log parser with limits
                entries = LogParser.extract_log_entries(trace)
                error_data = _limit_generic_errors(entries, max_errors)
                return _create_job_analysis_response(
                    project_id,
                    job_id,
                    trace,
                    error_data,
                    "generic",
                    max_errors,
                    include_traceback,
                )

        except (httpx.HTTPError, httpx.RequestError, ValueError, KeyError) as e:
            return {
                "error": f"Failed to analyze job (limited): {str(e)}",
                "project_id": str(project_id),
                "job_id": job_id,
                "mcp_info": {
                    "name": "GitLab Pipeline Analyzer",
                    "version": get_version(),
                    "tool_used": "analyze_single_job_limited",
                },
            }

    @mcp.tool
    async def get_error_batch(
        project_id: str | int, job_id: int, start_index: int = 0, batch_size: int = 3
    ) -> dict[str, Any]:
        """
        📦 BATCH: Get a specific batch of errors from a job to handle large error lists.

        WHEN TO USE:
        - Job has many errors and you need to process them in batches
        - Want to get specific errors by index range
        - Need to paginate through large error lists

        WHAT YOU GET:
        - Specific batch of errors with full details
        - Batch metadata (start, size, total)
        - Complete error context for the requested range

        Args:
            project_id: The GitLab project ID or path
            job_id: The ID of the specific job to analyze
            start_index: Starting index for the batch (0-based)
            batch_size: Number of errors to return in this batch

        Returns:
            Batch of errors with pagination information
        """
        try:
            analyzer = get_gitlab_analyzer()
            trace = await analyzer.get_job_trace(project_id, job_id)

            if _is_pytest_log(trace):
                pytest_result = _extract_pytest_errors(trace)
                all_errors = pytest_result.get("errors", [])
            else:
                all_errors, _ = _extract_errors_from_trace(trace)

            # Extract the requested batch
            end_index = min(start_index + batch_size, len(all_errors))
            batch_errors = all_errors[start_index:end_index]

            return {
                "project_id": str(project_id),
                "job_id": job_id,
                "errors": batch_errors,
                "batch_info": _create_batch_info(
                    start_index, batch_size, batch_errors, all_errors
                ),
                "parser_type": "pytest" if _is_pytest_log(trace) else "generic",
                "analysis_timestamp": datetime.now().isoformat(),
                "mcp_info": {
                    "name": "GitLab Pipeline Analyzer",
                    "version": get_version(),
                    "tool_used": "get_error_batch",
                },
            }

        except (httpx.HTTPError, httpx.RequestError, ValueError, KeyError) as e:
            return {
                "error": f"Failed to get error batch: {str(e)}",
                "project_id": str(project_id),
                "job_id": job_id,
                "mcp_info": {
                    "name": "GitLab Pipeline Analyzer",
                    "version": get_version(),
                    "tool_used": "get_error_batch",
                },
            }

    @mcp.tool
    async def group_errors_by_file(
        project_id: str | int,
        pipeline_id: int | None = None,
        job_id: int | None = None,
        max_files: int = 10,
        max_errors_per_file: int = 5,
    ) -> dict[str, Any]:
        """
        📁 GROUP: Group errors by file path for systematic fixing approach.

        WHEN TO USE:
        - Pipeline has errors across multiple files
        - Want to fix all errors in a file at once
        - Need to prioritize files with most errors
        - Want to avoid processing same file multiple times

        WHAT YOU GET:
        - Errors grouped by file path
        - File-level error statistics
        - Priority ordering by error count
        - Limited errors per file to prevent truncation

        Args:
            project_id: The GitLab project ID or path
            pipeline_id: The ID of the GitLab pipeline to analyze (required if job_id not provided)
            job_id: The ID of a specific job to analyze (optional, overrides pipeline_id)
            max_files: Maximum number of files to return (default: 10)
            max_errors_per_file: Maximum errors per file (default: 5)

        Returns:
            Errors grouped by file with file-level statistics and priority ordering
        """
        try:
            analyzer = get_gitlab_analyzer()

            # Initialize variables that will be assigned in conditional blocks
            processing_mode: str
            scope_info: dict[str, Any]
            all_errors: list[dict[str, Any]]

            if job_id is not None:
                # Single job mode
                trace = await analyzer.get_job_trace(project_id, job_id)

                # Extract errors from the job trace
                if _is_pytest_log(trace):
                    pytest_result = _extract_pytest_errors(trace)
                    all_errors = pytest_result.get("errors", [])
                    parser_type = "pytest"
                else:
                    entries = LogParser.extract_log_entries(trace)
                    all_errors = [
                        _extract_error_context_from_generic_entry(entry)
                        for entry in entries
                        if entry.level == "error"
                    ]
                    parser_type = "generic"

                # Add job context to each error
                for error in all_errors:
                    error["job_id"] = job_id
                    error["parser_type"] = parser_type

                processing_mode = "grouped_by_file_for_job"
                scope_info = {"job_id": job_id}

            elif pipeline_id is not None:
                # Pipeline mode
                import asyncio

                pipeline_status, failed_jobs = await asyncio.gather(
                    analyzer.get_pipeline(project_id, pipeline_id),
                    analyzer.get_failed_pipeline_jobs(project_id, pipeline_id),
                )

                # Collect all errors from all jobs
                async def collect_job_errors(job: Any) -> list[dict[str, Any]]:
                    try:
                        trace = await analyzer.get_job_trace(project_id, job.id)

                        if _is_pytest_log(trace):
                            pytest_result = _extract_pytest_errors(trace)
                            errors = pytest_result.get("errors", [])
                            parser_type = "pytest"
                        else:
                            entries = LogParser.extract_log_entries(trace)
                            errors = [
                                _extract_error_context_from_generic_entry(entry)
                                for entry in entries
                                if entry.level == "error"
                            ]
                            parser_type = "generic"

                        # Add job context to each error
                        for error in errors:
                            error["job_id"] = job.id
                            error["job_name"] = job.name
                            error["parser_type"] = parser_type

                        return errors

                    except Exception:
                        return []

                # Process jobs with concurrency limit
                semaphore = asyncio.Semaphore(5)

                async def collect_with_semaphore(job: Any) -> list[dict[str, Any]]:
                    async with semaphore:
                        return await collect_job_errors(job)

                job_error_lists = await asyncio.gather(
                    *[collect_with_semaphore(job) for job in failed_jobs]
                )

                # Flatten all errors
                all_errors = []
                for error_list in job_error_lists:
                    all_errors.extend(error_list)

                processing_mode = "grouped_by_file_for_pipeline"
                scope_info = {
                    "pipeline_id": pipeline_id,
                    "pipeline_status": pipeline_status,
                }

            else:
                raise ValueError("Either pipeline_id or job_id must be provided")

            # Group errors by file path
            file_groups: dict[str, dict[str, Any]] = {}
            for error in all_errors:
                # Extract file path from different sources
                file_path = None

                # For pytest errors, use test_file
                if (
                    "test_file" in error
                    and error["test_file"]
                    and error["test_file"] != "unknown"
                ):
                    file_path = error["test_file"]
                # For generic errors, try to extract from message
                elif "message" in error:
                    file_path = _extract_file_path_from_message(error["message"])

                # Fallback to "unknown" if no file path found
                if not file_path:
                    file_path = "unknown"

                if file_path not in file_groups:
                    file_groups[file_path] = {
                        "file_path": file_path,
                        "errors": [],
                        "error_count": 0,
                        "parser_types": set(),
                        "error_types": set(),
                    }
                    # Only add jobs_affected for pipeline mode
                    if pipeline_id is not None:
                        file_groups[file_path]["jobs_affected"] = set()

                file_groups[file_path]["errors"].append(error)
                file_groups[file_path]["error_count"] += 1
                file_groups[file_path]["parser_types"].add(
                    error.get("parser_type", "unknown")
                )

                # Add job info for pipeline mode
                if pipeline_id is not None:
                    file_groups[file_path]["jobs_affected"].add(
                        error.get("job_name", "unknown")
                    )

                # Extract error type
                if "exception_type" in error:
                    file_groups[file_path]["error_types"].add(error["exception_type"])
                elif (
                    "categorization" in error and "category" in error["categorization"]
                ):
                    file_groups[file_path]["error_types"].add(
                        error["categorization"]["category"]
                    )

            # Sort files by error count (descending) and limit
            sorted_files = _process_file_groups(
                file_groups, max_files, max_errors_per_file
            )

            # Calculate summary statistics
            total_files_with_errors = len(file_groups)
            total_errors = sum(group["error_count"] for group in file_groups.values())

            # Categorize files by fixability
            categorization = _categorize_files_by_type(sorted_files)

            # Build response
            response = {
                "project_id": str(project_id),
                "file_groups": sorted_files,
                "summary": {
                    "total_files_with_errors": total_files_with_errors,
                    "files_returned": len(sorted_files),
                    "total_errors": total_errors,
                    "files_truncated": total_files_with_errors > max_files,
                },
                "categorization": categorization,
                "processing_limits": {
                    "max_files": max_files,
                    "max_errors_per_file": max_errors_per_file,
                    "total_files_available": total_files_with_errors,
                },
                "analysis_timestamp": datetime.now().isoformat(),
                "processing_mode": processing_mode,
                "mcp_info": {
                    "name": "GitLab Pipeline Analyzer",
                    "version": get_version(),
                    "tool_used": "group_errors_by_file",
                },
            }

            # Add scope-specific information
            response.update(scope_info)

            return response

        except (httpx.HTTPError, httpx.RequestError, ValueError, KeyError) as e:
            error_response: dict[str, Any] = {
                "error": f"Failed to group errors by file: {str(e)}",
                "project_id": str(project_id),
                "mcp_info": {
                    "name": "GitLab Pipeline Analyzer",
                    "version": get_version(),
                    "tool_used": "group_errors_by_file",
                },
            }

            if job_id is not None:
                error_response["job_id"] = job_id
            if pipeline_id is not None:
                error_response["pipeline_id"] = pipeline_id

            return error_response

    @mcp.tool
    async def get_files_with_errors(
        project_id: str | int,
        pipeline_id: int | None = None,
        job_id: int | None = None,
        max_files: int = 20,
    ) -> dict[str, Any]:
        """
        📋 FILE LIST: Get list of files that have errors without the error details.

        WHEN TO USE:
        - Need quick overview of which files have errors
        - Want to see file error counts without full error details
        - Planning which files to process for fixing
        - Getting file list for iteration or selection

        WHAT YOU GET:
        - List of files with error counts
        - File type categorization (test, source, unknown)
        - Summary statistics
        - No actual error details (lightweight response)

        Args:
            project_id: The GitLab project ID or path
            pipeline_id: The ID of the GitLab pipeline to analyze (required if job_id not provided)
            job_id: The ID of a specific job to analyze (optional, overrides pipeline_id)
            max_files: Maximum number of files to return (default: 20)

        Returns:
            List of files with error counts but no error details
        """
        try:
            analyzer = get_gitlab_analyzer()

            # Initialize variables that will be assigned in conditional blocks
            processing_mode: str
            scope_info: dict[str, Any]
            all_errors: list[dict[str, Any]]

            if job_id is not None:
                # Single job mode
                trace = await analyzer.get_job_trace(project_id, job_id)

                # Extract errors from the job trace
                if _is_pytest_log(trace):
                    pytest_result = _extract_pytest_errors(trace)
                    all_errors = pytest_result.get("errors", [])
                    parser_type = "pytest"
                else:
                    entries = LogParser.extract_log_entries(trace)
                    all_errors = [
                        _extract_error_context_from_generic_entry(entry)
                        for entry in entries
                        if entry.level == "error"
                    ]
                    parser_type = "generic"

                processing_mode = "files_list_for_job"
                scope_info = {"job_id": job_id}

            elif pipeline_id is not None:
                # Pipeline mode
                import asyncio

                pipeline_status, failed_jobs = await asyncio.gather(
                    analyzer.get_pipeline(project_id, pipeline_id),
                    analyzer.get_failed_pipeline_jobs(project_id, pipeline_id),
                )

                # Collect all errors from all jobs
                async def collect_job_errors(job: Any) -> list[dict[str, Any]]:
                    try:
                        trace = await analyzer.get_job_trace(project_id, job.id)

                        if _is_pytest_log(trace):
                            pytest_result = _extract_pytest_errors(trace)
                            errors = pytest_result.get("errors", [])
                            parser_type = "pytest"
                        else:
                            entries = LogParser.extract_log_entries(trace)
                            errors = [
                                _extract_error_context_from_generic_entry(entry)
                                for entry in entries
                                if entry.level == "error"
                            ]
                            parser_type = "generic"

                        # Add job context to each error
                        for error in errors:
                            error["job_id"] = job.id
                            error["job_name"] = job.name
                            error["parser_type"] = parser_type

                        return errors

                    except Exception:
                        return []

                # Process jobs with concurrency limit
                semaphore = asyncio.Semaphore(5)

                async def collect_with_semaphore(job: Any) -> list[dict[str, Any]]:
                    async with semaphore:
                        return await collect_job_errors(job)

                job_error_lists = await asyncio.gather(
                    *[collect_with_semaphore(job) for job in failed_jobs]
                )

                # Flatten all errors
                all_errors = []
                for error_list in job_error_lists:
                    all_errors.extend(error_list)

                parser_type = "mixed"  # Could be from multiple parsers
                processing_mode = "files_list_for_pipeline"
                scope_info = {
                    "pipeline_id": pipeline_id,
                    "pipeline_status": pipeline_status,
                }

            else:
                raise ValueError("Either pipeline_id or job_id must be provided")

            # Group errors by file path (without storing actual errors)
            file_counts: dict[str, dict[str, Any]] = {}
            for error in all_errors:
                # Extract file path from different sources
                file_path = None

                # For pytest errors, use test_file
                if (
                    "test_file" in error
                    and error["test_file"]
                    and error["test_file"] != "unknown"
                ):
                    file_path = error["test_file"]
                # For generic errors, try to extract from message
                elif "message" in error:
                    file_path = _extract_file_path_from_message(error["message"])

                # Fallback to "unknown" if no file path found
                if not file_path:
                    file_path = "unknown"

                if file_path not in file_counts:
                    file_counts[file_path] = {
                        "file_path": file_path,
                        "error_count": 0,
                        "error_types": set(),
                    }
                    # Add jobs_affected for pipeline mode
                    if pipeline_id is not None:
                        file_counts[file_path]["jobs_affected"] = set()

                file_counts[file_path]["error_count"] += 1

                # Add job info for pipeline mode
                if pipeline_id is not None:
                    file_counts[file_path]["jobs_affected"].add(
                        error.get("job_name", "unknown")
                    )

                # Extract error type for categorization
                if "exception_type" in error:
                    file_counts[file_path]["error_types"].add(error["exception_type"])
                elif (
                    "categorization" in error and "category" in error["categorization"]
                ):
                    file_counts[file_path]["error_types"].add(
                        error["categorization"]["category"]
                    )

            # Sort files by error count (descending) and limit
            sorted_files = sorted(
                file_counts.values(), key=lambda x: x["error_count"], reverse=True
            )[:max_files]

            # Convert sets to lists for JSON serialization
            for file_info in sorted_files:
                file_info["error_types"] = list(file_info["error_types"])
                if "jobs_affected" in file_info:
                    file_info["jobs_affected"] = list(file_info["jobs_affected"])

            # Calculate summary statistics
            total_files_with_errors = len(file_counts)
            total_errors = sum(info["error_count"] for info in file_counts.values())

            # Categorize files by type
            test_files = [
                f
                for f in sorted_files
                if any(
                    indicator in f["file_path"].lower()
                    for indicator in ["test_", "tests/", "_test.", "/test/", "conftest"]
                )
            ]

            source_files = [
                f
                for f in sorted_files
                if f not in test_files and f["file_path"] != "unknown"
            ]

            unknown_files = [f for f in sorted_files if f["file_path"] == "unknown"]

            categorization = {
                "test_files": {
                    "count": len(test_files),
                    "total_errors": sum(f["error_count"] for f in test_files),
                    "files": [
                        {
                            "file_path": f["file_path"],
                            "error_count": f["error_count"],
                            "error_types": f["error_types"],
                            **(
                                {"jobs_affected": f["jobs_affected"]}
                                if "jobs_affected" in f
                                else {}
                            ),
                        }
                        for f in test_files
                    ],
                },
                "source_files": {
                    "count": len(source_files),
                    "total_errors": sum(f["error_count"] for f in source_files),
                    "files": [
                        {
                            "file_path": f["file_path"],
                            "error_count": f["error_count"],
                            "error_types": f["error_types"],
                            **(
                                {"jobs_affected": f["jobs_affected"]}
                                if "jobs_affected" in f
                                else {}
                            ),
                        }
                        for f in source_files
                    ],
                },
                "unknown_files": {
                    "count": len(unknown_files),
                    "total_errors": sum(f["error_count"] for f in unknown_files),
                    "files": [
                        {
                            "file_path": f["file_path"],
                            "error_count": f["error_count"],
                            "error_types": f["error_types"],
                            **(
                                {"jobs_affected": f["jobs_affected"]}
                                if "jobs_affected" in f
                                else {}
                            ),
                        }
                        for f in unknown_files
                    ],
                },
            }

            # Build response
            response = {
                "project_id": str(project_id),
                "files_with_errors": sorted_files,
                "summary": {
                    "total_files_with_errors": total_files_with_errors,
                    "files_returned": len(sorted_files),
                    "total_errors": total_errors,
                    "files_truncated": total_files_with_errors > max_files,
                },
                "categorization": categorization,
                "processing_limits": {
                    "max_files": max_files,
                    "total_files_available": total_files_with_errors,
                },
                "parser_type": parser_type,
                "analysis_timestamp": datetime.now().isoformat(),
                "processing_mode": processing_mode,
                "mcp_info": {
                    "name": "GitLab Pipeline Analyzer",
                    "version": get_version(),
                    "tool_used": "get_files_with_errors",
                },
            }

            # Add scope-specific information
            response.update(scope_info)

            return response

        except (httpx.HTTPError, httpx.RequestError, ValueError, KeyError) as e:
            error_response: dict[str, Any] = {
                "error": f"Failed to get files with errors: {str(e)}",
                "project_id": str(project_id),
                "mcp_info": {
                    "name": "GitLab Pipeline Analyzer",
                    "version": get_version(),
                    "tool_used": "get_files_with_errors",
                },
            }

            if job_id is not None:
                error_response["job_id"] = job_id
            if pipeline_id is not None:
                error_response["pipeline_id"] = pipeline_id

            return error_response

    @mcp.tool
    async def get_file_errors(
        project_id: str | int, job_id: int, file_path: str, max_errors: int = 10
    ) -> dict[str, Any]:
        """
        📄 FILE FOCUS: Get all errors for a specific file from a job.

        WHEN TO USE:
        - Want to see all errors in a specific file
        - Processing files one by one systematically
        - Need complete error context for a file

        WHAT YOU GET:
        - All errors for the specified file
        - File-specific error statistics
        - Complete error context and details

        Args:
            project_id: The GitLab project ID or path
            job_id: The ID of the specific job to analyze
            file_path: The specific file path to get errors for
            max_errors: Maximum number of errors to return

        Returns:
            All errors for the specified file with complete context
        """
        try:
            analyzer = get_gitlab_analyzer()
            trace = await analyzer.get_job_trace(project_id, job_id)

            if _is_pytest_log(trace):
                pytest_result = _extract_pytest_errors(trace)
                all_errors = pytest_result.get("errors", [])
                parser_type = "pytest"
            else:
                entries = LogParser.extract_log_entries(trace)
                all_errors = [
                    _extract_error_context_from_generic_entry(entry)
                    for entry in entries
                    if entry.level == "error"
                ]
                parser_type = "generic"

            # Filter errors for the specific file
            file_errors = _filter_file_specific_errors(all_errors, file_path)

            # Limit the number of errors returned
            limited_errors = file_errors[:max_errors]

            return {
                "project_id": str(project_id),
                "job_id": job_id,
                "file_path": file_path,
                "errors": limited_errors,
                "file_statistics": {
                    "returned_errors": len(limited_errors),
                    "truncated": len(file_errors) > max_errors,
                    **_create_file_statistics_summary(file_errors),
                },
                "parser_type": parser_type,
                "analysis_timestamp": datetime.now().isoformat(),
                "mcp_info": {
                    "name": "GitLab Pipeline Analyzer",
                    "version": get_version(),
                    "tool_used": "get_file_errors",
                },
            }

        except (httpx.HTTPError, httpx.RequestError, ValueError, KeyError) as e:
            return {
                "error": f"Failed to get file errors: {str(e)}",
                "project_id": str(project_id),
                "job_id": job_id,
                "file_path": file_path,
                "mcp_info": {
                    "name": "GitLab Pipeline Analyzer",
                    "version": get_version(),
                    "tool_used": "get_file_errors",
                },
            }
