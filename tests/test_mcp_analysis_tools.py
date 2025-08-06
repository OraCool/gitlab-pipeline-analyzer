"""
Unit tests for MCP analysis tools.

Copyright (c) 2025 Siarhei Skuratovich
Licensed under the MIT License - see LICENSE file for details
"""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from fastmcp import FastMCP

from gitlab_analyzer.mcp.tools.analysis_tools import register_analysis_tools
from gitlab_analyzer.models.job_info import JobInfo


class TestAnalysisTools:
    """Test MCP analysis tools."""

    @pytest.fixture
    def mcp_server(self):
        """Create FastMCP server with analysis tools."""
        mcp = FastMCP("test")
        register_analysis_tools(mcp)
        return mcp

    @pytest.fixture
    def mock_analyzer(self):
        """Mock GitLab analyzer."""
        analyzer = AsyncMock()
        return analyzer

    @pytest.fixture
    def sample_pipeline(self):
        """Sample pipeline data (dict as returned by API)."""
        return {
            "id": 123,
            "project_id": 456,
            "ref": "main",
            "status": "failed",
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
        }

    @pytest.fixture
    def sample_failed_jobs(self):
        """Sample failed jobs data."""
        return [
            JobInfo(
                id=1001,
                name="test-job-1",
                status="failed",
                stage="test",
                created_at=datetime.now().isoformat(),
                web_url="https://gitlab.com/project/job/1001",
            ),
            JobInfo(
                id=1002,
                name="test-job-2",
                status="failed",
                stage="build",
                created_at=datetime.now().isoformat(),
                web_url="https://gitlab.com/project/job/1002",
            ),
        ]

    @pytest.mark.asyncio
    async def test_analyze_failed_pipeline_success(
        self, mcp_server, mock_analyzer, sample_pipeline, sample_failed_jobs
    ):
        """Test successful pipeline analysis."""
        # Mock trace data with errors and warnings
        mock_trace = """
        ERROR: Test failed with assertion error
        WARNING: Deprecated function used
        INFO: Starting build process
        """

        with patch(
            "gitlab_analyzer.mcp.tools.analysis_tools.get_gitlab_analyzer",
            return_value=mock_analyzer,
        ):
            # Setup mock responses
            mock_analyzer.get_pipeline.return_value = sample_pipeline
            mock_analyzer.get_failed_pipeline_jobs.return_value = sample_failed_jobs
            mock_analyzer.get_job_trace.return_value = mock_trace

            # Mock log parser
            with patch(
                "gitlab_analyzer.mcp.tools.analysis_tools.LogParser.extract_log_entries"
            ) as mock_extract:
                mock_extract.return_value = [
                    MagicMock(
                        level="error",
                        message="Test failed with assertion error",
                        line_number=1,
                        timestamp=None,
                        context="test context",
                    ),
                    MagicMock(
                        level="warning",
                        message="Deprecated function used",
                        line_number=2,
                        timestamp=None,
                        context="warning context",
                    ),
                ]

                # Get the tool function
                tool_func = None
                for tool in list((await mcp_server.get_tools()).values()):
                    if tool.name == "analyze_failed_pipeline":
                        tool_func = tool.fn
                        break

                assert tool_func is not None

                # Execute tool
                result = await tool_func(project_id="test-project", pipeline_id=123)

                # Verify result structure
                assert "project_id" in result
                assert "pipeline_id" in result
                assert "pipeline_status" in result
                assert "failed_jobs_count" in result
                assert "job_analyses" in result
                assert "summary" in result
                assert "analysis_timestamp" in result

                # Verify job analyses
                assert len(result["job_analyses"]) == 2
                for job_analysis in result["job_analyses"]:
                    assert "job_id" in job_analysis
                    assert "job_name" in job_analysis
                    assert "errors" in job_analysis
                    assert "warnings" in job_analysis
                    assert "error_count" in job_analysis
                    assert "warning_count" in job_analysis

                # Verify summary
                summary = result["summary"]
                assert "total_errors" in summary
                assert "total_warnings" in summary
                assert "jobs_with_errors" in summary
                assert "jobs_with_warnings" in summary

    @pytest.mark.asyncio
    async def test_analyze_failed_pipeline_http_error(self, mcp_server, mock_analyzer):
        """Test pipeline analysis with HTTP error."""
        with patch(
            "gitlab_analyzer.mcp.tools.analysis_tools.get_gitlab_analyzer",
            return_value=mock_analyzer,
        ):
            # Setup mock to raise HTTP error
            mock_analyzer.get_pipeline.side_effect = httpx.HTTPError("API Error")

            # Get the tool function
            tool_func = None
            for tool in list((await mcp_server.get_tools()).values()):
                if tool.name == "analyze_failed_pipeline":
                    tool_func = tool.fn
                    break

            assert tool_func is not None

            # Execute tool
            result = await tool_func(project_id="test-project", pipeline_id=123)

            # Verify error handling
            assert "error" in result
            assert "Failed to analyze pipeline" in result["error"]
            assert result["project_id"] == "test-project"
            assert result["pipeline_id"] == 123

    @pytest.mark.asyncio
    async def test_analyze_failed_pipeline_job_error(
        self, mcp_server, mock_analyzer, sample_pipeline, sample_failed_jobs
    ):
        """Test pipeline analysis with individual job errors."""
        with patch(
            "gitlab_analyzer.mcp.tools.analysis_tools.get_gitlab_analyzer",
            return_value=mock_analyzer,
        ):
            # Setup mock responses
            mock_analyzer.get_pipeline.return_value = sample_pipeline
            mock_analyzer.get_failed_pipeline_jobs.return_value = sample_failed_jobs
            mock_analyzer.get_job_trace.side_effect = Exception("Job trace error")

            # Get the tool function
            tool_func = None
            for tool in list((await mcp_server.get_tools()).values()):
                if tool.name == "analyze_failed_pipeline":
                    tool_func = tool.fn
                    break

            assert tool_func is not None

            # Execute tool
            result = await tool_func(project_id="test-project", pipeline_id=123)

            # Verify result handles job errors gracefully
            assert "job_analyses" in result
            assert len(result["job_analyses"]) == 2

            for job_analysis in result["job_analyses"]:
                assert "error" in job_analysis
                assert "Failed to analyze job" in job_analysis["error"]
                assert job_analysis["error_count"] == 0
                assert job_analysis["warning_count"] == 0

    @pytest.mark.asyncio
    async def test_analyze_single_job_success(self, mcp_server, mock_analyzer):
        """Test successful single job analysis."""
        mock_trace = """
        ERROR: Build failed
        WARNING: Compilation warning
        """

        with patch(
            "gitlab_analyzer.mcp.tools.analysis_tools.get_gitlab_analyzer",
            return_value=mock_analyzer,
        ):
            # Setup mock responses
            mock_analyzer.get_job_trace.return_value = mock_trace

            # Mock log parser
            with (
                patch(
                    "gitlab_analyzer.mcp.tools.analysis_tools._is_pytest_log",
                    return_value=False,
                ),
                patch(
                    "gitlab_analyzer.mcp.tools.analysis_tools.LogParser.extract_log_entries"
                ) as mock_extract,
                patch(
                    "gitlab_analyzer.mcp.tools.analysis_tools.LogParser.categorize_error",
                    return_value={"category": "build", "severity": "high"},
                ),
            ):
                mock_extract.return_value = [
                    MagicMock(
                        level="error",
                        message="Build failed",
                        line_number=1,
                        timestamp=None,
                        context="build context",
                    ),
                    MagicMock(
                        level="warning",
                        message="Compilation warning",
                        line_number=2,
                        timestamp=None,
                        context="warning context",
                    ),
                ]

                # Get the tool function
                tool_func = None
                for tool in list((await mcp_server.get_tools()).values()):
                    if tool.name == "analyze_single_job":
                        tool_func = tool.fn
                        break

                assert tool_func is not None

                # Execute tool
                result = await tool_func(project_id="test-project", job_id=1001)

                # Verify result structure
                assert "project_id" in result
                assert "job_id" in result
                assert "errors" in result
                assert "warnings" in result
                assert "error_count" in result
                assert "warning_count" in result
                assert "analysis_timestamp" in result

                # Verify errors have categorization
                assert len(result["errors"]) == 1
                assert "categorization" in result["errors"][0]

    @pytest.mark.asyncio
    async def test_analyze_single_job_error(self, mcp_server, mock_analyzer):
        """Test single job analysis with error."""
        with patch(
            "gitlab_analyzer.mcp.tools.analysis_tools.get_gitlab_analyzer",
            return_value=mock_analyzer,
        ):
            # Setup mock to raise error
            mock_analyzer.get_job_trace.side_effect = httpx.RequestError(
                "Network error"
            )

            # Get the tool function
            tool_func = None
            for tool in list((await mcp_server.get_tools()).values()):
                if tool.name == "analyze_single_job":
                    tool_func = tool.fn
                    break

            assert tool_func is not None

            # Execute tool
            result = await tool_func(project_id="test-project", job_id=1001)

            # Verify error handling
            assert "error" in result
            assert "Failed to analyze job" in result["error"]
            assert result["project_id"] == "test-project"
            assert result["job_id"] == 1001

    @pytest.mark.asyncio
    async def test_analyze_single_job_empty_trace(self, mcp_server, mock_analyzer):
        """Test single job analysis with empty trace."""
        with patch(
            "gitlab_analyzer.mcp.tools.analysis_tools.get_gitlab_analyzer",
            return_value=mock_analyzer,
        ):
            # Setup mock responses
            mock_analyzer.get_job_trace.return_value = ""

            # Mock log parser returning empty results
            with patch(
                "gitlab_analyzer.mcp.tools.analysis_tools.LogParser.extract_log_entries",
                return_value=[],
            ):
                # Get the tool function
                tool_func = None
                for tool in list((await mcp_server.get_tools()).values()):
                    if tool.name == "analyze_single_job":
                        tool_func = tool.fn
                        break

                assert tool_func is not None

                # Execute tool
                result = await tool_func(project_id="test-project", job_id=1001)

                # Verify result with empty trace
                assert result["error_count"] == 0
                assert result["warning_count"] == 0
                assert result["errors"] == []
                assert result["warnings"] == []

    async def test_register_analysis_tools(self):
        """Test that analysis tools are properly registered."""
        mcp = FastMCP("test")
        register_analysis_tools(mcp)

        # Verify tools are registered
        tool_names = [tool.name for tool in list((await mcp.get_tools()).values())]
        assert "analyze_failed_pipeline" in tool_names
        assert "analyze_single_job" in tool_names

        # Verify tool metadata
        for tool in list((await mcp.get_tools()).values()):
            if tool.name == "analyze_failed_pipeline":
                assert "pipeline_id" in str(tool.fn.__annotations__)
                assert "project_id" in str(tool.fn.__annotations__)
            elif tool.name == "analyze_single_job":
                assert "job_id" in str(tool.fn.__annotations__)
                assert "project_id" in str(tool.fn.__annotations__)
