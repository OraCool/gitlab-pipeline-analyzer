"""
Simple tests to increase module coverage

Copyright (c) 2025 Siarhei Skuratovich
Licensed under the MIT License - see LICENSE file for details
"""

from unittest.mock import Mock


class TestModuleCoverage:
    """Simple tests to increase coverage of various modules"""

    def test_trace_analysis_tools_import(self):
        """Test trace analysis tools module import"""
        from gitlab_analyzer.mcp.tools.trace_analysis_tools import (
            register_trace_analysis_tools,
        )

        # Test that function can be imported
        assert callable(register_trace_analysis_tools)

    def test_clean_trace_tools_import(self):
        """Test clean trace tools module import"""
        from gitlab_analyzer.mcp.tools.clean_trace_tools import (
            register_clean_trace_tools,
        )

        # Test that function can be imported
        assert callable(register_clean_trace_tools)

    def test_error_resources_import(self):
        """Test error resources module import"""
        from gitlab_analyzer.mcp.resources.error import register_error_resources

        # Test that function can be imported
        assert callable(register_error_resources)

    def test_file_resources_import(self):
        """Test file resources module import"""
        from gitlab_analyzer.mcp.resources.file import register_file_resources

        # Test that function can be imported
        assert callable(register_file_resources)

    def test_trace_analysis_registration(self):
        """Test trace analysis tools registration"""
        from gitlab_analyzer.mcp.tools.trace_analysis_tools import (
            register_trace_analysis_tools,
        )

        mock_mcp = Mock()
        mock_mcp.tool = Mock()

        # Should not raise exception
        register_trace_analysis_tools(mock_mcp)

        # Should have registered at least one tool
        assert mock_mcp.tool.call_count >= 1

    def test_clean_trace_registration(self):
        """Test clean trace tools registration"""
        from gitlab_analyzer.mcp.tools.clean_trace_tools import (
            register_clean_trace_tools,
        )

        mock_mcp = Mock()
        mock_mcp.tool = Mock()

        # Should not raise exception
        register_clean_trace_tools(mock_mcp)

        # Should have registered at least one tool
        assert mock_mcp.tool.call_count >= 1

    def test_error_resources_registration(self):
        """Test error resources registration"""
        from gitlab_analyzer.mcp.resources.error import register_error_resources

        mock_mcp = Mock()
        mock_mcp.resource = Mock()

        # Should not raise exception
        register_error_resources(mock_mcp)

        # Should have registered at least one resource
        assert mock_mcp.resource.call_count >= 1

    def test_file_resources_registration(self):
        """Test file resources registration"""
        from gitlab_analyzer.mcp.resources.file import register_file_resources

        mock_mcp = Mock()
        mock_mcp.resource = Mock()

        # Should not raise exception
        register_file_resources(mock_mcp)

        # Should have registered at least one resource
        assert mock_mcp.resource.call_count >= 1

    def test_utils_debug_functions(self):
        """Test debug utility functions"""
        from gitlab_analyzer.utils.debug import (
            debug_print,
            verbose_debug_print,
            very_verbose_debug_print,
        )

        # Test that functions can be called without error
        debug_print("test message")
        verbose_debug_print("test verbose message")
        very_verbose_debug_print("test very verbose message")

    def test_parsers_import(self):
        """Test parsers module imports"""
        from gitlab_analyzer.parsers.base_parser import BaseParser
        from gitlab_analyzer.parsers.log_parser import LogParser
        from gitlab_analyzer.parsers.pytest_parser import PytestLogParser

        # Test that classes can be imported
        assert LogParser is not None
        assert PytestLogParser is not None
        assert BaseParser is not None
