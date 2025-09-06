"""
Tests for job analysis tools

Copyright (c) 2025 Siarhei Skuratovich
Licensed under the MIT License - see LICENSE file for details
"""

from unittest.mock import AsyncMock, Mock, patch

import pytest

from gitlab_analyzer.mcp.tools.job_analysis_tools import register_job_analysis_tools


class TestJobAnalysisTools:
    """Test job analysis tools"""

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
        analyzer.get_job_info = AsyncMock(
            return_value={
                "id": 1001,
                "name": "test-job",
                "stage": "test",
                "status": "failed",
                "created_at": "2025-01-01T00:00:00Z",
                "started_at": "2025-01-01T00:01:00Z",
                "finished_at": "2025-01-01T00:05:00Z",
                "failure_reason": "script_failure",
                "web_url": "https://gitlab.example.com/test-project/-/jobs/1001",
                "pipeline": {"id": 12345, "sha": "abc123"},
                "ref": "main",
                "duration": 240,
            }
        )
        analyzer.get_job_trace = AsyncMock(
            return_value="""
            Running tests...
            test_example.py::test_function FAILED
            === FAILURES ===
            AssertionError: Test failed
        """
        )
        analyzer.get_pipeline = AsyncMock(
            return_value={
                "id": 12345,
                "status": "failed",
                "ref": "main",
                "sha": "abc123",
                "created_at": "2025-01-01T00:00:00Z",
                "updated_at": "2025-01-01T00:05:00Z",
                "web_url": "https://gitlab.example.com/test-project/-/pipelines/12345",
                "source_branch": "main",
                "target_branch": "main",
            }
        )
        return analyzer

    @pytest.fixture
    def mock_cache_manager(self):
        """Mock cache manager"""
        cache_manager = Mock()
        cache_manager.get_job_info_async = AsyncMock(return_value=None)
        cache_manager.get_job_errors = Mock(return_value=[])
        cache_manager.store_pipeline_info_async = AsyncMock()
        return cache_manager

    @pytest.fixture
    def mock_analysis_result(self):
        """Mock analysis result"""
        return {
            "total_errors": 1,
            "files_with_errors": 1,
            "error_statistics": {
                "by_type": {"assertion_error": 1},
                "by_file": {"test_example.py": 1},
            },
        }

    def test_register_job_analysis_tools(self, mock_mcp):
        """Test that job analysis tools are registered"""
        register_job_analysis_tools(mock_mcp)

        # Should have registered 2 tools (analyze_job and analyze_job_with_pipeline_context)
        assert mock_mcp.tool.call_count == 2

    @pytest.mark.asyncio
    async def test_analyze_job_success(
        self, mock_mcp, mock_analyzer, mock_cache_manager, mock_analysis_result
    ):
        """Test successful job analysis"""
        # Register tools to get access to the actual functions
        register_job_analysis_tools(mock_mcp)

        # Get the analyze_job function from the registration calls
        analyze_job_call = mock_mcp.tool.call_args_list[0]
        analyze_job_func = analyze_job_call[0][0]  # First positional argument

        with (
            patch(
                "gitlab_analyzer.mcp.tools.job_analysis_tools.get_gitlab_analyzer",
                return_value=mock_analyzer,
            ),
            patch(
                "gitlab_analyzer.mcp.tools.job_analysis_tools.get_cache_manager",
                return_value=mock_cache_manager,
            ),
            patch(
                "gitlab_analyzer.mcp.tools.job_analysis_tools.analyze_job_trace",
                new_callable=AsyncMock,
                return_value=mock_analysis_result,
            ),
            patch(
                "gitlab_analyzer.mcp.tools.job_analysis_tools.get_mcp_info",
                return_value={"version": "test"},
            ),
        ):
            result = await analyze_job_func(
                project_id=123,  # Use integer project ID
                job_id=1001,
                store_in_db=True,
                exclude_file_patterns=None,
                disable_file_filtering=False,
            )

            # Verify the result structure
            assert "job_info" in result
            assert "analysis_summary" in result
            assert "error_statistics" in result
            assert "resource_links" in result
            assert "mcp_info" in result
            assert "debug_timing" in result

            # Verify job info
            job_info = result["job_info"]
            assert job_info["job_id"] == 1001
            assert job_info["name"] == "test-job"
            assert job_info["status"] == "failed"
            assert job_info["pipeline_id"] == 12345

            # Verify analysis summary
            analysis_summary = result["analysis_summary"]
            assert analysis_summary["total_errors"] == 1
            assert analysis_summary["files_with_errors"] == 1
            assert analysis_summary["analysis_type"] == "individual_job"
            assert analysis_summary["filtering_enabled"] is True

            # Verify resource links
            resource_links = result["resource_links"]
            assert len(resource_links) >= 2
            assert any("gl://job/" in link["resourceUri"] for link in resource_links)
            assert any("gl://errors/" in link["resourceUri"] for link in resource_links)

            # Verify analyzer calls
            mock_analyzer.get_job_info.assert_called_once_with(123, 1001)
            mock_analyzer.get_job_trace.assert_called_once_with(123, 1001)

    @pytest.mark.asyncio
    async def test_analyze_job_cached_data(
        self, mock_mcp, mock_analyzer, mock_cache_manager, mock_analysis_result
    ):
        """Test job analysis with cached data"""
        # Setup cached job info
        cached_job_info = {
            "job_id": 1001,
            "name": "cached-job",
            "pipeline_id": 12345,
        }
        mock_cache_manager.get_job_info_async = AsyncMock(return_value=cached_job_info)
        mock_cache_manager.get_job_errors = Mock(
            return_value=[{"file_path": "test.py", "error": "Test error"}]
        )

        register_job_analysis_tools(mock_mcp)
        analyze_job_func = mock_mcp.tool.call_args_list[0][0][0]

        with (
            patch(
                "gitlab_analyzer.mcp.tools.job_analysis_tools.get_gitlab_analyzer",
                return_value=mock_analyzer,
            ),
            patch(
                "gitlab_analyzer.mcp.tools.job_analysis_tools.get_cache_manager",
                return_value=mock_cache_manager,
            ),
            patch(
                "gitlab_analyzer.mcp.tools.job_analysis_tools.get_mcp_info",
                return_value={"version": "test"},
            ),
        ):
            result = await analyze_job_func(
                project_id=123,
                job_id=1001,
                store_in_db=False,  # This triggers cached data path
            )

            # Should return cached data without calling GitLab API
            assert "job_info" in result
            assert result["job_info"] == cached_job_info
            assert result["analysis_summary"]["source"] == "cached_data"

            # Should not call GitLab API
            mock_analyzer.get_job_info.assert_not_called()
            mock_analyzer.get_job_trace.assert_not_called()

    @pytest.mark.asyncio
    async def test_analyze_job_not_found(
        self, mock_mcp, mock_analyzer, mock_cache_manager
    ):
        """Test job analysis when job not found"""
        mock_analyzer.get_job_info = AsyncMock(return_value=None)

        register_job_analysis_tools(mock_mcp)
        analyze_job_func = mock_mcp.tool.call_args_list[0][0][0]

        with (
            patch(
                "gitlab_analyzer.mcp.tools.job_analysis_tools.get_gitlab_analyzer",
                return_value=mock_analyzer,
            ),
            patch(
                "gitlab_analyzer.mcp.tools.job_analysis_tools.get_cache_manager",
                return_value=mock_cache_manager,
            ),
            patch(
                "gitlab_analyzer.mcp.tools.job_analysis_tools.get_mcp_info",
                return_value={"version": "test"},
            ),
        ):
            result = await analyze_job_func(
                project_id="test-project",
                job_id=9999,
            )

            assert "error" in result
            assert result["error"] == "job_not_found"
            assert result["job_id"] == 9999
            assert "debug_timing" in result

    @pytest.mark.asyncio
    async def test_analyze_job_with_pipeline_context_success(
        self, mock_mcp, mock_analyzer, mock_cache_manager, mock_analysis_result
    ):
        """Test successful job analysis with pipeline context"""
        register_job_analysis_tools(mock_mcp)

        # Get the analyze_job_with_pipeline_context function
        analyze_job_with_pipeline_context_func = mock_mcp.tool.call_args_list[1][0][0]

        with (
            patch(
                "gitlab_analyzer.mcp.tools.job_analysis_tools.get_gitlab_analyzer",
                return_value=mock_analyzer,
            ),
            patch(
                "gitlab_analyzer.mcp.tools.job_analysis_tools.get_cache_manager",
                return_value=mock_cache_manager,
            ),
            patch(
                "gitlab_analyzer.mcp.tools.job_analysis_tools.analyze_job_trace",
                new_callable=AsyncMock,
                return_value=mock_analysis_result,
            ),
            patch(
                "gitlab_analyzer.mcp.tools.job_analysis_tools.get_mcp_info",
                return_value={"version": "test"},
            ),
        ):
            result = await analyze_job_with_pipeline_context_func(
                project_id="test-project",
                pipeline_id=12345,
                job_id=1001,
                store_in_db=True,
            )

            # Should have pipeline context in result
            assert "pipeline_context" in result
            pipeline_context = result["pipeline_context"]
            assert pipeline_context["pipeline_id"] == 12345
            assert pipeline_context["status"] == "failed"
            assert pipeline_context["ref"] == "main"

            # Should have updated job info with pipeline ID
            assert result["job_info"]["pipeline_id"] == 12345

            # Verify both pipeline and job API calls
            mock_analyzer.get_pipeline.assert_called_once_with("test-project", 12345)
            mock_analyzer.get_job_info.assert_called_once_with("test-project", 1001)

            # Verify pipeline info storage
            mock_cache_manager.store_pipeline_info_async.assert_called_once()

    @pytest.mark.asyncio
    async def test_analyze_job_with_filtering_options(
        self, mock_mcp, mock_analyzer, mock_cache_manager, mock_analysis_result
    ):
        """Test job analysis with filtering options"""
        register_job_analysis_tools(mock_mcp)
        analyze_job_func = mock_mcp.tool.call_args_list[0][0][0]

        with (
            patch(
                "gitlab_analyzer.mcp.tools.job_analysis_tools.get_gitlab_analyzer",
                return_value=mock_analyzer,
            ),
            patch(
                "gitlab_analyzer.mcp.tools.job_analysis_tools.get_cache_manager",
                return_value=mock_cache_manager,
            ),
            patch(
                "gitlab_analyzer.mcp.tools.job_analysis_tools.analyze_job_trace",
                new_callable=AsyncMock,
                return_value=mock_analysis_result,
            ) as mock_analyze_trace,
            patch(
                "gitlab_analyzer.mcp.tools.job_analysis_tools.get_mcp_info",
                return_value={"version": "test"},
            ),
        ):
            result = await analyze_job_func(
                project_id="test-project",
                job_id=1001,
                exclude_file_patterns=["node_modules/", "vendor/"],
                disable_file_filtering=True,
            )

            # Verify filtering options were passed to analyze_job_trace
            mock_analyze_trace.assert_called_once()
            call_args = mock_analyze_trace.call_args
            assert call_args[1]["exclude_file_patterns"] == ["node_modules/", "vendor/"]
            assert call_args[1]["disable_file_filtering"] is True

            # Verify analysis summary reflects filtering settings
            analysis_summary = result["analysis_summary"]
            assert analysis_summary["filtering_enabled"] is False
            assert analysis_summary["excluded_patterns"] == ["node_modules/", "vendor/"]

    @pytest.mark.asyncio
    async def test_analyze_job_exception_handling(
        self, mock_mcp, mock_analyzer, mock_cache_manager
    ):
        """Test job analysis exception handling"""
        mock_analyzer.get_job_info = AsyncMock(side_effect=Exception("API Error"))

        register_job_analysis_tools(mock_mcp)
        analyze_job_func = mock_mcp.tool.call_args_list[0][0][0]

        with (
            patch(
                "gitlab_analyzer.mcp.tools.job_analysis_tools.get_gitlab_analyzer",
                return_value=mock_analyzer,
            ),
            patch(
                "gitlab_analyzer.mcp.tools.job_analysis_tools.get_cache_manager",
                return_value=mock_cache_manager,
            ),
            patch(
                "gitlab_analyzer.mcp.tools.job_analysis_tools.get_mcp_info",
                return_value={"version": "test"},
            ),
        ):
            result = await analyze_job_func(
                project_id="test-project",
                job_id=1001,
            )

            assert "error" in result
            assert result["error"] == "analysis_failed"
            assert "API Error" in result["message"]
            assert "debug_timing" in result

    @pytest.mark.asyncio
    async def test_analyze_job_empty_trace(
        self, mock_mcp, mock_analyzer, mock_cache_manager, mock_analysis_result
    ):
        """Test job analysis with empty trace"""
        mock_analyzer.get_job_trace = AsyncMock(return_value="")

        register_job_analysis_tools(mock_mcp)
        analyze_job_func = mock_mcp.tool.call_args_list[0][0][0]

        with (
            patch(
                "gitlab_analyzer.mcp.tools.job_analysis_tools.get_gitlab_analyzer",
                return_value=mock_analyzer,
            ),
            patch(
                "gitlab_analyzer.mcp.tools.job_analysis_tools.get_cache_manager",
                return_value=mock_cache_manager,
            ),
            patch(
                "gitlab_analyzer.mcp.tools.job_analysis_tools.analyze_job_trace",
                new_callable=AsyncMock,
                return_value=mock_analysis_result,
            ) as mock_analyze_trace,
            patch(
                "gitlab_analyzer.mcp.tools.job_analysis_tools.get_mcp_info",
                return_value={"version": "test"},
            ),
        ):
            result = await analyze_job_func(
                project_id="test-project",
                job_id=1001,
            )

            # Should handle empty trace gracefully
            assert "analysis_summary" in result
            assert result["analysis_summary"]["trace_length"] == 0

            # Should still call analyze_job_trace with empty string
            mock_analyze_trace.assert_called_once()
            call_args = mock_analyze_trace.call_args
            assert call_args[1]["trace_content"] == ""

    @pytest.mark.asyncio
    async def test_resource_links_generation(
        self, mock_mcp, mock_analyzer, mock_cache_manager
    ):
        """Test that resource links are generated correctly"""
        mock_analysis_result = {
            "total_errors": 2,
            "files_with_errors": 2,
            "error_statistics": {},
        }

        register_job_analysis_tools(mock_mcp)
        analyze_job_func = mock_mcp.tool.call_args_list[0][0][0]

        with (
            patch(
                "gitlab_analyzer.mcp.tools.job_analysis_tools.get_gitlab_analyzer",
                return_value=mock_analyzer,
            ),
            patch(
                "gitlab_analyzer.mcp.tools.job_analysis_tools.get_cache_manager",
                return_value=mock_cache_manager,
            ),
            patch(
                "gitlab_analyzer.mcp.tools.job_analysis_tools.analyze_job_trace",
                new_callable=AsyncMock,
                return_value=mock_analysis_result,
            ),
            patch(
                "gitlab_analyzer.mcp.tools.job_analysis_tools.get_mcp_info",
                return_value={"version": "test"},
            ),
        ):
            result = await analyze_job_func(
                project_id="test-project",
                job_id=1001,
            )

            resource_links = result["resource_links"]

            # Should have at least job, errors, files, and pipeline links
            assert len(resource_links) >= 4

            # Check specific resource URIs
            resource_uris = [link["resourceUri"] for link in resource_links]
            assert any(
                "gl://job/test-project/12345/1001" in uri for uri in resource_uris
            )
            assert any("gl://errors/test-project/1001" in uri for uri in resource_uris)
            assert any("gl://files/test-project/1001" in uri for uri in resource_uris)
            assert any(
                "gl://pipeline/test-project/12345" in uri for uri in resource_uris
            )
