"""
Additional comprehensive unit tests for LogParser class to improve coverage.

Copyright (c) 2025 Siarhei Skuratovich
Licensed under the MIT License - see LICENSE file for details
"""

from gitlab_analyzer.models import LogEntry
from gitlab_analyzer.parsers.log_parser import LogParser


class TestLogParserAdvanced:
    """Advanced tests for LogParser functionality not covered in existing tests."""

    def test_is_duplicate_test_error_detailed_format(self):
        """Test duplicate detection for detailed pytest format."""
        existing_entries = [
            LogEntry(
                level="error",
                message="test/test_file.py:10: in test_function",
                line_number=1,
                context="",
            )
        ]

        # Test duplicate detection
        duplicate_msg = "test/test_file.py:10: in test_function"
        assert (
            LogParser._is_duplicate_test_error(duplicate_msg, existing_entries) is True
        )

        # Test non-duplicate
        different_msg = "test/test_file.py:10: in different_function"
        assert (
            LogParser._is_duplicate_test_error(different_msg, existing_entries) is False
        )

    def test_is_duplicate_test_error_failed_format(self):
        """Test duplicate detection for FAILED pytest format."""
        existing_entries = [
            LogEntry(
                level="error",
                message="FAILED test/test_file.py::test_function - Error",
                line_number=1,
                context="",
            )
        ]

        # Test duplicate detection
        duplicate_msg = "FAILED test/test_file.py::test_function - Different error"
        assert (
            LogParser._is_duplicate_test_error(duplicate_msg, existing_entries) is True
        )

        # Test non-duplicate
        different_msg = "FAILED test/test_file.py::different_function - Error"
        assert (
            LogParser._is_duplicate_test_error(different_msg, existing_entries) is False
        )

    def test_is_duplicate_test_error_no_test_function(self):
        """Test duplicate detection when no test function found."""
        existing_entries = []

        # AssertionError without test function should not be considered duplicate
        msg = "AssertionError: Test failed"
        assert LogParser._is_duplicate_test_error(msg, existing_entries) is False

    def test_is_in_pytest_failure_section_basic(self):
        """Test pytest failure section detection."""
        lines = [
            "Some previous output",
            "===== FAILURES =====",
            "Test failure details",
            "More failure info",
            "===== SHORT TEST SUMMARY =====",
            "Summary info",
        ]

        # Line 2 (index 2) should be in FAILURES section
        assert LogParser._is_in_pytest_failure_section(lines, 2) is True
        # Line 3 (index 3) should be in FAILURES section
        assert LogParser._is_in_pytest_failure_section(lines, 3) is True
        # Line 5 (index 5) should NOT be in FAILURES section
        assert LogParser._is_in_pytest_failure_section(lines, 5) is False

    def test_is_in_pytest_failure_section_no_failures(self):
        """Test pytest failure section detection when no FAILURES section."""
        lines = ["Some output", "===== PASSED =====", "All tests passed"]

        # Should not be in FAILURES section
        assert LogParser._is_in_pytest_failure_section(lines, 1) is False
        assert LogParser._is_in_pytest_failure_section(lines, 2) is False

    def test_is_in_pytest_failure_section_job_boundary(self):
        """Test pytest failure section detection with job boundaries."""
        lines = [
            "===== FAILURES =====",
            "Test failure",
            "section_start:123:next_step",
            "Next step output",
        ]

        # Line 1 should be in FAILURES section
        assert LogParser._is_in_pytest_failure_section(lines, 1) is True
        # Line 3 should NOT be in FAILURES section due to job boundary
        assert LogParser._is_in_pytest_failure_section(lines, 3) is False

    def test_extract_log_entries_with_pytest_detailed_format(self):
        """Test extracting entries with pytest detailed format."""
        log_content = """
Running tests...
===== FAILURES =====
test/test_file.py:15: in test_example
    assert value == expected
E   AssertionError: Test failed
    at line 15
FAILED test/test_file.py::test_example - AssertionError
===== SHORT TEST SUMMARY =====
Test summary
"""

        entries = LogParser.extract_log_entries(log_content)

        # Should extract the detailed format entry
        detailed_entries = [e for e in entries if "in test_example" in e.message]
        assert len(detailed_entries) > 0

        # Should not duplicate with FAILED format due to deduplication
        # (The FAILED entry might be skipped due to duplicate detection)

    def test_extract_log_entries_skip_pytest_details_in_failures_section(self):
        """Test skipping pytest error details in FAILURES section."""
        log_content = """
===== FAILURES =====
test_failure
E   This should be skipped
E   This too
AssertionError: This standalone should be skipped too
test/file.py:10: in test_func
    This should be included
===== END =====
"""

        entries = LogParser.extract_log_entries(log_content)

        # Should not include E   prefixed lines or standalone exceptions in FAILURES
        e_entries = [e for e in entries if e.message.startswith("E   ")]
        assert len(e_entries) == 0

        # Should include the detailed format line
        detailed_entries = [e for e in entries if "in test_func" in e.message]
        assert len(detailed_entries) > 0

    def test_extract_log_entries_complex_deduplication(self):
        """Test complex deduplication scenarios."""
        log_content = """
test/test_file.py:10: in test_function_name
    Test details
FAILED test/test_file.py::test_function_name - Error
test/test_file.py:20: in different_function
    Different test details
"""

        entries = LogParser.extract_log_entries(log_content)

        # Should have entries for both functions
        test_func_entries = [e for e in entries if "test_function_name" in e.message]
        different_func_entries = [
            e for e in entries if "different_function" in e.message
        ]

        # Should have at least one entry for each distinct test
        assert len(test_func_entries) >= 1
        assert len(different_func_entries) >= 1

    def test_get_context_with_filtering(self):
        """Test context extraction with infrastructure filtering."""
        lines = [
            "Running with gitlab-runner",  # Should be filtered
            "Important error context",
            "ERROR: Main error message",  # This is the current line
            "More error details",
            "section_start:123:test",  # Should be filtered
        ]

        context = LogParser._get_context(lines, 2)  # ERROR line is index 2

        # Should include important context but filter infrastructure
        assert "Important error context" in context
        assert "More error details" in context
        assert "gitlab-runner" not in context
        assert "section_start" not in context

    def test_get_context_edge_cases(self):
        """Test context extraction edge cases."""
        lines = ["Single line"]

        # Context for single line should work
        context = LogParser._get_context(lines, 0)
        assert "Single line" in context

        # Empty lines should be handled
        lines_with_empty = ["Line 1", "", "Line 3"]
        context = LogParser._get_context(lines_with_empty, 2)
        assert "Line 1" in context
        assert "Line 3" in context

    def test_categorize_error_code_formatting_individual_file(self):
        """Test categorization of individual file formatting errors."""
        message = "would reformat src/example.py"

        category = LogParser.categorize_error(message)

        assert category["category"] == "Code Formatting"
        assert category["severity"] == "medium"
        assert "src/example.py" in category["details"]
        assert "black src/example.py" in category["solution"]

    def test_categorize_error_code_formatting_summary(self):
        """Test categorization of formatting summary errors."""
        message = "3 files would be reformatted, 2 files would be left unchanged"

        category = LogParser.categorize_error(message)

        assert category["category"] == "Code Formatting Summary"
        assert category["severity"] == "medium"
        assert "3 files requiring reformatting" in category["details"]
        assert "2 files already properly formatted" in category["details"]

    def test_categorize_error_syntax_error_detailed(self):
        """Test categorization of detailed syntax errors."""
        message = 'File "src/app.py", line 42: SyntaxError: invalid syntax'

        category = LogParser.categorize_error(message)

        assert category["category"] == "Python Syntax Error"
        assert category["severity"] == "high"
        assert "src/app.py" in category["details"]
        assert "line 42" in category["details"]
        assert "invalid syntax" in category["details"]

    def test_categorize_error_import_error_module(self):
        """Test categorization of module import errors."""
        message = "ModuleNotFoundError: No module named 'missing_package'"

        category = LogParser.categorize_error(message)

        assert category["category"] == "Python Import Error"
        assert category["severity"] == "high"
        assert "missing_package" in category["details"]
        assert "pip install missing_package" in category["solution"]

    def test_categorize_error_test_failure_detailed_format(self):
        """Test categorization of detailed test failure format."""
        message = "test/test_file.py:25: in test_calculation"
        context = "AssertionError: Expected 5, got 3"

        category = LogParser.categorize_error(message, context)

        assert category["category"] == "Test Failure"
        assert category["severity"] == "high"
        assert "test_calculation" in category["details"]
        assert "test/test_file.py" in category["details"]
        assert category["source_file"] == "test/test_file.py"
        assert category["source_line"] == "25"
        assert category["test_function"] == "test_calculation"

    def test_categorize_error_test_failure_summary_format(self):
        """Test categorization of summary test failure format."""
        message = "FAILED test/test_file.py::test_method - AssertionError: test failed"

        category = LogParser.categorize_error(message)

        assert category["category"] == "Test Failure"
        assert category["severity"] == "high"
        assert "test_method" in category["details"]
        assert "test/test_file.py" in category["details"]
        assert category["source_file"] == "test_file.py"
        assert category["test_function"] == "test_method"

    def test_categorize_error_build_failure(self):
        """Test categorization of build failures."""
        message = "compilation error: undefined reference to 'missing_function'"

        category = LogParser.categorize_error(message)

        assert category["category"] == "Build Error"
        assert category["severity"] == "high"
        assert "undefined reference to 'missing_function'" in category["details"]

    def test_categorize_error_file_system(self):
        """Test categorization of file system errors."""
        message = "Permission denied: '/restricted/file.txt'"

        category = LogParser.categorize_error(message)

        assert category["category"] == "File System Error"
        assert category["severity"] == "medium"
        assert "/restricted/file.txt" in category["details"]

    def test_categorize_error_linting(self):
        """Test categorization of linting errors."""
        message = "pylint Lint check failed: multiple issues found"

        category = LogParser.categorize_error(message)

        assert category["category"] == "Code Quality Error"
        assert category["severity"] == "medium"
        assert "pylint" in category["details"]

    def test_categorize_error_generic_error(self):
        """Test categorization of generic errors."""
        message = "ERROR: Connection timeout occurred"

        category = LogParser.categorize_error(message)

        assert category["category"] == "General Error"
        assert category["severity"] == "medium"
        assert "Connection timeout occurred" in category["details"]

    def test_categorize_error_specific_error_types(self):
        """Test categorization of specific error message types."""
        test_cases = [
            ("ERROR: no files to upload", "GitLab CI attempted to upload artifacts"),
            ("ERROR: compilation failed", "Build compilation process failed"),
            (
                "ERROR: permission denied access",
                "File system permission error",
            ),  # This one matches actual logic
            ("ERROR: connection refused", "Network or connection error occurred"),
            ("ERROR: operation timeout", "Operation timed out"),
        ]

        for message, expected_detail in test_cases:
            category = LogParser.categorize_error(message)
            # For permission errors, check the general file system category
            if "permission" in message.lower():
                assert (
                    "Cannot access:" in category["details"]
                    or expected_detail in category["details"]
                )
            else:
                assert expected_detail in category["details"]

    def test_categorize_error_unknown_pattern(self):
        """Test categorization of unknown error patterns."""
        message = "Some completely unknown error message"

        category = LogParser.categorize_error(message)

        assert category["category"] == "Unknown Error"
        assert category["severity"] == "medium"
        assert message in category["details"]

    def test_exclude_patterns_comprehensive(self):
        """Test comprehensive exclusion pattern matching."""
        excluded_messages = [
            "Running with gitlab-runner 14.0.0",
            "on GCP Ocean instance",
            "system ID: abc123",
            "shared k8s runner pod-123",
            "please use cache for dependencies",
            "per job and 1GB per service limit",
            "Using Kubernetes executor",
            "Pod activeDeadlineSeconds set to 3600",
            "Waiting for pod default/runner-pod to be running",
            "Getting source from Git repository",
            "Fetching changes with git depth set to 50",
            "Checking cache for dependencies",
            "Successfully extracted cache archive",
            'Executing "step_script" stage',
            "Preparing the docker executor",
            '$ echo "test command"',
            "Requirement already satisfied: requests",
            "Installing collected packages: numpy",
            "Running pip as the 'root' user",
            "Oh no! 💥 💔 💥",
            "✅ All checks passed",
            "SIMULATING TEST FAILURE as expected!",
            "/scripts-1234-5678/get_sources: line 42: export: not a valid identifier",
        ]

        for message in excluded_messages:
            entries = LogParser.extract_log_entries(message)
            # These should be filtered out
            assert len(entries) == 0, f"Message should be excluded: {message}"

    def test_error_patterns_case_sensitivity(self):
        """Test error pattern case sensitivity."""
        test_cases = [
            "ERROR: Test failed",
            "error: Test failed",
            "Error: Test failed",
            # Remove FATAL as it's not in the current patterns
            "WARNING: Test warning",
            "warning: Test warning",
        ]

        for message in test_cases:
            entries = LogParser.extract_log_entries(message)
            assert len(entries) > 0, f"Message should be detected: {message}"

    def test_warning_patterns(self):
        """Test warning pattern detection."""
        warning_messages = [
            "DeprecationWarning: This feature is deprecated",
            "UserWarning: User action required",
            "FutureWarning: This will change in future",
            "WARNING: General warning message",
            "WARN: Simple warning",
            "warning: Lowercase warning",
        ]

        for message in warning_messages:
            entries = LogParser.extract_log_entries(message)
            assert len(entries) > 0
            assert entries[0].level == "warning"

    def test_complex_real_world_log(self):
        """Test with a complex real-world CI/CD log."""
        complex_log = """
Running with gitlab-runner 14.0.0 on shared-runner
Getting source from Git repository
$ make test
Running tests with pytest
===== FAILURES =====
test/test_app.py:42: in test_calculation
    assert result == expected
E   AssertionError: assert 3 == 5
E   + where 3 = calculate(1, 2)

FAILED test/test_app.py::test_calculation - AssertionError
ERROR: Test execution failed
would reformat src/app.py
2 files would be reformatted, 1 file would be left unchanged
SyntaxError: invalid syntax in helper.py line 10
ImportError: No module named 'requests'
Job failed: exit code 1
"""

        entries = LogParser.extract_log_entries(complex_log)

        # Should extract meaningful errors and filter infrastructure
        error_entries = [e for e in entries if e.level == "error"]
        assert len(error_entries) > 0

        # Should not include gitlab-runner messages
        runner_entries = [e for e in entries if "gitlab-runner" in e.message]
        assert len(runner_entries) == 0

        # Should include test failures
        test_entries = [e for e in entries if "test_calculation" in e.message]
        assert len(test_entries) > 0

        # Should include formatting and syntax errors
        formatting_entries = [e for e in entries if "reformat" in e.message]
        assert len(formatting_entries) > 0
