#!/usr/bin/env python3
"""
Simple test script for GitLab Pipeline Analyzer (no             print("\n✅ Log extraction test completed successfully!")
            print("\n💡 This demonstrates how the analyzer can extract structured")
            print("   error and warning information from CI/CD logs for AI analysis.")
            
            print("\n" + "=" * 55)
            print("📝 Note: Project ID is now a parameter for pipeline analysis tools:")
            print("   - analyze_failed_pipeline(project_id, pipeline_id)")
            print("   - get_pipeline_jobs(project_id, pipeline_id)")
            print("   - get_job_trace(project_id, job_id)")
            print("   - get_pipeline_status(project_id, pipeline_id)")
    
    except Exception as e:
        print(f"❌ Test failed: {e}")
        print("   Make sure you've run: source .venv/bin/activate")ials required)
"""

import asyncio
import sys
import os

# Add current directory to path
sys.path.insert(0, os.path.dirname(__file__))

from fastmcp import Client


async def test_log_extraction():
    """Test log error extraction without requiring GitLab credentials"""
    
    print("🧪 Testing GitLab Pipeline Analyzer - Log Extraction")
    print("=" * 55)
    
    # Sample log that simulates a typical Python CI/CD failure
    sample_log = """
[2024-01-15 10:30:45] INFO: Starting build process...
[2024-01-15 10:30:50] INFO: Installing dependencies...
[2024-01-15 10:31:15] ERROR: Package installation failed: numpy==1.24.0
[2024-01-15 10:31:16] WARNING: Using deprecated API in module auth.utils
[2024-01-15 10:31:20] INFO: Running pylint...
[2024-01-15 10:31:25] pylint: E1101: Instance of 'User' has no 'email' member
[2024-01-15 10:31:30] INFO: Running tests with pytest...
[2024-01-15 10:31:45] FAILED: test_user_authentication - AssertionError: Expected True, got False
[2024-01-15 10:31:46] E       AssertionError: Login should succeed with valid credentials
[2024-01-15 10:31:50] ERROR: Test suite failed with 3 failures
[2024-01-15 10:31:55] WARNING: Code coverage below threshold: 75%
[2024-01-15 10:31:58] mypy: error: Cannot find implementation or library stub
[2024-01-15 10:32:00] Command failed with exit code 1
[2024-01-15 10:32:01] Process exited with code 1
"""
    
    try:
        client = Client("gitlab_analyzer.py")
        
        async with client:
            print("📋 Extracting errors and warnings from sample CI/CD log...")
            
            result = await client.call_tool("extract_log_errors", {
                "log_text": sample_log
            })
            
            # Handle the MCP result properly
            if hasattr(result, 'content'):
                # If it's an MCP result object, get the content
                import json
                result_data = json.loads(result.content[0].text) if result.content else {}
            else:
                # If it's already a dict
                result_data = result
            
            if "error" in result_data:
                print(f"❌ Error: {result_data['error']}")
                return
            
            print(f"\n📊 Summary:")
            print(f"   Total Entries: {result_data.get('total_entries', 0)}")
            print(f"   Errors: {result_data.get('error_count', 0)}")
            print(f"   Warnings: {result_data.get('warning_count', 0)}")
            
            errors = result_data.get("errors", [])
            if errors:
                print(f"\n❌ Found {len(errors)} Errors:")
                for i, error in enumerate(errors, 1):
                    print(f"   {i}. Line {error['line_number']}: {error['message']}")
            
            warnings = result_data.get("warnings", [])
            if warnings:
                print(f"\n⚠️  Found {len(warnings)} Warnings:")
                for i, warning in enumerate(warnings, 1):
                    print(f"   {i}. Line {warning['line_number']}: {warning['message']}")
            
            print(f"\n✅ Log extraction test completed successfully!")
            print(f"\n💡 This demonstrates how the analyzer can extract structured")
            print(f"   error and warning information from CI/CD logs for AI analysis.")
    
    except Exception as e:
        print(f"❌ Test failed: {e}")
        print("   Make sure you've run: source .venv/bin/activate")


if __name__ == "__main__":
    asyncio.run(test_log_extraction())
