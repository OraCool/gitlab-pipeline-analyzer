"""
Tests for failed pipeline analysis tool

Copyright (c) 2025 Siarhei Skuratovich
Licensed under the MIT License - see LICENSE file for details
"""

from unittest.mock import AsyncMock, Mock, patch

import pytest

from gitlab_analyzer.mcp.tools.failed_pipeline_analysis import (
    register_failed_pipeline_analysis_tools,
)


class TestFailedPipelineAnalysisTools:
    """Test failed pipeline analysis tools"""

    @pytest.fixture
    def mock_mcp(self):
        """Mock FastMCP server"""
        mcp = Mock()
        mcp.tool = Mock()
        return mcp

    @pytest.fixture
    def mock_analyzer(self):
        """Mock GitLab analyzer"""
        analyzer = Mock()
        # Create proper mock jobs with all needed attributes
        job1 = Mock()
        job1.id = 123
        job1.name = "test-job-1"
        job1.stage = "test"

        job2 = Mock()
        job2.id = 124
        job2.name = "test-job-2"
        job2.stage = "test"

        analyzer.get_failed_pipeline_jobs = AsyncMock(return_value=[job1, job2])
        analyzer.get_job_trace = AsyncMock(
            return_value="""
            Running tests...
            test_example.py::test_function FAILED
            === FAILURES ===
            AssertionError: Test failed
        """
        )
        return analyzer

    @pytest.fixture
    def mock_cache_manager(self):
        """Mock cache manager"""
        manager = Mock()
        manager.store_pipeline_info_async = AsyncMock()
        manager.store_failed_jobs_basic = AsyncMock()
        manager.store_error_trace_segments = AsyncMock()
        manager.store_job_file_errors = AsyncMock()
        return manager

    @pytest.fixture
    def mock_pipeline_info(self):
        """Mock comprehensive pipeline info"""
        return {
            "id": 456,
            "status": "failed",
            "source_branch": "feature/test",
            "target_branch": "main",
            "sha": "abc123def456",
            "created_at": "2025-01-01T10:00:00Z",
            "updated_at": "2025-01-01T10:30:00Z",
        }

    def test_register_failed_pipeline_analysis_tools(self, mock_mcp):
        """Test failed pipeline analysis tools registration"""
        register_failed_pipeline_analysis_tools(mock_mcp)

        # Verify 1 tool was registered
        assert mock_mcp.tool.call_count == 1

        # Check that tool was decorated (registered)
        assert mock_mcp.tool.called

    @patch(
        "gitlab_analyzer.mcp.tools.failed_pipeline_analysis.get_comprehensive_pipeline_info"
    )
    @patch("gitlab_analyzer.mcp.tools.failed_pipeline_analysis.get_cache_manager")
    @patch("gitlab_analyzer.mcp.tools.failed_pipeline_analysis.get_gitlab_analyzer")
    @patch("gitlab_analyzer.mcp.tools.failed_pipeline_analysis.get_mcp_info")
    async def test_failed_pipeline_analysis_basic(
        self,
        mock_get_mcp_info,
        mock_get_analyzer,
        mock_get_cache_manager,
        mock_get_pipeline_info,
        mock_cache_manager,
        mock_analyzer,
        mock_pipeline_info,
        mock_mcp,
    ):
        """Test basic failed pipeline analysis functionality"""
        # Setup mocks
        mock_get_analyzer.return_value = mock_analyzer
        mock_get_cache_manager.return_value = mock_cache_manager
        mock_get_pipeline_info.return_value = mock_pipeline_info
        mock_get_mcp_info.return_value = {
            "tool": "failed_pipeline_analysis",
            "timestamp": "2025-01-01",
        }

        # Register tools
        register_failed_pipeline_analysis_tools(mock_mcp)

        # Find the failed_pipeline_analysis function
        analysis_func = None
        for call in mock_mcp.tool.call_args_list:
            if (
                hasattr(call[0][0], "__name__")
                and call[0][0].__name__ == "failed_pipeline_analysis"
            ):
                analysis_func = call[0][0]
                break

        assert analysis_func is not None, "failed_pipeline_analysis function not found"

        # Test analysis
        result = await analysis_func(project_id="test-project", pipeline_id=456)

        # Verify basic structure
        assert "content" in result
        assert "mcp_info" in result
        assert isinstance(result["content"], list)
        assert len(result["content"]) > 0

        # Verify first content item has analysis summary
        first_content = result["content"][0]
        assert first_content["type"] == "text"
        assert "456" in first_content["text"]  # Pipeline ID should be mentioned
        assert (
            "failed jobs" in first_content["text"] or "failed" in first_content["text"]
        )

        # Verify resource links are present
        resource_links = [
            item for item in result["content"] if item["type"] == "resource_link"
        ]
        assert len(resource_links) > 0

        # Verify pipeline info was stored
        mock_cache_manager.store_pipeline_info_async.assert_called_once()

        # Verify failed jobs were processed
        mock_analyzer.get_failed_pipeline_jobs.assert_called_once_with(
            project_id="test-project", pipeline_id=456
        )

        # Verify job traces were retrieved
        assert mock_analyzer.get_job_trace.call_count == 2  # For both failed jobs

    @patch(
        "gitlab_analyzer.mcp.tools.failed_pipeline_analysis.get_comprehensive_pipeline_info"
    )
    @patch("gitlab_analyzer.mcp.tools.failed_pipeline_analysis.get_cache_manager")
    @patch("gitlab_analyzer.mcp.tools.failed_pipeline_analysis.get_gitlab_analyzer")
    @patch("gitlab_analyzer.mcp.tools.failed_pipeline_analysis.get_mcp_info")
    async def test_failed_pipeline_analysis_no_store(
        self,
        mock_get_mcp_info,
        mock_get_analyzer,
        mock_get_cache_manager,
        mock_get_pipeline_info,
        mock_cache_manager,
        mock_analyzer,
        mock_pipeline_info,
        mock_mcp,
    ):
        """Test failed pipeline analysis without storing in database"""
        # Setup mocks
        mock_get_analyzer.return_value = mock_analyzer
        mock_get_cache_manager.return_value = mock_cache_manager
        mock_get_pipeline_info.return_value = mock_pipeline_info
        mock_get_mcp_info.return_value = {
            "tool": "failed_pipeline_analysis",
            "timestamp": "2025-01-01",
        }

        # Register tools
        register_failed_pipeline_analysis_tools(mock_mcp)

        # Find the failed_pipeline_analysis function
        analysis_func = None
        for call in mock_mcp.tool.call_args_list:
            if (
                hasattr(call[0][0], "__name__")
                and call[0][0].__name__ == "failed_pipeline_analysis"
            ):
                analysis_func = call[0][0]
                break

        # Test analysis without storing
        result = await analysis_func(
            project_id="test-project", pipeline_id=456, store_in_db=False
        )

        # Verify basic structure
        assert "content" in result
        assert "mcp_info" in result

        # Verify pipeline info was NOT stored
        mock_cache_manager.store_pipeline_info_async.assert_not_called()
        mock_cache_manager.store_failed_jobs_basic.assert_not_called()
        mock_cache_manager.store_error_trace_segments.assert_not_called()
        mock_cache_manager.store_job_file_errors.assert_not_called()

    @patch(
        "gitlab_analyzer.mcp.tools.failed_pipeline_analysis.get_comprehensive_pipeline_info"
    )
    @patch("gitlab_analyzer.mcp.tools.failed_pipeline_analysis.get_cache_manager")
    @patch("gitlab_analyzer.mcp.tools.failed_pipeline_analysis.get_gitlab_analyzer")
    @patch("gitlab_analyzer.mcp.tools.failed_pipeline_analysis.get_mcp_info")
    async def test_failed_pipeline_analysis_with_file_filtering(
        self,
        mock_get_mcp_info,
        mock_get_analyzer,
        mock_get_cache_manager,
        mock_get_pipeline_info,
        mock_cache_manager,
        mock_analyzer,
        mock_pipeline_info,
        mock_mcp,
    ):
        """Test failed pipeline analysis with custom file filtering"""
        # Setup mocks
        mock_get_analyzer.return_value = mock_analyzer
        mock_get_cache_manager.return_value = mock_cache_manager
        mock_get_pipeline_info.return_value = mock_pipeline_info
        mock_get_mcp_info.return_value = {
            "tool": "failed_pipeline_analysis",
            "timestamp": "2025-01-01",
        }

        # Setup job trace with different file types
        mock_analyzer.get_job_trace.return_value = """
            ERROR: test_app.py:42: AssertionError
            ERROR: /usr/local/lib/python3.8/site-packages/pytest.py:100: ImportError
            ERROR: migrations/0001_initial.py:10: DatabaseError
        """

        # Register tools
        register_failed_pipeline_analysis_tools(mock_mcp)

        # Find the failed_pipeline_analysis function
        analysis_func = None
        for call in mock_mcp.tool.call_args_list:
            if (
                hasattr(call[0][0], "__name__")
                and call[0][0].__name__ == "failed_pipeline_analysis"
            ):
                analysis_func = call[0][0]
                break

        # Test analysis with custom exclude patterns
        result = await analysis_func(
            project_id="test-project",
            pipeline_id=456,
            exclude_file_patterns=["migrations/"],
            disable_file_filtering=False,
        )

        # Verify result structure
        assert "content" in result
        assert "mcp_info" in result

    @patch(
        "gitlab_analyzer.mcp.tools.failed_pipeline_analysis.get_comprehensive_pipeline_info"
    )
    @patch("gitlab_analyzer.mcp.tools.failed_pipeline_analysis.get_cache_manager")
    @patch("gitlab_analyzer.mcp.tools.failed_pipeline_analysis.get_gitlab_analyzer")
    @patch("gitlab_analyzer.mcp.tools.failed_pipeline_analysis.get_mcp_info")
    async def test_failed_pipeline_analysis_disabled_filtering(
        self,
        mock_get_mcp_info,
        mock_get_analyzer,
        mock_get_cache_manager,
        mock_get_pipeline_info,
        mock_cache_manager,
        mock_analyzer,
        mock_pipeline_info,
        mock_mcp,
    ):
        """Test failed pipeline analysis with disabled file filtering"""
        # Setup mocks
        mock_get_analyzer.return_value = mock_analyzer
        mock_get_cache_manager.return_value = mock_cache_manager
        mock_get_pipeline_info.return_value = mock_pipeline_info
        mock_get_mcp_info.return_value = {
            "tool": "failed_pipeline_analysis",
            "timestamp": "2025-01-01",
        }

        # Register tools
        register_failed_pipeline_analysis_tools(mock_mcp)

        # Find the failed_pipeline_analysis function
        analysis_func = None
        for call in mock_mcp.tool.call_args_list:
            if (
                hasattr(call[0][0], "__name__")
                and call[0][0].__name__ == "failed_pipeline_analysis"
            ):
                analysis_func = call[0][0]
                break

        # Test analysis with disabled filtering
        result = await analysis_func(
            project_id="test-project", pipeline_id=456, disable_file_filtering=True
        )

        # Verify result structure
        assert "content" in result
        assert "mcp_info" in result

    @patch(
        "gitlab_analyzer.mcp.tools.failed_pipeline_analysis.get_comprehensive_pipeline_info"
    )
    @patch("gitlab_analyzer.mcp.tools.failed_pipeline_analysis.get_cache_manager")
    @patch("gitlab_analyzer.mcp.tools.failed_pipeline_analysis.get_gitlab_analyzer")
    @patch("gitlab_analyzer.mcp.tools.failed_pipeline_analysis.get_mcp_info")
    async def test_failed_pipeline_analysis_error_handling(
        self,
        mock_get_mcp_info,
        mock_get_analyzer,
        mock_get_cache_manager,
        mock_get_pipeline_info,
        mock_mcp,
    ):
        """Test error handling in failed pipeline analysis"""
        # Setup error in the analyzer itself, not in the getter
        mock_analyzer = Mock()
        mock_analyzer.get_failed_pipeline_jobs = AsyncMock(
            side_effect=Exception("GitLab API error")
        )
        mock_get_analyzer.return_value = mock_analyzer
        mock_get_cache_manager.return_value = Mock()
        mock_get_pipeline_info.return_value = {}
        mock_get_mcp_info.return_value = {
            "tool": "failed_pipeline_analysis",
            "error": True,
        }

        # Register tools
        register_failed_pipeline_analysis_tools(mock_mcp)

        # Find the failed_pipeline_analysis function
        analysis_func = None
        for call in mock_mcp.tool.call_args_list:
            if (
                hasattr(call[0][0], "__name__")
                and call[0][0].__name__ == "failed_pipeline_analysis"
            ):
                analysis_func = call[0][0]
                break

        # Test error handling
        result = await analysis_func(project_id="test-project", pipeline_id=456)

        # Verify error response
        assert "content" in result
        assert "mcp_info" in result
        assert len(result["content"]) > 0

        # Check that error message is in the content
        error_content = result["content"][0]
        assert error_content["type"] == "text"
        assert (
            "Failed to analyze pipeline" in error_content["text"]
            or "❌" in error_content["text"]
        )

    @patch(
        "gitlab_analyzer.mcp.tools.failed_pipeline_analysis.get_comprehensive_pipeline_info"
    )
    @patch("gitlab_analyzer.mcp.tools.failed_pipeline_analysis.get_cache_manager")
    @patch("gitlab_analyzer.mcp.tools.failed_pipeline_analysis.get_gitlab_analyzer")
    @patch("gitlab_analyzer.mcp.tools.failed_pipeline_analysis.get_mcp_info")
    async def test_failed_pipeline_analysis_no_failed_jobs(
        self,
        mock_get_mcp_info,
        mock_get_analyzer,
        mock_get_cache_manager,
        mock_get_pipeline_info,
        mock_cache_manager,
        mock_analyzer,
        mock_pipeline_info,
        mock_mcp,
    ):
        """Test failed pipeline analysis when no failed jobs exist"""
        # Setup mocks with no failed jobs
        mock_analyzer.get_failed_pipeline_jobs = AsyncMock(return_value=[])
        mock_get_analyzer.return_value = mock_analyzer
        mock_get_cache_manager.return_value = mock_cache_manager
        mock_get_pipeline_info.return_value = mock_pipeline_info
        mock_get_mcp_info.return_value = {
            "tool": "failed_pipeline_analysis",
            "timestamp": "2025-01-01",
        }

        # Register tools
        register_failed_pipeline_analysis_tools(mock_mcp)

        # Find the failed_pipeline_analysis function
        analysis_func = None
        for call in mock_mcp.tool.call_args_list:
            if (
                hasattr(call[0][0], "__name__")
                and call[0][0].__name__ == "failed_pipeline_analysis"
            ):
                analysis_func = call[0][0]
                break

        # Test analysis with no failed jobs
        result = await analysis_func(project_id="test-project", pipeline_id=456)

        # Verify result structure
        assert "content" in result
        assert "mcp_info" in result

        # Check that "0 failed jobs" is mentioned
        first_content = result["content"][0]
        assert "0 failed jobs" in first_content["text"]

        # Verify no job traces were retrieved
        mock_analyzer.get_job_trace.assert_not_called()
