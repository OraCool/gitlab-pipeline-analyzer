"""
Tests for error resources

Copyright (c) 2025 Siarhei Skuratovich
Licensed under the MIT License - see LICENSE file for details
"""

from unittest.mock import Mock

import pytest

from gitlab_analyzer.mcp.resources.error import register_error_resources


class TestErrorResources:
    """Test error resource functionality"""

    @pytest.fixture
    def mock_mcp(self):
        """Mock MCP server"""
        mcp = Mock()
        mcp.resource = Mock()
        return mcp

    def test_register_error_resources(self, mock_mcp):
        """Test error resource registration"""
        # Execute registration
        register_error_resources(mock_mcp)

        # Verify resource decorators were called (4 error resources)
        assert mock_mcp.resource.call_count == 4

        # Check the resource URI patterns
        call_args = [call[0][0] for call in mock_mcp.resource.call_args_list]
        expected_patterns = [
            "gl://error/{project_id}/{job_id}",
            "gl://error/{project_id}/{job_id}?mode={mode}",
            "gl://error/{project_id}/{job_id}/{error_id}",
            "gl://error/{project_id}/{job_id}/{error_id}?mode={mode}",
        ]

        for pattern in expected_patterns:
            assert pattern in call_args

    def test_register_error_resources_decorator_usage(self, mock_mcp):
        """Test that error resources are registered with correct decorator usage"""
        # Execute registration
        register_error_resources(mock_mcp)

        # Verify the decorators were called with the right patterns
        expected_calls = [
            "gl://error/{project_id}/{job_id}",
            "gl://error/{project_id}/{job_id}?mode={mode}",
            "gl://error/{project_id}/{job_id}/{error_id}",
            "gl://error/{project_id}/{job_id}/{error_id}?mode={mode}",
        ]

        # Check that all expected patterns were used
        actual_calls = [call[0][0] for call in mock_mcp.resource.call_args_list]
        assert len(actual_calls) == 4
        for expected_call in expected_calls:
            assert expected_call in actual_calls

    def test_register_error_resources_multiple_calls(self, mock_mcp):
        """Test that multiple calls to register don't cause issues"""
        # Execute registration multiple times
        register_error_resources(mock_mcp)
        register_error_resources(mock_mcp)

        # Should have been called 8 times total (4 per registration)
        assert mock_mcp.resource.call_count == 8

        # Check that patterns are consistent
        call_args_list = [call[0][0] for call in mock_mcp.resource.call_args_list]
        expected_patterns = [
            "gl://error/{project_id}/{job_id}",
            "gl://error/{project_id}/{job_id}?mode={mode}",
            "gl://error/{project_id}/{job_id}/{error_id}",
            "gl://error/{project_id}/{job_id}/{error_id}?mode={mode}",
        ]

        # Each pattern should appear twice
        for pattern in expected_patterns:
            assert call_args_list.count(pattern) == 2
