"""
Unit tests for MCP info tools.

Copyright (c) 2025 Siarhei Skuratovich
Licensed under the MIT License - see LICENSE file for details
"""

from datetime import datetime
from unittest.mock import AsyncMock, patch

import httpx
import pytest
from fastmcp import FastMCP

from gitlab_analyzer.mcp.tools.info_tools import register_info_tools
from gitlab_analyzer.models.job_info import JobInfo


class TestInfoTools:
    """Test MCP info tools."""

    @pytest.fixture
    def mcp_server(self):
        """Create FastMCP server with info tools."""
        mcp = FastMCP("test")
        register_info_tools(mcp)
        return mcp

    @pytest.fixture
    def mock_analyzer(self):
        """Mock GitLab analyzer."""
        analyzer = AsyncMock()
        return analyzer

    @pytest.fixture
    def sample_jobs(self):
        """Sample jobs data."""
        return [
            JobInfo(
                id=1001,
                name="test-job-1",
                status="success",
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
            JobInfo(
                id=1003,
                name="test-job-3",
                status="running",
                stage="deploy",
                created_at=datetime.now().isoformat(),
                web_url="https://gitlab.com/project/job/1003",
            ),
        ]

    @pytest.fixture
    def sample_failed_jobs(self):
        """Sample failed jobs data."""
        return [
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
    async def test_get_pipeline_jobs_success(
        self, mcp_server, mock_analyzer, sample_jobs
    ):
        """Test successful pipeline jobs retrieval."""
        with patch(
            "gitlab_analyzer.mcp.tools.info_tools.get_gitlab_analyzer",
            return_value=mock_analyzer,
        ):
            # Setup mock response
            mock_analyzer.get_pipeline_jobs.return_value = sample_jobs

            # Get the tool function
            tool_func = None
            for tool in list((await mcp_server.get_tools()).values()):
                if tool.name == "get_pipeline_jobs":
                    tool_func = tool.fn
                    break

            assert tool_func is not None

            # Execute tool
            result = await tool_func(project_id="test-project", pipeline_id=123)

            # Verify result structure
            assert "project_id" in result
            assert "pipeline_id" in result
            assert "jobs" in result
            assert "job_count" in result
            assert "analysis_timestamp" in result

            # Verify data
            assert result["project_id"] == "test-project"
            assert result["pipeline_id"] == 123
            assert result["job_count"] == 3
            assert len(result["jobs"]) == 3

            # Verify timestamp format
            assert isinstance(result["analysis_timestamp"], str)

    @pytest.mark.asyncio
    async def test_get_pipeline_jobs_error(self, mcp_server, mock_analyzer):
        """Test pipeline jobs retrieval with error."""
        with patch(
            "gitlab_analyzer.mcp.tools.info_tools.get_gitlab_analyzer",
            return_value=mock_analyzer,
        ):
            # Setup mock to raise error
            mock_analyzer.get_pipeline_jobs.side_effect = httpx.HTTPError("API Error")

            # Get the tool function
            tool_func = None
            for tool in list((await mcp_server.get_tools()).values()):
                if tool.name == "get_pipeline_jobs":
                    tool_func = tool.fn
                    break

            assert tool_func is not None

            # Execute tool
            result = await tool_func(project_id="test-project", pipeline_id=123)

            # Verify error handling
            assert "error" in result
            assert "Failed to get pipeline jobs" in result["error"]
            assert result["project_id"] == "test-project"
            assert result["pipeline_id"] == 123

    @pytest.mark.asyncio
    async def test_get_pipeline_jobs_empty_result(self, mcp_server, mock_analyzer):
        """Test pipeline jobs retrieval with empty result."""
        with patch(
            "gitlab_analyzer.mcp.tools.info_tools.get_gitlab_analyzer",
            return_value=mock_analyzer,
        ):
            # Setup mock to return empty list
            mock_analyzer.get_pipeline_jobs.return_value = []

            # Get the tool function
            tool_func = None
            for tool in list((await mcp_server.get_tools()).values()):
                if tool.name == "get_pipeline_jobs":
                    tool_func = tool.fn
                    break

            assert tool_func is not None

            # Execute tool
            result = await tool_func(project_id="test-project", pipeline_id=123)

            # Verify result with no jobs
            assert result["job_count"] == 0
            assert result["jobs"] == []

    @pytest.mark.asyncio
    async def test_get_failed_jobs_success(
        self, mcp_server, mock_analyzer, sample_failed_jobs
    ):
        """Test successful failed jobs retrieval."""
        with patch(
            "gitlab_analyzer.mcp.tools.info_tools.get_gitlab_analyzer",
            return_value=mock_analyzer,
        ):
            # Setup mock response
            mock_analyzer.get_failed_pipeline_jobs.return_value = sample_failed_jobs

            # Get the tool function
            tool_func = None
            for tool in list((await mcp_server.get_tools()).values()):
                if tool.name == "get_failed_jobs":
                    tool_func = tool.fn
                    break

            assert tool_func is not None

            # Execute tool
            result = await tool_func(project_id="test-project", pipeline_id=123)

            # Verify result structure
            assert "project_id" in result
            assert "pipeline_id" in result
            assert "failed_jobs" in result
            assert "failed_job_count" in result
            assert "analysis_timestamp" in result

            # Verify data
            assert result["project_id"] == "test-project"
            assert result["pipeline_id"] == 123
            assert result["failed_job_count"] == 1
            assert len(result["failed_jobs"]) == 1

    @pytest.mark.asyncio
    async def test_get_failed_jobs_error(self, mcp_server, mock_analyzer):
        """Test failed jobs retrieval with error."""
        with patch(
            "gitlab_analyzer.mcp.tools.info_tools.get_gitlab_analyzer",
            return_value=mock_analyzer,
        ):
            # Setup mock to raise error
            mock_analyzer.get_failed_pipeline_jobs.side_effect = httpx.RequestError(
                "Network error"
            )

            # Get the tool function
            tool_func = None
            for tool in list((await mcp_server.get_tools()).values()):
                if tool.name == "get_failed_jobs":
                    tool_func = tool.fn
                    break

            assert tool_func is not None

            # Execute tool
            result = await tool_func(project_id="test-project", pipeline_id=123)

            # Verify error handling
            assert "error" in result
            assert "Failed to get failed jobs" in result["error"]

    @pytest.mark.asyncio
    async def test_get_failed_jobs_no_failures(self, mcp_server, mock_analyzer):
        """Test failed jobs retrieval when no jobs failed."""
        with patch(
            "gitlab_analyzer.mcp.tools.info_tools.get_gitlab_analyzer",
            return_value=mock_analyzer,
        ):
            # Setup mock to return empty list
            mock_analyzer.get_failed_pipeline_jobs.return_value = []

            # Get the tool function
            tool_func = None
            for tool in list((await mcp_server.get_tools()).values()):
                if tool.name == "get_failed_jobs":
                    tool_func = tool.fn
                    break

            assert tool_func is not None

            # Execute tool
            result = await tool_func(project_id="test-project", pipeline_id=123)

            # Verify result with no failed jobs
            assert result["failed_job_count"] == 0
            assert result["failed_jobs"] == []

    @pytest.mark.asyncio
    async def test_get_job_trace_success(self, mcp_server, mock_analyzer):
        """Test successful job trace retrieval."""
        sample_trace = """
        Starting job...
        Running tests...
        ERROR: Test failed
        Job completed with errors
        """

        with patch(
            "gitlab_analyzer.mcp.tools.info_tools.get_gitlab_analyzer",
            return_value=mock_analyzer,
        ):
            # Setup mock response
            mock_analyzer.get_job_trace.return_value = sample_trace

            # Get the tool function
            tool_func = None
            for tool in list((await mcp_server.get_tools()).values()):
                if tool.name == "get_job_trace":
                    tool_func = tool.fn
                    break

            assert tool_func is not None

            # Execute tool
            result = await tool_func(project_id="test-project", job_id=1001)

            # Verify result structure
            assert "project_id" in result
            assert "job_id" in result
            assert "trace" in result
            assert "trace_length" in result
            assert "analysis_timestamp" in result

            # Verify data
            assert result["project_id"] == "test-project"
            assert result["job_id"] == 1001
            assert result["trace"] == sample_trace
            assert result["trace_length"] == len(sample_trace)

    @pytest.mark.asyncio
    async def test_get_job_trace_error(self, mcp_server, mock_analyzer):
        """Test job trace retrieval with error."""
        with patch(
            "gitlab_analyzer.mcp.tools.info_tools.get_gitlab_analyzer",
            return_value=mock_analyzer,
        ):
            # Setup mock to raise error
            mock_analyzer.get_job_trace.side_effect = ValueError("Invalid job ID")

            # Get the tool function
            tool_func = None
            for tool in list((await mcp_server.get_tools()).values()):
                if tool.name == "get_job_trace":
                    tool_func = tool.fn
                    break

            assert tool_func is not None

            # Execute tool
            result = await tool_func(project_id="test-project", job_id=1001)

            # Verify error handling
            assert "error" in result
            assert "Failed to get job trace" in result["error"]

    @pytest.mark.asyncio
    async def test_get_cleaned_job_trace_success(self, mcp_server, mock_analyzer):
        """Test successful cleaned job trace retrieval."""
        sample_trace = "\x1b[31mRed text\x1b[0m\nNormal text\n\x1b[32mGreen text\x1b[0m"
        cleaned_trace = "Red text\nNormal text\nGreen text"

        with patch(
            "gitlab_analyzer.mcp.tools.info_tools.get_gitlab_analyzer",
            return_value=mock_analyzer,
        ):
            # Setup mock response
            mock_analyzer.get_job_trace.return_value = sample_trace

            # Mock BaseParser.clean_ansi_sequences
            with patch(
                "gitlab_analyzer.mcp.tools.info_tools.BaseParser.clean_ansi_sequences",
                return_value=cleaned_trace,
            ):
                # Get the tool function
                tool_func = None
                for tool in list((await mcp_server.get_tools()).values()):
                    if tool.name == "get_cleaned_job_trace":
                        tool_func = tool.fn
                        break

                assert tool_func is not None

                # Execute tool
                result = await tool_func(project_id="test-project", job_id=1001)

                # Verify result structure
                assert "project_id" in result
                assert "job_id" in result
                assert "cleaned_trace" in result
                assert "original_length" in result
                assert "cleaned_length" in result
                assert "ansi_sequences_found" in result
                assert "analysis_timestamp" in result

                # Verify data
                assert result["project_id"] == "test-project"
                assert result["job_id"] == 1001
                assert result["cleaned_trace"] == cleaned_trace
                assert result["original_length"] == len(sample_trace)
                assert result["cleaned_length"] == len(cleaned_trace)
                assert result["ansi_sequences_found"] > 0

    @pytest.mark.asyncio
    async def test_get_pipeline_status_success(self, mcp_server, mock_analyzer):
        """Test successful pipeline status retrieval."""
        sample_pipeline = {
            "id": 123,
            "project_id": 456,
            "ref": "main",
            "status": "success",
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
        }

        with patch(
            "gitlab_analyzer.mcp.tools.info_tools.get_gitlab_analyzer",
            return_value=mock_analyzer,
        ):
            # Setup mock response
            mock_analyzer.get_pipeline.return_value = sample_pipeline

            # Get the tool function
            tool_func = None
            for tool in list((await mcp_server.get_tools()).values()):
                if tool.name == "get_pipeline_status":
                    tool_func = tool.fn
                    break

            assert tool_func is not None

            # Execute tool
            result = await tool_func(project_id="test-project", pipeline_id=123)

            # Verify result structure
            assert "project_id" in result
            assert "pipeline_id" in result
            assert "pipeline" in result
            assert "analysis_timestamp" in result

            # Verify data
            assert result["project_id"] == "test-project"
            assert result["pipeline_id"] == 123
            assert result["pipeline"] == sample_pipeline

    async def test_register_info_tools(self):
        """Test that info tools are properly registered."""
        mcp = FastMCP("test")
        register_info_tools(mcp)

        # Verify tools are registered
        tool_names = [tool.name for tool in list((await mcp.get_tools()).values())]
        expected_tools = [
            "get_pipeline_jobs",
            "get_failed_jobs",
            "get_job_trace",
            "get_cleaned_job_trace",
            "get_pipeline_status",
            "get_pipeline_info",
        ]

        for expected_tool in expected_tools:
            assert expected_tool in tool_names

    @pytest.mark.asyncio
    async def test_get_pipeline_info_regular_branch(self, mcp_server, mock_analyzer):
        """Test get_pipeline_info with regular branch pipeline."""
        sample_pipeline = {
            "id": 123,
            "project_id": 456,
            "ref": "feature-branch",
            "status": "failed",
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
        }

        with patch(
            "gitlab_analyzer.mcp.tools.info_tools.get_gitlab_analyzer",
            return_value=mock_analyzer,
        ):
            # Setup mock response
            mock_analyzer.get_pipeline.return_value = sample_pipeline

            # Get the tool function
            tool_func = None
            for tool in list((await mcp_server.get_tools()).values()):
                if tool.name == "get_pipeline_info":
                    tool_func = tool.fn
                    break

            assert tool_func is not None

            # Execute tool
            result = await tool_func(project_id="test-project", pipeline_id=123)

            # Verify result structure
            assert "project_id" in result
            assert "pipeline_id" in result
            assert "pipeline_info" in result
            assert "original_branch" in result
            assert "target_branch" in result
            assert "pipeline_type" in result
            assert "merge_request_info" in result
            assert "can_auto_fix" in result

            # Verify data for regular branch
            assert result["project_id"] == "test-project"
            assert result["pipeline_id"] == 123
            assert result["original_branch"] == "feature-branch"
            assert (
                result["target_branch"] == "feature-branch"
            )  # Same as original for regular branch
            assert result["pipeline_type"] == "branch"
            assert result["merge_request_info"] is None
            assert result["can_auto_fix"] is True

    @pytest.mark.asyncio
    async def test_get_pipeline_info_merge_request(self, mcp_server, mock_analyzer):
        """Test get_pipeline_info with merge request pipeline."""
        sample_pipeline = {
            "id": 123,
            "project_id": 456,
            "ref": "refs/merge-requests/42/head",
            "status": "failed",
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
        }

        sample_merge_request = {
            "id": 999,
            "iid": 42,
            "source_branch": "feature-new-functionality",
            "target_branch": "main",
            "title": "Add new functionality",
            "state": "opened",
        }

        with patch(
            "gitlab_analyzer.mcp.tools.info_tools.get_gitlab_analyzer",
            return_value=mock_analyzer,
        ):
            # Setup mock responses
            mock_analyzer.get_pipeline.return_value = sample_pipeline
            mock_analyzer.get_merge_request.return_value = sample_merge_request

            # Get the tool function
            tool_func = None
            for tool in list((await mcp_server.get_tools()).values()):
                if tool.name == "get_pipeline_info":
                    tool_func = tool.fn
                    break

            assert tool_func is not None

            # Execute tool
            result = await tool_func(project_id="test-project", pipeline_id=123)

            # Verify result structure
            assert "project_id" in result
            assert "pipeline_id" in result
            assert "pipeline_info" in result
            assert "original_branch" in result
            assert "target_branch" in result
            assert "pipeline_type" in result
            assert "merge_request_info" in result
            assert "can_auto_fix" in result

            # Verify data for merge request
            assert result["project_id"] == "test-project"
            assert result["pipeline_id"] == 123
            assert result["original_branch"] == "refs/merge-requests/42/head"
            assert (
                result["target_branch"] == "feature-new-functionality"
            )  # Source branch from MR
            assert result["pipeline_type"] == "merge_request"
            assert result["merge_request_info"] == sample_merge_request
            assert result["can_auto_fix"] is True

            # Verify analyzer was called correctly
            mock_analyzer.get_merge_request.assert_called_once_with("test-project", 42)

    @pytest.mark.asyncio
    async def test_get_pipeline_info_merge_request_error(
        self, mcp_server, mock_analyzer
    ):
        """Test get_pipeline_info with merge request pipeline when MR fetch fails."""
        sample_pipeline = {
            "id": 123,
            "project_id": 456,
            "ref": "refs/merge-requests/42/head",
            "status": "failed",
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
        }

        with patch(
            "gitlab_analyzer.mcp.tools.info_tools.get_gitlab_analyzer",
            return_value=mock_analyzer,
        ):
            # Setup mock responses
            mock_analyzer.get_pipeline.return_value = sample_pipeline
            mock_analyzer.get_merge_request.side_effect = httpx.HTTPError(
                "MR not found"
            )

            # Get the tool function
            tool_func = None
            for tool in list((await mcp_server.get_tools()).values()):
                if tool.name == "get_pipeline_info":
                    tool_func = tool.fn
                    break

            assert tool_func is not None

            # Execute tool
            result = await tool_func(project_id="test-project", pipeline_id=123)

            # Verify fallback behavior when MR fetch fails
            assert result["original_branch"] == "refs/merge-requests/42/head"
            assert (
                result["target_branch"] == "refs/merge-requests/42/head"
            )  # Falls back to original
            assert result["pipeline_type"] == "merge_request"
            assert (
                result["can_auto_fix"] is False
            )  # Should be false when MR fetch fails
            assert "error" in result["merge_request_info"]

    @pytest.mark.asyncio
    async def test_get_pipeline_info_invalid_mr_ref(self, mcp_server, mock_analyzer):
        """Test get_pipeline_info with invalid merge request ref format."""
        sample_pipeline = {
            "id": 123,
            "project_id": 456,
            "ref": "refs/merge-requests/invalid/head",  # Invalid MR ID
            "status": "failed",
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
        }

        with patch(
            "gitlab_analyzer.mcp.tools.info_tools.get_gitlab_analyzer",
            return_value=mock_analyzer,
        ):
            # Setup mock response
            mock_analyzer.get_pipeline.return_value = sample_pipeline

            # Get the tool function
            tool_func = None
            for tool in list((await mcp_server.get_tools()).values()):
                if tool.name == "get_pipeline_info":
                    tool_func = tool.fn
                    break

            assert tool_func is not None

            # Execute tool
            result = await tool_func(project_id="test-project", pipeline_id=123)

            # Verify fallback behavior when MR ref is invalid
            assert result["original_branch"] == "refs/merge-requests/invalid/head"
            assert (
                result["target_branch"] == "refs/merge-requests/invalid/head"
            )  # Falls back to original
            assert result["pipeline_type"] == "merge_request"
            assert result["can_auto_fix"] is False  # Should be false when parsing fails
            assert "error" in result["merge_request_info"]

    @pytest.mark.asyncio
    async def test_project_id_type_conversion(
        self, mcp_server, mock_analyzer, sample_jobs
    ):
        """Test that project_id is properly converted to string in results."""
        with patch(
            "gitlab_analyzer.mcp.tools.info_tools.get_gitlab_analyzer",
            return_value=mock_analyzer,
        ):
            # Setup mock response
            mock_analyzer.get_pipeline_jobs.return_value = sample_jobs

            # Get the tool function
            tool_func = None
            for tool in list((await mcp_server.get_tools()).values()):
                if tool.name == "get_pipeline_jobs":
                    tool_func = tool.fn
                    break

            assert tool_func is not None

            # Execute tool with integer project_id
            result = await tool_func(project_id=12345, pipeline_id=123)

            # Verify project_id is converted to string
            assert result["project_id"] == "12345"
            assert isinstance(result["project_id"], str)
