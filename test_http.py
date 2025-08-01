#!/usr/bin/env python3
"""
Test HTTP transport functionality

Simple test script to verify the HTTP server is working.
"""

import asyncio
import os
import httpx


async def test_http_server():
    """Test if the HTTP MCP server is responding"""

    server_url = os.getenv("MCP_SERVER_URL", "http://127.0.0.1:8000/mcp")

    print(f"Testing HTTP MCP server at: {server_url}")

    try:
        async with httpx.AsyncClient() as client:
            # Test basic connectivity
            response = await client.post(
                server_url,
                json={"jsonrpc": "2.0", "id": 1, "method": "ping", "params": {}},
                headers={"Content-Type": "application/json"},
            )

            print(f"Status: {response.status_code}")
            print(f"Response: {response.text}")

            if response.status_code == 200:
                print("✅ HTTP server is responding!")
            else:
                print("❌ HTTP server returned error status")

    except Exception as e:
        print(f"❌ Failed to connect: {e}")
        print("Make sure the HTTP server is running with: python http_server.py")


if __name__ == "__main__":
    asyncio.run(test_http_server())
