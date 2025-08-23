"""
Analysis resources for MCP server

Copyright (c) 2025 Siarhei Skuratovich
Licensed under the MIT License - see LICENSE file for details
"""

import json
import logging
from datetime import UTC, datetime

from ..cache import get_cache_manager
from ..tools.utils import get_gitlab_analyzer, get_mcp_info

logger = logging.getLogger(__name__)


async def _get_comprehensive_analysis(
    project_id: str,
    pipeline_id: str | None = None,
    job_id: str | None = None,
    response_mode: str = "balanced",
) -> str:
    """Internal function to get comprehensive analysis with configurable response mode."""
    try:
        cache_manager = get_cache_manager()
        analyzer = get_gitlab_analyzer()

        # Determine analysis scope and create appropriate cache key
        if job_id:
            scope = "job"
            cache_key = f"analysis_{project_id}_{job_id}_{response_mode}"
            resource_uri = (
                f"gl://analysis/{project_id}/job/{job_id}?mode={response_mode}"
            )
        elif pipeline_id:
            scope = "pipeline"
            cache_key = f"analysis_{project_id}_{pipeline_id}_{response_mode}"
            resource_uri = f"gl://analysis/{project_id}/pipeline/{pipeline_id}?mode={response_mode}"
        else:
            scope = "project"
            cache_key = f"analysis_{project_id}_{response_mode}"
            resource_uri = f"gl://analysis/{project_id}?mode={response_mode}"

        # Try to get from cache first
        cached_data = await cache_manager.get(cache_key)
        if cached_data:
            return json.dumps(cached_data, indent=2)

        # Get analysis data based on scope
        analysis_data = {}

        if scope == "job":
            # Single job analysis
            if job_id is None:
                raise ValueError("job_id is required for job scope")
            trace = await analyzer.get_job_trace(project_id, int(job_id))

            from gitlab_analyzer.parsers.log_parser import LogParser

            parser = LogParser()
            log_entries = parser.extract_log_entries(trace)

            errors = [entry for entry in log_entries if entry.level == "error"]
            warnings = [entry for entry in log_entries if entry.level == "warning"]

            analysis_data = {
                "scope": "job",
                "job_id": int(job_id),
                "summary": {
                    "total_log_entries": len(log_entries),
                    "error_count": len(errors),
                    "warning_count": len(warnings),
                    "success": len(errors) == 0,
                },
                "error_analysis": _analyze_errors(errors),
                "warning_analysis": _analyze_warnings(warnings),
                "patterns": _identify_patterns(log_entries),
            }

        elif scope == "pipeline":
            # Pipeline-wide analysis
            if pipeline_id is None:
                raise ValueError("pipeline_id is required for pipeline scope")
            pipeline_info = await analyzer.get_pipeline(project_id, int(pipeline_id))
            jobs = await analyzer.get_pipeline_jobs(project_id, int(pipeline_id))

            failed_jobs = [job for job in jobs if job.status == "failed"]

            analysis_data = {
                "scope": "pipeline",
                "pipeline_id": int(pipeline_id),
                "summary": {
                    "total_jobs": len(jobs),
                    "failed_jobs": len(failed_jobs),
                    "success_rate": (
                        (len(jobs) - len(failed_jobs)) / len(jobs) if jobs else 0
                    ),
                    "status": pipeline_info.get("status"),
                },
                "job_analysis": {
                    "jobs_by_status": _group_jobs_by_status(jobs),
                    "failed_job_details": [
                        {
                            "id": job.id,
                            "name": job.name,
                            "stage": job.stage,
                            "failure_reason": getattr(job, "failure_reason", "unknown"),
                        }
                        for job in failed_jobs
                    ],
                },
                "patterns": _identify_pipeline_patterns(jobs),
            }

        else:
            # Project-level analysis (placeholder for future implementation)
            analysis_data = {
                "scope": "project",
                "summary": {
                    "message": "Project-level analysis not yet implemented",
                    "suggestion": "Use pipeline or job-specific analysis",
                },
            }

        # Process the analysis result
        result = {
            "comprehensive_analysis": {
                "project_id": project_id,
                **analysis_data,
            },
            "resource_uri": resource_uri,
            "cached_at": datetime.now(UTC).isoformat(),
            "metadata": {
                "analysis_scope": scope,
                "source": "multiple_endpoints",
                "response_mode": response_mode,
                "coverage": "comprehensive",
            },
        }

        # Apply response mode optimization
        from ..tools.utils import optimize_tool_response

        result = optimize_tool_response(result, response_mode)

        mcp_info = get_mcp_info(
            tool_used="comprehensive_analysis", error=False, parser_type="resource"
        )

        # Cache the result
        result["mcp_info"] = mcp_info
        await cache_manager.set(
            cache_key,
            result,
            data_type="analysis",
            project_id=project_id,
            job_id=int(job_id) if job_id else None,
            pipeline_id=int(pipeline_id) if pipeline_id else None,
        )

        return json.dumps(result, indent=2)

    except Exception as e:
        logger.error("Error getting analysis resource %s: %s", project_id, e)
        error_result = {
            "error": f"Failed to get analysis resource: {str(e)}",
            "project_id": project_id,
            "resource_uri": (
                resource_uri
                if "resource_uri" in locals()
                else f"gl://analysis/{project_id}"
            ),
        }
        return json.dumps(error_result, indent=2)


def _analyze_errors(errors):
    """Analyze error patterns and provide insights"""
    if not errors:
        return {"message": "No errors found"}

    error_types = {}
    file_errors = {}

    for error in errors:
        error_type = getattr(error, "exception_type", "unknown")
        error_types[error_type] = error_types.get(error_type, 0) + 1

        file_path = getattr(error, "file_path", None) or getattr(
            error, "test_file", None
        )
        if file_path:
            file_errors[str(file_path)] = file_errors.get(str(file_path), 0) + 1

    return {
        "total_errors": len(errors),
        "error_types": error_types,
        "most_common_error": (
            max(error_types.items(), key=lambda x: x[1])[0] if error_types else None
        ),
        "files_with_errors": file_errors,
        "most_problematic_file": (
            max(file_errors.items(), key=lambda x: x[1])[0] if file_errors else None
        ),
    }


def _analyze_warnings(warnings):
    """Analyze warning patterns"""
    if not warnings:
        return {"message": "No warnings found"}

    return {
        "total_warnings": len(warnings),
        "warning_messages": [
            getattr(w, "message", "") for w in warnings[:5]
        ],  # First 5 warnings
    }


def _identify_patterns(log_entries):
    """Identify common patterns in log entries"""
    patterns = []

    # Check for common failure patterns
    messages = [getattr(entry, "message", "") for entry in log_entries]

    if any("timeout" in msg.lower() for msg in messages):
        patterns.append("timeout_issues")
    if any("connection" in msg.lower() for msg in messages):
        patterns.append("connection_issues")
    if any("import" in msg.lower() and "error" in msg.lower() for msg in messages):
        patterns.append("import_errors")
    if any("syntax" in msg.lower() for msg in messages):
        patterns.append("syntax_errors")

    return patterns


def _group_jobs_by_status(jobs):
    """Group jobs by their status"""
    status_groups = {}
    for job in jobs:
        status = job.status if hasattr(job, "status") else "unknown"
        status_groups[status] = status_groups.get(status, 0) + 1
    return status_groups


def _identify_pipeline_patterns(jobs):
    """Identify patterns across pipeline jobs"""
    patterns = []

    # Check for stage-specific failures
    failed_stages = set()
    for job in jobs:
        if hasattr(job, "status") and job.status == "failed":
            stage = job.stage if hasattr(job, "stage") else "unknown"
            failed_stages.add(stage)

    if len(failed_stages) > 1:
        patterns.append("multiple_stage_failures")
    elif len(failed_stages) == 1:
        patterns.append(f"stage_specific_failure_{list(failed_stages)[0]}")

    return patterns


def register_analysis_resources(mcp) -> None:
    """Register analysis resources with MCP server"""

    @mcp.resource("gl://analysis/{project_id}")
    async def get_project_analysis_resource(project_id: str) -> str:
        """
        Get project-level analysis as a resource with caching.

        Args:
            project_id: GitLab project ID

        Returns:
            Project-level analysis with metadata

        Note: Resources provide "balanced" mode by default for optimal agent consumption.
        """
        return await _get_comprehensive_analysis(project_id, response_mode="balanced")

    @mcp.resource("gl://analysis/{project_id}?mode={mode}")
    async def get_project_analysis_resource_with_mode(
        project_id: str, mode: str
    ) -> str:
        """
        Get project-level analysis as a resource with specific response mode.

        Args:
            project_id: GitLab project ID
            mode: Response mode - "minimal", "balanced", "fixing", or "full"

        Returns:
            Project-level analysis optimized for the specified mode
        """
        return await _get_comprehensive_analysis(project_id, response_mode=mode)

    @mcp.resource("gl://analysis/{project_id}/pipeline/{pipeline_id}")
    async def get_pipeline_analysis_resource(project_id: str, pipeline_id: str) -> str:
        """
        Get pipeline-level analysis as a resource with caching.

        Args:
            project_id: GitLab project ID
            pipeline_id: GitLab pipeline ID

        Returns:
            Pipeline-level analysis with metadata
        """
        return await _get_comprehensive_analysis(
            project_id, pipeline_id, response_mode="balanced"
        )

    @mcp.resource("gl://analysis/{project_id}/pipeline/{pipeline_id}?mode={mode}")
    async def get_pipeline_analysis_resource_with_mode(
        project_id: str, pipeline_id: str, mode: str
    ) -> str:
        """
        Get pipeline-level analysis as a resource with specific response mode.

        Args:
            project_id: GitLab project ID
            pipeline_id: GitLab pipeline ID
            mode: Response mode - "minimal", "balanced", "fixing", or "full"

        Returns:
            Pipeline-level analysis optimized for the specified mode
        """
        return await _get_comprehensive_analysis(
            project_id, pipeline_id, response_mode=mode
        )

    @mcp.resource("gl://analysis/{project_id}/job/{job_id}")
    async def get_job_analysis_resource(project_id: str, job_id: str) -> str:
        """
        Get job-level analysis as a resource with caching.

        Args:
            project_id: GitLab project ID
            job_id: GitLab job ID

        Returns:
            Job-level analysis with metadata
        """
        return await _get_comprehensive_analysis(
            project_id, job_id=job_id, response_mode="balanced"
        )

    @mcp.resource("gl://analysis/{project_id}/job/{job_id}?mode={mode}")
    async def get_job_analysis_resource_with_mode(
        project_id: str, job_id: str, mode: str
    ) -> str:
        """
        Get job-level analysis as a resource with specific response mode.

        Args:
            project_id: GitLab project ID
            job_id: GitLab job ID
            mode: Response mode - "minimal", "balanced", "fixing", or "full"

        Returns:
            Job-level analysis optimized for the specified mode
        """
        return await _get_comprehensive_analysis(
            project_id, job_id=job_id, response_mode=mode
        )

    logger.info("Analysis resources registered")
