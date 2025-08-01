"""
FastMCP server creation and configuration

Copyright (c) 2025 Siarhei Skuratovich
Licensed under the MIT License - see LICENSE file for details
"""

import os
from pathlib import Path

from fastmcp import FastMCP

from .tools import register_tools


def create_server() -> FastMCP:
    """Create and configure the FastMCP server"""
    # Initialize FastMCP server
    mcp: FastMCP = FastMCP(
        name="GitLab Pipeline Analyzer",
        instructions="""
        Analyze GitLab CI/CD pipelines for errors and warnings
        """,
    )

    # Register all tools
    register_tools(mcp)
    return mcp


def load_env_file() -> None:
    """Load environment variables from .env file if it exists"""
    env_file = Path(__file__).parent / ".." / ".." / ".." / ".env"
    if env_file.exists():
        with env_file.open(encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    os.environ[key] = value
