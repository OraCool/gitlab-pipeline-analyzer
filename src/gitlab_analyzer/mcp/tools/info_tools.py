"""
GitLab pipeline and job information MCP tools

Copyright (c) 2025 Siarhei Skuratovich
Licensed under the MIT License - see LICENSE file for details
"""

from datetime import datetime
from typing import Any

import httpx
from fastmcp import FastMCP

from gitlab_analyzer.parsers.base_parser import BaseParser

from .utils import get_gitlab_analyzer


def register_info_tools(mcp: FastMCP) -> None:
    """Register pipeline and job information tools"""

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
        try:
            analyzer = get_gitlab_analyzer()
            jobs = await analyzer.get_pipeline_jobs(project_id, pipeline_id)

            return {
                "project_id": str(project_id),
                "pipeline_id": pipeline_id,
                "jobs": jobs,
                "job_count": len(jobs),
                "analysis_timestamp": datetime.now().isoformat(),
            }

        except (httpx.HTTPError, httpx.RequestError, ValueError, KeyError) as e:
            return {
                "error": f"Failed to get pipeline jobs: {str(e)}",
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
        try:
            analyzer = get_gitlab_analyzer()
            failed_jobs = await analyzer.get_failed_pipeline_jobs(
                project_id, pipeline_id
            )

            return {
                "project_id": str(project_id),
                "pipeline_id": pipeline_id,
                "failed_jobs": failed_jobs,
                "failed_job_count": len(failed_jobs),
                "analysis_timestamp": datetime.now().isoformat(),
            }

        except (httpx.HTTPError, httpx.RequestError, ValueError, KeyError) as e:
            return {
                "error": f"Failed to get failed jobs: {str(e)}",
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
        try:
            analyzer = get_gitlab_analyzer()
            trace = await analyzer.get_job_trace(project_id, job_id)

            return {
                "project_id": str(project_id),
                "job_id": job_id,
                "trace": trace,
                "trace_length": len(trace),
                "analysis_timestamp": datetime.now().isoformat(),
            }

        except (httpx.HTTPError, httpx.RequestError, ValueError, KeyError) as e:
            return {
                "error": f"Failed to get job trace: {str(e)}",
                "project_id": str(project_id),
                "job_id": job_id,
            }

    @mcp.tool
    async def get_cleaned_job_trace(
        project_id: str | int, job_id: int
    ) -> dict[str, Any]:
        """
        Get the trace log for a specific GitLab CI/CD job with ANSI codes removed.

        This tool fetches the raw job trace and automatically cleans it by removing
        ANSI escape sequences, making it more suitable for automated analysis and
        human reading.

        Args:
            project_id: The GitLab project ID or path
            job_id: The ID of the GitLab job

        Returns:
            The cleaned trace log (without ANSI codes) and cleaning statistics
        """
        try:
            analyzer = get_gitlab_analyzer()

            # Get the raw trace
            raw_trace = await analyzer.get_job_trace(project_id, job_id)

            # Clean ANSI codes using BaseParser
            cleaned_trace = BaseParser.clean_ansi_sequences(raw_trace)

            # Analyze ANSI sequences for statistics
            import re

            ansi_pattern = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")
            ansi_matches = ansi_pattern.findall(raw_trace)

            # Count different types of ANSI sequences
            ansi_types: dict[str, int] = {}
            for match in ansi_matches:
                ansi_types[match] = ansi_types.get(match, 0) + 1

            return {
                "project_id": str(project_id),
                "job_id": job_id,
                "cleaned_trace": cleaned_trace,
                "original_length": len(raw_trace),
                "cleaned_length": len(cleaned_trace),
                "bytes_removed": len(raw_trace) - len(cleaned_trace),
                "ansi_sequences_found": len(ansi_matches),
                "unique_ansi_types": len(ansi_types),
                "analysis_timestamp": datetime.now().isoformat(),
            }

        except (httpx.HTTPError, httpx.RequestError, ValueError, KeyError) as e:
            return {
                "error": f"Failed to get cleaned job trace: {str(e)}",
                "project_id": str(project_id),
                "job_id": job_id,
            }

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
        try:
            analyzer = get_gitlab_analyzer()
            status = await analyzer.get_pipeline(project_id, pipeline_id)

            return {
                "project_id": str(project_id),
                "pipeline_id": pipeline_id,
                "status": status,
                "analysis_timestamp": datetime.now().isoformat(),
            }

        except (httpx.HTTPError, httpx.RequestError, ValueError, KeyError) as e:
            return {
                "error": f"Failed to get pipeline status: {str(e)}",
                "project_id": str(project_id),
                "pipeline_id": pipeline_id,
            }
