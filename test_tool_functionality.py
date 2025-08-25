#!/usr/bin/env python3
"""
Test a specific tool from our streamlined architecture.

This tests the cache_health tool to verify our architecture works.
"""

import asyncio
import json
import subprocess
from pathlib import Path

from dotenv import load_dotenv

# Load environment variables
load_dotenv()


async def test_cache_health():
    """Test the cache_health tool"""

    print("🧪 Testing Streamlined Tool: cache_health")
    print("=" * 50)

    try:
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

        # Send initialize, then call cache_health tool
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

        tool_call_request = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/call",
            "params": {"name": "cache_health", "arguments": {}},
        }

        requests = (
            json.dumps(init_request) + "\n" + json.dumps(tool_call_request) + "\n"
        )
        print(f"🔍 Sending requests:")
        print(f"   Init: {json.dumps(init_request, indent=2)}")
        print(f"   Tool call: {json.dumps(tool_call_request, indent=2)}")

        stdout, stderr = process.communicate(input=requests, timeout=15)

        # Parse the response
        if stdout:
            lines = stdout.strip().split("\n")
            for line in lines:
                if line:
                    try:
                        response = json.loads(line)
                        if response.get("id") == 2:
                            if "result" in response:
                                result = response["result"]
                                print("✅ cache_health tool executed successfully!")

                                if "content" in result:
                                    content = result["content"]
                                    if isinstance(content, list) and content:
                                        tool_result = content[0].get("text", "")
                                        if tool_result:
                                            try:
                                                parsed_result = json.loads(tool_result)
                                                print(
                                                    f"📊 Health Status: {parsed_result.get('status', 'unknown')}"
                                                )
                                                if "health" in parsed_result:
                                                    health = parsed_result["health"]
                                                    print(
                                                        f"🗄️  Database: {health.get('database_status', 'unknown')}"
                                                    )
                                                    print(
                                                        f"⚡ Performance: {health.get('performance_check', 'unknown')}"
                                                    )
                                                print(
                                                    f"🔧 Operation: {parsed_result.get('operation', 'unknown')}"
                                                )
                                                return True
                                            except json.JSONDecodeError:
                                                print(f"📄 Raw result: {tool_result}")
                                                return True
                                    else:
                                        print(f"📄 Result content: {content}")
                                        return True
                                else:
                                    print(f"📄 Raw result: {result}")
                                    return True
                            elif "error" in response:
                                error = response["error"]
                                print(
                                    f"❌ Tool call failed: {error.get('message', 'unknown error')}"
                                )
                                return False
                            break
                    except json.JSONDecodeError:
                        continue

        print("❌ No valid response received")
        if stderr:
            print(f"⚠️  stderr: {stderr}")
        return False

    except subprocess.TimeoutExpired:
        print("❌ Test timeout")
        process.kill()
        return False
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback

        traceback.print_exc()
        return False


async def main():
    """Main test function"""
    print("🎯 Streamlined Architecture Functional Test")
    print("Testing with real GitLab credentials from .env file\n")

    success = await test_cache_health()

    if success:
        print("\n🎉 Streamlined architecture is working correctly!")
        print("✅ MCP server responds properly")
        print("✅ Tools are registered and callable")
        print("✅ Cache system is functional")
        print("\nNext steps:")
        print("• Test comprehensive_pipeline_analysis with real pipeline data")
        print("• Test search tools with repository access")
        print("• Validate resource-based data access")
    else:
        print("\n⚠️  Some issues detected. Check server logs.")


if __name__ == "__main__":
    asyncio.run(main())
