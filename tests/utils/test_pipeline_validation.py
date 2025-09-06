"""
Tests for pipeline validation utilities

Copyright (c) 2025 Siarhei Skuratovich
Licensed under the MIT License - see LICENSE file for details
"""

from unittest.mock import AsyncMock, Mock

import pytest

from gitlab_analyzer.mcp.utils.pipeline_validation import (
    check_job_analyzed,
    check_pipeline_analyzed,
)


class TestPipelineValidation:
    """Test pipeline validation utilities"""

    @pytest.fixture
    def mock_cache_manager(self):
        """Mock cache manager"""
        cache_manager = Mock()
        return cache_manager

    @pytest.mark.asyncio
    async def test_check_pipeline_analyzed_exists(self, mock_cache_manager):
        """Test check_pipeline_analyzed when pipeline exists"""
        mock_cache_manager.get_pipeline_info = Mock(
            return_value={
                "pipeline_id": 12345,
                "status": "failed",
            }
        )

        with mock_cache_manager:
            result = await check_pipeline_analyzed(
                "test-project", "12345", "test_resource"
            )

        assert result is None
        mock_cache_manager.get_pipeline_info.assert_called_once_with(12345)

    @pytest.mark.asyncio
    async def test_check_pipeline_analyzed_not_exists(self, mock_cache_manager):
        """Test check_pipeline_analyzed when pipeline doesn't exist"""
        mock_cache_manager.get_pipeline_info = Mock(return_value=None)

        with mock_cache_manager:
            result = await check_pipeline_analyzed(
                "test-project", "12345", "test_resource"
            )

        assert result is not None
        assert "error" in result
        assert result["error"] == "pipeline_not_analyzed"
        assert result["pipeline_id"] == "12345"
        assert result["project_id"] == "test-project"
        assert "suggested_action" in result
        assert "mcp_info" in result

    @pytest.mark.asyncio
    async def test_check_job_analyzed_exists(self, mock_cache_manager):
        """Test check_job_analyzed when job exists"""
        mock_cache_manager.get_job_info_async = AsyncMock(
            return_value={
                "job_id": 1001,
                "name": "test-job",
            }
        )

        with mock_cache_manager:
            result = await check_job_analyzed("test-project", 1001, "test_resource")

        assert result is None
        mock_cache_manager.get_job_info_async.assert_called_once_with(1001)

    @pytest.mark.asyncio
    async def test_check_job_analyzed_not_exists(self, mock_cache_manager):
        """Test check_job_analyzed when job doesn't exist"""
        mock_cache_manager.get_job_info_async = AsyncMock(return_value=None)

        with mock_cache_manager:
            result = await check_job_analyzed("test-project", 1001, "test_resource")

        assert result is not None
        assert "error" in result
        assert result["error"] == "job_not_analyzed"
        assert result["job_id"] == 1001
        assert result["project_id"] == "test-project"
        assert "suggested_action" in result
        assert "mcp_info" in result

    @pytest.mark.asyncio
    async def test_check_pipeline_analyzed_custom_resource_context(
        self, mock_cache_manager
    ):
        """Test check_pipeline_analyzed with custom resource context"""
        mock_cache_manager.get_pipeline_info = Mock(return_value=None)

        with mock_cache_manager:
            result = await check_pipeline_analyzed(
                "test-project", "12345", "custom_resource"
            )

        assert result is not None
        assert result["mcp_info"]["resource_context"] == "custom_resource"

    @pytest.mark.asyncio
    async def test_check_job_analyzed_custom_resource_context(self, mock_cache_manager):
        """Test check_job_analyzed with custom resource context"""
        mock_cache_manager.get_job_info_async = AsyncMock(return_value=None)

        with mock_cache_manager:
            result = await check_job_analyzed("test-project", 1001, "custom_resource")

        assert result is not None
        assert result["mcp_info"]["resource_context"] == "custom_resource"

    @pytest.mark.asyncio
    async def test_error_message_content(self, mock_cache_manager):
        """Test that error messages contain helpful information"""
        mock_cache_manager.get_pipeline_info = Mock(return_value=None)

        with mock_cache_manager:
            result = await check_pipeline_analyzed(
                "test-project", "12345", "pipeline_errors"
            )

        assert "Pipeline has not been analyzed yet" in result["message"]
        assert "failed_pipeline_analysis" in result["suggested_action"]
        assert result["pipeline_id"] == "12345"
        assert result["project_id"] == "test-project"

    @pytest.mark.asyncio
    async def test_job_error_message_content(self, mock_cache_manager):
        """Test that job error messages contain helpful information"""
        mock_cache_manager.get_job_info_async = AsyncMock(return_value=None)

        with mock_cache_manager:
            result = await check_job_analyzed("test-project", 1001, "job_errors")

        assert "Job has not been analyzed yet" in result["message"]
        assert "analyze_job" in result["suggested_action"]
        assert result["job_id"] == 1001
        assert result["project_id"] == "test-project"
