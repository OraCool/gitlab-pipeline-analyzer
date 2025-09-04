"""
Test pipeline MR data filtering based on pipeline type.

This module tests that merge request related fields (merge_request, jira_tickets)
are only included in responses when the pipeline is actually a merge request pipeline.
"""

from unittest.mock import patch

import pytest

from gitlab_analyzer.cache.mcp_cache import McpCache
from gitlab_analyzer.mcp.resources.pipeline import get_pipeline_resource


class TestPipelineMRFiltering:
    """Test MR data filtering based on pipeline type"""

    @pytest.mark.asyncio
    async def test_merge_request_pipeline_includes_mr_data(self):
        """Test that MR pipeline includes MR and Jira data"""

        # Mock database data for an MR pipeline
        mock_pipeline_data = {
            "pipeline_id": 123,
            "project_id": 83,
            "ref": "refs/merge-requests/456/merge",  # MR pipeline
            "sha": "abc123",
            "status": "failed",
            "web_url": "https://gitlab.example.com/pipeline/123",
            "created_at": "2025-09-04T14:17:56.784Z",
            "updated_at": "2025-09-04T14:24:44.909Z",
            "source_branch": "feature-branch",
            "target_branch": "main",
            # MR data fields
            "mr_iid": 456,
            "mr_title": "TEST-123: Sample MR",
            "mr_description": "Test description with PROJ-456",
            "mr_author": "test.user",
            "mr_web_url": "https://gitlab.example.com/mr/456",
            "jira_tickets": '["TEST-123", "PROJ-456"]',
        }

        with patch.object(McpCache, "get_pipeline_info_async") as mock_get_pipeline:
            mock_get_pipeline.return_value = mock_pipeline_data

            with patch.object(McpCache, "get_pipeline_jobs") as mock_get_jobs:
                mock_get_jobs.return_value = []

                with patch.object(McpCache, "get_or_compute") as mock_cache:
                    # Make cache return the computed result directly
                    async def side_effect(key, compute_func, **kwargs):
                        return await compute_func()

                    mock_cache.side_effect = side_effect

                    result = await get_pipeline_resource("83", "123")

        # Verify MR pipeline includes MR data
        assert "merge_request" in result
        assert "jira_tickets" in result

        # Verify MR data content
        assert result["merge_request"]["iid"] == 456
        assert result["merge_request"]["title"] == "TEST-123: Sample MR"
        assert result["jira_tickets"] == ["TEST-123", "PROJ-456"]

        # Verify pipeline type
        assert result["pipeline_info"]["pipeline_type"] == "merge_request"

    @pytest.mark.asyncio
    async def test_branch_pipeline_excludes_mr_data(self):
        """Test that branch pipeline excludes MR and Jira data"""

        # Mock database data for a branch pipeline
        mock_pipeline_data = {
            "pipeline_id": 124,
            "project_id": 83,
            "ref": "main",  # Branch pipeline, not MR
            "sha": "def456",
            "status": "failed",
            "web_url": "https://gitlab.example.com/pipeline/124",
            "created_at": "2025-09-04T15:17:56.784Z",
            "updated_at": "2025-09-04T15:24:44.909Z",
            "source_branch": None,
            "target_branch": None,
            # These MR fields might exist in DB but shouldn't be included
            "mr_iid": None,
            "mr_title": None,
            "mr_description": None,
            "mr_author": None,
            "mr_web_url": None,
            "jira_tickets": None,
        }

        with patch.object(McpCache, "get_pipeline_info_async") as mock_get_pipeline:
            mock_get_pipeline.return_value = mock_pipeline_data

            with patch.object(McpCache, "get_pipeline_jobs") as mock_get_jobs:
                mock_get_jobs.return_value = []

                with patch.object(McpCache, "get_or_compute") as mock_cache:
                    # Make cache return the computed result directly
                    async def side_effect(key, compute_func, **kwargs):
                        return await compute_func()

                    mock_cache.side_effect = side_effect

                    result = await get_pipeline_resource("83", "124")

        # Verify branch pipeline excludes MR data
        assert "merge_request" not in result
        assert "jira_tickets" not in result

        # Verify pipeline type
        assert result["pipeline_info"]["pipeline_type"] == "branch"

    @pytest.mark.asyncio
    async def test_branch_pipeline_with_populated_mr_fields_still_excludes_mr_data(
        self,
    ):
        """Test that even if DB has MR data, branch pipeline still excludes it"""

        # Mock database data for a branch pipeline that somehow has MR data
        # (this could happen due to data inconsistency or migration issues)
        mock_pipeline_data = {
            "pipeline_id": 125,
            "project_id": 83,
            "ref": "develop",  # Branch pipeline, not MR
            "sha": "ghi789",
            "status": "failed",
            "web_url": "https://gitlab.example.com/pipeline/125",
            "created_at": "2025-09-04T16:17:56.784Z",
            "updated_at": "2025-09-04T16:24:44.909Z",
            "source_branch": None,
            "target_branch": None,
            # These MR fields exist but should NOT be included for branch pipeline
            "mr_iid": 789,
            "mr_title": "Stale MR Data",
            "mr_description": "This should not appear",
            "mr_author": "stale.user",
            "mr_web_url": "https://gitlab.example.com/mr/789",
            "jira_tickets": '["STALE-123"]',
        }

        with patch.object(McpCache, "get_pipeline_info_async") as mock_get_pipeline:
            mock_get_pipeline.return_value = mock_pipeline_data

            with patch.object(McpCache, "get_pipeline_jobs") as mock_get_jobs:
                mock_get_jobs.return_value = []

                with patch.object(McpCache, "get_or_compute") as mock_cache:
                    # Make cache return the computed result directly
                    async def side_effect(key, compute_func, **kwargs):
                        return await compute_func()

                    mock_cache.side_effect = side_effect

                    result = await get_pipeline_resource("83", "125")

        # Verify branch pipeline excludes MR data even when DB has it
        assert "merge_request" not in result
        assert "jira_tickets" not in result

        # Verify pipeline type is correctly identified as branch
        assert result["pipeline_info"]["pipeline_type"] == "branch"
        assert result["pipeline_info"]["ref"] == "develop"

    @pytest.mark.asyncio
    async def test_merge_request_pipeline_without_mr_data_excludes_fields(self):
        """Test that MR pipeline without MR data doesn't include empty fields"""

        # Mock database data for an MR pipeline without MR data populated
        mock_pipeline_data = {
            "pipeline_id": 126,
            "project_id": 83,
            "ref": "refs/merge-requests/999/merge",  # MR pipeline
            "sha": "jkl012",
            "status": "failed",
            "web_url": "https://gitlab.example.com/pipeline/126",
            "created_at": "2025-09-04T17:17:56.784Z",
            "updated_at": "2025-09-04T17:24:44.909Z",
            "source_branch": "feature-incomplete",
            "target_branch": "main",
            # MR fields are None/empty
            "mr_iid": None,
            "mr_title": None,
            "mr_description": None,
            "mr_author": None,
            "mr_web_url": None,
            "jira_tickets": None,
        }

        with patch.object(McpCache, "get_pipeline_info_async") as mock_get_pipeline:
            mock_get_pipeline.return_value = mock_pipeline_data

            with patch.object(McpCache, "get_pipeline_jobs") as mock_get_jobs:
                mock_get_jobs.return_value = []

                with patch.object(McpCache, "get_or_compute") as mock_cache:
                    # Make cache return the computed result directly
                    async def side_effect(key, compute_func, **kwargs):
                        return await compute_func()

                    mock_cache.side_effect = side_effect

                    result = await get_pipeline_resource("83", "126")

        # Verify MR pipeline without data doesn't include empty MR fields
        assert "merge_request" not in result
        assert "jira_tickets" not in result

        # Verify pipeline type is correctly identified as MR
        assert result["pipeline_info"]["pipeline_type"] == "merge_request"
        assert result["pipeline_info"]["ref"] == "refs/merge-requests/999/merge"
