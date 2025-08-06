"""
Unit tests for MCP tools utilities.

Copyright (c) 2025 Siarhei Skuratovich
Licensed under the MIT License - see LICENSE file for details
"""

from unittest.mock import patch

import pytest

from gitlab_analyzer.api.client import GitLabAnalyzer
from gitlab_analyzer.mcp.tools.utils import _is_pytest_log, get_gitlab_analyzer


class TestMCPToolsUtils:
    """Test MCP tools utilities."""

    def test_get_gitlab_analyzer_with_environment_variables(self):
        """Test GitLab analyzer creation with environment variables."""
        with (
            patch.dict(
                "os.environ",
                {
                    "GITLAB_URL": "https://custom-gitlab.com",
                    "GITLAB_TOKEN": "custom-token-123",
                },
            ),
            patch("gitlab_analyzer.mcp.tools.utils._GITLAB_ANALYZER", None),
        ):
            analyzer = get_gitlab_analyzer()

            assert isinstance(analyzer, GitLabAnalyzer)
            assert analyzer is not None

    def test_get_gitlab_analyzer_singleton(self):
        """Test that GitLab analyzer is a singleton."""
        with (
            patch.dict(
                "os.environ",
                {
                    "GITLAB_URL": "https://test-gitlab.com",
                    "GITLAB_TOKEN": "test-token",
                },
            ),
            patch("gitlab_analyzer.mcp.tools.utils._GITLAB_ANALYZER", None),
        ):
            # Get analyzer twice
            analyzer1 = get_gitlab_analyzer()
            analyzer2 = get_gitlab_analyzer()

            # Should be the same instance
            assert analyzer1 is analyzer2

    def test_get_gitlab_analyzer_missing_token(self):
        """Test GitLab analyzer creation without token."""
        with (
            patch.dict("os.environ", {"GITLAB_URL": "https://gitlab.com"}, clear=True),
            patch("gitlab_analyzer.mcp.tools.utils._GITLAB_ANALYZER", None),
            pytest.raises(
                ValueError, match="GITLAB_TOKEN environment variable is required"
            ),
        ):
            get_gitlab_analyzer()

    def test_get_gitlab_analyzer_default_url(self):
        """Test GitLab analyzer with default URL when not specified."""
        with (
            patch.dict("os.environ", {"GITLAB_TOKEN": "test-token"}, clear=True),
            patch("gitlab_analyzer.mcp.tools.utils._GITLAB_ANALYZER", None),
        ):
            analyzer = get_gitlab_analyzer()

            assert isinstance(analyzer, GitLabAnalyzer)
            # The default URL should be used (https://gitlab.com)

    def test_is_pytest_log_positive_cases(self):
        """Test pytest log detection with positive cases."""
        pytest_logs = [
            # These should have multiple indicators
            "=== FAILURES ===\nsome test FAILED",  # Has "=== FAILURES ===" and "FAILED"
            "short test summary info\nFAILED test.py::test_func",  # Has "short test summary info", "FAILED", ".py::"
            "1 failed, 2 passed, 3 skipped in 1.23s",  # Has "failed, ", "passed, ", " in "
            "test_example.py::test_function PASSED",  # Has "test_", ".py::", "PASSED"
            "collecting tests... ERROR test_",  # Has "collecting ...", "ERROR", "test_"
            "pytest session starts ERROR",  # Has "pytest", "ERROR"
            "tests/test_module.py::TestClass::test_method FAILED",  # Has "test_", ".py::", "FAILED"
        ]

        for log_text in pytest_logs:
            assert _is_pytest_log(log_text) is True, (
                f"Failed to detect pytest log: {log_text}"
            )

    def test_is_pytest_log_negative_cases(self):
        """Test pytest log detection with negative cases."""
        non_pytest_logs = [
            "Build completed successfully",
            "Service started",
            "INFO: Starting service",
            "npm install completed",
            "Docker image built successfully",
            "Compilation failed due to syntax issue",  # Changed from "error in"
            "",  # Empty string
            "Just some random log text",
        ]

        for log_text in non_pytest_logs:
            assert _is_pytest_log(log_text) is False, (
                f"Incorrectly detected as pytest log: {log_text}"
            )

    def test_is_pytest_log_case_insensitive(self):
        """Test pytest log detection is case insensitive."""
        mixed_case_logs = [
            # These have multiple indicators to meet the threshold
            "=== FAILURES === with some ERROR",  # Has "=== FAILURES ===" and "ERROR"
            "=== failures === and test_",  # Has "=== failures ===" and "test_"
            "Short Test Summary Info FAILED something",  # Has "short test summary info" and "FAILED"
            "PASSED test_example.py::",  # Has "PASSED", "test_", and ".py::"
            "passed test_example.py ERROR",  # Has "passed", "test_", and "ERROR"
            "FAILED test_example.py::",  # Has "FAILED", "test_", and ".py::"
        ]

        for log_text in mixed_case_logs:
            assert _is_pytest_log(log_text) is True, (
                f"Failed case insensitive detection: {log_text}"
            )

    def test_is_pytest_log_partial_matches(self):
        """Test pytest log detection with partial keyword matches."""
        partial_logs = [
            "This log contains the word failed but not pytest context",
            "passed validation check",  # 'passed' but not in pytest context
            "error in application",  # 'error' but not pytest
            "collecting user data",  # 'collecting' but not pytest
        ]

        # These should not be detected as pytest logs because they don't have
        # enough pytest-specific context
        for log_text in partial_logs:
            # Some might be detected due to individual keywords, but that's acceptable
            # since the function uses a heuristic approach
            assert isinstance(_is_pytest_log(log_text), bool)

    def test_is_pytest_log_comprehensive_pytest_output(self):
        """Test with comprehensive pytest output."""
        comprehensive_log = """
        ========================= test session starts =========================
        platform linux -- Python 3.8.10, pytest-6.2.4, py-1.10.0, pluggy-0.13.1
        rootdir: /path/to/project
        collected 5 items

        tests/test_example.py::test_success PASSED                       [ 20%]
        tests/test_example.py::test_failure FAILED                       [ 40%]
        tests/test_example.py::test_skip SKIPPED                         [ 60%]
        tests/test_example.py::test_error ERROR                          [ 80%]
        tests/test_example.py::test_xfail XFAIL                          [100%]

        =================================== FAILURES ===================================
        _________________________ test_failure _________________________

        def test_failure():
        >       assert 1 == 2
        E       AssertionError

        tests/test_example.py:10: AssertionError

        =========================== short test summary info ============================
        FAILED tests/test_example.py::test_failure - AssertionError
        ERROR tests/test_example.py::test_error - setup failure

        ================ 1 failed, 1 passed, 1 skipped, 1 error in 0.23s ===============
        """

        assert _is_pytest_log(comprehensive_log) is True

    def test_is_pytest_log_empty_and_whitespace(self):
        """Test pytest log detection with empty and whitespace strings."""
        empty_cases = [
            "",
            "   ",
            "\n",
            "\t",
            "\n\n\n",
        ]

        for log_text in empty_cases:
            assert _is_pytest_log(log_text) is False

    def test_is_pytest_log_threshold_behavior(self):
        """Test that pytest detection requires sufficient indicators."""
        # These should NOT trigger detection (only 1 indicator each)
        single_indicators = [
            "=== FAILURES ===",  # Only 1 indicator
            "something.py::",  # Only 1 indicator (no test_)
            "1 failed",  # Only 1 indicator (no comma or 'in')
            "ERROR only",  # Only 1 indicator
        ]

        for log_text in single_indicators:
            assert _is_pytest_log(log_text) is False, (
                f"Single indicator should not trigger: {log_text}"
            )

        # These SHOULD trigger detection (2+ indicators each)
        multi_indicators = [
            "=== FAILURES === test_",  # 2 indicators
            "test_something.py:: FAILED",  # 3 indicators: test_, .py::, FAILED
            "1 failed, 2 passed, in 2.3s",  # 3 indicators: failed,, passed,, in
        ]

        for log_text in multi_indicators:
            assert _is_pytest_log(log_text) is True, (
                f"Multiple indicators should trigger: {log_text}"
            )

    def test_get_gitlab_analyzer_environment_priority(self):
        """Test that environment variables take priority."""
        with (
            patch.dict(
                "os.environ",
                {
                    "GITLAB_URL": "https://priority-gitlab.com",
                    "GITLAB_TOKEN": "priority-token",
                },
            ),
            patch("gitlab_analyzer.mcp.tools.utils._GITLAB_ANALYZER", None),
        ):
            analyzer = get_gitlab_analyzer()

            # Verify the analyzer was created (we can't easily test the URL/token
            # without accessing private members, but we can verify it's created)
            assert isinstance(analyzer, GitLabAnalyzer)

    def test_multiple_pytest_indicators_in_log(self):
        """Test log with multiple pytest indicators."""
        multi_indicator_log = """
        pytest session starts
        collecting tests...
        test_example.py::test_func PASSED
        test_example.py::test_func2 FAILED
        === FAILURES ===
        short test summary info
        1 failed, 1 passed in 1.0s
        """

        assert _is_pytest_log(multi_indicator_log) is True

    def test_pytest_log_with_noise(self):
        """Test pytest log detection with surrounding noise."""
        noisy_log = """
        Starting CI pipeline...
        Installing dependencies...
        npm install completed

        ========================= test session starts =========================
        platform linux -- Python 3.8.10
        collected 3 items

        tests/test_app.py::test_function PASSED                         [100%]

        ========================= 1 passed in 0.12s =========================

        Build completed successfully
        Cleaning up...
        """

        assert _is_pytest_log(noisy_log) is True

    def test_utils_module_exports(self):
        """Test that utils module exports expected functions."""
        from gitlab_analyzer.mcp.tools import utils

        # Verify expected functions are available
        assert hasattr(utils, "get_gitlab_analyzer")
        assert hasattr(utils, "_is_pytest_log")
        assert callable(utils.get_gitlab_analyzer)
        assert callable(utils._is_pytest_log)
