#!/usr/bin/env python3
"""
Query specific pipeline for failed jobs
"""

import asyncio
import os
import sys

# Add the current directory to Python path for local imports
sys.path.insert(0, os.path.dirname(__file__))

from fastmcp import Client


async def get_failed_jobs(project_id: int, pipeline_id: int):
    """Get failed jobs for a specific pipeline"""
    
    # For uv run, we need to run in the same environment
    # So we'll just run our own script with uv run too
    # But use the direct approach since we're already in uv environment
    client = Client("gitlab_analyzer.py")
    
    async with client:
        print(f"🔍 Getting failed jobs for pipeline {pipeline_id} in project {project_id}")
        print("=" * 70)
        
        # Set the project ID in environment
        os.environ["GITLAB_PROJECT_ID"] = str(project_id)
        
        try:
            # Get all jobs for the pipeline
            print("\n1. Getting all jobs for pipeline...")
            jobs = await client.call_tool("get_pipeline_jobs", {
                "project_id": project_id,
                "pipeline_id": pipeline_id
            })
            print(f"Jobs: {jobs}")
            
            # Analyze failed pipeline specifically
            print("\n2. Analyzing failed pipeline...")
            analysis = await client.call_tool("analyze_failed_pipeline", {
                "project_id": project_id,
                "pipeline_id": pipeline_id
            })
            print(f"Failed Pipeline Analysis: {analysis}")
            
        except Exception as e:
            print(f"Error: {e}")
            import traceback
            traceback.print_exc()

        print("\n✅ Query completed!")


if __name__ == "__main__":
    # Pipeline 623320 in project 19133
    asyncio.run(get_failed_jobs(19133, 623320))
