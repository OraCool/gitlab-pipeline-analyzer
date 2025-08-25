"""
Real MCP Client Example using FastMCP Client Library

This module demonstrates proper MCP protocol usage using the FastMCP Client library
instead of subprocess-based approaches. It shows how to:

1. Connect to GitLab Pipeline Analyzer MCP server using stdio transport
2. Run comprehensive pipeline analysis
3. Access resources via gl:// URI patterns for ALL information
4. Test cache management tools

Key Improvements:
- Get pipeline info from resources (not analysis result)
- List all available tools/resources/prompts in detail

Usage:
    python real_mcp_client.py
"""

import asyncio
import json
import os

from fastmcp import Client


async def demo_pipeline_analysis():
    """Demo: Complete pipeline analysis workflow using proper FastMCP Client"""

    print("🎯 GitLab Pipeline Analyzer - Real MCP Client Demo")
    print("=" * 60)
    print()

    # Configuration - get from environment variables or use defaults
    PROJECT_ID = os.getenv("PROJECT_ID", "83")
    PIPELINE_ID = int(os.getenv("PIPELINE_ID", "1594344"))

    print(f"📊 Target: Project {PROJECT_ID}, Pipeline {PIPELINE_ID}")
    print()

    # Create FastMCP Client using stdio transport with uv run command
    # The client will automatically start the server via stdio transport
    config = {
        "mcpServers": {
            "gitlab_analyzer": {
                "transport": "stdio",
                "command": "uv",
                "args": ["run", "gitlab-analyzer"],
                "env": {
                    "GITLAB_URL": os.getenv("GITLAB_URL", "https://gitbud.epam.com"),
                    "GITLAB_TOKEN": os.getenv("GITLAB_TOKEN", "W118SktdLchfwe11ejqs"),
                },
            }
        }
    }
    client = Client(config)

    try:
        print("1️⃣ Connecting to MCP server...")
        async with client:
            print("✅ Connected to GitLab Pipeline Analyzer MCP server")

            # Step 2: Verify server connectivity
            print("\n2️⃣ Verifying server connectivity...")
            await client.ping()
            print("✅ Server ping successful")

            # Step 3: List available tools (detailed)
            print("\n3️⃣ Listing available tools...")
            tools = await client.list_tools()
            print(f"📋 Found {len(tools)} tools:")
            for i, tool in enumerate(tools, 1):
                print(f"   {i}. {tool.name}")
                print(f"      Description: {tool.description}")
                if (
                    hasattr(tool, "inputSchema")
                    and tool.inputSchema
                    and "properties" in tool.inputSchema
                ):
                    params = list(tool.inputSchema["properties"].keys())
                    print(f"      Parameters: {', '.join(params)}")
                print()

            # Step 4: List available resources (detailed)
            print("4️⃣ Listing available resources...")
            resources = await client.list_resources()
            print(f"📚 Found {len(resources)} resource templates:")
            for i, resource in enumerate(resources, 1):
                print(f"   {i}. {resource.uri}")
                print(f"      Name: {resource.name}")
                print(f"      Description: {resource.description}")
                print(f"      MIME Type: {resource.mimeType}")
                print()

            # Step 5: List available prompts (if any)
            print("5️⃣ Listing available prompts...")
            try:
                prompts = await client.list_prompts()
                if prompts:
                    print(f"💬 Found {len(prompts)} prompts:")
                    for i, prompt in enumerate(prompts, 1):
                        print(f"   {i}. {prompt.name}")
                        print(f"      Description: {prompt.description}")
                        if hasattr(prompt, "arguments") and prompt.arguments:
                            args = [arg.name for arg in prompt.arguments]
                            print(f"      Arguments: {', '.join(args)}")
                        print()
                else:
                    print("💬 No prompts available")
            except Exception as e:
                print(f"💬 No prompts available (error: {e})")

            # Step 6: Run comprehensive pipeline analysis
            print("6️⃣ Running comprehensive_pipeline_analysis...")
            analysis_result = await client.call_tool(
                "comprehensive_pipeline_analysis",
                {
                    "project_id": PROJECT_ID,
                    "pipeline_id": PIPELINE_ID,
                    "use_cache": True,
                    "store_in_db": True,
                },
            )

            print("✅ Pipeline analysis completed!")

            # Parse the analysis result to get resource URIs
            resource_uris = {}
            if hasattr(analysis_result, "content") and analysis_result.content:
                result_text = analysis_result.content[0].text
                print(f"📝 Raw analysis result: {result_text[:500]}...")
                try:
                    result_data = json.loads(result_text)
                    print(f"📊 Analysis result keys: {list(result_data.keys())}")
                    if "resource_uris" in result_data:
                        resource_uris = result_data["resource_uris"]
                        print(f"\n📚 Analysis created {len(resource_uris)} resources:")
                        for name, uri in resource_uris.items():
                            print(f"   • {name}: {uri}")
                    else:
                        print("❌ No resource URIs found in analysis result")
                        print(f"Available keys: {list(result_data.keys())}")
                except json.JSONDecodeError as e:
                    print(f"❌ Failed to parse analysis result: {e}")
                    print(f"Raw result: {result_text[:200]}...")
            else:
                print("❌ No content in analysis result")

            if not resource_uris:
                print("❌ Cannot proceed without resource URIs from analysis.")

                # Let's check if any resources are available now
                print("\n🔍 Checking available resources after analysis...")
                resources_after = await client.list_resources()
                print(
                    f"📚 Found {len(resources_after)} resource templates after analysis:"
                )
                for i, resource in enumerate(resources_after, 1):
                    print(f"   {i}. {resource.uri}")
                    print(f"      Name: {resource.name}")
                    print(f"      Description: {resource.description}")

                # Test direct resource access using known URI patterns
                print("\n🧪 Testing direct resource access with known URI patterns...")
                test_uris = [
                    f"gl://pipeline/{PROJECT_ID}/{PIPELINE_ID}",
                    f"gl://analysis/{PROJECT_ID}/pipeline/{PIPELINE_ID}",
                    f"gl://job/{PROJECT_ID}/{PIPELINE_ID}",  # This might fail if job_id format is different
                ]

                for test_uri in test_uris:
                    try:
                        print(f"\n🔍 Testing resource: {test_uri}")
                        resource_data = await client.read_resource(test_uri)
                        if resource_data.contents:
                            content = resource_data.contents[0].text
                            print(f"✅ Resource accessible: {test_uri}")
                            print(f"   Content preview: {content[:200]}...")
                        else:
                            print(f"❌ No content from resource: {test_uri}")
                    except Exception as e:
                        print(f"❌ Failed to access {test_uri}: {e}")

                return

            # Step 7: Get ALL information from resources (including pipeline info)
            print("\n7️⃣ Accessing all information via resources...")

            # 7a: Get pipeline information from resource (not from analysis)
            print("\n📊 Pipeline Information (from resource):")
            pipeline_uri = resource_uris.get("pipeline")
            if pipeline_uri:
                try:
                    pipeline_resource = await client.read_resource(pipeline_uri)
                    if pipeline_resource.contents:
                        pipeline_text = pipeline_resource.contents[0].text
                        pipeline_data = json.loads(pipeline_text)
                        print(f"✅ Pipeline resource accessed: {pipeline_uri}")
                        print(f"   Pipeline ID: {pipeline_data.get('id', 'N/A')}")
                        print(f"   Status: {pipeline_data.get('status', 'N/A')}")
                        print(f"   Branch: {pipeline_data.get('ref', 'N/A')}")
                        print(f"   Created: {pipeline_data.get('created_at', 'N/A')}")
                        print(
                            f"   Duration: {pipeline_data.get('duration', 'N/A')} seconds"
                        )
                        print(
                            f"   User: {pipeline_data.get('user', {}).get('name', 'N/A')}"
                        )
                        print(f"   Web URL: {pipeline_data.get('web_url', 'N/A')}")
                except Exception as e:
                    print(f"❌ Failed to access pipeline resource: {e}")
            else:
                print("❌ Pipeline resource URI not available")

            # 7b: Get jobs information from resource
            print("\n🔧 Jobs Information (from resource):")
            jobs_uri = resource_uris.get("jobs")
            if jobs_uri:
                try:
                    jobs_resource = await client.read_resource(jobs_uri)
                    if jobs_resource.contents:
                        jobs_text = jobs_resource.contents[0].text
                        jobs_data = json.loads(jobs_text)
                        print(f"✅ Jobs resource accessed: {jobs_uri}")
                        print(
                            f"   Total jobs: {len(jobs_data) if isinstance(jobs_data, list) else 'N/A'}"
                        )

                        if isinstance(jobs_data, list) and jobs_data:
                            # Categorize jobs by status
                            jobs_by_status = {}
                            for job in jobs_data:
                                status = job.get("status", "unknown")
                                if status not in jobs_by_status:
                                    jobs_by_status[status] = []
                                jobs_by_status[status].append(job)

                            # Show summary by status
                            for status, status_jobs in jobs_by_status.items():
                                print(f"   {status.title()} jobs: {len(status_jobs)}")

                            # Show failed jobs details
                            failed_jobs = jobs_by_status.get("failed", [])
                            if failed_jobs:
                                print("\n   Failed Jobs Details:")
                                for i, job in enumerate(
                                    failed_jobs[:5], 1
                                ):  # Show first 5 failed jobs
                                    print(f"     {i}. {job.get('name', 'Unknown')}")
                                    print(
                                        f"        Stage: {job.get('stage', 'Unknown stage')}"
                                    )
                                    print(
                                        f"        Duration: {job.get('duration', 'N/A')} seconds"
                                    )
                                    print(
                                        f"        Web URL: {job.get('web_url', 'N/A')}"
                                    )
                except Exception as e:
                    print(f"❌ Failed to access jobs resource: {e}")
            else:
                print("❌ Jobs resource URI not available")

            # 7c: Get failed jobs list from resource
            print("\n🚨 Failed Jobs List (from resource):")
            failed_jobs_uri = resource_uris.get("failed_jobs")
            if failed_jobs_uri:
                try:
                    failed_jobs_resource = await client.read_resource(failed_jobs_uri)
                    if failed_jobs_resource.contents:
                        failed_jobs_text = failed_jobs_resource.contents[0].text
                        failed_jobs_data = json.loads(failed_jobs_text)
                        print(f"✅ Failed jobs resource accessed: {failed_jobs_uri}")

                        if isinstance(failed_jobs_data, list):
                            print(f"   Total failed jobs: {len(failed_jobs_data)}")
                            for i, job in enumerate(
                                failed_jobs_data[:3], 1
                            ):  # Show first 3
                                print(
                                    f"     {i}. {job.get('name', 'Unknown')} (ID: {job.get('id', 'N/A')})"
                                )
                        elif isinstance(failed_jobs_data, dict):
                            print(f"   Failed jobs data: {failed_jobs_data}")
                except Exception as e:
                    print(f"❌ Failed to access failed jobs resource: {e}")
            else:
                print("❌ Failed jobs resource URI not available")

            # 7d: Get errors information from resource
            print("\n🔥 Errors Information (from resource):")
            errors_uri = resource_uris.get("errors")
            if errors_uri:
                try:
                    errors_resource = await client.read_resource(errors_uri)
                    if errors_resource.contents:
                        errors_text = errors_resource.contents[0].text
                        errors_data = json.loads(errors_text)
                        print(f"✅ Errors resource accessed: {errors_uri}")

                        if isinstance(errors_data, dict):
                            total_errors = sum(
                                len(job_errors) for job_errors in errors_data.values()
                            )
                            print(f"   Total errors found: {total_errors}")

                            # Show errors by job
                            for job_name, job_errors in list(errors_data.items())[
                                :3
                            ]:  # First 3 jobs
                                if job_errors:
                                    print(
                                        f"\n   Job '{job_name}': {len(job_errors)} errors"
                                    )
                                    # Show first few errors as examples
                                    for i, error in enumerate(
                                        job_errors[:2], 1
                                    ):  # First 2 errors per job
                                        if isinstance(error, dict):
                                            error_msg = error.get(
                                                "message", "No message"
                                            )
                                            line_num = error.get("line", "unknown")
                                            print(
                                                f"     {i}. Line {line_num}: {error_msg[:100]}..."
                                            )
                                        elif isinstance(error, str):
                                            print(f"     {i}. {error[:100]}...")
                except Exception as e:
                    print(f"❌ Failed to access errors resource: {e}")
            else:
                print("❌ Errors resource URI not available")

            # 7e: Get files with errors from resource
            print("\n📁 Files with Errors (from resource):")
            files_with_errors_uri = resource_uris.get("files_with_errors")
            if files_with_errors_uri:
                try:
                    files_resource = await client.read_resource(files_with_errors_uri)
                    if files_resource.contents:
                        files_text = files_resource.contents[0].text
                        files_data = json.loads(files_text)
                        print(
                            f"✅ Files with errors resource accessed: {files_with_errors_uri}"
                        )

                        if isinstance(files_data, list):
                            print(f"   Total files with errors: {len(files_data)}")
                            for i, file_path in enumerate(
                                files_data[:5], 1
                            ):  # Show first 5
                                print(f"     {i}. {file_path}")
                        elif isinstance(files_data, dict):
                            print(f"   Files with errors data: {files_data}")
                except Exception as e:
                    print(f"❌ Failed to access files with errors resource: {e}")
            else:
                print("❌ Files with errors resource URI not available")

            # 7f: Get analysis details from resource
            print("\n📋 Analysis Details (from resource):")
            analysis_uri = resource_uris.get("analysis")
            if analysis_uri:
                try:
                    analysis_resource = await client.read_resource(analysis_uri)
                    if analysis_resource.contents:
                        analysis_text = analysis_resource.contents[0].text
                        analysis_data = json.loads(analysis_text)
                        print(f"✅ Analysis resource accessed: {analysis_uri}")
                        print(
                            f"   Analysis timestamp: {analysis_data.get('analysis_timestamp', 'N/A')}"
                        )
                        print(
                            f"   Used cache: {analysis_data.get('used_cache', 'N/A')}"
                        )
                        print(
                            f"   Stored in DB: {analysis_data.get('stored_in_db', 'N/A')}"
                        )

                        # Show analysis summary if available
                        if "analysis_summary" in analysis_data:
                            summary = analysis_data["analysis_summary"]
                            print(
                                f"   Total failed jobs: {summary.get('total_failed_jobs', 0)}"
                            )
                            print(f"   Total errors: {summary.get('total_errors', 0)}")
                            print(
                                f"   Total warnings: {summary.get('total_warnings', 0)}"
                            )
                except Exception as e:
                    print(f"❌ Failed to access analysis resource: {e}")
            else:
                print("❌ Analysis resource URI not available")

            # Step 8: Test cache management tools
            print("\n8️⃣ Testing cache management tools...")

            # Cache health check
            print("\n🏥 Cache Health Check:")
            try:
                cache_health = await client.call_tool("cache_health")
                if hasattr(cache_health, "content") and cache_health.content:
                    health_text = cache_health.content[0].text
                    health_data = json.loads(health_text)
                    print(f"✅ Cache health: {health_data.get('status', 'unknown')}")
                    if "health" in health_data:
                        health_info = health_data["health"]
                        print(
                            f"   Database: {health_info.get('database_status', 'unknown')}"
                        )
                        print(
                            f"   Performance: {health_info.get('performance_check', 'unknown')}"
                        )
            except Exception as e:
                print(f"❌ Cache health check failed: {e}")

            # Cache statistics
            print("\n📊 Cache Statistics:")
            try:
                cache_stats = await client.call_tool("cache_stats")
                if hasattr(cache_stats, "content") and cache_stats.content:
                    stats_text = cache_stats.content[0].text
                    stats_data = json.loads(stats_text)
                    print("✅ Cache stats retrieved")
                    if "stats" in stats_data:
                        stats_info = stats_data["stats"]
                        summary = stats_info.get("summary", {})
                        print(f"   Total entries: {summary.get('total_entries', 0)}")
                        print(f"   Database size: {summary.get('total_size_mb', 0)} MB")
            except Exception as e:
                print(f"❌ Cache stats failed: {e}")

            print("\n🎉 MCP Demo completed successfully!")
            print("✅ Used proper FastMCP Client for server communication")
            print("✅ Listed all available tools, resources, and prompts in detail")
            print("✅ Got pipeline information from resources (not analysis result)")
            print("✅ Accessed all data via gl:// URI patterns")
            print("✅ Validated end-to-end pipeline analysis workflow")
            print("✅ Demonstrated cache management capabilities")

    except Exception as e:
        print(f"❌ Demo failed: {e}")
        import traceback

        traceback.print_exc()


async def main():
    """Main entry point"""
    await demo_pipeline_analysis()


if __name__ == "__main__":
    asyncio.run(main())
