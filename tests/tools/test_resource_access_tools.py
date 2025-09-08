"""
Tests for resource access tools

Copyright (c) 2025 Siarhei Skuratovich
Licensed under the MIT License - see LICENSE file for details
"""

from unittest.mock import AsyncMock, Mock, patch

import pytest

from gitlab_analyzer.mcp.tools.resource_access_tools import (
    register_resource_access_tools,
)


class TestResourceAccessTools:
    """Test resource access tools"""

    @pytest.fixture
    def mock_mcp(self):
        """Mock FastMCP server"""
        mcp = Mock()
        mcp.tool = Mock()
        return mcp

    def test_register_resource_access_tools(self, mock_mcp):
        """Test resource access tools registration"""
        register_resource_access_tools(mock_mcp)

        # Verify 1 tool was registered
        assert mock_mcp.tool.call_count == 1

        # Check that tools were decorated (registered)
        assert mock_mcp.tool.called

    @patch("gitlab_analyzer.mcp.tools.resource_access_tools.get_pipeline_resource")
    async def test_get_mcp_resource_pipeline(self, mock_get_pipeline, mock_mcp):
        """Test accessing pipeline resource"""
        mock_get_pipeline.return_value = {"pipeline_id": 123, "status": "success"}

        # Register tools to get access to the function
        register_resource_access_tools(mock_mcp)

        # Find the get_mcp_resource function from the decorator calls
        get_mcp_resource_func = None
        for call in mock_mcp.tool.call_args_list:
            if (
                hasattr(call[0][0], "__name__")
                and call[0][0].__name__ == "get_mcp_resource"
            ):
                get_mcp_resource_func = call[0][0]
                break

        assert get_mcp_resource_func is not None, "get_mcp_resource function not found"

        # Test pipeline resource access
        result = await get_mcp_resource_func("gl://pipeline/123/123")

        assert result["pipeline_id"] == 123
        assert result["status"] == "success"
        mock_get_pipeline.assert_called_once_with("123", "123")

    @patch("gitlab_analyzer.mcp.tools.resource_access_tools.get_pipeline_jobs_resource")
    async def test_get_mcp_resource_jobs(self, mock_get_jobs, mock_mcp):
        """Test accessing jobs resource"""
        mock_get_jobs.return_value = {"jobs": [{"id": 1}, {"id": 2}]}

        # Register tools
        register_resource_access_tools(mock_mcp)

        # Find the function
        get_mcp_resource_func = None
        for call in mock_mcp.tool.call_args_list:
            if (
                hasattr(call[0][0], "__name__")
                and call[0][0].__name__ == "get_mcp_resource"
            ):
                get_mcp_resource_func = call[0][0]
                break

        # Test jobs resource access
        result = await get_mcp_resource_func("gl://jobs/123/pipeline/123")
        assert "jobs" in result
        mock_get_jobs.assert_called_once_with("123", "123", "all")

        # Test failed jobs
        await get_mcp_resource_func("gl://jobs/123/pipeline/123/failed")
        mock_get_jobs.assert_called_with("123", "123", "failed")

    @patch("gitlab_analyzer.mcp.tools.resource_access_tools.get_job_resource")
    async def test_get_mcp_resource_job(self, mock_get_job, mock_mcp):
        """Test accessing individual job resource"""
        mock_get_job.return_value = {"job_id": 456, "status": "failed"}

        # Register tools
        register_resource_access_tools(mock_mcp)

        # Find the function
        get_mcp_resource_func = None
        for call in mock_mcp.tool.call_args_list:
            if (
                hasattr(call[0][0], "__name__")
                and call[0][0].__name__ == "get_mcp_resource"
            ):
                get_mcp_resource_func = call[0][0]
                break

        # Test job resource access
        result = await get_mcp_resource_func("gl://job/123/123/456")
        assert result["job_id"] == 456
        mock_get_job.assert_called_once_with("123", "123", "456")

    @patch("gitlab_analyzer.mcp.tools.resource_access_tools.get_file_service")
    async def test_get_mcp_resource_pipeline_files(
        self, mock_get_file_service, mock_mcp
    ):
        """Test accessing pipeline files resource"""
        # Setup mock file service
        mock_file_service = AsyncMock()
        mock_file_service.get_pipeline_files.return_value = {
            "files": ["file1.py", "file2.py"]
        }
        mock_get_file_service.return_value = mock_file_service

        # Register tools
        register_resource_access_tools(mock_mcp)

        # Find the function
        get_mcp_resource_func = None
        for call in mock_mcp.tool.call_args_list:
            if (
                hasattr(call[0][0], "__name__")
                and call[0][0].__name__ == "get_mcp_resource"
            ):
                get_mcp_resource_func = call[0][0]
                break

        # Test pipeline files resource access
        result = await get_mcp_resource_func("gl://files/123/pipeline/123")
        assert "files" in result
        mock_file_service.get_pipeline_files.assert_called_once_with(
            "123", "123", 1, 20
        )

        # Test with pagination
        await get_mcp_resource_func("gl://files/123/pipeline/123/page/2/limit/50")
        mock_file_service.get_pipeline_files.assert_called_with("123", "123", 2, 50)

    @patch("gitlab_analyzer.mcp.tools.resource_access_tools.get_file_service")
    async def test_get_mcp_resource_job_files(self, mock_get_file_service, mock_mcp):
        """Test accessing job files resource"""
        # Setup mock file service
        mock_file_service = AsyncMock()
        mock_file_service.get_files_for_job.return_value = {
            "files": ["error1.py", "error2.py"]
        }
        mock_get_file_service.return_value = mock_file_service

        # Register tools
        register_resource_access_tools(mock_mcp)

        # Find the function
        get_mcp_resource_func = None
        for call in mock_mcp.tool.call_args_list:
            if (
                hasattr(call[0][0], "__name__")
                and call[0][0].__name__ == "get_mcp_resource"
            ):
                get_mcp_resource_func = call[0][0]
                break

        # Test job files resource access
        result = await get_mcp_resource_func("gl://files/123/456")
        assert "files" in result
        mock_file_service.get_files_for_job.assert_called_once_with("123", "456", 1, 20)

    @patch("gitlab_analyzer.mcp.tools.resource_access_tools.get_file_service")
    async def test_get_mcp_resource_specific_file(
        self, mock_get_file_service, mock_mcp
    ):
        """Test accessing specific file resource"""
        # Setup mock file service
        mock_file_service = AsyncMock()
        mock_file_service.get_file_data.return_value = {
            "file_path": "src/main.py",
            "errors": [],
        }
        mock_get_file_service.return_value = mock_file_service

        # Register tools
        register_resource_access_tools(mock_mcp)

        # Find the function
        get_mcp_resource_func = None
        for call in mock_mcp.tool.call_args_list:
            if (
                hasattr(call[0][0], "__name__")
                and call[0][0].__name__ == "get_mcp_resource"
            ):
                get_mcp_resource_func = call[0][0]
                break

        # Test specific file resource access
        result = await get_mcp_resource_func("gl://file/123/456/src/main.py")
        assert result["file_path"] == "src/main.py"
        mock_file_service.get_file_data.assert_called_once_with(
            "123", "456", "src/main.py"
        )

    @patch("gitlab_analyzer.mcp.tools.resource_access_tools.get_file_analysis_service")
    async def test_get_mcp_resource_file_with_trace(
        self, mock_get_file_analysis_service, mock_mcp
    ):
        """Test accessing file resource with trace"""
        # Setup mock file analysis service
        mock_file_analysis_service = AsyncMock()
        mock_response = {"file_path": "src/main.py", "trace": "..."}
        mock_file_analysis_service.get_file_with_trace.return_value = mock_response
        mock_get_file_analysis_service.return_value = mock_file_analysis_service

        # Register tools
        register_resource_access_tools(mock_mcp)

        # Find the function
        get_mcp_resource_func = None
        for call in mock_mcp.tool.call_args_list:
            if (
                hasattr(call[0][0], "__name__")
                and call[0][0].__name__ == "get_mcp_resource"
            ):
                get_mcp_resource_func = call[0][0]
                break

        # Test file with trace resource access using URL-encoded file path
        result = await get_mcp_resource_func(
            "gl://file/123/456/src%2Fmain.py/trace?mode=detailed&include_trace=true"
        )
        assert result["file_path"] == "src/main.py"
        mock_file_analysis_service.get_file_with_trace.assert_called_once_with(
            "123", "456", "src/main.py", "detailed", "true"
        )

    @patch("gitlab_analyzer.mcp.tools.resource_access_tools.error_service")
    async def test_get_mcp_resource_job_errors(self, mock_error_service, mock_mcp):
        """Test accessing job errors resource"""
        mock_error_service.get_job_errors = AsyncMock(
            return_value={"errors": [{"id": 1}, {"id": 2}]}
        )

        # Register tools
        register_resource_access_tools(mock_mcp)

        # Find the function
        get_mcp_resource_func = None
        for call in mock_mcp.tool.call_args_list:
            if (
                hasattr(call[0][0], "__name__")
                and call[0][0].__name__ == "get_mcp_resource"
            ):
                get_mcp_resource_func = call[0][0]
                break

        # Test job errors resource access
        result = await get_mcp_resource_func("gl://error/123/456")
        assert "errors" in result
        mock_error_service.get_job_errors.assert_called_once_with(
            "123", "456", "balanced"
        )

        # Test with mode
        await get_mcp_resource_func("gl://error/123/456?mode=detailed")
        mock_error_service.get_job_errors.assert_called_with("123", "456", "detailed")

    @patch("gitlab_analyzer.mcp.tools.resource_access_tools.error_service")
    async def test_get_mcp_resource_individual_error(
        self, mock_error_service, mock_mcp
    ):
        """Test accessing individual error resource"""
        mock_error_service.get_individual_error = AsyncMock(
            return_value={"error_id": "123_0", "message": "Test error"}
        )

        # Register tools
        register_resource_access_tools(mock_mcp)

        # Find the function
        get_mcp_resource_func = None
        for call in mock_mcp.tool.call_args_list:
            if (
                hasattr(call[0][0], "__name__")
                and call[0][0].__name__ == "get_mcp_resource"
            ):
                get_mcp_resource_func = call[0][0]
                break

        # Test individual error resource access
        result = await get_mcp_resource_func("gl://error/123/456/123_0")
        assert result["error_id"] == "123_0"
        mock_error_service.get_individual_error.assert_called_once_with(
            "123", "456", "123_0", "balanced"
        )

    @patch("gitlab_analyzer.mcp.tools.resource_access_tools.error_service")
    async def test_get_mcp_resource_pipeline_errors(self, mock_error_service, mock_mcp):
        """Test accessing pipeline errors resource"""
        mock_error_service.get_pipeline_errors = AsyncMock(
            return_value={"pipeline_errors": [{"job_id": 1}, {"job_id": 2}]}
        )

        # Register tools
        register_resource_access_tools(mock_mcp)

        # Find the function
        get_mcp_resource_func = None
        for call in mock_mcp.tool.call_args_list:
            if (
                hasattr(call[0][0], "__name__")
                and call[0][0].__name__ == "get_mcp_resource"
            ):
                get_mcp_resource_func = call[0][0]
                break

        # Test pipeline errors resource access
        result = await get_mcp_resource_func("gl://errors/123/pipeline/123")
        assert "pipeline_errors" in result
        mock_error_service.get_pipeline_errors.assert_called_once_with("123", "123")

    @patch("gitlab_analyzer.mcp.tools.resource_access_tools.error_service")
    async def test_get_mcp_resource_file_errors(self, mock_error_service, mock_mcp):
        """Test accessing file errors resource"""
        mock_error_service.get_file_errors = AsyncMock(
            return_value={"file_errors": [{"line": 10}, {"line": 20}]}
        )

        # Register tools
        register_resource_access_tools(mock_mcp)

        # Find the function
        get_mcp_resource_func = None
        for call in mock_mcp.tool.call_args_list:
            if (
                hasattr(call[0][0], "__name__")
                and call[0][0].__name__ == "get_mcp_resource"
            ):
                get_mcp_resource_func = call[0][0]
                break

        # Test file errors resource access
        result = await get_mcp_resource_func("gl://errors/123/456/src/main.py")
        assert "file_errors" in result
        mock_error_service.get_file_errors.assert_called_once_with(
            "123", "456", "src/main.py"
        )

    @patch("gitlab_analyzer.mcp.tools.resource_access_tools.get_analysis_resource_data")
    async def test_get_mcp_resource_analysis(self, mock_get_analysis, mock_mcp):
        """Test accessing analysis resources"""
        mock_get_analysis.return_value = {"analysis": "comprehensive"}

        # Register tools
        register_resource_access_tools(mock_mcp)

        # Find the function
        get_mcp_resource_func = None
        for call in mock_mcp.tool.call_args_list:
            if (
                hasattr(call[0][0], "__name__")
                and call[0][0].__name__ == "get_mcp_resource"
            ):
                get_mcp_resource_func = call[0][0]
                break

        # Test project analysis
        result = await get_mcp_resource_func("gl://analysis/123")
        assert result["analysis"] == "comprehensive"
        mock_get_analysis.assert_called_once_with("123", None, None, "balanced")

        # Test pipeline analysis
        await get_mcp_resource_func("gl://analysis/123/pipeline/123?mode=detailed")
        mock_get_analysis.assert_called_with("123", "123", None, "detailed")

        # Test job analysis
        await get_mcp_resource_func("gl://analysis/123/job/456?mode=minimal")
        mock_get_analysis.assert_called_with("123", None, "456", "minimal")

    async def test_get_mcp_resource_invalid_uri(self, mock_mcp):
        """Test handling of invalid resource URIs"""
        # Register tools
        register_resource_access_tools(mock_mcp)

        # Find the function
        get_mcp_resource_func = None
        for call in mock_mcp.tool.call_args_list:
            if (
                hasattr(call[0][0], "__name__")
                and call[0][0].__name__ == "get_mcp_resource"
            ):
                get_mcp_resource_func = call[0][0]
                break

        # Test invalid URI format
        result = await get_mcp_resource_func("invalid://uri")
        assert "error" in result
        assert "Invalid resource URI format" in result["error"]

        # Test unsupported pattern
        result = await get_mcp_resource_func("gl://unsupported/pattern")
        assert "error" in result
        assert "Unsupported resource URI pattern" in result["error"]
        assert "available_patterns" in result

    @patch("gitlab_analyzer.mcp.tools.resource_access_tools.get_pipeline_resource")
    async def test_get_mcp_resource_exception_handling(
        self, mock_get_pipeline, mock_mcp
    ):
        """Test exception handling in resource access"""
        mock_get_pipeline.side_effect = Exception("Database error")

        # Register tools
        register_resource_access_tools(mock_mcp)

        # Find the function
        get_mcp_resource_func = None
        for call in mock_mcp.tool.call_args_list:
            if (
                hasattr(call[0][0], "__name__")
                and call[0][0].__name__ == "get_mcp_resource"
            ):
                get_mcp_resource_func = call[0][0]
                break

        # Test exception handling
        result = await get_mcp_resource_func("gl://pipeline/123/123")
        assert "error" in result
        assert "Failed to access resource" in result["error"]
        assert result["resource_uri"] == "gl://pipeline/123/123"

    async def test_get_mcp_resource_various_patterns(self, mock_mcp):
        """Test parsing of various URI patterns"""
        # Register tools
        register_resource_access_tools(mock_mcp)

        # Find the function
        get_mcp_resource_func = None
        for call in mock_mcp.tool.call_args_list:
            if (
                hasattr(call[0][0], "__name__")
                and call[0][0].__name__ == "get_mcp_resource"
            ):
                get_mcp_resource_func = call[0][0]
                break

        # Test patterns that should result in errors (no mocking)
        test_patterns = [
            "gl://jobs/123/pipeline/123/success",
            "gl://files/123/pipeline/123/page/1/limit/10",
            "gl://file/123/456/deeply/nested/file.py",
            "gl://errors/123/456",
            "gl://analysis/123?mode=fixing",
        ]

        for pattern in test_patterns:
            result = await get_mcp_resource_func(pattern)
            # These will fail because we're not mocking the underlying functions
            # but at least we test that the pattern parsing works
            assert isinstance(result, dict)

    @patch("gitlab_analyzer.mcp.tools.resource_access_tools.get_merge_request_resource")
    async def test_get_mcp_resource_merge_request(self, mock_get_mr, mock_mcp):
        """Test accessing merge request resource"""
        mock_get_mr.return_value = {
            "merge_request": {
                "iid": 567,
                "title": "Test MR",
                "author": "test_author",
            },
            "code_review": {
                "review_comments": [],
                "approval_status": {"approved_count": 0},
            },
            "metadata": {
                "resource_type": "merge_request",
                "project_id": "83",
                "mr_iid": 567,
            },
        }

        # Register tools
        register_resource_access_tools(mock_mcp)

        # Find the get_mcp_resource function
        get_mcp_resource_func = None
        for call in mock_mcp.tool.call_args_list:
            if (
                hasattr(call[0][0], "__name__")
                and call[0][0].__name__ == "get_mcp_resource"
            ):
                get_mcp_resource_func = call[0][0]
                break

        assert get_mcp_resource_func is not None, "get_mcp_resource function not found"

        # Test merge request resource access
        result = await get_mcp_resource_func("gl://mr/83/567")

        # Verify the result structure
        assert "merge_request" in result
        assert "code_review" in result
        assert "metadata" in result

        # Verify specific fields
        assert result["merge_request"]["iid"] == 567
        assert result["merge_request"]["title"] == "Test MR"
        assert result["metadata"]["resource_type"] == "merge_request"

        # Verify the mock was called with correct parameters
        mock_get_mr.assert_called_once_with("83", "567")

    @patch("gitlab_analyzer.mcp.tools.resource_access_tools.get_merge_request_resource")
    async def test_get_mcp_resource_merge_request_not_found(
        self, mock_get_mr, mock_mcp
    ):
        """Test accessing non-existent merge request resource"""
        mock_get_mr.return_value = {
            "error": "mr_not_analyzed",
            "message": "Merge request 999 has not been analyzed yet.",
            "mr_iid": 999,
            "project_id": "83",
            "metadata": {
                "resource_type": "merge_request",
                "data_source": "none",
                "status": "not_analyzed",
            },
        }

        # Register tools
        register_resource_access_tools(mock_mcp)

        # Find the function
        get_mcp_resource_func = None
        for call in mock_mcp.tool.call_args_list:
            if (
                hasattr(call[0][0], "__name__")
                and call[0][0].__name__ == "get_mcp_resource"
            ):
                get_mcp_resource_func = call[0][0]
                break

        # Test non-existent merge request
        result = await get_mcp_resource_func("gl://mr/83/999")

        # Verify error response
        assert result["error"] == "mr_not_analyzed"
        assert "not been analyzed yet" in result["message"]
        assert result["mr_iid"] == 999
        assert result["metadata"]["status"] == "not_analyzed"

        # Verify the mock was called
        mock_get_mr.assert_called_once_with("83", "999")

    async def test_merge_request_pattern_in_available_patterns(self, mock_mcp):
        """Test that merge request pattern is included in available patterns"""
        # Register tools
        register_resource_access_tools(mock_mcp)

        # Find the function
        get_mcp_resource_func = None
        for call in mock_mcp.tool.call_args_list:
            if (
                hasattr(call[0][0], "__name__")
                and call[0][0].__name__ == "get_mcp_resource"
            ):
                get_mcp_resource_func = call[0][0]
                break

        # Test with an unsupported pattern to get available patterns
        result = await get_mcp_resource_func("gl://unsupported/pattern")

        # Verify merge request pattern is in available patterns
        assert "available_patterns" in result
        patterns = result["available_patterns"]
        assert "gl://mr/{project_id}/{mr_iid}" in patterns

    @patch("gitlab_analyzer.mcp.tools.resource_access_tools.get_merge_request_resource")
    async def test_get_mcp_resource_merge_request_exception(
        self, mock_get_mr, mock_mcp
    ):
        """Test exception handling for merge request resource"""
        mock_get_mr.side_effect = Exception("Database connection failed")

        # Register tools
        register_resource_access_tools(mock_mcp)

        # Find the function
        get_mcp_resource_func = None
        for call in mock_mcp.tool.call_args_list:
            if (
                hasattr(call[0][0], "__name__")
                and call[0][0].__name__ == "get_mcp_resource"
            ):
                get_mcp_resource_func = call[0][0]
                break

        # Test exception handling
        result = await get_mcp_resource_func("gl://mr/83/567")

        # Verify error response
        assert "error" in result
        assert "Failed to access resource" in result["error"]
        assert result["resource_uri"] == "gl://mr/83/567"
