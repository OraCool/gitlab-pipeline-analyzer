#!/usr/bin/env python3
"""
Example usage of GitLab Pipeline Analyzer MCP Server

This script shows how to interact with the MCP server to analyze pipeline failures.
"""

import asyncio
import json
import os
from typing import Any, Dict

from fastmcp import Client


async def analyze_pipeline_example(pipeline_id: int) -> None:
    """Example: Analyze a failed pipeline and pretty-print results"""
    
    client = Client("gitlab_analyzer.py")
    
    async with client:
        print(f"🔍 Analyzing GitLab Pipeline {pipeline_id}")
        print("=" * 60)
        
        # Get full pipeline analysis
        result = await client.call_tool("analyze_failed_pipeline", {
            "pipeline_id": pipeline_id
        })
        
        if "error" in result:
            print(f"❌ Error: {result['error']}")
            return
        
        # Pretty print the summary
        summary = result.get("summary", {})
        print(f"\n📊 Pipeline Summary:")
        print(f"   Status: {summary.get('pipeline_status', 'unknown')}")
        print(f"   Total Jobs: {summary.get('total_jobs', 0)}")
        print(f"   Failed Jobs: {summary.get('failed_jobs_count', 0)}")
        print(f"   Total Errors: {summary.get('total_errors', 0)}")
        print(f"   Total Warnings: {summary.get('total_warnings', 0)}")
        print(f"   Failed Stages: {', '.join(summary.get('failed_stages', []))}")
        
        # Show failed jobs
        failed_jobs = result.get("failed_jobs", [])
        if failed_jobs:
            print(f"\n💥 Failed Jobs ({len(failed_jobs)}):")
            for job in failed_jobs:
                print(f"   • {job['name']} (Stage: {job['stage']})")
                if job.get('failure_reason'):
                    print(f"     Reason: {job['failure_reason']}")
        
        # Show analysis results
        analysis = result.get("analysis", {})
        if analysis:
            print(f"\n🔍 Error Analysis:")
            for job_name, entries in analysis.items():
                if entries:
                    print(f"\n   📋 {job_name}:")
                    errors = [e for e in entries if e['level'] == 'error']
                    warnings = [e for e in entries if e['level'] == 'warning']
                    
                    if errors:
                        print(f"      ❌ Errors ({len(errors)}):")
                        for error in errors[:3]:  # Show first 3 errors
                            print(f"         - {error['message']}")
                    
                    if warnings:
                        print(f"      ⚠️  Warnings ({len(warnings)}):")
                        for warning in warnings[:3]:  # Show first 3 warnings
                            print(f"         - {warning['message']}")
        
        print(f"\n✅ Analysis complete!")


async def extract_errors_example() -> None:
    """Example: Extract errors from sample log text"""
    
    sample_log = """
    [2024-01-15 10:30:45] INFO: Starting build process...
    [2024-01-15 10:30:50] INFO: Installing dependencies...
    [2024-01-15 10:31:15] ERROR: Package installation failed: numpy==1.24.0
    [2024-01-15 10:31:16] WARNING: Using deprecated API in module auth.utils
    [2024-01-15 10:31:20] INFO: Running tests...
    [2024-01-15 10:31:45] FAILED: test_user_authentication - AssertionError: Expected True, got False
    [2024-01-15 10:31:50] ERROR: Test suite failed with 3 failures
    [2024-01-15 10:31:55] WARNING: Code coverage below threshold: 75%
    [2024-01-15 10:32:00] Process exited with code 1
    """
    
    client = Client("gitlab_analyzer.py")
    
    async with client:
        print("🔍 Extracting Errors from Sample Log")
        print("=" * 40)
        
        result = await client.call_tool("extract_log_errors", {
            "log_text": sample_log
        })
        
        if "error" in result:
            print(f"❌ Error: {result['error']}")
            return
        
        print(f"📊 Summary:")
        print(f"   Total Entries: {result.get('total_entries', 0)}")
        print(f"   Errors: {result.get('error_count', 0)}")
        print(f"   Warnings: {result.get('warning_count', 0)}")
        
        errors = result.get("errors", [])
        if errors:
            print(f"\n❌ Errors ({len(errors)}):")
            for error in errors:
                print(f"   Line {error['line_number']}: {error['message']}")
        
        warnings = result.get("warnings", [])
        if warnings:
            print(f"\n⚠️  Warnings ({len(warnings)}):")
            for warning in warnings:
                print(f"   Line {warning['line_number']}: {warning['message']}")


async def main() -> None:
    """Main example function"""
    
    print("GitLab Pipeline Analyzer - Example Usage")
    print("=" * 50)
    
    # Check if environment is configured
    if not os.getenv("GITLAB_TOKEN"):
        print("⚠️  Please configure your .env file with GitLab credentials")
        print("   Copy .env.example to .env and fill in your details")
        return
    
    try:
        # Example 1: Extract errors from log text (no API calls needed)
        await extract_errors_example()
        
        print("\n" + "=" * 50)
        
        # Example 2: Analyze a real pipeline (requires valid pipeline ID)
        pipeline_id = os.getenv("EXAMPLE_PIPELINE_ID")
        if pipeline_id:
            await analyze_pipeline_example(int(pipeline_id))
        else:
            print("💡 To analyze a real pipeline, set EXAMPLE_PIPELINE_ID in your .env")
            print("   Example: EXAMPLE_PIPELINE_ID=123456")
    
    except Exception as e:
        print(f"❌ Error: {e}")
        print("   Make sure the MCP server is properly configured and accessible")


if __name__ == "__main__":
    asyncio.run(main())
