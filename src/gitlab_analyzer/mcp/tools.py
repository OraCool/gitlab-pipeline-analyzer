"""
MCP tool functions for GitLab Pipeline Analyzer
"""

import os
from datetime import datetime
from typing import Any, Dict, Union
import httpx
from fastmcp import FastMCP

from ..api.client import GitLabAnalyzer
from ..parsers.log_parser import LogParser


# GitLab analyzer singleton instance
_gitlab_analyzer = None


def get_gitlab_analyzer() -> GitLabAnalyzer:
    """Get or create GitLab analyzer instance"""
    global _gitlab_analyzer  # pylint: disable=global-statement

    if _gitlab_analyzer is None:
        gitlab_url = os.getenv("GITLAB_URL", "https://gitlab.com")
        gitlab_token = os.getenv("GITLAB_TOKEN")

        if not gitlab_token:
            raise ValueError("GITLAB_TOKEN environment variable is required")

        _gitlab_analyzer = GitLabAnalyzer(gitlab_url, gitlab_token)

    return _gitlab_analyzer


def register_tools(mcp: FastMCP):
    """Register all MCP tools"""

    @mcp.tool
    async def analyze_failed_pipeline(
        project_id: Union[str, int], pipeline_id: int
    ) -> Dict[str, Any]:
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
    async def analyze_single_job(
        project_id: Union[str, int], job_id: int
    ) -> Dict[str, Any]:
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

            # Categorize entries
            errors = [entry.dict() for entry in log_entries if entry.level == "error"]
            warnings = [
                entry.dict() for entry in log_entries if entry.level == "warning"
            ]

            # Get job URL (construct based on GitLab URL pattern)
            analyzer_instance = get_gitlab_analyzer()
            job_url = f"{analyzer_instance.gitlab_url}/-/jobs/{job_id}"

            result = {
                "project_id": str(project_id),
                "job_id": job_id,
                "job_url": job_url,
                "analysis": {"errors": errors, "warnings": warnings},
                "summary": {
                    "total_errors": len(errors),
                    "total_warnings": len(warnings),
                    "total_log_entries": len(log_entries),
                    "has_trace": bool(trace.strip()),
                    "trace_length": len(trace),
                    "analysis_timestamp": datetime.now().isoformat(),
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
        project_id: Union[str, int], pipeline_id: int
    ) -> Dict[str, Any]:
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
    async def get_job_trace(project_id: Union[str, int], job_id: int) -> Dict[str, Any]:
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
    async def extract_log_errors(log_text: str) -> Dict[str, Any]:
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
        project_id: Union[str, int], pipeline_id: int
    ) -> Dict[str, Any]:
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
    project_id: Union[str, int], pipeline_id: int
) -> Dict[str, Any]:
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
        for job in failed_jobs:
            trace = await analyzer.get_job_trace(project_id, job.id)
            log_entries = LogParser.extract_log_entries(trace)
            analysis[job.name] = [entry.dict() for entry in log_entries]

        # Create summary (without total job count for efficiency)
        total_errors = sum(
            len([entry for entry in entries if entry["level"] == "error"])
            for entries in analysis.values()
        )
        total_warnings = sum(
            len([entry for entry in entries if entry["level"] == "warning"])
            for entries in analysis.values()
        )

        summary = {
            "pipeline_id": pipeline_id,
            "pipeline_status": pipeline["status"],
            "failed_jobs_count": len(failed_jobs),
            "total_errors": total_errors,
            "total_warnings": total_warnings,
            "failed_stages": list(set(job.stage for job in failed_jobs)),
            "analysis_timestamp": datetime.now().isoformat(),
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
