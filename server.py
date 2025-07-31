#!/usr/bin/env python3
"""
GitLab Pipeline Analyzer MCP Server
"""

from gitlab_analyzer.mcp.server import create_server, load_env_file


def main() -> None:
    """Main entry point"""
    load_env_file()
    mcp = create_server()
    mcp.run()


if __name__ == "__main__":
    main()
