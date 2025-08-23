"""
Tests for file resources

Copyright (c) 2025 Siarhei Skuratovich
Licensed under the MIT License - see LICENSE file for details
"""

import json
from unittest.mock import AsyncMock, Mock, patch

import pytest

from gitlab_analyzer.mcp.resources.file import (
    _get_file_analysis,
    register_file_resources,
)


class TestFileResources:
    """Test file resource functionality"""

    @pytest.fixture
    def mock_analyzer(self):
        """Mock GitLab analyzer"""
        analyzer = Mock()
        analyzer.get_job_trace = AsyncMock(return_value="mock trace content")
        return analyzer

    @pytest.fixture
    def mock_cache_manager(self):
        """Mock cache manager"""
        cache_manager = Mock()
        cache_manager.get = AsyncMock(return_value=None)
        cache_manager.set = AsyncMock()
        return cache_manager

    @pytest.fixture
    def mock_log_entries(self):
        """Mock log entries from parser"""
        entry1 = Mock()
        entry1.message = "Error in test_file.py"
        entry1.level = "error"
        entry1.line_number = 42
        entry1.test_file = "test_file.py"
        entry1.file_path = "test_file.py"
        entry1.exception_type = "AssertionError"
        entry1.exception_message = "Test failed"
        entry1.context = ["context line 1", "context line 2"]

        entry2 = Mock()
        entry2.message = "Warning in other_file.py"
        entry2.level = "warning"
        entry2.line_number = None
        entry2.test_file = None
        entry2.file_path = "other_file.py"
        entry2.exception_type = None
        entry2.exception_message = None
        entry2.context = []

        return [entry1, entry2]

    @patch("gitlab_analyzer.mcp.resources.file.get_cache_manager")
    @patch("gitlab_analyzer.mcp.resources.file.get_gitlab_analyzer")
    @patch("gitlab_analyzer.mcp.resources.file.get_mcp_info")
    @patch("gitlab_analyzer.mcp.resources.file.LogParser")
    async def test_get_file_analysis_basic(
        self,
        mock_parser_class,
        mock_get_mcp_info,
        mock_get_analyzer,
        mock_get_cache,
        mock_log_entries,
        mock_cache_manager,
        mock_analyzer,
    ):
        """Test basic file analysis functionality"""
        # Setup parser mock
        mock_parser = Mock()
        mock_parser.extract_log_entries.return_value = mock_log_entries
        mock_parser_class.return_value = mock_parser

        # Setup other mocks
        mock_get_cache.return_value = mock_cache_manager
        mock_get_analyzer.return_value = mock_analyzer
        mock_get_mcp_info.return_value = {"tool": "test", "timestamp": "2025-01-01"}

        # Test parameters
        project_id = "123"
        job_id = "456"
        file_path = "test_file.py"
        response_mode = "balanced"

        # Execute
        result = await _get_file_analysis(project_id, job_id, file_path, response_mode)

        # Verify
        data = json.loads(result)

        # Check structure
        assert "file_analysis" in data
        assert "resource_uri" in data
        assert "cached_at" in data
        assert "metadata" in data
        assert "mcp_info" in data

        # Check file analysis content
        file_data = data["file_analysis"]
        assert file_data["project_id"] == project_id
        assert file_data["job_id"] == int(job_id)
        assert file_data["file_path"] == file_path

        # Check metadata
        metadata = data["metadata"]
        assert metadata["response_mode"] == response_mode
        assert metadata["file_type"] == "test"

        # Use mocks to avoid unused variable warnings
        assert mock_parser_class.called
        assert mock_get_mcp_info.called
        assert mock_get_analyzer.called

    @patch("gitlab_analyzer.mcp.resources.file.get_cache_manager")
    @patch("gitlab_analyzer.mcp.resources.file.get_gitlab_analyzer")
    async def test_get_file_analysis_cached(
        self,
        mock_get_analyzer,
        mock_get_cache,
        mock_cache_manager,
    ):
        """Test file analysis with cached data"""
        # Setup cached data
        cached_data = {
            "file_analysis": {
                "project_id": "123",
                "job_id": 456,
                "file_path": "test_file.py",
                "errors": [],
                "error_count": 0,
            },
            "cached": True,
        }
        mock_cache_manager.get.return_value = cached_data
        mock_get_cache.return_value = mock_cache_manager

        # Execute
        result = await _get_file_analysis("123", "456", "test_file.py", "balanced")

        # Verify
        data = json.loads(result)
        assert data == cached_data

        # Verify cache was checked but analyzer was not called
        mock_cache_manager.get.assert_called_once()
        mock_get_analyzer.assert_not_called()

    @pytest.mark.parametrize("response_mode", ["minimal", "balanced", "fixing", "full"])
    @patch("gitlab_analyzer.mcp.resources.file.get_cache_manager")
    @patch("gitlab_analyzer.mcp.resources.file.get_gitlab_analyzer")
    @patch("gitlab_analyzer.mcp.resources.file.get_mcp_info")
    @patch("gitlab_analyzer.mcp.resources.file.optimize_tool_response")
    @patch("gitlab_analyzer.parsers.log_parser.LogParser")
    async def test_get_file_analysis_modes(
        self,
        mock_parser_class,
        mock_optimize,
        mock_get_mcp_info,
        mock_get_analyzer,
        mock_get_cache,
        mock_cache_manager,
        mock_analyzer,
        mock_log_entries,
        response_mode,
    ):
        """Test file analysis with different response modes"""
        # Setup mocks
        mock_get_cache.return_value = mock_cache_manager
        mock_get_analyzer.return_value = mock_analyzer
        mock_get_mcp_info.return_value = {"tool": "test"}

        mock_parser = Mock()
        mock_parser.extract_log_entries.return_value = mock_log_entries
        mock_parser_class.return_value = mock_parser

        # Mock optimization to return the same data (testing that it's called)
        mock_optimize.side_effect = lambda x, mode: x

        # Execute
        result = await _get_file_analysis("123", "456", "test_file.py", response_mode)

        # Verify
        data = json.loads(result)

        # Check mode is set correctly
        assert data["metadata"]["response_mode"] == response_mode
        assert f"mode={response_mode}" in data["resource_uri"]

        # Verify optimization was called with correct mode
        mock_optimize.assert_called_once()
        call_args = mock_optimize.call_args
        assert call_args[1] == response_mode  # Second argument should be the mode

        # Verify cache key includes mode
        cache_call = mock_cache_manager.get.call_args[0][0]
        assert response_mode in cache_call

    @patch("gitlab_analyzer.mcp.resources.file.get_cache_manager")
    @patch("gitlab_analyzer.mcp.resources.file.get_gitlab_analyzer")
    async def test_get_file_analysis_error_handling(
        self, mock_get_analyzer, mock_get_cache, mock_cache_manager, mock_analyzer
    ):
        """Test error handling in file analysis"""
        # Setup mocks
        mock_get_cache.return_value = mock_cache_manager
        mock_get_analyzer.return_value = mock_analyzer

        # Make analyzer raise an exception
        mock_analyzer.get_job_trace.side_effect = Exception("GitLab API error")

        # Execute
        result = await _get_file_analysis("123", "456", "test_file.py", "balanced")

        # Verify error response
        data = json.loads(result)
        assert "error" in data
        assert "Failed to get file resource" in data["error"]
        assert data["project_id"] == "123"
        assert data["job_id"] == "456"
        assert data["file_path"] == "test_file.py"

    def test_file_type_classification(self):
        """Test file type classification"""
        from gitlab_analyzer.mcp.resources.file import _classify_file_type

        # Test file types
        assert _classify_file_type("test_example.py") == "test"
        assert _classify_file_type("example_test.py") == "test"
        assert _classify_file_type("tests/test_something.py") == "test"
        assert _classify_file_type("src/main.py") == "source"
        assert _classify_file_type("app.js") == "source"
        assert _classify_file_type("config.yaml") == "config"
        assert _classify_file_type("settings.json") == "config"
        assert _classify_file_type("README.md") == "documentation"
        assert _classify_file_type("unknown.xyz") == "unknown"

    def test_register_file_resources(self):
        """Test resource registration"""
        # Mock MCP server
        mock_mcp = Mock()

        # Execute registration
        register_file_resources(mock_mcp)

        # Verify resource decorators were called
        assert mock_mcp.resource.call_count == 2

        # Check the resource URI patterns
        call_args = [call[0][0] for call in mock_mcp.resource.call_args_list]
        expected_patterns = [
            "gl://file/{project_id}/{job_id}/{file_path}",
            "gl://file/{project_id}/{job_id}/{file_path}?mode={mode}",
        ]

        for pattern in expected_patterns:
            assert pattern in call_args

    @pytest.mark.parametrize(
        "file_path,contains_in_message,expected_match",
        [
            ("test_file.py", "test_file.py", True),
            ("other_file.py", "test_file.py", False),
            ("test_file.py", "some/path/test_file.py", True),
        ],
    )
    @patch("gitlab_analyzer.mcp.resources.file.get_cache_manager")
    @patch("gitlab_analyzer.mcp.resources.file.get_gitlab_analyzer")
    @patch("gitlab_analyzer.mcp.resources.file.get_mcp_info")
    @patch("gitlab_analyzer.parsers.log_parser.LogParser")
    async def test_file_filtering(
        self,
        mock_parser_class,
        mock_get_mcp_info,
        mock_get_analyzer,
        mock_get_cache,
        mock_cache_manager,
        mock_analyzer,
        file_path,
        contains_in_message,
        expected_match,
    ):
        """Test that errors are correctly filtered by file path"""
        # Setup mocks
        mock_get_cache.return_value = mock_cache_manager
        mock_get_analyzer.return_value = mock_analyzer
        mock_get_mcp_info.return_value = {"tool": "test"}

        # Create log entry with specific message
        entry = Mock()
        entry.message = f"Error in {contains_in_message}"
        entry.level = "error"
        entry.line_number = 42
        entry.test_file = None
        entry.file_path = None
        entry.exception_type = "Error"
        entry.exception_message = "Test error"
        entry.context = []

        mock_parser = Mock()
        mock_parser.extract_log_entries.return_value = [entry]
        mock_parser_class.return_value = mock_parser

        # Execute
        result = await _get_file_analysis("123", "456", file_path, "balanced")

        # Verify
        data = json.loads(result)
        errors = data["file_analysis"]["errors"]

        if expected_match:
            assert len(errors) == 1
            assert errors[0]["message"] == entry.message
        else:
            assert len(errors) == 0
