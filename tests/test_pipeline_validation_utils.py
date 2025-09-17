"""
Targeted tests for pipeline validation utilities to achieve final coverage.

Tests edge cases and error handling paths in the pipeline validation module.
"""

from unittest.mock import AsyncMock, patch

import pytest

from src.gitlab_analyzer.mcp.utils.pipeline_validation import (
    check_job_analyzed,
    check_pipeline_analyzed,
)


class TestPipelineValidationUtilities:
    """Test cases for pipeline validation utility functions."""

    @pytest.mark.asyncio
    async def test_check_pipeline_analyzed_returns_none_when_pipeline_exists(self):
        """Test check_pipeline_analyzed returns None when pipeline is found."""
        with patch(
            "src.gitlab_analyzer.mcp.utils.pipeline_validation.get_cache_manager"
        ) as mock_get_cache:
            mock_cache = AsyncMock()
            mock_cache.get_pipeline_info_async.return_value = {
                "id": 12345,
                "status": "analyzed",
            }
            mock_get_cache.return_value = mock_cache

            result = await check_pipeline_analyzed("83", "12345", "test")

            assert result is None
            mock_cache.get_pipeline_info_async.assert_called_once_with(12345)

    @pytest.mark.asyncio
    async def test_check_pipeline_analyzed_returns_error_when_pipeline_missing(self):
        """Test check_pipeline_analyzed returns error dict when pipeline not found."""
        with patch(
            "src.gitlab_analyzer.mcp.utils.pipeline_validation.get_cache_manager"
        ) as mock_get_cache:
            mock_cache = AsyncMock()
            mock_cache.get_pipeline_info_async.return_value = None
            mock_get_cache.return_value = mock_cache

            result = await check_pipeline_analyzed("83", "12345", "test_resource")

            assert result is not None
            assert result["error"] == "pipeline_not_analyzed"
            assert result["pipeline_id"] == 12345
            assert result["project_id"] == "83"
            assert result["metadata"]["resource_type"] == "test_resource"

    @pytest.mark.asyncio
    async def test_check_job_analyzed_returns_none_when_job_exists(self):
        """Test check_job_analyzed returns None when job is found."""
        with patch(
            "src.gitlab_analyzer.mcp.utils.pipeline_validation.get_cache_manager"
        ) as mock_get_cache:
            mock_cache = AsyncMock()
            mock_cache.get_job_info_async.return_value = {
                "id": 67890,
                "name": "test_job",
            }
            mock_get_cache.return_value = mock_cache

            result = await check_job_analyzed("83", "67890", "test_job")

            assert result is None
            mock_cache.get_job_info_async.assert_called_once_with(67890)

    @pytest.mark.asyncio
    async def test_check_job_analyzed_returns_error_when_job_missing(self):
        """Test check_job_analyzed returns error dict when job not found."""
        with patch(
            "src.gitlab_analyzer.mcp.utils.pipeline_validation.get_cache_manager"
        ) as mock_get_cache:
            mock_cache = AsyncMock()
            mock_cache.get_job_info_async.return_value = None
            mock_get_cache.return_value = mock_cache

            result = await check_job_analyzed("83", "67890", "job_resource")

            assert result is not None
            assert result["error"] == "job_not_analyzed"
            assert result["job_id"] == 67890
            assert result["project_id"] == "83"
            assert "suggested_actions" in result
            assert len(result["suggested_actions"]) == 2

    @pytest.mark.asyncio
    async def test_check_job_analyzed_handles_cache_exception(self):
        """Test check_job_analyzed handles exceptions from cache manager gracefully."""
        with patch(
            "src.gitlab_analyzer.mcp.utils.pipeline_validation.get_cache_manager"
        ) as mock_get_cache:
            mock_cache = AsyncMock()
            # This triggers the missing lines 80-81 (exception handling)
            mock_cache.get_job_info_async.side_effect = Exception("Cache error")
            mock_get_cache.return_value = mock_cache

            result = await check_job_analyzed("83", "67890", "job_resource")

            # Should handle exception and return error response (job_info becomes None)
            assert result is not None
            assert result["error"] == "job_not_analyzed"
            assert result["job_id"] == 67890
            assert result["project_id"] == "83"
            mock_cache.get_job_info_async.assert_called_once_with(67890)

    @pytest.mark.asyncio
    async def test_check_pipeline_analyzed_with_custom_resource_type(self):
        """Test check_pipeline_analyzed with custom resource type context."""
        with patch(
            "src.gitlab_analyzer.mcp.utils.pipeline_validation.get_cache_manager"
        ) as mock_get_cache:
            mock_cache = AsyncMock()
            mock_cache.get_pipeline_info_async.return_value = None
            mock_get_cache.return_value = mock_cache

            result = await check_pipeline_analyzed("83", "12345", "custom_analysis")

            assert result is not None
            assert result["metadata"]["resource_type"] == "custom_analysis"
            assert (
                "Pipeline" in result["message"]
            )  # General check that it contains expected text

    @pytest.mark.asyncio
    async def test_check_job_analyzed_with_custom_resource_type(self):
        """Test check_job_analyzed with custom resource type context."""
        with patch(
            "src.gitlab_analyzer.mcp.utils.pipeline_validation.get_cache_manager"
        ) as mock_get_cache:
            mock_cache = AsyncMock()
            mock_cache.get_job_info_async.return_value = None
            mock_get_cache.return_value = mock_cache

            result = await check_job_analyzed("83", "67890", "custom_job_analysis")

            assert result is not None
            assert "custom_job_analysis" in str(result["mcp_info"]["tool_used"])
            assert result["resource_uri"] == "gl://error/83/67890"
