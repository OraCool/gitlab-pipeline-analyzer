"""
Core analysis functions for pipeline failure investigation.

This module contains pure functions that were previously embedded in MCP tools.
Following DRY and KISS principles, these functions can be reused across tools and resources.
"""

import re
from typing import Any

from gitlab_analyzer.api.client import GitLabAnalyzer
from gitlab_analyzer.parsers.log_parser import LogParser
from gitlab_analyzer.parsers.pytest_parser import PytestLogParser


def is_pytest_job(
    job_name: str = "", job_stage: str = "", trace_content: str = ""
) -> bool:
    """
    Determine if a job is likely running pytest tests.

    Args:
        job_name: Name of the CI/CD job
        job_stage: Stage of the CI/CD job
        trace_content: Raw log content from the job

    Returns:
        True if job appears to be running pytest
    """
    # Check job name patterns
    pytest_name_patterns = [
        r"test",
        r"pytest",
        r"unit.*test",
        r"integration.*test",
        r"e2e.*test",
    ]

    for pattern in pytest_name_patterns:
        if re.search(pattern, job_name.lower()):
            return True

    # Check job stage patterns
    pytest_stage_patterns = [r"test", r"testing", r"unit", r"integration"]

    for pattern in pytest_stage_patterns:
        if re.search(pattern, job_stage.lower()):
            return True

    # Check trace content for pytest indicators
    if trace_content:
        pytest_indicators = [
            "pytest",
            "==== FAILURES ====",
            "==== test session starts ====",
            "collected \\d+ items?",
            "::.*FAILED",
            "conftest.py",
        ]

        for indicator in pytest_indicators:
            if re.search(indicator, trace_content, re.IGNORECASE):
                return True

    return False


def get_optimal_parser(
    job_name: str = "", job_stage: str = "", trace_content: str = ""
) -> str:
    """
    Select the optimal parser for a job based on its characteristics.

    Args:
        job_name: Name of the CI/CD job
        job_stage: Stage of the CI/CD job
        trace_content: Raw log content from the job

    Returns:
        Parser type: "pytest" or "generic"
    """
    if is_pytest_job(job_name, job_stage, trace_content):
        return "pytest"
    return "generic"


def parse_job_logs(
    trace_content: str,
    parser_type: str = "auto",
    job_name: str = "",
    job_stage: str = "",
    include_traceback: bool = True,
    exclude_paths: list[str] | None = None,
) -> dict[str, Any]:
    """
    Parse job logs using the appropriate parser.

    Args:
        trace_content: Raw log content
        parser_type: "auto", "pytest", or "generic"
        job_name: Job name for auto-detection
        job_stage: Job stage for auto-detection
        include_traceback: Whether to include traceback in results
        exclude_paths: Paths to exclude from traceback

    Returns:
        Parsed log data with errors, warnings, and metadata
    """
    if parser_type == "auto":
        parser_type = get_optimal_parser(job_name, job_stage, trace_content)

    if parser_type == "pytest":
        return parse_pytest_logs(trace_content, include_traceback, exclude_paths)
    else:
        return parse_generic_logs(trace_content)


def parse_pytest_logs(
    trace_content: str,
    include_traceback: bool = True,
    exclude_paths: list[str] | None = None,
) -> dict[str, Any]:
    """
    Parse pytest logs using specialized pytest parser.

    Args:
        trace_content: Raw pytest log content
        include_traceback: Whether to include traceback details
        exclude_paths: Paths to exclude from traceback

    Returns:
        Parsed pytest data with detailed failure information
    """
    pytest_result = PytestLogParser.parse_pytest_log(trace_content)

    # Convert to standardized format
    errors = []
    warnings = []

    if pytest_result.detailed_failures:
        for failure in pytest_result.detailed_failures:
            error_data = {
                "test_file": failure.test_file or "unknown",
                "test_function": failure.test_function or "unknown",
                "exception_type": failure.exception_type or "Unknown",
                "message": failure.message or "No message",
                "line_number": failure.line_number,
                "has_traceback": bool(failure.traceback and include_traceback),
            }

            if include_traceback and failure.traceback:
                # Filter traceback if paths are specified
                filtered_traceback = []
                for tb in failure.traceback:
                    if exclude_paths:
                        skip = any(
                            exclude_path in str(tb.file_path)
                            for exclude_path in exclude_paths
                        )
                        if not skip:
                            filtered_traceback.append(
                                {
                                    "file_path": tb.file_path,
                                    "line_number": tb.line_number,
                                    "function_name": tb.function_name,
                                    "code_context": tb.code_context,
                                }
                            )
                    else:
                        filtered_traceback.append(
                            {
                                "file_path": tb.file_path,
                                "line_number": tb.line_number,
                                "function_name": tb.function_name,
                                "code_context": tb.code_context,
                            }
                        )
                error_data["traceback"] = filtered_traceback

            errors.append(error_data)

    return {
        "parser_type": "pytest",
        "errors": errors,
        "warnings": warnings,  # Pytest parser doesn't extract warnings yet
        "error_count": len(errors),
        "warning_count": len(warnings),
        "test_summary": (
            {
                "total_tests": pytest_result.total_tests,
                "passed": pytest_result.passed_tests,
                "failed": pytest_result.failed_tests,
                "skipped": pytest_result.skipped_tests,
                "duration": pytest_result.duration,
            }
            if pytest_result.total_tests
            else None
        ),
    }


def parse_generic_logs(trace_content: str) -> dict[str, Any]:
    """
    Parse generic logs using the standard log parser.

    Args:
        trace_content: Raw log content

    Returns:
        Parsed log data with errors and warnings
    """
    parser = LogParser()
    log_entries = parser.extract_log_entries(trace_content)

    errors = [
        {
            "message": entry.message,
            "level": entry.level,
            "line_number": entry.line_number,
            "context": entry.context,
            "category": entry.category,
        }
        for entry in log_entries
        if entry.level == "error"
    ]

    warnings = [
        {
            "message": entry.message,
            "level": entry.level,
            "line_number": entry.line_number,
            "context": entry.context,
            "category": entry.category,
        }
        for entry in log_entries
        if entry.level == "warning"
    ]

    return {
        "parser_type": "generic",
        "errors": errors,
        "warnings": warnings,
        "error_count": len(errors),
        "warning_count": len(warnings),
        "total_entries": len(log_entries),
    }


def filter_unknown_errors(parsed_data: dict[str, Any]) -> dict[str, Any]:
    """
    Filter out unknown/meaningless errors from parsed data.

    Args:
        parsed_data: Result from parse_job_logs()

    Returns:
        Filtered data with meaningful errors only
    """
    if not parsed_data or "errors" not in parsed_data:
        return parsed_data

    filtered_errors = []
    for error in parsed_data.get("errors", []):
        # Skip unknown files and errors
        if (
            error.get("test_file") == "unknown"
            or error.get("exception_type") == "Unknown"
            or error.get("message", "").startswith("unknown:")
            or not error.get("message", "").strip()
        ):
            continue
        filtered_errors.append(error)

    # Return updated result
    result = parsed_data.copy()
    result["errors"] = filtered_errors
    result["error_count"] = len(filtered_errors)
    result["filtered"] = True

    return result


async def analyze_pipeline_jobs(
    analyzer: GitLabAnalyzer,
    project_id: str | int,
    pipeline_id: int,
    failed_jobs_only: bool = True,
) -> dict[str, Any]:
    """
    Analyze all jobs in a pipeline, selecting optimal parsers.

    Args:
        analyzer: GitLab analyzer instance
        project_id: GitLab project ID
        pipeline_id: Pipeline ID to analyze
        failed_jobs_only: Only analyze failed jobs

    Returns:
        Comprehensive pipeline analysis with job-specific parsing
    """
    # Get pipeline info and jobs
    pipeline_info = await analyzer.get_pipeline(project_id, pipeline_id)
    jobs = await analyzer.get_pipeline_jobs(project_id, pipeline_id)

    if failed_jobs_only:
        jobs = [job for job in jobs if job.get("status") == "failed"]

    analyzed_jobs = []
    total_errors = 0
    total_warnings = 0

    for job in jobs:
        job_id = job["id"]
        job_name = job.get("name", "")
        job_stage = job.get("stage", "")

        try:
            # Get job trace
            trace = await analyzer.get_job_trace(project_id, job_id)

            # Parse with optimal parser
            parsed_data = parse_job_logs(
                trace_content=trace,
                parser_type="auto",
                job_name=job_name,
                job_stage=job_stage,
            )

            # Filter meaningless errors
            filtered_data = filter_unknown_errors(parsed_data)

            analyzed_jobs.append(
                {
                    "job_id": job_id,
                    "job_name": job_name,
                    "job_stage": job_stage,
                    "job_status": job.get("status"),
                    "analysis": filtered_data,
                }
            )

            total_errors += filtered_data.get("error_count", 0)
            total_warnings += filtered_data.get("warning_count", 0)

        except Exception as e:
            analyzed_jobs.append(
                {
                    "job_id": job_id,
                    "job_name": job_name,
                    "job_stage": job_stage,
                    "job_status": job.get("status"),
                    "analysis": {
                        "error": f"Failed to analyze job: {str(e)}",
                        "parser_type": "error",
                    },
                }
            )

    return {
        "pipeline_id": pipeline_id,
        "project_id": str(project_id),
        "pipeline_status": pipeline_info.get("status"),
        "analyzed_jobs": analyzed_jobs,
        "total_failed_jobs": len(
            [j for j in analyzed_jobs if j["job_status"] == "failed"]
        ),
        "total_errors": total_errors,
        "total_warnings": total_warnings,
        "analysis_summary": {
            "pytest_jobs": len(
                [
                    j
                    for j in analyzed_jobs
                    if j["analysis"].get("parser_type") == "pytest"
                ]
            ),
            "generic_jobs": len(
                [
                    j
                    for j in analyzed_jobs
                    if j["analysis"].get("parser_type") == "generic"
                ]
            ),
            "error_jobs": len(
                [
                    j
                    for j in analyzed_jobs
                    if j["analysis"].get("parser_type") == "error"
                ]
            ),
        },
    }
