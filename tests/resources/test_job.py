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

        # Verify resource decorator was called (7 job resources)
        assert mock_mcp.resource.call_count == 7

        # Check some core resource URI patterns
        call_args = [call[0][0] for call in mock_mcp.resource.call_args_list]
        expected_core_patterns = [
            "gl://job/{project_id}/{pipeline_id}/{job_id}",
            "gl://jobs/{project_id}/pipeline/{pipeline_id}",
            "gl://jobs/{project_id}/pipeline/{pipeline_id}/failed",
            "gl://jobs/{project_id}/pipeline/{pipeline_id}/success",
        ]

        for pattern in expected_core_patterns:
            assert pattern in call_args

    def test_register_job_resources_decorator_usage(self, mock_mcp):
        """Test that job resources are registered with correct decorator usage"""
        # Execute registration
        register_job_resources(mock_mcp)

        # Verify the decorators were called with the right patterns
        expected_core_patterns = [
            "gl://job/{project_id}/{pipeline_id}/{job_id}",
            "gl://jobs/{project_id}/pipeline/{pipeline_id}",
            "gl://jobs/{project_id}/pipeline/{pipeline_id}/failed",
            "gl://jobs/{project_id}/pipeline/{pipeline_id}/success",
        ]

        # Check that all expected core patterns were used
        actual_patterns = [call[0][0] for call in mock_mcp.resource.call_args_list]
        assert len(actual_patterns) == 7  # Total resources registered
        for expected_pattern in expected_core_patterns:
            assert expected_pattern in actual_patterns

    def test_register_job_resources_multiple_calls(self, mock_mcp):
        """Test that multiple calls to register don't cause issues"""
        # Execute registration multiple times
        register_job_resources(mock_mcp)
        register_job_resources(mock_mcp)

        # Should have been called 14 times total (7 per registration)
        assert mock_mcp.resource.call_count == 14

        # Check that patterns are consistent
        call_args_list = [call[0][0] for call in mock_mcp.resource.call_args_list]
        expected_core_patterns = [
            "gl://job/{project_id}/{pipeline_id}/{job_id}",
            "gl://jobs/{project_id}/pipeline/{pipeline_id}",
            "gl://jobs/{project_id}/pipeline/{pipeline_id}/failed",
            "gl://jobs/{project_id}/pipeline/{pipeline_id}/success",
        ]

        # Each core pattern should appear twice
        for pattern in expected_core_patterns:
            assert call_args_list.count(pattern) == 2
