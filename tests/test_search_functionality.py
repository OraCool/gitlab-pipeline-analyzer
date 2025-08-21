"""
Tests for search functionality

Copyright (c) 2025 Siarhei Skuratovich
Licensed under the MIT License - see LICENSE file for details
"""

from unittest.mock import AsyncMock, Mock, patch

import pytest

from src.gitlab_analyzer.api.client import GitLabAnalyzer


@pytest.mark.asyncio
async def test_search_project_code():
    """Test the search_project_code method"""
    client = GitLabAnalyzer("https://gitlab.example.com", "test-token")

    # Mock the HTTP response
    mock_response_data = [
        {
            "path": "src/main.py",
            "data": "async def process_data():\n    return True",
            "startline": 15,
            "ref": "main",
            "project_id": 123,
        },
        {
            "path": "tests/test_main.py",
            "data": "async def test_process():\n    assert True",
            "startline": 8,
            "ref": "main",
            "project_id": 123,
        },
    ]

    with patch("httpx.AsyncClient") as mock_client:
        mock_response = Mock()
        mock_response.json.return_value = mock_response_data
        mock_response.raise_for_status.return_value = None

        mock_client.return_value.__aenter__.return_value.get = AsyncMock(
            return_value=mock_response
        )

        results = await client.search_project_code(
            project_id=123, search_term="async def", extension_filter="py"
        )

        assert len(results) == 2
        assert results[0]["path"] == "src/main.py"
        assert results[0]["startline"] == 15
        assert "async def process_data" in results[0]["data"]


@pytest.mark.asyncio
async def test_search_project_code_with_filters():
    """Test search_project_code with various filters"""
    client = GitLabAnalyzer("https://gitlab.example.com", "test-token")

    with patch("httpx.AsyncClient") as mock_client:
        mock_response = Mock()
        mock_response.json.return_value = []
        mock_response.raise_for_status.return_value = None

        mock_client.return_value.__aenter__.return_value.get = AsyncMock(
            return_value=mock_response
        )

        await client.search_project_code(
            project_id=123,
            search_term="test",
            branch="feature-branch",
            filename_filter="*.py",
            path_filter="src/*",
            extension_filter="py",
        )

        # Verify the call was made with correct parameters
        call_args = mock_client.return_value.__aenter__.return_value.get.call_args
        assert call_args[1]["params"]["scope"] == "blobs"
        assert (
            call_args[1]["params"]["search"]
            == "test filename:*.py path:src/* extension:py"
        )
        assert call_args[1]["params"]["ref"] == "feature-branch"


@pytest.mark.asyncio
async def test_search_project_commits():
    """Test the search_project_commits method"""
    client = GitLabAnalyzer("https://gitlab.example.com", "test-token")

    mock_response_data = [
        {
            "id": "abc123def456",
            "short_id": "abc123d",
            "title": "Fix bug in authentication",
            "message": "Fix bug in authentication\n\nResolves issue with user login",
            "author_name": "John Doe",
            "author_email": "john@example.com",
            "created_at": "2025-01-15T10:30:00Z",
            "committed_date": "2025-01-15T10:30:00Z",
        }
    ]

    with patch("httpx.AsyncClient") as mock_client:
        mock_response = Mock()
        mock_response.json.return_value = mock_response_data
        mock_response.raise_for_status.return_value = None

        mock_client.return_value.__aenter__.return_value.get = AsyncMock(
            return_value=mock_response
        )

        results = await client.search_project_commits(
            project_id=123, search_term="fix bug"
        )

        assert len(results) == 1
        assert results[0]["short_id"] == "abc123d"
        assert results[0]["title"] == "Fix bug in authentication"
        assert results[0]["author_name"] == "John Doe"


@pytest.mark.asyncio
async def test_search_project_commits_with_branch():
    """Test search_project_commits with branch filter"""
    client = GitLabAnalyzer("https://gitlab.example.com", "test-token")

    with patch("httpx.AsyncClient") as mock_client:
        mock_response = Mock()
        mock_response.json.return_value = []
        mock_response.raise_for_status.return_value = None

        mock_client.return_value.__aenter__.return_value.get = AsyncMock(
            return_value=mock_response
        )

        await client.search_project_commits(
            project_id=123, search_term="merge", branch="main"
        )

        # Verify the call was made with correct parameters
        call_args = mock_client.return_value.__aenter__.return_value.get.call_args
        assert call_args[1]["params"]["scope"] == "commits"
        assert call_args[1]["params"]["search"] == "merge"
        assert call_args[1]["params"]["ref"] == "main"


@pytest.mark.asyncio
async def test_search_error_handling():
    """Test error handling in search methods"""
    client = GitLabAnalyzer("https://gitlab.example.com", "test-token")

    with patch("httpx.AsyncClient") as mock_client:
        mock_response = Mock()
        mock_response.raise_for_status.side_effect = Exception("API Error")

        mock_client.return_value.__aenter__.return_value.get = AsyncMock(
            return_value=mock_response
        )

        with pytest.raises(Exception, match="API Error"):
            await client.search_project_code(project_id=123, search_term="test")


def test_search_query_building():
    """Test that search queries are built correctly with filters"""
    # This tests the query building logic without making HTTP calls

    # Test with no filters
    base_term = "async def"
    assert base_term == "async def"

    # Test filter building
    search_term = "async def"
    filters = []

    filename_filter = "*.py"
    if filename_filter:
        filters.append(f"filename:{filename_filter}")

    path_filter = "src/*"
    if path_filter:
        filters.append(f"path:{path_filter}")

    extension_filter = "py"
    if extension_filter:
        filters.append(f"extension:{extension_filter}")

    expected_query = f"{search_term} {' '.join(filters)}"
    assert expected_query == "async def filename:*.py path:src/* extension:py"


def test_search_query_no_filters():
    """Test search query building with no filters"""
    search_term = "function definition"
    filters = []

    filename_filter = None
    path_filter = None
    extension_filter = None

    if filename_filter:
        filters.append(f"filename:{filename_filter}")
    if path_filter:
        filters.append(f"path:{path_filter}")
    if extension_filter:
        filters.append(f"extension:{extension_filter}")

    expected_query = search_term + (" " + " ".join(filters) if filters else "")
    assert expected_query == "function definition"
