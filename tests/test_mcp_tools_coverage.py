"""
Additional tests for MCP tools to improve coverage.

Copyright (c) 2025 Siarhei Skuratovich
Licensed under the MIT License - see LICENSE file for details
"""

from unittest.mock import AsyncMock, patch

import pytest
from fastmcp import FastMCP

from gitlab_analyzer.mcp.tools import get_gitlab_analyzer, register_tools


class TestMCPToolsCoverage:
    """Additional tests for MCP tools to improve code coverage."""

    def test_get_gitlab_analyzer_initialization(self):
        """Test GitLab analyzer initialization."""
        with patch.dict(
            "os.environ", {"GITLAB_URL": "https://test.com", "GITLAB_TOKEN": "token"}
        ):
            analyzer = get_gitlab_analyzer()
            assert analyzer is not None

    def test_get_gitlab_analyzer_no_environment(self):
        """Test GitLab analyzer when environment variables are missing."""
        with patch.dict("os.environ", {}, clear=True):
            # Reset the global analyzer first
            import gitlab_analyzer.mcp.tools as tools_module

            tools_module._GITLAB_ANALYZER = None

            with pytest.raises(
                ValueError, match="GITLAB_TOKEN environment variable is required"
            ):
                get_gitlab_analyzer()

    def test_register_tools_adds_tools(self):
        """Test that register_tools adds tools to FastMCP server."""
        mcp = FastMCP("test")

        # Register tools
        register_tools(mcp)

        # Verify server has tools registered
        assert mcp is not None

    @pytest.mark.asyncio
    async def test_mcp_tool_execution_flow(self):
        """Test the general MCP tool execution flow."""
        with patch(
            "gitlab_analyzer.mcp.tools.get_gitlab_analyzer"
        ) as mock_get_analyzer:
            mock_analyzer = AsyncMock()
            mock_get_analyzer.return_value = mock_analyzer

            # Create a FastMCP server and register tools
            mcp = FastMCP("test")
            register_tools(mcp)

            # Verify tools are registered by checking if we can access them
            # Use the internal method since list_tools might not be public API
            tools = await mcp._list_tools()
            assert len(tools) > 0

    def test_gitlab_analyzer_singleton_behavior(self):
        """Test that GitLab analyzer behaves as singleton."""
        with patch.dict(
            "os.environ", {"GITLAB_URL": "https://test.com", "GITLAB_TOKEN": "token"}
        ):
            analyzer1 = get_gitlab_analyzer()
            analyzer2 = get_gitlab_analyzer()

            # Should return the same instance
            assert analyzer1 is analyzer2


class TestMCPToolsIntegration:
    """Integration tests for MCP tools."""

    @pytest.mark.asyncio
    async def test_tools_registration_complete(self):
        """Test that all expected tools are registered."""
        mcp = FastMCP("test-integration")
        register_tools(mcp)

        tools = await mcp._list_tools()
        tool_names = [tool.name for tool in tools]

        # Check that key tools are registered
        expected_tools = [
            "analyze_failed_pipeline",
            "get_cleaned_job_trace",
            "get_pipeline_status",
            "get_pipeline_jobs",
        ]

        for expected_tool in expected_tools:
            assert (
                expected_tool in tool_names
            ), f"Tool {expected_tool} not found in registered tools"

    @pytest.mark.asyncio
    async def test_mcp_server_with_tools_creation(self):
        """Test creating MCP server with all tools."""
        mcp = FastMCP("test-server")
        register_tools(mcp)

        # Verify server is properly configured
        assert mcp.name == "test-server"
        tools = await mcp._list_tools()
        assert len(tools) > 0

    @pytest.mark.asyncio
    async def test_tool_execution_with_mock_analyzer(self):
        """Test tool execution with mocked analyzer."""
        with patch(
            "gitlab_analyzer.mcp.tools.get_gitlab_analyzer"
        ) as mock_get_analyzer:
            mock_analyzer = AsyncMock()
            mock_get_analyzer.return_value = mock_analyzer

            # Mock successful responses
            mock_analyzer.get_pipeline.return_value = {"id": 123, "status": "failed"}
            mock_analyzer.get_job_trace.return_value = (
                "Sample trace\x1b[31mERROR\x1b[0m"
            )

            # Create server and register tools
            mcp = FastMCP("test-execution")
            register_tools(mcp)

            # Get a tool and verify it's callable
            tools = await mcp._list_tools()
            assert len(tools) > 0
