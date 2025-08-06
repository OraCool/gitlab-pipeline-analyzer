#!/usr/bin/env python3
"""
GitLab Pipeline Analyzer MCP SSE Server

Copyright (c) 2025 Siarhei Skuratovich
Licensed under the MIT License - see LICENSE file for details
"""

import os

from gitlab_analyzer.mcp.servers.server import create_server, load_env_file


def main() -> None:
    """Main entry point for SSE server"""
    load_env_file()
    mcp = create_server()

    host = os.getenv("MCP_HOST", "127.0.0.1")
    port = int(os.getenv("MCP_PORT", "8000"))

    print(f"Starting GitLab Pipeline Analyzer MCP SSE Server on http://{host}:{port}")
    mcp.run(transport="sse", host=host, port=port)


if __name__ == "__main__":
    main()
