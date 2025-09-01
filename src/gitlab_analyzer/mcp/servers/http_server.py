#!/usr/bin/env python3
"""
GitLab Pipeline Analyzer MCP HTTP Server

Copyright (c) 2025 Siarhei Skuratovich
Licensed under the MIT License - see LICENSE file for details
"""

import asyncio
import os

from gitlab_analyzer.cache.mcp_cache import get_cache_manager
from gitlab_analyzer.mcp.servers.server import create_server, load_env_file


async def startup():
    """Initialize cache when server starts with comprehensive debug information"""
    try:
        print("🚀 [STARTUP] Initializing GitLab Pipeline Analyzer HTTP Server...")

        # Get database path from environment variable or use default
        db_path = os.environ.get("MCP_DATABASE_PATH")
        print(f"🔧 [DEBUG] Database path from env: {db_path}")

        if db_path:
            print(f"🔧 [DEBUG] Using custom database path: {db_path}")
        else:
            print("🔧 [DEBUG] Using default database path: analysis_cache.db")

        # Debug environment variables
        print("🔧 [DEBUG] Environment variables:")
        for key in [
            "MCP_DATABASE_PATH",
            "GITLAB_URL",
            "GITLAB_TOKEN",
            "MCP_HOST",
            "MCP_PORT",
            "MCP_PATH",
        ]:
            value = os.environ.get(key)
            if key == "GITLAB_TOKEN" and value:
                # Mask token for security
                masked_value = f"{value[:8]}..." if len(value) > 8 else "***"
                print(f"🔧 [DEBUG]   {key}: {masked_value}")
            else:
                print(f"🔧 [DEBUG]   {key}: {value}")

        print("🔧 [DEBUG] Attempting to initialize cache manager...")
        # Cache is initialized in constructor, just ensure it's created
        get_cache_manager(db_path)
        print("✅ [STARTUP] Cache manager initialized successfully")

    except Exception as e:
        print(f"❌ [STARTUP ERROR] Failed to initialize cache manager: {e}")
        print(f"❌ [STARTUP ERROR] Exception type: {type(e).__name__}")
        import traceback

        print("❌ [STARTUP ERROR] Traceback:")
        traceback.print_exc()
        raise


async def run_http_server():
    """Run the HTTP server asynchronously"""
    load_env_file()
    mcp = create_server()

    host = os.getenv("MCP_HOST", "127.0.0.1")
    port = int(os.getenv("MCP_PORT", "8000"))
    path = os.getenv("MCP_PATH", "/mcp")

    print(f"Starting GitLab Pipeline Analyzer MCP Server on http://{host}:{port}{path}")

    # Initialize cache before starting server
    await startup()

    # Run HTTP server asynchronously
    await mcp.run_http_async(host=host, port=port, path=path)


def main() -> None:
    """Main entry point for HTTP server"""
    asyncio.run(run_http_server())


if __name__ == "__main__":
    main()
