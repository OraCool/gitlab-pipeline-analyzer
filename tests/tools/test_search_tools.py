"""
Tests for search tools

Copyright (c) 2025 Siarhei Skuratovich
Licensed under the MIT License - see LICENSE file for details
"""

import json
from unittest.mock import AsyncMock, Mock, patch

import pytest

from gitlab_analyzer.mcp.tools.search_tools import register_search_tools


class TestSearchTools:
    """Test search tools"""

    @pytest.fixture
    def mock_mcp(self):
        """Mock FastMCP server"""
        mcp = Mock()
        mcp.tool = Mock()
        return mcp

    @pytest.fixture
    def mock_gitlab_analyzer(self):
        """Mock GitLab analyzer"""
        analyzer = Mock()
        analyzer.search_project_code = AsyncMock()
        analyzer.search_project_commits = AsyncMock()
        return analyzer

    @pytest.fixture
    def mock_code_search_results(self):
        """Mock code search results"""
        return [
            {
                "path": "src/main.py",
                "filename": "main.py",
                "startline": 42,
                "data": "def process_data():\n    return data",
                "ref": "main",
            },
            {
                "path": "tests/test_main.py",
                "filename": "test_main.py",
                "startline": 15,
                "data": "def test_process_data():\n    assert True",
                "ref": "main",
            },
        ]

    @pytest.fixture
    def mock_commit_search_results(self):
        """Mock commit search results"""
        return [
            {
                "id": "abc123def456789",
                "short_id": "abc123de",
                "title": "Fix data processing bug",
                "message": "Fix data processing bug\n\nResolves issue with null values",
                "author_name": "John Doe",
                "author_email": "john@example.com",
                "created_at": "2025-01-01T10:00:00Z",
                "committed_date": "2025-01-01T10:00:00Z",
            },
            {
                "id": "def456abc789123",
                "short_id": "def456ab",
                "title": "Add new feature",
                "message": "Add new feature for processing",
                "author_name": "Jane Smith",
                "author_email": "jane@example.com",
                "created_at": "2025-01-02T11:00:00Z",
                "committed_date": "2025-01-02T11:00:00Z",
            },
        ]

    def test_register_search_tools(self, mock_mcp):
        """Test search tools registration"""
        register_search_tools(mock_mcp)

        # Verify 2 tools were registered
        assert mock_mcp.tool.call_count == 2

        # Check that tools were decorated (registered)
        assert mock_mcp.tool.called

    @patch("gitlab_analyzer.mcp.tools.search_tools.get_gitlab_analyzer")
    @patch("gitlab_analyzer.mcp.tools.search_tools.get_mcp_info")
    async def test_search_repository_code_text_format(
        self,
        mock_get_mcp_info,
        mock_get_gitlab_analyzer,
        mock_mcp,
        mock_gitlab_analyzer,
        mock_code_search_results,
    ):
        """Test code search with text format output"""
        # Setup mocks
        mock_get_gitlab_analyzer.return_value = mock_gitlab_analyzer
        mock_get_mcp_info.return_value = {"tool": "search_repository_code"}
        mock_gitlab_analyzer.search_project_code.return_value = mock_code_search_results

        # Register tools
        register_search_tools(mock_mcp)

        # Find the search_repository_code function
        search_code_func = None
        for call in mock_mcp.tool.call_args_list:
            if (
                hasattr(call[0][0], "__name__")
                and call[0][0].__name__ == "search_repository_code"
            ):
                search_code_func = call[0][0]
                break

        assert search_code_func is not None

        # Test code search
        result = await search_code_func(
            project_id="123", search_keywords="process_data", output_format="text"
        )

        # Verify search was called correctly
        mock_gitlab_analyzer.search_project_code.assert_called_once_with(
            project_id="123",
            search_term="process_data",
            branch=None,
            filename_filter=None,
            path_filter=None,
            extension_filter=None,
        )

        # Verify result format
        assert isinstance(result, str)
        assert "Code Search Results" in result
        assert "process_data" in result
        assert "src/main.py" in result
        assert "Found 2 total matches" in result

    @patch("gitlab_analyzer.mcp.tools.search_tools.get_gitlab_analyzer")
    @patch("gitlab_analyzer.mcp.tools.search_tools.get_mcp_info")
    async def test_search_repository_code_json_format(
        self,
        mock_get_mcp_info,
        mock_get_gitlab_analyzer,
        mock_mcp,
        mock_gitlab_analyzer,
        mock_code_search_results,
    ):
        """Test code search with JSON format output"""
        # Setup mocks
        mock_get_gitlab_analyzer.return_value = mock_gitlab_analyzer
        mock_get_mcp_info.return_value = {"tool": "search_repository_code"}
        mock_gitlab_analyzer.search_project_code.return_value = mock_code_search_results

        # Register tools
        register_search_tools(mock_mcp)

        # Find the search_repository_code function
        search_code_func = None
        for call in mock_mcp.tool.call_args_list:
            if (
                hasattr(call[0][0], "__name__")
                and call[0][0].__name__ == "search_repository_code"
            ):
                search_code_func = call[0][0]
                break

        # Test code search with JSON output
        result = await search_code_func(
            project_id="123",
            search_keywords="async def",
            branch="feature-branch",
            extension_filter="py",
            output_format="json",
        )

        # Verify result is valid JSON
        result_data = json.loads(result)
        assert result_data["search_keywords"] == "async def"
        assert result_data["project_id"] == "123"
        assert result_data["branch"] == "feature-branch"
        assert result_data["total_results"] == 2
        assert result_data["showing_results"] == 2
        assert result_data["filters"]["extension_filter"] == "py"
        assert len(result_data["results"]) == 2
        assert "mcp_info" in result_data

        # Check first result structure
        first_result = result_data["results"][0]
        assert first_result["file"] == "src/main.py"
        assert first_result["branch"] == "main"
        assert first_result["start_line"] == 42

    @patch("gitlab_analyzer.mcp.tools.search_tools.get_gitlab_analyzer")
    @patch("gitlab_analyzer.mcp.tools.search_tools.get_mcp_info")
    async def test_search_repository_code_no_results(
        self,
        mock_get_mcp_info,
        mock_get_gitlab_analyzer,
        mock_mcp,
        mock_gitlab_analyzer,
    ):
        """Test code search with no results"""
        # Setup mocks
        mock_get_gitlab_analyzer.return_value = mock_gitlab_analyzer
        mock_get_mcp_info.return_value = {"tool": "search_repository_code"}
        mock_gitlab_analyzer.search_project_code.return_value = []

        # Register tools
        register_search_tools(mock_mcp)

        # Find the search_repository_code function
        search_code_func = None
        for call in mock_mcp.tool.call_args_list:
            if (
                hasattr(call[0][0], "__name__")
                and call[0][0].__name__ == "search_repository_code"
            ):
                search_code_func = call[0][0]
                break

        # Test code search with no results - text format
        result = await search_code_func(
            project_id="123", search_keywords="nonexistent", output_format="text"
        )

        assert "No code matches found" in result
        assert "nonexistent" in result

        # Test code search with no results - JSON format
        result = await search_code_func(
            project_id="123", search_keywords="nonexistent", output_format="json"
        )

        result_data = json.loads(result)
        assert result_data["total_results"] == 0
        assert result_data["showing_results"] == 0
        assert result_data["results"] == []
        assert "No code matches found" in result_data["message"]

    @patch("gitlab_analyzer.mcp.tools.search_tools.get_gitlab_analyzer")
    async def test_search_repository_code_error_handling(
        self,
        mock_get_gitlab_analyzer,
        mock_mcp,
        mock_gitlab_analyzer,
    ):
        """Test code search error handling"""
        # Setup error
        mock_get_gitlab_analyzer.return_value = mock_gitlab_analyzer
        mock_gitlab_analyzer.search_project_code.side_effect = Exception(
            "Search failed"
        )

        # Register tools
        register_search_tools(mock_mcp)

        # Find the search_repository_code function
        search_code_func = None
        for call in mock_mcp.tool.call_args_list:
            if (
                hasattr(call[0][0], "__name__")
                and call[0][0].__name__ == "search_repository_code"
            ):
                search_code_func = call[0][0]
                break

        # Test error handling
        result = await search_code_func(project_id="123", search_keywords="test")

        assert "Error searching repository code" in result
        assert "Search failed" in result

    @patch("gitlab_analyzer.mcp.tools.search_tools.get_gitlab_analyzer")
    @patch("gitlab_analyzer.mcp.tools.search_tools.get_mcp_info")
    async def test_search_repository_code_with_filters(
        self,
        mock_get_mcp_info,
        mock_get_gitlab_analyzer,
        mock_mcp,
        mock_gitlab_analyzer,
        mock_code_search_results,
    ):
        """Test code search with various filters"""
        # Setup mocks
        mock_get_gitlab_analyzer.return_value = mock_gitlab_analyzer
        mock_get_mcp_info.return_value = {"tool": "search_repository_code"}
        mock_gitlab_analyzer.search_project_code.return_value = mock_code_search_results

        # Register tools
        register_search_tools(mock_mcp)

        # Find the search_repository_code function
        search_code_func = None
        for call in mock_mcp.tool.call_args_list:
            if (
                hasattr(call[0][0], "__name__")
                and call[0][0].__name__ == "search_repository_code"
            ):
                search_code_func = call[0][0]
                break

        # Test with all filters
        result = await search_code_func(
            project_id="123",
            search_keywords="class",
            branch="develop",
            filename_filter="*.py",
            path_filter="src/*",
            extension_filter="py",
            max_results=10,
        )

        # Verify search was called with filters
        mock_gitlab_analyzer.search_project_code.assert_called_once_with(
            project_id="123",
            search_term="class",
            branch="develop",
            filename_filter="*.py",
            path_filter="src/*",
            extension_filter="py",
        )

        # Verify filters are mentioned in output
        assert "Filters:" in result
        assert "filename:*.py" in result
        assert "path:src/*" in result
        assert "extension:py" in result

    @patch("gitlab_analyzer.mcp.tools.search_tools.get_gitlab_analyzer")
    @patch("gitlab_analyzer.mcp.tools.search_tools.get_mcp_info")
    async def test_search_repository_code_max_results(
        self,
        mock_get_mcp_info,
        mock_get_gitlab_analyzer,
        mock_mcp,
        mock_gitlab_analyzer,
    ):
        """Test code search with max results limit"""
        # Create many results
        many_results = [
            {
                "path": f"file_{i}.py",
                "filename": f"file_{i}.py",
                "startline": i,
                "data": f"def function_{i}():\n    pass",
                "ref": "main",
            }
            for i in range(30)
        ]

        # Setup mocks
        mock_get_gitlab_analyzer.return_value = mock_gitlab_analyzer
        mock_get_mcp_info.return_value = {"tool": "search_repository_code"}
        mock_gitlab_analyzer.search_project_code.return_value = many_results

        # Register tools
        register_search_tools(mock_mcp)

        # Find the search_repository_code function
        search_code_func = None
        for call in mock_mcp.tool.call_args_list:
            if (
                hasattr(call[0][0], "__name__")
                and call[0][0].__name__ == "search_repository_code"
            ):
                search_code_func = call[0][0]
                break

        # Test with max_results limit
        result = await search_code_func(
            project_id="123", search_keywords="function", max_results=5
        )

        assert "Found 30 total matches (showing first 5)" in result
        assert "and 25 more results" in result

    @patch("gitlab_analyzer.mcp.tools.search_tools.get_gitlab_analyzer")
    @patch("gitlab_analyzer.mcp.tools.search_tools.get_mcp_info")
    async def test_search_repository_commits_text_format(
        self,
        mock_get_mcp_info,
        mock_get_gitlab_analyzer,
        mock_mcp,
        mock_gitlab_analyzer,
        mock_commit_search_results,
    ):
        """Test commit search with text format output"""
        # Setup mocks
        mock_get_gitlab_analyzer.return_value = mock_gitlab_analyzer
        mock_get_mcp_info.return_value = {"tool": "search_repository_commits"}
        mock_gitlab_analyzer.search_project_commits.return_value = (
            mock_commit_search_results
        )

        # Register tools
        register_search_tools(mock_mcp)

        # Find the search_repository_commits function
        search_commits_func = None
        for call in mock_mcp.tool.call_args_list:
            if (
                hasattr(call[0][0], "__name__")
                and call[0][0].__name__ == "search_repository_commits"
            ):
                search_commits_func = call[0][0]
                break

        assert search_commits_func is not None

        # Test commit search
        result = await search_commits_func(
            project_id="123", search_keywords="bug fix", output_format="text"
        )

        # Verify search was called correctly
        mock_gitlab_analyzer.search_project_commits.assert_called_once_with(
            project_id="123",
            search_term="bug fix",
            branch=None,
        )

        # Verify result format
        assert isinstance(result, str)
        assert "Commit Search Results" in result
        assert "bug fix" in result
        assert "abc123de" in result
        assert "Fix data processing bug" in result
        assert "John Doe" in result
        assert "Found 2 total matches" in result

    @patch("gitlab_analyzer.mcp.tools.search_tools.get_gitlab_analyzer")
    @patch("gitlab_analyzer.mcp.tools.search_tools.get_mcp_info")
    async def test_search_repository_commits_json_format(
        self,
        mock_get_mcp_info,
        mock_get_gitlab_analyzer,
        mock_mcp,
        mock_gitlab_analyzer,
        mock_commit_search_results,
    ):
        """Test commit search with JSON format output"""
        # Setup mocks
        mock_get_gitlab_analyzer.return_value = mock_gitlab_analyzer
        mock_get_mcp_info.return_value = {"tool": "search_repository_commits"}
        mock_gitlab_analyzer.search_project_commits.return_value = (
            mock_commit_search_results
        )

        # Register tools
        register_search_tools(mock_mcp)

        # Find the search_repository_commits function
        search_commits_func = None
        for call in mock_mcp.tool.call_args_list:
            if (
                hasattr(call[0][0], "__name__")
                and call[0][0].__name__ == "search_repository_commits"
            ):
                search_commits_func = call[0][0]
                break

        # Test commit search with JSON output
        result = await search_commits_func(
            project_id="123",
            search_keywords="feature",
            branch="main",
            output_format="json",
        )

        # Verify result is valid JSON
        result_data = json.loads(result)
        assert result_data["search_query"] == "feature"
        assert result_data["project_id"] == "123"
        assert result_data["branch"] == "main"
        assert result_data["total_matches"] == 2
        assert result_data["showing_results"] == 2
        assert len(result_data["commits"]) == 2
        assert "mcp_info" in result_data

        # Check first commit structure
        first_commit = result_data["commits"][0]
        assert first_commit["sha"] == "abc123def456789"
        assert first_commit["short_sha"] == "abc123de"
        assert first_commit["title"] == "Fix data processing bug"
        assert first_commit["author"]["name"] == "John Doe"
        assert first_commit["author"]["email"] == "john@example.com"

    @patch("gitlab_analyzer.mcp.tools.search_tools.get_gitlab_analyzer")
    @patch("gitlab_analyzer.mcp.tools.search_tools.get_mcp_info")
    async def test_search_repository_commits_no_results(
        self,
        mock_get_mcp_info,
        mock_get_gitlab_analyzer,
        mock_mcp,
        mock_gitlab_analyzer,
    ):
        """Test commit search with no results"""
        # Setup mocks
        mock_get_gitlab_analyzer.return_value = mock_gitlab_analyzer
        mock_get_mcp_info.return_value = {"tool": "search_repository_commits"}
        mock_gitlab_analyzer.search_project_commits.return_value = []

        # Register tools
        register_search_tools(mock_mcp)

        # Find the search_repository_commits function
        search_commits_func = None
        for call in mock_mcp.tool.call_args_list:
            if (
                hasattr(call[0][0], "__name__")
                and call[0][0].__name__ == "search_repository_commits"
            ):
                search_commits_func = call[0][0]
                break

        # Test commit search with no results - text format
        result = await search_commits_func(
            project_id="123", search_keywords="nonexistent", output_format="text"
        )

        assert "No commit matches found" in result
        assert "nonexistent" in result

        # Test commit search with no results - JSON format
        result = await search_commits_func(
            project_id="123", search_keywords="nonexistent", output_format="json"
        )

        result_data = json.loads(result)
        assert result_data["total_results"] == 0
        assert result_data["showing_results"] == 0
        assert result_data["commits"] == []
        assert "No commit matches found" in result_data["message"]

    @patch("gitlab_analyzer.mcp.tools.search_tools.get_gitlab_analyzer")
    async def test_search_repository_commits_error_handling(
        self,
        mock_get_gitlab_analyzer,
        mock_mcp,
        mock_gitlab_analyzer,
    ):
        """Test commit search error handling"""
        # Setup error
        mock_get_gitlab_analyzer.return_value = mock_gitlab_analyzer
        mock_gitlab_analyzer.search_project_commits.side_effect = Exception(
            "Commit search failed"
        )

        # Register tools
        register_search_tools(mock_mcp)

        # Find the search_repository_commits function
        search_commits_func = None
        for call in mock_mcp.tool.call_args_list:
            if (
                hasattr(call[0][0], "__name__")
                and call[0][0].__name__ == "search_repository_commits"
            ):
                search_commits_func = call[0][0]
                break

        # Test error handling
        result = await search_commits_func(project_id="123", search_keywords="test")

        assert "Error searching repository commits" in result
        assert "Commit search failed" in result

    @patch("gitlab_analyzer.mcp.tools.search_tools.get_gitlab_analyzer")
    @patch("gitlab_analyzer.mcp.tools.search_tools.get_mcp_info")
    async def test_search_repository_commits_max_results(
        self,
        mock_get_mcp_info,
        mock_get_gitlab_analyzer,
        mock_mcp,
        mock_gitlab_analyzer,
    ):
        """Test commit search with max results limit"""
        # Create many commit results
        many_commits = [
            {
                "id": f"commit{i:03d}",
                "short_id": f"commit{i:03d}"[:8],
                "title": f"Commit {i}",
                "message": f"Commit message {i}",
                "author_name": f"Author {i}",
                "author_email": f"author{i}@example.com",
                "created_at": "2025-01-01T10:00:00Z",
                "committed_date": "2025-01-01T10:00:00Z",
            }
            for i in range(25)
        ]

        # Setup mocks
        mock_get_gitlab_analyzer.return_value = mock_gitlab_analyzer
        mock_get_mcp_info.return_value = {"tool": "search_repository_commits"}
        mock_gitlab_analyzer.search_project_commits.return_value = many_commits

        # Register tools
        register_search_tools(mock_mcp)

        # Find the search_repository_commits function
        search_commits_func = None
        for call in mock_mcp.tool.call_args_list:
            if (
                hasattr(call[0][0], "__name__")
                and call[0][0].__name__ == "search_repository_commits"
            ):
                search_commits_func = call[0][0]
                break

        # Test with max_results limit
        result = await search_commits_func(
            project_id="123", search_keywords="commit", max_results=10
        )

        assert "Found 25 total matches (showing first 10)" in result
        assert "and 15 more results" in result

    @patch("gitlab_analyzer.mcp.tools.search_tools.get_gitlab_analyzer")
    @patch("gitlab_analyzer.mcp.tools.search_tools.get_mcp_info")
    async def test_search_repository_commits_with_branch(
        self,
        mock_get_mcp_info,
        mock_get_gitlab_analyzer,
        mock_mcp,
        mock_gitlab_analyzer,
        mock_commit_search_results,
    ):
        """Test commit search with specific branch"""
        # Setup mocks
        mock_get_gitlab_analyzer.return_value = mock_gitlab_analyzer
        mock_get_mcp_info.return_value = {"tool": "search_repository_commits"}
        mock_gitlab_analyzer.search_project_commits.return_value = (
            mock_commit_search_results
        )

        # Register tools
        register_search_tools(mock_mcp)

        # Find the search_repository_commits function
        search_commits_func = None
        for call in mock_mcp.tool.call_args_list:
            if (
                hasattr(call[0][0], "__name__")
                and call[0][0].__name__ == "search_repository_commits"
            ):
                search_commits_func = call[0][0]
                break

        # Test with specific branch
        result = await search_commits_func(
            project_id="123", search_keywords="fix", branch="develop"
        )

        # Verify search was called with branch
        mock_gitlab_analyzer.search_project_commits.assert_called_once_with(
            project_id="123",
            search_term="fix",
            branch="develop",
        )

        # Verify branch is mentioned in output
        assert "Branch: develop" in result
