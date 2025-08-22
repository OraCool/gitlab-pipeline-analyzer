"""
Unit tests for the get_cleaned_job_trace MCP tool
"""

import json
import re
from unittest.mock import AsyncMock, patch

import pytest

from gitlab_analyzer.mcp.servers.server import create_server
from gitlab_analyzer.parsers.log_parser import LogParser


class TestGetCleanedJobTrace:
    """Test cases for the get_cleaned_job_trace tool"""

    @pytest.mark.asyncio
    async def test_get_cleaned_job_trace_success(
        self, mock_env_vars, clean_global_analyzer
    ):
        """Test successful trace cleaning"""
        sample_raw_trace = (
            "\x1b[0KRunning with gitlab-runner 17.8.5 (c9164c8c)\x1b[0;m\n"
            "\x1b[0K  on GCP Ocean (shared k8s runner)\x1b[0;m\n"
            "\x1b[31mERROR:\x1b[0m Something went wrong\n"
            "\x1b[33mWARNING:\x1b[0m This is a warning\n"
            "Normal text without ANSI codes\n"
            "\x1b[32;1mSUCCESS:\x1b[0m Operation completed\n"
        )

        expected_cleaned_trace = (
            "Running with gitlab-runner 17.8.5 (c9164c8c)\n"
            "  on GCP Ocean (shared k8s runner)\n"
            "ERROR: Something went wrong\n"
            "WARNING: This is a warning\n"
            "Normal text without ANSI codes\n"
            "SUCCESS: Operation completed\n"
        )

        # Mock the GitLabAnalyzer before server creation
        mock_instance = AsyncMock()
        mock_instance.get_job_trace.return_value = sample_raw_trace

        with (
            patch(
                "gitlab_analyzer.mcp.tools.utils.get_gitlab_analyzer",
                return_value=mock_instance,
            ),
            patch(
                "gitlab_analyzer.mcp.tools.info_tools.get_gitlab_analyzer",
                return_value=mock_instance,
            ),
            patch(
                "gitlab_analyzer.mcp.tools.analysis_tools.get_gitlab_analyzer",
                return_value=mock_instance,
            ),
            patch(
                "gitlab_analyzer.mcp.tools.utils.get_gitlab_analyzer",
                return_value=mock_instance,
            ),
        ):
            # Create server and get tool
            server = create_server()
            tool = await server.get_tool("get_cleaned_job_trace")

            # Execute the tool
            tool_result = await tool.run({"project_id": "123", "job_id": 456})
            result = json.loads(tool_result.content[0].text)

            # Verify the result structure
            assert "error" not in result
            assert result["project_id"] == "123"
            assert result["job_id"] == 456
            assert result["cleaned_trace"] == expected_cleaned_trace
            assert result["original_length"] == len(sample_raw_trace)
            assert result["cleaned_length"] == len(expected_cleaned_trace)
            assert result["bytes_removed"] > 0
            assert result["ansi_sequences_found"] > 0
            assert result["unique_ansi_types"] > 0

            # Verify the analyzer was called correctly
            mock_instance.get_job_trace.assert_called_once_with("123", 456)

    @pytest.mark.asyncio
    async def test_get_cleaned_job_trace_no_ansi(
        self, mock_env_vars, clean_global_analyzer
    ):
        """Test trace cleaning with no ANSI sequences"""
        plain_trace = "This is a plain text trace\nwith no ANSI codes\n"

        mock_instance = AsyncMock()
        mock_instance.get_job_trace.return_value = plain_trace

        with (
            patch(
                "gitlab_analyzer.mcp.tools.utils.get_gitlab_analyzer",
                return_value=mock_instance,
            ),
            patch(
                "gitlab_analyzer.mcp.tools.info_tools.get_gitlab_analyzer",
                return_value=mock_instance,
            ),
            patch(
                "gitlab_analyzer.mcp.tools.analysis_tools.get_gitlab_analyzer",
                return_value=mock_instance,
            ),
            patch(
                "gitlab_analyzer.mcp.tools.utils.get_gitlab_analyzer",
                return_value=mock_instance,
            ),
        ):
            server = create_server()
            tool = await server.get_tool("get_cleaned_job_trace")

            tool_result = await tool.run({"project_id": "123", "job_id": 456})
            result = json.loads(tool_result.content[0].text)

            # Verify the result
            assert "error" not in result
            assert result["cleaned_trace"] == plain_trace
            assert result["ansi_sequences_found"] == 0

            # Verify cleaning statistics for no ANSI codes
            assert result["original_length"] == len(plain_trace)
            assert result["cleaned_length"] == len(plain_trace)
            assert result["bytes_removed"] == 0
            assert result["unique_ansi_types"] == 0

    @pytest.mark.asyncio
    async def test_get_cleaned_job_trace_empty_trace(
        self, mock_env_vars, clean_global_analyzer
    ):
        """Test trace cleaning with empty trace"""
        empty_trace = ""

        mock_instance = AsyncMock()
        mock_instance.get_job_trace.return_value = empty_trace

        with (
            patch(
                "gitlab_analyzer.mcp.tools.utils.get_gitlab_analyzer",
                return_value=mock_instance,
            ),
            patch(
                "gitlab_analyzer.mcp.tools.info_tools.get_gitlab_analyzer",
                return_value=mock_instance,
            ),
            patch(
                "gitlab_analyzer.mcp.tools.analysis_tools.get_gitlab_analyzer",
                return_value=mock_instance,
            ),
            patch(
                "gitlab_analyzer.mcp.tools.utils.get_gitlab_analyzer",
                return_value=mock_instance,
            ),
        ):
            server = create_server()
            tool = await server.get_tool("get_cleaned_job_trace")

            tool_result = await tool.run({"project_id": "123", "job_id": 456})
            result = json.loads(tool_result.content[0].text)

            # Verify the result
            assert "error" not in result
            assert result["cleaned_trace"] == ""
            assert result["original_length"] == 0
            assert result["cleaned_length"] == 0
            assert result["bytes_removed"] == 0
            assert result["ansi_sequences_found"] == 0
            assert result["unique_ansi_types"] == 0

    @pytest.mark.asyncio
    async def test_get_cleaned_job_trace_network_error(
        self, mock_env_vars, clean_global_analyzer
    ):
        """Test handling of network errors"""
        import httpx

        with patch(
            "gitlab_analyzer.mcp.tools.utils.get_gitlab_analyzer"
        ) as mock_analyzer:
            mock_instance = AsyncMock()
            mock_instance.get_job_trace.side_effect = httpx.HTTPError("Network error")
            mock_analyzer.return_value = mock_instance

            server = create_server()
            tool = await server.get_tool("get_cleaned_job_trace")

            tool_result = await tool.run({"project_id": "123", "job_id": 456})
            result = json.loads(tool_result.content[0].text)

            # Verify error handling
            assert "error" in result
            assert "Failed to get cleaned job trace" in result["error"]
            assert result["project_id"] == "123"
            assert result["job_id"] == 456

    def test_ansi_pattern_regex(self):
        """Test the ANSI regex pattern directly"""
        ansi_pattern = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")

        test_cases = [
            ("\x1b[0m", True),  # Reset
            ("\x1b[31m", True),  # Red
            ("\x1b[1;32m", True),  # Bold green
            ("\x1b[0K", True),  # Clear line
            ("\x1b[2J", True),  # Clear screen
            ("\x1b[H", True),  # Home
            ("\x1b[?25l", True),  # Hide cursor
            ("normal text", False),  # No ANSI
            ("\x1b", False),  # Incomplete
        ]

        for text, should_match in test_cases:
            matches = ansi_pattern.findall(text)
            if should_match:
                assert len(matches) > 0, f"Should match ANSI in: {repr(text)}"
            else:
                assert len(matches) == 0, f"Should not match ANSI in: {repr(text)}"


class TestAnsiSequenceTypes:
    """Test detection and counting of different ANSI sequence types"""

    def test_ansi_sequence_counting(self):
        """Test counting of different ANSI sequence types"""
        # Create a trace with repeated ANSI sequences
        trace = (
            "\x1b[0m" * 3
            + "\x1b[31m" * 2
            + "\x1b[0K" * 4
            + "some text"  # Reset (3 times)  # Red (2 times)  # Clear line (4 times)
        )

        # Clean the trace
        cleaned = LogParser.clean_ansi_sequences(trace)
        assert cleaned == "some text"

        # Count ANSI sequences manually
        ansi_pattern = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")
        ansi_matches = ansi_pattern.findall(trace)

        # Count types
        ansi_types = {}
        for match in ansi_matches:
            ansi_types[match] = ansi_types.get(match, 0) + 1

        # Verify counts
        assert ansi_types["\x1b[0m"] == 3
        assert ansi_types["\x1b[31m"] == 2
        assert ansi_types["\x1b[0K"] == 4
        assert len(ansi_types) == 3  # 3 unique types
        assert sum(ansi_types.values()) == 9  # 9 total sequences

    def test_log_parser_clean_ansi_sequences(self):
        """Test LogParser._clean_ansi_sequences method directly"""
        # Test various ANSI escape sequences
        test_cases = [
            ("\x1b[0m", ""),  # Reset
            ("Hello\x1b[31mWorld\x1b[0m", "HelloWorld"),  # Color codes
            ("\x1b[1m\x1b[4mBold Underline\x1b[0m", "Bold Underline"),  # Multiple
            ("No ANSI here", "No ANSI here"),  # Plain text
            ("", ""),  # Empty string
            ("\x1b[0K\x1b[2J\x1b[H", ""),  # Clear sequences only
        ]

        for input_text, expected_output in test_cases:
            result = LogParser.clean_ansi_sequences(input_text)
            assert result == expected_output, f"Failed for input: {repr(input_text)}"


class TestToolIntegration:
    """Integration tests for the tool within the MCP framework"""

    @pytest.mark.asyncio
    async def test_tool_registration(self):
        """Test that the tool is properly registered"""
        server = create_server()

        # Get the tool to verify it exists
        tool = await server.get_tool("get_cleaned_job_trace")
        assert tool is not None

    @pytest.mark.asyncio
    async def test_tool_alongside_other_tools(
        self, mock_env_vars, clean_global_analyzer
    ):
        """Test that the new tool works alongside existing tools"""
        raw_trace = "\x1b[31mError\x1b[0m: Something failed"

        # Mock analyzer for both tools
        mock_instance = AsyncMock()
        mock_instance.get_job_trace.return_value = raw_trace

        with (
            patch(
                "gitlab_analyzer.mcp.tools.utils.get_gitlab_analyzer",
                return_value=mock_instance,
            ),
            patch(
                "gitlab_analyzer.mcp.tools.info_tools.get_gitlab_analyzer",
                return_value=mock_instance,
            ),
            patch(
                "gitlab_analyzer.mcp.tools.analysis_tools.get_gitlab_analyzer",
                return_value=mock_instance,
            ),
            patch(
                "gitlab_analyzer.mcp.tools.utils.get_gitlab_analyzer",
                return_value=mock_instance,
            ),
        ):
            server = create_server()

            # Test raw trace tool
            raw_tool = await server.get_tool("get_job_trace")
            raw_result = await raw_tool.run({"project_id": "123", "job_id": 456})
            raw_data = json.loads(raw_result.content[0].text)
            assert raw_data["trace"] == raw_trace

            # Test cleaned trace tool
            cleaned_tool = await server.get_tool("get_cleaned_job_trace")
            cleaned_result = await cleaned_tool.run(
                {"project_id": "123", "job_id": 456}
            )
            cleaned_data = json.loads(cleaned_result.content[0].text)
            assert cleaned_data["cleaned_trace"] == "Error: Something failed"

            # Verify both tools called the same underlying method
            assert mock_instance.get_job_trace.call_count == 2
