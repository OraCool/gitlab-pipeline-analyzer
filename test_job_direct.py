#!/usr/bin/env python3
"""
Test single job analysis by creating a direct client
"""

import asyncio
import os
import sys
from datetime import datetime

# Add current directory to path for imports
sys.path.insert(0, '.')

# Import after path setup to avoid linting issues
try:
    from gitlab_analyzer import GitLabAnalyzer, LogParser
except ImportError as e:
    print(f"Import error: {e}")
    sys.exit(1)


async def test_single_job_analysis():
    """Test single job analysis functionality directly"""
    
    # Set up environment variables
    gitlab_url = "https://gitbud.epam.com"
    gitlab_token = os.getenv("GITLAB_TOKEN")
    
    if not gitlab_token:
        print("Error: GITLAB_TOKEN environment variable is required")
        return
    
    print("Testing single job analysis...")
    print("=" * 50)
    
    # Test parameters
    project_id = 19133
    job_id = 2002975  # The 'test' job that failed
    
    try:
        # Create analyzer instance
        analyzer = GitLabAnalyzer(gitlab_url, gitlab_token)
        
        # Get job trace
        print(f"Fetching trace for job {job_id}...")
        trace = await analyzer.get_job_trace(project_id, job_id)
        
        if not trace.strip():
            print(f"No trace found for job {job_id}")
            return
        
        print(f"Trace length: {len(trace)} characters")
        
        # Extract errors and warnings from the trace
        print("Analyzing trace for errors and warnings...")
        log_entries = LogParser.extract_log_entries(trace)
        
        # Categorize entries
        errors = [
            entry.dict() for entry in log_entries
            if entry.level == "error"
        ]
        warnings = [
            entry.dict() for entry in log_entries
            if entry.level == "warning"
        ]
        
        # Get job URL
        job_url = f"{gitlab_url}/-/jobs/{job_id}"
        
        # Create result
        result = {
            "project_id": str(project_id),
            "job_id": job_id,
            "job_url": job_url,
            "analysis": {
                "errors": errors,
                "warnings": warnings
            },
            "summary": {
                "total_errors": len(errors),
                "total_warnings": len(warnings),
                "total_log_entries": len(log_entries),
                "has_trace": bool(trace.strip()),
                "trace_length": len(trace),
                "analysis_timestamp": datetime.now().isoformat()
            }
        }
        
        print("\n✅ Analysis Results:")
        print(f"Job ID: {result['job_id']}")
        print(f"Job URL: {result['job_url']}")
        print(f"Project ID: {result['project_id']}")
        print(f"Total Errors: {result['summary']['total_errors']}")
        print(f"Total Warnings: {result['summary']['total_warnings']}")
        print(f"Total Log Entries: {result['summary']['total_log_entries']}")
        print(f"Trace Length: {result['summary']['trace_length']}")
        print(f"Has Trace: {result['summary']['has_trace']}")
        
        # Show first few errors if any
        if errors:
            print("\n📋 First few errors:")
            for i, error in enumerate(errors[:5]):
                line_no = error.get('line_number', 'N/A')
                message = error.get('message', 'No message')[:120]
                print(f"  {i+1}. Line {line_no}: {message}...")
        
        # Show first few warnings if any
        if warnings:
            print("\n⚠️  First few warnings:")
            for i, warning in enumerate(warnings[:3]):
                line_no = warning.get('line_number', 'N/A')
                message = warning.get('message', 'No message')[:120]
                print(f"  {i+1}. Line {line_no}: {message}...")
        
        print("\n🎉 Single job analysis completed successfully!")
        return result
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return None


if __name__ == "__main__":
    asyncio.run(test_single_job_analysis())
