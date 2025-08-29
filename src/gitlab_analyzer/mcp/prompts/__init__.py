"""
MCP prompts for agent guidance

Copyright (c) 2025 Siarhei Skuratovich
Licensed under the MIT License - see LICENSE file for details
"""

from .advanced import register_advanced_prompts
from .debugging import register_debugging_prompts
from .educational import register_educational_prompts
from .investigation import register_investigation_prompts
from .performance import register_performance_prompts

__all__ = [
    "register_investigation_prompts",
    "register_debugging_prompts",
    "register_advanced_prompts",
    "register_performance_prompts",
    "register_educational_prompts",
]


def register_all_prompts(mcp) -> None:
    """Register all prompt types with the MCP server"""
    register_investigation_prompts(mcp)
    register_debugging_prompts(mcp)
    register_advanced_prompts(mcp)
    register_performance_prompts(mcp)
    register_educational_prompts(mcp)
