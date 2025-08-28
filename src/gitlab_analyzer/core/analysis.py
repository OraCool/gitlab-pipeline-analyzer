"""
Core analysis functions for pipeline failure investigation.

This module contains pure functions that were previously embedded in MCP tools.
Following DRY and KISS principles, these functions can be reused across tools and resources.
"""

import json
import logging
import re
from typing import Any

from gitlab_analyzer.api.client import GitLabAnalyzer
from gitlab_analyzer.cache.models import generate_standard_error_id
from gitlab_analyzer.parsers.log_parser import LogParser
from gitlab_analyzer.parsers.pytest_parser import PytestLogParser

logger = logging.getLogger(__name__)


async def store_jobs_metadata_step(
    cache_manager, project_id: str | int, pipeline_id: int, jobs
) -> None:
    """Store job metadata immediately after job list retrieval"""
    try:
        import aiosqlite

        async with aiosqlite.connect(cache_manager.db_path) as conn:
            for job in jobs:
                await conn.execute(
                    """
                    INSERT OR REPLACE INTO jobs
                    (job_id, project_id, pipeline_id, ref, sha, status, trace_hash, parser_version, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
                    """,
                    (
                        job.id,
                        int(project_id),
                        pipeline_id,
                        getattr(job, "ref", ""),
                        getattr(job, "sha", ""),
                        job.status,
                        f"pending_{job.id}",  # Placeholder until trace is analyzed
                        cache_manager.parser_version,
                    ),
                )

            await conn.commit()
            # Metadata stored for {len(jobs)} jobs

    except Exception as e:
        logger.error(f"Error storing job metadata: {e}")


async def store_job_analysis_step(
    cache_manager,
    project_id: str | int,
    pipeline_id: int,
    job_id: int,
    job,
    trace_content: str,
    analysis_data: dict,
) -> None:
    """Store job analysis data progressively as each job is processed"""
    try:
        import aiosqlite

        async with aiosqlite.connect(cache_manager.db_path) as conn:
            # Step 1: Update job with trace hash (job metadata already stored)
            await conn.execute(
                """
                UPDATE jobs
                SET trace_hash = ?, completed_at = datetime('now')
                WHERE job_id = ?
                """,
                (f"trace_{job_id}", job_id),
            )

            # Step 2: Note - Trace storage handled by trace_segments table
            # Raw trace storage not needed as we store contextual segments per error

            # Step 3: Store individual errors
            errors = analysis_data.get("errors", [])
            file_errors: dict[str, list[str]] = {}  # file_path -> [error_ids]

            for i, error in enumerate(errors):
                error_id = generate_standard_error_id(job_id, i)

                await conn.execute(
                    """
                    INSERT OR REPLACE INTO errors
                    (job_id, error_id, fingerprint, exception, message, file, line, detail_json)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        job_id,
                        error_id,
                        str(hash(str(error))),
                        error.get("type", "unknown"),
                        error.get("message", ""),
                        error.get("file", ""),
                        error.get("line", 0),
                        json.dumps(error),
                    ),
                )

                # Build file index
                file_path = error.get("file", "")
                if file_path:
                    if file_path not in file_errors:
                        file_errors[file_path] = []
                    file_errors[file_path].append(error_id)

            # Step 4: Store file index for fast file-based lookup
            for file_path, error_ids in file_errors.items():
                await conn.execute(
                    "INSERT OR REPLACE INTO file_index (job_id, path, error_ids) VALUES (?, ?, ?)",
                    (job_id, file_path, json.dumps(error_ids)),
                )

            await conn.commit()
            print(
                f"DEBUG: Stored analysis for job {job_id} - {len(errors)} errors, {len(file_errors)} files"
            )

    except Exception as e:
        print(f"DEBUG: Error storing job analysis for {job_id}: {e}")


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
    Parse job logs using the appropriate parser with hybrid fallback.

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
        # Try pytest parser first
        pytest_result = parse_pytest_logs(
            trace_content, include_traceback, exclude_paths
        )

        # If pytest parser finds no errors, fall back to generic parser
        # This handles cases where pytest jobs fail during setup/import phase
        if pytest_result.get("error_count", 0) == 0:
            logger.debug(
                f"Pytest parser found no errors for job {job_name}, trying generic parser"
            )
            generic_result = parse_generic_logs(trace_content)

            # If generic parser finds errors, use it but preserve pytest metadata
            if generic_result.get("error_count", 0) > 0:
                logger.info(
                    f"Generic parser found {generic_result.get('error_count')} errors for pytest job {job_name}"
                )
                # Merge results - use generic errors but keep pytest structure
                pytest_result.update(
                    {
                        "errors": generic_result.get("errors", []),
                        "error_count": generic_result.get("error_count", 0),
                        "warnings": generic_result.get("warnings", []),
                        "warning_count": generic_result.get("warning_count", 0),
                        "parser_type": "hybrid_pytest_generic",  # Indicate hybrid parsing
                        "fallback_reason": "pytest_parser_found_no_errors",
                    }
                )

        return pytest_result
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
    warnings: list[dict[str, Any]] = []

    if pytest_result.detailed_failures:
        for failure in pytest_result.detailed_failures:
            error_data = {
                "test_file": failure.test_file or "unknown",
                "test_function": failure.test_function or "unknown",
                "exception_type": failure.exception_type or "Unknown",
                "message": failure.exception_message or "No message",
                "line_number": getattr(failure, "line_number", None),
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
                                    "code_context": tb.code_line,
                                }
                            )
                    else:
                        filtered_traceback.append(
                            {
                                "file_path": tb.file_path,
                                "line_number": tb.line_number,
                                "function_name": tb.function_name,
                                "code_context": tb.code_line,
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
                "total_tests": pytest_result.statistics.total_tests,
                "passed": pytest_result.statistics.passed,
                "failed": pytest_result.statistics.failed,
                "skipped": pytest_result.statistics.skipped,
                "duration": pytest_result.statistics.duration_formatted,
            }
            if pytest_result.statistics.total_tests
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
        # Only skip truly meaningless errors, NOT errors with "unknown" file paths
        # SyntaxErrors and other real errors should be kept even if file path extraction failed
        if (
            error.get("exception_type")
            == "Unknown"  # Keep this filter for truly unknown exception types
            or error.get("message", "").startswith(
                "unknown:"
            )  # Keep this for unknown message prefixes
            or not error.get("message", "").strip()  # Keep this for empty messages
        ):
            continue

        # REMOVED: error.get("test_file") == "unknown" - this was filtering out real SyntaxErrors
        # Real errors with failed file path extraction should still be stored

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
    cache_manager=None,
) -> dict[str, Any]:
    """
    Analyze all jobs in a pipeline, selecting optimal parsers.

    Args:
        analyzer: GitLab analyzer instance
        project_id: GitLab project ID
        pipeline_id: Pipeline ID to analyze
        failed_jobs_only: Only analyze failed jobs
        cache_manager: Optional cache manager for progressive storage

    Returns:
        Comprehensive pipeline analysis with job-specific parsing
    """
    # Get pipeline info and jobs
    pipeline_info = await analyzer.get_pipeline(project_id, pipeline_id)
    jobs = await analyzer.get_pipeline_jobs(project_id, pipeline_id)

    if failed_jobs_only:
        jobs = [job for job in jobs if job.status == "failed"]

    # Store job metadata immediately (Step 2A: Job List)
    if cache_manager:
        print(f"DEBUG: Storing metadata for {len(jobs)} jobs")
        await store_jobs_metadata_step(cache_manager, project_id, pipeline_id, jobs)

    analyzed_jobs = []
    total_errors = 0
    total_warnings = 0

    # Now process each job's trace and analysis (Step 2B: Job Analysis)
    for job in jobs:
        job_id = job.id
        job_name = job.name
        job_stage = job.stage

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

            job_analysis = {
                "job_id": job_id,
                "job_name": job_name,
                "job_stage": job_stage,
                "job_status": job.status,
                "analysis": filtered_data,
            }

            analyzed_jobs.append(job_analysis)

            # Progressive storage: Store job data immediately
            if cache_manager:
                await store_job_analysis_step(
                    cache_manager,
                    project_id,
                    pipeline_id,
                    job_id,
                    job,
                    trace,
                    filtered_data,
                )

            total_errors += filtered_data.get("error_count", 0)
            total_warnings += filtered_data.get("warning_count", 0)

        except Exception as e:
            analyzed_jobs.append(
                {
                    "job_id": job_id,
                    "job_name": job_name,
                    "job_stage": job_stage,
                    "job_status": job.status,
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
                    if isinstance(j["analysis"], dict)
                    and j["analysis"].get("parser_type") == "pytest"
                ]
            ),
            "generic_jobs": len(
                [
                    j
                    for j in analyzed_jobs
                    if isinstance(j["analysis"], dict)
                    and j["analysis"].get("parser_type") == "generic"
                ]
            ),
            "error_jobs": len(
                [
                    j
                    for j in analyzed_jobs
                    if isinstance(j["analysis"], dict)
                    and j["analysis"].get("parser_type") == "error"
                ]
            ),
        },
    }
