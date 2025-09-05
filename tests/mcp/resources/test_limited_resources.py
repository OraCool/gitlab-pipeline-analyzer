"""
Tests for limited error and job resources

Copyright (c) 2025 Siarhei Skuratovich
Licensed under the MIT License - see LICENSE file for details
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from gitlab_analyzer.mcp.resources.error import (
    get_limited_job_errors_resource_data,
    get_limited_pipeline_errors_resource_data,
)
from gitlab_analyzer.mcp.resources.job import get_limited_pipeline_jobs_resource


class TestLimitedErrorResources:
    """Test limited error resources functionality"""

    @patch("gitlab_analyzer.mcp.resources.error.get_cache_manager")
    @patch("gitlab_analyzer.mcp.resources.error.get_mcp_info")
    async def test_get_limited_job_errors_basic(
        self, mock_get_mcp_info, mock_get_cache_manager
    ):
        """Test basic limited job errors functionality"""
        # Setup mock
        mock_cache = MagicMock()
        mock_get_cache_manager.return_value = mock_cache
        mock_get_mcp_info.return_value = {"tool": "test"}

        # Mock error data
        mock_errors = [
            {
                "id": "123_0",
                "message": "Test error 1",
                "line": 10,
                "file_path": "test.py",
                "error_type": "python_error",
            },
            {
                "id": "123_1",
                "message": "Test error 2",
                "line": 20,
                "file_path": "test.py",
                "error_type": "syntax_error",
            },
            {
                "id": "123_2",
                "message": "Test error 3",
                "line": 30,
                "file_path": "test2.py",
                "error_type": "import_error",
            },
        ]
        mock_cache.get_job_errors.return_value = mock_errors

        # Test with limit 2
        result = await get_limited_job_errors_resource_data(
            project_id="83",
            job_id="123",
            limit=2,
            mode="balanced",
            include_trace=False,
        )

        # Verify results
        assert result["job_id"] == 123
        assert result["project_id"] == "83"
        assert result["limit"] == 2
        assert result["mode"] == "balanced"
        assert not result["include_trace"]
        assert len(result["errors"]) == 2
        assert result["summary"]["total_errors_available"] == 3
        assert result["summary"]["errors_returned"] == 2
        assert result["summary"]["limit_applied"]

        # Verify error content
        assert result["errors"][0]["id"] == "123_0"
        assert result["errors"][0]["message"] == "Test error 1"
        assert result["errors"][1]["id"] == "123_1"
        assert result["errors"][1]["message"] == "Test error 2"

        # Verify resource links
        assert len(result["resource_links"]) >= 1
        assert any(
            "gl://error/83/123" in link["resourceUri"]
            for link in result["resource_links"]
        )

    @patch("gitlab_analyzer.mcp.resources.error.get_cache_manager")
    @patch("gitlab_analyzer.mcp.resources.error.get_mcp_info")
    async def test_get_limited_job_errors_no_errors(
        self, mock_get_mcp_info, mock_get_cache_manager
    ):
        """Test limited job errors when no errors exist"""
        # Setup mock
        mock_cache = MagicMock()
        mock_get_cache_manager.return_value = mock_cache
        mock_get_mcp_info.return_value = {"tool": "test"}

        mock_cache.get_job_errors.return_value = []

        # Test with limit 2
        result = await get_limited_job_errors_resource_data(
            project_id="83",
            job_id="123",
            limit=2,
        )

        # Verify error response
        assert "error" in result
        assert result["error"] == "No errors found"
        assert result["job_id"] == 123
        assert result["project_id"] == "83"
        assert result["limit"] == 2

    @patch("gitlab_analyzer.mcp.resources.error.get_cache_manager")
    @patch("gitlab_analyzer.mcp.resources.error.get_mcp_info")
    async def test_get_limited_pipeline_errors_basic(
        self, mock_get_mcp_info, mock_get_cache_manager
    ):
        """Test basic limited pipeline errors functionality"""
        # Setup mock
        mock_cache = MagicMock()
        mock_get_cache_manager.return_value = mock_cache
        mock_get_mcp_info.return_value = {"tool": "test"}

        # Mock failed jobs
        mock_failed_jobs = [
            {"job_id": 123, "name": "test-job-1"},
            {"job_id": 124, "name": "test-job-2"},
        ]
        mock_cache.get_pipeline_failed_jobs.return_value = mock_failed_jobs

        # Mock errors for each job
        def mock_get_job_errors(job_id):
            if job_id == 123:
                return [
                    {
                        "id": "123_0",
                        "message": "Job 1 Error 1",
                        "line": 10,
                        "file_path": "test1.py",
                        "error_type": "python_error",
                    },
                    {
                        "id": "123_1",
                        "message": "Job 1 Error 2",
                        "line": 20,
                        "file_path": "test1.py",
                        "error_type": "syntax_error",
                    },
                ]
            elif job_id == 124:
                return [
                    {
                        "id": "124_0",
                        "message": "Job 2 Error 1",
                        "line": 15,
                        "file_path": "test2.py",
                        "error_type": "import_error",
                    },
                ]
            return []

        mock_cache.get_job_errors.side_effect = mock_get_job_errors

        # Test with limit 2
        result = await get_limited_pipeline_errors_resource_data(
            project_id="83",
            pipeline_id="1615883",
            limit=2,
            mode="balanced",
            include_trace=False,
        )

        # Verify results
        assert result["pipeline_id"] == 1615883
        assert result["project_id"] == "83"
        assert result["limit"] == 2
        assert result["mode"] == "balanced"
        assert not result["include_trace"]
        assert len(result["errors"]) == 2  # Limited to 2 errors
        assert result["summary"]["total_errors_available"] == 3  # Total available
        assert result["summary"]["errors_returned"] == 2
        assert result["summary"]["limit_applied"]
        assert result["summary"]["failed_jobs_count"] == 2

        # Verify error content includes job context
        assert result["errors"][0]["job_id"] == 123
        assert result["errors"][0]["job_name"] == "test-job-1"
        assert result["errors"][1]["job_id"] == 123
        assert "job_id" in result["errors"][1]

        # Verify jobs_processed info
        assert len(result["jobs_processed"]) == 2
        assert result["jobs_processed"][0]["job_id"] == 123
        assert result["jobs_processed"][0]["error_count"] == 2
        assert result["jobs_processed"][1]["job_id"] == 124
        assert result["jobs_processed"][1]["error_count"] == 1


class TestLimitedJobResources:
    """Test limited job resources functionality"""

    @patch("gitlab_analyzer.mcp.resources.job.get_cache_manager")
    @patch("gitlab_analyzer.mcp.resources.job.get_mcp_info")
    @patch("gitlab_analyzer.mcp.resources.job.generate_cache_key")
    async def test_get_limited_pipeline_jobs_failed(
        self, mock_cache_key, mock_get_mcp_info, mock_get_cache_manager
    ):
        """Test limited failed jobs functionality"""
        # Setup mocks
        mock_cache = MagicMock()
        mock_get_cache_manager.return_value = mock_cache
        mock_get_mcp_info.return_value = {"tool": "test"}
        mock_cache_key.return_value = "test_key"

        # Mock pipeline info
        mock_cache.get_pipeline_info_async = AsyncMock(
            return_value={
                "status": "failed",
                "branch": "main",
            }
        )

        # Mock failed jobs
        mock_failed_jobs = [
            {
                "job_id": 123,
                "name": "test-job-1",
                "status": "failed",
                "project_id": 83,
            },
            {
                "job_id": 124,
                "name": "test-job-2",
                "status": "failed",
                "project_id": 83,
            },
            {
                "job_id": 125,
                "name": "test-job-3",
                "status": "failed",
                "project_id": 83,
            },
        ]
        mock_cache.get_pipeline_failed_jobs.return_value = mock_failed_jobs

        # Mock get_or_compute to execute the function directly
        async def mock_get_or_compute(key, compute_func, **kwargs):
            return await compute_func()

        mock_cache.get_or_compute = mock_get_or_compute

        # Test with limit 2
        result = await get_limited_pipeline_jobs_resource(
            project_id="83",
            pipeline_id="1615883",
            status_filter="failed",
            limit=2,
        )

        # Verify results
        assert result["pipeline_info"]["pipeline_id"] == 1615883
        assert result["pipeline_info"]["project_id"] == "83"
        assert result["limit"] == 2
        assert len(result["jobs"]) == 2  # Limited to 2 jobs
        assert result["summary"]["total_jobs_available"] == 3  # Total available
        assert result["summary"]["jobs_returned"] == 2
        assert result["summary"]["limit_applied"]
        assert result["summary"]["status_filter"] == "failed"
        assert result["summary"]["failed_jobs"] == 2

        # Verify job content
        assert result["jobs"][0]["job_id"] == 123
        assert result["jobs"][0]["name"] == "test-job-1"
        assert result["jobs"][0]["status"] == "failed"
        assert result["jobs"][1]["job_id"] == 124
        assert result["jobs"][1]["name"] == "test-job-2"

        # Verify resource links exist
        assert "resource_links" in result["jobs"][0]
        assert len(result["jobs"][0]["resource_links"]) >= 1
        assert any(
            "gl://job/83/1615883/123" in link["resourceUri"]
            for link in result["jobs"][0]["resource_links"]
        )

    @patch("gitlab_analyzer.mcp.resources.job.get_cache_manager")
    @patch("gitlab_analyzer.mcp.resources.job.get_mcp_info")
    @patch("gitlab_analyzer.mcp.resources.job.generate_cache_key")
    async def test_get_limited_pipeline_jobs_success(
        self, mock_cache_key, mock_get_mcp_info, mock_get_cache_manager
    ):
        """Test limited successful jobs functionality"""
        # Setup mocks
        mock_cache = MagicMock()
        mock_get_cache_manager.return_value = mock_cache
        mock_get_mcp_info.return_value = {"tool": "test"}
        mock_cache_key.return_value = "test_key"

        # Mock pipeline info
        mock_cache.get_pipeline_info_async = AsyncMock(
            return_value={
                "status": "success",
                "branch": "main",
            }
        )

        # Mock all jobs with filtering
        mock_all_jobs = [
            {
                "job_id": 123,
                "name": "test-job-1",
                "status": "success",
                "project_id": 83,
            },
            {
                "job_id": 124,
                "name": "test-job-2",
                "status": "success",
                "project_id": 83,
            },
            {
                "job_id": 125,
                "name": "test-job-3",
                "status": "failed",
                "project_id": 83,
            },
        ]
        mock_cache.get_pipeline_jobs = AsyncMock(return_value=mock_all_jobs)

        # Mock get_or_compute to execute the function directly
        async def mock_get_or_compute(key, compute_func, **kwargs):
            return await compute_func()

        mock_cache.get_or_compute = mock_get_or_compute

        # Test with success filter and limit 1
        result = await get_limited_pipeline_jobs_resource(
            project_id="83",
            pipeline_id="1615883",
            status_filter="success",
            limit=1,
        )

        # Verify results
        assert result["pipeline_info"]["pipeline_id"] == 1615883
        assert result["limit"] == 1
        assert len(result["jobs"]) == 1  # Limited to 1 job
        assert result["summary"]["total_jobs_available"] == 2  # Only success jobs
        assert result["summary"]["jobs_returned"] == 1
        assert result["summary"]["limit_applied"]
        assert result["summary"]["status_filter"] == "success"
        assert result["summary"]["successful_jobs"] == 1

        # Verify job content
        assert result["jobs"][0]["job_id"] == 123
        assert result["jobs"][0]["status"] == "success"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
