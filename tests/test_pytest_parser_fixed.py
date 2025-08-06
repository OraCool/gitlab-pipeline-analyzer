"""
Comprehensive unit tests for PytestLogParser class to improve coverage.

Copyright (c) 2025 Siarhei Skuratovich
Licensed under the MIT License - see LICENSE file for details
"""

from gitlab_analyzer.models.pytest_models import (
    PytestFailureDetail,
    PytestLogAnalysis,
    PytestShortSummary,
    PytestStatistics,
)
from gitlab_analyzer.parsers.pytest_parser import PytestLogParser


class TestPytestLogParser:
    """Test PytestLogParser initialization and functionality."""

    def test_pytest_log_parser_init(self):
        """Test PytestLogParser initialization."""
        parser = PytestLogParser()
        assert parser is not None

    def test_parse_pytest_log_empty(self):
        """Test parsing empty pytest log."""
        result = PytestLogParser.parse_pytest_log("")

        assert isinstance(result, PytestLogAnalysis)
        assert result.detailed_failures == []
        assert result.short_summary == []  # Returns empty list, not None
        assert isinstance(
            result.statistics, PytestStatistics
        )  # Returns empty stats, not None
        assert result.has_failures_section is False
        assert result.has_short_summary_section is False

    def test_parse_pytest_log_with_ansi_sequences(self):
        """Test parsing pytest log with ANSI escape sequences."""
        log_with_ansi = (
            "\x1b[31m=== FAILURES ===\x1b[0m\n"
            "\x1b[1m__ test_example __\x1b[0m\n"
            "def test_example():\n"
            "\x1b[31m>   assert False\x1b[0m\n"
            "\x1b[31mE   AssertionError\x1b[0m\n"
        )

        result = PytestLogParser.parse_pytest_log(log_with_ansi)

        assert isinstance(result, PytestLogAnalysis)
        assert result.has_failures_section is True

    def test_parse_pytest_log_basic_failure(self):
        """Test parsing basic pytest failure."""
        pytest_log = """
=== FAILURES ===
____________________ test_example ____________________

def test_example():
>   assert False
E   AssertionError

test_file.py:5: AssertionError
"""

        result = PytestLogParser.parse_pytest_log(pytest_log)

        assert isinstance(result, PytestLogAnalysis)
        assert result.has_failures_section is True

    def test_parse_pytest_log_short_summary(self):
        """Test parsing pytest short test summary."""
        pytest_log = """
=== short test summary info ===
FAILED test_file.py::test_example - AssertionError
FAILED test_file.py::test_another - ValueError: bad value
"""

        result = PytestLogParser.parse_pytest_log(pytest_log)

        assert isinstance(result, PytestLogAnalysis)
        assert result.has_short_summary_section is True
        assert len(result.short_summary) >= 1
        assert isinstance(result.short_summary[0], PytestShortSummary)

    def test_parse_pytest_log_statistics(self):
        """Test parsing pytest statistics."""
        pytest_log = """
=== 1 failed, 1 passed, 1 skipped in 2.34s ===
"""

        result = PytestLogParser.parse_pytest_log(pytest_log)

        assert isinstance(result, PytestLogAnalysis)
        assert result.statistics is not None
        assert isinstance(result.statistics, PytestStatistics)
        assert result.statistics.failed == 1
        assert result.statistics.passed == 1
        assert result.statistics.skipped == 1
        assert result.statistics.duration_seconds == 2.34

    def test_extract_detailed_failures_multiple_sections(self):
        """Test extracting failures from multiple FAILURES sections."""
        pytest_log = """
=== FAILURES ===
____________________ test_first ____________________
First failure content

=== ERRORS ===
Some errors here

=== FAILURES ===
____________________ test_second ____________________
Second failure content
"""

        result = PytestLogParser._extract_detailed_failures(pytest_log)

        assert isinstance(result, list)

    def test_parse_single_failure_invalid_header(self):
        """Test parsing single failure with invalid header."""
        # Test with coverage report header (should be filtered out)
        result = PytestLogParser._parse_single_failure(
            "coverage report", "Some coverage content"
        )
        assert result is None

        # Test with empty header
        result = PytestLogParser._parse_single_failure("", "Some content")
        assert result is None

    def test_parse_single_failure_valid_test(self):
        """Test parsing single failure with valid test."""
        test_content = """
def test_example():
>   assert False
E   AssertionError

test_file.py:5: AssertionError
"""

        result = PytestLogParser._parse_single_failure("test_example", test_content)

        assert result is not None
        assert isinstance(result, PytestFailureDetail)
        assert "test_example" in result.test_name

    def test_parse_single_failure_with_parameters(self):
        """Test parsing single failure with test parameters."""
        result = PytestLogParser._parse_single_failure(
            "test_params[value1-value2]", "Test content"
        )

        assert result is not None
        assert "test_params" in result.test_name
        assert result.test_parameters == "value1-value2"

    def test_is_valid_test_header(self):
        """Test validation of test headers."""
        # Valid test headers
        assert PytestLogParser._is_valid_test_header("test_example") is True
        assert PytestLogParser._is_valid_test_header("test_with_params[value]") is True
        assert PytestLogParser._is_valid_test_header("TestClass::test_method") is True

        # Invalid headers (coverage reports, etc.)
        assert PytestLogParser._is_valid_test_header("coverage report") is False
        assert PytestLogParser._is_valid_test_header("") is False

    def test_parse_traceback(self):
        """Test parsing traceback information."""
        content = """
def test_example():
    def helper():
        raise ValueError("error")
>   helper()

test_file.py:5:
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _

def helper():
>   raise ValueError("error")
E   ValueError: error

test_file.py:2: ValueError
"""

        traceback = PytestLogParser._parse_traceback(content)

        assert isinstance(traceback, list)

    def test_extract_short_summary_basic(self):
        """Test extracting short test summary."""
        log_text = """
=== short test summary info ===
FAILED test_file.py::test_one - AssertionError
FAILED test_file.py::test_two - ValueError: bad value
"""

        summary = PytestLogParser._extract_short_summary(log_text)

        assert len(summary) >= 1
        assert isinstance(summary[0], PytestShortSummary)

    def test_extract_short_summary_no_summary(self):
        """Test extracting short summary when none present."""
        log_text = "No short summary here"

        summary = PytestLogParser._extract_short_summary(log_text)

        assert summary == []

    def test_extract_statistics_basic(self):
        """Test extracting basic statistics."""
        log_text = "=== 3 failed, 2 passed, 1 skipped in 5.67s ==="

        stats = PytestLogParser._extract_statistics(log_text)

        assert stats is not None
        assert isinstance(stats, PytestStatistics)
        assert stats.failed == 3
        assert stats.passed == 2
        assert stats.skipped == 1
        assert stats.duration_seconds == 5.67

    def test_extract_statistics_various_formats(self):
        """Test extracting statistics in various formats."""
        test_cases = [
            ("=== 1 failed in 2.34s ===", {"failed": 1, "duration_seconds": 2.34}),
            ("=== 5 passed in 1.00s ===", {"passed": 5, "duration_seconds": 1.00}),
            (
                "=== 1 failed, 2 skipped in 0.5s ===",
                {"failed": 1, "skipped": 2, "duration_seconds": 0.5},
            ),
            (
                "=== 1 error, 1 passed in 3s ===",
                {"errors": 1, "passed": 1, "duration_seconds": 3.0},
            ),
        ]

        for log_line, expected in test_cases:
            stats = PytestLogParser._extract_statistics(log_line)
            assert stats is not None

            for key, value in expected.items():
                assert getattr(stats, key) == value

    def test_extract_statistics_no_stats(self):
        """Test extracting statistics when none present."""
        log_text = "No statistics here"

        stats = PytestLogParser._extract_statistics(log_text)

        assert isinstance(stats, PytestStatistics)
        assert stats.total_tests == 0

    def test_complex_pytest_log_parsing(self):
        """Test parsing a complex pytest log with all sections."""
        complex_log = """
=== test session starts ===
platform linux -- Python 3.8.10
collected 5 items

=== FAILURES ===
____________________ test_first ____________________

def test_first():
>   assert 1 == 2
E   AssertionError

test_file.py:5: AssertionError

=== short test summary info ===
FAILED test_file.py::test_first - AssertionError

=== 1 failed, 1 passed, 2 skipped in 3.45s ===
"""

        result = PytestLogParser.parse_pytest_log(complex_log)

        assert isinstance(result, PytestLogAnalysis)
        assert result.has_failures_section is True
        assert result.has_short_summary_section is True
        assert result.statistics is not None
        assert result.statistics.failed == 1
        assert result.statistics.passed == 1
        assert result.statistics.skipped == 2
        assert result.statistics.duration_seconds == 3.45

    def test_inheritance_from_base_parser(self):
        """Test that PytestLogParser inherits from BaseParser."""
        from gitlab_analyzer.parsers.base_parser import BaseParser

        assert issubclass(PytestLogParser, BaseParser)

        # Test that it can use base parser methods
        cleaned = PytestLogParser.clean_ansi_sequences("\x1b[31mRed\x1b[0m")
        assert cleaned == "Red"

    def test_parse_pytest_log_real_world_example(self):
        """Test with a real-world pytest log example."""
        real_log = """
==================================== FAILURES ====================================
_________________________ TestMyClass.test_method _________________________

self = <test_example.TestMyClass object at 0x7f8b8c0d2e48>

    def test_method(self):
        obj = MyClass()
>       assert obj.value == 42
E       AssertionError: assert 0 == 42
E        +  where 0 = <example.MyClass object at 0x7f8b8c0d2e80>.value

test_example.py:15: AssertionError

=========================== short test summary info ============================
FAILED test_example.py::TestMyClass::test_method - AssertionError: assert 0 == 42

========================= 1 failed, 2 passed in 0.23s =======================
"""

        result = PytestLogParser.parse_pytest_log(real_log)

        assert isinstance(result, PytestLogAnalysis)
        assert result.has_failures_section is True
        assert result.has_short_summary_section is True
        assert result.statistics is not None
        assert result.statistics.failed == 1
        assert result.statistics.passed == 2
        assert result.statistics.duration_seconds == 0.23
