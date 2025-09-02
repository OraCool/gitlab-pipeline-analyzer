"""
MCP tools package for GitLab Pipeline Analyzer - Streamlined Version

Only essential tools following DRY and KISS principles:
1. Comprehensive pipeline analysis with intelligent parsing
2. Search tools for repository content
3. Cache management tools
4. Clean trace access tools
5. Trace analysis tools for pure parsing without database storage

All other functionality moved to pure functions and accessed via resources.

Copyright (c) 2025 Siarhei Skuratovich
Licensed under the MIT License - see LICENSE file for details
"""

from fastmcp import FastMCP

from gitlab_analyzer.utils.utils import get_gitlab_analyzer

from .cache_tools import register_cache_tools
from .clean_trace_tools import register_clean_trace_tools
from .failed_pipeline_analysis import register_failed_pipeline_analysis_tools
from .resource_access_tools import register_resource_access_tools
from .search_tools import register_search_tools
from .trace_analysis_tools import register_trace_analysis_tools


def register_tools(mcp: FastMCP) -> None:
    """Register only essential MCP tools with the FastMCP instance"""
    register_failed_pipeline_analysis_tools(mcp)
    register_search_tools(mcp)
    register_cache_tools(mcp)
    register_resource_access_tools(mcp)
    register_clean_trace_tools(mcp)
    register_trace_analysis_tools(mcp)


__all__ = [
    "register_tools",
    "register_failed_pipeline_analysis_tools",
    "register_search_tools",
    "register_cache_tools",
    "register_resource_access_tools",
    "register_clean_trace_tools",
    "register_trace_analysis_tools",
    "get_gitlab_analyzer",
]
