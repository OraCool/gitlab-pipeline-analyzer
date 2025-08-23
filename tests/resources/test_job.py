"""
Tests for job resources

Copyright (c) 2025 Siarhei Skuratovich
Licensed under the MIT License - see LICENSE file for details
"""

from unittest.mock import Mock

import pytest

from gitlab_analyzer.mcp.resources.job import register_job_resources


class TestJobResources:
    """Test job resource functionality"""

    @pytest.fixture
    def mock_mcp(self):
        """Mock MCP server"""
        mcp = Mock()
        mcp.resource = Mock()
        return mcp

    def test_register_job_resources(self, mock_mcp):
        """Test job resource registration"""
        # Execute registration
        register_job_resources(mock_mcp)

        # Verify resource decorator was called
        assert mock_mcp.resource.call_count == 1

        # Check the resource URI pattern
        call_args = mock_mcp.resource.call_args_list[0][0][0]
        expected_pattern = "gl://job/{project_id}/{job_id}"
        assert call_args == expected_pattern

    def test_register_job_resources_decorator_usage(self, mock_mcp):
        """Test that job resources are registered with correct decorator usage"""
        # Execute registration
        register_job_resources(mock_mcp)

        # Verify the decorator was called with the right pattern
        mock_mcp.resource.assert_called_once_with("gl://job/{project_id}/{job_id}")

        # Verify that the decorator was called (meaning a function was decorated)
        assert mock_mcp.resource.call_count == 1

    def test_register_job_resources_multiple_calls(self, mock_mcp):
        """Test that multiple calls to register don't cause issues"""
        # Execute registration multiple times
        register_job_resources(mock_mcp)
        register_job_resources(mock_mcp)

        # Should have been called twice
        assert mock_mcp.resource.call_count == 2

        # Both calls should have the same pattern
        call_args_list = [call[0][0] for call in mock_mcp.resource.call_args_list]
        assert all(args == "gl://job/{project_id}/{job_id}" for args in call_args_list)
