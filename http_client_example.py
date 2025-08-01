#!/usr/bin/env python3
"""
Example HTTP client for GitLab Pipeline Analyzer MCP Server

This demonstrates how to connect to the MCP server over HTTP transport.
"""

import asyncio
import os

from fastmcp.client import Client


async def main():
    """Example of connecting to the MCP server via HTTP"""

    # Configuration for HTTP transport
    server_url = os.getenv("MCP_SERVER_URL", "http://127.0.0.1:8000/mcp")

    print(f"Connecting to MCP server at: {server_url}")

    try:
        async with Client(server_url) as client:
            print("✅ Connected successfully!")

            # List available tools
            print("\n📋 Available tools:")
            tools_result = await client.list_tools()
            for tool in tools_result.tools:
                print(f"  - {tool.name}: {tool.description}")

            # Example: Analyze a pipeline (replace with actual project/pipeline IDs)
            project_id = input(
                "\nEnter GitLab project ID (or press Enter to skip): "
            ).strip()
            if project_id:
                pipeline_id = input("Enter pipeline ID: ").strip()
                if pipeline_id:
                    print(
                        f"\n🔍 Analyzing pipeline {pipeline_id} in project {project_id}..."
                    )
                    try:
                        result = await client.call_tool(
                            "analyze_pipeline",
                            {"project_id": project_id, "pipeline_id": pipeline_id},
                        )
                        print("📊 Analysis result:")
                        print(
                            result.content[0].text
                            if result.content
                            else "No content returned"
                        )
                    except Exception as e:
                        print(f"❌ Error analyzing pipeline: {e}")

            print("\n✅ Demo completed successfully!")

    except Exception as e:
        print(f"❌ Failed to connect to MCP server: {e}")
        print("Make sure the HTTP server is running with: python http_server.py")


if __name__ == "__main__":
    asyncio.run(main())
