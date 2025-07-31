#!/usr/bin/env python3
"""
Test script for single job analysis functionality
"""

import asyncio
import os
from gitlab_analyzer import analyze_single_job


async def main():
    """Test the single job analysis functionality"""
    
    # Set up environment variables (replace with your actual values)
    os.environ["GITLAB_URL"] = "https://gitbud.epam.com"
    os.environ["GITLAB_TOKEN"] = os.getenv("GITLAB_TOKEN", "your-token-here")
    
    print("Testing single job analysis...")
    print("=" * 50)
    
    # Test with a known failed job ID from pipeline 623320
    project_id = 19133
    job_id = 2002975  # The 'test' job that failed
    
    try:
        # Call the function directly
        result = await analyze_single_job(
            project_id=project_id,
            job_id=job_id
        )
        
        print(f"Job ID: {result.get('job_id')}")
        print(f"Job URL: {result.get('job_url')}")
        print(f"Project ID: {result.get('project_id')}")
        
        if 'error' in result:
            print(f"Error: {result['error']}")
        else:
            summary = result.get('summary', {})
            print(f"Total Errors: {summary.get('total_errors', 0)}")
            print(f"Total Warnings: {summary.get('total_warnings', 0)}")
            print(f"Trace Length: {summary.get('trace_length', 0)}")
            print(f"Has Trace: {summary.get('has_trace', False)}")
            
            # Show first few errors if any
            analysis = result.get('analysis', {})
            errors = analysis.get('errors', [])
            if errors:
                print("\nFirst few errors:")
                for i, error in enumerate(errors[:3]):
                    print(f"  {i+1}. Line {error.get('line_number', 'N/A')}: "
                          f"{error.get('message', 'No message')[:100]}...")
    
    except Exception as e:
        print(f"Test failed: {e}")


if __name__ == "__main__":
    asyncio.run(main())
