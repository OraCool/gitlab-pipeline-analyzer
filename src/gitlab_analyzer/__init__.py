"""
GitLab Pipeline Analyzer MCP Server

A FastMCP server that analyzes GitLab CI/CD pipeline failures, extracts errors
and warnings from job traces, and returns structured JSON responses for AI
analysis.

Copyright (c) 2025 Siarhei Skuratovich
Licensed under the MIT License - see LICENSE file for details
"""

from .api.client import GitLabAnalyzer
from .mcp.servers.server import create_server
from .models import JobInfo, LogEntry, PipelineAnalysis
from .parsers.log_parser import LogParser
from .utils.utils import get_gitlab_analyzer

__all__ = [
    "JobInfo",
    "LogEntry",
    "PipelineAnalysis",
    "GitLabAnalyzer",
    "LogParser",
    "create_server",
    "get_gitlab_analyzer",
]
