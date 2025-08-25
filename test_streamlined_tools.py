#!/usr/bin/env python3
"""
Test script for streamlined architecture with real GitLab data.

This tests our 6 streamlined tools:
1. comprehensive_pipeline_analysis
2. search_repository_code
3. search_repository_commits
4. clear_cache
5. cache_stats
6. cache_health
"""

import asyncio
import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))


async def test_streamlined_tools():
    """Test our streamlined tools with real data"""

    # Check if GitLab credentials are available
    gitlab_url = os.getenv("GITLAB_URL")
    gitlab_token = os.getenv("GITLAB_TOKEN")

    if not gitlab_url or not gitlab_token:
        print("❌ Missing GitLab credentials!")
        print("Please set GITLAB_URL and GITLAB_TOKEN environment variables")
        return

    print(f"🔗 GitLab URL: {gitlab_url}")
    print(
        f"🔑 Token: {'*' * 20}{gitlab_token[-4:] if len(gitlab_token) > 4 else '****'}"
    )

    # Create MCP server with our tools
    mcp = FastMCP("test-server")
    register_tools(mcp)

    print("\n=== Streamlined Tools Test ===")
    print("✅ MCP Server created successfully")
    print(f"✅ Registered {len(mcp._tools)} tools:")

    # List available tools
    for tool_name in sorted(mcp._tools.keys()):
        print(f"   • {tool_name}")

    # Test 1: Try to call cache_health through MCP
    print("\n1️⃣ Testing cache_health...")
    try:
        # Get the tool function
        cache_health_tool = mcp._tools.get("cache_health")
        if cache_health_tool:
            result = await cache_health_tool()
            print(f"✅ Cache Health: {result.get('status', 'unknown')}")
            if "health" in result:
                health_data = result["health"]
                print(f"   Database: {health_data.get('database_status', 'unknown')}")
                print(
                    f"   Performance: {health_data.get('performance_check', 'unknown')}"
                )
        else:
            print("❌ cache_health tool not found")
    except Exception as e:
        print(f"❌ Cache health failed: {e}")

    # Test 2: Cache Stats
    print("\n2️⃣ Testing cache_stats...")
    try:
        cache_stats_tool = mcp._tools.get("cache_stats")
        if cache_stats_tool:
            result = await cache_stats_tool()
            if "stats" in result:
                stats = result["stats"]
                total_entries = stats.get("summary", {}).get("total_entries", 0)
                print(f"✅ Cache Stats: {total_entries} total entries")

                if "by_type" in stats:
                    for data_type, count in stats["by_type"].items():
                        if count > 0:
                            print(f"   {data_type}: {count}")
            else:
                print(f"✅ Cache Stats result: {result.get('status', 'unknown')}")
        else:
            print("❌ cache_stats tool not found")
    except Exception as e:
        print(f"❌ Cache stats failed: {e}")

    # Test 3: Search Tools - Search for common terms
    print("\n3️⃣ Testing search_repository_code...")
    try:
        search_tool = mcp._tools.get("search_repository_code")
        if search_tool:
            # Test with a project - adjust project_id as needed
            result = await search_tool(
                project_id="83",  # Replace with a project you have access to
                search_keywords="import",
                extension_filter="py",
                max_results=3,
            )
            if isinstance(result, str):
                lines = result.split("\n")[:5]  # Show first 5 lines
                print("✅ Code Search completed:")
                for line in lines:
                    if line.strip():
                        print(f"   {line}")
                if len(result.split("\n")) > 5:
                    print("   ... (truncated)")
            else:
                print(f"✅ Code Search result type: {type(result)}")
        else:
            print("❌ search_repository_code tool not found")
    except Exception as e:
        print(f"❌ Code search failed: {e}")

    # Test 4: Pipeline Analysis (if we have access to a failed pipeline)
    print("\n4️⃣ Testing comprehensive_pipeline_analysis...")
    try:
        analysis_tool = mcp._tools.get("comprehensive_pipeline_analysis")
        if analysis_tool:
            # Use a test project and pipeline - adjust as needed
            result = await analysis_tool(
                project_id="83",  # Replace with your project
                pipeline_id=1594344,  # Replace with a pipeline you have access to
                use_cache=True,
                store_in_db=True,
            )

            if "error" in result:
                print(f"❌ Pipeline analysis error: {result['error']}")
            else:
                print("✅ Pipeline Analysis completed:")
                if "pipeline_info" in result:
                    pipeline_info = result["pipeline_info"]
                    print(f"   Pipeline ID: {pipeline_info.get('id', 'N/A')}")
                    print(f"   Status: {pipeline_info.get('status', 'N/A')}")
                    print(f"   Branch: {pipeline_info.get('target_branch', 'N/A')}")

                if "analysis_summary" in result:
                    summary = result["analysis_summary"]
                    print(f"   Failed jobs: {summary.get('total_failed_jobs', 0)}")
                    print(f"   Total errors: {summary.get('total_errors', 0)}")

                if "resource_uris" in result:
                    print("   Available resources:")
                    for name, uri in result["resource_uris"].items():
                        print(f"     {name}: {uri}")
        else:
            print("❌ comprehensive_pipeline_analysis tool not found")
    except Exception as e:
        print(f"❌ Pipeline analysis failed: {e}")

    print("\n🎉 Streamlined Architecture Test Complete!")
    print("\nOur 6-tool streamlined architecture includes:")
    print("• Pipeline Analysis: comprehensive_pipeline_analysis")
    print("• Search: search_repository_code, search_repository_commits")
    print("• Cache Management: clear_cache, cache_stats, cache_health")


if __name__ == "__main__":
    asyncio.run(test_streamlined_tools())
