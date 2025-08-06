"""
Pytest-specific MCP tools for GitLab Pipeline Analyzer

Copyright (c) 2025 Siarhei Skuratovich
Licensed under the MIT License - see LICENSE file for details
"""

from datetime import datetime
from typing import Any

import httpx
from fastmcp import FastMCP

from gitlab_analyzer.parsers.pytest_parser import PytestLogParser

from .utils import get_gitlab_analyzer


def _extract_pytest_errors(log_text: str) -> dict[str, Any]:
    """Extract errors from pytest logs using specialized parser"""
    try:
        pytest_analysis = PytestLogParser.parse_pytest_log(log_text)

        # Convert detailed failures to error format
        errors = []

        # Use detailed failures if available (more comprehensive)
        if pytest_analysis.detailed_failures:
            for failure in pytest_analysis.detailed_failures:
                # Extract the actual source code line number from traceback
                source_line_number = None
                if failure.traceback:
                    # Find the first traceback entry that has a line number
                    for tb in failure.traceback:
                        if tb.line_number:
                            source_line_number = tb.line_number
                            break

                # Build comprehensive context with full error text and traceback
                context_parts = [
                    f"Test: {failure.test_name}",
                    f"File: {failure.test_file}",
                    f"Function: {failure.test_function}",
                    f"Exception: {failure.exception_type}: {failure.exception_message}",
                ]

                # Add full error text if available
                if failure.full_error_text:
                    context_parts.append(
                        f"\nFull Error Details:\n{failure.full_error_text}"
                    )

                error: dict[str, Any] = {
                    "level": "error",
                    "message": f"{failure.test_file}:{failure.exception_type}: {failure.exception_message}",
                    "line_number": source_line_number,  # Use actual source code line number
                    "timestamp": None,
                    "context": "\n".join(context_parts),
                    "test_name": failure.test_name,
                    "test_file": failure.test_file,
                    "test_function": failure.test_function,
                    "exception_type": failure.exception_type,
                    "exception_message": failure.exception_message,
                    "platform_info": failure.platform_info,
                    "python_version": failure.python_version,
                    "full_error_text": failure.full_error_text,  # Add full error text as separate field
                }
                if failure.traceback:
                    # Add detailed traceback info to context
                    traceback_info = []
                    for tb in failure.traceback:
                        if tb.line_number:
                            traceback_info.append(
                                f'  File "{tb.file_path}", line {tb.line_number}, in {tb.function_name}'
                            )
                            if tb.code_line:
                                traceback_info.append(f"    {tb.code_line}")
                            if tb.error_type and tb.error_message:
                                traceback_info.append(
                                    f"    {tb.error_type}: {tb.error_message}"
                                )

                    if traceback_info:
                        # Add traceback to context (which already has full error text)
                        current_context = str(error.get("context", ""))
                        error["context"] = (
                            current_context
                            + "\n\nTraceback Details:\n"
                            + "\n".join(traceback_info)
                        )
                        # Also add traceback as separate field for structured access
                        error["traceback"] = [
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
                errors.append(error)

        # If no detailed failures, fall back to short summary
        elif pytest_analysis.short_summary:
            for summary in pytest_analysis.short_summary:
                # Build comprehensive context for short summary
                context_parts = [
                    f"Test: {summary.test_name}",
                    f"File: {summary.test_file}",
                    f"Function: {summary.test_function}",
                    f"Exception: {summary.error_type}: {summary.error_message}",
                    "\nNote: This is from short summary - limited details available",
                ]

                summary_error: dict[str, Any] = {
                    "level": "error",
                    "message": f"{summary.test_file}:{summary.error_type}: {summary.error_message}",
                    "line_number": None,
                    "timestamp": None,
                    "context": "\n".join(context_parts),
                    "test_name": summary.test_name,
                    "test_file": summary.test_file,
                    "test_function": summary.test_function,
                    "exception_type": summary.error_type,
                    "exception_message": summary.error_message,
                }
                errors.append(summary_error)

        # Add statistics information if available
        additional_info = {}
        if pytest_analysis.statistics:
            stats = pytest_analysis.statistics
            additional_info.update(
                {
                    "total_tests": stats.total_tests,
                    "passed": stats.passed,
                    "failed": stats.failed,
                    "skipped": stats.skipped,
                    "pytest_errors": stats.errors,  # Rename to avoid conflict
                    "pytest_warnings": stats.warnings,  # Rename to avoid conflict
                    "duration_seconds": stats.duration_seconds,
                    "duration_formatted": stats.duration_formatted,
                }
            )

        return {
            "total_entries": len(errors),
            "errors": errors,
            "warnings": [],  # pytest warnings not typically captured as warnings
            "error_count": len(errors),
            "warning_count": 0,
            "analysis_timestamp": datetime.now().isoformat(),
            "parser_type": "pytest",
            "has_failures_section": pytest_analysis.has_failures_section,
            "has_short_summary_section": pytest_analysis.has_short_summary_section,
            **additional_info,
        }

    except Exception as e:
        return {"error": f"Failed to extract pytest errors: {str(e)}"}


def register_pytest_tools(mcp: FastMCP) -> None:
    """Register pytest-specific analysis tools"""

    @mcp.tool
    async def extract_pytest_detailed_failures(
        project_id: str | int, job_id: int
    ) -> dict[str, Any]:
        """
        Extract detailed test failures from a pytest job's trace with full
        tracebacks and call stacks.

        Args:
            project_id: The GitLab project ID or path
            job_id: The ID of the job containing pytest failures

        Returns:
            Detailed analysis of pytest failures including full tracebacks,
            exception details, and file/line information
        """
        try:
            analyzer = get_gitlab_analyzer()
            trace = await analyzer.get_job_trace(project_id, job_id)

            pytest_analysis = PytestLogParser.parse_pytest_log(trace)

            return {
                "project_id": str(project_id),
                "job_id": job_id,
                "has_failures_section": pytest_analysis.has_failures_section,
                "detailed_failures": [
                    {
                        "test_name": failure.test_name,
                        "test_file": failure.test_file,
                        "test_function": failure.test_function,
                        "test_parameters": failure.test_parameters,
                        "platform_info": failure.platform_info,
                        "python_version": failure.python_version,
                        "exception_type": failure.exception_type,
                        "exception_message": failure.exception_message,
                        "traceback": [
                            {
                                "file_path": tb.file_path,
                                "line_number": tb.line_number,
                                "function_name": tb.function_name,
                                "code_line": tb.code_line,
                                "error_type": tb.error_type,
                                "error_message": tb.error_message,
                            }
                            for tb in failure.traceback
                        ],
                        "full_error_text": failure.full_error_text,
                    }
                    for failure in pytest_analysis.detailed_failures
                ],
                "failure_count": len(pytest_analysis.detailed_failures),
                "analysis_timestamp": datetime.now().isoformat(),
            }

        except (httpx.HTTPError, httpx.RequestError, ValueError, KeyError) as e:
            return {
                "error": f"Failed to extract pytest detailed failures: {str(e)}",
                "project_id": str(project_id),
                "job_id": job_id,
            }

    @mcp.tool
    async def extract_pytest_short_summary(
        project_id: str | int, job_id: int
    ) -> dict[str, Any]:
        """
        Extract short test summary info from a pytest job's trace, providing
        concise failure information.

        Args:
            project_id: The GitLab project ID or path
            job_id: The ID of the job containing pytest failures

        Returns:
            Short summary of pytest failures with test names and brief error
            messages
        """
        try:
            analyzer = get_gitlab_analyzer()
            trace = await analyzer.get_job_trace(project_id, job_id)

            pytest_analysis = PytestLogParser.parse_pytest_log(trace)

            return {
                "project_id": str(project_id),
                "job_id": job_id,
                "has_short_summary_section": pytest_analysis.has_short_summary_section,
                "short_summary": [
                    {
                        "test_name": summary.test_name,
                        "test_file": summary.test_file,
                        "test_function": summary.test_function,
                        "test_parameters": summary.test_parameters,
                        "error_type": summary.error_type,
                        "error_message": summary.error_message,
                    }
                    for summary in pytest_analysis.short_summary
                ],
                "summary_count": len(pytest_analysis.short_summary),
                "analysis_timestamp": datetime.now().isoformat(),
            }

        except (httpx.HTTPError, httpx.RequestError, ValueError, KeyError) as e:
            return {
                "error": f"Failed to extract pytest short summary: {str(e)}",
                "project_id": str(project_id),
                "job_id": job_id,
            }

    @mcp.tool
    async def extract_pytest_statistics(
        project_id: str | int, job_id: int
    ) -> dict[str, Any]:
        """
        Extract pytest test statistics including total tests, passed, failed,
        skipped counts and execution duration.

        Args:
            project_id: The GitLab project ID or path
            job_id: The ID of the job containing pytest results

        Returns:
            Complete pytest run statistics including test counts and timing
            information
        """
        try:
            analyzer = get_gitlab_analyzer()
            trace = await analyzer.get_job_trace(project_id, job_id)

            pytest_analysis = PytestLogParser.parse_pytest_log(trace)

            statistics = pytest_analysis.statistics
            return {
                "project_id": str(project_id),
                "job_id": job_id,
                "statistics": {
                    "total_tests": statistics.total_tests,
                    "passed": statistics.passed,
                    "failed": statistics.failed,
                    "skipped": statistics.skipped,
                    "errors": statistics.errors,
                    "warnings": statistics.warnings,
                    "duration_seconds": statistics.duration_seconds,
                    "duration_formatted": statistics.duration_formatted,
                    "success_rate": (
                        round((statistics.passed / statistics.total_tests) * 100, 2)
                        if statistics.total_tests > 0
                        else 0
                    ),
                },
                "analysis_timestamp": datetime.now().isoformat(),
            }

        except (httpx.HTTPError, httpx.RequestError, ValueError, KeyError) as e:
            return {
                "error": f"Failed to extract pytest statistics: {str(e)}",
                "project_id": str(project_id),
                "job_id": job_id,
            }

    @mcp.tool
    async def analyze_pytest_job_complete(
        project_id: str | int, job_id: int
    ) -> dict[str, Any]:
        """
        Complete pytest job analysis that combines detailed failures, short
        summary, and statistics in one comprehensive report.

        Args:
            project_id: The GitLab project ID or path
            job_id: The ID of the job containing pytest results

        Returns:
            Complete pytest analysis with all three types of information:
            detailed failures, short summary, and statistics
        """
        try:
            analyzer = get_gitlab_analyzer()
            trace = await analyzer.get_job_trace(project_id, job_id)

            pytest_analysis = PytestLogParser.parse_pytest_log(trace)

            # Convert detailed failures
            detailed_failures = [
                {
                    "test_name": failure.test_name,
                    "test_file": failure.test_file,
                    "test_function": failure.test_function,
                    "test_parameters": failure.test_parameters,
                    "platform_info": failure.platform_info,
                    "python_version": failure.python_version,
                    "exception_type": failure.exception_type,
                    "exception_message": failure.exception_message,
                    "traceback": [
                        {
                            "file_path": tb.file_path,
                            "line_number": tb.line_number,
                            "function_name": tb.function_name,
                            "code_line": tb.code_line,
                            "error_type": tb.error_type,
                            "error_message": tb.error_message,
                        }
                        for tb in failure.traceback
                    ],
                    "full_error_text": failure.full_error_text,
                }
                for failure in pytest_analysis.detailed_failures
            ]

            # Convert short summary
            short_summary = [
                {
                    "test_name": summary.test_name,
                    "test_file": summary.test_file,
                    "test_function": summary.test_function,
                    "test_parameters": summary.test_parameters,
                    "error_type": summary.error_type,
                    "error_message": summary.error_message,
                }
                for summary in pytest_analysis.short_summary
            ]

            # Convert statistics
            statistics = {
                "total_tests": pytest_analysis.statistics.total_tests,
                "passed": pytest_analysis.statistics.passed,
                "failed": pytest_analysis.statistics.failed,
                "skipped": pytest_analysis.statistics.skipped,
                "errors": pytest_analysis.statistics.errors,
                "warnings": pytest_analysis.statistics.warnings,
                "duration_seconds": pytest_analysis.statistics.duration_seconds,
                "duration_formatted": pytest_analysis.statistics.duration_formatted,
                "success_rate": (
                    round(
                        (
                            pytest_analysis.statistics.passed
                            / pytest_analysis.statistics.total_tests
                        )
                        * 100,
                        2,
                    )
                    if pytest_analysis.statistics.total_tests > 0
                    else 0
                ),
            }

            return {
                "project_id": str(project_id),
                "job_id": job_id,
                "detailed_failures": detailed_failures,
                "short_summary": short_summary,
                "statistics": statistics,
                "has_failures_section": pytest_analysis.has_failures_section,
                "has_short_summary_section": pytest_analysis.has_short_summary_section,
                "analysis_timestamp": datetime.now().isoformat(),
                "summary": {
                    "failure_count": len(detailed_failures),
                    "summary_count": len(short_summary),
                    "test_success_rate": statistics["success_rate"],
                    "critical_failures": len(
                        [
                            f
                            for f in detailed_failures
                            if (exception_type := f.get("exception_type"))
                            and isinstance(exception_type, str)
                            and "error" in exception_type.lower()
                        ]
                    ),
                },
            }

        except (httpx.HTTPError, httpx.RequestError, ValueError, KeyError) as e:
            return {
                "error": f"Failed to analyze pytest job: {str(e)}",
                "project_id": str(project_id),
                "job_id": job_id,
            }
