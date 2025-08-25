#!/usr/bin/env python3
"""
Display available MCP tools in the streamlined GitLab Pipeline Analyzer.

This script shows what tools are available in our streamlined architecture.
"""

import asyncio
import json
import subprocess
import sys
from pathlib import Path

from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))


async def main():
    """Display available tools via MCP client"""

    print("🛠️  GitLab Pipeline Analyzer - Streamlined Tools")
    print("=" * 60)

    try:
        # Use subprocess to call the MCP server and get tools list

        # Start the server process
        cmd = ["uv", "run", "gitlab-analyzer"]
        process = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=Path(__file__).parent,
        )

        # Send initialize and tools/list requests
        init_request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {}},
                "clientInfo": {"name": "display-client", "version": "1.0.0"},
            },
        }

        tools_request = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/list",
            "params": {},
        }

        requests = json.dumps(init_request) + "\n" + json.dumps(tools_request) + "\n"
        stdout, stderr = process.communicate(input=requests, timeout=10)

        # Parse the response
        tools_found = []
        if stdout:
            lines = stdout.strip().split("\n")
            for line in lines:
                if line:
                    try:
                        response = json.loads(line)
                        if response.get("id") == 2 and "result" in response:
                            tools = response["result"].get("tools", [])
                            for tool in tools:
                                tools_found.append(
                                    {
                                        "name": tool.get("name", "unknown"),
                                        "description": tool.get(
                                            "description", "No description"
                                        ),
                                    }
                                )
                            break
                    except json.JSONDecodeError:
                        continue

        print(f"📊 Total Tools: {len(tools_found)}")
        print("🎯 Architecture: Streamlined (DRY/KISS principles)")
        print("⚡ Framework: FastMCP v2.11.1\n")

        # Display each tool
        for i, tool in enumerate(tools_found, 1):
            print(f"{i}️⃣  {tool['name']}")
            description = tool["description"]
            # Extract first meaningful line
            first_line = (
                description.split("\n")[0].strip() if description else "No description"
            )
            print(f"   {first_line[:100]}...")
            print()

        if not tools_found:
            print("⚠️  No tools found via MCP client. Showing expected tools:")
            expected_tools = [
                "comprehensive_pipeline_analysis - Complete pipeline failure analysis",
                "search_repository_code - Search repository code files",
                "search_repository_commits - Search commit messages",
                "clear_cache - Clear cached data",
                "cache_stats - Get cache statistics",
                "cache_health - Check cache health",
            ]
            for i, tool in enumerate(expected_tools, 1):
                print(f"{i}️⃣  {tool}")

        print("\n✅ Streamlined Architecture Benefits:")
        print("• Reduced from 21 tools to 6 essential tools")
        print("• DRY principle: No duplicate functionality")
        print("• KISS principle: Simple, focused tools")
        print("• Resource-based access via gl:// URIs")
        print("• Intelligent caching and analysis")
        print("• Clean separation of concerns")

    except Exception as e:
        print(f"❌ Error displaying tools: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
