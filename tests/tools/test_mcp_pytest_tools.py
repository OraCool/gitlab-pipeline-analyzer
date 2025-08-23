"""
Unit tests for MCP pytest tools.

Copyright (c) 2025 Siarhei Skuratovich
Licensed under the MIT License - see LICENSE file for details
"""

from unittest.mock import AsyncMock, patch

import httpx
import pytest
from fastmcp import FastMCP

from gitlab_analyzer.mcp.tools.pytest_tools import (
    register_pytest_tools,
)
from gitlab_analyzer.mcp.tools.utils import _extract_pytest_errors
from gitlab_analyzer.models.pytest_models import (
    PytestFailureDetail,
    PytestLogAnalysis,
    PytestShortSummary,
    PytestStatistics,
)


class TestPytestTools:
    """Test MCP pytest tools."""

    @pytest.fixture
    def mcp_server(self):
        """Create FastMCP server with pytest tools."""
        mcp = FastMCP("test")
        register_pytest_tools(mcp)
        return mcp

    @pytest.fixture
    def mock_analyzer(self):
        """Mock GitLab analyzer."""
        analyzer = AsyncMock()
        return analyzer

    @pytest.fixture
    def sample_pytest_log(self):
        """Sample pytest log with failures."""
        return """
        === FAILURES ===
        ____________________ test_example ____________________

        def test_example():
        >   assert 1 == 2
        E   AssertionError

        test_file.py:5: AssertionError

        === short test summary info ===
        FAILED test_file.py::test_example - AssertionError

        === 1 failed, 2 passed in 3.45s ===
        """

    @pytest.fixture
    def sample_pytest_analysis(self):
        """Sample pytest analysis object."""
        return PytestLogAnalysis(
            detailed_failures=[
                PytestFailureDetail(
                    test_name="test_example",
                    test_file="test_file.py",
                    test_function="test_example",
                    test_parameters=None,
                    exception_type="AssertionError",
                    exception_message="assert 1 == 2",
                    platform_info="linux",
                    python_version="3.8.10",
                    traceback=[],
                    full_error_text="Full error text",
                )
            ],
            short_summary=[
                PytestShortSummary(
                    test_name="test_example",
                    test_file="test_file.py",
                    test_function="test_example",
                    test_parameters=None,
                    error_type="AssertionError",
                    error_message="assert 1 == 2",
                )
            ],
            statistics=PytestStatistics(
                total_tests=3,
                passed=2,
                failed=1,
                skipped=0,
                errors=0,
                warnings=0,
                duration_seconds=3.45,
                duration_formatted="3.45s",
            ),
            has_failures_section=True,
            has_short_summary_section=True,
        )

    def test_extract_pytest_errors_with_detailed_failures(self, sample_pytest_analysis):
        """Test extracting pytest errors from detailed failures."""
        with patch(
            "gitlab_analyzer.mcp.tools.pytest_tools.PytestLogParser.parse_pytest_log",
            return_value=sample_pytest_analysis,
        ):
            result = _extract_pytest_errors("sample log")

            # Verify result structure
            assert "errors" in result
            assert "warnings" in result
            assert "error_count" in result
            assert "warning_count" in result
            assert "parser_type" in result

            # Verify error details
            assert result["error_count"] == 1
            assert len(result["errors"]) == 1

            error = result["errors"][0]
            assert error["category"] == "test_failure"
            assert error["test_name"] == "test_example"
            assert error["test_file"] == "test_file.py"
            assert error["exception_type"] == "AssertionError"

    def test_extract_pytest_errors_with_short_summary_only(self):
        """Test extracting pytest errors from short summary when no detailed failures."""
        analysis = PytestLogAnalysis(
            detailed_failures=[],
            short_summary=[
                PytestShortSummary(
                    test_name="test_short",
                    test_file="test_short.py",
                    test_function="test_short",
                    test_parameters=None,
                    error_type="ValueError",
                    error_message="invalid value",
                )
            ],
            statistics=PytestStatistics(
                total_tests=1,
                passed=0,
                failed=1,
                skipped=0,
                errors=0,
                warnings=0,
                duration_seconds=1.23,
                duration_formatted="1.23s",
            ),
            has_failures_section=False,
            has_short_summary_section=True,
        )

        with patch(
            "gitlab_analyzer.mcp.tools.pytest_tools.PytestLogParser.parse_pytest_log",
            return_value=analysis,
        ):
            result = _extract_pytest_errors("sample log")

            # Verify short summary is used
            assert (
                result["error_count"] == 0
            )  # _extract_pytest_errors only uses detailed_failures
            assert result["errors"] == []

    def test_extract_pytest_errors_no_failures(self):
        """Test extracting pytest errors when no failures exist."""
        analysis = PytestLogAnalysis(
            detailed_failures=[],
            short_summary=[],
            statistics=PytestStatistics(
                total_tests=5,
                passed=5,
                failed=0,
                skipped=0,
                errors=0,
                warnings=0,
                duration_seconds=2.1,
                duration_formatted="2.1s",
            ),
            has_failures_section=False,
            has_short_summary_section=False,
        )

        with patch(
            "gitlab_analyzer.mcp.tools.pytest_tools.PytestLogParser.parse_pytest_log",
            return_value=analysis,
        ):
            result = _extract_pytest_errors("sample log")

            # Verify no errors found
            assert result["error_count"] == 0
            assert result["errors"] == []

    def test_extract_pytest_errors_with_traceback(self):
        """Test extracting pytest errors with traceback information."""
        from gitlab_analyzer.models.pytest_models import PytestTraceback

        failure_with_traceback = PytestFailureDetail(
            test_name="test_with_traceback",
            test_file="test_traceback.py",
            test_function="test_with_traceback",
            test_parameters=None,
            platform_info=None,
            python_version=None,
            exception_type="RuntimeError",
            exception_message="Something went wrong",
            traceback=[
                PytestTraceback(
                    file_path="test_traceback.py",
                    line_number=10,
                    function_name="test_with_traceback",
                    code_line="raise RuntimeError('Something went wrong')",
                    error_type="RuntimeError",
                    error_message="Something went wrong",
                ),
                PytestTraceback(
                    file_path="helper.py",
                    line_number=25,
                    function_name="helper_function",
                    code_line="return problematic_call()",
                    error_type=None,
                    error_message=None,
                ),
            ],
            full_error_text="RuntimeError: Something went wrong",
        )

        analysis = PytestLogAnalysis(
            detailed_failures=[failure_with_traceback],
            short_summary=[],
            statistics=PytestStatistics(
                failed=1,
                total_tests=1,
                duration_seconds=1.0,
                passed=0,
                skipped=0,
                errors=0,
                warnings=0,
                duration_formatted="1.0s",
            ),
            has_failures_section=True,
            has_short_summary_section=False,
        )

        with patch(
            "gitlab_analyzer.mcp.tools.pytest_tools.PytestLogParser.parse_pytest_log",
            return_value=analysis,
        ):
            result = _extract_pytest_errors("sample log")

            # Verify traceback is included in error data
            error = result["errors"][0]
            assert error["has_traceback"] is True
            assert len(error["traceback"]) == 2
            assert error["traceback"][0]["file_path"] == "test_traceback.py"
            assert error["traceback"][0]["line_number"] == 10

    @pytest.mark.asyncio
    async def test_extract_pytest_detailed_failures_success(
        self, mcp_server, mock_analyzer, sample_pytest_log, sample_pytest_analysis
    ):
        """Test successful detailed failures extraction."""
        with patch(
            "gitlab_analyzer.mcp.tools.pytest_tools.get_gitlab_analyzer",
            return_value=mock_analyzer,
        ):
            # Setup mock responses
            mock_analyzer.get_job_trace.return_value = sample_pytest_log

            # Mock pytest parser
            with patch(
                "gitlab_analyzer.mcp.tools.pytest_tools.PytestLogParser.parse_pytest_log",
                return_value=sample_pytest_analysis,
            ):
                # Get the tool function
                tool_func = None
                for tool in list((await mcp_server.get_tools()).values()):
                    if tool.name == "extract_pytest_detailed_failures":
                        tool_func = tool.fn
                        break

                assert tool_func is not None

                # Execute tool
                result = await tool_func(project_id="test-project", job_id=1001)

                # Verify result structure
                assert "project_id" in result
                assert "job_id" in result
                assert "detailed_failures" in result
                assert "failure_count" in result
                assert "mcp_info" in result

                # Verify detailed failure data
                assert result["failure_count"] == 1
                assert len(result["detailed_failures"]) == 1

                failure = result["detailed_failures"][0]
                assert failure["test_name"] == "test_example"
                assert failure["test_file"] == "test_file.py"
                assert failure["exception_type"] == "AssertionError"

    @pytest.mark.asyncio
    async def test_extract_pytest_short_summary_success(
        self, mcp_server, mock_analyzer, sample_pytest_log, sample_pytest_analysis
    ):
        """Test successful short summary extraction."""
        with patch(
            "gitlab_analyzer.mcp.tools.pytest_tools.get_gitlab_analyzer",
            return_value=mock_analyzer,
        ):
            # Setup mock responses
            mock_analyzer.get_job_trace.return_value = sample_pytest_log

            # Mock pytest parser
            with patch(
                "gitlab_analyzer.mcp.tools.pytest_tools.PytestLogParser.parse_pytest_log",
                return_value=sample_pytest_analysis,
            ):
                # Get the tool function
                tool_func = None
                for tool in list((await mcp_server.get_tools()).values()):
                    if tool.name == "extract_pytest_short_summary":
                        tool_func = tool.fn
                        break

                assert tool_func is not None

                # Execute tool
                result = await tool_func(project_id="test-project", job_id=1001)

                # Verify result structure
                assert "project_id" in result
                assert "job_id" in result
                assert "failed_tests" in result
                assert "failure_count" in result
                assert "mcp_info" in result

                # Verify short summary data
                assert result["failure_count"] == 1
                assert len(result["failed_tests"]) == 1

                summary = result["failed_tests"][0]
                assert summary["test_name"] == "test_example"
                assert summary["test_file"] == "test_file.py"
                assert summary["exception_type"] == "AssertionError"

    @pytest.mark.asyncio
    async def test_extract_pytest_statistics_success(
        self, mcp_server, mock_analyzer, sample_pytest_log, sample_pytest_analysis
    ):
        """Test successful statistics extraction."""
        with patch(
            "gitlab_analyzer.mcp.tools.pytest_tools.get_gitlab_analyzer",
            return_value=mock_analyzer,
        ):
            # Setup mock responses
            mock_analyzer.get_job_trace.return_value = sample_pytest_log

            # Mock pytest parser
            with patch(
                "gitlab_analyzer.mcp.tools.pytest_tools.PytestLogParser.parse_pytest_log",
                return_value=sample_pytest_analysis,
            ):
                # Get the tool function
                tool_func = None
                for tool in list((await mcp_server.get_tools()).values()):
                    if tool.name == "extract_pytest_statistics":
                        tool_func = tool.fn
                        break

                assert tool_func is not None

                # Execute tool
                result = await tool_func(project_id="test-project", job_id=1001)

                # Verify result structure
                assert "project_id" in result
                assert "job_id" in result
                assert "statistics" in result
                assert "mcp_info" in result

                # Verify statistics data
                stats = result["statistics"]
                assert stats["total_tests"] == 3
                assert stats["passed_tests"] == 2
                assert stats["failed_tests"] == 1
                assert stats["duration_seconds"] == 3.45

    @pytest.mark.asyncio
    async def test_analyze_pytest_job_complete_success(
        self, mcp_server, mock_analyzer, sample_pytest_log, sample_pytest_analysis
    ):
        """Test complete pytest job analysis."""
        with patch(
            "gitlab_analyzer.mcp.tools.pytest_tools.get_gitlab_analyzer",
            return_value=mock_analyzer,
        ):
            # Setup mock responses
            mock_analyzer.get_job_trace.return_value = sample_pytest_log

            # Mock pytest parser
            with patch(
                "gitlab_analyzer.mcp.tools.pytest_tools.PytestLogParser.parse_pytest_log",
                return_value=sample_pytest_analysis,
            ):
                # Get the tool function
                tool_func = None
                for tool in list((await mcp_server.get_tools()).values()):
                    if tool.name == "analyze_pytest_job_complete":
                        tool_func = tool.fn
                        break

                assert tool_func is not None

                # Execute tool
                result = await tool_func(project_id="test-project", job_id=1001)

                # Verify comprehensive result structure
                assert "project_id" in result
                assert "job_id" in result
                assert "detailed_failures" in result
                assert "failure_summary" in result
                assert "statistics" in result
                assert "mcp_info" in result

                # Verify all sections are populated
                assert len(result["detailed_failures"]) == 1
                assert len(result["failure_summary"]) == 1
                assert result["statistics"]["total_tests"] == 3

    @pytest.mark.asyncio
    async def test_pytest_tools_http_error(self, mcp_server, mock_analyzer):
        """Test pytest tools with HTTP error."""
        with patch(
            "gitlab_analyzer.mcp.tools.pytest_tools.get_gitlab_analyzer",
            return_value=mock_analyzer,
        ):
            # Setup mock to raise HTTP error
            mock_analyzer.get_job_trace.side_effect = httpx.HTTPError("API Error")

            # Test each pytest tool
            pytest_tools = [
                "extract_pytest_detailed_failures",
                "extract_pytest_short_summary",
                "extract_pytest_statistics",
                "analyze_pytest_job_complete",
            ]

            for tool_name in pytest_tools:
                tool_func = None
                for tool in list((await mcp_server.get_tools()).values()):
                    if tool.name == tool_name:
                        tool_func = tool.fn
                        break

                assert tool_func is not None

                # Execute tool
                result = await tool_func(project_id="test-project", job_id=1001)

                # Verify error handling
                assert "error" in result
                assert "Failed to" in result["error"]

    @pytest.mark.asyncio
    async def test_pytest_tools_empty_trace(self, mcp_server, mock_analyzer):
        """Test pytest tools with empty trace."""
        empty_analysis = PytestLogAnalysis(
            detailed_failures=[],
            short_summary=[],
            statistics=PytestStatistics(
                total_tests=0,
                passed=0,
                failed=0,
                skipped=0,
                errors=0,
                warnings=0,
                duration_seconds=0.0,
                duration_formatted="0.0s",
            ),
            has_failures_section=False,
            has_short_summary_section=False,
        )

        with patch(
            "gitlab_analyzer.mcp.tools.pytest_tools.get_gitlab_analyzer",
            return_value=mock_analyzer,
        ):
            # Setup mock responses
            mock_analyzer.get_job_trace.return_value = ""

            # Mock pytest parser
            with patch(
                "gitlab_analyzer.mcp.tools.pytest_tools.PytestLogParser.parse_pytest_log",
                return_value=empty_analysis,
            ):
                # Test detailed failures tool
                tool_func = None
                for tool in list((await mcp_server.get_tools()).values()):
                    if tool.name == "extract_pytest_detailed_failures":
                        tool_func = tool.fn
                        break

                assert tool_func is not None

                # Execute tool
                result = await tool_func(project_id="test-project", job_id=1001)

                # Verify empty result handling
                assert result["failure_count"] == 0
                assert result["detailed_failures"] == []

    async def test_register_pytest_tools(self):
        """Test that pytest tools are properly registered."""
        mcp = FastMCP("test")
        register_pytest_tools(mcp)

        # Verify tools are registered
        tool_names = [tool.name for tool in list((await mcp.get_tools()).values())]
        expected_tools = [
            "extract_pytest_detailed_failures",
            "extract_pytest_short_summary",
            "extract_pytest_statistics",
            "analyze_pytest_job_complete",
        ]

        for expected_tool in expected_tools:
            assert expected_tool in tool_names

        # Verify tool parameters
        for tool in list((await mcp.get_tools()).values()):
            if tool.name in expected_tools:
                assert "project_id" in str(tool.fn.__annotations__)
                assert "job_id" in str(tool.fn.__annotations__)

    def test_extract_pytest_errors_exception_handling(self):
        """Test exception handling in _extract_pytest_errors."""
        with patch(
            "gitlab_analyzer.mcp.tools.pytest_tools.PytestLogParser.parse_pytest_log",
            side_effect=Exception("Parser error"),
        ):
            result = _extract_pytest_errors("sample log")

            # Verify error is handled gracefully - fallback to generic parser
            assert result["parser_type"] == "generic"
            assert result["error_count"] == 0

    def test_extract_pytest_errors_with_none_statistics(self):
        """Test extracting pytest errors when statistics is None."""
        analysis = PytestLogAnalysis(
            detailed_failures=[],
            short_summary=[],
            statistics=None,
            has_failures_section=False,
            has_short_summary_section=False,
        )

        with patch(
            "gitlab_analyzer.mcp.tools.pytest_tools.PytestLogParser.parse_pytest_log",
            return_value=analysis,
        ):
            result = _extract_pytest_errors("sample log")

            # Verify basic structure is maintained without statistics
            assert result["error_count"] == 0
            assert result["warning_count"] == 0
            assert "total_tests" not in result
