"""
MCP resources for static data access

Copyright (c) 2025 Siarhei Skuratovich
Licensed under the MIT License - see LICENSE file for details
"""

from .analysis import register_analysis_resources
from .error import register_error_resources
from .file import register_file_resources
from .job import register_job_resources
from .pipeline import register_pipeline_resources

__all__ = [
    "register_pipeline_resources",
    "register_job_resources",
    "register_analysis_resources",
    "register_error_resources",
    "register_file_resources",
]


def register_all_resources(mcp) -> None:
    """Register all resource types with the MCP server"""
    register_pipeline_resources(mcp)
    register_job_resources(mcp)
    register_analysis_resources(mcp)
    register_error_resources(mcp)
    register_file_resources(mcp)
