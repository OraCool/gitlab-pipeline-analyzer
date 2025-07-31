#!/usr/bin/env python3
"""
Query script to test single job analysis via MCP
"""

import json
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def test_single_job():
    """Test single job analysis through MCP"""
    
    # Server parameters for uv execution
    server_params = StdioServerParameters(
        command="uv", args=["run", "python", "gitlab_analyzer.py"]
    )
    
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            
            # Test single job analysis
            print("Testing single job analysis...")
            print("=" * 50)
            
            try:
                # Test with known failed job
                result = await session.call_tool(
                    "analyze_single_job",
                    arguments={
                        "project_id": 19133,
                        "job_id": 2002975  # The 'test' job that failed
                    }
                )
                
                print("✅ Single Job Analysis Results:")
                print(json.dumps(result.content, indent=2))
                
            except Exception as e:
                print(f"❌ Single job analysis failed: {e}")


if __name__ == "__main__":
    import asyncio
    asyncio.run(test_single_job())
