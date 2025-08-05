"""
Example utilities for demonstrating MCP tool usage
"""

import asyncio
import json
from typing import Any

from fastmcp import Client


class MCPToolDemo:
    """Demonstration utilities for MCP tools"""

    def __init__(self, server_script: str = "server.py"):
        self.server_script = server_script

    async def demonstrate_cleaned_trace_tool(
        self, project_id: str, job_id: int
    ) -> dict[str, Any]:
        """
        Demonstrate the get_cleaned_job_trace tool

        Args:
            project_id: GitLab project ID
            job_id: GitLab job ID

        Returns:
            Demonstration results with statistics
        """
        client = Client(self.server_script)
        async with client:
            # Get cleaned trace
            result = await client.call_tool(
                "get_cleaned_job_trace", {"project_id": project_id, "job_id": job_id}
            )

            if hasattr(result, "content") and result.content:
                trace_data = json.loads(result.content[0].text)
            else:
                trace_data = result

            return trace_data

    async def compare_raw_vs_cleaned(
        self, project_id: str, job_id: int
    ) -> dict[str, Any]:
        """
        Compare raw vs cleaned trace tools

        Args:
            project_id: GitLab project ID
            job_id: GitLab job ID

        Returns:
            Comparison results
        """
        client = Client(self.server_script)
        async with client:
            # Get raw trace
            raw_result = await client.call_tool(
                "get_job_trace", {"project_id": project_id, "job_id": job_id}
            )

            # Get cleaned trace
            cleaned_result = await client.call_tool(
                "get_cleaned_job_trace", {"project_id": project_id, "job_id": job_id}
            )

            # Process results
            if hasattr(raw_result, "content") and raw_result.content:
                raw_data = json.loads(raw_result.content[0].text)
            else:
                raw_data = raw_result

            if hasattr(cleaned_result, "content") and cleaned_result.content:
                cleaned_data = json.loads(cleaned_result.content[0].text)
            else:
                cleaned_data = cleaned_result

            return {
                "raw_trace": raw_data,
                "cleaned_trace": cleaned_data,
                "comparison": {
                    "size_reduction": (
                        cleaned_data.get("cleaning_stats", {}).get(
                            "reduction_percentage", 0
                        )
                    ),
                    "ansi_sequences_removed": (
                        cleaned_data.get("cleaning_stats", {}).get(
                            "ansi_sequences_found", 0
                        )
                    ),
                },
            }

    async def list_available_tools(self) -> list:
        """List all available MCP tools"""
        client = Client(self.server_script)
        async with client:
            tools = await client.list_tools()
            return [
                {
                    "name": tool.name,
                    "description": (
                        " ".join(tool.description.split())
                        if tool.description
                        else "No description"
                    ),
                }
                for tool in tools
            ]


# Example usage functions
async def example_cleaned_trace_demo():
    """Example: Demonstrate cleaned trace tool"""
    demo = MCPToolDemo()

    # Note: These are example values - replace with actual project/job IDs
    project_id = "19133"
    job_id = 2009734

    try:
        result = await demo.demonstrate_cleaned_trace_tool(project_id, job_id)

        if "error" in result:
            print(f"Error: {result['error']}")
            return

        stats = result.get("cleaning_stats", {})
        print("Cleaned Trace Tool Demo Results:")
        print(f"  Original length: {stats.get('original_length', 0):,} chars")
        print(f"  Cleaned length: {stats.get('cleaned_length', 0):,} chars")
        print(f"  Reduction: {stats.get('reduction_percentage', 0)}%")
        print(f"  ANSI sequences: {stats.get('ansi_sequences_found', 0)}")

    except Exception as e:
        print(f"Demo failed: {e}")


async def example_tools_list():
    """Example: List all available tools"""
    demo = MCPToolDemo()

    try:
        tools = await demo.list_available_tools()
        print("Available MCP Tools:")
        for i, tool in enumerate(tools, 1):
            print(f"  {i:2d}. {tool['name']}")
            print(f"      {tool['description']}")
            print()
    except Exception as e:
        print(f"Failed to list tools: {e}")


if __name__ == "__main__":
    # Run examples
    print("Running MCP Tool Examples...")

    asyncio.run(example_tools_list())
    print("\n" + "=" * 50 + "\n")
    asyncio.run(example_cleaned_trace_demo())
