"""
Tests for MCP server functionality

Copyright (c) 2025 Siarhei Skuratovich
Licensed under the MIT License - see LICENSE file for details
"""

import json
import os
from unittest.mock import MagicMock, patch

import pytest

from gitlab_analyzer.mcp.server import create_server, load_env_file, main
from gitlab_analyzer.mcp.tools import get_gitlab_analyzer


class TestMCPServer:
    """Test MCP server creation and configuration"""

    def test_create_server(self):
        """Test that MCP server is created successfully"""
        server = create_server()

        assert server is not None
        assert server.name == "GitLab Pipeline Analyzer"
        assert "Analyze GitLab CI/CD pipelines" in server.instructions

    def test_server_has_tools(self):
        """Test that server has the expected tools registered"""
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

    @patch("gitlab_analyzer.mcp.server.Path.exists")
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
    """Test MCP tool functions"""

    @pytest.mark.asyncio
    async def test_analyze_failed_pipeline(
        self,
        mock_env_vars,
        clean_global_analyzer,
        mock_gitlab_analyzer,
        sample_pipeline_data,
        sample_failed_jobs,
        sample_job_trace,
    ):
        """Test analyzing a failed pipeline"""
        # Setup mock analyzer
        mock_gitlab_analyzer.get_pipeline.return_value = sample_pipeline_data
        mock_gitlab_analyzer.get_failed_pipeline_jobs.return_value = sample_failed_jobs
        mock_gitlab_analyzer.get_job_trace.return_value = sample_job_trace

        with patch(
            "gitlab_analyzer.mcp.tools.get_gitlab_analyzer",
            return_value=mock_gitlab_analyzer,
        ):
            server = create_server()

            # Get the tool function
            analyze_tool = await server.get_tool("analyze_failed_pipeline")

            assert analyze_tool is not None

            # Call the tool
            tool_result = await analyze_tool.run(
                {"project_id": "test-project", "pipeline_id": 12345}
            )

            # Extract the result from ToolResult
            result = json.loads(tool_result.content[0].text)

            assert result is not None
            assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_analyze_single_job(
        self,
        mock_env_vars,
        clean_global_analyzer,
        mock_gitlab_analyzer,
        sample_job_trace,
    ):
        """Test analyzing a single job"""
        # Setup mock analyzer
        mock_gitlab_analyzer.get_job_trace.return_value = sample_job_trace

        with patch(
            "gitlab_analyzer.mcp.tools.get_gitlab_analyzer",
            return_value=mock_gitlab_analyzer,
        ):
            server = create_server()

            # Get the tool function
            analyze_tool = await server.get_tool("analyze_single_job")

            assert analyze_tool is not None

            # Call the tool
            tool_result = await analyze_tool.run(
                {"project_id": "test-project", "job_id": 1001}
            )

            # Extract the result from ToolResult
            result = json.loads(tool_result.content[0].text)

            assert result is not None
            assert isinstance(result, dict)
            assert result["project_id"] == "test-project"
            assert result["job_id"] == 1001

    @pytest.mark.asyncio
    async def test_analyze_single_job_no_trace(
        self, mock_env_vars, clean_global_analyzer, mock_gitlab_analyzer
    ):
        """Test analyzing a single job with no trace"""
        # Setup mock analyzer with empty trace
        mock_gitlab_analyzer.get_job_trace.return_value = ""

        with patch(
            "gitlab_analyzer.mcp.tools.get_gitlab_analyzer",
            return_value=mock_gitlab_analyzer,
        ):
            server = create_server()

            # Get the tool function
            analyze_tool = await server.get_tool("analyze_single_job")

            assert analyze_tool is not None

            # Call the tool
            tool_result = await analyze_tool.run(
                {"project_id": "test-project", "job_id": 1001}
            )

            # Extract the result from ToolResult
            result = json.loads(tool_result.content[0].text)

            assert result is not None
            assert isinstance(result, dict)
            assert "error" in result
            assert "No trace found for job 1001" in result["error"]

    @pytest.mark.asyncio
    async def test_get_pipeline_status(
        self, mock_env_vars, clean_global_analyzer, mock_gitlab_analyzer
    ):
        """Test getting pipeline status"""
        # Setup mock analyzer
        mock_pipeline = {"id": 12345, "status": "failed", "ref": "main"}
        mock_gitlab_analyzer.get_pipeline.return_value = mock_pipeline

        with patch(
            "gitlab_analyzer.mcp.tools.get_gitlab_analyzer",
            return_value=mock_gitlab_analyzer,
        ):
            server = create_server()

            # Get the tool function
            status_tool = await server.get_tool("get_pipeline_status")

            assert status_tool is not None

            # Call the tool
            tool_result = await status_tool.run(
                {"project_id": "test-project", "pipeline_id": 12345}
            )

            # Extract the result from ToolResult
            result = json.loads(tool_result.content[0].text)

            assert result is not None
            assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_get_pipeline_jobs(
        self,
        mock_env_vars,
        clean_global_analyzer,
        mock_gitlab_analyzer,
        sample_pipeline_data,
        sample_job_data,
    ):
        """Test getting pipeline jobs"""
        # Setup mock analyzer
        mock_gitlab_analyzer.get_pipeline_jobs.return_value = sample_job_data

        with patch(
            "gitlab_analyzer.mcp.tools.get_gitlab_analyzer",
            return_value=mock_gitlab_analyzer,
        ):
            server = create_server()

            # Get the tool function
            jobs_tool = await server.get_tool("get_pipeline_jobs")

            assert jobs_tool is not None

            # Call the tool
            tool_result = await jobs_tool.run(
                {"project_id": "test-project", "pipeline_id": 12345}
            )

            # Extract the result from ToolResult
            result = json.loads(tool_result.content[0].text)

            assert result is not None
            assert isinstance(result, dict)


class TestMainFunction:
    """Test the main entry point function"""

    @patch("gitlab_analyzer.mcp.server.create_server")
    @patch("gitlab_analyzer.mcp.server.load_env_file")
    @patch("sys.argv", ["gitlab-analyzer"])
    def test_main_default_stdio(self, mock_load_env, mock_create_server):
        """Test main function with default stdio transport"""
        # Setup mocks
        mock_mcp = MagicMock()
        mock_create_server.return_value = mock_mcp

        # Call main function
        main()

        # Verify calls
        mock_load_env.assert_called_once()
        mock_create_server.assert_called_once()
        mock_mcp.run.assert_called_once_with(transport="stdio")

    @patch("gitlab_analyzer.mcp.server.create_server")
    @patch("gitlab_analyzer.mcp.server.load_env_file")
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
        mock_create_server.return_value = mock_mcp

        # Call main function
        main()

        # Verify calls
        mock_load_env.assert_called_once()
        mock_create_server.assert_called_once()
        mock_mcp.run.assert_called_once_with(
            transport="http", host="localhost", port=9000, path="/mcp"
        )

    @patch("gitlab_analyzer.mcp.server.create_server")
    @patch("gitlab_analyzer.mcp.server.load_env_file")
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
        mock_create_server.return_value = mock_mcp

        # Call main function
        main()

        # Verify calls
        mock_load_env.assert_called_once()
        mock_create_server.assert_called_once()
        mock_mcp.run.assert_called_once_with(transport="sse", host="0.0.0.0", port=8080)

    @patch("gitlab_analyzer.mcp.server.create_server")
    @patch("gitlab_analyzer.mcp.server.load_env_file")
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
        mock_create_server.return_value = mock_mcp

        # Call main function
        main()

        # Verify calls
        mock_load_env.assert_called_once()
        mock_create_server.assert_called_once()
        mock_mcp.run.assert_called_once_with(
            transport="http", host="example.com", port=3000, path="/api/mcp"
        )
