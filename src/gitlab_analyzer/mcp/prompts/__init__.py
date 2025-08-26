"""
MCP prompts for agent guidance

Copyright (c) 2025 Siarhei Skuratovich
Licensed under the MIT License - see LICENSE file for details
"""

from .debugging import register_debugging_prompts
from .investigation import register_investigation_prompts

__all__ = [
    "register_investigation_prompts",
    "register_debugging_prompts",
]


def register_all_prompts(mcp) -> None:
    """Register all prompt types with the MCP server"""
    register_investigation_prompts(mcp)
    register_debugging_prompts(mcp)
