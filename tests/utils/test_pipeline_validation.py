"""
Tests for pipeline validation utilities

Copyright (c) 2025 Siarhei Skuratovich
Licensed under the MIT License - see LICENSE file for details
"""

from unittest.mock import AsyncMock, Mock, patch

import pytest

from gitlab_analyzer.mcp.utils.pipeline_validation import (
    check_job_analyzed,
    check_pipeline_analyzed,
)


class TestPipelineValidation:
    """Test pipeline validation utilities"""

    @pytest.mark.asyncio
    @patch("gitlab_analyzer.mcp.utils.pipeline_validation.get_cache_manager")
    async def test_check_pipeline_analyzed_exists(self, mock_get_cache_manager):
        """Test check_pipeline_analyzed when pipeline exists"""
        mock_cache_manager = Mock()
        mock_get_cache_manager.return_value = mock_cache_manager

        mock_cache_manager.get_pipeline_info_async = AsyncMock(
            return_value={
                "pipeline_id": 12345,
                "status": "failed",
            }
        )

        result = await check_pipeline_analyzed("test-project", "12345", "test_resource")

        assert result is None
        mock_cache_manager.get_pipeline_info_async.assert_called_once_with(12345)

    @pytest.mark.asyncio
    @patch("gitlab_analyzer.mcp.utils.pipeline_validation.get_cache_manager")
    async def test_check_pipeline_analyzed_not_exists(self, mock_get_cache_manager):
        """Test check_pipeline_analyzed when pipeline doesn't exist"""
        mock_cache_manager = Mock()
        mock_get_cache_manager.return_value = mock_cache_manager

        mock_cache_manager.get_pipeline_info_async = AsyncMock(return_value=None)

        result = await check_pipeline_analyzed("test-project", "12345", "test_resource")

        assert result is not None
        assert "error" in result
        assert result["error"] == "pipeline_not_analyzed"
        assert result["pipeline_id"] == 12345
        assert result["project_id"] == "test-project"
        assert "required_action" in result
        assert "mcp_info" in result

    @pytest.mark.asyncio
    @patch("gitlab_analyzer.mcp.utils.pipeline_validation.get_cache_manager")
    async def test_check_job_analyzed_exists(self, mock_get_cache_manager):
        """Test check_job_analyzed when job exists"""
        mock_cache_manager = Mock()
        mock_get_cache_manager.return_value = mock_cache_manager

        mock_cache_manager.get_job_info_async = AsyncMock(
            return_value={
                "job_id": 1001,
                "name": "test-job",
            }
        )

        result = await check_job_analyzed("test-project", "1001", "test_resource")

        assert result is None
        mock_cache_manager.get_job_info_async.assert_called_once_with(1001)

    @pytest.mark.asyncio
    @patch("gitlab_analyzer.mcp.utils.pipeline_validation.get_cache_manager")
    async def test_check_job_analyzed_not_exists(self, mock_get_cache_manager):
        """Test check_job_analyzed when job doesn't exist"""
        mock_cache_manager = Mock()
        mock_get_cache_manager.return_value = mock_cache_manager

        mock_cache_manager.get_job_info_async = AsyncMock(return_value=None)

        result = await check_job_analyzed("test-project", "1001", "test_resource")

        assert result is not None
        assert "error" in result
        assert result["error"] == "job_not_analyzed"
        assert result["job_id"] == 1001
        assert result["project_id"] == "test-project"
        assert "suggested_actions" in result
        assert "mcp_info" in result

    @pytest.mark.asyncio
    @patch("gitlab_analyzer.mcp.utils.pipeline_validation.get_cache_manager")
    async def test_check_pipeline_analyzed_custom_resource_context(
        self, mock_get_cache_manager
    ):
        """Test check_pipeline_analyzed with custom resource context"""
        mock_cache_manager = Mock()
        mock_get_cache_manager.return_value = mock_cache_manager

        mock_cache_manager.get_pipeline_info_async = AsyncMock(return_value=None)

        result = await check_pipeline_analyzed(
            "test-project", "12345", "custom_resource"
        )

        assert result is not None
        assert result["metadata"]["resource_type"] == "custom_resource"

    @pytest.mark.asyncio
    @patch("gitlab_analyzer.mcp.utils.pipeline_validation.get_cache_manager")
    async def test_check_job_analyzed_custom_resource_context(
        self, mock_get_cache_manager
    ):
        """Test check_job_analyzed with custom resource context"""
        mock_cache_manager = Mock()
        mock_get_cache_manager.return_value = mock_cache_manager

        mock_cache_manager.get_job_info_async = AsyncMock(return_value=None)

        result = await check_job_analyzed("test-project", "1001", "custom_resource")

        assert result is not None
        assert "mcp_info" in result

    @pytest.mark.asyncio
    @patch("gitlab_analyzer.mcp.utils.pipeline_validation.get_cache_manager")
    async def test_error_message_content(self, mock_get_cache_manager):
        """Test that error messages contain helpful information"""
        mock_cache_manager = Mock()
        mock_get_cache_manager.return_value = mock_cache_manager

        mock_cache_manager.get_pipeline_info_async = AsyncMock(return_value=None)

        result = await check_pipeline_analyzed(
            "test-project", "12345", "pipeline_errors"
        )

        assert "Pipeline 12345 has not been analyzed yet" in result["message"]
        assert "failed_pipeline_analysis" in result["required_action"]
        assert result["pipeline_id"] == 12345
        assert result["project_id"] == "test-project"

    @pytest.mark.asyncio
    @patch("gitlab_analyzer.mcp.utils.pipeline_validation.get_cache_manager")
    async def test_job_error_message_content(self, mock_get_cache_manager):
        """Test that job error messages contain helpful information"""
        mock_cache_manager = Mock()
        mock_get_cache_manager.return_value = mock_cache_manager

        mock_cache_manager.get_job_info_async = AsyncMock(return_value=None)

        result = await check_job_analyzed("test-project", "1001", "job_errors")

        assert "Job 1001 not found in cache" in result["message"]
        assert "analyze_job" in str(result["suggested_actions"])
        assert result["job_id"] == 1001
        assert result["project_id"] == "test-project"
