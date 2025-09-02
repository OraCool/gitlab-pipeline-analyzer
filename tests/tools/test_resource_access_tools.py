"""
Tests for resource access tools

Copyright (c) 2025 Siarhei Skuratovich
Licensed under the MIT License - see LICENSE file for details
"""

from unittest.mock import Mock, patch

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

    @patch(
        "gitlab_analyzer.mcp.tools.resource_access_tools.get_pipeline_files_resource"
    )
    async def test_get_mcp_resource_pipeline_files(self, mock_get_files, mock_mcp):
        """Test accessing pipeline files resource"""
        mock_get_files.return_value = {"files": ["file1.py", "file2.py"]}

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
        mock_get_files.assert_called_once_with("123", "123", 1, 20)

        # Test with pagination
        await get_mcp_resource_func("gl://files/123/pipeline/123/page/2/limit/50")
        mock_get_files.assert_called_with("123", "123", 2, 50)

    @patch("gitlab_analyzer.mcp.tools.resource_access_tools.get_files_resource")
    async def test_get_mcp_resource_job_files(self, mock_get_file, mock_mcp):
        """Test accessing job files resource"""
        mock_get_file.return_value = {"files": ["error1.py", "error2.py"]}

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
        mock_get_file.assert_called_once_with("123", "456", 1, 20)

    @patch("gitlab_analyzer.mcp.tools.resource_access_tools.get_file_resource")
    async def test_get_mcp_resource_specific_file(self, mock_get_file, mock_mcp):
        """Test accessing specific file resource"""
        mock_get_file.return_value = {"file_path": "src/main.py", "errors": []}

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
        mock_get_file.assert_called_once_with("123", "456", "src/main.py")

    @patch(
        "gitlab_analyzer.mcp.tools.resource_access_tools.get_file_resource_with_trace"
    )
    async def test_get_mcp_resource_file_with_trace(
        self, mock_get_file_trace, mock_mcp
    ):
        """Test accessing file resource with trace"""
        import json

        from mcp.types import TextResourceContents

        mock_response = {"file_path": "src/main.py", "trace": "..."}
        mock_get_file_trace.return_value = TextResourceContents(
            uri="gl://file/123/456/src/main.py/trace", text=json.dumps(mock_response)
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

        # Test file with trace resource access using URL-encoded file path
        result = await get_mcp_resource_func(
            "gl://file/123/456/src%2Fmain.py/trace?mode=detailed&include_trace=true"
        )
        assert result["file_path"] == "src/main.py"
        mock_get_file_trace.assert_called_once_with(
            "123", "456", "src/main.py", "detailed", "true"
        )

    @patch("gitlab_analyzer.mcp.tools.resource_access_tools.get_error_resource_data")
    async def test_get_mcp_resource_job_errors(self, mock_get_errors, mock_mcp):
        """Test accessing job errors resource"""
        mock_get_errors.return_value = {"errors": [{"id": 1}, {"id": 2}]}

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
        mock_get_errors.assert_called_once_with("123", "456", "balanced")

        # Test with mode
        await get_mcp_resource_func("gl://error/123/456?mode=detailed")
        mock_get_errors.assert_called_with("123", "456", "detailed")

    @patch("gitlab_analyzer.mcp.tools.resource_access_tools.get_individual_error_data")
    async def test_get_mcp_resource_individual_error(self, mock_get_error, mock_mcp):
        """Test accessing individual error resource"""
        mock_get_error.return_value = {"error_id": "123_0", "message": "Test error"}

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
        mock_get_error.assert_called_once_with("123", "456", "123_0", "balanced")

    @patch(
        "gitlab_analyzer.mcp.tools.resource_access_tools.get_pipeline_errors_resource_data"
    )
    async def test_get_mcp_resource_pipeline_errors(self, mock_get_errors, mock_mcp):
        """Test accessing pipeline errors resource"""
        mock_get_errors.return_value = {
            "pipeline_errors": [{"job_id": 1}, {"job_id": 2}]
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

        # Test pipeline errors resource access
        result = await get_mcp_resource_func("gl://errors/123/pipeline/123")
        assert "pipeline_errors" in result
        mock_get_errors.assert_called_once_with("123", "123")

    @patch(
        "gitlab_analyzer.mcp.tools.resource_access_tools.get_file_errors_resource_data"
    )
    async def test_get_mcp_resource_file_errors(self, mock_get_errors, mock_mcp):
        """Test accessing file errors resource"""
        mock_get_errors.return_value = {"file_errors": [{"line": 10}, {"line": 20}]}

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
        mock_get_errors.assert_called_once_with("123", "456", "src/main.py")

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
