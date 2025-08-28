"""
Clean Trace Tools for MCP Server

This module provides tools and resources for accessing raw, unprocessed job traces
without full analysis overhead.

Copyright (c) 2025 Siarhei Skuratovich
Licensed under the MIT License - see LICENSE file for details
"""

from typing import Any

from fastmcp import FastMCP

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
        🔍 CLEAN TRACE: Get raw, unprocessed job trace without analysis overhead.

        WHEN TO USE:
        - Need raw trace data for debugging
        - Want to see exactly what GitLab CI produced
        - Investigating parser issues
        - Manual error analysis

        FEATURES:
        - Direct GitLab API access
        - No parsing or processing
        - Optional file saving
        - Multiple output formats

        Args:
            project_id: The GitLab project ID
            job_id: The specific job ID to get trace for
            save_to_file: Whether to save trace to a local file
            output_format: Output format - 'text' for plain text, 'json' for structured

        Returns:
            Raw trace content with metadata

        EXAMPLES:
        - get_clean_job_trace(83, 76986695) - Get raw trace
        - get_clean_job_trace(83, 76986695, save_to_file=True) - Save to file
        """
        try:
            analyzer = get_gitlab_analyzer()

            # Get raw trace from GitLab
            trace_content = await analyzer.get_job_trace(project_id, job_id)

            if not trace_content:
                return {
                    "status": "no_trace",
                    "message": f"No trace found for job {job_id}",
                    "project_id": str(project_id),
                    "job_id": str(job_id),
                    "trace_length": 0,
                    "trace_lines": 0,
                }

            # Calculate basic stats
            lines = trace_content.split("\n")
            trace_length = len(trace_content)
            trace_lines = len(lines)

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
                from pathlib import Path

                output_file = Path(f"clean_trace_{project_id}_{job_id}.log")
                output_file.write_text(trace_content, encoding="utf-8")
                result["saved_to"] = str(output_file)

            # Format output
            if output_format == "json":
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
            else:
                # For text format, include full trace
                result["trace_content"] = trace_content

            result["mcp_info"] = get_mcp_info("get_clean_job_trace")

            return result

        except Exception as e:
            return {
                "status": "error",
                "message": str(e),
                "project_id": str(project_id),
                "job_id": str(job_id),
                "mcp_info": get_mcp_info("get_clean_job_trace"),
            }

    @mcp.resource("trace://{project_id}/{job_id}")
    async def get_raw_trace_resource(project_id: str, job_id: str) -> str:
        """
        📄 RAW TRACE RESOURCE: Direct access to unprocessed job trace content.

        Access via: trace://project_id/job_id

        Returns the complete, unprocessed trace content as plain text.
        Perfect for debugging, manual analysis, or when you need the exact
        output that GitLab CI produced.
        """
        try:
            analyzer = get_gitlab_analyzer()
            trace_content = await analyzer.get_job_trace(project_id, job_id)

            if not trace_content:
                return f"No trace found for job {job_id} in project {project_id}"

            return trace_content

        except Exception as e:
            return f"Error retrieving trace for job {job_id}: {str(e)}"
