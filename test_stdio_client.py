#!/usr/bin/env python3
"""
Test client for STDIO MCP server

This script tests the GitLab Pipeline Analyzer MCP server using STDIO transport.
"""

import asyncio
import os
from fastmcp import Client


async def test_pipeline_analysis():
    """Test pipeline analysis using STDIO client"""
    # Set environment variables
    os.environ["GITLAB_URL"] = "https://gitbud.epam.com"
    os.environ["GITLAB_TOKEN"] = "W118SktdLchfwe11ejqs"

    print("🚀 Starting STDIO MCP client test...")

    client = Client("server.py")
    async with client:
        print("✅ Connected to MCP server")

        # Test pipeline analysis
        print("🔍 Analyzing pipeline 623320 for project 19133...")
        result = await client.call_tool(
            "analyze_failed_pipeline", {"project_id": "19133", "pipeline_id": 623320}
        )

        print("📊 Analysis Result:")
        if hasattr(result, "content") and len(result.content) > 0:
            content = result.content[0]
            if hasattr(content, "text"):
                print(content.text)
            else:
                print(content)
        else:
            print(result)


if __name__ == "__main__":
    asyncio.run(test_pipeline_analysis())
