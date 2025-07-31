#!/usr/bin/env python3
"""
Test client for GitLab Pipeline Analyzer MCP Server

This script demonstrates how to use the GitLab Pipeline Analyzer tools.
"""

import asyncio
import os
import sys

# Add the current directory to Python path for local imports
sys.path.insert(0, os.path.dirname(__file__))

from fastmcp import Client


async def test_analyzer():
    """Test the GitLab Pipeline Analyzer MCP server"""
    
    # Create a client pointing to our server
    client = Client("gitlab_analyzer.py")
    
    async with client:
        print("🔍 Testing GitLab Pipeline Analyzer MCP Server")
        print("=" * 50)
        
        # Test with a sample pipeline ID (you'll need to replace this)
        pipeline_id = 123456  # Replace with actual pipeline ID
        
        print(f"\n1. Getting pipeline status for ID: {pipeline_id}")
        try:
            status = await client.call_tool("get_pipeline_status", {
                "pipeline_id": pipeline_id
            })
            print(f"Status: {status}")
        except Exception as e:
            print(f"Error: {e}")
        
        print(f"\n2. Getting pipeline jobs for ID: {pipeline_id}")
        try:
            jobs = await client.call_tool("get_pipeline_jobs", {
                "pipeline_id": pipeline_id
            })
            print(f"Jobs: {jobs}")
        except Exception as e:
            print(f"Error: {e}")
        
        print(f"\n3. Analyzing failed pipeline: {pipeline_id}")
        try:
            analysis = await client.call_tool("analyze_failed_pipeline", {
                "pipeline_id": pipeline_id
            })
            print(f"Analysis: {analysis}")
        except Exception as e:
            print(f"Error: {e}")
        
        print("\n4. Testing log error extraction")
        sample_log = """
        Starting job...
        Running tests...
        ERROR: Test failed - assertion error in test_user_login
        WARNING: Deprecated function usage detected
        FAILED: test_database_connection
        Process exited with code 1
        """
        
        try:
            errors = await client.call_tool("extract_log_errors", {
                "log_text": sample_log
            })
            print(f"Extracted errors/warnings: {errors}")
        except Exception as e:
            print(f"Error: {e}")
        
        print("\n✅ Test completed!")


def print_usage():
    """Print usage instructions"""
    print("""
GitLab Pipeline Analyzer Test Client

Usage:
    python test_client.py

Before running:
1. Set up your .env file with:
   GITLAB_URL=https://gitlab.com
   GITLAB_TOKEN=your-personal-access-token
   GITLAB_PROJECT_ID=your-project-id

2. Edit the pipeline_id variable in this script to use a real pipeline ID

3. Install dependencies:
   uv pip install fastmcp python-gitlab httpx pydantic
""")


if __name__ == "__main__":
    if "--help" in sys.argv or "-h" in sys.argv:
        print_usage()
    else:
        # Check if environment is configured
        if not os.getenv("GITLAB_TOKEN"):
            print("⚠️  GITLAB_TOKEN not set. Please configure your .env file.")
            print_usage()
        else:
            asyncio.run(test_analyzer())
