"""
Updated MCP server registration to include the new webhook-triggered cache-first architecture.

This integrates the recommended architecture:
1. Webhook tools for triggering analysis
2. Cache-first resources for fast serving
3. Backward compatibility with existing tools
"""

# Import the new cache-first components
from gitlab_analyzer.mcp.resources.cache_resources import (
    register_cache_resources,
    register_webhook_tools,
)


def setup_webhook_cache_architecture(app):
    """
    Setup the new webhook-triggered cache-first architecture.

    This adds:
    - webhook analysis tools
    - cache-first resources
    - fast serving endpoints
    """
    print("🚀 Setting up webhook-triggered cache-first architecture...")

    # Register cache-first resources
    register_cache_resources(app)
    print("   ✅ Registered cache-first resources")

    # Register webhook processing tools
    register_webhook_tools(app)
    print("   ✅ Registered webhook analysis tools")

    print("   🎯 Available Resources:")
    print("      - gl://job/{project_id}/{job_id}/problems")
    print("      - gl://file/{project_id}/{job_id}/{file_path}/errors")
    print("      - gl://error/{project_id}/{job_id}/{error_id}/trace/{mode}")
    print("      - gl://pipeline/{project_id}/{pipeline_id}/failed_jobs")

    print("   🔧 Available Tools:")
    print("      - trigger_pipeline_analysis: Webhook-style processing")
    print("      - get_cache_status: Check what's cached")

    print("   💾 Architecture Benefits:")
    print("      - Cache-first: No GitLab re-fetching during serving")
    print("      - Immutable records: Parse once, serve forever")
    print("      - Fast file filtering: Indexed error lookup")
    print("      - Compressed storage: gzip'd traces")
    print("      - Version tracking: Parser version invalidation")


# Example usage for existing server.py
if __name__ == "__main__":
    from fastmcp import FastMCP

    app = FastMCP("GitLab Pipeline Analyzer")
    setup_webhook_cache_architecture(app)

    print("\n🎉 Webhook-triggered cache-first architecture ready!")
    print("Now you can:")
    print("1. Call trigger_pipeline_analysis(project_id, pipeline_id)")
    print("2. Access cached data via resources like gl://job/.../problems")
    print("3. Enjoy fast serving with no GitLab API calls!")
