"""
Focused tests for trace_analysis_tools module to increase coverage

Copyright (c) 2025 Siarhei Skuratovich
Licensed under the MIT License - see LICENSE file for details
"""

import asyncio
from unittest.mock import Mock, patch


class TestTraceAnalysisToolsFocused:
    """Focused tests for trace_analysis_tools to increase coverage"""

    def test_register_trace_analysis_tools(self):
        """Test that trace analysis tools register successfully"""
        from gitlab_analyzer.mcp.tools.trace_analysis_tools import (
            register_trace_analysis_tools,
        )

        mock_mcp = Mock()
        mock_mcp.tool = Mock()

        # Should register without errors
        register_trace_analysis_tools(mock_mcp)

        # Verify tool was registered
        assert mock_mcp.tool.called
        assert mock_mcp.tool.call_count >= 1

    @patch("gitlab_analyzer.mcp.tools.trace_analysis_tools.LogParser")
    @patch("gitlab_analyzer.mcp.tools.trace_analysis_tools.PytestLogParser")
    def test_parse_trace_for_errors_basic(
        self, mock_pytest_parser_class, mock_log_parser_class
    ):
        """Test basic parse_trace_for_errors functionality"""
        from gitlab_analyzer.mcp.tools.trace_analysis_tools import (
            register_trace_analysis_tools,
        )

        # Setup mock parsers
        mock_log_parser = Mock()
        mock_log_parser.extract_log_entries.return_value = []
        mock_log_parser_class.return_value = mock_log_parser

        mock_pytest_parser = Mock()
        mock_pytest_parser.extract_log_entries.return_value = []
        mock_pytest_parser_class.return_value = mock_pytest_parser

        # Setup MCP and register tools
        mock_mcp = Mock()
        register_trace_analysis_tools(mock_mcp)

        # Get the registered function
        tool_function = None
        for call in mock_mcp.tool.call_args_list:
            if (
                call.args
                and hasattr(call.args[0], "__name__")
                and "parse_trace_for_errors" in call.args[0].__name__
            ):
                tool_function = call.args[0]
                break

        assert tool_function is not None

        # Test the function with basic trace
        trace_content = "ERROR: Test failed\nWARNING: Something happened"

        # Run the async function
        result = asyncio.run(
            tool_function(trace_content=trace_content, analysis_type="general")
        )

        assert isinstance(result, dict)
        assert "analysis_type" in result or "results" in result

    @patch("gitlab_analyzer.mcp.tools.trace_analysis_tools.LogParser")
    def test_parse_trace_auto_detection(self, mock_log_parser_class):
        """Test auto-detection of trace type"""
        from gitlab_analyzer.mcp.tools.trace_analysis_tools import (
            register_trace_analysis_tools,
        )

        # Setup mock parser
        mock_log_parser = Mock()
        mock_log_parser.extract_log_entries.return_value = []
        mock_log_parser_class.return_value = mock_log_parser

        mock_mcp = Mock()
        register_trace_analysis_tools(mock_mcp)

        # Get the function
        tool_function = None
        for call in mock_mcp.tool.call_args_list:
            if (
                call.args
                and hasattr(call.args[0], "__name__")
                and "parse_trace_for_errors" in call.args[0].__name__
            ):
                tool_function = call.args[0]
                break

        # Test with pytest-like content
        pytest_trace = """
        FAILED test_something.py::test_function - assert False
        collected 5 items
        =========================== FAILURES ===========================
        """

        result = asyncio.run(
            tool_function(trace_content=pytest_trace, analysis_type="auto")
        )

        assert isinstance(result, dict)

    @patch("gitlab_analyzer.mcp.tools.trace_analysis_tools.PytestLogParser")
    def test_parse_trace_pytest_mode(self, mock_pytest_parser_class):
        """Test pytest analysis mode"""
        from gitlab_analyzer.mcp.tools.trace_analysis_tools import (
            register_trace_analysis_tools,
        )

        # Setup mock pytest parser with proper return structure
        mock_parser_result = Mock()
        mock_parser_result.detailed_failures = []
        mock_parser_result.short_summary = "No tests ran"
        mock_parser_result.statistics = {}
        mock_pytest_parser_class.parse_pytest_log.return_value = mock_parser_result

        mock_mcp = Mock()
        register_trace_analysis_tools(mock_mcp)

        # Get the function
        tool_function = None
        for call in mock_mcp.tool.call_args_list:
            if (
                call.args
                and hasattr(call.args[0], "__name__")
                and "parse_trace_for_errors" in call.args[0].__name__
            ):
                tool_function = call.args[0]
                break

        trace_content = "pytest output"

        result = asyncio.run(
            tool_function(trace_content=trace_content, analysis_type="pytest")
        )

        assert isinstance(result, dict)
        # Verify pytest parser was used
        mock_pytest_parser_class.parse_pytest_log.assert_called()

    @patch("gitlab_analyzer.mcp.tools.trace_analysis_tools.LogParser")
    @patch("gitlab_analyzer.mcp.tools.trace_analysis_tools.PytestLogParser")
    def test_parse_trace_both_mode(
        self, mock_pytest_parser_class, mock_log_parser_class
    ):
        """Test both parsers mode"""
        from gitlab_analyzer.mcp.tools.trace_analysis_tools import (
            register_trace_analysis_tools,
        )

        # Setup mock log parser
        mock_log_parser_class.extract_log_entries.return_value = [
            Mock(
                message="General error",
                level="error",
                line_number=1,
                error_type="general",
                context="",
            )
        ]

        # Setup mock pytest parser with proper return structure
        mock_parser_result = Mock()
        mock_parser_result.detailed_failures = []
        mock_parser_result.short_summary = "No tests ran"
        mock_parser_result.statistics = {}
        mock_pytest_parser_class.parse_pytest_log.return_value = mock_parser_result

        mock_mcp = Mock()
        register_trace_analysis_tools(mock_mcp)

        # Get the function
        tool_function = None
        for call in mock_mcp.tool.call_args_list:
            if (
                call.args
                and hasattr(call.args[0], "__name__")
                and "parse_trace_for_errors" in call.args[0].__name__
            ):
                tool_function = call.args[0]
                break

        trace_content = "ERROR: Something failed\nFAILED test_example.py"

        result = asyncio.run(
            tool_function(trace_content=trace_content, analysis_type="both")
        )

        assert isinstance(result, dict)
        # Verify both parsers were used
        mock_log_parser_class.extract_log_entries.assert_called()
        mock_pytest_parser_class.parse_pytest_log.assert_called()

    @patch("gitlab_analyzer.mcp.tools.trace_analysis_tools.LogParser")
    def test_parse_trace_options(self, mock_log_parser_class):
        """Test different parsing options"""
        from gitlab_analyzer.mcp.tools.trace_analysis_tools import (
            register_trace_analysis_tools,
        )

        # Setup mock parser
        mock_log_parser = Mock()
        mock_log_parser.extract_log_entries.return_value = []
        mock_log_parser_class.return_value = mock_log_parser

        mock_mcp = Mock()
        register_trace_analysis_tools(mock_mcp)

        # Get the function
        tool_function = None
        for call in mock_mcp.tool.call_args_list:
            if (
                call.args
                and hasattr(call.args[0], "__name__")
                and "parse_trace_for_errors" in call.args[0].__name__
            ):
                tool_function = call.args[0]
                break

        trace_content = "ERROR: Test error"

        # Test with different options
        result = asyncio.run(
            tool_function(
                trace_content=trace_content,
                analysis_type="general",
                include_warnings=False,
                include_context=False,
                filter_duplicates=False,
            )
        )

        assert isinstance(result, dict)

    @patch("gitlab_analyzer.mcp.tools.trace_analysis_tools.LogParser")
    def test_parse_trace_error_handling(self, mock_log_parser_class):
        """Test error handling in trace parsing"""
        from gitlab_analyzer.mcp.tools.trace_analysis_tools import (
            register_trace_analysis_tools,
        )

        # Setup parser to raise exception
        mock_log_parser = Mock()
        mock_log_parser.extract_log_entries.side_effect = Exception("Parser error")
        mock_log_parser_class.return_value = mock_log_parser

        mock_mcp = Mock()
        register_trace_analysis_tools(mock_mcp)

        # Get the function
        tool_function = None
        for call in mock_mcp.tool.call_args_list:
            if (
                call.args
                and hasattr(call.args[0], "__name__")
                and "parse_trace_for_errors" in call.args[0].__name__
            ):
                tool_function = call.args[0]
                break

        trace_content = "ERROR: Test error"

        # Should handle exception gracefully
        result = asyncio.run(
            tool_function(trace_content=trace_content, analysis_type="general")
        )

        assert isinstance(result, dict)
        # Should contain error information or success flag
        assert "success" in result or "error" in result or "results" in result
