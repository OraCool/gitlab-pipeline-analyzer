"""
Tests for GitLab API client merge request overview functionality

Copyright (c) 2025 Siarhei Skuratovich
Licensed under the MIT License - see LICENSE file for details
"""

from unittest.mock import AsyncMock, Mock, patch

import httpx
import pytest

from gitlab_analyzer.api.client import GitLabAnalyzer


class TestGitLabAnalyzerMROverview:
    """Test GitLab analyzer MR overview functionality"""

    @pytest.fixture
    def analyzer(self):
        """Create GitLab analyzer instance"""
        return GitLabAnalyzer("https://gitlab.example.com", "token123")

    @pytest.fixture
    def mock_mr_data(self):
        """Mock merge request data from GitLab API"""
        return {
            "iid": 123,
            "title": "Fix critical bug in authentication",
            "description": "This MR fixes PROJ-456 authentication issue\n\nAlso addresses TEST-789",
            "author": {
                "name": "John Doe",
                "username": "john.doe",
                "web_url": "https://gitlab.example.com/john.doe",
            },
            "state": "opened",
            "web_url": "https://gitlab.example.com/project/merge_requests/123",
            "source_branch": "feature/auth-fix",
            "target_branch": "main",
            "labels": ["bug", "TASK-111"],
            "milestone": {"title": "Sprint 10", "id": 42},
            "created_at": "2025-01-01T10:00:00Z",
            "updated_at": "2025-01-01T12:00:00Z",
        }

    @pytest.mark.asyncio
    async def test_get_merge_request_overview_success(self, analyzer, mock_mr_data):
        """Test successful MR overview retrieval"""
        with patch.object(
            analyzer, "get_merge_request", new_callable=AsyncMock
        ) as mock_get_mr:
            mock_get_mr.return_value = mock_mr_data

            result = await analyzer.get_merge_request_overview(83, 123)

            # Verify the method was called correctly
            mock_get_mr.assert_called_once_with(83, 123)

            # Verify the returned structure
            assert result["iid"] == 123
            assert result["title"] == "Fix critical bug in authentication"
            assert (
                result["description"]
                == "This MR fixes PROJ-456 authentication issue\n\nAlso addresses TEST-789"
            )
            assert result["author"]["name"] == "John Doe"
            assert result["author"]["username"] == "john.doe"
            assert result["state"] == "opened"
            assert (
                result["web_url"]
                == "https://gitlab.example.com/project/merge_requests/123"
            )
            assert result["source_branch"] == "feature/auth-fix"
            assert result["target_branch"] == "main"
            assert result["labels"] == ["bug", "TASK-111"]
            assert result["milestone"]["title"] == "Sprint 10"

    @pytest.mark.asyncio
    async def test_get_merge_request_overview_minimal_data(self, analyzer):
        """Test MR overview with minimal data"""
        minimal_mr_data = {"iid": 456, "title": "Simple fix"}

        with patch.object(
            analyzer, "get_merge_request", new_callable=AsyncMock
        ) as mock_get_mr:
            mock_get_mr.return_value = minimal_mr_data

            result = await analyzer.get_merge_request_overview(83, 456)

            # Verify required fields are present with defaults
            assert result["iid"] == 456
            assert result["title"] == "Simple fix"
            assert result["description"] == ""
            assert result["author"]["name"] == ""
            assert result["author"]["username"] == ""
            assert result["state"] == ""
            assert result["web_url"] == ""
            assert result["source_branch"] == ""
            assert result["target_branch"] == ""
            assert result["labels"] == []
            assert result["milestone"] is None

    @pytest.mark.asyncio
    async def test_get_merge_request_overview_http_error(self, analyzer):
        """Test MR overview when HTTP error occurs"""
        with patch.object(
            analyzer, "get_merge_request", new_callable=AsyncMock
        ) as mock_get_mr:
            mock_get_mr.side_effect = httpx.HTTPStatusError(
                "404 Not Found", request=Mock(), response=Mock(status_code=404)
            )

            with pytest.raises(httpx.HTTPStatusError):
                await analyzer.get_merge_request_overview(83, 999)

    @pytest.mark.asyncio
    async def test_get_merge_request_overview_request_error(self, analyzer):
        """Test MR overview when network error occurs"""
        with patch.object(
            analyzer, "get_merge_request", new_callable=AsyncMock
        ) as mock_get_mr:
            mock_get_mr.side_effect = httpx.RequestError("Network error")

            with pytest.raises(httpx.RequestError):
                await analyzer.get_merge_request_overview(83, 123)

    @pytest.mark.asyncio
    async def test_get_merge_request_overview_none_values(self, analyzer):
        """Test MR overview with None values in data"""
        mr_data_with_nones = {
            "iid": 789,
            "title": None,
            "description": None,
            "author": None,
            "state": None,
            "web_url": None,
            "source_branch": None,
            "target_branch": None,
            "labels": None,
            "milestone": None,
            "created_at": None,
            "updated_at": None,
        }

        with patch.object(
            analyzer, "get_merge_request", new_callable=AsyncMock
        ) as mock_get_mr:
            mock_get_mr.return_value = mr_data_with_nones

            result = await analyzer.get_merge_request_overview(83, 789)

            # Verify None values are handled gracefully
            assert result["iid"] == 789
            assert result["title"] == ""  # None converted to empty string
            assert result["description"] == ""
            assert result["author"]["name"] == ""
            assert result["author"]["username"] == ""
            assert result["author"]["web_url"] == ""
            assert result["state"] == ""
            assert result["web_url"] == ""
            assert result["source_branch"] == ""
            assert result["target_branch"] == ""
            assert result["labels"] == []
            assert result["milestone"] is None

    @pytest.mark.asyncio
    async def test_get_merge_request_overview_empty_author(self, analyzer):
        """Test MR overview with empty author object"""
        mr_data = {"iid": 101, "title": "Test MR", "author": {}}  # Empty author object

        with patch.object(
            analyzer, "get_merge_request", new_callable=AsyncMock
        ) as mock_get_mr:
            mock_get_mr.return_value = mr_data

            result = await analyzer.get_merge_request_overview(83, 101)

            assert result["author"]["name"] == ""
            assert result["author"]["username"] == ""
            assert result["author"]["web_url"] == ""

    @pytest.mark.asyncio
    async def test_get_merge_request_overview_project_id_types(
        self, analyzer, mock_mr_data
    ):
        """Test MR overview with different project ID types"""
        with patch.object(
            analyzer, "get_merge_request", new_callable=AsyncMock
        ) as mock_get_mr:
            mock_get_mr.return_value = mock_mr_data

            # Test with integer project ID
            await analyzer.get_merge_request_overview(83, 123)
            mock_get_mr.assert_called_with(83, 123)

            # Test with string project ID
            await analyzer.get_merge_request_overview("83", 123)
            mock_get_mr.assert_called_with("83", 123)

            # Test with project path
            await analyzer.get_merge_request_overview("group/project", 123)
            mock_get_mr.assert_called_with("group/project", 123)
