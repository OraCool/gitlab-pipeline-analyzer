"""
Simple coverage test for clean_trace_tools module

Copyright (c) 2025 Siarhei Skuratovich
Licensed under the MIT License - see LICENSE file for details
"""

from unittest.mock import Mock


class TestCleanTraceRegistration:
    """Simple test for clean trace tools registration"""

    def test_register_clean_trace_tools_simple(self):
        """Test clean trace tools registration without execution"""
        from gitlab_analyzer.mcp.tools.clean_trace_tools import (
            register_clean_trace_tools,
        )

        mock_mcp = Mock()

        # This should register the tools without errors
        register_clean_trace_tools(mock_mcp)

        # Verify that the tool decorator was called
        assert mock_mcp.tool.called
        assert mock_mcp.tool.call_count >= 1

        # Get the registered function
        registered_calls = mock_mcp.tool.call_args_list
        assert len(registered_calls) > 0

        # The first call should be the registration
        first_call = registered_calls[0]
        assert len(first_call.args) > 0
