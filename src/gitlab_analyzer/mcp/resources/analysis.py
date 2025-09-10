"""
Analysis resources for MCP server

Copyright (c) 2025 Siarhei Skuratovich
Licensed under the MIT License - see LICENSE file for details
"""

import json
import logging
from datetime import datetime, timezone
from typing import Any

from mcp.types import TextResourceContents

from gitlab_analyzer.analysis.error_model import Error
from gitlab_analyzer.analysis.root_cause_analyzer import RootCauseAnalyzer
from gitlab_analyzer.analysis.summarizer import ErrorSummarizer
from gitlab_analyzer.cache.mcp_cache import get_cache_manager
from gitlab_analyzer.mcp.utils.pipeline_validation import check_pipeline_analyzed
from gitlab_analyzer.utils.debug import debug_print, verbose_debug_print
from gitlab_analyzer.utils.utils import get_mcp_info

from .utils import create_text_resource

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
            # Single job analysis using database data
            if job_id is None:
                raise ValueError("job_id is required for job scope")

            # Get job errors and job info from database
            job_errors = cache_manager.get_job_errors(int(job_id))
            job_info = await cache_manager.get_job_info_async(int(job_id))

            analysis_data = {
                "scope": "job",
                "job_id": int(job_id),
                "job_info": job_info,
                "summary": {
                    "error_count": len(job_errors),
                    "success": len(job_errors) == 0,
                    "data_source": "database_only",
                },
                "errors": job_errors,
                "error_analysis": _analyze_database_errors(job_errors),
                "patterns": _identify_error_patterns(job_errors),
            }

        elif scope == "pipeline":
            # Pipeline-wide analysis using database data
            if pipeline_id is None:
                raise ValueError("pipeline_id is required for pipeline scope")

            # Check if pipeline has been analyzed using utility function
            error_response = await check_pipeline_analyzed(
                project_id, str(pipeline_id), "pipeline_analysis"
            )
            if error_response:
                return json.dumps(error_response, indent=2)

            # Get pipeline data from database
            pipeline_info = cache_manager.get_pipeline_info(int(pipeline_id))
            jobs = await cache_manager.get_pipeline_jobs(int(pipeline_id))
            failed_jobs = cache_manager.get_pipeline_failed_jobs(int(pipeline_id))

            analysis_data = {
                "scope": "pipeline",
                "pipeline_id": int(pipeline_id),
                "pipeline_info": pipeline_info,
                "summary": {
                    "total_jobs": len(jobs),
                    "failed_jobs": len(failed_jobs),
                    "success_rate": (
                        (len(jobs) - len(failed_jobs)) / len(jobs) if jobs else 0
                    ),
                    "status": (
                        pipeline_info.get("status") if pipeline_info else "unknown"
                    ),
                    "data_source": "database_only",
                },
                "job_analysis": {
                    "jobs": jobs,
                    "failed_jobs": failed_jobs,
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
            "cached_at": datetime.now(timezone.utc).isoformat(),
            "metadata": {
                "analysis_scope": scope,
                "source": "multiple_endpoints",
                "response_mode": response_mode,
                "coverage": "comprehensive",
            },
        }

        # Apply response mode optimization
        from gitlab_analyzer.utils.utils import optimize_tool_response

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


def _analyze_database_errors(db_errors):
    """Analyze error patterns from database error data"""
    if not db_errors:
        return {"message": "No errors found"}

    error_types = {}
    error_files = set()
    total_errors = len(db_errors)

    for error in db_errors:
        # Count error types
        exception_type = error.get("exception", "UnknownError")
        error_types[exception_type] = error_types.get(exception_type, 0) + 1

        # Track affected files
        if error.get("file_path"):
            error_files.add(error["file_path"])

    return {
        "total_errors": total_errors,
        "unique_error_types": len(error_types),
        "error_types": error_types,
        "most_common_error": (
            max(error_types.items(), key=lambda x: x[1])[0] if error_types else None
        ),
        "affected_files": list(error_files),
        "affected_file_count": len(error_files),
        "errors_per_file": total_errors / len(error_files) if error_files else 0,
    }


def _identify_error_patterns(db_errors):
    """Identify common patterns in database error data"""
    patterns = []

    if not db_errors:
        return patterns

    # Check for common failure patterns based on exception types
    exception_counts = {}
    for error in db_errors:
        exception_type = error.get("exception", "")
        exception_counts[exception_type] = exception_counts.get(exception_type, 0) + 1

    # Identify patterns
    for exception_type, count in exception_counts.items():
        if count > 1:
            patterns.append(f"Multiple {exception_type} errors ({count} occurrences)")

    # Check for file-specific patterns
    file_errors = {}
    for error in db_errors:
        file_path = error.get("file_path", "")
        if file_path:
            file_errors[file_path] = file_errors.get(file_path, 0) + 1

    for file_path, count in file_errors.items():
        if count > 1:
            patterns.append(f"Multiple errors in {file_path} ({count} errors)")

    return patterns


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


async def get_analysis_resource_data(
    project_id: str,
    pipeline_id: str | None = None,
    job_id: str | None = None,
    mode: str = "balanced",
) -> dict[str, Any]:
    """
    Get analysis resource data (standalone function for resource access tool)

    Args:
        project_id: GitLab project ID
        pipeline_id: Pipeline ID (optional)
        job_id: Job ID (optional)
        mode: Response mode (minimal, balanced, detailed, etc.)

    Returns:
        Analysis data as dict
    """
    try:
        result_json = await _get_comprehensive_analysis(
            project_id, pipeline_id, job_id, mode
        )
        return json.loads(result_json)
    except Exception as e:
        logger.error(
            "Error getting analysis resource data %s/%s/%s: %s",
            project_id,
            pipeline_id,
            job_id,
            e,
        )
        uri_parts = [f"gl://analysis/{project_id}"]
        if pipeline_id:
            uri_parts.append(f"pipeline/{pipeline_id}")
        if job_id:
            uri_parts.append(f"job/{job_id}")

        resource_uri = "/".join(uri_parts)
        if mode != "balanced":
            resource_uri += f"?mode={mode}"

        return {
            "error": f"Failed to get analysis resource: {str(e)}",
            "project_id": project_id,
            "pipeline_id": pipeline_id,
            "job_id": job_id,
            "resource_uri": resource_uri,
        }


def _filter_root_causes(
    root_causes: list[dict],
    limit: int | None = None,
    severity_filter: str | None = None,
    category_filter: str | None = None,
    min_confidence: float | None = None,
) -> list[dict]:
    """Filter and limit root causes based on specified criteria."""
    filtered = root_causes.copy()

    # Apply confidence filter
    if min_confidence is not None:
        filtered = [
            cause for cause in filtered if cause.get("confidence", 0) >= min_confidence
        ]

    # Apply severity filter
    if severity_filter:
        severity_filter = severity_filter.lower()
        filtered = [
            cause
            for cause in filtered
            if cause.get("pattern", {}).get("severity", "").lower() == severity_filter
        ]

    # Apply category filter
    if category_filter:
        filtered = [
            cause
            for cause in filtered
            if category_filter.lower()
            in cause.get("pattern", {}).get("category", "").lower()
        ]

    # Apply limit
    if limit and limit > 0:
        filtered = filtered[:limit]

    return filtered


async def _get_job_root_cause_analysis(
    project_id: str,
    job_id: str,
    response_mode: str = "minimal",
    limit: int | None = None,
    severity_filter: str | None = None,
    category_filter: str | None = None,
    min_confidence: float | None = None,
) -> str:
    """
    Internal function to get job-specific root cause analysis with filtering options.

    Args:
        project_id: GitLab project ID
        job_id: GitLab job ID
        response_mode: Response optimization mode
        limit: Maximum number of root causes to return
        severity_filter: Filter by severity level
        category_filter: Filter by category
        min_confidence: Minimum confidence threshold

    Returns:
        JSON string with job root cause analysis
    """
    debug_print(
        f"🔍 Starting job root cause analysis for {project_id}/{job_id} (mode: {response_mode})"
    )

    try:
        cache_manager = get_cache_manager()

        # Create cache key for job root cause analysis
        cache_key = f"job_root_cause_{project_id}_{job_id}_{response_mode}"
        verbose_debug_print(f"🔑 Using cache key: {cache_key}")

        # Try to get from cache first
        cached_data = await cache_manager.get(cache_key)
        if cached_data:
            debug_print("💾 Found cached job root cause analysis")
            # Apply filtering to cached data if needed
            if any([limit, severity_filter, category_filter, min_confidence]):
                debug_print("🔍 Applying filters to cached data")
                cached_analysis = cached_data.get("root_cause_analysis", {})
                root_causes = cached_analysis.get("root_causes", [])
                filtered_causes = _filter_root_causes(
                    root_causes,
                    limit=limit,
                    severity_filter=severity_filter,
                    category_filter=category_filter,
                    min_confidence=min_confidence,
                )
                # Update cached data with filtered results
                cached_analysis["root_causes"] = filtered_causes
                cached_analysis["root_causes_summary"]["total_causes_identified"] = len(
                    filtered_causes
                )
                cached_data["root_cause_analysis"] = cached_analysis
            return json.dumps(cached_data, indent=2)

        # Get job data from database
        verbose_debug_print("📊 Fetching job data from database...")
        job_info = await cache_manager.get_job_info_async(int(job_id))
        job_errors = cache_manager.get_job_errors(int(job_id))

        debug_print(f"📊 Job data: {len(job_errors)} errors found")

        if not job_errors:
            result = {
                "root_cause_analysis": {
                    "project_id": project_id,
                    "job_id": int(job_id),
                    "summary": "No errors found - job appears successful",
                    "status": "success",
                    "job_info": job_info,
                    "error_count": 0,
                },
                "resource_uri": f"gl://root-cause/{project_id}/job/{job_id}",
                "cached_at": datetime.now(timezone.utc).isoformat(),
            }
        else:
            # Convert dict errors to Error objects
            verbose_debug_print("🔍 Converting errors to Error objects...")
            error_objects = []
            for error_dict in job_errors:
                try:
                    error = Error.from_dict(error_dict)
                    error.job_id = int(job_id)
                    error_objects.append(error)
                except Exception as e:
                    logger.warning(f"Failed to convert error to Error object: {e}")
                    continue

            debug_print(f"🔍 Total errors converted: {len(error_objects)}")

            # Initialize AI-optimized analyzers
            verbose_debug_print("🤖 Initializing AI-optimized analyzers...")
            root_cause_analyzer = RootCauseAnalyzer()
            error_summarizer = ErrorSummarizer()

            # Perform root cause analysis
            debug_print("🔍 Performing job root cause analysis...")
            root_cause_analysis = root_cause_analyzer.analyze(error_objects)

            # Generate AI-optimized summary
            verbose_debug_print("📝 Generating AI-optimized summary...")
            summary = error_summarizer.generate_root_cause_summary(root_cause_analysis)
            debug_print(
                f"📝 Summary generated: {len(summary.key_insights)} key insights, context reduced by ~{summary.context_reduction_percentage}%"
            )

            # Convert dataclass to dict for JSON serialization
            from dataclasses import asdict

            summary_dict = asdict(summary)

            # Create a safe serializable version of the analysis
            def make_serializable(obj):
                """Convert objects to JSON-serializable format."""
                if hasattr(obj, "__dict__"):
                    result = {}
                    for key, value in obj.__dict__.items():
                        if key == "pattern" and hasattr(value, "name"):
                            # For ErrorPattern objects, just keep essential info
                            result[key] = {
                                "name": value.name,
                                "category": value.category,
                                "description": value.description,
                                "severity": value.severity,
                            }
                        elif hasattr(value, "__dict__"):
                            result[key] = make_serializable(value)
                        elif isinstance(value, list):
                            result[key] = [
                                (
                                    make_serializable(item)
                                    if hasattr(item, "__dict__")
                                    else item
                                )
                                for item in value
                            ]
                        elif isinstance(value, set):
                            result[key] = list(value)
                        else:
                            result[key] = value
                    return result
                return obj

            analysis_dict = make_serializable(root_cause_analysis)

            # Create a comprehensive root causes breakdown
            verbose_debug_print("🏗️ Building comprehensive root causes breakdown...")
            root_causes = []

            def _deduplicate_sample_errors(errors: list, max_samples: int) -> list:
                """Deduplicate sample errors based on message, file_path, and line_number."""
                seen = set()
                unique_errors = []

                for error in errors:
                    # Create a key based on error identifying characteristics
                    error_key = (
                        error.message,
                        error.file_path,
                        error.line_number,
                        error.exception_type,
                    )

                    if error_key not in seen:
                        seen.add(error_key)
                        unique_errors.append(error)

                        if len(unique_errors) >= max_samples:
                            break

                return unique_errors

            # Add primary cause
            if (
                root_cause_analysis.primary_cause
                and root_cause_analysis.primary_cause.errors
            ):
                primary_cause = root_cause_analysis.primary_cause
                debug_print(
                    f"🎯 Primary cause: {primary_cause.pattern.name} ({len(primary_cause.errors)} errors, confidence: {primary_cause.confidence:.2f})"
                )

                # Get deduplicated sample errors
                unique_sample_errors = _deduplicate_sample_errors(
                    primary_cause.errors, 3
                )

                root_causes.append(
                    {
                        "type": "primary",
                        "pattern": {
                            "name": primary_cause.pattern.name,
                            "category": primary_cause.pattern.category,
                            "description": primary_cause.pattern.description,
                            "severity": primary_cause.pattern.severity,
                        },
                        "error_count": len(primary_cause.errors),
                        "confidence": primary_cause.confidence,
                        "impact_score": primary_cause.impact_score,
                        "affected_files": list(primary_cause.affected_files),
                        "sample_errors": [
                            {
                                "message": (
                                    error.message[:400] + "..."
                                    if len(error.message) > 400
                                    else error.message
                                ),
                                "file_path": error.file_path,
                                "line_number": error.line_number,
                                "exception_type": error.exception_type,
                            }
                            for error in unique_sample_errors
                        ],
                        "error_references": [f"gl://errors/{project_id}/{job_id}"],
                    }
                )

                verbose_debug_print(
                    f"   📊 Primary cause affects {len(primary_cause.affected_files)} files"
                )

            # Add secondary causes
            debug_print(
                f"📋 Processing {len(root_cause_analysis.secondary_causes)} secondary causes..."
            )
            for i, secondary_cause in enumerate(root_cause_analysis.secondary_causes):
                if secondary_cause.errors:
                    verbose_debug_print(
                        f"   #{i + 2}: {secondary_cause.pattern.name} ({len(secondary_cause.errors)} errors)"
                    )

                    # Get deduplicated sample errors
                    unique_sample_errors = _deduplicate_sample_errors(
                        secondary_cause.errors, 2
                    )

                    root_causes.append(
                        {
                            "type": "secondary",
                            "rank": i
                            + 2,  # Primary is rank 1, so secondary starts at 2
                            "pattern": {
                                "name": secondary_cause.pattern.name,
                                "category": secondary_cause.pattern.category,
                                "description": secondary_cause.pattern.description,
                                "severity": secondary_cause.pattern.severity,
                            },
                            "error_count": len(secondary_cause.errors),
                            "confidence": secondary_cause.confidence,
                            "impact_score": secondary_cause.impact_score,
                            "affected_files": list(secondary_cause.affected_files),
                            "sample_errors": [
                                {
                                    "message": (
                                        error.message[:400] + "..."
                                        if len(error.message) > 400
                                        else error.message
                                    ),
                                    "file_path": error.file_path,
                                    "line_number": error.line_number,
                                    "exception_type": error.exception_type,
                                }
                                for error in unique_sample_errors
                            ],
                            "error_references": [f"gl://errors/{project_id}/{job_id}"],
                        }
                    )

            # Apply filtering and limiting
            if any([limit, severity_filter, category_filter, min_confidence]):
                debug_print(
                    f"🔍 Applying filters: limit={limit}, severity={severity_filter}, category={category_filter}, confidence={min_confidence}"
                )
                filtered_causes = _filter_root_causes(
                    root_causes,
                    limit=limit,
                    severity_filter=severity_filter,
                    category_filter=category_filter,
                    min_confidence=min_confidence,
                )
                debug_print(
                    f"📊 Filtered from {len(root_causes)} to {len(filtered_causes)} root causes"
                )
                root_causes = filtered_causes

            result = {
                "root_cause_analysis": {
                    "project_id": project_id,
                    "job_id": int(job_id),
                    "ai_optimized_summary": summary_dict,
                    "root_causes": root_causes,
                    "root_causes_summary": {
                        "total_causes_identified": len(root_causes),
                        "primary_issue": (
                            root_causes[0]["pattern"]["description"]
                            if root_causes
                            else "No clear root cause identified"
                        ),
                        "total_errors_analyzed": len(error_objects),
                        "confidence": root_cause_analysis.confidence,
                        "most_affected_files": (
                            list(root_cause_analysis.affected_files)[:5]
                            if hasattr(root_cause_analysis, "affected_files")
                            else []
                        ),
                    },
                    "detailed_analysis": analysis_dict,
                    "job_context": {
                        "status": job_info.get("status") if job_info else "unknown",
                        "stage": job_info.get("stage") if job_info else "unknown",
                        "name": job_info.get("name") if job_info else "unknown",
                        "duration": job_info.get("duration") if job_info else None,
                        "pipeline_id": (
                            job_info.get("pipeline_id") if job_info else None
                        ),
                    },
                },
                "resource_uri": f"gl://root-cause/{project_id}/job/{job_id}",
                "cached_at": datetime.now(timezone.utc).isoformat(),
                "metadata": {
                    "analysis_type": "ai_optimized_job_root_cause",
                    "response_mode": response_mode,
                    "context_reduction": "optimized_for_ai_consumption",
                    "error_count": len(error_objects),
                },
            }

            debug_print(
                f"✅ Job root cause analysis complete: {len(root_causes)} causes identified"
            )

        # Apply response mode optimization
        verbose_debug_print(f"⚙️ Applying response mode optimization: {response_mode}")
        from gitlab_analyzer.utils.utils import optimize_tool_response

        result = optimize_tool_response(result, response_mode)

        mcp_info = get_mcp_info(
            tool_used="job_root_cause_analysis", error=False, parser_type="ai_optimized"
        )
        result["mcp_info"] = mcp_info

        # Cache the result (without filters applied so base data is available)
        verbose_debug_print(f"💾 Caching result with key: {cache_key}")
        await cache_manager.set(
            cache_key,
            result,
            data_type="root_cause",
            project_id=project_id,
            job_id=int(job_id),
        )

        debug_print("✅ Job root cause analysis cached and ready to return")
        return json.dumps(result, indent=2)

    except Exception as e:
        debug_print(
            f"❌ Error in job root cause analysis for {project_id}/{job_id}: {str(e)}"
        )
        logger.error(
            "Error getting job root cause analysis %s/%s: %s", project_id, job_id, e
        )
        error_result = {
            "error": f"Failed to get job root cause analysis: {str(e)}",
            "project_id": project_id,
            "job_id": int(job_id),
            "resource_uri": f"gl://root-cause/{project_id}/job/{job_id}",
        }
        return json.dumps(error_result, indent=2)


async def _get_root_cause_analysis(
    project_id: str,
    pipeline_id: str,
    response_mode: str = "minimal",
    limit: int | None = None,
    severity_filter: str | None = None,
    category_filter: str | None = None,
    min_confidence: float | None = None,
) -> str:
    """Get AI-optimized root cause analysis for a pipeline."""
    debug_print(
        f"🔍 Starting root cause analysis for pipeline {project_id}/{pipeline_id} (mode: {response_mode})"
    )

    try:
        cache_manager = get_cache_manager()

        # Check if pipeline has been analyzed
        verbose_debug_print("📋 Checking if pipeline has been analyzed...")
        error_response = await check_pipeline_analyzed(
            project_id, pipeline_id, "root_cause_analysis"
        )
        if error_response:
            debug_print("❌ Pipeline not analyzed - returning error response")
            return json.dumps(error_response, indent=2)

        # Create cache key for root cause analysis
        cache_key = f"root_cause_{project_id}_{pipeline_id}_{response_mode}"
        verbose_debug_print(f"🔑 Using cache key: {cache_key}")

        # Try to get from cache first
        cached_data = await cache_manager.get(cache_key)
        if cached_data:
            debug_print("💾 Found cached root cause analysis")
            return json.dumps(cached_data, indent=2)

        # Get pipeline data
        verbose_debug_print("📊 Fetching pipeline data from database...")
        pipeline_info = cache_manager.get_pipeline_info(int(pipeline_id))
        failed_jobs = cache_manager.get_pipeline_failed_jobs(int(pipeline_id))

        debug_print(f"📊 Pipeline data: {len(failed_jobs)} failed jobs found")

        if not failed_jobs:
            result = {
                "root_cause_analysis": {
                    "project_id": project_id,
                    "pipeline_id": int(pipeline_id),
                    "summary": "No failed jobs found - pipeline appears successful",
                    "status": "success",
                    "total_jobs": len(
                        await cache_manager.get_pipeline_jobs(int(pipeline_id))
                    ),
                    "failed_jobs": 0,
                },
                "resource_uri": f"gl://root-cause/{project_id}/{pipeline_id}",
                "cached_at": datetime.now(timezone.utc).isoformat(),
            }
        else:
            # Get all errors from failed jobs and convert to Error objects
            verbose_debug_print("🔍 Processing errors from failed jobs...")
            all_errors = []
            job_error_mapping = {}  # Track which job each error belongs to

            for job in failed_jobs:
                job_id = job.get("job_id") or job.get("id")
                if job_id:
                    job_errors = cache_manager.get_job_errors(job_id)
                    debug_print(f"   📋 Job {job_id}: {len(job_errors)} errors found")

                    # Convert dict errors to Error objects
                    for error_dict in job_errors:
                        try:
                            error = Error.from_dict(error_dict)
                            # Add job context to error
                            error.job_id = job_id
                            all_errors.append(error)
                            job_error_mapping[id(error)] = job_id
                        except Exception as e:
                            logger.warning(
                                f"Failed to convert error to Error object: {e}"
                            )
                            continue

            debug_print(
                f"🔍 Total errors collected: {len(all_errors)} from {len(failed_jobs)} failed jobs"
            )

            # Initialize AI-optimized analyzers
            verbose_debug_print("🤖 Initializing AI-optimized analyzers...")
            root_cause_analyzer = RootCauseAnalyzer()
            error_summarizer = ErrorSummarizer()

            # Perform root cause analysis
            debug_print("🔍 Performing root cause analysis...")
            root_cause_analysis = root_cause_analyzer.analyze(all_errors)

            # Generate AI-optimized summary
            verbose_debug_print("📝 Generating AI-optimized summary...")
            summary = error_summarizer.generate_root_cause_summary(root_cause_analysis)
            debug_print(
                f"📝 Summary generated: {len(summary.key_insights)} key insights, context reduced by ~{summary.context_reduction_percentage}%"
            )

            # Convert dataclass to dict for JSON serialization
            from dataclasses import asdict

            summary_dict = asdict(summary)

            # Create a safe serializable version of the analysis
            def make_serializable(obj):
                """Convert objects to JSON-serializable format."""
                if hasattr(obj, "__dict__"):
                    result = {}
                    for key, value in obj.__dict__.items():
                        if key == "pattern" and hasattr(value, "name"):
                            # For ErrorPattern objects, just keep essential info
                            result[key] = {
                                "name": value.name,
                                "category": value.category,
                                "description": value.description,
                                "severity": value.severity,
                            }
                        elif hasattr(value, "__dict__"):
                            result[key] = make_serializable(value)
                        elif isinstance(value, list):
                            result[key] = [
                                (
                                    make_serializable(item)
                                    if hasattr(item, "__dict__")
                                    else item
                                )
                                for item in value
                            ]
                        elif isinstance(value, set):
                            result[key] = list(value)
                        else:
                            result[key] = value
                    return result
                return obj

            analysis_dict = make_serializable(root_cause_analysis)

            # Create a comprehensive root causes breakdown
            verbose_debug_print("🏗️ Building comprehensive root causes breakdown...")
            root_causes = []

            def _deduplicate_sample_errors(errors: list, max_samples: int) -> list:
                """Deduplicate sample errors based on message, file_path, and line_number."""
                seen = set()
                unique_errors = []

                for error in errors:
                    # Create a key based on error identifying characteristics
                    error_key = (
                        error.message,
                        error.file_path,
                        error.line_number,
                        error.exception_type,
                    )

                    if error_key not in seen:
                        seen.add(error_key)
                        unique_errors.append(error)

                        if len(unique_errors) >= max_samples:
                            break

                return unique_errors

            # Add primary cause
            if (
                root_cause_analysis.primary_cause
                and root_cause_analysis.primary_cause.errors
            ):
                primary_cause = root_cause_analysis.primary_cause
                debug_print(
                    f"🎯 Primary cause: {primary_cause.pattern.name} ({len(primary_cause.errors)} errors, confidence: {primary_cause.confidence:.2f})"
                )

                # Get deduplicated sample errors
                unique_sample_errors = _deduplicate_sample_errors(
                    primary_cause.errors, 3
                )

                root_causes.append(
                    {
                        "type": "primary",
                        "pattern": {
                            "name": primary_cause.pattern.name,
                            "category": primary_cause.pattern.category,
                            "description": primary_cause.pattern.description,
                            "severity": primary_cause.pattern.severity,
                        },
                        "error_count": len(primary_cause.errors),
                        "confidence": primary_cause.confidence,
                        "impact_score": primary_cause.impact_score,
                        "affected_files": list(primary_cause.affected_files),
                        "sample_errors": [
                            {
                                "message": (
                                    error.message[:400] + "..."
                                    if len(error.message) > 400
                                    else error.message
                                ),
                                "file_path": error.file_path,
                                "line_number": error.line_number,
                                "exception_type": error.exception_type,
                            }
                            for error in unique_sample_errors
                        ],
                        "error_references": [
                            f"gl://errors/{project_id}/{getattr(error, 'job_id', 'unknown')}"
                            for error in unique_sample_errors
                            if hasattr(error, "job_id")
                        ],
                    }
                )

                verbose_debug_print(
                    f"   📊 Primary cause affects {len(primary_cause.affected_files)} files"
                )

            # Add secondary causes
            debug_print(
                f"📋 Processing {len(root_cause_analysis.secondary_causes)} secondary causes..."
            )
            for i, secondary_cause in enumerate(root_cause_analysis.secondary_causes):
                if secondary_cause.errors:
                    verbose_debug_print(
                        f"   #{i + 2}: {secondary_cause.pattern.name} ({len(secondary_cause.errors)} errors)"
                    )

                    # Get deduplicated sample errors
                    unique_sample_errors = _deduplicate_sample_errors(
                        secondary_cause.errors, 2
                    )

                    root_causes.append(
                        {
                            "type": "secondary",
                            "rank": i
                            + 2,  # Primary is rank 1, so secondary starts at 2
                            "pattern": {
                                "name": secondary_cause.pattern.name,
                                "category": secondary_cause.pattern.category,
                                "description": secondary_cause.pattern.description,
                                "severity": secondary_cause.pattern.severity,
                            },
                            "error_count": len(secondary_cause.errors),
                            "confidence": secondary_cause.confidence,
                            "impact_score": secondary_cause.impact_score,
                            "affected_files": list(secondary_cause.affected_files),
                            "sample_errors": [
                                {
                                    "message": (
                                        error.message[:400] + "..."
                                        if len(error.message) > 400
                                        else error.message
                                    ),
                                    "file_path": error.file_path,
                                    "line_number": error.line_number,
                                    "exception_type": error.exception_type,
                                }
                                for error in unique_sample_errors
                            ],
                            "error_references": [
                                f"gl://errors/{project_id}/{getattr(error, 'job_id', 'unknown')}"
                                for error in unique_sample_errors
                                if hasattr(error, "job_id")
                            ],
                        }
                    )

            # Apply filtering and limiting
            if any([limit, severity_filter, category_filter, min_confidence]):
                debug_print(
                    f"🔍 Applying filters: limit={limit}, severity={severity_filter}, category={category_filter}, confidence={min_confidence}"
                )
                filtered_causes = _filter_root_causes(
                    root_causes,
                    limit=limit,
                    severity_filter=severity_filter,
                    category_filter=category_filter,
                    min_confidence=min_confidence,
                )
                debug_print(
                    f"📊 Filtered from {len(root_causes)} to {len(filtered_causes)} root causes"
                )
                root_causes = filtered_causes

            result = {
                "root_cause_analysis": {
                    "project_id": project_id,
                    "pipeline_id": int(pipeline_id),
                    "ai_optimized_summary": summary_dict,
                    "root_causes": root_causes,
                    "root_causes_summary": {
                        "total_causes_identified": len(root_causes),
                        "primary_issue": (
                            root_causes[0]["pattern"]["description"]
                            if root_causes
                            else "No clear root cause identified"
                        ),
                        "total_errors_analyzed": len(all_errors),
                        "confidence": root_cause_analysis.confidence,
                        "most_affected_files": (
                            list(root_cause_analysis.affected_files)[:5]
                            if hasattr(root_cause_analysis, "affected_files")
                            else []
                        ),
                    },
                    "detailed_analysis": analysis_dict,
                    "pipeline_context": {
                        "status": (
                            pipeline_info.get("status") if pipeline_info else "unknown"
                        ),
                        "total_jobs": len(
                            await cache_manager.get_pipeline_jobs(int(pipeline_id))
                        ),
                        "failed_jobs": len(failed_jobs),
                        "success_rate": (
                            round(
                                (
                                    len(
                                        await cache_manager.get_pipeline_jobs(
                                            int(pipeline_id)
                                        )
                                    )
                                    - len(failed_jobs)
                                )
                                / len(
                                    await cache_manager.get_pipeline_jobs(
                                        int(pipeline_id)
                                    )
                                )
                                * 100,
                                1,
                            )
                            if await cache_manager.get_pipeline_jobs(int(pipeline_id))
                            else 0
                        ),
                    },
                },
                "resource_uri": f"gl://root-cause/{project_id}/{pipeline_id}",
                "cached_at": datetime.now(timezone.utc).isoformat(),
                "metadata": {
                    "analysis_type": "ai_optimized_root_cause",
                    "response_mode": response_mode,
                    "context_reduction": "optimized_for_ai_consumption",
                    "error_count": len(all_errors),
                },
            }

            debug_print(
                f"✅ Root cause analysis complete: {len(root_causes)} causes identified"
            )

        # Apply response mode optimization
        verbose_debug_print(f"⚙️ Applying response mode optimization: {response_mode}")
        from gitlab_analyzer.utils.utils import optimize_tool_response

        result = optimize_tool_response(result, response_mode)

        mcp_info = get_mcp_info(
            tool_used="root_cause_analysis", error=False, parser_type="ai_optimized"
        )
        result["mcp_info"] = mcp_info

        # Cache the result
        verbose_debug_print(f"💾 Caching result with key: {cache_key}")
        await cache_manager.set(
            cache_key,
            result,
            data_type="root_cause",
            project_id=project_id,
            pipeline_id=int(pipeline_id),
        )

        debug_print("✅ Root cause analysis cached and ready to return")
        return json.dumps(result, indent=2)

    except Exception as e:
        debug_print(
            f"❌ Error in root cause analysis for {project_id}/{pipeline_id}: {str(e)}"
        )
        logger.error(
            "Error getting root cause analysis %s/%s: %s", project_id, pipeline_id, e
        )
        error_result = {
            "error": f"Failed to get root cause analysis: {str(e)}",
            "project_id": project_id,
            "pipeline_id": int(pipeline_id),
            "resource_uri": f"gl://root-cause/{project_id}/{pipeline_id}",
        }
        return json.dumps(error_result, indent=2)


def register_analysis_resources(mcp) -> None:
    """Register analysis resources with MCP server"""

    @mcp.resource("gl://analysis/{project_id}")
    async def get_project_analysis_resource(project_id: str) -> TextResourceContents:
        """
        Get project-level analysis as a resource with caching.

        Args:
            project_id: GitLab project ID

        Returns:
            Project-level analysis with metadata

        Note: Resources provide "balanced" mode by default for optimal agent consumption.
        """
        result = await _get_comprehensive_analysis(project_id, response_mode="balanced")
        return create_text_resource("gl://analysis/{project_id}", result)

    @mcp.resource("gl://analysis/{project_id}?mode={mode}")
    async def get_project_analysis_resource_with_mode(
        project_id: str, mode: str
    ) -> TextResourceContents:
        """
        Get project-level analysis as a resource with specific response mode.

        Args:
            project_id: GitLab project ID
            mode: Response mode - "minimal", "balanced", "fixing", or "full"

        Returns:
            Project-level analysis optimized for the specified mode
        """
        result = await _get_comprehensive_analysis(project_id, response_mode=mode)
        return create_text_resource("gl://analysis/{project_id}?mode={mode}", result)

    @mcp.resource("gl://analysis/{project_id}/pipeline/{pipeline_id}")
    async def get_pipeline_analysis_resource(
        project_id: str, pipeline_id: str
    ) -> TextResourceContents:
        """
        Get pipeline-level analysis as a resource with caching.

        Args:
            project_id: GitLab project ID
            pipeline_id: GitLab pipeline ID

        Returns:
            Pipeline-level analysis with metadata
        """
        result = await _get_comprehensive_analysis(
            project_id, pipeline_id, response_mode="balanced"
        )
        return create_text_resource(
            "gl://analysis/{project_id}/pipeline/{pipeline_id}", result
        )

    @mcp.resource("gl://analysis/{project_id}/pipeline/{pipeline_id}?mode={mode}")
    async def get_pipeline_analysis_resource_with_mode(
        project_id: str, pipeline_id: str, mode: str
    ) -> TextResourceContents:
        """
        Get pipeline-level analysis as a resource with specific response mode.

        Args:
            project_id: GitLab project ID
            pipeline_id: GitLab pipeline ID
            mode: Response mode - "minimal", "balanced", "fixing", or "full"

        Returns:
            Pipeline-level analysis optimized for the specified mode
        """
        result = await _get_comprehensive_analysis(
            project_id, pipeline_id, response_mode=mode
        )
        return create_text_resource(
            "gl://analysis/{project_id}/pipeline/{pipeline_id}?mode={mode}",
            result,
        )

    @mcp.resource("gl://analysis/{project_id}/job/{job_id}")
    async def get_job_analysis_resource(
        project_id: str, job_id: str
    ) -> TextResourceContents:
        """
        Get job-level analysis as a resource with caching.

        Args:
            project_id: GitLab project ID
            job_id: GitLab job ID

        Returns:
            Job-level analysis with metadata
        """
        result = await _get_comprehensive_analysis(
            project_id, job_id=job_id, response_mode="balanced"
        )
        return create_text_resource("gl://analysis/{project_id}/job/{job_id}", result)

    @mcp.resource("gl://analysis/{project_id}/job/{job_id}?mode={mode}")
    async def get_job_analysis_resource_with_mode(
        project_id: str, job_id: str, mode: str
    ) -> TextResourceContents:
        """
        Get job-level analysis as a resource with specific response mode.

        Args:
            project_id: GitLab project ID
            job_id: GitLab job ID
            mode: Response mode - "minimal", "balanced", "fixing", or "full"

        Returns:
            Job-level analysis optimized for the specified mode
        """
        result = await _get_comprehensive_analysis(
            project_id, job_id=job_id, response_mode=mode
        )
        return create_text_resource(
            "gl://analysis/{project_id}/job/{job_id}?mode={mode}", result
        )

    @mcp.resource("gl://root-cause/{project_id}/{pipeline_id}")
    async def get_root_cause_resource(
        project_id: str, pipeline_id: str
    ) -> TextResourceContents:
        """
        Get AI-optimized root cause analysis for a pipeline.

        This resource provides minimal, focused error analysis specifically
        designed for AI consumption with maximum context reduction.

        Args:
            project_id: GitLab project ID
            pipeline_id: GitLab pipeline ID

        Returns:
            Root cause analysis with AI-optimized summary
        """
        result = await _get_root_cause_analysis(project_id, pipeline_id, "minimal")
        return create_text_resource(
            "gl://root-cause/{project_id}/{pipeline_id}", result
        )

    @mcp.resource("gl://root-cause/{project_id}/{pipeline_id}?mode={mode}")
    async def get_root_cause_resource_with_mode(
        project_id: str, pipeline_id: str, mode: str
    ) -> TextResourceContents:
        """
        Get AI-optimized root cause analysis with specific response mode.

        Args:
            project_id: GitLab project ID
            pipeline_id: GitLab pipeline ID
            mode: Response mode - "minimal", "balanced", "detailed"

        Returns:
            Root cause analysis optimized for the specified mode
        """
        result = await _get_root_cause_analysis(project_id, pipeline_id, mode)
        return create_text_resource(
            "gl://root-cause/{project_id}/{pipeline_id}?mode={mode}", result
        )

    @mcp.resource("gl://root-cause/{project_id}/{pipeline_id}?limit={limit}")
    async def get_root_cause_resource_with_limit(
        project_id: str, pipeline_id: str, limit: str
    ) -> TextResourceContents:
        """
        Get AI-optimized root cause analysis with limit.

        Args:
            project_id: GitLab project ID
            pipeline_id: GitLab pipeline ID
            limit: Maximum number of root causes to return

        Returns:
            Root cause analysis with limited results
        """
        try:
            limit_int = int(limit)
        except (ValueError, TypeError):
            limit_int = None

        result = await _get_root_cause_analysis(
            project_id, pipeline_id, "minimal", limit=limit_int
        )
        return create_text_resource(
            "gl://root-cause/{project_id}/{pipeline_id}?limit={limit}", result
        )

    @mcp.resource("gl://root-cause/{project_id}/{pipeline_id}?severity={severity}")
    async def get_root_cause_resource_with_severity(
        project_id: str, pipeline_id: str, severity: str
    ) -> TextResourceContents:
        """
        Get AI-optimized root cause analysis filtered by severity.

        Args:
            project_id: GitLab project ID
            pipeline_id: GitLab pipeline ID
            severity: Severity level filter (critical, high, medium, low)

        Returns:
            Root cause analysis filtered by severity
        """
        result = await _get_root_cause_analysis(
            project_id, pipeline_id, "minimal", severity_filter=severity
        )
        return create_text_resource(
            "gl://root-cause/{project_id}/{pipeline_id}?severity={severity}", result
        )

    @mcp.resource("gl://root-cause/{project_id}/{pipeline_id}?category={category}")
    async def get_root_cause_resource_with_category(
        project_id: str, pipeline_id: str, category: str
    ) -> TextResourceContents:
        """
        Get AI-optimized root cause analysis filtered by category.

        Args:
            project_id: GitLab project ID
            pipeline_id: GitLab pipeline ID
            category: Category filter (e.g., 'syntax', 'import', 'test', etc.)

        Returns:
            Root cause analysis filtered by category
        """
        result = await _get_root_cause_analysis(
            project_id, pipeline_id, "minimal", category_filter=category
        )
        return create_text_resource(
            "gl://root-cause/{project_id}/{pipeline_id}?category={category}", result
        )

    @mcp.resource("gl://root-cause/{project_id}/{pipeline_id}?confidence={confidence}")
    async def get_root_cause_resource_with_confidence(
        project_id: str, pipeline_id: str, confidence: str
    ) -> TextResourceContents:
        """
        Get AI-optimized root cause analysis filtered by minimum confidence.

        Args:
            project_id: GitLab project ID
            pipeline_id: GitLab pipeline ID
            confidence: Minimum confidence threshold (0.0-1.0)

        Returns:
            Root cause analysis filtered by confidence
        """
        try:
            confidence_float = float(confidence)
        except (ValueError, TypeError):
            confidence_float = None

        result = await _get_root_cause_analysis(
            project_id, pipeline_id, "minimal", min_confidence=confidence_float
        )
        return create_text_resource(
            "gl://root-cause/{project_id}/{pipeline_id}?confidence={confidence}", result
        )

    # Job-specific root cause analysis resources
    @mcp.resource("gl://root-cause/{project_id}/job/{job_id}")
    async def get_job_root_cause_resource(
        project_id: str, job_id: str
    ) -> TextResourceContents:
        """
        Get AI-optimized root cause analysis for a specific job.

        This resource provides minimal, focused error analysis specifically
        designed for AI consumption with maximum context reduction.

        Args:
            project_id: GitLab project ID
            job_id: GitLab job ID

        Returns:
            Job root cause analysis with AI-optimized summary
        """
        result = await _get_job_root_cause_analysis(project_id, job_id, "minimal")
        return create_text_resource("gl://root-cause/{project_id}/job/{job_id}", result)

    @mcp.resource("gl://root-cause/{project_id}/job/{job_id}?mode={mode}")
    async def get_job_root_cause_resource_with_mode(
        project_id: str, job_id: str, mode: str
    ) -> TextResourceContents:
        """
        Get AI-optimized job root cause analysis with specific response mode.

        Args:
            project_id: GitLab project ID
            job_id: GitLab job ID
            mode: Response mode - "minimal", "balanced", "detailed"

        Returns:
            Job root cause analysis optimized for the specified mode
        """
        result = await _get_job_root_cause_analysis(project_id, job_id, mode)
        return create_text_resource(
            "gl://root-cause/{project_id}/job/{job_id}?mode={mode}", result
        )

    @mcp.resource("gl://root-cause/{project_id}/job/{job_id}?limit={limit}")
    async def get_job_root_cause_resource_with_limit(
        project_id: str, job_id: str, limit: str
    ) -> TextResourceContents:
        """
        Get AI-optimized job root cause analysis with limit.

        Args:
            project_id: GitLab project ID
            job_id: GitLab job ID
            limit: Maximum number of root causes to return

        Returns:
            Job root cause analysis with limited results
        """
        try:
            limit_int = int(limit)
        except (ValueError, TypeError):
            limit_int = None

        result = await _get_job_root_cause_analysis(
            project_id, job_id, "minimal", limit=limit_int
        )
        return create_text_resource(
            "gl://root-cause/{project_id}/job/{job_id}?limit={limit}", result
        )

    @mcp.resource("gl://root-cause/{project_id}/job/{job_id}?severity={severity}")
    async def get_job_root_cause_resource_with_severity(
        project_id: str, job_id: str, severity: str
    ) -> TextResourceContents:
        """
        Get AI-optimized job root cause analysis filtered by severity.

        Args:
            project_id: GitLab project ID
            job_id: GitLab job ID
            severity: Severity level filter (critical, high, medium, low)

        Returns:
            Job root cause analysis filtered by severity
        """
        result = await _get_job_root_cause_analysis(
            project_id, job_id, "minimal", severity_filter=severity
        )
        return create_text_resource(
            "gl://root-cause/{project_id}/job/{job_id}?severity={severity}", result
        )

    @mcp.resource("gl://root-cause/{project_id}/job/{job_id}?category={category}")
    async def get_job_root_cause_resource_with_category(
        project_id: str, job_id: str, category: str
    ) -> TextResourceContents:
        """
        Get AI-optimized job root cause analysis filtered by category.

        Args:
            project_id: GitLab project ID
            job_id: GitLab job ID
            category: Category filter (e.g., 'syntax', 'import', 'test', etc.)

        Returns:
            Job root cause analysis filtered by category
        """
        result = await _get_job_root_cause_analysis(
            project_id, job_id, "minimal", category_filter=category
        )
        return create_text_resource(
            "gl://root-cause/{project_id}/job/{job_id}?category={category}", result
        )

    @mcp.resource("gl://root-cause/{project_id}/job/{job_id}?confidence={confidence}")
    async def get_job_root_cause_resource_with_confidence(
        project_id: str, job_id: str, confidence: str
    ) -> TextResourceContents:
        """
        Get AI-optimized job root cause analysis filtered by minimum confidence.

        Args:
            project_id: GitLab project ID
            job_id: GitLab job ID
            confidence: Minimum confidence threshold (0.0-1.0)

        Returns:
            Job root cause analysis filtered by confidence
        """
        try:
            confidence_float = float(confidence)
        except (ValueError, TypeError):
            confidence_float = None

        result = await _get_job_root_cause_analysis(
            project_id, job_id, "minimal", min_confidence=confidence_float
        )
        return create_text_resource(
            "gl://root-cause/{project_id}/job/{job_id}?confidence={confidence}", result
        )

    @mcp.resource(
        "gl://root-cause/{project_id}/job/{job_id}?limit={limit}&severity={severity}"
    )
    async def get_job_root_cause_resource_with_limit_and_severity(
        project_id: str, job_id: str, limit: str, severity: str
    ) -> TextResourceContents:
        """
        Get AI-optimized job root cause analysis with limit and severity filter.

        Args:
            project_id: GitLab project ID
            job_id: GitLab job ID
            limit: Maximum number of root causes to return
            severity: Severity level filter (critical, high, medium, low)

        Returns:
            Job root cause analysis with limited results filtered by severity
        """
        try:
            limit_int = int(limit)
        except (ValueError, TypeError):
            limit_int = None

        result = await _get_job_root_cause_analysis(
            project_id, job_id, "minimal", limit=limit_int, severity_filter=severity
        )
        return create_text_resource(
            "gl://root-cause/{project_id}/job/{job_id}?limit={limit}&severity={severity}",
            result,
        )

    @mcp.resource(
        "gl://root-cause/{project_id}/job/{job_id}?limit={limit}&category={category}"
    )
    async def get_job_root_cause_resource_with_limit_and_category(
        project_id: str, job_id: str, limit: str, category: str
    ) -> TextResourceContents:
        """
        Get AI-optimized job root cause analysis with limit and category filter.

        Args:
            project_id: GitLab project ID
            job_id: GitLab job ID
            limit: Maximum number of root causes to return
            category: Category filter (e.g., 'syntax', 'import', 'test', etc.)

        Returns:
            Job root cause analysis with limited results filtered by category
        """
        try:
            limit_int = int(limit)
        except (ValueError, TypeError):
            limit_int = None

        result = await _get_job_root_cause_analysis(
            project_id, job_id, "minimal", limit=limit_int, category_filter=category
        )
        return create_text_resource(
            "gl://root-cause/{project_id}/job/{job_id}?limit={limit}&category={category}",
            result,
        )

    logger.info("Analysis resources registered")
