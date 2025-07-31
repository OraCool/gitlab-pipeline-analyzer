"""
FastMCP server creation and configuration
"""

import os
from fastmcp import FastMCP
from .tools import register_tools


def create_server() -> FastMCP:
    """Create and configure the FastMCP server"""
    # Initialize FastMCP server
    mcp = FastMCP(
        name="GitLab Pipeline Analyzer",
        instructions="""
        Analyze GitLab CI/CD pipelines for errors and warnings
        """,
    )

    # Register all tools
    register_tools(mcp)
    return mcp


def load_env_file():
    """Load environment variables from .env file if it exists"""
    env_file = os.path.join(os.path.dirname(__file__), "..", "..", "..", ".env")
    if os.path.exists(env_file):
        with open(env_file, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    os.environ[key] = value
