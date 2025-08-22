"""
Pytest-specific MCP tools for GitLab Pipeline Analyzer.

Copyright (c) 2025 Siarhei Skuratovich
Licensed under the MIT License - see LICENSE file for details
"""

from typing import Any

import httpx
from fastmcp import FastMCP

from gitlab_analyzer.parsers.pytest_parser import PytestLogParser

from .utils import DEFAULT_EXCLUDE_PATHS, get_gitlab_analyzer, get_mcp_info


async def _extract_pytest_detailed_failures_impl(
    project_id: int | str,
    job_id: int,
    include_traceback: bool = True,
    exclude_paths: list[str] | None = None,
) -> dict[str, Any]:
    """Implementation for extract_pytest_detailed_failures."""
    analyzer = get_gitlab_analyzer()
    trace = await analyzer.get_job_trace(project_id, job_id)

    # Use the specialized PytestLogParser for detailed analysis
    pytest_result = PytestLogParser.parse_pytest_log(trace)

    if pytest_result.detailed_failures:
        # Convert to expected format with traceback filtering support
        detailed_failures = []
        for failure in pytest_result.detailed_failures:
            # Convert traceback to dict format for filtering
            traceback_dicts = []
            if failure.traceback:
                traceback_dicts = [
                    {
                        "file_path": tb.file_path,
                        "line_number": tb.line_number,
                        "function_name": tb.function_name,
                        "code_line": tb.code_line,
                        "error_type": tb.error_type,
                        "error_message": tb.error_message,
                    }
                    for tb in failure.traceback
                ]

            failure_dict = {
                "test_name": failure.test_name,
                "test_file": failure.test_file,
                "test_function": failure.test_function,
                "test_parameters": failure.test_parameters,
                "platform_info": failure.platform_info,
                "exception_type": failure.exception_type,
                "exception_message": failure.exception_message,
                "traceback": traceback_dicts,
                "full_error_text": failure.full_error_text,
            }

            # Apply traceback filtering
            cleaned_failure = _clean_pytest_error_response(
                failure_dict, include_traceback, exclude_paths
            )
            detailed_failures.append(cleaned_failure)

        return {
            "project_id": str(project_id),
            "job_id": job_id,
            "detailed_failures": detailed_failures,
            "parser_type": "pytest",
            "failure_count": len(detailed_failures),
            "platform_info": "Extracted from pytest output",
            "traceback_included": include_traceback,
            "traceback_filtered": exclude_paths is not None and len(exclude_paths) > 0,
            "mcp_info": get_mcp_info("extract_pytest_detailed_failures"),
        }
    else:
        return {
            "project_id": str(project_id),
            "job_id": job_id,
            "detailed_failures": [],
            "parser_type": "not_pytest",
            "failure_count": 0,
            "message": "No pytest failures detected in job trace",
            "mcp_info": get_mcp_info("extract_pytest_detailed_failures"),
        }


async def _extract_pytest_short_summary_impl(
    project_id: int | str, job_id: int
) -> dict[str, Any]:
    """Implementation for extract_pytest_short_summary."""
    analyzer = get_gitlab_analyzer()
    trace = await analyzer.get_job_trace(project_id, job_id)

    # Use the specialized PytestLogParser for short summary
    pytest_result = PytestLogParser.parse_pytest_log(trace)

    if pytest_result.short_summary:
        # Convert to expected format
        summary = []
        for item in pytest_result.short_summary:
            summary.append(
                {
                    "test_name": item.test_name,
                    "exception_type": item.error_type,
                    "brief_message": item.error_message[:100],  # Truncate for brevity
                    "test_file": item.test_file,
                    "test_function": item.test_function,
                    "test_parameters": item.test_parameters,
                }
            )

        return {
            "project_id": str(project_id),
            "job_id": job_id,
            "failed_tests": summary,
            "failure_count": len(summary),
            "parser_type": "pytest",
            "mcp_info": get_mcp_info("extract_pytest_short_summary"),
        }
    else:
        return {
            "project_id": str(project_id),
            "job_id": job_id,
            "failed_tests": [],
            "failure_count": 0,
            "parser_type": "not_pytest",
            "message": "No pytest failures detected in job trace",
            "mcp_info": get_mcp_info("extract_pytest_short_summary"),
        }


async def _extract_pytest_statistics_impl(
    project_id: int | str, job_id: int
) -> dict[str, Any]:
    """Implementation for extract_pytest_statistics."""
    analyzer = get_gitlab_analyzer()
    trace = await analyzer.get_job_trace(project_id, job_id)

    # Use the specialized PytestLogParser for statistics
    pytest_result = PytestLogParser.parse_pytest_log(trace)

    # Extract statistics from the parser result
    stats = pytest_result.statistics

    return {
        "project_id": str(project_id),
        "job_id": job_id,
        "statistics": {
            "total_tests": stats.total_tests,
            "passed_tests": stats.passed,
            "failed_tests": stats.failed,
            "skipped_tests": stats.skipped,
            "errors": stats.errors,
            "warnings": stats.warnings,
            "pass_rate": round(
                (
                    (stats.passed / stats.total_tests * 100)
                    if stats.total_tests > 0
                    else 0
                ),
                2,
            ),
            "failure_rate": round(
                (
                    (stats.failed / stats.total_tests * 100)
                    if stats.total_tests > 0
                    else 0
                ),
                2,
            ),
            "duration_seconds": stats.duration_seconds,
            "duration_formatted": stats.duration_formatted,
        },
        "parser_type": (
            "pytest"
            if pytest_result.has_failures_section
            or pytest_result.has_short_summary_section
            else "not_pytest"
        ),
        "mcp_info": get_mcp_info("extract_pytest_statistics"),
    }


def _filter_traceback_by_paths(
    traceback_entries: list[dict], exclude_paths: list[str]
) -> list[dict]:
    """Filter traceback entries by excluding specified path patterns"""
    if not exclude_paths:
        return traceback_entries

    filtered_traceback = []
    for entry in traceback_entries:
        file_path = entry.get("file_path", "")

        # Check if this file path should be excluded
        should_exclude = False
        for exclude_pattern in exclude_paths:
            if exclude_pattern in file_path:
                should_exclude = True
                break

        if not should_exclude:
            filtered_traceback.append(entry)

    return filtered_traceback


def _clean_pytest_error_response(
    error: dict[str, Any],
    include_traceback: bool = True,
    exclude_paths: list[str] | None = None,
) -> dict[str, Any]:
    """Clean pytest error response based on traceback and path filtering preferences"""
    if exclude_paths is None:
        exclude_paths = DEFAULT_EXCLUDE_PATHS

    cleaned_error = error.copy()

    # Handle traceback inclusion/exclusion
    if not include_traceback:
        # Remove traceback-related fields completely
        cleaned_error.pop("traceback", None)
        cleaned_error.pop("full_error_text", None)
        cleaned_error["has_traceback"] = False
    else:
        # Include traceback, apply filtering if exclude_paths has items
        if exclude_paths and "traceback" in cleaned_error:
            # Filter traceback by paths if traceback is included
            cleaned_error["traceback"] = _filter_traceback_by_paths(
                cleaned_error["traceback"], exclude_paths
            )

        # Filter full_error_text to remove excluded paths only if exclude_paths has items
        if exclude_paths and "full_error_text" in cleaned_error:
            full_error_lines = cleaned_error["full_error_text"].split("\n")
            filtered_lines = []

            for line in full_error_lines:
                should_exclude = False
                for exclude_pattern in exclude_paths:
                    if exclude_pattern in line:
                        should_exclude = True
                        break

                if not should_exclude:
                    filtered_lines.append(line)

            cleaned_error["full_error_text"] = "\n".join(filtered_lines)

        cleaned_error["has_traceback"] = True

    return cleaned_error


def register_pytest_tools(mcp: FastMCP) -> None:
    """Register pytest-specific MCP tools."""

    @mcp.tool
    async def extract_pytest_detailed_failures(
        project_id: int | str,
        job_id: int,
        include_traceback: bool = True,
        exclude_paths: list[str] | None = None,
    ) -> dict[str, Any]:
        """
        🧪 PYTEST DEEP DIVE: Extract comprehensive pytest failure information with full tracebacks.

        WHEN TO USE:
        - Job name contains "test", "pytest", or shows test-related failures
        - Need comprehensive test failure analysis
        - User asks "what tests failed and why?"

        WHAT YOU GET:
        - Detailed failures: Full tracebacks, exception details, file/line info
        - Exception types, messages, and platform information
        - File paths, line numbers, and code context
        - Test parameters and function details

        Args:
            project_id: The GitLab project ID or path
            job_id: The ID of the job containing pytest results
            include_traceback: Whether to include traceback information (default: True)
            exclude_paths: List of path patterns to exclude from traceback.
                          If None, uses DEFAULT_EXCLUDE_PATHS for common system/dependency paths.
                          Use [] to disable all filtering and get complete traceback.

        Returns:
            Detailed analysis of pytest failures including full tracebacks and exception details
        """
        try:
            return await _extract_pytest_detailed_failures_impl(
                project_id, job_id, include_traceback, exclude_paths
            )
        except (httpx.HTTPError, httpx.RequestError, ValueError, KeyError) as e:
            return {
                "error": f"Failed to extract pytest detailed failures: {str(e)}",
                "project_id": str(project_id),
                "job_id": job_id,
                "mcp_info": get_mcp_info(
                    "extract_pytest_detailed_failures", error=True
                ),
            }

    @mcp.tool
    async def extract_pytest_short_summary(
        project_id: int | str, job_id: int
    ) -> dict[str, Any]:
        """
        📋 QUICK OVERVIEW: Get concise test failure summary for rapid assessment.

        WHEN TO USE:
        - Need quick overview of test failures without full detail
        - Want to see failing test names and basic error messages
        - Performing initial triage of test failures

        WHAT YOU GET:
        - List of failed tests with names and brief error messages
        - Test file locations and function names
        - Exception types without full tracebacks
        - Concise failure count and summary

        Args:
            project_id: The GitLab project ID or path
            job_id: The ID of the job containing pytest results

        Returns:
            Short summary of pytest failures with test names and brief error messages
        """
        try:
            return await _extract_pytest_short_summary_impl(project_id, job_id)
        except (httpx.HTTPError, httpx.RequestError, ValueError, KeyError) as e:
            return {
                "error": f"Failed to extract pytest short summary: {str(e)}",
                "project_id": str(project_id),
                "job_id": job_id,
                "mcp_info": get_mcp_info("extract_pytest_short_summary", error=True),
            }

    @mcp.tool
    async def extract_pytest_statistics(
        project_id: int | str, job_id: int
    ) -> dict[str, Any]:
        """
        📊 METRICS: Get test execution statistics and performance data.

        WHEN TO USE:
        - Need test suite performance metrics (pass rate, duration)
        - Want to understand test coverage and execution efficiency
        - Analyzing test suite health and trends

        WHAT YOU GET:
        - Test counts (total, passed, failed, skipped, errors)
        - Execution duration and timing information
        - Pass rate and failure rate calculations
        - Performance metrics for test suite analysis

        Args:
            project_id: The GitLab project ID or path
            job_id: The ID of the job containing pytest results

        Returns:
            Complete pytest run statistics including test counts and timing information
        """
        try:
            return await _extract_pytest_statistics_impl(project_id, job_id)
        except (httpx.HTTPError, httpx.RequestError, ValueError, KeyError) as e:
            return {
                "error": f"Failed to extract pytest statistics: {str(e)}",
                "project_id": str(project_id),
                "job_id": job_id,
                "mcp_info": get_mcp_info("extract_pytest_statistics", error=True),
            }

    @mcp.tool
    async def analyze_pytest_job_complete(
        project_id: int | str,
        job_id: int,
        include_traceback: bool = True,
        exclude_paths: list[str] | None = None,
    ) -> dict[str, Any]:
        """
        🎯 COMPLETE: Complete pytest analysis combining detailed failures, summary, and statistics.

        WHEN TO USE:
        - Job name contains "test", "pytest", or shows test-related failures
        - Need comprehensive test failure analysis in one call
        - User asks "what tests failed and why?"

        WHAT YOU GET:
        - Detailed failures: Full tracebacks, exception details, file/line info
        - Short summary: Concise failure list with test names and brief errors
        - Statistics: Test counts (total, passed, failed, skipped) and timing

        Args:
            project_id: The GitLab project ID or path
            job_id: The ID of the job containing pytest results
            include_traceback: Whether to include traceback information (default: True)
            exclude_paths: List of path patterns to exclude from traceback.
                          If None, uses DEFAULT_EXCLUDE_PATHS for common system/dependency paths.
                          Use [] to disable all filtering and get complete traceback.

        Returns:
            Complete pytest analysis with detailed failures, summary, and statistics
        """
        try:
            # Get all three analyses using the implementation functions
            detailed = await _extract_pytest_detailed_failures_impl(
                project_id, job_id, include_traceback, exclude_paths
            )
            summary = await _extract_pytest_short_summary_impl(project_id, job_id)
            stats = await _extract_pytest_statistics_impl(project_id, job_id)

            # Combine results
            return {
                "project_id": str(project_id),
                "job_id": job_id,
                "detailed_failures": detailed.get("detailed_failures", []),
                "failure_summary": summary.get("failed_tests", []),
                "statistics": stats.get("statistics", {}),
                "parser_type": detailed.get("parser_type", "unknown"),
                "analysis_complete": True,
                "tools_used": [
                    "extract_pytest_detailed_failures",
                    "extract_pytest_short_summary",
                    "extract_pytest_statistics",
                ],
                "mcp_info": get_mcp_info("analyze_pytest_job_complete"),
            }

        except (httpx.HTTPError, httpx.RequestError, ValueError, KeyError) as e:
            return {
                "error": f"Failed to complete pytest analysis: {str(e)}",
                "project_id": str(project_id),
                "job_id": job_id,
                "mcp_info": get_mcp_info("analyze_pytest_job_complete", error=True),
            }
