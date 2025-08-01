#!/usr/bin/env python3
"""
Test HTTP transport functionality

Simple test script to verify the HTTP server is working.
"""

import asyncio
import os
from pathlib import Path

import httpx


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


async def test_http_server():
    """Test if the HTTP MCP server is responding"""

    # Load environment variables from .env file
    load_env_file()

    server_url = os.getenv("MCP_SERVER_URL", "http://127.0.0.1:8000/mcp")

    print(f"Testing HTTP MCP server at: {server_url}")

    try:
        async with httpx.AsyncClient(follow_redirects=True) as client:
            print("🔍 Testing basic connectivity...")

            # Test tools/list - proper MCP method
            response = await client.post(
                server_url,
                json={"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}},
                headers={
                    "Content-Type": "application/json",
                    "Accept": "application/json, text/event-stream",
                },
            )

            print(f"Status: {response.status_code}")

            if response.status_code == 200:
                print("✅ HTTP server is responding!")
                result = response.json()
                print(f"Response keys: {list(result.keys())}")

                # Check if we got a proper MCP response
                if "result" in result and "tools" in result["result"]:
                    tools = result["result"]["tools"]
                    print(f"📋 Found {len(tools)} tools:")
                    for tool in tools:
                        print(
                            f"  - {tool.get('name', 'Unknown')}: {tool.get('description', 'No description')}"
                        )
                elif "error" in result:
                    print(f"❌ MCP Error: {result['error']}")
                else:
                    print("⚠️  Response doesn't contain expected MCP structure")
                    print(f"Full response: {result}")

            elif response.status_code == 307:
                print("📍 Got redirect (307) - this might be normal for FastMCP")
                print(f"Location header: {response.headers.get('location', 'None')}")
            else:
                print("❌ HTTP server returned error status")
                print(f"Response: {response.text}")

    except Exception as e:
        print(f"❌ Failed to connect: {e}")
        print("Make sure the HTTP server is running with: python http_server.py")


if __name__ == "__main__":
    asyncio.run(test_http_server())
