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
from gitlab_analyzer.version import get_version

from .utils import get_gitlab_analyzer


def register_info_tools(mcp: FastMCP) -> None:
    """Register pipeline and job information tools"""

    @mcp.tool
    async def get_pipeline_jobs(
        project_id: str | int, pipeline_id: int
    ) -> dict[str, Any]:
        """
        📋 INVENTORY: Get complete job list for pipeline with status and metadata.

        WHEN TO USE:
        - Need overview of all jobs in a pipeline (passed, failed, skipped)
        - Want to understand pipeline structure and job organization
        - Looking for specific job names or stages before detailed analysis

        WHAT YOU GET:
        - Complete list of all jobs with names, status, and stage information
        - Job counts and pipeline structure overview
        - Basic metadata for each job (ID, duration, etc.)

        AI ANALYSIS TIPS:
        - Filter by "status" field to find failed jobs quickly
        - Check "stage" field to understand pipeline phases
        - Use job "name" patterns to identify test vs build vs deploy jobs
        - Look at job counts for pipeline complexity assessment

        Args:
            project_id: The GitLab project ID or path
            pipeline_id: The ID of the GitLab pipeline

        Returns:
            List of all jobs in the pipeline with their status and details

        WORKFLOW: Use for job discovery → leads to analyze_single_job for specific failures
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
                "mcp_info": {
                    "name": "GitLab Pipeline Analyzer",
                    "version": get_version(),
                    "tool_used": "get_pipeline_jobs",
                },
            }

        except (httpx.HTTPError, httpx.RequestError, ValueError, KeyError) as e:
            return {
                "error": f"Failed to get pipeline jobs: {str(e)}",
                "project_id": str(project_id),
                "pipeline_id": pipeline_id,
                "mcp_info": {
                    "name": "GitLab Pipeline Analyzer",
                    "version": get_version(),
                    "tool_used": "get_pipeline_jobs",
                    "error": True,
                },
            }

    @mcp.tool
    async def get_failed_jobs(
        project_id: str | int, pipeline_id: int
    ) -> dict[str, Any]:
        """
        🚨 FILTER: Get only failed jobs for focused failure analysis.

        WHEN TO USE:
        - Pipeline has many jobs but you only want to see failures
        - Need quick list of problematic jobs without full pipeline analysis
        - Want to count and categorize failed jobs

        WHAT YOU GET:
        - Filtered list containing only failed jobs
        - Failed job count for quick assessment
        - Job details for each failure (name, stage, etc.)

        AI ANALYSIS TIPS:
        - Use for quick failure count and job identification
        - Check job names for patterns (test failures vs build failures)
        - Look at stages to understand where in pipeline failures occur
        - Combine with analyze_single_job for detailed failure analysis

        Args:
            project_id: The GitLab project ID or path
            pipeline_id: The ID of the GitLab pipeline

        Returns:
            List of failed jobs with their details

        WORKFLOW: Alternative to get_pipeline_jobs when only failures matter → analyze_single_job
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
                "mcp_info": {
                    "name": "GitLab Pipeline Analyzer",
                    "version": get_version(),
                    "tool_used": "get_failed_jobs",
                },
            }

        except (httpx.HTTPError, httpx.RequestError, ValueError, KeyError) as e:
            return {
                "error": f"Failed to get failed jobs: {str(e)}",
                "project_id": str(project_id),
                "pipeline_id": pipeline_id,
                "mcp_info": {
                    "name": "GitLab Pipeline Analyzer",
                    "version": get_version(),
                    "tool_used": "get_failed_jobs",
                    "error": True,
                },
            }

    @mcp.tool
    async def get_job_trace(project_id: str | int, job_id: int) -> dict[str, Any]:
        """
        📝 RAW ACCESS: Get unprocessed job trace with ANSI formatting intact.

        WHEN TO USE:
        - Need to see original job output exactly as it appeared
        - Debugging ANSI formatting or color issues
        - Want complete raw log before any processing

        WHAT YOU GET:
        - Complete raw job trace including ANSI codes
        - Trace length information
        - Unmodified output as seen in GitLab UI

        AI ANALYSIS TIPS:
        - Use get_cleaned_job_trace instead for better readability
        - This tool preserves original formatting but may be harder to parse
        - Good for debugging if cleaned version seems missing information

        Args:
            project_id: The GitLab project ID or path
            job_id: The ID of the GitLab job

        Returns:
            The complete trace log for the job

        WORKFLOW: Rarely used → prefer get_cleaned_job_trace for most analysis
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
                "mcp_info": {
                    "name": "GitLab Pipeline Analyzer",
                    "version": get_version(),
                    "tool_used": "get_job_trace",
                },
            }

        except (httpx.HTTPError, httpx.RequestError, ValueError, KeyError) as e:
            return {
                "error": f"Failed to get job trace: {str(e)}",
                "project_id": str(project_id),
                "job_id": job_id,
                "mcp_info": {
                    "name": "GitLab Pipeline Analyzer",
                    "version": get_version(),
                    "tool_used": "get_job_trace",
                    "error": True,
                },
            }

    @mcp.tool
    async def get_cleaned_job_trace(
        project_id: str | int, job_id: int
    ) -> dict[str, Any]:
        """
        📋 RAW LOGS: Get clean, readable job traces without ANSI formatting for detailed analysis.

        WHEN TO USE:
        - Need to see complete job execution log
        - Other tools don't provide enough context
        - Looking for specific error patterns or debugging complex issues
        - Want to perform custom log analysis

        WHAT YOU GET:
        - Complete job trace with ANSI codes removed
        - Character counts and cleaning statistics
        - Human-readable format suitable for AI analysis

        AI ANALYSIS TIPS:
        - Use when specific error patterns aren't caught by specialized parsers
        - Look for error keywords: "ERROR", "FAILED", "Exception", "Traceback"
        - Search for setup/teardown issues that happen outside main execution
        - Check for environment or dependency problems

        Args:
            project_id: The GitLab project ID or path
            job_id: The ID of the GitLab job

        Returns:
            The cleaned trace log (without ANSI codes) and cleaning statistics

        WORKFLOW: Use when analyze_single_job needs more detail → provides complete execution context
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
                "ansi_sequences_found": len(ansi_matches),  # Change back to "found"
                "unique_ansi_types": len(ansi_types),
                "analysis_timestamp": datetime.now().isoformat(),
                "mcp_info": {
                    "name": "GitLab Pipeline Analyzer",
                    "version": get_version(),
                    "tool_used": "get_cleaned_job_trace",
                },
            }

        except (httpx.HTTPError, httpx.RequestError, ValueError, KeyError) as e:
            return {
                "error": f"Failed to get cleaned job trace: {str(e)}",
                "project_id": str(project_id),
                "job_id": job_id,
                "mcp_info": {
                    "name": "GitLab Pipeline Analyzer",
                    "version": get_version(),
                    "tool_used": "get_cleaned_job_trace",
                    "error": True,
                },
            }

    @mcp.tool
    async def get_pipeline_status(
        project_id: str | int, pipeline_id: int
    ) -> dict[str, Any]:
        """
        📊 OVERVIEW: Get pipeline status and basic information for quick assessment.

        WHEN TO USE:
        - Need quick pipeline health check
        - Want to verify pipeline state before detailed analysis
        - User asks "what's the status of pipeline X?"

        WHAT YOU GET:
        - Pipeline status (success, failed, running, etc.)
        - Basic metadata (ID, ref, commit SHA, created/updated times)
        - Duration and execution details
        - Web URL for browser access

        AI ANALYSIS TIPS:
        - Check "status" field first: "failed" = needs investigation
        - Use "duration" to assess if timeouts might be involved
        - Compare "created_at" vs "updated_at" for execution time
        - Use "web_url" to provide users with direct access link

        Args:
            project_id: The GitLab project ID or path
            pipeline_id: The ID of the GitLab pipeline

        Returns:
            Pipeline status and basic information

        WORKFLOW: Start here for pipeline investigations → leads to analyze_failed_pipeline if needed
        """
        try:
            analyzer = get_gitlab_analyzer()
            status = await analyzer.get_pipeline(project_id, pipeline_id)

            return {
                "project_id": str(project_id),
                "pipeline_id": pipeline_id,
                "pipeline": status,  # Change from "status" to "pipeline" to match test expectation
                "analysis_timestamp": datetime.now().isoformat(),
                "mcp_info": {
                    "name": "GitLab Pipeline Analyzer",
                    "version": get_version(),
                    "tool_used": "get_pipeline_status",
                },
            }

        except (httpx.HTTPError, httpx.RequestError, ValueError, KeyError) as e:
            return {
                "error": f"Failed to get pipeline status: {str(e)}",
                "project_id": str(project_id),
                "pipeline_id": pipeline_id,
                "mcp_info": {
                    "name": "GitLab Pipeline Analyzer",
                    "version": get_version(),
                    "tool_used": "get_pipeline_status",
                    "error": True,
                },
            }

    @mcp.tool
    async def get_pipeline_info(
        project_id: str | int, pipeline_id: int
    ) -> dict[str, Any]:
        """
        📊 INFO: Get comprehensive pipeline information and metadata.

        WHEN TO USE:
        - Need detailed pipeline information including all metadata
        - Want comprehensive pipeline overview before analysis
        - User asks for "pipeline info" or "pipeline details"

        WHAT YOU GET:
        - Complete pipeline information and metadata
        - Pipeline status, timing, and execution details
        - Git reference information (branch, commit, etc.)
        - Web URLs and direct access links
        - Original branch information extracted from pipeline ref

        AI ANALYSIS TIPS:
        - Check "status" field for pipeline state assessment
        - Use "duration" and timing fields for performance analysis
        - Check "ref" and "sha" for git context
        - Use "web_url" to provide users with direct access
        - Use "original_branch" for branch-specific operations

        Args:
            project_id: The GitLab project ID or path
            pipeline_id: The ID of the GitLab pipeline

        Returns:
            Comprehensive pipeline information and metadata

        WORKFLOW: Use for detailed pipeline information → leads to job-specific analysis if needed
        """
        try:
            analyzer = get_gitlab_analyzer()
            pipeline_info = await analyzer.get_pipeline(project_id, pipeline_id)

            # Extract original branch from pipeline ref
            original_branch = pipeline_info.get("ref", "main")

            return {
                "project_id": str(project_id),
                "pipeline_id": pipeline_id,
                "pipeline_info": pipeline_info,
                "original_branch": original_branch,
                "analysis_timestamp": datetime.now().isoformat(),
                "mcp_info": {
                    "name": "GitLab Pipeline Analyzer",
                    "version": get_version(),
                    "tool_used": "get_pipeline_info",
                },
            }

        except (httpx.HTTPError, httpx.RequestError, ValueError, KeyError) as e:
            return {
                "error": f"Failed to get pipeline info: {str(e)}",
                "project_id": str(project_id),
                "pipeline_id": pipeline_id,
                "mcp_info": {
                    "name": "GitLab Pipeline Analyzer",
                    "version": get_version(),
                    "tool_used": "get_pipeline_info",
                    "error": True,
                },
            }
