#!/usr/bin/env python3
"""
Simple test script for streamlined architecture using MCP stdio interface.

This tests our streamlined tools via the actual MCP server.
"""

import asyncio
import json
import subprocess
from pathlib import Path

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


async def test_mcp_tools():
    """Test MCP tools via stdio interface"""

    print("🧪 Testing Streamlined MCP Architecture")
    print("=" * 50)

    # Test 1: Initialize MCP server and list tools
    print("\n1️⃣ Testing MCP server initialization...")

    try:
        # Start the server and send initialize request
        cmd = ["uv", "run", "gitlab-analyzer"]
        process = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=Path(__file__).parent,
        )

        # Send initialize request
        init_request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {}},
                "clientInfo": {"name": "test-client", "version": "1.0.0"},
            },
        }

        request_str = json.dumps(init_request) + "\n"
        stdout, stderr = process.communicate(input=request_str, timeout=10)

        if stdout:
            try:
                response = json.loads(stdout.strip())
                if "result" in response and "capabilities" in response["result"]:
                    tools = response["result"]["capabilities"].get("tools", {})
                    print("✅ MCP server initialized successfully")
                    print(
                        f"   Protocol version: {response['result'].get('protocolVersion', 'unknown')}"
                    )
                    print(f"   Tools available: {tools}")
                else:
                    print(f"❌ Unexpected response format: {response}")
            except json.JSONDecodeError as e:
                print(f"❌ Failed to parse JSON response: {e}")
                print(f"   Raw stdout: {stdout}")
        else:
            print("❌ No response from server")

        if stderr:
            print(f"   stderr: {stderr}")

    except subprocess.TimeoutExpired:
        print("❌ Server timeout")
        process.kill()
    except Exception as e:
        print(f"❌ Test failed: {e}")

    # Test 2: Test tools/list to see our streamlined tools
    print("\n2️⃣ Testing tools/list...")

    try:
        cmd = ["uv", "run", "gitlab-analyzer"]
        process = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=Path(__file__).parent,
        )

        # Send initialize first, then tools/list
        init_request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {}},
                "clientInfo": {"name": "test-client", "version": "1.0.0"},
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

        if stdout:
            lines = stdout.strip().split("\n")
            for line in lines:
                if line:
                    try:
                        response = json.loads(line)
                        if response.get("id") == 2 and "result" in response:
                            tools = response["result"].get("tools", [])
                            print(f"✅ Found {len(tools)} streamlined tools:")
                            for tool in tools:
                                print(
                                    f"   - {tool.get('name', 'unknown')}: {tool.get('description', 'no description')[:80]}..."
                                )
                            break
                    except json.JSONDecodeError:
                        continue
        else:
            print("❌ No response for tools/list")

    except subprocess.TimeoutExpired:
        print("❌ Tools list timeout")
        process.kill()
    except Exception as e:
        print(f"❌ Tools list failed: {e}")

    print("\n🎉 Streamlined Architecture Test Complete!")
    print("\nOur architecture now contains only essential tools:")
    print("1. comprehensive_pipeline_analysis - Complete failure analysis")
    print("2. search_repository_code - Code search")
    print("3. search_repository_commits - Commit search")
    print("4. clear_cache - Cache cleanup")
    print("5. cache_stats - Cache statistics")
    print("6. cache_health - Cache monitoring")


if __name__ == "__main__":
    asyncio.run(test_mcp_tools())
