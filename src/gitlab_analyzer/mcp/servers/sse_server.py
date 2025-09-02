#!/usr/bin/env python3
"""
GitLab Pipeline Analyzer MCP SSE Server

Copyright (c) 2025 Siarhei Skuratovich
Licensed under the MIT License - see LICENSE file for details
"""

import asyncio
import os

from gitlab_analyzer.cache.mcp_cache import get_cache_manager
from gitlab_analyzer.mcp.servers.server import create_server, load_env_file
from gitlab_analyzer.utils.debug import (
    debug_print,
    error_print,
    startup_print,
)


async def startup():
    """Initialize cache when server starts with comprehensive debug information"""
    try:
        startup_print(
            "🚀 [STARTUP] Initializing GitLab Pipeline Analyzer SSE Server..."
        )

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

    except Exception as e:
        error_print(f"❌ [STARTUP ERROR] Failed to initialize cache manager: {e}")
        error_print(f"❌ [STARTUP ERROR] Exception type: {type(e).__name__}")
        import traceback

        error_print("❌ [STARTUP ERROR] Traceback:")
        traceback.print_exc()
        raise


async def run_sse_server():
    """Run the SSE server asynchronously"""
    load_env_file()
    mcp = create_server()

    host = os.getenv("MCP_HOST", "127.0.0.1")
    port = int(os.getenv("MCP_PORT", "8000"))

    startup_print(
        f"Starting GitLab Pipeline Analyzer MCP SSE Server on http://{host}:{port}"
    )

    # Initialize cache before starting server
    await startup()

    # Run SSE server asynchronously
    await mcp.run_sse_async(host=host, port=port)


def main() -> None:
    """Main entry point for SSE server"""
    asyncio.run(run_sse_server())


if __name__ == "__main__":
    main()
