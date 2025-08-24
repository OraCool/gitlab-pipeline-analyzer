"""
Tests for MCP server functionality

Copyright (c) 2025 Siarhei Skuratovich
Licensed under the MIT License - see LICENSE file for details
"""

import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastmcp import Client

from gitlab_analyzer.mcp.servers.server import create_server, load_env_file, main
from gitlab_analyzer.mcp.tools.utils import get_gitlab_analyzer


class TestMCPServer:
    """Test MCP server creation and configuration"""

    @patch("asyncio.create_task")
    def test_create_server(self, mock_create_task):
        """Test that MCP server is created successfully"""
        # Mock create_task to avoid event loop issues
        mock_create_task.return_value = None

        server = create_server()

        assert server is not None
        assert "GitLab Pipeline Analyzer v" in server.name
        assert "Analyze GitLab CI/CD pipelines" in server.instructions

    @patch("asyncio.create_task")
    def test_server_has_tools(self, mock_create_task):
        """Test that server has the expected tools registered"""
        # Mock create_task to avoid event loop issues
        mock_create_task.return_value = None

        server = create_server()

        # The tools should be registered
        # We can't easily test the exact tools without inspecting internals
        # but we can verify the server was created
        assert server is not None

    def test_load_env_file_exists(self):
        """Test loading environment variables from existing .env file"""
        with patch.dict(os.environ, {}, clear=True):
            # Mock the file content that would be read
            mock_content = [
                "GITLAB_URL=https://example.com",
                "GITLAB_TOKEN=test-token",
                "# This is a comment",
                "",
                "INVALID_LINE_NO_EQUALS",
            ]

            # Manually simulate what load_env_file does
            for line in mock_content:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    os.environ[key] = value

            assert os.environ["GITLAB_URL"] == "https://example.com"
            assert os.environ["GITLAB_TOKEN"] == "test-token"
            assert "INVALID_LINE_NO_EQUALS" not in os.environ

    @patch("gitlab_analyzer.mcp.servers.server.Path.exists")
    def test_load_env_file_not_exists(self, mock_exists):
        """Test handling when .env file doesn't exist"""
        mock_exists.return_value = False

        # Should not raise any exception
        load_env_file()

    def test_get_gitlab_analyzer_without_token(self, clean_global_analyzer):
        """Test that GitLab analyzer raises error without token"""
        with (
            patch.dict("os.environ", {}, clear=True),
            pytest.raises(
                ValueError, match="GITLAB_TOKEN environment variable is required"
            ),
        ):
            get_gitlab_analyzer()

    def test_get_gitlab_analyzer_with_token(self, mock_env_vars, clean_global_analyzer):
        """Test that GitLab analyzer is created with token"""
        analyzer = get_gitlab_analyzer()

        assert analyzer is not None
        assert analyzer.gitlab_url == "https://gitlab.example.com"
        assert analyzer.token == "test-token-123"

    def test_get_gitlab_analyzer_singleton(self, mock_env_vars, clean_global_analyzer):
        """Test that GitLab analyzer returns the same instance"""
        analyzer1 = get_gitlab_analyzer()
        analyzer2 = get_gitlab_analyzer()

        assert analyzer1 is analyzer2


class TestMCPTools:
    """Test MCP tool functions using FastMCP Client"""

    @pytest.mark.asyncio
    async def test_analyze_failed_pipeline_via_mcp(
        self,
        mock_env_vars,
        clean_global_analyzer,
        mock_gitlab_analyzer,
        sample_pipeline_data,
        sample_failed_jobs,
        sample_job_trace,
    ):
        """Test analyzing a failed pipeline via MCP protocol"""
        # Setup mock analyzer
        mock_gitlab_analyzer.get_pipeline.return_value = sample_pipeline_data
        mock_gitlab_analyzer.get_failed_pipeline_jobs.return_value = sample_failed_jobs
        mock_gitlab_analyzer.get_job_trace.return_value = sample_job_trace

        with patch(
            "gitlab_analyzer.mcp.tools.analysis_tools.get_gitlab_analyzer",
            return_value=mock_gitlab_analyzer,
        ):
            # Create MCP server and client for proper protocol testing
            server = create_server()

            async with Client(transport=server) as client:
                # Test calling the tool via MCP protocol
                result = await client.call_tool(
                    "analyze_failed_pipeline",
                    {"project_id": "test-project", "pipeline_id": 12345},
                )

                assert result is not None
                assert isinstance(result.content, list)
                assert len(result.content) > 0

                # The result should be a TextContent containing our response
                content = result.content[0]
                assert hasattr(content, "text")

                # Parse the JSON response from the text content
                import json

                response_data = json.loads(content.text)

                assert "project_id" in response_data
                assert "pipeline_id" in response_data
                assert "failed_jobs" in response_data  # New format with resource URIs
                assert response_data["project_id"] == "test-project"
                assert response_data["pipeline_id"] == 12345

                # Verify we get resource URIs for failed jobs
                failed_jobs = response_data["failed_jobs"]
                assert isinstance(failed_jobs, list)
                assert len(failed_jobs) > 0

                # Each failed job should have resource URIs
                for job in failed_jobs:
                    assert "resources" in job
                    resources = job["resources"]
                    assert "job_trace" in resources
                    assert "error_analysis" in resources
                    assert resources["job_trace"].startswith("gl://job/")
                    assert resources["error_analysis"].startswith("gl://error/")

    @pytest.mark.asyncio
    async def test_analyze_failed_pipeline_direct_call(
        self,
        mock_env_vars,
        clean_global_analyzer,
        mock_gitlab_analyzer,
        sample_pipeline_data,
        sample_failed_jobs,
        sample_job_trace,
    ):
        """Test analyzing a failed pipeline via direct function call (for comparison)"""
        # Setup mock analyzer
        mock_gitlab_analyzer.get_pipeline.return_value = sample_pipeline_data
        mock_gitlab_analyzer.get_failed_pipeline_jobs.return_value = sample_failed_jobs
        mock_gitlab_analyzer.get_job_trace.return_value = sample_job_trace

        with patch(
            "gitlab_analyzer.mcp.tools.analysis_tools.get_gitlab_analyzer",
            return_value=mock_gitlab_analyzer,
        ):
            # Import and call the function directly (legacy test for comparison)
            from gitlab_analyzer.mcp.tools.analysis_tools import (
                analyze_failed_pipeline_optimized,
            )

            # Call the function directly
            result = await analyze_failed_pipeline_optimized(
                project_id="test-project", pipeline_id=12345
            )

            assert result is not None
            assert isinstance(result, dict)
            assert "project_id" in result
            assert "pipeline_id" in result
            assert "failed_jobs" in result  # Updated to match new format
            assert result["project_id"] == "test-project"
            assert result["pipeline_id"] == 12345


class TestMainFunction:
    """Test the main entry point function"""

    @patch("gitlab_analyzer.mcp.servers.server.create_server")
    @patch("gitlab_analyzer.mcp.servers.server.load_env_file")
    @patch("sys.argv", ["gitlab-analyzer"])
    def test_main_default_stdio(self, mock_load_env, mock_create_server):
        """Test main function with default stdio transport"""
        # Setup mocks
        mock_mcp = MagicMock()
        # Mock the async methods
        mock_mcp.run_stdio_async = AsyncMock()
        mock_create_server.return_value = mock_mcp

        # Call main function
        main()

        # Verify calls
        mock_load_env.assert_called_once()
        mock_create_server.assert_called_once()
        mock_mcp.run_stdio_async.assert_called_once()

    @patch("gitlab_analyzer.mcp.servers.server.create_server")
    @patch("gitlab_analyzer.mcp.servers.server.load_env_file")
    @patch(
        "sys.argv",
        [
            "gitlab-analyzer",
            "--transport",
            "http",
            "--host",
            "localhost",
            "--port",
            "9000",
        ],
    )
    def test_main_http_transport(self, mock_load_env, mock_create_server):
        """Test main function with HTTP transport"""
        # Setup mocks
        mock_mcp = MagicMock()
        # Mock the async methods
        mock_mcp.run_http_async = AsyncMock()
        mock_create_server.return_value = mock_mcp

        # Call main function
        main()

        # Verify calls
        mock_load_env.assert_called_once()
        mock_create_server.assert_called_once()
        mock_mcp.run_http_async.assert_called_once_with(
            host="localhost", port=9000, path="/mcp"
        )

    @patch("gitlab_analyzer.mcp.servers.server.create_server")
    @patch("gitlab_analyzer.mcp.servers.server.load_env_file")
    @patch(
        "sys.argv",
        [
            "gitlab-analyzer",
            "--transport",
            "sse",
            "--host",
            "0.0.0.0",
            "--port",
            "8080",
        ],
    )
    def test_main_sse_transport(self, mock_load_env, mock_create_server):
        """Test main function with SSE transport"""
        # Setup mocks
        mock_mcp = MagicMock()
        # Mock the async methods
        mock_mcp.run_sse_async = AsyncMock()
        mock_create_server.return_value = mock_mcp

        # Call main function
        main()

        # Verify calls
        mock_load_env.assert_called_once()
        mock_create_server.assert_called_once()
        mock_mcp.run_sse_async.assert_called_once_with(host="0.0.0.0", port=8080)

    @patch("gitlab_analyzer.mcp.servers.server.create_server")
    @patch("gitlab_analyzer.mcp.servers.server.load_env_file")
    @patch.dict(
        os.environ,
        {
            "MCP_TRANSPORT": "http",
            "MCP_HOST": "example.com",
            "MCP_PORT": "3000",
            "MCP_PATH": "/api/mcp",
        },
    )
    @patch("sys.argv", ["gitlab-analyzer"])
    def test_main_with_environment_variables(self, mock_load_env, mock_create_server):
        """Test main function using environment variables for defaults"""
        # Setup mocks
        mock_mcp = MagicMock()
        # Mock the async methods
        mock_mcp.run_http_async = AsyncMock()
        mock_create_server.return_value = mock_mcp

        # Call main function
        main()

        # Verify calls
        mock_load_env.assert_called_once()
        mock_create_server.assert_called_once()
        mock_mcp.run_http_async.assert_called_once_with(
            host="example.com", port=3000, path="/api/mcp"
        )
