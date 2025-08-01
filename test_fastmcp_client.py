#!/usr/bin/env python3
"""
Test HTTP transport using FastMCP client

This test uses the proper FastMCP client to test HTTP transport.
"""

import asyncio
import os
from pathlib import Path

from fastmcp.client import Client


def load_env_file() -> None:
    """Load environment variables from .env file if it exists"""
    env_file = Path(__file__).parent / ".env"
    if env_file.exists():
        with env_file.open(encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    os.environ[key] = value


async def test_fastmcp_client():
    """Test the HTTP MCP server using FastMCP client"""

    # Load environment variables from .env file
    load_env_file()

    server_url = os.getenv("MCP_SERVER_URL", "http://127.0.0.1:8000/mcp")

    print(f"🔍 Testing FastMCP client connection to: {server_url}")

    try:
        async with Client(server_url) as client:
            print("✅ Successfully connected to MCP server!")

            # List available tools
            print("\n📋 Listing available tools...")
            tools_result = await client.list_tools()

            print(f"Tools result type: {type(tools_result)}")
            print(f"Tools result: {tools_result}")

            # Handle different possible return types
            if hasattr(tools_result, "tools"):
                tools = tools_result.tools
            elif isinstance(tools_result, list):
                tools = tools_result
            elif hasattr(tools_result, "result") and hasattr(
                tools_result.result, "tools"
            ):
                tools = tools_result.result.tools
            else:
                tools = []
                print(f"Unexpected tools result format: {tools_result}")

            if tools:
                print(f"Found {len(tools)} tools:")
                for tool in tools:
                    name = getattr(tool, "name", str(tool))
                    description = getattr(tool, "description", "No description")
                    print(f"  - {name}: {description}")

                # Test calling one of the tools (if any exist)
                if tools:
                    first_tool = tools[0]
                    tool_name = getattr(first_tool, "name", str(first_tool))
                    print(f"\n🧪 Testing tool: {tool_name}")

                    # For demo purposes, let's try with some basic parameters
                    try:
                        if tool_name in ["analyze_pipeline", "get_failed_jobs"]:
                            print(
                                "  (Skipping tool test - requires real project/pipeline IDs)"
                            )
                        else:
                            result = await client.call_tool(tool_name, {})
                            print(
                                f"  Result: {result.content[0].text if result.content else 'No content'}"
                            )
                    except Exception as tool_error:
                        print(f"  ⚠️  Tool test failed: {tool_error}")
            else:
                print("No tools found!")

            # List resources if any
            print("\n📂 Listing available resources...")
            resources_result = await client.list_resources()

            # Handle different possible return types
            if hasattr(resources_result, "resources"):
                resources = resources_result.resources
            elif isinstance(resources_result, list):
                resources = resources_result
            else:
                resources = []
                print(f"Unexpected resources result format: {resources_result}")

            if resources:
                print(f"Found {len(resources)} resources:")
                for resource in resources:
                    name = getattr(resource, "name", str(resource))
                    description = getattr(resource, "description", "No description")
                    print(f"  - {name}: {description}")
            else:
                print("No resources found!")

            print("\n✅ HTTP transport test completed successfully!")

    except Exception as e:
        print(f"❌ Failed to connect to MCP server: {e}")
        print("Make sure the HTTP server is running with: python http_server.py")


if __name__ == "__main__":
    asyncio.run(test_fastmcp_client())
