"""
FastMCP server creation and configuration

Copyright (c) 2025 Siarhei Skuratovich
Licensed under the MIT License - see LICENSE file for details
"""

import argparse
import os
from pathlib import Path

from fastmcp import FastMCP

from gitlab_analyzer.mcp.tools import register_tools

# Get version from pyproject.toml to avoid circular imports


def get_version() -> str:
    """Get version from pyproject.toml"""
    try:
        pyproject_path = (
            Path(__file__).parent / ".." / ".." / ".." / ".." / "pyproject.toml"
        )
        if pyproject_path.exists():
            content = pyproject_path.read_text(encoding="utf-8")
            for line in content.split("\n"):
                if line.startswith("version = "):
                    return line.split('"')[1]
    except Exception:  # nosec B110
        # Fallback if pyproject.toml cannot be read
        pass
    return "0.2.2"  # fallback version


def create_server() -> FastMCP:
    """Create and configure the FastMCP server"""
    version = get_version()

    # Initialize FastMCP server
    mcp: FastMCP = FastMCP(
        name=f"GitLab Pipeline Analyzer v{version}",
        version=version,
        instructions=f"""
        Analyze GitLab CI/CD pipelines for errors and warnings

        GitLab Pipeline Analyzer v{version}
        """,
    )

    # Register all tools
    register_tools(mcp)
    return mcp


def load_env_file() -> None:
    """Load environment variables from .env file if it exists"""
    env_file = Path(__file__).parent / ".." / ".." / ".." / ".." / ".env"
    if env_file.exists():
        with env_file.open(encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    os.environ[key] = value


def main() -> None:
    """Main entry point"""
    parser = argparse.ArgumentParser(description="GitLab Pipeline Analyzer MCP Server")
    parser.add_argument(
        "--transport",
        choices=["stdio", "http", "sse"],
        default=os.environ.get("MCP_TRANSPORT", "stdio"),
        help="Transport protocol to use (default: stdio)",
    )
    parser.add_argument(
        "--host",
        default=os.environ.get("MCP_HOST", "127.0.0.1"),
        help="Host to bind to for HTTP/SSE transport (default: 127.0.0.1)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.environ.get("MCP_PORT", "8000")),
        help="Port to bind to for HTTP/SSE transport (default: 8000)",
    )
    parser.add_argument(
        "--path",
        default=os.environ.get("MCP_PATH", "/mcp"),
        help="Path for HTTP transport (default: /mcp)",
    )

    args = parser.parse_args()

    load_env_file()
    mcp = create_server()

    if args.transport == "stdio":
        mcp.run(transport="stdio")
    elif args.transport == "http":
        mcp.run(transport="http", host=args.host, port=args.port, path=args.path)
    elif args.transport == "sse":
        mcp.run(transport="sse", host=args.host, port=args.port)
