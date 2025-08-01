#!/usr/bin/env python3
"""
GitLab Pipeline Analyzer MCP Server

Copyright (c) 2025 Siarhei Skuratovich
Licensed under the MIT License - see LICENSE file for details
"""

import argparse
import os

from gitlab_analyzer.mcp.server import create_server, load_env_file


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


if __name__ == "__main__":
    main()
