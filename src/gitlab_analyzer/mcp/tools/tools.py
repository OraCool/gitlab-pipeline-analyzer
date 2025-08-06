"""
MCP tool functions for GitLab Pipeline Analyzer - Legacy compatibility module

Copyright (c) 2025 Siarhei Skuratovich
Licensed under the MIT License - see LICENSE file for details

This module provides backward compatibility while tools are refactored
into separate modules. Import from tools/ package instead.
"""

from fastmcp import FastMCP

from gitlab_analyzer.mcp.tools.analysis_tools import register_analysis_tools
from gitlab_analyzer.mcp.tools.info_tools import register_info_tools
from gitlab_analyzer.mcp.tools.log_tools import register_log_tools
from gitlab_analyzer.mcp.tools.pytest_tools import register_pytest_tools
from gitlab_analyzer.mcp.tools.utils import get_gitlab_analyzer

__all__ = [
    "register_tools",
    "get_gitlab_analyzer",
    "register_analysis_tools",
    "register_info_tools",
    "register_log_tools",
    "register_pytest_tools",
]


def register_tools(mcp: FastMCP) -> None:
    """Register all MCP tools with the FastMCP instance"""
    register_analysis_tools(mcp)
    register_info_tools(mcp)
    register_log_tools(mcp)
    register_pytest_tools(mcp)
