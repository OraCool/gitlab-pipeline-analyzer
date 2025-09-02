"""
FastMCP server creation and configuration

Copyright (c) 2025 Siarhei Skuratovich
Licensed under the MIT License - see LICENSE file for details
"""

import argparse
import os
from pathlib import Path

from fastmcp import FastMCP

from gitlab_analyzer.mcp.prompts import register_all_prompts
from gitlab_analyzer.mcp.resources import register_all_resources
from gitlab_analyzer.mcp.tools import register_tools
from gitlab_analyzer.utils.debug import (
    debug_print,
    error_print,
    startup_print,
)
from gitlab_analyzer.version import get_version


def create_server() -> FastMCP:
    """Create and configure the FastMCP server"""
    version = get_version()

    # Initialize FastMCP server
    mcp: FastMCP = FastMCP(
        name=f"GitLab Pipeline Analyzer v{version}",
        version=version,
        instructions=f"""
        Analyze GitLab CI/CD pipelines for errors and warnings

        This server provides comprehensive pipeline analysis with intelligent caching.
        Available resources: pipelines, jobs, analysis results, and error details.
        Use prompts for guided investigation workflows.

        GitLab Pipeline Analyzer v{version}
        """,
    )

    # Cache manager will be initialized when server starts
    # Note: We don't initialize here to avoid event loop issues

    # Register all tools, resources, and prompts
    register_tools(mcp)
    register_all_resources(mcp)
    register_all_prompts(mcp)
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

    # Initialize cache before running server
    async def startup():
        """Initialize cache when server starts with comprehensive debug information"""
        try:
            startup_print(
                f"🚀 [STARTUP] Initializing GitLab Pipeline Analyzer MCP Server (transport: {args.transport})..."
            )

            from gitlab_analyzer.cache.mcp_cache import get_cache_manager

            # Get database path from environment variable or use default
            db_path = os.environ.get("MCP_DATABASE_PATH")
            debug_print(f"🔧 [DEBUG] Database path from env: {db_path}")

            if db_path:
                debug_print(f"🔧 [DEBUG] Using custom database path: {db_path}")
            else:
                debug_print("🔧 [DEBUG] Using default database path: analysis_cache.db")

            # Debug environment variables
            debug_print("🔧 [DEBUG] Environment variables:")
            for key in [
                "MCP_DATABASE_PATH",
                "GITLAB_URL",
                "GITLAB_TOKEN",
                "MCP_HOST",
                "MCP_PORT",
                "MCP_PATH",
                "MCP_TRANSPORT",
                "MCP_DEBUG_LEVEL",
            ]:
                value = os.environ.get(key)
                if key == "GITLAB_TOKEN" and value:
                    # Mask token for security
                    masked_value = f"{value[:8]}..." if len(value) > 8 else "***"
                    debug_print(f"🔧 [DEBUG]   {key}: {masked_value}")
                else:
                    debug_print(f"🔧 [DEBUG]   {key}: {value}")

            debug_print("🔧 [DEBUG] Attempting to initialize cache manager...")
            # Cache is initialized in constructor, just ensure it's created
            get_cache_manager(db_path)
            startup_print("✅ [STARTUP] Cache manager initialized successfully")
            # No need to call initialize() - it's done in __init__

        except Exception as e:
            error_print(f"❌ [STARTUP ERROR] Failed to initialize server: {e}")
            error_print(f"❌ [STARTUP ERROR] Exception type: {type(e).__name__}")
            import traceback

            error_print("❌ [STARTUP ERROR] Traceback:")
            traceback.print_exc()
            raise

    # Run server with proper cache initialization
    if args.transport == "stdio":
        import asyncio

        async def run_stdio():
            await startup()
            await mcp.run_stdio_async()

        asyncio.run(run_stdio())
    elif args.transport == "http":
        import asyncio

        async def run_http():
            await startup()
            await mcp.run_http_async(host=args.host, port=args.port, path=args.path)

        asyncio.run(run_http())
    elif args.transport == "sse":
        import asyncio

        async def run_sse():
            await startup()
            await mcp.run_sse_async(host=args.host, port=args.port)

        asyncio.run(run_sse())
