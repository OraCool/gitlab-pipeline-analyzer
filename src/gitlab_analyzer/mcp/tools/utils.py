"""
Utilities for MCP tools

Copyright (c) 2025 Siarhei Skuratovich
Licensed under the MIT License - see LICENSE file for details
"""

# Re-export optimize_tool_response from utils
from gitlab_analyzer.utils.utils import optimize_tool_response

# Global analyzer instance for testing purposes
_GITLAB_ANALYZER = None

__all__ = ["optimize_tool_response", "_GITLAB_ANALYZER"]
