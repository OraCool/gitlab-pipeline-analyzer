"""
Integration tests for MCP server

Copyright (c) 2025 Siarhei Skuratovich
Licensed under the MIT License - see LICENSE file for details
"""

from unittest.mock import AsyncMock, Mock, patch

import pytest

from gitlab_analyzer.mcp.servers.server import create_server
from gitlab_analyzer.models.job_info import JobInfo


class TestMCPIntegration:
    """Integration tests for MCP server functionality"""

    @pytest.mark.asyncio
    async def test_full_pipeline_analysis_flow(
        self, mock_env_vars, clean_global_analyzer
    ):
        """Test the complete flow of analyzing a failed pipeline"""
        # Mock GitLab API responses
        mock_pipeline_data = {
            "id": 12345,
            "iid": 123,
            "project_id": 1,
            "sha": "abc123def456",
            "ref": "main",
            "status": "failed",
            "created_at": "2025-01-01T10:00:00.000Z",
            "updated_at": "2025-01-01T10:30:00.000Z",
            "web_url": "https://gitlab.example.com/project/-/pipelines/12345",
        }

        mock_job_trace = """
        $ python -m pytest tests/ -v
        ============================== test session starts ==============================
        platform linux -- Python 3.11.0, pytest-7.4.3, pluggy-1.4.0
        cachedir: .pytest_cache
        rootdir: /builds/project/
        collected 3 items

        tests/test_example.py::test_passing PASSED                          [ 33%]
        tests/test_example.py::test_failing FAILED                          [ 66%]
        tests/test_example.py::test_error PASSED                            [100%]

        =================================== FAILURES ===================================
        __________________________ test_failing __________________________

            def test_failing():
        >       assert False, "This test is designed to fail"
        E       AssertionError: This test is designed to fail
        E       assert False

        tests/test_example.py:10: AssertionError
        ========================= short test summary info =========================
        FAILED tests/test_example.py::test_failing - AssertionError: This test is designed to fail
        ==================== 1 failed, 2 passed in 0.12s ====================
        ERROR: Job failed: exit code 1
        """

        # Create mock analyzer
        mock_analyzer = Mock()
        mock_analyzer.gitlab_url = "https://gitlab.example.com"
        mock_analyzer.get_pipeline = AsyncMock(return_value=mock_pipeline_data)
        mock_analyzer.get_failed_pipeline_jobs = AsyncMock(
            return_value=[
                JobInfo(
                    id=1001,
                    name="python-tests",
                    status="failed",
                    stage="test",
                    created_at="2025-01-01T10:05:00.000Z",
                    started_at="2025-01-01T10:06:00.000Z",
                    finished_at="2025-01-01T10:15:00.000Z",
                    failure_reason="script_failure",
                    web_url="https://gitlab.example.com/project/-/jobs/1001",
                )
            ]
        )
        mock_analyzer.get_job_trace = AsyncMock(return_value=mock_job_trace)

        with (
            patch(
                "gitlab_analyzer.mcp.tools.utils.get_gitlab_analyzer",
                return_value=mock_analyzer,
            ),
            patch(
                "gitlab_analyzer.mcp.tools.analysis_tools.get_gitlab_analyzer",
                return_value=mock_analyzer,
            ),
            patch(
                "gitlab_analyzer.mcp.tools.info_tools.get_gitlab_analyzer",
                return_value=mock_analyzer,
            ),
            patch(
                "gitlab_analyzer.mcp.tools.pytest_tools.get_gitlab_analyzer",
                return_value=mock_analyzer,
            ),
            patch(
                "gitlab_analyzer.mcp.tools.pytest_tools.get_gitlab_analyzer",
                return_value=mock_analyzer,
            ),
        ):
            server = create_server()

            # Get the analyze_failed_pipeline tool
            analyze_tool = await server.get_tool("analyze_failed_pipeline")

            assert analyze_tool is not None

            # Execute the tool function directly
            result = await analyze_tool.fn(project_id="test-project", pipeline_id=12345)

            # Verify the result structure
            assert isinstance(result, dict)
            assert "pipeline_id" in result
            assert "job_analyses" in result
            assert "summary" in result

            # Verify pipeline information
            assert result["pipeline_id"] == 12345
            assert result["pipeline_status"]["status"] == "failed"

            # Verify failed jobs information
            job_analyses = result["job_analyses"]
            assert len(job_analyses) == 1
            assert job_analyses[0]["job_id"] == 1001
            assert job_analyses[0]["job_name"] == "python-tests"

            # Verify that errors were extracted (they're in the job_analyses)
            job_analysis = job_analyses[0]
            assert "errors" in job_analysis
            assert len(job_analysis["errors"]) > 0

            # Verify summary
            summary = result["summary"]
            assert "total_errors" in summary
            assert "total_warnings" in summary
            assert summary["total_errors"] > 0

            # Verify failed jobs count is in the main result, not summary
            assert result["failed_jobs_count"] == 1

    @pytest.mark.asyncio
    async def test_single_job_analysis_flow(self, mock_env_vars, clean_global_analyzer):
        """Test the complete flow of analyzing a single job"""
        mock_job_trace = """
        $ python -m pytest tests/ -v
        ============================== test session starts ==============================
        platform linux -- Python 3.11.0, pytest-7.4.3, pluggy-1.4.0
        cachedir: .pytest_cache
        rootdir: /builds/project/
        collected 1 items

        tests/test_example.py::test_function FAILED                          [100%]

        =================================== FAILURES ===================================
        __________________________ test_function __________________________

            def test_function():
        >       assert add(1, 2) == 5, "expected 5, got 3"
        E       AssertionError: expected 5, got 3
        E       assert 3 == 5
        E        +  where 3 = add(1, 2)

        tests/test_example.py:15: AssertionError
        ========================= short test summary info =========================
        FAILED tests/test_example.py::test_function - AssertionError: expected 5, got 3
        ==================== 1 failed, 0 passed in 0.05s ====================
        ERROR: Test failed with exit code 1
        """

        # Create mock analyzer
        mock_analyzer = Mock()
        mock_analyzer.gitlab_url = "https://gitlab.example.com"
        mock_analyzer.get_job_trace = AsyncMock(return_value=mock_job_trace)

        with (
            patch(
                "gitlab_analyzer.mcp.tools.utils.get_gitlab_analyzer",
                return_value=mock_analyzer,
            ),
            patch(
                "gitlab_analyzer.mcp.tools.analysis_tools.get_gitlab_analyzer",
                return_value=mock_analyzer,
            ),
            patch(
                "gitlab_analyzer.mcp.tools.info_tools.get_gitlab_analyzer",
                return_value=mock_analyzer,
            ),
            patch(
                "gitlab_analyzer.mcp.tools.pytest_tools.get_gitlab_analyzer",
                return_value=mock_analyzer,
            ),
            patch(
                "gitlab_analyzer.mcp.tools.pytest_tools.get_gitlab_analyzer",
                return_value=mock_analyzer,
            ),
        ):
            server = create_server()

            # Get the analyze_single_job tool
            analyze_tool = await server.get_tool("analyze_single_job")

            assert analyze_tool is not None

            # Execute the tool function directly
            result = await analyze_tool.fn(project_id="test-project", job_id=1001)

            # Verify the result structure
            assert isinstance(result, dict)
            assert result["project_id"] == "test-project"
            assert result["job_id"] == 1001
            assert "errors" in result
            assert "warnings" in result
            assert "error_count" in result

            # Verify that errors were extracted from the trace
            assert len(result["errors"]) > 0

            # The analyze_single_job tool doesn't return job_url, so let's remove that assertion
            # Just verify the analysis worked correctly

    @pytest.mark.asyncio
    async def test_error_handling_invalid_project(
        self, mock_env_vars, clean_global_analyzer
    ):
        """Test error handling for invalid project"""
        from httpx import HTTPStatusError

        # Create mock analyzer that raises HTTP error
        mock_analyzer = Mock()
        mock_analyzer.get_pipeline = AsyncMock(
            side_effect=HTTPStatusError(
                "404 Not Found", request=Mock(), response=Mock(status_code=404)
            )
        )

        with (
            patch(
                "gitlab_analyzer.mcp.tools.utils.get_gitlab_analyzer",
                return_value=mock_analyzer,
            ),
            patch(
                "gitlab_analyzer.mcp.tools.analysis_tools.get_gitlab_analyzer",
                return_value=mock_analyzer,
            ),
            patch(
                "gitlab_analyzer.mcp.tools.info_tools.get_gitlab_analyzer",
                return_value=mock_analyzer,
            ),
            patch(
                "gitlab_analyzer.mcp.tools.pytest_tools.get_gitlab_analyzer",
                return_value=mock_analyzer,
            ),
            patch(
                "gitlab_analyzer.mcp.tools.pytest_tools.get_gitlab_analyzer",
                return_value=mock_analyzer,
            ),
        ):
            server = create_server()

            # Get the analyze_failed_pipeline tool
            analyze_tool = await server.get_tool("analyze_failed_pipeline")

            assert analyze_tool is not None

            # Execute the tool function directly - should handle the error gracefully
            try:
                result = await analyze_tool.fn(
                    project_id="invalid-project", pipeline_id=99999
                )
                # If it doesn't raise, it should return an error structure
                assert isinstance(result, dict)
                assert "error" in result
            except HTTPStatusError:
                # It's also acceptable for the tool to let HTTP errors bubble up
                pass

    @pytest.mark.asyncio
    async def test_empty_trace_handling(self, mock_env_vars, clean_global_analyzer):
        """Test handling of jobs with empty traces"""
        # Create mock analyzer with empty trace
        mock_analyzer = Mock()
        mock_analyzer.gitlab_url = "https://gitlab.example.com"
        mock_analyzer.get_job_trace = AsyncMock(return_value="")

        with (
            patch(
                "gitlab_analyzer.mcp.tools.utils.get_gitlab_analyzer",
                return_value=mock_analyzer,
            ),
            patch(
                "gitlab_analyzer.mcp.tools.analysis_tools.get_gitlab_analyzer",
                return_value=mock_analyzer,
            ),
            patch(
                "gitlab_analyzer.mcp.tools.info_tools.get_gitlab_analyzer",
                return_value=mock_analyzer,
            ),
            patch(
                "gitlab_analyzer.mcp.tools.pytest_tools.get_gitlab_analyzer",
                return_value=mock_analyzer,
            ),
            patch(
                "gitlab_analyzer.mcp.tools.pytest_tools.get_gitlab_analyzer",
                return_value=mock_analyzer,
            ),
        ):
            server = create_server()

            # Get the analyze_single_job tool
            analyze_tool = await server.get_tool("analyze_single_job")

            assert analyze_tool is not None

            # Execute the tool function directly
            result = await analyze_tool.fn(project_id="test-project", job_id=1001)

            # Should handle empty trace gracefully
            assert isinstance(result, dict)
            assert result["job_id"] == 1001
            assert result["error_count"] == 0
            assert len(result["errors"]) == 0
            assert result["trace_length"] == 0

    @pytest.mark.asyncio
    async def test_multiple_failed_jobs_analysis(
        self, mock_env_vars, clean_global_analyzer
    ):
        """Test analysis of pipeline with multiple failed jobs"""
        mock_pipeline_data = {
            "id": 12345,
            "status": "failed",
            "ref": "main",
            "web_url": "https://gitlab.example.com/project/-/pipelines/12345",
        }

        mock_failed_jobs = [
            JobInfo(
                id=1001,
                name="test-job-1",
                status="failed",
                stage="test",
                created_at="2025-01-01T10:05:00.000Z",
                started_at="2025-01-01T10:06:00.000Z",
                finished_at="2025-01-01T10:15:00.000Z",
                failure_reason="script_failure",
                web_url="https://gitlab.example.com/project/-/jobs/1001",
            ),
            JobInfo(
                id=1002,
                name="test-job-2",
                status="failed",
                stage="test",
                created_at="2025-01-01T10:05:00.000Z",
                started_at="2025-01-01T10:06:00.000Z",
                finished_at="2025-01-01T10:15:00.000Z",
                failure_reason="script_failure",
                web_url="https://gitlab.example.com/project/-/jobs/1002",
            ),
        ]

        mock_job_traces = {
            1001: "npm ERR! Test failure in job 1",
            1002: "npm ERR! Test failure in job 2",
        }

        # Create mock analyzer
        mock_analyzer = Mock()
        mock_analyzer.gitlab_url = "https://gitlab.example.com"
        mock_analyzer.get_pipeline = AsyncMock(return_value=mock_pipeline_data)
        mock_analyzer.get_failed_pipeline_jobs = AsyncMock(
            return_value=mock_failed_jobs
        )
        mock_analyzer.get_job_trace = AsyncMock(
            side_effect=lambda project_id, job_id: mock_job_traces[job_id]
        )

        with (
            patch(
                "gitlab_analyzer.mcp.tools.utils.get_gitlab_analyzer",
                return_value=mock_analyzer,
            ),
            patch(
                "gitlab_analyzer.mcp.tools.analysis_tools.get_gitlab_analyzer",
                return_value=mock_analyzer,
            ),
            patch(
                "gitlab_analyzer.mcp.tools.info_tools.get_gitlab_analyzer",
                return_value=mock_analyzer,
            ),
            patch(
                "gitlab_analyzer.mcp.tools.pytest_tools.get_gitlab_analyzer",
                return_value=mock_analyzer,
            ),
            patch(
                "gitlab_analyzer.mcp.tools.pytest_tools.get_gitlab_analyzer",
                return_value=mock_analyzer,
            ),
        ):
            server = create_server()

            # Get the analyze_failed_pipeline tool
            analyze_tool = await server.get_tool("analyze_failed_pipeline")

            assert analyze_tool is not None

            # Execute the tool function directly
            result = await analyze_tool.fn(project_id="test-project", pipeline_id=12345)

            # Verify multiple jobs were analyzed
            assert isinstance(result, dict)
            assert "job_analyses" in result
            job_analyses = result["job_analyses"]
            assert len(job_analyses) == 2

            # Verify both jobs have analysis
            job_ids = [job["job_id"] for job in job_analyses]
            assert 1001 in job_ids
            assert 1002 in job_ids

            # Verify summary accounts for both jobs
            assert result["failed_jobs_count"] == 2
