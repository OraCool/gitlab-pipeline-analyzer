"""
Trace Analysis Tools for MCP Server

This module provides tools for parsing raw CI/CD traces and extracting errors
without storing results in database - pure analysis functionality.

Copyright (c) 2025 Siarhei Skuratovich
Licensed under the MIT License - see LICENSE file for details
"""

import time
from typing import Any, cast

from fastmcp import FastMCP

from gitlab_analyzer.parsers.log_parser import LogParser
from gitlab_analyzer.parsers.pytest_parser import PytestLogParser
from gitlab_analyzer.utils.debug import debug_print, error_print, verbose_debug_print


def register_trace_analysis_tools(mcp: FastMCP) -> None:
    """Register trace analysis tools"""

    @mcp.tool
    async def parse_trace_for_errors(
        trace_content: str,
        analysis_type: str = "auto",
        include_warnings: bool = True,
        include_context: bool = True,
        filter_duplicates: bool = True,
    ) -> dict[str, Any]:
        """
        🔍 TRACE PARSER: Parse raw CI/CD trace content and extract errors without database storage.

        Pure analysis tool that processes trace content and returns structured error information.
        Supports automatic detection of trace type (general logs vs pytest) or manual selection.

        WHEN TO USE:
        - Analyze trace content from any source (file, API, clipboard)
        - Extract errors without storing results in database
        - Quick error analysis for troubleshooting
        - Validate trace content before processing
        - Educational/debugging purposes

        ANALYSIS TYPES:
        - "auto": Automatically detect if pytest trace or general log
        - "general": Use general log parser for standard CI/CD traces
        - "pytest": Use pytest-specific parser for test execution traces
        - "both": Run both parsers and return combined results

        FEATURES:
        - Pure analysis - no database storage
        - Automatic trace type detection
        - Error categorization and classification
        - Context extraction around errors
        - Duplicate filtering
        - Performance timing

        Args:
            trace_content: Raw trace content to analyze
            analysis_type: Type of analysis ("auto", "general", "pytest", "both")
            include_warnings: Whether to include warning-level entries
            include_context: Whether to include context around errors
            filter_duplicates: Whether to filter out duplicate errors

        Returns:
            Structured analysis with errors, statistics, and metadata

        EXAMPLES:
        - parse_trace_for_errors(trace_text) - Auto-detect and parse
        - parse_trace_for_errors(trace_text, "pytest") - Force pytest parsing
        - parse_trace_for_errors(trace_text, "general", include_warnings=False) - Errors only
        """
        start_time = time.time()

        debug_print(f"Starting trace analysis - analysis_type: {analysis_type}")
        debug_print(f"Trace size: {len(trace_content)} characters")
        debug_print(
            f"Options: warnings={include_warnings}, context={include_context}, filter_duplicates={filter_duplicates}"
        )

        try:
            # Clean the trace content
            verbose_debug_print("Cleaning ANSI sequences from trace content")
            cleaned_trace = LogParser.clean_ansi_sequences(trace_content)
            verbose_debug_print(f"Cleaned trace size: {len(cleaned_trace)} characters")

            # Determine analysis type
            actual_analysis_type = analysis_type
            if analysis_type == "auto":
                verbose_debug_print("Auto-detecting trace type")
                actual_analysis_type = _detect_trace_type(cleaned_trace)
                debug_print(f"Auto-detected trace type: {actual_analysis_type}")

            results = {}

            # Perform analysis based on type
            if actual_analysis_type == "general" or actual_analysis_type == "both":
                verbose_debug_print("Running general log analysis")
                general_start = time.time()

                # Extract log entries using general parser
                log_entries = LogParser.extract_log_entries(cleaned_trace)
                debug_print(f"General parser found {len(log_entries)} log entries")

                # Filter by level if needed
                if not include_warnings:
                    log_entries = [
                        entry for entry in log_entries if entry.level == "error"
                    ]
                    debug_print(f"After filtering warnings: {len(log_entries)} entries")

                # Filter duplicates if requested
                if filter_duplicates:
                    original_count = len(log_entries)
                    log_entries = _filter_duplicate_entries(log_entries)
                    debug_print(
                        f"After duplicate filtering: {len(log_entries)} entries (removed {original_count - len(log_entries)})"
                    )

                # Convert to detailed format
                general_errors = []
                for entry in log_entries:
                    error_detail = {
                        "message": entry.message,
                        "level": entry.level,
                        "line_number": entry.line_number,
                        "error_type": entry.error_type,
                        "categorization": LogParser.categorize_error(
                            entry.message, entry.context if include_context else ""
                        ),
                    }

                    if include_context and entry.context:
                        error_detail["context"] = entry.context

                    general_errors.append(error_detail)

                general_duration = time.time() - general_start
                verbose_debug_print(
                    f"General analysis completed in {general_duration:.3f}s"
                )

                results["general_analysis"] = {
                    "errors": general_errors,
                    "total_entries": len(general_errors),
                    "error_count": len(
                        [e for e in general_errors if e["level"] == "error"]
                    ),
                    "warning_count": len(
                        [e for e in general_errors if e["level"] == "warning"]
                    ),
                    "processing_time": general_duration,
                }

            if actual_analysis_type == "pytest" or actual_analysis_type == "both":
                verbose_debug_print("Running pytest-specific analysis")
                pytest_start = time.time()

                # Use pytest parser
                pytest_analysis = PytestLogParser.parse_pytest_log(cleaned_trace)
                debug_print(
                    f"Pytest parser found {len(pytest_analysis.detailed_failures)} detailed failures"
                )

                # Convert pytest results to consistent format
                pytest_errors = []

                # Process detailed failures
                for failure in pytest_analysis.detailed_failures:
                    error_detail = {
                        "message": f"Test failure in {failure.test_function}",
                        "level": "error",
                        "line_number": failure.line_number,
                        "error_type": "test_failure",
                        "test_file": failure.test_file,
                        "test_function": failure.test_function,
                        "failure_reason": failure.failure_reason,
                        "categorization": {
                            "category": "Test Failure",
                            "severity": "high",
                            "description": "Pytest test execution failed",
                            "details": f"Test '{failure.test_function}' in '{failure.test_file}' failed: {failure.failure_reason}",
                            "solution": "Review test output and fix the failing test or code",
                            "impact": "Code quality issues, potential bugs",
                        },
                    }

                    if include_context and failure.traceback:
                        error_detail["traceback"] = {
                            "file_path": failure.traceback.file_path,
                            "line_number": failure.traceback.line_number,
                            "function_name": failure.traceback.function_name,
                            "code_context": failure.traceback.code_context,
                            "error_message": failure.traceback.error_message,
                        }

                    pytest_errors.append(error_detail)

                # Process short summary if available
                summary_errors = []
                if pytest_analysis.short_summary:
                    for item in pytest_analysis.short_summary.failed_tests:
                        if not any(
                            e.get("test_function") == item.test_name
                            for e in pytest_errors
                        ):
                            summary_errors.append(
                                {
                                    "message": f"Test failure: {item.test_name}",
                                    "level": "error",
                                    "error_type": "test_failure",
                                    "test_file": item.test_file,
                                    "test_function": item.test_name,
                                    "failure_reason": item.reason,
                                    "source": "short_summary",
                                }
                            )

                pytest_duration = time.time() - pytest_start
                verbose_debug_print(
                    f"Pytest analysis completed in {pytest_duration:.3f}s"
                )

                results["pytest_analysis"] = {
                    "detailed_failures": pytest_errors,
                    "summary_failures": summary_errors,
                    "total_failures": len(pytest_errors) + len(summary_errors),
                    "statistics": (
                        {
                            "passed": (
                                pytest_analysis.statistics.passed
                                if pytest_analysis.statistics
                                else 0
                            ),
                            "failed": (
                                pytest_analysis.statistics.failed
                                if pytest_analysis.statistics
                                else 0
                            ),
                            "skipped": (
                                pytest_analysis.statistics.skipped
                                if pytest_analysis.statistics
                                else 0
                            ),
                            "errors": (
                                pytest_analysis.statistics.errors
                                if pytest_analysis.statistics
                                else 0
                            ),
                            "warnings": (
                                pytest_analysis.statistics.warnings
                                if pytest_analysis.statistics
                                else 0
                            ),
                        }
                        if pytest_analysis.statistics
                        else None
                    ),
                    "processing_time": pytest_duration,
                }

            # Combine results if both analyses were run
            if actual_analysis_type == "both":
                debug_print("Combining results from both analysis types")
                # Create combined view
                all_errors: list[dict[str, Any]] = []

                if "general_analysis" in results:
                    general_analysis = results["general_analysis"]
                    if (
                        isinstance(general_analysis, dict)
                        and "errors" in general_analysis
                    ):
                        general_errors = cast(
                            "list[dict[str, Any]]", general_analysis["errors"]
                        )
                        all_errors.extend(general_errors)

                if "pytest_analysis" in results:
                    pytest_analysis = results["pytest_analysis"]
                    if isinstance(pytest_analysis, dict):
                        if "detailed_failures" in pytest_analysis:
                            pytest_detailed = pytest_analysis["detailed_failures"]
                            if isinstance(pytest_detailed, list):
                                all_errors.extend(pytest_detailed)
                        if "summary_failures" in pytest_analysis:
                            pytest_summary = pytest_analysis["summary_failures"]
                            if isinstance(pytest_summary, list):
                                all_errors.extend(pytest_summary)

                # Filter duplicates in combined results
                if filter_duplicates:
                    original_count = len(all_errors)
                    all_errors = _filter_duplicate_combined_errors(all_errors)
                    debug_print(
                        f"Combined duplicate filtering: {len(all_errors)} errors (removed {original_count - len(all_errors)})"
                    )

                results["combined_analysis"] = {
                    "all_errors": all_errors,
                    "total_errors": len(all_errors),
                    "error_count": len(
                        [e for e in all_errors if e["level"] == "error"]
                    ),
                    "warning_count": len(
                        [e for e in all_errors if e["level"] == "warning"]
                    ),
                }

            # Calculate total duration
            total_duration = time.time() - start_time
            debug_print(
                f"Trace analysis completed successfully in {total_duration:.3f}s"
            )

            # Prepare final response
            response = {
                "analysis_type": actual_analysis_type,
                "trace_info": {
                    "original_size": len(trace_content),
                    "cleaned_size": len(cleaned_trace),
                    "analysis_options": {
                        "include_warnings": include_warnings,
                        "include_context": include_context,
                        "filter_duplicates": filter_duplicates,
                    },
                },
                "results": results,
                "timing": {
                    "total_duration": total_duration,
                    "analysis_completed_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                },
                "success": True,
            }

            return response

        except Exception as e:
            error_duration = time.time() - start_time
            error_print(f"Trace analysis failed after {error_duration:.3f}s: {str(e)}")

            return {
                "analysis_type": analysis_type,
                "error": str(e),
                "timing": {"failed_after": error_duration},
                "success": False,
            }


def _detect_trace_type(trace_content: str) -> str:
    """Detect whether trace is pytest-specific or general log"""
    verbose_debug_print("Analyzing trace content for type detection")

    # Check for pytest-specific markers
    pytest_indicators = [
        "===",  # pytest section markers
        "FAILURES",
        "short test summary",
        "test session starts",
        "collected",
        "PASSED",
        "FAILED",
        "ERROR",
        "::test_",  # pytest test function format
        ".py::test_",
    ]

    pytest_score = 0
    for indicator in pytest_indicators:
        if indicator in trace_content:
            pytest_score += 1

    verbose_debug_print(
        f"Pytest indicators found: {pytest_score}/{len(pytest_indicators)}"
    )

    # If we have strong pytest indicators, use pytest parser
    if pytest_score >= 3:
        return "pytest"

    # Otherwise use general parser
    return "general"


def _filter_duplicate_entries(entries: list) -> list:
    """Filter duplicate log entries based on message similarity"""
    verbose_debug_print(f"Filtering duplicates from {len(entries)} entries")

    seen_messages = set()
    filtered_entries = []

    for entry in entries:
        # Create a normalized version of the message for duplicate detection
        normalized = entry.message.lower().strip()

        # Remove dynamic parts that might vary between duplicates
        import re

        normalized = re.sub(r"\d+", "N", normalized)  # Replace numbers
        normalized = re.sub(r"line \d+", "line N", normalized)  # Normalize line numbers

        if normalized not in seen_messages:
            seen_messages.add(normalized)
            filtered_entries.append(entry)

    verbose_debug_print(
        f"After duplicate filtering: {len(filtered_entries)} unique entries"
    )
    return filtered_entries


def _filter_duplicate_combined_errors(errors: list) -> list:
    """Filter duplicates from combined error results"""
    verbose_debug_print(f"Filtering duplicates from {len(errors)} combined errors")

    seen_messages = set()
    filtered_errors = []

    for error in errors:
        # Create a key for duplicate detection
        message = error.get("message", "")
        test_function = error.get("test_function", "")

        # Create normalized key
        key = f"{message.lower().strip()}_{test_function}"

        if key not in seen_messages:
            seen_messages.add(key)
            filtered_errors.append(error)

    verbose_debug_print(
        f"After combined duplicate filtering: {len(filtered_errors)} unique errors"
    )
    return filtered_errors
