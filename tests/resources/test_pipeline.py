"""
Tests for pipeline resources

Copyright (c) 2025 Siarhei Skuratovich
Licensed under the MIT License - see LICENSE file for details
"""

from unittest.mock import AsyncMock, Mock, patch

import pytest

from gitlab_analyzer.mcp.resources.pipeline import (
    get_pipeline_resource,
    register_pipeline_resources,
)


class TestPipelineResources:
    """Test pipeline resource functionality"""

    @pytest.fixture
    def mock_analyzer(self):
        """Mock GitLab analyzer"""
        analyzer = Mock()
        analyzer.get_pipeline = AsyncMock(
            return_value={
                "id": 456,
                "project_id": "123",
                "status": "failed",
                "ref": "main",
                "sha": "abc123",
                "created_at": "2025-01-01T00:00:00Z",
                "updated_at": "2025-01-01T05:00:00Z",
                "duration": 300,
                "web_url": "https://gitlab.example.com/project/-/pipelines/456",
            }
        )

        # Create mock job objects with required attributes
        mock_job1 = Mock()
        mock_job1.id = 123
        mock_job1.name = "test_job"
        mock_job1.stage = "test"
        mock_job1.status = "failed"
        mock_job1.duration = 120
        mock_job1.created_at = "2025-01-01T00:00:00Z"
        mock_job1.finished_at = "2025-01-01T00:02:00Z"
        mock_job1.web_url = "https://gitlab.example.com/job/123"
        mock_job1.failure_reason = "test_failure"

        mock_job2 = Mock()
        mock_job2.id = 124
        mock_job2.name = "build_job"
        mock_job2.stage = "build"
        mock_job2.status = "success"
        mock_job2.duration = 60
        mock_job2.created_at = "2025-01-01T00:00:00Z"
        mock_job2.finished_at = "2025-01-01T00:01:00Z"
        mock_job2.web_url = "https://gitlab.example.com/job/124"
        mock_job2.failure_reason = None

        analyzer.get_pipeline_jobs = AsyncMock(return_value=[mock_job1, mock_job2])
        return analyzer

    @pytest.fixture
    def mock_cache_manager(self):
        """Mock cache manager"""
        cache_manager = Mock()
        cache_manager.get_or_compute = AsyncMock()
        cache_manager._stats = Mock()
        cache_manager._stats.newest_entry = None
        return cache_manager

    @patch("gitlab_analyzer.mcp.resources.pipeline.get_cache_manager")
    @patch("gitlab_analyzer.utils.utils.get_mcp_info")
    async def test_get_pipeline_resource_basic(
        self,
        mock_get_mcp_info,
        mock_get_cache,
        mock_cache_manager,
    ):
        """Test basic pipeline resource functionality"""
        # Setup mocks
        mock_get_cache.return_value = mock_cache_manager
        mock_get_mcp_info.return_value = {"tool": "test", "timestamp": "2025-01-01"}

        # Configure AsyncMock for cache manager methods
        from unittest.mock import AsyncMock

        mock_cache_manager.get_pipeline_info_async = AsyncMock(
            return_value={
                "pipeline_id": 456,
                "project_id": "123",
                "ref": "main",
                "sha": "abc123",
                "status": "failed",
                "web_url": "https://gitlab.example.com/project/-/pipelines/456",
                "created_at": "2025-01-01T00:00:00Z",
                "updated_at": "2025-01-01T05:00:00Z",
                "source_branch": None,
                "target_branch": None,
            }
        )

        mock_cache_manager.get_pipeline_jobs = AsyncMock(
            return_value=[
                {
                    "job_id": 123,
                    "name": "test_job",
                    "stage": "test",
                    "status": "failed",
                    "duration": 120,
                    "created_at": "2025-01-01T00:00:00Z",
                    "finished_at": "2025-01-01T00:02:00Z",
                    "web_url": "https://gitlab.example.com/job/123",
                    "failure_reason": "test_failure",
                },
                {
                    "job_id": 124,
                    "name": "build_job",
                    "stage": "build",
                    "status": "success",
                    "duration": 90,
                    "created_at": "2025-01-01T00:00:00Z",
                    "finished_at": "2025-01-01T00:01:30Z",
                    "web_url": "https://gitlab.example.com/job/124",
                    "failure_reason": None,
                },
            ]
        )

        mock_cache_manager.get_job_files_with_errors = AsyncMock(return_value=[])
        mock_cache_manager.get_or_compute = AsyncMock()

        # Mock cache to return computed data
        async def mock_compute_side_effect(key, compute_func, **kwargs):
            return await compute_func()

        mock_cache_manager.get_or_compute.side_effect = mock_compute_side_effect

        # Test parameters
        project_id = "123"
        pipeline_id = "456"

        # Execute
        result = await get_pipeline_resource(project_id, pipeline_id)

        # Verify
        assert result is not None
        assert isinstance(result, dict)

        # Check structure
        assert "pipeline_info" in result
        assert "jobs" in result
        assert "jobs_count" in result
        assert "failed_jobs_count" in result
        assert "metadata" in result
        assert "mcp_info" in result

        # Check pipeline content
        pipeline_info = result["pipeline_info"]
        assert pipeline_info["project_id"] == project_id
        assert pipeline_info["id"] == 456
        assert pipeline_info["status"] == "failed"
        assert pipeline_info["ref"] == "main"

        # Check jobs data
        jobs = result["jobs"]
        assert len(jobs) == 2
        assert jobs[0]["name"] == "test_job"
        assert jobs[0]["status"] == "failed"
        assert jobs[1]["name"] == "build_job"
        assert jobs[1]["status"] == "success"

        # Check metadata
        metadata = result["metadata"]
        assert metadata["resource_type"] == "pipeline"
        assert metadata["project_id"] == project_id
        assert metadata["pipeline_id"] == int(pipeline_id)

        # Verify database calls were made
        mock_cache_manager.get_or_compute.assert_called_once()
        mock_cache_manager.get_pipeline_info_async.assert_called_once_with(456)
        mock_cache_manager.get_pipeline_jobs.assert_called_once_with(456)
        mock_cache_manager.get_job_files_with_errors.assert_called_once_with(123)

    @patch("gitlab_analyzer.mcp.resources.pipeline.get_cache_manager")
    async def test_get_pipeline_resource_cached(
        self,
        mock_get_cache,
        mock_cache_manager,
    ):
        """Test pipeline resource with cached data"""
        # Setup cached data
        cached_data = {
            "pipeline_info": {
                "project_id": "123",
                "id": 456,
                "status": "success",
            },
            "jobs": [],
            "jobs_count": 0,
            "failed_jobs_count": 0,
            "cached": True,
        }
        mock_cache_manager.get_or_compute.return_value = cached_data
        mock_get_cache.return_value = mock_cache_manager

        # Execute
        result = await get_pipeline_resource("123", "456")

        # Verify
        assert result == cached_data

        # Verify cache was checked
        mock_cache_manager.get_or_compute.assert_called_once()

    @patch("gitlab_analyzer.mcp.resources.pipeline.get_cache_manager")
    async def test_get_pipeline_resource_error_handling(
        self, mock_get_cache, mock_cache_manager, mock_analyzer
    ):
        """Test error handling in pipeline resource"""
        # Setup mocks
        mock_get_cache.return_value = mock_cache_manager

        # Make analyzer raise an exception and cache propagate it
        mock_cache_manager.get_or_compute.side_effect = Exception("GitLab API error")

        # Execute and verify exception is raised
        with pytest.raises(Exception, match="GitLab API error"):
            await get_pipeline_resource("123", "456")

    def test_register_pipeline_resources(self):
        """Test resource registration"""
        # Mock MCP server
        mock_mcp = Mock()

        # Execute registration
        register_pipeline_resources(mock_mcp)

        # Verify resource decorator was called
        assert mock_mcp.resource.call_count == 1

        # Check the resource URI pattern
        call_args = mock_mcp.resource.call_args_list[0][0][0]
        expected_pattern = "gl://pipeline/{project_id}/{pipeline_id}"
        assert call_args == expected_pattern

    @patch("gitlab_analyzer.mcp.resources.pipeline.get_cache_manager")
    @patch("gitlab_analyzer.utils.utils.get_mcp_info")
    async def test_pipeline_status_calculation(
        self,
        mock_get_mcp_info,
        mock_get_cache,
        mock_cache_manager,
    ):
        """Test pipeline status and statistics calculation"""
        # Setup mocks
        mock_get_cache.return_value = mock_cache_manager
        mock_get_mcp_info.return_value = {"tool": "test"}

        # Configure AsyncMock for cache manager methods
        from unittest.mock import AsyncMock

        # Setup jobs with various statuses - converted to dict format for database
        job_data = []
        statuses = ["success", "failed", "success", "canceled"]
        for i, status in enumerate(statuses, 1):
            job_data.append(
                {
                    "job_id": i,
                    "name": f"job_{i}",
                    "stage": "test",
                    "status": status,
                    "duration": 60,
                    "created_at": "2025-01-01T00:00:00Z",
                    "finished_at": "2025-01-01T00:01:00Z",
                    "web_url": f"https://gitlab.example.com/job/{i}",
                    "failure_reason": "test_failure" if status == "failed" else None,
                }
            )

        mock_cache_manager.get_pipeline_info_async = AsyncMock(
            return_value={
                "pipeline_id": 456,
                "project_id": "123",
                "ref": "main",
                "sha": "abc123",
                "status": "failed",
                "web_url": "https://gitlab.example.com/project/-/pipelines/456",
                "created_at": "2025-01-01T00:00:00Z",
                "updated_at": "2025-01-01T05:00:00Z",
                "source_branch": None,
                "target_branch": None,
            }
        )

        mock_cache_manager.get_pipeline_jobs = AsyncMock(return_value=job_data)
        mock_cache_manager.get_job_files_with_errors = AsyncMock(return_value=[])
        mock_cache_manager.get_or_compute = AsyncMock()

        # Mock cache to return computed data
        async def mock_compute_side_effect(key, compute_func, **kwargs):
            return await compute_func()

        mock_cache_manager.get_or_compute.side_effect = mock_compute_side_effect

        # Execute
        result = await get_pipeline_resource("123", "456")

        # Verify statistics
        jobs = result["jobs"]
        assert len(jobs) == 4
        assert result["jobs_count"] == 4
        assert result["failed_jobs_count"] == 1

        # Verify job details are preserved
        success_jobs = [job for job in jobs if job["status"] == "success"]
        failed_jobs = [job for job in jobs if job["status"] == "failed"]
        canceled_jobs = [job for job in jobs if job["status"] == "canceled"]

        assert len(success_jobs) == 2
        assert len(failed_jobs) == 1
        assert len(canceled_jobs) == 1

    @patch("gitlab_analyzer.mcp.resources.pipeline.get_cache_manager")
    @patch("gitlab_analyzer.utils.utils.get_mcp_info")
    async def test_pipeline_timing_info(
        self,
        mock_get_mcp_info,
        mock_get_cache,
        mock_cache_manager,
    ):
        """Test pipeline timing information"""
        # Setup mocks
        mock_get_cache.return_value = mock_cache_manager
        mock_get_mcp_info.return_value = {"tool": "test"}

        # Configure AsyncMock for cache manager methods
        from unittest.mock import AsyncMock

        mock_cache_manager.get_pipeline_info_async = AsyncMock(
            return_value={
                "pipeline_id": 456,
                "project_id": "123",
                "ref": "main",
                "sha": "abc123",
                "status": "failed",
                "web_url": "https://gitlab.example.com/project/-/pipelines/456",
                "created_at": "2025-01-01T10:00:00Z",
                "updated_at": "2025-01-01T10:15:00Z",
                "source_branch": None,
                "target_branch": None,
            }
        )

        mock_cache_manager.get_pipeline_jobs = AsyncMock(return_value=[])
        mock_cache_manager.get_job_files_with_errors = AsyncMock(return_value=[])
        mock_cache_manager.get_or_compute = AsyncMock()

        # Mock cache to return computed data
        async def mock_compute_side_effect(key, compute_func, **kwargs):
            return await compute_func()

        mock_cache_manager.get_or_compute.side_effect = mock_compute_side_effect

        # Execute
        result = await get_pipeline_resource("123", "456")

        # Verify timing information
        pipeline_data = result["pipeline_info"]
        assert pipeline_data["created_at"] == "2025-01-01T10:00:00Z"
        assert pipeline_data["updated_at"] == "2025-01-01T10:15:00Z"
