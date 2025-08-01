"""
Tests for GitLab API client

Copyright (c) 2025 Siarhei Skuratovich
Licensed under the MIT License - see LICENSE file for details
"""

from unittest.mock import AsyncMock, Mock, patch

import httpx
import pytest

from gitlab_analyzer.api.client import GitLabAnalyzer
from gitlab_analyzer.models import JobInfo


class TestGitLabAnalyzer:
    """Test GitLab API client functionality"""

    def setup_method(self):
        """Set up test fixtures"""
        self.gitlab_url = "https://gitlab.example.com"
        self.token = "test-token-123"
        self.analyzer = GitLabAnalyzer(self.gitlab_url, self.token)

    def test_init(self):
        """Test GitLab analyzer initialization"""
        assert self.analyzer.gitlab_url == "https://gitlab.example.com"
        assert self.analyzer.token == "test-token-123"
        assert self.analyzer.api_url == "https://gitlab.example.com/api/v4"
        assert self.analyzer.headers["Authorization"] == "Bearer test-token-123"
        assert self.analyzer.headers["Content-Type"] == "application/json"

    def test_init_strips_trailing_slash(self):
        """Test that trailing slash is stripped from GitLab URL"""
        analyzer = GitLabAnalyzer("https://gitlab.example.com/", "token")
        assert analyzer.gitlab_url == "https://gitlab.example.com"
        assert analyzer.api_url == "https://gitlab.example.com/api/v4"

    @pytest.mark.asyncio
    async def test_get_pipeline_success(self):
        """Test successful pipeline retrieval"""
        mock_response_data = {
            "id": 12345,
            "status": "failed",
            "ref": "main",
            "sha": "abc123",
        }

        with patch("httpx.AsyncClient") as mock_client:
            mock_response = Mock()
            mock_response.json.return_value = mock_response_data
            mock_response.raise_for_status.return_value = None

            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response
            )

            result = await self.analyzer.get_pipeline("test-project", 12345)

            assert result == mock_response_data
            mock_client.return_value.__aenter__.return_value.get.assert_called_once_with(
                "https://gitlab.example.com/api/v4/projects/test-project/pipelines/12345",
                headers=self.analyzer.headers,
            )

    @pytest.mark.asyncio
    async def test_get_pipeline_http_error(self):
        """Test pipeline retrieval with HTTP error"""
        with patch("httpx.AsyncClient") as mock_client:
            mock_response = Mock()
            mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
                "404 Not Found", request=Mock(), response=Mock()
            )

            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response
            )

            with pytest.raises(httpx.HTTPStatusError):
                await self.analyzer.get_pipeline("test-project", 12345)

    @pytest.mark.asyncio
    async def test_get_pipeline_jobs_success(self):
        """Test successful pipeline jobs retrieval"""
        mock_jobs_data = [
            {
                "id": 1001,
                "name": "test-job",
                "status": "failed",
                "stage": "test",
                "created_at": "2025-01-01T10:00:00.000Z",
                "started_at": "2025-01-01T10:01:00.000Z",
                "finished_at": "2025-01-01T10:05:00.000Z",
                "duration": 240.0,
                "web_url": "https://gitlab.example.com/project/-/jobs/1001",
            }
        ]

        with patch("httpx.AsyncClient") as mock_client:
            mock_response = Mock()
            mock_response.json.return_value = mock_jobs_data
            mock_response.raise_for_status.return_value = None

            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response
            )

            result = await self.analyzer.get_pipeline_jobs("test-project", 12345)

            assert len(result) == 1
            assert isinstance(result[0], JobInfo)
            assert result[0].id == 1001
            assert result[0].name == "test-job"
            assert result[0].status == "failed"

    @pytest.mark.asyncio
    async def test_get_failed_pipeline_jobs_success(self):
        """Test successful failed jobs retrieval"""
        mock_jobs_data = [
            {
                "id": 1001,
                "name": "test-job",
                "status": "failed",
                "stage": "test",
                "created_at": "2025-01-01T10:00:00.000Z",
                "started_at": "2025-01-01T10:01:00.000Z",
                "finished_at": "2025-01-01T10:05:00.000Z",
                "failure_reason": "script_failure",
                "web_url": "https://gitlab.example.com/project/-/jobs/1001",
            }
        ]

        with patch("httpx.AsyncClient") as mock_client:
            mock_response = Mock()
            mock_response.json.return_value = mock_jobs_data
            mock_response.raise_for_status.return_value = None

            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response
            )

            result = await self.analyzer.get_failed_pipeline_jobs("test-project", 12345)

            # Should only return failed jobs
            assert len(result) == 1
            assert isinstance(result[0], JobInfo)
            assert result[0].id == 1001
            assert result[0].status == "failed"
            assert result[0].failure_reason == "script_failure"

    @pytest.mark.asyncio
    async def test_get_job_trace_success(self):
        """Test successful job trace retrieval"""
        mock_trace = (
            "Sample job trace output\nwith multiple lines\nERROR: Something failed"
        )

        with patch("httpx.AsyncClient") as mock_client:
            mock_response = Mock()
            mock_response.text = mock_trace
            mock_response.raise_for_status.return_value = None

            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response
            )

            result = await self.analyzer.get_job_trace("test-project", 1001)

            assert result == mock_trace
            mock_client.return_value.__aenter__.return_value.get.assert_called_once_with(
                "https://gitlab.example.com/api/v4/projects/test-project/jobs/1001/trace",
                headers=self.analyzer.headers,
            )

    @pytest.mark.asyncio
    async def test_timeout_configuration(self):
        """Test that HTTP client is configured with correct timeout"""
        with patch("httpx.AsyncClient") as mock_client:
            mock_response = Mock()
            mock_response.json.return_value = {}
            mock_response.raise_for_status.return_value = None

            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response
            )

            await self.analyzer.get_pipeline("test-project", 12345)

            # Verify AsyncClient was called with timeout=30.0
            mock_client.assert_called_with(timeout=30.0)
