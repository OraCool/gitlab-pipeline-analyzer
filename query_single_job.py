#!/usr/bin/env python3
"""
Query specific job for analysis
"""

import asyncio
import os
import sys

# Add the current directory to Python path for local imports
sys.path.insert(0, os.path.dirname(__file__))

from fastmcp import Client


async def analyze_single_job_test(project_id: int, job_id: int):
    """Analyze a single job"""
    
    client = Client("gitlab_analyzer.py")
    
    async with client:
        print(f"🔍 Analyzing single job {job_id} in project {project_id}")
        print("=" * 70)
        
        try:
            # Analyze single job
            print(f"\n1. Analyzing job {job_id}...")
            result = await client.call_tool("analyze_single_job", {
                "project_id": project_id,
                "job_id": job_id
            })
            print(f"Single Job Analysis Result: {result}")
            
        except Exception as e:
            print(f"Error: {e}")
            import traceback
            traceback.print_exc()


async def main():
    """Main test function"""
    
    # Test parameters
    project_id = 19133
    job_id = 2002975  # Known failed job from pipeline 623320
    
    await analyze_single_job_test(project_id, job_id)


if __name__ == "__main__":
    asyncio.run(main())
