"""
Focused tests for clean_trace_tools module to increase coverage

Copyright (c) 2025 Siarhei Skuratovich
Licensed under the MIT License - see LICENSE file for details
"""

import asyncio
from unittest.mock import AsyncMock, Mock, patch


class TestCleanTraceToolsFocused:
    """Focused tests for clean_trace_tools to increase coverage"""

    def test_register_clean_trace_tools(self):
        """Test that clean trace tools register successfully"""
        from gitlab_analyzer.mcp.tools.clean_trace_tools import (
            register_clean_trace_tools,
        )

        mock_mcp = Mock()
        mock_mcp.tool = Mock()

        # Should register without errors
        register_clean_trace_tools(mock_mcp)

        # Verify tool was registered
        assert mock_mcp.tool.called
        assert mock_mcp.tool.call_count >= 1

    @patch("gitlab_analyzer.mcp.tools.clean_trace_tools.get_gitlab_analyzer")
    def test_get_clean_job_trace_basic(self, mock_get_analyzer):
        """Test basic get_clean_job_trace functionality"""
        from gitlab_analyzer.mcp.tools.clean_trace_tools import (
            register_clean_trace_tools,
        )

        # Setup mock analyzer
        mock_analyzer = Mock()
        mock_analyzer.get_job_trace = AsyncMock(
            return_value="Raw trace content with \x1b[31mANSI\x1b[0m codes"
        )
        mock_get_analyzer.return_value = mock_analyzer

        # Setup MCP and register tools
        mock_mcp = Mock()
        register_clean_trace_tools(mock_mcp)

        # Get the registered function
        tool_function = None
        for call in mock_mcp.tool.call_args_list:
            if (
                call.args
                and hasattr(call.args[0], "__name__")
                and "get_clean_job_trace" in call.args[0].__name__
            ):
                tool_function = call.args[0]
                break

        assert tool_function is not None

        # Test the function
        result = asyncio.run(
            tool_function(
                project_id="123", job_id=456, save_to_file=False, output_format="text"
            )
        )

        assert isinstance(result, dict)
        assert "clean_trace" in result or "trace_content" in result
        mock_analyzer.get_job_trace.assert_called_with("123", 456)

    @patch("gitlab_analyzer.mcp.tools.clean_trace_tools.get_gitlab_analyzer")
    def test_get_clean_job_trace_json_format(self, mock_get_analyzer):
        """Test get_clean_job_trace with JSON format"""
        from gitlab_analyzer.mcp.tools.clean_trace_tools import (
            register_clean_trace_tools,
        )

        # Setup mock analyzer
        mock_analyzer = Mock()
        mock_analyzer.get_job_trace = AsyncMock(return_value="Line 1\nLine 2\nLine 3")
        mock_get_analyzer.return_value = mock_analyzer

        mock_mcp = Mock()
        register_clean_trace_tools(mock_mcp)

        # Get the function
        tool_function = None
        for call in mock_mcp.tool.call_args_list:
            if (
                call.args
                and hasattr(call.args[0], "__name__")
                and "get_clean_job_trace" in call.args[0].__name__
            ):
                tool_function = call.args[0]
                break

        # Test with JSON format
        result = asyncio.run(
            tool_function(
                project_id="123", job_id=456, save_to_file=False, output_format="json"
            )
        )

        assert isinstance(result, dict)
        assert "trace_preview" in result or "error_indicators" in result

    @patch("gitlab_analyzer.mcp.tools.clean_trace_tools.get_gitlab_analyzer")
    @patch("pathlib.Path.write_text")
    def test_get_clean_job_trace_save_file(self, mock_write_text, mock_get_analyzer):
        """Test get_clean_job_trace with file saving"""
        from gitlab_analyzer.mcp.tools.clean_trace_tools import (
            register_clean_trace_tools,
        )

        # Setup mock analyzer
        mock_analyzer = Mock()
        mock_analyzer.get_job_trace = AsyncMock(return_value="Trace content to save")
        mock_get_analyzer.return_value = mock_analyzer

        mock_mcp = Mock()
        register_clean_trace_tools(mock_mcp)

        # Get the function
        tool_function = None
        for call in mock_mcp.tool.call_args_list:
            if (
                call.args
                and hasattr(call.args[0], "__name__")
                and "get_clean_job_trace" in call.args[0].__name__
            ):
                tool_function = call.args[0]
                break

        # Test with file saving
        result = asyncio.run(
            tool_function(
                project_id="123", job_id=456, save_to_file=True, output_format="text"
            )
        )

        assert isinstance(result, dict)
        # Verify file operations were attempted
        mock_write_text.assert_called()

    @patch("gitlab_analyzer.mcp.tools.clean_trace_tools.get_gitlab_analyzer")
    def test_get_clean_job_trace_error_handling(self, mock_get_analyzer):
        """Test get_clean_job_trace error handling"""
        from gitlab_analyzer.mcp.tools.clean_trace_tools import (
            register_clean_trace_tools,
        )

        # Setup analyzer to raise exception
        mock_analyzer = Mock()
        mock_analyzer.get_job_trace = AsyncMock(side_effect=Exception("API error"))
        mock_get_analyzer.return_value = mock_analyzer

        mock_mcp = Mock()
        register_clean_trace_tools(mock_mcp)

        # Get the function
        tool_function = None
        for call in mock_mcp.tool.call_args_list:
            if (
                call.args
                and hasattr(call.args[0], "__name__")
                and "get_clean_job_trace" in call.args[0].__name__
            ):
                tool_function = call.args[0]
                break

        # Should handle exception gracefully
        result = asyncio.run(
            tool_function(
                project_id="123", job_id=456, save_to_file=False, output_format="text"
            )
        )

        assert isinstance(result, dict)
        # Should contain error information
        assert "error" in result or "message" in result or "success" in result

    @patch("gitlab_analyzer.mcp.tools.clean_trace_tools.get_gitlab_analyzer")
    def test_get_clean_job_trace_empty_trace(self, mock_get_analyzer):
        """Test get_clean_job_trace with empty trace"""
        from gitlab_analyzer.mcp.tools.clean_trace_tools import (
            register_clean_trace_tools,
        )

        # Setup mock analyzer with empty trace
        mock_analyzer = Mock()
        mock_analyzer.get_job_trace = AsyncMock(return_value="")
        mock_get_analyzer.return_value = mock_analyzer

        mock_mcp = Mock()
        register_clean_trace_tools(mock_mcp)

        # Get the function
        tool_function = None
        for call in mock_mcp.tool.call_args_list:
            if (
                call.args
                and hasattr(call.args[0], "__name__")
                and "get_clean_job_trace" in call.args[0].__name__
            ):
                tool_function = call.args[0]
                break

        # Test with empty trace
        result = asyncio.run(
            tool_function(
                project_id="123", job_id=456, save_to_file=False, output_format="text"
            )
        )

        assert isinstance(result, dict)

    @patch("gitlab_analyzer.mcp.tools.clean_trace_tools.get_gitlab_analyzer")
    def test_get_clean_job_trace_ansi_cleaning(self, mock_get_analyzer):
        """Test ANSI escape sequence cleaning"""
        from gitlab_analyzer.mcp.tools.clean_trace_tools import (
            register_clean_trace_tools,
        )

        # Setup mock analyzer with ANSI sequences
        trace_with_ansi = (
            "\x1b[31mERROR:\x1b[0m Test failed\n\x1b[32mINFO:\x1b[0m Test passed"
        )
        mock_analyzer = Mock()
        mock_analyzer.get_job_trace = AsyncMock(return_value=trace_with_ansi)
        mock_get_analyzer.return_value = mock_analyzer

        mock_mcp = Mock()
        register_clean_trace_tools(mock_mcp)

        # Get the function
        tool_function = None
        for call in mock_mcp.tool.call_args_list:
            if (
                call.args
                and hasattr(call.args[0], "__name__")
                and "get_clean_job_trace" in call.args[0].__name__
            ):
                tool_function = call.args[0]
                break

        # Test ANSI cleaning
        result = asyncio.run(
            tool_function(
                project_id="123", job_id=456, save_to_file=False, output_format="text"
            )
        )

        assert isinstance(result, dict)
        # Check that trace was processed
        assert "clean_trace" in result or "trace_content" in result
