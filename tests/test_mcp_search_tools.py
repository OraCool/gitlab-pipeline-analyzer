"""
Unit tests for MCP search tools.

Copyright (c) 2025 Siarhei Skuratovich
Licensed under the MIT License - see LICENSE file for details
"""

from unittest.mock import AsyncMock, patch

import pytest
from fastmcp import FastMCP

from gitlab_analyzer.mcp.tools.search_tools import register_search_tools


class TestSearchTools:
    """Test MCP search tools."""

    @pytest.fixture
    def mcp_server(self):
        """Create FastMCP server with search tools."""
        mcp = FastMCP("test")
        register_search_tools(mcp)
        return mcp

    @pytest.fixture
    def mock_analyzer(self):
        """Mock GitLab analyzer."""
        analyzer = AsyncMock()
        return analyzer

    @pytest.mark.asyncio
    async def test_search_repository_code_success(self, mcp_server):
        """Test successful code search"""
        mock_response_data = [
            {
                "path": "src/main.py",
                "data": "async def process_data():\\n    return True",
                "startline": 15,
                "ref": "main",
                "project_id": 123,
            },
            {
                "path": "tests/test_main.py",
                "data": "async def test_process():\\n    assert True",
                "startline": 8,
                "ref": "main",
                "project_id": 123,
            },
        ]

        with patch(
            "gitlab_analyzer.mcp.tools.search_tools.get_gitlab_analyzer"
        ) as mock_get_client:
            mock_client = AsyncMock()
            mock_client.search_project_code.return_value = mock_response_data
            mock_get_client.return_value = mock_client

            # Get the tool function
            tool_func = None
            for tool in list((await mcp_server.get_tools()).values()):
                if tool.name == "search_repository_code":
                    tool_func = tool.fn
                    break

            assert tool_func is not None

            # Execute tool
            result = await tool_func(
                project_id=123,
                search_keywords="async def",
                extension_filter="py",
                max_results=10,
            )

            assert "Code Search Results for 'async def'" in result
            assert "Found 2 total matches" in result
            assert "src/main.py" in result
            assert "tests/test_main.py" in result
            assert "Line: 15" in result
            assert "extension:py" in result

            mock_client.search_project_code.assert_called_once_with(
                project_id=123,
                search_term="async def",
                branch=None,
                filename_filter=None,
                path_filter=None,
                extension_filter="py",
            )

    @pytest.mark.asyncio
    async def test_search_repository_code_with_all_filters(self, mcp_server):
        """Test code search with all possible filters"""
        mock_response_data = [
            {
                "path": "src/models/user.py",
                "data": "class User:\\n    pass",
                "startline": 1,
                "ref": "feature-branch",
                "project_id": 456,
            }
        ]

        with patch(
            "gitlab_analyzer.mcp.tools.search_tools.get_gitlab_analyzer"
        ) as mock_get_client:
            mock_client = AsyncMock()
            mock_client.search_project_code.return_value = mock_response_data
            mock_get_client.return_value = mock_client

            # Get the tool function
            tool_func = None
            for tool in list((await mcp_server.get_tools()).values()):
                if tool.name == "search_repository_code":
                    tool_func = tool.fn
                    break

            assert tool_func is not None

            # Execute tool
            result = await tool_func(
                project_id="my-project",
                search_keywords="class User",
                branch="feature-branch",
                filename_filter="*.py",
                path_filter="src/*",
                extension_filter="py",
                max_results=5,
            )

            assert "Code Search Results for 'class User'" in result
            assert "Branch: feature-branch" in result
            assert "filename:*.py" in result
            assert "path:src/*" in result
            assert "extension:py" in result
            assert "src/models/user.py" in result

            mock_client.search_project_code.assert_called_once_with(
                project_id="my-project",
                search_term="class User",
                branch="feature-branch",
                filename_filter="*.py",
                path_filter="src/*",
                extension_filter="py",
            )

    @pytest.mark.asyncio
    async def test_search_repository_code_no_results(self, mcp_server):
        """Test code search with no results"""
        with patch(
            "gitlab_analyzer.mcp.tools.search_tools.get_gitlab_analyzer"
        ) as mock_get_client:
            mock_client = AsyncMock()
            mock_client.search_project_code.return_value = []
            mock_get_client.return_value = mock_client

            # Get the tool function
            tool_func = None
            for tool in list((await mcp_server.get_tools()).values()):
                if tool.name == "search_repository_code":
                    tool_func = tool.fn
                    break

            assert tool_func is not None

            # Execute tool
            result = await tool_func(
                project_id=123, search_keywords="nonexistent function", branch="main"
            )

            assert "No code matches found for 'nonexistent function'" in result
            assert "on branch 'main'" in result

    @pytest.mark.asyncio
    async def test_search_repository_code_error_handling(self, mcp_server):
        """Test code search error handling"""
        with patch(
            "gitlab_analyzer.mcp.tools.search_tools.get_gitlab_analyzer"
        ) as mock_get_client:
            mock_client = AsyncMock()
            mock_client.search_project_code.side_effect = Exception("API Error")
            mock_get_client.return_value = mock_client

            # Get the tool function
            tool_func = None
            for tool in list((await mcp_server.get_tools()).values()):
                if tool.name == "search_repository_code":
                    tool_func = tool.fn
                    break

            assert tool_func is not None

            # Execute tool
            result = await tool_func(project_id=123, search_keywords="test")

            assert "Error searching repository code: API Error" in result

    @pytest.mark.asyncio
    async def test_search_repository_code_limit_results(self, mcp_server):
        """Test code search result limiting"""
        # Create more results than max_results
        mock_response_data = [
            {
                "path": f"file_{i}.py",
                "data": f"def function_{i}():\\n    pass",
                "startline": 1,
                "ref": "main",
                "project_id": 123,
            }
            for i in range(25)
        ]

        with patch(
            "gitlab_analyzer.mcp.tools.search_tools.get_gitlab_analyzer"
        ) as mock_get_client:
            mock_client = AsyncMock()
            mock_client.search_project_code.return_value = mock_response_data
            mock_get_client.return_value = mock_client

            # Get the tool function
            tool_func = None
            for tool in list((await mcp_server.get_tools()).values()):
                if tool.name == "search_repository_code":
                    tool_func = tool.fn
                    break

            assert tool_func is not None

            # Execute tool
            result = await tool_func(
                project_id=123, search_keywords="def function", max_results=10
            )

            assert "Found 25 total matches (showing first 10)" in result
            assert "... and 15 more results" in result
            assert "Use max_results parameter to see more results" in result

            # Check that only 10 results are shown
            assert result.count("📄 Result") == 10

    @pytest.mark.asyncio
    async def test_search_repository_commits_success(self, mcp_server):
        """Test successful commit search"""
        mock_response_data = [
            {
                "id": "abc123def456",
                "short_id": "abc123d",
                "title": "Fix bug in authentication",
                "message": "Fix bug in authentication\\n\\nResolves issue with user login",
                "author_name": "John Doe",
                "author_email": "john@example.com",
                "created_at": "2025-01-15T10:30:00Z",
                "committed_date": "2025-01-15T10:30:00Z",
            }
        ]

        with patch(
            "gitlab_analyzer.mcp.tools.search_tools.get_gitlab_analyzer"
        ) as mock_get_client:
            mock_client = AsyncMock()
            mock_client.search_project_commits.return_value = mock_response_data
            mock_get_client.return_value = mock_client

            # Get the tool function
            tool_func = None
            for tool in list((await mcp_server.get_tools()).values()):
                if tool.name == "search_repository_commits":
                    tool_func = tool.fn
                    break

            assert tool_func is not None

            # Execute tool
            result = await tool_func(
                project_id=123, search_keywords="fix bug", max_results=10
            )

            assert "Commit Search Results for 'fix bug'" in result
            assert "Found 1 total matches" in result
            assert "abc123d" in result
            assert "Fix bug in authentication" in result
            assert "John Doe" in result

            mock_client.search_project_commits.assert_called_once_with(
                project_id=123, search_term="fix bug", branch=None
            )

    @pytest.mark.asyncio
    async def test_search_repository_commits_no_results(self, mcp_server):
        """Test commit search with no results"""
        with patch(
            "gitlab_analyzer.mcp.tools.search_tools.get_gitlab_analyzer"
        ) as mock_get_client:
            mock_client = AsyncMock()
            mock_client.search_project_commits.return_value = []
            mock_get_client.return_value = mock_client

            # Get the tool function
            tool_func = None
            for tool in list((await mcp_server.get_tools()).values()):
                if tool.name == "search_repository_commits":
                    tool_func = tool.fn
                    break

            assert tool_func is not None

            # Execute tool
            result = await tool_func(
                project_id=123, search_keywords="nonexistent commit", branch="develop"
            )

            assert "No commit matches found for 'nonexistent commit'" in result
            assert "on branch 'develop'" in result

    @pytest.mark.asyncio
    async def test_search_repository_commits_error_handling(self, mcp_server):
        """Test commit search error handling"""
        with patch(
            "gitlab_analyzer.mcp.tools.search_tools.get_gitlab_analyzer"
        ) as mock_get_client:
            mock_client = AsyncMock()
            mock_client.search_project_commits.side_effect = Exception("Network Error")
            mock_get_client.return_value = mock_client

            # Get the tool function
            tool_func = None
            for tool in list((await mcp_server.get_tools()).values()):
                if tool.name == "search_repository_commits":
                    tool_func = tool.fn
                    break

            assert tool_func is not None

            # Execute tool
            result = await tool_func(project_id=123, search_keywords="test")

            assert "Error searching repository commits: Network Error" in result

    @pytest.mark.asyncio
    async def test_search_repository_commits_with_branch(self, mcp_server):
        """Test commit search with branch filter"""
        mock_response_data = [
            {
                "id": "abc123def456",
                "short_id": "abc123d",
                "title": "Merge request feature",
                "message": "Merge request feature",
                "author_name": "Developer",
                "author_email": "dev@example.com",
                "created_at": "2025-01-15T10:30:00Z",
                "committed_date": "2025-01-15T10:30:00Z",
            }
        ]

        with patch(
            "gitlab_analyzer.mcp.tools.search_tools.get_gitlab_analyzer"
        ) as mock_get_client:
            mock_client = AsyncMock()
            mock_client.search_project_commits.return_value = mock_response_data
            mock_get_client.return_value = mock_client

            # Get the tool function
            tool_func = None
            for tool in list((await mcp_server.get_tools()).values()):
                if tool.name == "search_repository_commits":
                    tool_func = tool.fn
                    break

            assert tool_func is not None

            # Execute tool
            result = await tool_func(
                project_id="my-project",
                search_keywords="merge",
                branch="main",
                max_results=5,
            )

            assert "Commit Search Results for 'merge'" in result
            assert "Branch: main" in result
            assert "abc123d" in result

            mock_client.search_project_commits.assert_called_once_with(
                project_id="my-project", search_term="merge", branch="main"
            )
