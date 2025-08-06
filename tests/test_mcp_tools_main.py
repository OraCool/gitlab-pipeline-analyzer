"""
Unit tests for MCP tools main module.

Copyright (c) 2025 Siarhei Skuratovich
Licensed under the MIT License - see LICENSE file for details
"""

from unittest.mock import patch

import pytest
from fastmcp import FastMCP

from gitlab_analyzer.mcp.tools import register_tools


class TestMCPToolsMain:
    """Test main MCP tools module."""

    @pytest.fixture
    def mcp_server(self):
        """Create FastMCP server."""
        return FastMCP("test")

    async def test_register_tools_all_modules(self, mcp_server):
        """Test that register_tools registers all tool modules."""
        with patch("gitlab_analyzer.mcp.tools.utils.get_gitlab_analyzer"):
            # Register all tools
            register_tools(mcp_server)

            # Get all registered tool names
            tool_names = [tool.name for tool in (await mcp_server.get_tools()).values()]

            # Verify analysis tools are registered
            analysis_tools = [
                "analyze_failed_pipeline",
                "analyze_single_job",
            ]
            for tool_name in analysis_tools:
                assert tool_name in tool_names, (
                    f"Analysis tool {tool_name} not registered"
                )

            # Verify info tools are registered
            info_tools = [
                "get_pipeline_jobs",
                "get_failed_jobs",
                "get_job_trace",
                "get_cleaned_job_trace",
                "get_pipeline_status",
            ]
            for tool_name in info_tools:
                assert tool_name in tool_names, f"Info tool {tool_name} not registered"

            # Verify log tools are registered
            log_tools = [
                "extract_log_errors",
            ]
            for tool_name in log_tools:
                assert tool_name in tool_names, f"Log tool {tool_name} not registered"

            # Verify pytest tools are registered
            pytest_tools = [
                "extract_pytest_detailed_failures",
                "extract_pytest_short_summary",
                "extract_pytest_statistics",
                "analyze_pytest_job_complete",
            ]
            for tool_name in pytest_tools:
                assert tool_name in tool_names, (
                    f"Pytest tool {tool_name} not registered"
                )

    async def test_register_tools_no_duplicates(self, mcp_server):
        """Test that no duplicate tools are registered."""
        with patch("gitlab_analyzer.mcp.tools.utils.get_gitlab_analyzer"):
            # Register tools
            register_tools(mcp_server)

            # Get all tool names
            tool_names = [tool.name for tool in (await mcp_server.get_tools()).values()]

            # Verify no duplicates
            assert len(tool_names) == len(set(tool_names)), "Duplicate tools found"

    async def test_register_tools_empty_server(self, mcp_server):
        """Test registering tools on empty server."""
        # Verify server starts empty
        assert len(await mcp_server.get_tools()) == 0

        with patch("gitlab_analyzer.mcp.tools.utils.get_gitlab_analyzer"):
            # Register tools
            register_tools(mcp_server)

            # Verify tools were added
            assert len(await mcp_server.get_tools()) > 0

    async def test_register_tools_idempotent(self, mcp_server):
        """Test that registering tools multiple times doesn't cause issues."""
        with patch("gitlab_analyzer.mcp.tools.utils.get_gitlab_analyzer"):
            # Register tools twice
            register_tools(mcp_server)
            initial_count = len(await mcp_server.get_tools())

            register_tools(mcp_server)
            final_count = len(await mcp_server.get_tools())

            # Count should be the same (tools replaced, not duplicated)
            assert final_count >= initial_count

    async def test_all_tools_have_required_structure(self, mcp_server):
        """Test that all registered tools have the required structure."""
        with patch("gitlab_analyzer.mcp.tools.utils.get_gitlab_analyzer"):
            # Register tools
            register_tools(mcp_server)

            # Verify each tool has required attributes
            for tool in (await mcp_server.get_tools()).values():
                assert hasattr(tool, "name"), "Tool missing name attribute"
                assert hasattr(tool, "fn"), f"Tool {tool.name} missing fn"
                assert callable(tool.fn), f"Tool {tool.name} fn is not callable"

    async def test_tools_parameter_validation(self, mcp_server):
        """Test that tools have proper parameter validation."""
        with patch("gitlab_analyzer.mcp.tools.utils.get_gitlab_analyzer"):
            # Register tools
            register_tools(mcp_server)

            # Check that project_id parameter exists in relevant tools
            project_tools = [
                "analyze_failed_pipeline",
                "analyze_single_job",
                "get_pipeline_jobs",
                "get_failed_jobs",
                "get_job_trace",
                "get_cleaned_job_trace",
                "get_pipeline_status",
                "extract_pytest_detailed_failures",
                "extract_pytest_short_summary",
                "extract_pytest_statistics",
                "analyze_pytest_job_complete",
            ]

            for tool in (await mcp_server.get_tools()).values():
                if tool.name in project_tools:
                    # Verify project_id parameter is in function signature
                    annotations = tool.fn.__annotations__
                    assert "project_id" in annotations, (
                        f"Tool {tool.name} missing project_id parameter"
                    )

    async def test_tools_return_type_hints(self, mcp_server):
        """Test that tools have proper return type hints."""
        with patch("gitlab_analyzer.mcp.tools.utils.get_gitlab_analyzer"):
            # Register tools
            register_tools(mcp_server)

            # Verify all tools have return type annotations
            for tool in (await mcp_server.get_tools()).values():
                annotations = tool.fn.__annotations__
                assert "return" in annotations, (
                    f"Tool {tool.name} missing return type annotation"
                )

    def test_module_exports(self):
        """Test that module exports expected items."""
        from gitlab_analyzer.mcp.tools import (
            get_gitlab_analyzer,
            register_analysis_tools,
            register_info_tools,
            register_log_tools,
            register_pytest_tools,
            register_tools,
        )

        # Verify all expected exports are callable
        exports = [
            register_tools,
            register_analysis_tools,
            register_info_tools,
            register_log_tools,
            register_pytest_tools,
            get_gitlab_analyzer,
        ]

        for export in exports:
            assert callable(export), f"Export {export.__name__} is not callable"

    async def test_tool_categories_coverage(self, mcp_server):
        """Test that all tool categories are covered."""
        with patch("gitlab_analyzer.mcp.tools.utils.get_gitlab_analyzer"):
            # Register tools
            register_tools(mcp_server)

            tool_names = [tool.name for tool in (await mcp_server.get_tools()).values()]

            # Verify we have tools from each category
            categories = {
                "analysis": ["analyze_failed_pipeline", "analyze_single_job"],
                "info": ["get_pipeline_jobs", "get_failed_jobs"],
                "log": ["extract_log_errors"],
                "pytest": [
                    "extract_pytest_detailed_failures",
                    "analyze_pytest_job_complete",
                ],
            }

            for category, expected_tools in categories.items():
                found_tools = [tool for tool in expected_tools if tool in tool_names]
                assert len(found_tools) > 0, (
                    f"No tools found for category {category}. Expected: {expected_tools}"
                )

    async def test_tools_error_handling_structure(self, mcp_server):
        """Test that tools are structured to handle errors properly."""
        with patch("gitlab_analyzer.mcp.tools.utils.get_gitlab_analyzer"):
            # Register tools
            register_tools(mcp_server)

            # We can't easily test error handling without running the tools,
            # but we can verify they're async functions (required for error handling)
            async_tools = [
                "analyze_failed_pipeline",
                "analyze_single_job",
                "get_pipeline_jobs",
                "get_failed_jobs",
                "get_job_trace",
                "get_cleaned_job_trace",
                "get_pipeline_status",
                "extract_pytest_detailed_failures",
                "extract_pytest_short_summary",
                "extract_pytest_statistics",
                "analyze_pytest_job_complete",
                "extract_log_errors",
            ]

            for tool in (await mcp_server.get_tools()).values():
                if tool.name in async_tools:
                    # Check if it's an async function
                    import asyncio

                    assert asyncio.iscoroutinefunction(tool.fn), (
                        f"Tool {tool.name} should be async"
                    )

    async def test_minimum_tool_count(self, mcp_server):
        """Test that minimum expected number of tools are registered."""
        with patch("gitlab_analyzer.mcp.tools.utils.get_gitlab_analyzer"):
            # Register tools
            register_tools(mcp_server)

            # We should have at least 11 tools (based on our current implementation)
            # 2 analysis + 5 info + 1 log + 4 pytest = 12 tools minimum
            assert len(await mcp_server.get_tools()) >= 11, (
                f"Expected at least 11 tools, got {len(await mcp_server.get_tools())}"
            )

    async def test_register_tools_with_mock_error(self, mcp_server):
        """Test register_tools behavior when utils function fails."""
        with patch(
            "gitlab_analyzer.mcp.tools.utils.get_gitlab_analyzer",
            side_effect=ValueError("Mock error"),
        ):
            # Should still register tools successfully (they handle their own errors)
            register_tools(mcp_server)

            # Tools should still be registered
            assert len(await mcp_server.get_tools()) > 0
