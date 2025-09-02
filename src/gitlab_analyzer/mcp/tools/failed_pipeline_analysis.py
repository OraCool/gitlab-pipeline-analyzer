"""
Failed Pipeline Analysis Tool - Focused on analyzing only failed pipeline jobs

This module provides efficient analysis by focusing specifically on failed jobs:
1. Gets pipeline info and stores in database
2. Gets only failed jobs using get_failed_pipeline_jobs (more efficient)
3. Stores failed job data for fu            for job_result in job_analysis_results:
                job_result_typed = cast("dict[str, Any]", job_result)
                job_id = job_result_typed["job_id"]
                job_name = job_result_typed["job_name"]

                # Add job-specific resources
                resources["jobs_detail"][str(job_id)] = {
                    "job": f"gl://job/{project_id}/{pipeline_id}/{job_id}",
                    "errors": f"gl://errors/{project_id}/{job_id}",
                    "files": {},
                }

                # Process file groups for this job
                file_groups = cast("list[dict[str, Any]]", job_result_typed.get("file_groups", []))
                for file_group in file_groups:
Copyright (c) 2025 Siarhei Skuratovich
Licensed under the MIT License - see LICENSE file for details
"""

import asyncio
import hashlib
import time
from typing import Any, cast

from fastmcp import FastMCP

from gitlab_analyzer.cache.mcp_cache import get_cache_manager
from gitlab_analyzer.cache.models import ErrorRecord
from gitlab_analyzer.core.pipeline_info import get_comprehensive_pipeline_info
from gitlab_analyzer.parsers.log_parser import LogParser
from gitlab_analyzer.parsers.pytest_parser import PytestLogParser
from gitlab_analyzer.utils.debug import debug_print, error_print, verbose_debug_print
from gitlab_analyzer.utils.utils import (
    _should_use_pytest_parser,
    categorize_files_by_type,
    combine_exclude_file_patterns,
    extract_file_path_from_message,
    get_gitlab_analyzer,
    get_mcp_info,
    should_exclude_file_path,
)


def _filter_duplicate_combined_errors(errors: list) -> list:
    """Filter duplicates from combined error results (local implementation)"""
    verbose_debug_print(f"Filtering duplicates from {len(errors)} combined errors")
    seen_errors = set()
    filtered_errors = []

    for error in errors:
        # Create a key for duplicate detection
        message = error.get("message", "") or error.get("exception_message", "")
        file_path = error.get("file_path", "") or error.get("file", "")
        line_number = error.get("line_number", "") or error.get("line", "")
        error_type = error.get("error_type", "") or error.get("exception_type", "")

        # Create a normalized key for duplicate detection
        key = f"{message}|{file_path}|{line_number}|{error_type}".lower().strip()

        if key not in seen_errors:
            seen_errors.add(key)
            filtered_errors.append(error)

    verbose_debug_print(
        f"After combined duplicate filtering: {len(filtered_errors)} unique errors"
    )
    return filtered_errors


def register_failed_pipeline_analysis_tools(mcp: FastMCP) -> None:
    """Register failed pipeline analysis tools"""

    @mcp.tool
    async def failed_pipeline_analysis(
        project_id: str | int,
        pipeline_id: int,
        store_in_db: bool = True,
        exclude_file_patterns: list[str] | None = None,
        disable_file_filtering: bool = False,
        include_jobs_resource: bool = False,
        include_files_resource: bool = False,
        include_errors_resource: bool = False,
    ) -> dict[str, Any]:
        """
        🚨 FAILED PIPELINE ANALYSIS: Efficient analysis focusing only on failed jobs.

        This tool provides targeted analysis by:
        1. Gets pipeline information with branch resolution
        2. Analyzes ONLY failed jobs using get_failed_pipeline_jobs (more efficient)
        3. Stores results in database for resource access
        4. Uses caching for performance
        5. Provides structured output for failed job investigation

        WHEN TO USE:
        - Pipeline shows "failed" status and you want to focus on failures
        - More efficient than comprehensive analysis when only failures matter
        - Need failed job data stored for resource-based access
        - Want targeted investigation of specific failures

        SMART FEATURES:
        - Uses get_failed_pipeline_jobs for efficient API calls
        - Filters out non-failed jobs automatically
        - Resolves real branch names for merge request pipelines
        - Caches results for repeated access
        - Stores analysis in database for resources

        WHAT YOU GET:
        - Complete pipeline metadata with resolved branches
        - Only failed jobs analyzed (no wasted time on successful jobs)
        - Structured error and failure reason data
        - Analysis summary and statistics focused on failures
        - Resource URIs for detailed investigation

        Args:
            project_id: The GitLab project ID or path
            pipeline_id: The ID of the GitLab pipeline to analyze
            store_in_db: Whether to store results in database for resources
            exclude_file_patterns: Additional file path patterns to exclude beyond defaults.
                                 Examples: ["migrations/", "node_modules/", "vendor/"]
                                 These are combined with default system paths like .venv, site-packages, etc.
            disable_file_filtering: If True, disables all file filtering including defaults.
                                  When True, all errors from all files (including system files) are included.
                                  Useful for comprehensive debugging or when you need to see everything.
            include_jobs_resource: If True, includes failed jobs overview resource link in response.
                                 Default: False for cleaner output. Set to True to include jobs resource link.
            include_files_resource: If True, includes files resource links in response.
                                   Default: False for cleaner output. Set to True to include files resource links.
            include_errors_resource: If True, includes errors resource links in response.
                                    Default: False for cleaner output. Set to True to include errors resource links.

        Returns:
            Failed pipeline analysis with efficient failed-job-only parsing and caching

        WORKFLOW: Primary failed analysis tool → use resources for specific data access
        """

        start_time = time.time()
        debug_print(
            f"🚨 Starting failed pipeline analysis for pipeline {pipeline_id} in project {project_id}"
        )
        verbose_debug_print(
            f"📋 Analysis options: store_in_db={store_in_db}, disable_file_filtering={disable_file_filtering}"
        )
        verbose_debug_print(
            f"📋 Resource includes: jobs={include_jobs_resource}, files={include_files_resource}, errors={include_errors_resource}"
        )
        if exclude_file_patterns:
            verbose_debug_print(f"🔧 Custom exclude patterns: {exclude_file_patterns}")

        try:
            debug_print("🔗 Initializing GitLab analyzer and cache manager...")
            analyzer = get_gitlab_analyzer()
            cache_manager = get_cache_manager()
            verbose_debug_print("✅ GitLab analyzer and cache manager initialized")

            # CLEAR CACHE: Clear any existing data for this pipeline to prevent conflicts
            # This prevents freezing when re-analyzing pipelines that already have data
            debug_print(f"🧹 Clearing existing cache for pipeline {pipeline_id}...")
            try:
                await cache_manager.clear_cache_by_pipeline(project_id, pipeline_id)
                debug_print(f"✅ Cleared existing cache for pipeline {pipeline_id}")
            except Exception as cache_error:
                verbose_debug_print(f"⚠️ Warning: Could not clear cache: {cache_error}")
                # Continue anyway - cache clearing failure shouldn't stop analysis

            # Step 1: Get comprehensive pipeline info and store it
            debug_print("📊 Step 1: Getting comprehensive pipeline information...")
            pipeline_info = await get_comprehensive_pipeline_info(
                analyzer=analyzer, project_id=project_id, pipeline_id=pipeline_id
            )
            verbose_debug_print(
                f"✅ Pipeline info retrieved: status={pipeline_info.get('status')}, branch={pipeline_info.get('source_branch')}"
            )

            if store_in_db:
                verbose_debug_print("💾 Storing pipeline info in database...")
                # Pass the full comprehensive pipeline info (the async method now handles extraction)
                await cache_manager.store_pipeline_info_async(
                    project_id=project_id,
                    pipeline_id=pipeline_id,
                    pipeline_info=pipeline_info,
                )
                verbose_debug_print("✅ Pipeline info stored in database")

            # Step 2: Get only failed jobs (more efficient than all jobs)
            debug_print(
                f"📊 Step 2: Fetching failed jobs for pipeline {pipeline_id}..."
            )
            failed_jobs = await analyzer.get_failed_pipeline_jobs(
                project_id=project_id, pipeline_id=pipeline_id
            )
            debug_print(f"📋 Found {len(failed_jobs)} failed jobs")
            if failed_jobs:
                job_names = [job.name for job in failed_jobs[:5]]  # Show first 5
                verbose_debug_print(f"🔍 Failed job names (first 5): {job_names}")

            # Step 3: Store basic failed job info in database using cache manager
            if store_in_db and failed_jobs:
                verbose_debug_print("💾 Storing basic failed job info in database...")
                await cache_manager.store_failed_jobs_basic(
                    project_id=project_id,
                    pipeline_id=pipeline_id,
                    failed_jobs=failed_jobs,
                    pipeline_info=pipeline_info,
                )
                verbose_debug_print("✅ Basic failed job info stored")

            # Step 4: For each failed job, get trace, select parser, extract/categorize/store errors/files
            debug_print("📊 Step 4: Analyzing individual failed jobs...")
            job_analysis_results = []
            # Set up file path exclusion patterns (combine defaults with user-provided patterns)
            if disable_file_filtering:
                exclude_patterns = []  # No filtering at all
                debug_print("🔧 File filtering disabled - analyzing all files")
            else:
                exclude_patterns = combine_exclude_file_patterns(exclude_file_patterns)
                verbose_debug_print(
                    f"🔧 File exclusion patterns: {len(exclude_patterns)} patterns configured"
                )

            for job_index, job in enumerate(failed_jobs, 1):
                debug_print(
                    f"🔍 [{job_index}/{len(failed_jobs)}] Analyzing job {job.name} (ID: {job.id})"
                )
                verbose_debug_print(
                    f"📋 Job details: stage={job.stage}, status={job.status}"
                )

                job_start_time = time.time()
                debug_print(f"📥 Fetching trace for job {job.id}...")
                trace = await analyzer.get_job_trace(project_id, job.id)
                trace_length = len(trace) if trace else 0
                verbose_debug_print(f"📊 Trace retrieved: {trace_length} characters")

                parser_type = (
                    "pytest"
                    if _should_use_pytest_parser(trace, job.name, job.stage)
                    else "generic"
                )
                debug_print(f"🔧 Selected parser type: {parser_type}")

                if parser_type == "pytest":
                    verbose_debug_print(
                        "🧪 Using pytest parser for detailed test failure analysis..."
                    )
                    pytest_parser = PytestLogParser()
                    parsed = pytest_parser.parse_pytest_log(trace)
                    debug_print(
                        f"📊 Pytest parsing found {len(parsed.detailed_failures)} detailed failures"
                    )

                    # Convert PytestFailureDetail objects to error dict format
                    errors: list[dict[str, Any]] = []
                    for failure_index, failure in enumerate(parsed.detailed_failures):
                        verbose_debug_print(
                            f"🔍 Processing failure {failure_index + 1}: {failure.test_name}"
                        )

                        # Classify the error type using the shared BaseParser method
                        error_message = (
                            f"{failure.exception_type}: {failure.exception_message}"
                        )
                        error_type = PytestLogParser.classify_error_type(error_message)

                        error_dict: dict[str, Any] = {
                            "exception_type": failure.exception_type,
                            "exception_message": failure.exception_message,
                            "file_path": failure.test_file,
                            "line_number": None,  # Get from traceback if available
                            "test_function": failure.test_function,
                            "test_name": failure.test_name,
                            "message": failure.exception_message,
                            "error_type": error_type,  # Add error type classification
                        }
                        # Try to get line number from traceback
                        if failure.traceback:
                            for tb in failure.traceback:
                                if tb.line_number:
                                    error_dict["line_number"] = str(tb.line_number)
                                    break
                        errors.append(error_dict)

                    # CRITICAL FIX: Use generic LogParser as fallback for pytest jobs
                    # to catch import-time errors (SyntaxError, etc.) that occur before pytest runs
                    verbose_debug_print(
                        "🔍 Running generic parser as fallback to catch import-time errors..."
                    )
                    log_parser = LogParser()
                    log_entries = log_parser.extract_log_entries(trace)
                    generic_errors = [
                        {
                            "message": entry.message,
                            "level": entry.level,
                            "line_number": (
                                str(entry.line_number)
                                if entry.line_number is not None
                                else None
                            ),
                            "context": entry.context,
                            "error_type": entry.error_type,  # Add missing error_type field
                        }
                        for entry in log_entries
                        if entry.level == "error"
                    ]
                    verbose_debug_print(
                        f"📊 Generic parser found {len(generic_errors)} additional errors"
                    )
                    # Combine pytest errors with generic errors to catch all failure types
                    errors.extend(generic_errors)
                    debug_print(f"📊 Total errors after combining: {len(errors)}")

                    # Filter duplicates between pytest and generic parser results
                    original_count = len(errors)
                    errors = _filter_duplicate_combined_errors(errors)
                    filtered_count = len(errors)
                    if original_count != filtered_count:
                        debug_print(
                            f"🔧 Filtered out {original_count - filtered_count} duplicate errors between parsers"
                        )
                else:
                    verbose_debug_print("🔧 Using generic log parser...")
                    log_parser = LogParser()
                    log_entries = log_parser.extract_log_entries(trace)
                    errors = [
                        {
                            "message": entry.message,
                            "level": entry.level,
                            "line_number": (
                                str(entry.line_number)
                                if entry.line_number is not None
                                else None
                            ),
                            "context": entry.context,
                            "error_type": entry.error_type,  # Add missing error_type field
                        }
                        for entry in log_entries
                        if entry.level == "error"
                    ]

                    debug_print(f"📊 Generic parser found {len(errors)} errors")

                # Optimize error processing: group by file path first to reduce processing
                debug_print(
                    f"🔍 Processing {len(errors)} errors for file grouping and filtering..."
                )

                # Pre-group errors by file path for efficient processing
                path_to_errors: dict[str, list] = {}

                for error in errors:
                    message = (
                        error.get("exception_message", "")
                        or error.get("message", "")
                        or ""
                    )
                    # Try to extract file path from message first
                    file_path = extract_file_path_from_message(message)

                    # If no file path found in message, try context field
                    if not file_path:
                        context = error.get("context", "")
                        if context:
                            file_path = extract_file_path_from_message(context)

                    # Fall back to error's file_path field or "unknown"
                    if not file_path:
                        file_path = error.get("file_path", "unknown") or "unknown"

                    if file_path not in path_to_errors:
                        path_to_errors[file_path] = []
                    path_to_errors[file_path].append(error)

                # Now process each file path once instead of each error individually
                file_groups: dict[str, dict[str, Any]] = {}
                filtered_errors: list[dict[str, Any]] = []
                processed_files = 0

                for file_path, errors_for_file in path_to_errors.items():
                    processed_files += 1
                    if processed_files % 50 == 0:  # Less verbose logging
                        debug_print(
                            f"🔍 Processing file {processed_files}/{len(path_to_errors)}: {file_path}"
                        )

                    # Check filtering once per file instead of per error
                    should_filter = False
                    if not disable_file_filtering:
                        if file_path != "unknown":
                            should_filter = should_exclude_file_path(
                                file_path, exclude_patterns
                            )
                        else:
                            # For "unknown" file paths, check if any error has valuable context
                            has_valuable_context = False
                            for error in errors_for_file:
                                error_context = error.get("context", "")
                                error_level = error.get("level", "")
                                error_msg = (
                                    error.get("exception_message", "")
                                    or error.get("message", "")
                                ).lower()

                                if (
                                    "syntaxerror" in error_msg
                                    or "traceback" in error_context.lower()
                                    or 'file "' in error_context.lower()
                                    or error_level == "error"
                                ):
                                    has_valuable_context = True
                                    break

                            should_filter = not has_valuable_context

                    if should_filter:
                        verbose_debug_print(
                            f"🚫 Filtering out {len(errors_for_file)} errors from {file_path} (excluded path)"
                        )
                        continue  # Skip all errors from this file

                    verbose_debug_print(
                        f"✅ Keeping {len(errors_for_file)} errors from {file_path}"
                    )

                    # Process all errors for this file
                    file_groups[file_path] = {
                        "file_path": file_path,
                        "error_count": len(errors_for_file),
                        "errors": [],
                    }

                    for error in errors_for_file:
                        # Update error dictionary with extracted file path for storage
                        error["file"] = file_path
                        if error.get("line_number"):
                            try:
                                error["line"] = int(error["line_number"])
                            except (ValueError, TypeError):
                                error["line"] = 0
                        else:
                            error["line"] = 0

                        filtered_errors.append(error)
                        file_groups[file_path]["errors"].append(error)

                # Print filtering results
                original_error_count = len(errors)
                filtered_error_count = len(filtered_errors)
                filtered_out_count = original_error_count - filtered_error_count
                debug_print(
                    f"📊 Error filtering results: {original_error_count} → {filtered_error_count} errors (filtered out: {filtered_out_count})"
                )
                debug_print(f"📁 Files with errors: {len(file_groups)}")

                categorized = categorize_files_by_type(list(file_groups.values()))
                verbose_debug_print(
                    f"📊 File categorization: {len(categorized)} categories"
                )

                # Store file and error info in DB (using filtered data)
                if store_in_db:
                    verbose_debug_print("💾 Storing job analysis data in database...")
                    # Calculate trace hash for consistency tracking
                    trace_hash = hashlib.sha256(trace.encode("utf-8")).hexdigest()
                    verbose_debug_print(
                        f"🔒 Calculated trace hash: {trace_hash[:12]}..."
                    )

                    # Convert error dictionaries to ErrorRecord objects for trace storage
                    error_records = []
                    for i, error_dict in enumerate(filtered_errors):
                        error_record = ErrorRecord.from_parsed_error(
                            job_id=job.id, error_data=error_dict, error_index=i
                        )
                        error_records.append(error_record)
                    verbose_debug_print(
                        f"📋 Created {len(error_records)} error records for storage"
                    )

                    # Store trace segments per error with context
                    verbose_debug_print("💾 Storing error trace segments...")
                    await cache_manager.store_error_trace_segments(
                        job_id=job.id,
                        trace_text=trace,
                        trace_hash=trace_hash,
                        errors=error_records,  # Use ErrorRecord objects
                        parser_type=parser_type,
                    )

                    # Store just the errors using the standard storage method
                    # Note: Job metadata was already stored correctly by store_failed_jobs_basic()
                    verbose_debug_print("💾 Storing errors using standard method...")

                    analysis_data = {
                        "errors": filtered_errors,
                        "parser_type": parser_type,
                        "trace_hash": trace_hash,
                    }
                    # Store only errors and trace segments without overwriting job metadata
                    # (job metadata was already stored correctly by store_failed_jobs_basic)
                    loop = asyncio.get_event_loop()
                    await loop.run_in_executor(
                        None,
                        cache_manager.store_errors_only,
                        job.id,
                        analysis_data,
                    )
                    verbose_debug_print("✅ Database storage completed")

                job_duration = time.time() - job_start_time
                debug_print(
                    f"✅ Job {job.name} analysis completed in {job_duration:.2f}s"
                )

                job_analysis_results.append(
                    {
                        "job_id": job.id,
                        "job_name": job.name,
                        "parser_type": parser_type,
                        "file_groups": list(file_groups.values()),
                        "categorized_files": categorized,
                        "errors": filtered_errors,  # Use filtered errors
                        "filtering_stats": {
                            "original_errors": original_error_count,
                            "filtered_errors": filtered_error_count,
                            "excluded_errors": filtered_out_count,
                        },
                    }
                )

            debug_print(
                "📊 Step 5: Building analysis results and resource structure..."
            )
            # Prepare analysis results - store in resources for later access
            # (failed_stages and failure_reasons are available in the stored data)

            # Build hierarchical resources structure with files and errors
            verbose_debug_print("🏗️ Creating resource hierarchy...")
            resources: dict[str, Any] = {
                "pipeline": f"gl://pipeline/{project_id}/{pipeline_id}",
                "jobs": f"gl://jobs/{project_id}/pipeline/{pipeline_id}",
                "files": {},
                "jobs_detail": {},
                "errors": {},
            }

            # Create file hierarchy with error links
            all_files: dict[
                str, dict[str, Any]
            ] = {}  # Global file registry across all jobs
            all_errors: dict[
                str, dict[str, Any]
            ] = {}  # Global error registry with trace references

            for job_result in job_analysis_results:
                job_id = job_result["job_id"]
                job_name = job_result["job_name"]

                # Add job-specific resources
                resources["jobs_detail"][str(job_id)] = {
                    "job": f"gl://job/{project_id}/{pipeline_id}/{job_id}",
                    "errors": f"gl://errors/{project_id}/{job_id}",
                    "files": {},
                }

                # Process file groups for this job
                file_groups_data = cast(
                    "list[dict[str, Any]]", job_result.get("file_groups", [])
                )
                for file_group in file_groups_data:
                    file_path = file_group["file_path"]
                    error_count = file_group["error_count"]

                    # Add individual error resources with trace references
                    errors_list = cast("list[dict[str, Any]]", file_group["errors"])
                    for i, error in enumerate(errors_list):
                        error_id = f"{job_id}_{i}"
                        error_resource_uri = (
                            f"gl://error/{project_id}/{job_id}/{error_id}"
                        )

                        # Add to global errors registry
                        all_errors[error_id] = {
                            "error": error_resource_uri,
                            "job_id": job_id,
                            "file_path": file_path,
                            "error_index": i,
                            "message": error.get("message", ""),
                            "line_number": error.get("line_number"),
                            "level": error.get("level", "error"),
                            "exception_type": error.get("exception_type"),
                            "test_function": error.get("test_function"),
                            "test_name": error.get("test_name"),
                        }

                    # Add to job-specific files
                    safe_file_path = file_path if file_path else "unknown"
                    resources["jobs_detail"][str(job_id)]["files"][safe_file_path] = {
                        "file": f"gl://file/{project_id}/{job_id}/{safe_file_path.replace('/', '%2F')}",
                        "error_count": error_count,
                        "errors": f"gl://errors/{project_id}/{job_id}/{safe_file_path.replace('/', '%2F')}",
                    }

                    # Add to global file registry (accumulate across jobs)
                    if safe_file_path not in all_files:
                        all_files[safe_file_path] = {
                            "path": safe_file_path,
                            "total_error_count": 0,
                            "jobs": {},
                        }

                    all_files[safe_file_path]["total_error_count"] += error_count
                    all_files[safe_file_path]["jobs"][str(job_id)] = {
                        "job_name": job_name,
                        "error_count": error_count,
                        "resource": f"gl://file/{project_id}/{job_id}/{safe_file_path.replace('/', '%2F')}",
                    }

            # Add global file hierarchy and errors to resources
            resources["files"] = all_files
            resources["errors"] = all_errors

            # Extract key information for summary
            source_branch = pipeline_info.get("source_branch") or pipeline_info.get(
                "target_branch", "unknown"
            )
            pipeline_sha = (
                pipeline_info.get("sha", "unknown")[:8]
                if pipeline_info.get("sha")
                else "unknown"
            )
            total_files = len(all_files)
            total_errors = len(all_errors)

            debug_print(
                f"📊 Analysis summary: {len(failed_jobs)} failed jobs, {total_files} files, {total_errors} errors"
            )
            verbose_debug_print(f"📋 Pipeline: {source_branch} @ {pipeline_sha}")

            # Create lightweight content-based response
            verbose_debug_print("📝 Building response content...")
            content = [
                {
                    "type": "text",
                    "text": f"Analyzed pipeline {pipeline_id} ({source_branch} @ {pipeline_sha}): {len(failed_jobs)} failed jobs, {total_files} files impacted, {total_errors} errors found.",
                },
                {
                    "type": "resource_link",
                    "resourceUri": f"gl://pipeline/{project_id}/{pipeline_id}",
                    "text": "Pipeline details & metadata",
                },
            ]

            # Add jobs resource if include_jobs_resource is True
            if include_jobs_resource:
                verbose_debug_print("📋 Adding jobs resource link to response")
                content.append(
                    {
                        "type": "resource_link",
                        "resourceUri": f"gl://jobs/{project_id}/pipeline/{pipeline_id}",
                        "text": f"Failed jobs overview ({len(failed_jobs)} jobs)",
                    }
                )

            # Add files resource if we have files with errors and include_files_resource is True
            if total_files > 0 and include_files_resource:
                verbose_debug_print("📁 Adding files resource link to response")
                # Show pagination hint for large file sets
                if total_files > 20:
                    content.append(
                        {
                            "type": "resource_link",
                            "resourceUri": f"gl://files/{project_id}/pipeline/{pipeline_id}/page/1/limit/20",
                            "text": f"Files with errors (page 1 of {(total_files + 19) // 20})",
                        }
                    )
                else:
                    content.append(
                        {
                            "type": "resource_link",
                            "resourceUri": f"gl://files/{project_id}/pipeline/{pipeline_id}",
                            "text": f"Files with errors ({total_files} files)",
                        }
                    )

            # Add errors resource if we have errors and include_errors_resource is True
            if total_errors > 0 and include_errors_resource:
                verbose_debug_print("⚠️ Adding errors resource link to response")
                content.append(
                    {
                        "type": "resource_link",
                        "resourceUri": f"gl://errors/{project_id}/pipeline/{pipeline_id}",
                        "text": f"Error details (page 1 of {(total_errors + 49) // 50})",
                    }
                )

            result = {
                "content": content,
                "mcp_info": get_mcp_info("failed_pipeline_analysis"),
            }

            # Add timing information
            end_time = time.time()
            total_duration = end_time - start_time
            debug_print(
                f"✅ Failed pipeline analysis completed successfully in {total_duration:.2f}s"
            )
            if isinstance(result, dict):
                result["debug_timing"] = {"duration_seconds": round(total_duration, 3)}

            return result

        except (ValueError, TypeError, KeyError, RuntimeError) as e:
            end_time = time.time()
            total_duration = end_time - start_time
            error_print(
                f"❌ Failed pipeline analysis error after {total_duration:.2f}s: {e}"
            )
            return {
                "content": [
                    {
                        "type": "text",
                        "text": f"❌ Failed to analyze pipeline {pipeline_id}: {str(e)}",
                    }
                ],
                "mcp_info": get_mcp_info("failed_pipeline_analysis", error=True),
            }
