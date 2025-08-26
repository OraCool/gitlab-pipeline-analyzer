"""
MCP (Model Context Protocol) integration modules
"""

from ..cache.mcp_cache import get_cache_manager
from .prompts import register_all_prompts
from .resources import register_all_resources
from .servers.server import create_server
from .tools import get_gitlab_analyzer, register_tools

__all__ = [
    "create_server",
    "get_gitlab_analyzer",
    "register_tools",
    "register_all_resources",
    "register_all_prompts",
    "get_cache_manager",
]
