"""
Clean Trace Tools for MCP Server

This module provides tools and resources for accessing raw, unprocessed job traces
without full analysis overhead.

Copyright (c) 2025 Siarhei Skuratovich
Licensed under the MIT License - see LICENSE file for details
"""

import time
from typing import Any

from fastmcp import FastMCP

from gitlab_analyzer.parsers.base_parser import BaseParser
from gitlab_analyzer.utils.debug import debug_print, error_print, verbose_debug_print
from gitlab_analyzer.utils.utils import get_gitlab_analyzer, get_mcp_info


def register_clean_trace_tools(mcp: FastMCP) -> None:
    """Register clean trace access tools"""

    @mcp.tool
    async def get_clean_job_trace(
        project_id: str | int,
        job_id: int,
        save_to_file: bool = False,
        output_format: str = "text",
    ) -> dict[str, Any]:
        """
        🔍 CLEAN TRACE: Get cleaned, human-readable job trace without analysis overhead.

        WHEN TO USE:
        - Need clean trace data for debugging (ANSI sequences removed)
        - Want to see readable GitLab CI output without color codes
        - Investigating parser issues with clean text
        - Manual error analysis on readable logs

        FEATURES:
        - Direct GitLab API access
        - ANSI escape sequence cleaning for readability
        - Optional file saving
        - Multiple output formats

        Args:
            project_id: The GitLab project ID
            job_id: The specific job ID to get trace for
            save_to_file: Whether to save cleaned trace to a local file
            output_format: Output format - 'text' for plain text, 'json' for structured

        Returns:
            Cleaned trace content with metadata (ANSI sequences removed)

        EXAMPLES:
        - get_clean_job_trace(123, 76986695) - Get cleaned trace
        - get_clean_job_trace(123, 76986695, save_to_file=True) - Save cleaned trace to file
        """
        start_time = time.time()
        debug_print(
            f"🧹 Starting clean trace retrieval for job {job_id} in project {project_id}"
        )
        verbose_debug_print(
            f"📋 Clean trace options: save_to_file={save_to_file}, output_format={output_format}"
        )

        try:
            analyzer = get_gitlab_analyzer()
            verbose_debug_print("🔗 GitLab analyzer instance obtained")

            # Get raw trace from GitLab
            debug_print(f"📥 Fetching raw trace from GitLab for job {job_id}...")
            trace_content = await analyzer.get_job_trace(project_id, job_id)

            if not trace_content:
                error_print(
                    f"❌ No trace found for job {job_id} in project {project_id}"
                )
                return {
                    "status": "no_trace",
                    "message": f"No trace found for job {job_id}",
                    "project_id": str(project_id),
                    "job_id": str(job_id),
                    "trace_length": 0,
                    "trace_lines": 0,
                    "debug_timing": {
                        "duration_seconds": round(time.time() - start_time, 3)
                    },
                }

            raw_length = len(trace_content)
            verbose_debug_print(f"📊 Raw trace retrieved: {raw_length} characters")

            # Clean ANSI escape sequences to make trace readable
            debug_print("🧹 Cleaning ANSI escape sequences from trace...")
            cleaned_trace = BaseParser.clean_ansi_sequences(trace_content)

            # Calculate basic stats
            lines = cleaned_trace.split("\n")
            trace_length = len(cleaned_trace)
            trace_lines = len(lines)
            verbose_debug_print(
                f"📊 Cleaned trace: {trace_length} characters, {trace_lines} lines"
            )

            result = {
                "status": "success",
                "project_id": str(project_id),
                "job_id": str(job_id),
                "trace_length": trace_length,
                "trace_lines": trace_lines,
                "format": output_format,
            }

            # Save to file if requested
            if save_to_file:
                debug_print("💾 Saving cleaned trace to file...")
                from pathlib import Path

                output_file = Path(f"clean_trace_{project_id}_{job_id}.log")
                output_file.write_text(cleaned_trace, encoding="utf-8")
                result["saved_to"] = str(output_file)
                verbose_debug_print(f"✅ Trace saved to: {output_file}")

            # Format output
            debug_print(f"📝 Formatting output as: {output_format}")
            if output_format == "json":
                verbose_debug_print(
                    "📊 Building JSON format with preview and error indicators..."
                )
                # For JSON format, include trace excerpts
                result.update(
                    {
                        "trace_preview": {
                            "first_10_lines": lines[:10],
                            "last_10_lines": lines[-10:] if len(lines) > 10 else lines,
                            "sample_lines": (
                                lines[:: max(1, len(lines) // 20)][:20]
                                if len(lines) > 40
                                else lines
                            ),
                        }
                    }
                )

                # Look for key error indicators
                syntax_errors = [
                    i for i, line in enumerate(lines) if "SyntaxError:" in line
                ]
                make_errors = [
                    i
                    for i, line in enumerate(lines)
                    if "make:" in line and "Error" in line
                ]

                result["error_indicators"] = {
                    "syntax_errors_at_lines": syntax_errors,
                    "make_errors_at_lines": make_errors,
                    "has_traceback": any(
                        "Traceback (most recent call last):" in line for line in lines
                    ),
                }
                verbose_debug_print(
                    f"🔍 Error indicators found: {len(syntax_errors)} syntax errors, {len(make_errors)} make errors"
                )
            else:
                verbose_debug_print("📄 Including full trace content in text format")
                # For text format, include cleaned trace
                result["trace_content"] = cleaned_trace

            result["mcp_info"] = get_mcp_info("get_clean_job_trace")

            # Add timing information
            end_time = time.time()
            duration = end_time - start_time
            result["debug_timing"] = {"duration_seconds": round(duration, 3)}
            debug_print(f"✅ Clean trace retrieval completed in {duration:.3f}s")

            return result

        except Exception as e:
            end_time = time.time()
            duration = end_time - start_time
            error_print(
                f"❌ Error retrieving clean trace for job {job_id} after {duration:.3f}s: {e}"
            )
            return {
                "status": "error",
                "message": str(e),
                "project_id": str(project_id),
                "job_id": str(job_id),
                "mcp_info": get_mcp_info("get_clean_job_trace"),
                "debug_timing": {"duration_seconds": round(duration, 3)},
            }

    @mcp.resource("trace://{project_id}/{job_id}")
    async def get_raw_trace_resource(project_id: str, job_id: str) -> str:
        """
        📄 CLEAN TRACE RESOURCE: Direct access to cleaned job trace content.

        Access via: trace://project_id/job_id

        Returns the complete trace content with ANSI escape sequences removed,
        making it perfect for human reading, debugging, manual analysis, or when
        you need clean text output that GitLab CI produced.
        """
        try:
            analyzer = get_gitlab_analyzer()
            trace_content = await analyzer.get_job_trace(project_id, int(job_id))

            if not trace_content:
                return f"No trace found for job {job_id} in project {project_id}"

            # Clean ANSI escape sequences for readable output
            cleaned_trace = BaseParser.clean_ansi_sequences(trace_content)
            return cleaned_trace

        except Exception as e:
            return f"Error retrieving trace for job {job_id}: {str(e)}"
