"""
MCP tools package for GitLab Pipeline Analyzer - Streamlined Version

Only essential tools following DRY and KISS principles:
1. Comprehensive pipeline analysis with intelligent parsing
2. Search tools for repository content
3. Cache management tools

All other functionality moved to pure functions and accessed via resources.

Copyright (c) 2025 Siarhei Skuratovich
Licensed under the MIT License - see LICENSE file for details
"""

from fastmcp import FastMCP

from .cache_tools import register_cache_tools
from .search_tools import register_search_tools
from .streamlined_analysis import register_streamlined_analysis_tools
from .utils import get_gitlab_analyzer


def register_tools(mcp: FastMCP) -> None:
    """Register only essential MCP tools with the FastMCP instance"""
    register_streamlined_analysis_tools(mcp)
    register_search_tools(mcp)
    register_cache_tools(mcp)


__all__ = [
    "register_tools",
    "register_streamlined_analysis_tools",
    "register_search_tools",
    "register_cache_tools",
    "get_gitlab_analyzer",
]
