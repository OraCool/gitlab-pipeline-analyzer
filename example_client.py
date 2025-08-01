#!/usr/bin/env python3
"""
Simple example script demonstrating how to use FastMCP client
to get job results from GitLab Pipeline Analyzer

This is a minimal example showing the core functionality.
For full CLI interface, use get_job_result.py instead.

Copyright (c) 2025 Siarhei Skuratovich
Licensed under the MIT License
"""

import asyncio
import os

try:
    from dotenv import load_dotenv

    load_dotenv()  # Load .env file if available
except ImportError:
    pass  # python-dotenv not installed, use environment variables directly

from fastmcp import Client


def extract_result(mcp_result):
    """Extract result from FastMCP CallToolResult"""
    if isinstance(mcp_result, dict):
        return mcp_result

    if hasattr(mcp_result, "content") and mcp_result.content:
        content = mcp_result.content[0]
        if hasattr(content, "text"):
            import json

            try:
                return json.loads(content.text)
            except json.JSONDecodeError:
                return {"error": f"Invalid JSON response: {content.text}"}

    return {"error": f"Unexpected result format: {type(mcp_result)}"}


async def analyze_job_example():
    """Simple example of getting job results via MCP"""

    # Check environment
    if not os.getenv("GITLAB_URL") or not os.getenv("GITLAB_TOKEN"):
        print("❌ Please set GITLAB_URL and GITLAB_TOKEN environment variables")
        return

    print("🚀 Starting MCP client to analyze GitLab job...")

    # Example parameters - replace with actual values
    project_id = "12345"  # Your GitLab project ID
    job_id = 67890  # Your GitLab job ID
    pipeline_id = 11111  # Your GitLab pipeline ID

    # Create MCP client
    client = Client("server.py")  # Path to your MCP server script

    try:
        async with client:
            print("🔗 Connected to MCP server")

            # Example 1: Analyze a single job
            print(f"\n📋 Analyzing job {job_id}...")
            job_result_raw = await client.call_tool(
                "analyze_single_job", {"project_id": project_id, "job_id": job_id}
            )
            job_result = extract_result(job_result_raw)

            print("Job Analysis Result:")
            if "error" in job_result:
                print(f"❌ Error: {job_result['error']}")
            else:
                summary = job_result.get("summary", {})
                print(f"   Errors: {summary.get('total_errors', 0)}")
                print(f"   Warnings: {summary.get('total_warnings', 0)}")
                print(f"   Has trace: {summary.get('has_trace', False)}")

            print("-" * 50)

            # Example 2: Get pipeline status
            print(f"\n📊 Getting pipeline {pipeline_id} status...")
            pipeline_status_raw = await client.call_tool(
                "get_pipeline_status",
                {"project_id": project_id, "pipeline_id": pipeline_id},
            )
            pipeline_status = extract_result(pipeline_status_raw)

            print("Pipeline Status:")
            if "error" in pipeline_status:
                print(f"❌ Error: {pipeline_status['error']}")
            else:
                print(f"   Status: {pipeline_status.get('status', 'Unknown')}")
                print(f"   Ref: {pipeline_status.get('ref', 'Unknown')}")
                print(f"   URL: {pipeline_status.get('web_url', 'N/A')}")

            print("-" * 50)

            # Example 3: Get failed jobs
            print(f"\n❌ Getting failed jobs for pipeline {pipeline_id}...")
            failed_jobs_raw = await client.call_tool(
                "get_failed_jobs",
                {"project_id": project_id, "pipeline_id": pipeline_id},
            )
            failed_jobs = extract_result(failed_jobs_raw)

            print("Failed Jobs:")
            if "error" in failed_jobs:
                print(f"❌ Error: {failed_jobs['error']}")
            else:
                jobs = failed_jobs.get("failed_jobs", [])
                print(f"   Found {len(jobs)} failed jobs")
                for job in jobs[:3]:  # Show first 3
                    print(
                        f"   • {job['name']} (Stage: {job['stage']}, Reason: {job.get('failure_reason', 'Unknown')})"
                    )
                if len(jobs) > 3:
                    print(f"   ... and {len(jobs) - 3} more failed jobs")

            print("-" * 50)

            # Example 4: Full pipeline analysis (for failed pipelines)
            print(f"\n🔥 Analyzing failed pipeline {pipeline_id}...")
            pipeline_analysis_raw = await client.call_tool(
                "analyze_failed_pipeline",
                {"project_id": project_id, "pipeline_id": pipeline_id},
            )
            pipeline_analysis = extract_result(pipeline_analysis_raw)

            print("Pipeline Analysis:")
            if "error" in pipeline_analysis:
                print(f"❌ Error: {pipeline_analysis['error']}")
            else:
                summary = pipeline_analysis.get("summary", {})
                print(
                    f"   Pipeline Status: {pipeline_analysis.get('pipeline_status', 'Unknown')}"
                )
                print(f"   Failed Jobs: {summary.get('failed_jobs_count', 0)}")
                print(f"   Total Errors: {summary.get('total_errors', 0)}")
                print(f"   Total Warnings: {summary.get('total_warnings', 0)}")
                if summary.get("failed_stages"):
                    print(f"   Failed Stages: {', '.join(summary['failed_stages'])}")

    except Exception as e:
        print(f"❌ Unexpected error: {str(e)}")

    print("\n✅ Example completed!")


async def get_job_trace_example():
    """Example of getting raw job trace"""

    # Check environment
    if not os.getenv("GITLAB_URL") or not os.getenv("GITLAB_TOKEN"):
        print("❌ Please set GITLAB_URL and GITLAB_TOKEN environment variables")
        return

    project_id = "12345"  # Your GitLab project ID
    job_id = 67890  # Your GitLab job ID

    client = Client("server.py")

    try:
        async with client:
            print(f"📋 Getting trace for job {job_id}...")

            trace_result_raw = await client.call_tool(
                "get_job_trace", {"project_id": project_id, "job_id": job_id}
            )
            trace_result = extract_result(trace_result_raw)

            if "error" in trace_result:
                print(f"❌ Error: {trace_result['error']}")
            else:
                trace = trace_result.get("trace", "")
                print(f"📋 Job Trace (Length: {len(trace)} chars)")
                print("=" * 60)
                # Show first 1000 characters of trace
                print(trace[:1000])
                if len(trace) > 1000:
                    print(
                        f"\n... (truncated, showing first 1000 of {len(trace)} characters)"
                    )
                print("=" * 60)

    except Exception as e:
        print(f"❌ Unexpected error: {str(e)}")


def main():
    """Main function with examples"""
    print("GitLab Job Result Analyzer - MCP Client Example")
    print("=" * 50)

    # Run main analysis example
    asyncio.run(analyze_job_example())

    print("\n" + "=" * 50)
    print("Getting job trace example:")
    print("=" * 50)

    # Run trace example
    asyncio.run(get_job_trace_example())


if __name__ == "__main__":
    main()
