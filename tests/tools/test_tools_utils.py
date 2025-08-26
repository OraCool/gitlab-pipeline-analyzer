"""
Unit tests for MCP tools utilities.

Copyright (c) 2025 Siarhei Skuratovich
Licensed under the MIT License - see LICENSE file for details
"""

from gitlab_analyzer.mcp.tools.utils import _GITLAB_ANALYZER, optimize_tool_response


class TestToolsUtils:
    """Test tools utilities module."""

    def test_gitlab_analyzer_global_variable(self):
        """Test that _GITLAB_ANALYZER global variable is accessible."""
        # Initially should be None
        assert _GITLAB_ANALYZER is None

    def test_optimize_tool_response_import(self):
        """Test that optimize_tool_response is properly imported."""
        # Test that the function is available and callable
        assert callable(optimize_tool_response)

    def test_optimize_tool_response_functionality(self):
        """Test that the imported optimize_tool_response works correctly."""
        response = {"test": "data"}

        # Test with full mode (should return unchanged)
        result = optimize_tool_response(response, "full")
        assert result == response

    def test_optimize_tool_response_with_optimization(self):
        """Test that the imported optimize_tool_response adds optimization metadata."""
        response = {"test": "data"}

        # Test with minimal mode (should add optimization metadata)
        result = optimize_tool_response(response, "minimal")
        assert "optimization" in result
        assert result["optimization"]["response_mode"] == "minimal"
        assert result["test"] == "data"

    def test_module_all_exports(self):
        """Test that __all__ exports are correctly defined."""
        from gitlab_analyzer.mcp.tools.utils import __all__

        expected_exports = ["optimize_tool_response", "_GITLAB_ANALYZER"]
        assert __all__ == expected_exports
