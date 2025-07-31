#!/usr/bin/env python3
"""
GitLab Pipeline Analyzer MCP Server

Copyright (c) 2025 Siarhei Skuratovich
Licensed under the MIT License - see LICENSE file for details
"""

from gitlab_analyzer.mcp.server import create_server, load_env_file


def main() -> None:
    """Main entry point"""
    load_env_file()
    mcp = create_server()
    mcp.run()


if __name__ == "__main__":
    main()
