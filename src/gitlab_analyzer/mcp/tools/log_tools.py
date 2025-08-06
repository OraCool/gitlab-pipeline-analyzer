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
        Extract errors and warnings from log text.

        Args:
            log_text: The log text to analyze

        Returns:
            Extracted errors and warnings with context
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
                if entry.level == "error"
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
