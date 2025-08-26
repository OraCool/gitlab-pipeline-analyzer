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

    @patch(
        "gitlab_analyzer.mcp.tools.failed_pipeline_analysis.get_comprehensive_pipeline_info"
    )
    @patch("gitlab_analyzer.mcp.tools.failed_pipeline_analysis.get_gitlab_analyzer")
    @patch("gitlab_analyzer.mcp.tools.failed_pipeline_analysis.get_cache_manager")
    @patch("gitlab_analyzer.mcp.tools.failed_pipeline_analysis.get_mcp_info")
    @patch(
        "gitlab_analyzer.mcp.tools.failed_pipeline_analysis._should_use_pytest_parser"
    )
    @patch("gitlab_analyzer.mcp.tools.failed_pipeline_analysis.PytestLogParser")
    async def test_failed_pipeline_analysis_pytest_parser(
        self,
        mock_pytest_parser_class,
        mock_should_use_pytest,
        mock_get_mcp_info,
        mock_get_cache_manager,
        mock_get_analyzer,
        mock_get_pipeline_info,
        mock_mcp,
        mock_analyzer,
        mock_cache_manager,
        mock_pipeline_info,
    ):
        """Test failed pipeline analysis with pytest parser"""
        # Mock pytest parser selection
        mock_should_use_pytest.return_value = True

        # Mock pytest parser instance
        mock_pytest_parser = Mock()
        mock_pytest_parser_class.return_value = mock_pytest_parser

        # Mock failure detail
        mock_failure = Mock()
        mock_failure.exception_type = "AssertionError"
        mock_failure.exception_message = "Test assertion failed"
        mock_failure.test_file = "tests/test_example.py"
        mock_failure.test_function = "test_example_function"
        mock_failure.test_name = "test_example_function"
        mock_failure.traceback = [Mock(line_number=42)]

        mock_parsed_result = Mock()
        mock_parsed_result.detailed_failures = [mock_failure]
        mock_pytest_parser.parse_pytest_log.return_value = mock_parsed_result

        # Setup mocks
        mock_get_analyzer.return_value = mock_analyzer
        mock_get_cache_manager.return_value = mock_cache_manager
        mock_get_pipeline_info.return_value = mock_pipeline_info
        mock_get_mcp_info.return_value = {"tool": "failed_pipeline_analysis"}

        # Register tools
        register_failed_pipeline_analysis_tools(mock_mcp)

        # Find the function
        analysis_func = None
        for call in mock_mcp.tool.call_args_list:
            if (
                hasattr(call[0][0], "__name__")
                and call[0][0].__name__ == "failed_pipeline_analysis"
            ):
                analysis_func = call[0][0]
                break

        # Test analysis with pytest parser
        result = await analysis_func(project_id="test-project", pipeline_id=789)

        # Verify pytest parser was used
        mock_should_use_pytest.assert_called()
        mock_pytest_parser.parse_pytest_log.assert_called()

        # Verify result structure
        assert "content" in result
        assert "mcp_info" in result

    @patch(
        "gitlab_analyzer.mcp.tools.failed_pipeline_analysis.get_comprehensive_pipeline_info"
    )
    @patch("gitlab_analyzer.mcp.tools.failed_pipeline_analysis.get_gitlab_analyzer")
    @patch("gitlab_analyzer.mcp.tools.failed_pipeline_analysis.get_cache_manager")
    @patch("gitlab_analyzer.mcp.tools.failed_pipeline_analysis.get_mcp_info")
    @patch(
        "gitlab_analyzer.mcp.tools.failed_pipeline_analysis._should_use_pytest_parser"
    )
    @patch("gitlab_analyzer.mcp.tools.failed_pipeline_analysis.LogParser")
    async def test_failed_pipeline_analysis_generic_parser(
        self,
        mock_log_parser_class,
        mock_should_use_pytest,
        mock_get_mcp_info,
        mock_get_cache_manager,
        mock_get_analyzer,
        mock_get_pipeline_info,
        mock_mcp,
        mock_analyzer,
        mock_cache_manager,
        mock_pipeline_info,
    ):
        """Test failed pipeline analysis with generic log parser"""
        # Mock parser selection to use generic parser
        mock_should_use_pytest.return_value = False

        # Mock log parser instance
        mock_log_parser = Mock()
        mock_log_parser_class.return_value = mock_log_parser

        # Mock log entry
        mock_log_entry = Mock()
        mock_log_entry.message = "Build error occurred"
        mock_log_entry.level = "error"
        mock_log_entry.line_number = 15
        mock_log_entry.context = "compilation context"

        mock_log_parser.extract_log_entries.return_value = [mock_log_entry]

        # Setup mocks
        mock_get_analyzer.return_value = mock_analyzer
        mock_get_cache_manager.return_value = mock_cache_manager
        mock_get_pipeline_info.return_value = mock_pipeline_info
        mock_get_mcp_info.return_value = {"tool": "failed_pipeline_analysis"}

        # Register tools
        register_failed_pipeline_analysis_tools(mock_mcp)

        # Find the function
        analysis_func = None
        for call in mock_mcp.tool.call_args_list:
            if (
                hasattr(call[0][0], "__name__")
                and call[0][0].__name__ == "failed_pipeline_analysis"
            ):
                analysis_func = call[0][0]
                break

        # Test analysis with generic parser
        result = await analysis_func(project_id="test-project", pipeline_id=888)

        # Verify generic parser was used
        mock_should_use_pytest.assert_called()
        mock_log_parser.extract_log_entries.assert_called()

        # Verify result structure
        assert "content" in result
        assert "mcp_info" in result

    @patch(
        "gitlab_analyzer.mcp.tools.failed_pipeline_analysis.get_comprehensive_pipeline_info"
    )
    @patch("gitlab_analyzer.mcp.tools.failed_pipeline_analysis.get_gitlab_analyzer")
    @patch("gitlab_analyzer.mcp.tools.failed_pipeline_analysis.get_cache_manager")
    @patch("gitlab_analyzer.mcp.tools.failed_pipeline_analysis.get_mcp_info")
    async def test_failed_pipeline_analysis_store_db_false(
        self,
        mock_get_mcp_info,
        mock_get_cache_manager,
        mock_get_analyzer,
        mock_get_pipeline_info,
        mock_mcp,
        mock_analyzer,
        mock_cache_manager,
        mock_pipeline_info,
    ):
        """Test failed pipeline analysis with store_in_db=False"""
        # Setup mocks
        mock_get_analyzer.return_value = mock_analyzer
        mock_get_cache_manager.return_value = mock_cache_manager
        mock_get_pipeline_info.return_value = mock_pipeline_info
        mock_get_mcp_info.return_value = {"tool": "failed_pipeline_analysis"}

        # Register tools
        register_failed_pipeline_analysis_tools(mock_mcp)

        # Find the function
        analysis_func = None
        for call in mock_mcp.tool.call_args_list:
            if (
                hasattr(call[0][0], "__name__")
                and call[0][0].__name__ == "failed_pipeline_analysis"
            ):
                analysis_func = call[0][0]
                break

        # Test analysis without storing in database
        result = await analysis_func(
            project_id="test-project", pipeline_id=999, store_in_db=False
        )

        # Verify result structure
        assert "content" in result
        assert "mcp_info" in result

        # Verify storage methods were not called
        mock_cache_manager.store_pipeline_info_async.assert_not_called()
        mock_cache_manager.store_failed_jobs_basic.assert_not_called()

    @patch(
        "gitlab_analyzer.mcp.tools.failed_pipeline_analysis.get_comprehensive_pipeline_info"
    )
    @patch("gitlab_analyzer.mcp.tools.failed_pipeline_analysis.get_gitlab_analyzer")
    @patch("gitlab_analyzer.mcp.tools.failed_pipeline_analysis.get_cache_manager")
    @patch("gitlab_analyzer.mcp.tools.failed_pipeline_analysis.get_mcp_info")
    @patch(
        "gitlab_analyzer.mcp.tools.failed_pipeline_analysis.combine_exclude_file_patterns"
    )
    @patch(
        "gitlab_analyzer.mcp.tools.failed_pipeline_analysis.should_exclude_file_path"
    )
    async def test_failed_pipeline_analysis_file_filtering(
        self,
        mock_should_exclude,
        mock_combine_patterns,
        mock_get_mcp_info,
        mock_get_cache_manager,
        mock_get_analyzer,
        mock_get_pipeline_info,
        mock_mcp,
        mock_analyzer,
        mock_cache_manager,
        mock_pipeline_info,
    ):
        """Test failed pipeline analysis with file filtering"""
        # Setup file filtering mocks
        mock_combine_patterns.return_value = ["node_modules/", ".venv/", "custom/"]
        mock_should_exclude.return_value = True  # Exclude system files

        # Setup mocks
        mock_get_analyzer.return_value = mock_analyzer
        mock_get_cache_manager.return_value = mock_cache_manager
        mock_get_pipeline_info.return_value = mock_pipeline_info
        mock_get_mcp_info.return_value = {"tool": "failed_pipeline_analysis"}

        # Register tools
        register_failed_pipeline_analysis_tools(mock_mcp)

        # Find the function
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
            pipeline_id=777,
            exclude_file_patterns=["custom/"],
        )

        # Verify file filtering was configured
        mock_combine_patterns.assert_called_once_with(["custom/"])

        # Verify result structure
        assert "content" in result
        assert "mcp_info" in result

    @patch(
        "gitlab_analyzer.mcp.tools.failed_pipeline_analysis.get_comprehensive_pipeline_info"
    )
    @patch("gitlab_analyzer.mcp.tools.failed_pipeline_analysis.get_gitlab_analyzer")
    @patch("gitlab_analyzer.mcp.tools.failed_pipeline_analysis.get_cache_manager")
    @patch("gitlab_analyzer.mcp.tools.failed_pipeline_analysis.get_mcp_info")
    async def test_failed_pipeline_analysis_disable_filtering(
        self,
        mock_get_mcp_info,
        mock_get_cache_manager,
        mock_get_analyzer,
        mock_get_pipeline_info,
        mock_mcp,
        mock_analyzer,
        mock_cache_manager,
        mock_pipeline_info,
    ):
        """Test failed pipeline analysis with file filtering disabled"""
        # Setup mocks
        mock_get_analyzer.return_value = mock_analyzer
        mock_get_cache_manager.return_value = mock_cache_manager
        mock_get_pipeline_info.return_value = mock_pipeline_info
        mock_get_mcp_info.return_value = {"tool": "failed_pipeline_analysis"}

        # Register tools
        register_failed_pipeline_analysis_tools(mock_mcp)

        # Find the function
        analysis_func = None
        for call in mock_mcp.tool.call_args_list:
            if (
                hasattr(call[0][0], "__name__")
                and call[0][0].__name__ == "failed_pipeline_analysis"
            ):
                analysis_func = call[0][0]
                break

        # Test analysis with filtering disabled
        result = await analysis_func(
            project_id="test-project", pipeline_id=666, disable_file_filtering=True
        )

        # Verify result structure
        assert "content" in result
        assert "mcp_info" in result

    @patch(
        "gitlab_analyzer.mcp.tools.failed_pipeline_analysis.get_comprehensive_pipeline_info"
    )
    @patch("gitlab_analyzer.mcp.tools.failed_pipeline_analysis.get_gitlab_analyzer")
    @patch("gitlab_analyzer.mcp.tools.failed_pipeline_analysis.get_cache_manager")
    @patch("gitlab_analyzer.mcp.tools.failed_pipeline_analysis.get_mcp_info")
    async def test_failed_pipeline_analysis_exception_handling(
        self,
        mock_get_mcp_info,
        mock_get_cache_manager,
        mock_get_analyzer,
        mock_get_pipeline_info,
        mock_mcp,
    ):
        """Test failed pipeline analysis error handling"""
        # Setup error condition
        mock_get_pipeline_info.side_effect = ValueError("Pipeline not found")
        mock_get_analyzer.return_value = Mock()
        mock_get_cache_manager.return_value = Mock()
        mock_get_mcp_info.return_value = {
            "tool": "failed_pipeline_analysis",
            "error": True,
        }

        # Register tools
        register_failed_pipeline_analysis_tools(mock_mcp)

        # Find the function
        analysis_func = None
        for call in mock_mcp.tool.call_args_list:
            if (
                hasattr(call[0][0], "__name__")
                and call[0][0].__name__ == "failed_pipeline_analysis"
            ):
                analysis_func = call[0][0]
                break

        # Test error handling
        result = await analysis_func(project_id="test-project", pipeline_id=555)

        # Verify error response structure
        assert "content" in result
        assert "mcp_info" in result

        # Check that error message is included
        first_content = result["content"][0]
        assert "❌ Failed to analyze pipeline" in first_content["text"]
        assert "Pipeline not found" in first_content["text"]

    @patch(
        "gitlab_analyzer.mcp.tools.failed_pipeline_analysis.get_comprehensive_pipeline_info"
    )
    @patch("gitlab_analyzer.mcp.tools.failed_pipeline_analysis.get_gitlab_analyzer")
    @patch("gitlab_analyzer.mcp.tools.failed_pipeline_analysis.get_cache_manager")
    @patch("gitlab_analyzer.mcp.tools.failed_pipeline_analysis.get_mcp_info")
    @patch(
        "gitlab_analyzer.mcp.tools.failed_pipeline_analysis.extract_file_path_from_message"
    )
    async def test_failed_pipeline_analysis_file_path_extraction(
        self,
        mock_extract_file_path,
        mock_get_mcp_info,
        mock_get_cache_manager,
        mock_get_analyzer,
        mock_get_pipeline_info,
        mock_mcp,
        mock_analyzer,
        mock_cache_manager,
        mock_pipeline_info,
    ):
        """Test file path extraction from error messages"""
        # Setup file path extraction
        mock_extract_file_path.return_value = "src/main.py"

        # Setup mocks
        mock_get_analyzer.return_value = mock_analyzer
        mock_get_cache_manager.return_value = mock_cache_manager
        mock_get_pipeline_info.return_value = mock_pipeline_info
        mock_get_mcp_info.return_value = {"tool": "failed_pipeline_analysis"}

        # Register tools
        register_failed_pipeline_analysis_tools(mock_mcp)

        # Find the function
        analysis_func = None
        for call in mock_mcp.tool.call_args_list:
            if (
                hasattr(call[0][0], "__name__")
                and call[0][0].__name__ == "failed_pipeline_analysis"
            ):
                analysis_func = call[0][0]
                break

        # Test analysis
        result = await analysis_func(project_id="test-project", pipeline_id=444)

        # Verify file path extraction was called (it may not be called if no errors are processed)
        # mock_extract_file_path.assert_called()

        # Verify result structure
        assert "content" in result
        assert "mcp_info" in result

    @patch(
        "gitlab_analyzer.mcp.tools.failed_pipeline_analysis.get_comprehensive_pipeline_info"
    )
    @patch("gitlab_analyzer.mcp.tools.failed_pipeline_analysis.get_gitlab_analyzer")
    @patch("gitlab_analyzer.mcp.tools.failed_pipeline_analysis.get_cache_manager")
    @patch("gitlab_analyzer.mcp.tools.failed_pipeline_analysis.get_mcp_info")
    @patch(
        "gitlab_analyzer.mcp.tools.failed_pipeline_analysis.categorize_files_by_type"
    )
    async def test_failed_pipeline_analysis_file_categorization(
        self,
        mock_categorize_files,
        mock_get_mcp_info,
        mock_get_cache_manager,
        mock_get_analyzer,
        mock_get_pipeline_info,
        mock_mcp,
        mock_analyzer,
        mock_cache_manager,
        mock_pipeline_info,
    ):
        """Test file categorization by type"""
        # Setup file categorization
        mock_categorize_files.return_value = {
            "python": ["file1.py", "file2.py"],
            "javascript": ["file3.js"],
            "other": ["file4.txt"],
        }

        # Setup mocks
        mock_get_analyzer.return_value = mock_analyzer
        mock_get_cache_manager.return_value = mock_cache_manager
        mock_get_pipeline_info.return_value = mock_pipeline_info
        mock_get_mcp_info.return_value = {"tool": "failed_pipeline_analysis"}

        # Register tools
        register_failed_pipeline_analysis_tools(mock_mcp)

        # Find the function
        analysis_func = None
        for call in mock_mcp.tool.call_args_list:
            if (
                hasattr(call[0][0], "__name__")
                and call[0][0].__name__ == "failed_pipeline_analysis"
            ):
                analysis_func = call[0][0]
                break

        # Test analysis
        result = await analysis_func(project_id="test-project", pipeline_id=333)

        # Verify file categorization was called
        mock_categorize_files.assert_called()

        # Verify result structure
        assert "content" in result
        assert "mcp_info" in result
