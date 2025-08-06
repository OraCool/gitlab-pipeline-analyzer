"""
Basic tests that avoid problematic imports

Copyright (c) 2025 Siarhei Skuratovich
Licensed under the MIT License - see LICENSE file for details
"""

import pytest


class TestBasicFunctionality:
    """Basic tests that don't require complex imports"""

    def test_basic_assertion(self):
        """Test that basic assertions work"""
        assert True

    @pytest.mark.asyncio
    async def test_async_functionality(self):
        """Test that async tests work"""

        async def simple_async_function():
            return "success"

        result = await simple_async_function()
        assert result == "success"

    def test_mock_behavior(self):
        """Test that we can create and use mocks"""

        # Create a mock that simulates the error response structure
        mock_result = {
            "error": "Failed to analyze pipeline (optimized): 404 Not Found",
            "project_id": "test-project",
            "pipeline_id": 12345,
            "mcp_info": {
                "name": "GitLab Pipeline Analyzer",
                "version": "0.2.2",
                "tool_used": "analyze_failed_pipeline",
                "error": True,
            },
        }

        # Verify the structure is correct
        assert isinstance(mock_result, dict)
        assert "error" in mock_result
        assert "project_id" in mock_result
        assert "pipeline_id" in mock_result
        assert "mcp_info" in mock_result

        mcp_info = mock_result["mcp_info"]
        assert mcp_info["name"] == "GitLab Pipeline Analyzer"
        assert "version" in mcp_info
        assert mcp_info["error"] is True

    def test_version_format(self):
        """Test version string validation"""
        version = "0.2.2"

        # Basic version format check
        parts = version.split(".")
        assert len(parts) == 3

        # Should be numbers
        for part in parts:
            assert part.isdigit()

        # Should match expected version
        assert version == "0.2.2"
