"""
Unit tests for MCP log tools.

Copyright (c) 2025 Siarhei Skuratovich
Licensed under the MIT License - see LICENSE file for details
"""

from unittest.mock import MagicMock, patch

import pytest
from fastmcp import FastMCP

from gitlab_analyzer.mcp.tools.log_tools import register_log_tools


class TestLogTools:
    """Test MCP log tools."""

    @pytest.fixture
    def mcp_server(self):
        """Create FastMCP server with log tools."""
        mcp = FastMCP("test")
        register_log_tools(mcp)
        return mcp

    @pytest.fixture
    def sample_generic_log(self):
        """Sample generic log text."""
        return """
        2024-01-01 10:00:00 INFO Starting process
        2024-01-01 10:01:00 WARNING Deprecated function used
        2024-01-01 10:02:00 ERROR Failed to connect to database
        2024-01-01 10:03:00 INFO Process completed
        """

    @pytest.fixture
    def sample_pytest_log(self):
        """Sample pytest log text."""
        return """
        === FAILURES ===
        ____________________ test_example ____________________

        def test_example():
        >   assert False
        E   AssertionError

        test_file.py:5: AssertionError

        === short test summary info ===
        FAILED test_file.py::test_example - AssertionError

        === 1 failed in 2.34s ===
        """

    @pytest.mark.asyncio
    async def test_extract_log_errors_generic_log(self, mcp_server, sample_generic_log):
        """Test extracting errors from generic log."""
        # Mock log parser
        with (
            patch(
                "gitlab_analyzer.mcp.tools.log_tools.LogParser.extract_log_entries"
            ) as mock_extract,
            patch(
                "gitlab_analyzer.mcp.tools.log_tools._is_pytest_log", return_value=False
            ),
        ):
            mock_extract.return_value = [
                MagicMock(
                    level="info",
                    message="Starting process",
                    line_number=1,
                    timestamp="2024-01-01 10:00:00",
                    context="startup context",
                ),
                MagicMock(
                    level="warning",
                    message="Deprecated function used",
                    line_number=2,
                    timestamp="2024-01-01 10:01:00",
                    context="warning context",
                ),
                MagicMock(
                    level="error",
                    message="Failed to connect to database",
                    line_number=3,
                    timestamp="2024-01-01 10:02:00",
                    context="error context",
                ),
            ]

            # Get the tool function
            tool_func = None
            for tool in (await mcp_server.get_tools()).values():
                if tool.name == "extract_log_errors":
                    tool_func = tool.fn
                    break

            assert tool_func is not None

            # Execute tool
            result = await tool_func(log_text=sample_generic_log)

            # Verify result structure
            assert "total_entries" in result
            assert "errors" in result
            assert "warnings" in result
            assert "error_count" in result
            assert "warning_count" in result
            assert "analysis_timestamp" in result

            # Verify data
            assert result["total_entries"] == 3
            assert result["error_count"] == 1
            assert result["warning_count"] == 1
            assert len(result["errors"]) == 1
            assert len(result["warnings"]) == 1

            # Verify error structure
            error = result["errors"][0]
            assert error["level"] == "error"
            assert error["message"] == "Failed to connect to database"
            assert error["line_number"] == 3
            assert error["timestamp"] == "2024-01-01 10:02:00"
            assert error["context"] == "error context"

            # Verify warning structure
            warning = result["warnings"][0]
            assert warning["level"] == "warning"
            assert warning["message"] == "Deprecated function used"

    @pytest.mark.asyncio
    async def test_extract_log_errors_pytest_log(self, mcp_server, sample_pytest_log):
        """Test extracting errors from pytest log."""
        # Mock pytest detection and extraction
        with (
            patch(
                "gitlab_analyzer.mcp.tools.log_tools._is_pytest_log", return_value=True
            ),
            patch(
                "gitlab_analyzer.mcp.tools.log_tools._extract_pytest_errors"
            ) as mock_pytest_extract,
        ):
            mock_pytest_extract.return_value = {
                "total_entries": 1,
                "errors": [
                    {
                        "level": "error",
                        "message": "test_file.py:AssertionError: ",
                        "test_name": "test_example",
                        "test_file": "test_file.py",
                        "exception_type": "AssertionError",
                    }
                ],
                "warnings": [],
                "error_count": 1,
                "warning_count": 0,
                "analysis_timestamp": "2024-01-01T10:00:00",
            }

            # Get the tool function
            tool_func = None
            for tool in (await mcp_server.get_tools()).values():
                if tool.name == "extract_log_errors":
                    tool_func = tool.fn
                    break

            assert tool_func is not None

            # Execute tool
            result = await tool_func(log_text=sample_pytest_log)

            # Verify pytest-specific extraction was called
            mock_pytest_extract.assert_called_once_with(sample_pytest_log)

            # Verify result structure is pytest-specific
            assert result["error_count"] == 1
            assert result["warning_count"] == 0
            assert "test_name" in result["errors"][0]
            assert "exception_type" in result["errors"][0]

    @pytest.mark.asyncio
    async def test_extract_log_errors_empty_log(self, mcp_server):
        """Test extracting errors from empty log."""
        with (
            patch(
                "gitlab_analyzer.mcp.tools.log_tools._is_pytest_log", return_value=False
            ),
            patch(
                "gitlab_analyzer.mcp.tools.log_tools.LogParser.extract_log_entries",
                return_value=[],
            ),
        ):
            # Get the tool function
            tool_func = None
            for tool in (await mcp_server.get_tools()).values():
                if tool.name == "extract_log_errors":
                    tool_func = tool.fn
                    break

            assert tool_func is not None

            # Execute tool
            result = await tool_func(log_text="")

            # Verify empty result
            assert result["total_entries"] == 0
            assert result["error_count"] == 0
            assert result["warning_count"] == 0
            assert result["errors"] == []
            assert result["warnings"] == []

    @pytest.mark.asyncio
    async def test_extract_log_errors_exception(self, mcp_server):
        """Test extracting errors when exception occurs."""
        with patch(
            "gitlab_analyzer.mcp.tools.log_tools._is_pytest_log",
            side_effect=Exception("Detection error"),
        ):
            # Get the tool function
            tool_func = None
            for tool in (await mcp_server.get_tools()).values():
                if tool.name == "extract_log_errors":
                    tool_func = tool.fn
                    break

            assert tool_func is not None

            # Execute tool
            result = await tool_func(log_text="Some log text")

            # Verify error handling
            assert "error" in result
            assert "Failed to extract log errors" in result["error"]

    @pytest.mark.asyncio
    async def test_extract_log_errors_no_errors_or_warnings(self, mcp_server):
        """Test extracting from log with no errors or warnings."""
        with (
            patch(
                "gitlab_analyzer.mcp.tools.log_tools._is_pytest_log", return_value=False
            ),
            patch(
                "gitlab_analyzer.mcp.tools.log_tools.LogParser.extract_log_entries"
            ) as mock_extract,
        ):
            # Mock log entries with only info level
            mock_extract.return_value = [
                MagicMock(
                    level="info",
                    message="Info message 1",
                    line_number=1,
                    timestamp=None,
                    context=None,
                ),
                MagicMock(
                    level="debug",
                    message="Debug message",
                    line_number=2,
                    timestamp=None,
                    context=None,
                ),
            ]

            # Get the tool function
            tool_func = None
            for tool in (await mcp_server.get_tools()).values():
                if tool.name == "extract_log_errors":
                    tool_func = tool.fn
                    break

            assert tool_func is not None

            # Execute tool
            result = await tool_func(log_text="Info and debug messages only")

            # Verify no errors or warnings found
            assert result["total_entries"] == 2
            assert result["error_count"] == 0
            assert result["warning_count"] == 0
            assert result["errors"] == []
            assert result["warnings"] == []

    async def test_register_log_tools(self):
        """Test that log tools are properly registered."""
        mcp = FastMCP("test")
        register_log_tools(mcp)

        # Verify tools are registered
        tool_names = [tool.name for tool in list((await mcp.get_tools()).values())]
        assert "extract_log_errors" in tool_names

        # Verify tool metadata
        for tool in list((await mcp.get_tools()).values()):
            if tool.name == "extract_log_errors":
                assert "log_text" in str(tool.fn.__annotations__)

    @pytest.mark.asyncio
    async def test_extract_log_errors_large_log(self, mcp_server):
        """Test extracting errors from large log with many entries."""
        # Create a large log with multiple types of entries
        large_log_entries = []
        for i in range(100):
            level = "error" if i % 10 == 0 else "warning" if i % 5 == 0 else "info"
            large_log_entries.append(
                MagicMock(
                    level=level,
                    message=f"Message {i}",
                    line_number=i + 1,
                    timestamp=f"2024-01-01 10:{i:02d}:00",
                    context=f"context {i}",
                )
            )

        with (
            patch(
                "gitlab_analyzer.mcp.tools.log_tools._is_pytest_log", return_value=False
            ),
            patch(
                "gitlab_analyzer.mcp.tools.log_tools.LogParser.extract_log_entries",
                return_value=large_log_entries,
            ),
        ):
            # Get the tool function
            tool_func = None
            for tool in (await mcp_server.get_tools()).values():
                if tool.name == "extract_log_errors":
                    tool_func = tool.fn
                    break

            assert tool_func is not None

            # Execute tool
            result = await tool_func(log_text="Large log text")

            # Verify counts (every 10th is error, every 5th is warning, excluding errors)
            expected_errors = 10  # positions 0, 10, 20, ..., 90
            expected_warnings = 10  # positions 5, 15, 25, 35, 45, 55, 65, 75, 85, 95

            assert result["total_entries"] == 100
            assert result["error_count"] == expected_errors
            assert result["warning_count"] == expected_warnings

    @pytest.mark.asyncio
    async def test_extract_log_errors_mixed_levels(self, mcp_server):
        """Test extracting from log with various log levels."""
        with (
            patch(
                "gitlab_analyzer.mcp.tools.log_tools._is_pytest_log", return_value=False
            ),
            patch(
                "gitlab_analyzer.mcp.tools.log_tools.LogParser.extract_log_entries"
            ) as mock_extract,
        ):
            # Mock diverse log entries
            mock_extract.return_value = [
                MagicMock(
                    level="critical",
                    message="Critical error",
                    line_number=1,
                    timestamp=None,
                    context=None,
                ),
                MagicMock(
                    level="error",
                    message="Regular error",
                    line_number=2,
                    timestamp=None,
                    context=None,
                ),
                MagicMock(
                    level="warning",
                    message="Warning message",
                    line_number=3,
                    timestamp=None,
                    context=None,
                ),
                MagicMock(
                    level="info",
                    message="Info message",
                    line_number=4,
                    timestamp=None,
                    context=None,
                ),
                MagicMock(
                    level="debug",
                    message="Debug message",
                    line_number=5,
                    timestamp=None,
                    context=None,
                ),
                MagicMock(
                    level="trace",
                    message="Trace message",
                    line_number=6,
                    timestamp=None,
                    context=None,
                ),
            ]

            # Get the tool function
            tool_func = None
            for tool in (await mcp_server.get_tools()).values():
                if tool.name == "extract_log_errors":
                    tool_func = tool.fn
                    break

            assert tool_func is not None

            # Execute tool
            result = await tool_func(log_text="Mixed level log")

            # Verify only errors and warnings are captured
            assert result["total_entries"] == 6
            assert result["error_count"] == 2  # critical and error levels
            assert result["warning_count"] == 1

            # Verify error levels captured
            error_messages = [error["message"] for error in result["errors"]]
            assert "Critical error" in error_messages
            assert "Regular error" in error_messages

            # Verify warning captured
            warning_messages = [warning["message"] for warning in result["warnings"]]
            assert "Warning message" in warning_messages
