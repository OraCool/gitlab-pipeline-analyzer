"""
Tests for limited error and job resources

Copyright (c) 2025 Siarhei Skuratovich
Licensed under the MIT License - see LICENSE file for details
"""

from unittest.mock import AsyncMock, MagicMock, patch

from gitlab_analyzer.mcp.resources.job import get_limited_pipeline_jobs_resource
from gitlab_analyzer.mcp.services.error_service import error_service


class TestLimitedErrorResources:
    """Test limited error resources functionality"""

    @patch("gitlab_analyzer.mcp.services.error_service.get_cache_manager")
    @patch("gitlab_analyzer.utils.utils.get_mcp_info")
    async def test_get_limited_job_errors_basic(
        self, mock_get_mcp_info, mock_get_cache_manager
    ):
        """Test basic limited job errors functionality"""
        # Setup mock
        mock_cache = MagicMock()
        mock_get_cache_manager.return_value = mock_cache
        mock_get_mcp_info.return_value = {"tool": "test"}

        # Refresh the service's cache manager with our mock
        error_service.cache_manager = mock_cache

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
        result = await error_service.get_limited_job_errors(
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

    @patch("gitlab_analyzer.mcp.services.error_service.get_cache_manager")
    @patch("gitlab_analyzer.utils.utils.get_mcp_info")
    async def test_get_limited_job_errors_no_errors(
        self, mock_get_mcp_info, mock_get_cache_manager
    ):
        """Test limited job errors with no errors found"""
        # Setup mock
        mock_cache = MagicMock()
        mock_get_cache_manager.return_value = mock_cache
        mock_get_mcp_info.return_value = {"tool": "test"}

        # Refresh the service's cache manager with our mock
        error_service.cache_manager = mock_cache

        mock_cache.get_job_errors.return_value = []

        # Test with limit 2
        result = await error_service.get_limited_job_errors(
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

    @patch("gitlab_analyzer.mcp.services.error_service.check_pipeline_analyzed")
    @patch("gitlab_analyzer.mcp.services.error_service.get_cache_manager")
    @patch("gitlab_analyzer.utils.utils.get_mcp_info")
    async def test_get_limited_pipeline_errors_basic(
        self, mock_get_mcp_info, mock_get_cache_manager, mock_check_pipeline_analyzed
    ):
        """Test basic limited pipeline errors functionality"""
        # Setup mock
        mock_cache = MagicMock()
        mock_get_cache_manager.return_value = mock_cache
        mock_get_mcp_info.return_value = {"tool": "test"}
        mock_check_pipeline_analyzed.return_value = None  # Pipeline is analyzed

        # Refresh the service's cache manager with our mock
        error_service.cache_manager = mock_cache

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
        result = await error_service.get_limited_pipeline_errors(
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
        assert result["errors"][1]["job_name"] == "test-job-1"

        # Verify resource links
        assert len(result["resource_links"]) >= 1
        assert any(
            "gl://errors/83/pipeline/1615883" in link["resourceUri"]
            for link in result["resource_links"]
        )


class TestLimitedJobResources:
    """Test limited job resources functionality"""

    @patch("gitlab_analyzer.mcp.resources.job.get_cache_manager")
    async def test_get_limited_pipeline_jobs_failed(self, mock_get_cache_manager):
        """Test getting limited failed jobs from pipeline"""
        # Setup mock
        mock_cache = AsyncMock()
        mock_get_cache_manager.return_value = mock_cache

        # Mock the return value for get_or_compute
        expected_result = {
            "pipeline_id": 1615883,
            "project_id": "83",
            "status_filter": "failed",
            "limit": 2,
            "jobs": [
                {"job_id": 123, "name": "test-job-1", "status": "failed"},
                {"job_id": 124, "name": "test-job-2", "status": "failed"},
            ],
            "summary": {
                "total_jobs_available": 3,
                "jobs_returned": 2,
                "limit_applied": True,
                "status_filter": "failed",
                "failed_jobs": 2,
                "successful_jobs": 0,
                "other_status_jobs": 0,
            },
        }
        mock_cache.get_or_compute.return_value = expected_result

        # Test with limit 2
        result = await get_limited_pipeline_jobs_resource(
            project_id="83", pipeline_id="1615883", status_filter="failed", limit=2
        )

        # Verify results
        assert result["pipeline_id"] == 1615883
        assert result["project_id"] == "83"
        assert result["status_filter"] == "failed"
        assert result["limit"] == 2
        assert len(result["jobs"]) == 2
        assert result["summary"]["total_jobs_available"] == 3
        assert result["summary"]["jobs_returned"] == 2
        assert result["summary"]["limit_applied"]

        # Verify job content
        assert result["jobs"][0]["job_id"] == 123
        assert result["jobs"][0]["name"] == "test-job-1"
        assert result["jobs"][1]["job_id"] == 124
        assert result["jobs"][1]["name"] == "test-job-2"

    @patch("gitlab_analyzer.mcp.resources.job.get_cache_manager")
    async def test_get_limited_pipeline_jobs_success(self, mock_get_cache_manager):
        """Test getting limited successful jobs from pipeline"""
        # Setup mock
        mock_cache = AsyncMock()
        mock_get_cache_manager.return_value = mock_cache

        # Mock the return value for get_or_compute
        expected_result = {
            "pipeline_id": 1615883,
            "project_id": "83",
            "status_filter": "success",
            "limit": 5,
            "jobs": [
                {"job_id": 126, "name": "success-job-1", "status": "success"},
                {"job_id": 127, "name": "success-job-2", "status": "success"},
            ],
            "summary": {
                "total_jobs_available": 2,
                "jobs_returned": 2,
                "limit_applied": False,
                "status_filter": "success",
                "failed_jobs": 0,
                "successful_jobs": 2,
                "other_status_jobs": 0,
            },
        }
        mock_cache.get_or_compute.return_value = expected_result

        # Test with limit 5 (more than available)
        result = await get_limited_pipeline_jobs_resource(
            project_id="83", pipeline_id="1615883", status_filter="success", limit=5
        )

        # Verify results
        assert result["pipeline_id"] == 1615883
        assert result["project_id"] == "83"
        assert result["status_filter"] == "success"
        assert result["limit"] == 5
        assert len(result["jobs"]) == 2  # Only 2 available
        assert result["summary"]["total_jobs_available"] == 2
        assert result["summary"]["jobs_returned"] == 2
        assert not result["summary"]["limit_applied"]  # Limit not reached

        # Verify job content
        assert result["jobs"][0]["job_id"] == 126
        assert result["jobs"][0]["name"] == "success-job-1"
        assert result["jobs"][1]["job_id"] == 127
        assert result["jobs"][1]["name"] == "success-job-2"
