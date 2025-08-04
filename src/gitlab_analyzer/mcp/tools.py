"""
MCP tool functions for GitLab Pipeline Analyzer

Copyright (c) 2025 Siarhei Skuratovich
Licensed under the MIT License - see LICENSE file for details
"""

import os
from datetime import datetime
from typing import Any

import httpx
from fastmcp import FastMCP

from ..api.client import GitLabAnalyzer
from ..parsers.log_parser import LogParser

# GitLab analyzer singleton instance
_GITLAB_ANALYZER = None


def get_gitlab_analyzer() -> GitLabAnalyzer:
    """Get or create GitLab analyzer instance"""
    global _GITLAB_ANALYZER  # pylint: disable=global-statement

    if _GITLAB_ANALYZER is None:
        gitlab_url = os.getenv("GITLAB_URL", "https://gitlab.com")
        gitlab_token = os.getenv("GITLAB_TOKEN")

        if not gitlab_token:
            raise ValueError("GITLAB_TOKEN environment variable is required")

        _GITLAB_ANALYZER = GitLabAnalyzer(gitlab_url, gitlab_token)

    return _GITLAB_ANALYZER


def register_tools(mcp: FastMCP) -> None:
    """Register all MCP tools"""

    @mcp.tool
    async def analyze_failed_pipeline(
        project_id: str | int, pipeline_id: int
    ) -> dict[str, Any]:
        """
        Analyze a failed GitLab CI/CD pipeline and extract errors/warnings from all
        failed jobs. Uses optimized API calls to fetch only failed jobs.

        Args:
            project_id: The GitLab project ID or path
            pipeline_id: The ID of the GitLab pipeline to analyze

        Returns:
            Complete analysis including pipeline info, failed jobs, and extracted
            errors/warnings
        """
        return await analyze_failed_pipeline_optimized(project_id, pipeline_id)

    @mcp.tool
    async def analyze_single_job(project_id: str | int, job_id: int) -> dict[str, Any]:
        """
        Analyze a single GitLab CI/CD job and extract errors/warnings from its
        trace.

        Args:
            project_id: The GitLab project ID or path
            job_id: The ID of the specific job to analyze

        Returns:
            Analysis of the single job including extracted errors/warnings
        """
        analyzer = get_gitlab_analyzer()

        try:
            # Get job trace
            trace = await analyzer.get_job_trace(project_id, job_id)

            if not trace.strip():
                return {
                    "error": f"No trace found for job {job_id}",
                    "project_id": str(project_id),
                    "job_id": job_id,
                }

            # Extract errors and warnings from the trace
            log_entries = LogParser.extract_log_entries(trace)

            # Categorize entries with detailed information
            errors = []
            warnings = []

            for entry in log_entries:
                entry_dict = entry.dict()

                if entry.level == "error":
                    # Add detailed error categorization
                    error_details = LogParser.categorize_error(
                        entry.message, entry.context or ""
                    )

                    # Use source line number if available (for test failures), otherwise use log line number
                    line_number = entry_dict[
                        "line_number"
                    ]  # Default to log line number
                    if "source_line" in error_details:
                        line_number = error_details["source_line"]

                    entry_dict.update(
                        {
                            "line_number": line_number,  # Override with source line if available
                            "category": error_details["category"],
                            "severity": error_details["severity"],
                            "description": error_details["description"],
                            "details": error_details.get(
                                "details", "No specific details available"
                            ),
                            "solution": error_details["solution"],
                            "impact": error_details["impact"],
                        }
                    )
                    errors.append(entry_dict)

                elif entry.level == "warning":
                    # Add basic categorization for warnings
                    entry_dict.update(
                        {
                            "category": "Warning",
                            "severity": "low",
                            "description": "Potential issue detected",
                            "solution": "Review warning message and consider addressing",
                            "impact": "May cause issues or indicate suboptimal configuration",
                        }
                    )
                    warnings.append(entry_dict)

            # Get job URL (construct based on GitLab URL pattern)
            analyzer_instance = get_gitlab_analyzer()
            job_url = f"{analyzer_instance.gitlab_url}/-/jobs/{job_id}"

            # Calculate error statistics by category and severity
            error_categories: dict[str, int] = {}
            severity_counts = {"high": 0, "medium": 0, "low": 0}
            affected_files = set()

            for error in errors:
                category = error.get("category", "Unknown")
                severity = error.get("severity", "medium")

                error_categories[category] = error_categories.get(category, 0) + 1
                severity_counts[severity] = severity_counts.get(severity, 0) + 1

                # Extract file paths from error messages
                message = error.get("message", "")
                if "would reformat" in message:
                    import re

                    file_match = re.search(r"would reformat (.+)", message)
                    if file_match:
                        affected_files.add(file_match.group(1))

            result = {
                "project_id": str(project_id),
                "job_id": job_id,
                "job_url": job_url,
                "analysis": {
                    "errors": errors,
                    "warnings": warnings,
                    "error_summary": {
                        "categories": error_categories,
                        "severity_breakdown": severity_counts,
                        "most_common_category": (
                            max(error_categories.items(), key=lambda x: x[1])[0]
                            if error_categories
                            else None
                        ),
                    },
                },
                "summary": {
                    "total_errors": len(errors),
                    "total_warnings": len(warnings),
                    "total_log_entries": len(log_entries),
                    "has_trace": bool(trace.strip()),
                    "trace_length": len(trace),
                    "analysis_timestamp": datetime.now().isoformat(),
                    "critical_issues": severity_counts["high"],
                    "needs_attention": severity_counts["high"]
                    + severity_counts["medium"],
                    "affected_files": sorted(affected_files) if affected_files else [],
                    "formatting_files_count": len(affected_files),
                },
            }

            return result

        except (httpx.HTTPError, httpx.RequestError, ValueError, KeyError) as e:
            return {
                "error": f"Failed to analyze job {job_id}: {str(e)}",
                "project_id": str(project_id),
                "job_id": job_id,
            }

    @mcp.tool
    async def get_pipeline_jobs(
        project_id: str | int, pipeline_id: int
    ) -> dict[str, Any]:
        """
        Get all jobs for a specific GitLab pipeline.

        Args:
            project_id: The GitLab project ID or path
            pipeline_id: The ID of the GitLab pipeline

        Returns:
            List of all jobs in the pipeline with their status and details
        """
        analyzer = get_gitlab_analyzer()

        try:
            jobs = await analyzer.get_pipeline_jobs(project_id, pipeline_id)
            return {
                "project_id": str(project_id),
                "pipeline_id": pipeline_id,
                "jobs": [job.dict() for job in jobs],
                "total_jobs": len(jobs),
                "failed_jobs": len([job for job in jobs if job.status == "failed"]),
                "passed_jobs": len([job for job in jobs if job.status == "success"]),
            }
        except (httpx.HTTPError, httpx.RequestError, ValueError, KeyError) as e:
            return {
                "error": (f"Failed to get jobs for pipeline {pipeline_id}: {str(e)}"),
                "project_id": str(project_id),
                "pipeline_id": pipeline_id,
            }

    @mcp.tool
    async def get_failed_jobs(
        project_id: str | int, pipeline_id: int
    ) -> dict[str, Any]:
        """
        Get only the failed jobs for a specific GitLab CI/CD pipeline.

        Args:
            project_id: The GitLab project ID or path
            pipeline_id: The ID of the GitLab pipeline

        Returns:
            List of failed jobs with their details
        """
        analyzer = get_gitlab_analyzer()

        try:
            failed_jobs = await analyzer.get_failed_pipeline_jobs(
                project_id, pipeline_id
            )
            return {
                "project_id": str(project_id),
                "pipeline_id": pipeline_id,
                "failed_jobs": [
                    {
                        "id": job.id,
                        "name": job.name,
                        "stage": job.stage,
                        "status": job.status,
                        "created_at": job.created_at,
                        "started_at": job.started_at,
                        "finished_at": job.finished_at,
                        "failure_reason": job.failure_reason,
                        "web_url": job.web_url,
                    }
                    for job in failed_jobs
                ],
                "failed_job_count": len(failed_jobs),
            }
        except (httpx.HTTPError, httpx.RequestError, ValueError) as e:
            return {
                "error": f"Failed to get failed jobs for pipeline {pipeline_id}: {str(e)}",
                "project_id": str(project_id),
                "pipeline_id": pipeline_id,
            }

    @mcp.tool
    async def get_job_trace(project_id: str | int, job_id: int) -> dict[str, Any]:
        """
        Get the trace log for a specific GitLab CI/CD job.

        Args:
            project_id: The GitLab project ID or path
            job_id: The ID of the GitLab job

        Returns:
            The complete trace log for the job
        """
        analyzer = get_gitlab_analyzer()

        try:
            trace = await analyzer.get_job_trace(project_id, job_id)
            return {
                "project_id": str(project_id),
                "job_id": job_id,
                "trace": trace,
                "trace_length": len(trace),
                "has_content": bool(trace.strip()),
            }
        except (httpx.HTTPError, httpx.RequestError, ValueError) as e:
            return {
                "error": f"Failed to get trace for job {job_id}: {str(e)}",
                "project_id": str(project_id),
                "job_id": job_id,
            }

    @mcp.tool
    async def extract_log_errors(log_text: str) -> dict[str, Any]:
        """
        Extract errors and warnings from log text.

        Args:
            log_text: The log text to analyze

        Returns:
            Extracted errors and warnings with context
        """
        try:
            log_entries = LogParser.extract_log_entries(log_text)

            errors = [entry.dict() for entry in log_entries if entry.level == "error"]
            warnings = [
                entry.dict() for entry in log_entries if entry.level == "warning"
            ]

            return {
                "total_entries": len(log_entries),
                "errors": errors,
                "warnings": warnings,
                "error_count": len(errors),
                "warning_count": len(warnings),
                "analysis_timestamp": datetime.now().isoformat(),
            }
        except (ValueError, TypeError, AttributeError) as e:
            return {"error": f"Failed to extract log errors: {str(e)}"}

    @mcp.tool
    async def get_pipeline_status(
        project_id: str | int, pipeline_id: int
    ) -> dict[str, Any]:
        """
        Get the current status and basic information of a GitLab pipeline.

        Args:
            project_id: The GitLab project ID or path
            pipeline_id: The ID of the GitLab pipeline

        Returns:
            Pipeline status and basic information
        """
        analyzer = get_gitlab_analyzer()

        try:
            pipeline = await analyzer.get_pipeline(project_id, pipeline_id)
            return {
                "project_id": str(project_id),
                "pipeline_id": pipeline_id,
                "status": pipeline["status"],
                "created_at": pipeline["created_at"],
                "updated_at": pipeline["updated_at"],
                "web_url": pipeline["web_url"],
                "ref": pipeline["ref"],
                "sha": pipeline["sha"],
                "source": pipeline.get("source", "unknown"),
            }
        except (httpx.HTTPError, httpx.RequestError, ValueError, KeyError) as e:
            return {
                "error": (f"Failed to get pipeline status for {pipeline_id}: {str(e)}"),
                "project_id": str(project_id),
                "pipeline_id": pipeline_id,
            }


async def analyze_failed_pipeline_optimized(
    project_id: str | int, pipeline_id: int
) -> dict[str, Any]:
    """
    Optimized version that only fetches failed jobs (faster for large
    pipelines)

    Args:
        project_id: The GitLab project ID or path
        pipeline_id: The ID of the GitLab pipeline to analyze

    Returns:
        Analysis focusing only on failed jobs without total job statistics
    """
    analyzer = get_gitlab_analyzer()

    try:
        # Get pipeline information
        pipeline = await analyzer.get_pipeline(project_id, pipeline_id)

        # Get only failed jobs (optimized - single API call)
        failed_jobs = await analyzer.get_failed_pipeline_jobs(project_id, pipeline_id)

        # Analyze each failed job
        analysis = {}
        error_categories: dict[str, int] = {}
        severity_counts = {"high": 0, "medium": 0, "low": 0}
        affected_files = set()

        for job in failed_jobs:
            trace = await analyzer.get_job_trace(project_id, job.id)
            log_entries = LogParser.extract_log_entries(trace)

            # Enhanced processing with detailed error categorization
            job_errors = []
            job_warnings = []

            for entry in log_entries:
                entry_dict = entry.dict()

                if entry.level == "error":
                    # Add detailed error categorization
                    error_details = LogParser.categorize_error(
                        entry.message, entry.context or ""
                    )

                    # Use source line number if available (for test failures), otherwise use log line number
                    line_number = entry_dict[
                        "line_number"
                    ]  # Default to log line number
                    if "source_line" in error_details:
                        line_number = error_details["source_line"]

                    entry_dict.update(
                        {
                            "line_number": line_number,  # Override with source line if available
                            "category": error_details["category"],
                            "severity": error_details["severity"],
                            "description": error_details["description"],
                            "details": error_details.get(
                                "details", "No specific details available"
                            ),
                            "solution": error_details["solution"],
                            "impact": error_details["impact"],
                        }
                    )

                    # Add test-specific fields if available
                    if "test_function" in error_details:
                        entry_dict["test_function"] = error_details["test_function"]
                    if "source_file" in error_details:
                        entry_dict["source_file"] = error_details["source_file"]
                    if "source_line" in error_details:
                        entry_dict["source_line"] = error_details["source_line"]

                    job_errors.append(entry_dict)

                    # Update global statistics
                    category = error_details["category"]
                    severity = error_details["severity"]
                    error_categories[category] = error_categories.get(category, 0) + 1
                    severity_counts[severity] = severity_counts.get(severity, 0) + 1

                    # Extract file paths from error messages
                    message = entry.message
                    if "would reformat" in message:
                        import re

                        file_match = re.search(r"would reformat (.+)", message)
                        if file_match:
                            affected_files.add(file_match.group(1))

                elif entry.level == "warning":
                    # Add basic categorization for warnings
                    entry_dict.update(
                        {
                            "category": "Warning",
                            "severity": "low",
                            "description": "Potential issue detected",
                            "solution": "Review warning message and consider addressing",
                            "impact": "May cause issues or indicate suboptimal configuration",
                        }
                    )
                    job_warnings.append(entry_dict)

            # Post-process: deduplicate test failures, keeping detailed format over summary
            if job_errors:
                test_failures: dict[
                    str, dict
                ] = {}  # test_function -> error_entry (keeping the best one)
                other_errors = []

                for error in job_errors:
                    if error.get("category") == "Test Failure" and error.get(
                        "test_function"
                    ):
                        test_func = error["test_function"]
                        existing = test_failures.get(test_func)

                        # Keep this error if:
                        # 1. We don't have one for this test yet, OR
                        # 2. This one has source_line and the existing doesn't
                        if not existing or (
                            "source_line" in error and "source_line" not in existing
                        ):
                            test_failures[test_func] = error
                    else:
                        other_errors.append(error)

                # Rebuild job_errors with deduplicated test failures
                job_errors = other_errors + list(test_failures.values())

            analysis[job.name] = {
                "errors": job_errors,
                "warnings": job_warnings,
                "job_info": {
                    "stage": job.stage,
                    "status": job.status,
                    "duration": getattr(job, "duration", None),
                },
            }

        # Create summary (without total job count for efficiency)
        total_errors = sum(
            len(job_analysis["errors"]) for job_analysis in analysis.values()
        )
        total_warnings = sum(
            len(job_analysis["warnings"]) for job_analysis in analysis.values()
        )

        summary = {
            "pipeline_id": pipeline_id,
            "pipeline_status": pipeline["status"],
            "failed_jobs_count": len(failed_jobs),
            "total_errors": total_errors,
            "total_warnings": total_warnings,
            "failed_stages": list({job.stage for job in failed_jobs}),
            "analysis_timestamp": datetime.now().isoformat(),
            "affected_files": sorted(affected_files) if affected_files else [],
            "formatting_files_count": len(affected_files),
            "error_summary": {
                "categories": error_categories,
                "severity_breakdown": severity_counts,
                "most_common_category": (
                    max(error_categories.items(), key=lambda x: x[1])[0]
                    if error_categories
                    else None
                ),
                "critical_issues": severity_counts["high"],
                "needs_attention": severity_counts["high"] + severity_counts["medium"],
            },
        }

        result = {
            "pipeline_id": pipeline_id,
            "pipeline_status": pipeline["status"],
            "pipeline_url": pipeline["web_url"],
            "failed_jobs": [job.dict() for job in failed_jobs],
            "analysis": analysis,
            "summary": summary,
        }

        return result

    except (httpx.HTTPError, httpx.RequestError, ValueError, KeyError) as e:
        return {
            "error": f"Failed to analyze pipeline {pipeline_id}: {str(e)}",
            "pipeline_id": pipeline_id,
        }
