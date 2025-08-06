"""
Log analysis MCP tools for GitLab Pipeline Analyzer

Copyright (c) 2025 Siarhei Skuratovich
Licensed under the MIT License - see LICENSE file for details
"""

from datetime import datetime
from typing import Any

from fastmcp import FastMCP

from gitlab_analyzer.parsers.log_parser import LogParser

from .pytest_tools import _extract_pytest_errors
from .utils import _is_pytest_log


def register_log_tools(mcp: FastMCP) -> None:
    """Register log analysis tools"""

    @mcp.tool
    async def extract_log_errors(log_text: str) -> dict[str, Any]:
        """
        🔧 PARSE LOGS: Extract errors and warnings from raw log text using advanced pattern matching.

        WHEN TO USE:
        - Have raw log content that needs error extraction
        - Want to apply consistent error parsing to any log format
        - Need to categorize and structure unstructured log data

        WHAT YOU GET:
        - Structured list of errors and warnings with context
        - Error categorization (build, test, syntax, import, etc.)
        - Line numbers and surrounding context for each issue
        - Summary statistics (error count, warning count)

        AI ANALYSIS TIPS:
        - Focus on "error" level entries for critical issues
        - Check "category" field for error type classification
        - Use "context" for understanding error environment
        - Look at "line_number" for precise error location

        Args:
            log_text: The log text to analyze

        Returns:
            Extracted errors and warnings with context and categorization

        WORKFLOW: Use with get_cleaned_job_trace output → provides structured error analysis
        """
        try:
            # Auto-detect pytest logs and use specialized parser
            if _is_pytest_log(log_text):
                return _extract_pytest_errors(log_text)

            # Use generic log parser for non-pytest logs
            entries = LogParser.extract_log_entries(log_text)

            errors = [
                {
                    "level": entry.level,
                    "message": entry.message,
                    "line_number": entry.line_number,
                    "timestamp": entry.timestamp,
                    "context": entry.context,
                }
                for entry in entries
                if entry.level
                in ["error", "critical"]  # Include both error and critical levels
            ]

            warnings = [
                {
                    "level": entry.level,
                    "message": entry.message,
                    "line_number": entry.line_number,
                    "timestamp": entry.timestamp,
                    "context": entry.context,
                }
                for entry in entries
                if entry.level == "warning"
            ]

            return {
                "total_entries": len(entries),
                "errors": errors,
                "warnings": warnings,
                "error_count": len(errors),
                "warning_count": len(warnings),
                "analysis_timestamp": datetime.now().isoformat(),
            }

        except Exception as e:
            return {"error": f"Failed to extract log errors: {str(e)}"}
