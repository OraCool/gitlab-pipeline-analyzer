"""
Job Analysis Tools for MCP Server

This module provides tools for analyzing individual GitLab CI/CD jobs independently,
without requiring full pipeline analysis.

Copyright (c) 2025 Siarhei Skuratovich
Licensed under the MIT License - see LICENSE file for details
"""

import time
from typing import Any

from fastmcp import FastMCP

from gitlab_analyzer.cache.mcp_cache import get_cache_manager
from gitlab_analyzer.core.analysis import store_job_analysis_step
from gitlab_analyzer.utils.debug import debug_print, error_print, verbose_debug_print
from gitlab_analyzer.utils.utils import get_gitlab_analyzer, get_mcp_info


async def analyze_job_trace(
    project_id: str | int,
    job_id: int,
    trace_content: str,
    job_name: str = "",
    job_stage: str = "",
    exclude_file_patterns: list[str] | None = None,
    disable_file_filtering: bool = False,
    store_in_db: bool = True,
    pipeline_id: int = 0,
) -> dict[str, Any]:
    """Analyze job trace and extract errors using enhanced parsing logic"""
    try:
        from gitlab_analyzer.core.analysis import parse_job_logs

        cache_manager = get_cache_manager()

        # Use enhanced parsing logic from analysis.py with auto-detection
        parsed_result = parse_job_logs(
            trace_content=trace_content,
            parser_type="auto",
            job_name=job_name,  # Use actual job name for proper pytest detection
            job_stage=job_stage,  # Use actual job stage for proper pytest detection
            include_traceback=True,
            exclude_paths=exclude_file_patterns,
        )

        debug_print(
            f"🔧 Enhanced parsing result: {parsed_result.get('parser_type', 'unknown')} parser"
        )

        # Convert to expected format
        errors = parsed_result.get("errors", [])

        # Ensure all errors have required fields for storage
        standardized_errors = []
        for error in errors:
            standardized_error = {
                "exception_type": error.get("exception_type", "unknown"),
                "exception_message": error.get("message", ""),
                "file_path": error.get("test_file") or error.get("file_path", ""),
                "line_number": error.get("line_number"),
                "test_function": error.get("test_function", ""),
                "test_name": error.get("test_name", ""),
                "traceback": error.get("traceback", []),
                "error_context": parsed_result.get("parser_type", "unknown"),
                "job_id": job_id,
            }
            standardized_errors.append(standardized_error)

        analysis_data = {
            "errors": standardized_errors,
            "parser_type": parsed_result.get("parser_type", "unknown"),
            "total_errors": len(standardized_errors),
            "files_with_errors": len(
                {e["file_path"] for e in standardized_errors if e["file_path"]}
            ),
            "parsing_metadata": {
                "error_count": parsed_result.get("error_count", 0),
                "warning_count": parsed_result.get("warning_count", 0),
                "test_summary": parsed_result.get("test_summary"),
                "fallback_reason": parsed_result.get("fallback_reason"),
            },
        }

        # Store analysis if requested
        if store_in_db:
            await store_job_analysis_step(
                cache_manager=cache_manager,
                project_id=project_id,
                pipeline_id=pipeline_id,  # Use the correct pipeline_id
                job_id=job_id,
                job={"id": job_id},  # Minimal job object
                trace_content=trace_content,
                analysis_data=analysis_data,
            )

        return analysis_data

    except Exception as e:
        error_print(f"❌ Error analyzing job trace: {e}")
        return {
            "errors": [],
            "parser_type": "error",
            "total_errors": 0,
            "files_with_errors": 0,
            "error": str(e),
        }


def _should_use_pytest_parser(trace_content: str) -> bool:
    """Determine if pytest parser should be used based on trace content"""
    # Use the enhanced detection from analysis.py
    from gitlab_analyzer.core.analysis import is_pytest_job

    return is_pytest_job(trace_content=trace_content)


def register_job_analysis_tools(mcp: FastMCP) -> None:
    """Register job analysis tools"""

    async def _analyze_job_core(
        project_id: str | int,
        job_id: int,
        store_in_db: bool = True,
        exclude_file_patterns: list[str] | None = None,
        disable_file_filtering: bool = False,
    ) -> dict[str, Any]:
        """Core job analysis logic shared between tools"""
        start_time = time.time()
        try:
            analyzer = get_gitlab_analyzer()
            cache_manager = get_cache_manager()

            # First check if job is already in database
            existing_job_info = await cache_manager.get_job_info_async(job_id)
            if existing_job_info and not store_in_db:
                debug_print(f"✅ Job {job_id} already analyzed, using cached data")
                # Return cached analysis without re-running API calls
                file_errors = cache_manager.get_job_errors(job_id)
                return {
                    "job_info": existing_job_info,
                    "analysis_summary": {
                        "total_errors": len(file_errors),
                        "files_with_errors": len(
                            {
                                e.get("file_path")
                                for e in file_errors
                                if e.get("file_path")
                            }
                        ),
                        "analysis_type": "individual_job",
                        "source": "cached_data",
                    },
                    "error_statistics": {"cached": True},
                    "resource_links": [
                        {
                            "type": "resource_link",
                            "resourceUri": f"gl://job/{project_id}/{existing_job_info.get('pipeline_id', 'unknown')}/{job_id}",
                            "text": f"View complete job analysis for {existing_job_info.get('name', job_id)}",
                        },
                        {
                            "type": "resource_link",
                            "resourceUri": f"gl://errors/{project_id}/{job_id}",
                            "text": f"View all errors in job {existing_job_info.get('name', job_id)}",
                        },
                    ],
                    "mcp_info": get_mcp_info("analyze_job"),
                    "debug_timing": {
                        "duration_seconds": round(time.time() - start_time, 3)
                    },
                }

            # Get job information from GitLab
            debug_print(f"📥 Fetching job info from GitLab for job {job_id}...")
            job_info = await analyzer.get_job_info(project_id, job_id)

            if not job_info:
                error_print(f"❌ Job {job_id} not found in project {project_id}")
                return {
                    "error": "job_not_found",
                    "message": f"Job {job_id} not found in project {project_id}",
                    "project_id": str(project_id),
                    "job_id": job_id,
                    "mcp_info": get_mcp_info("analyze_job", error=True),
                    "debug_timing": {
                        "duration_seconds": round(time.time() - start_time, 3)
                    },
                }

            verbose_debug_print(
                f"✅ Job info retrieved: {job_info.get('name', 'unnamed')} - {job_info.get('status', 'unknown')}"
            )

            # Get job trace
            debug_print(f"📥 Fetching job trace from GitLab for job {job_id}...")
            trace_content = await analyzer.get_job_trace(project_id, job_id)

            if not trace_content:
                debug_print(f"⚠️ No trace found for job {job_id}")
                trace_content = ""

            trace_length = len(trace_content)
            verbose_debug_print(f"📊 Trace retrieved: {trace_length} characters")

            # Store basic job info in database if requested
            if store_in_db:
                debug_print("💾 Job info will be stored during analysis...")
                # Note: Job info is stored during analyze_job_trace via store_job_analysis
                verbose_debug_print("✅ Job will be stored during trace analysis")

            # Analyze job trace for errors
            debug_print("🔍 Analyzing job trace for errors...")
            # Extract pipeline_id from job info for proper database storage
            pipeline_id = job_info.get("pipeline", {}).get("id", 0)
            debug_print(f"📋 Using pipeline_id: {pipeline_id}")

            analysis_result = await analyze_job_trace(
                project_id=project_id,
                job_id=job_id,
                trace_content=trace_content,
                job_name=job_info.get("name", ""),
                job_stage=job_info.get("stage", ""),
                exclude_file_patterns=exclude_file_patterns or [],
                disable_file_filtering=disable_file_filtering,
                store_in_db=store_in_db,
                pipeline_id=pipeline_id,  # Pass the correct pipeline_id
            )

            verbose_debug_print(
                f"📊 Analysis complete: {analysis_result.get('total_errors', 0)} errors found"
            )

            # Build comprehensive result
            result = {
                "job_info": {
                    "job_id": job_id,
                    "project_id": str(project_id),
                    "name": job_info.get("name"),
                    "stage": job_info.get("stage"),
                    "status": job_info.get("status"),
                    "pipeline_id": job_info.get("pipeline", {}).get("id"),
                    "web_url": job_info.get("web_url"),
                    "failure_reason": job_info.get("failure_reason"),
                    "duration": job_info.get("duration"),
                },
                "analysis_summary": {
                    "total_errors": analysis_result.get("total_errors", 0),
                    "files_with_errors": analysis_result.get("files_with_errors", 0),
                    "trace_length": trace_length,
                    "analysis_type": "individual_job",
                    "filtering_enabled": not disable_file_filtering,
                    "excluded_patterns": exclude_file_patterns or [],
                },
                "error_statistics": analysis_result.get("error_statistics", {}),
                "resource_links": [
                    {
                        "type": "resource_link",
                        "resourceUri": f"gl://job/{project_id}/{job_info.get('pipeline', {}).get('id', 'unknown')}/{job_id}",
                        "text": f"View complete job analysis for {job_info.get('name', job_id)}",
                    },
                    {
                        "type": "resource_link",
                        "resourceUri": f"gl://errors/{project_id}/{job_id}",
                        "text": f"View all errors in job {job_info.get('name', job_id)}",
                    },
                ],
                "mcp_info": get_mcp_info("analyze_job"),
            }

            # Add files resource link if there are files with errors
            if analysis_result.get("files_with_errors", 0) > 0:
                result["resource_links"].append(
                    {
                        "type": "resource_link",
                        "resourceUri": f"gl://files/{project_id}/{job_id}",
                        "text": f"Browse {analysis_result['files_with_errors']} files with errors in job {job_info.get('name', job_id)}",
                    }
                )

            # Add pipeline context if available
            pipeline_id = job_info.get("pipeline", {}).get("id")
            if pipeline_id:
                result["resource_links"].append(
                    {
                        "type": "resource_link",
                        "resourceUri": f"gl://pipeline/{project_id}/{pipeline_id}",
                        "text": f"View pipeline {pipeline_id} containing this job",
                    }
                )

            # Add timing information
            end_time = time.time()
            duration = end_time - start_time
            result["debug_timing"] = {"duration_seconds": round(duration, 3)}
            debug_print(f"✅ Job analysis completed in {duration:.3f}s")

            return result

        except Exception as e:
            end_time = time.time()
            duration = end_time - start_time
            error_print(f"❌ Error analyzing job {job_id} after {duration:.3f}s: {e}")
            return {
                "error": "analysis_failed",
                "message": f"Failed to analyze job {job_id}: {str(e)}",
                "project_id": str(project_id),
                "job_id": job_id,
                "mcp_info": get_mcp_info("analyze_job", error=True),
                "debug_timing": {"duration_seconds": round(duration, 3)},
            }

    @mcp.tool
    async def analyze_job(
        project_id: str | int,
        job_id: int,
        store_in_db: bool = True,
        exclude_file_patterns: list[str] | None = None,
        disable_file_filtering: bool = False,
    ) -> dict[str, Any]:
        """
        🔍 JOB ANALYSIS: Analyze a specific GitLab CI/CD job independently.

        WHEN TO USE:
        - Need to analyze a specific job without analyzing the entire pipeline
        - Want detailed error analysis for a single job
        - Investigating job-specific failures
        - Need to store job data for resource access

        FEATURES:
        - Analyzes job trace and extracts errors
        - Stores results in database for resource access
        - Supports file filtering to reduce noise
        - Provides structured error and failure analysis
        - Creates resource URIs for detailed investigation

        Args:
            project_id: The GitLab project ID or path
            job_id: The ID of the GitLab job to analyze
            store_in_db: Whether to store results in database for resources
            exclude_file_patterns: Additional file path patterns to exclude beyond defaults.
                                 Examples: ["migrations/", "node_modules/", "vendor/"]
                                 These are combined with default system paths like .venv, site-packages, etc.
            disable_file_filtering: If True, disables all file filtering including defaults.
                                  When True, all errors from all files (including system files) are included.
                                  Useful for comprehensive debugging or when you need to see everything.

        Returns:
            Job analysis with error parsing, statistics, and resource URIs

        WORKFLOW: Primary job analysis tool → use resources for specific data access

        EXAMPLES:
        - analyze_job(123, 76474172) - Analyze specific job
        - analyze_job(123, 76474172, exclude_file_patterns=["node_modules/"]) - Exclude patterns
        - analyze_job(123, 76474172, disable_file_filtering=True) - Include all files
        """
        debug_print(
            f"🔍 Starting job analysis for job {job_id} in project {project_id}"
        )
        verbose_debug_print(
            f"📋 Job analysis options: store_in_db={store_in_db}, "
            f"exclude_patterns={exclude_file_patterns}, disable_filtering={disable_file_filtering}"
        )

        return await _analyze_job_core(
            project_id=project_id,
            job_id=job_id,
            store_in_db=store_in_db,
            exclude_file_patterns=exclude_file_patterns,
            disable_file_filtering=disable_file_filtering,
        )

    @mcp.tool
    async def analyze_job_with_pipeline_context(
        project_id: str | int,
        pipeline_id: int,
        job_id: int,
        store_in_db: bool = True,
        exclude_file_patterns: list[str] | None = None,
        disable_file_filtering: bool = False,
    ) -> dict[str, Any]:
        """
        🔍 JOB ANALYSIS WITH CONTEXT: Analyze a job with full pipeline context.

        WHEN TO USE:
        - Need to analyze a job with pipeline information
        - Want to store both job and pipeline context
        - Analyzing a job as part of pipeline investigation
        - Need complete context for error correlation

        This tool analyzes a specific job but also stores pipeline context information,
        making it useful when you know both the pipeline and job IDs.

        Args:
            project_id: The GitLab project ID or path
            pipeline_id: The ID of the GitLab pipeline containing the job
            job_id: The ID of the GitLab job to analyze
            store_in_db: Whether to store results in database for resources
            exclude_file_patterns: Additional file path patterns to exclude beyond defaults
            disable_file_filtering: If True, disables all file filtering including defaults

        Returns:
            Job analysis with pipeline context and error parsing

        EXAMPLES:
        - analyze_job_with_pipeline_context(123, 1594344, 76474172) - Analyze job with pipeline context
        """
        start_time = time.time()
        debug_print(
            f"🔍 Starting job analysis with pipeline context: pipeline {pipeline_id}, job {job_id}"
        )

        try:
            # First get pipeline info for context
            analyzer = get_gitlab_analyzer()
            cache_manager = get_cache_manager()

            debug_print("📥 Fetching pipeline info for context...")
            pipeline_info = await analyzer.get_pipeline(project_id, pipeline_id)

            # Store pipeline info if requested
            if store_in_db and pipeline_info:
                debug_print("💾 Storing pipeline context in database...")
                await cache_manager.store_pipeline_info_async(
                    project_id=project_id,
                    pipeline_id=pipeline_id,
                    pipeline_info={
                        "pipeline_info": pipeline_info,
                        "pipeline_type": "branch",  # Default type
                    },
                )
                verbose_debug_print("✅ Pipeline context stored")

            # Analyze the job using the core function
            job_result = await _analyze_job_core(
                project_id=project_id,
                job_id=job_id,
                store_in_db=store_in_db,
                exclude_file_patterns=exclude_file_patterns,
                disable_file_filtering=disable_file_filtering,
            )

            # Add pipeline context to the result
            if "error" not in job_result and pipeline_info:
                job_result["pipeline_context"] = {
                    "pipeline_id": pipeline_id,
                    "status": pipeline_info.get("status"),
                    "ref": pipeline_info.get("ref"),
                    "source_branch": pipeline_info.get("source_branch"),
                    "target_branch": pipeline_info.get("target_branch"),
                    "web_url": pipeline_info.get("web_url"),
                }

                # Update job info with pipeline ID
                if "job_info" in job_result:
                    job_result["job_info"]["pipeline_id"] = pipeline_id

            # Update timing
            end_time = time.time()
            duration = end_time - start_time
            if "debug_timing" in job_result:
                job_result["debug_timing"]["duration_seconds"] = round(duration, 3)

            debug_print(
                f"✅ Job analysis with pipeline context completed in {duration:.3f}s"
            )
            return job_result

        except Exception as e:
            end_time = time.time()
            duration = end_time - start_time
            error_print(
                f"❌ Error analyzing job {job_id} with pipeline context after {duration:.3f}s: {e}"
            )
            return {
                "error": "analysis_failed",
                "message": f"Failed to analyze job {job_id} with pipeline context: {str(e)}",
                "project_id": str(project_id),
                "pipeline_id": pipeline_id,
                "job_id": job_id,
                "mcp_info": get_mcp_info(
                    "analyze_job_with_pipeline_context", error=True
                ),
                "debug_timing": {"duration_seconds": round(duration, 3)},
            }
