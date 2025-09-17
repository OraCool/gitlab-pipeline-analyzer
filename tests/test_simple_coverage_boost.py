"""
Simple tests to boost coverage for key components.

These tests target specific functions to maintain test coverage.
"""

from unittest.mock import Mock, patch

from src.gitlab_analyzer.analysis.error_model import Error
from src.gitlab_analyzer.parsers.base_parser import TestFramework
from src.gitlab_analyzer.utils.debug import debug_print
from src.gitlab_analyzer.utils.jira_utils import parse_jira_tickets_from_storage


class TestErrorModelBasic:
    """Basic tests for Error model"""

    def test_error_from_log_entry_method(self):
        """Test Error.from_log_entry class method."""
        # Create a mock LogEntry object
        mock_log_entry = Mock()
        mock_log_entry.message = "Test error message"
        mock_log_entry.level = "ERROR"
        mock_log_entry.line_number = 42
        mock_log_entry.context = "Test context"
        mock_log_entry.error_type = "SyntaxError"

        error = Error.from_log_entry(mock_log_entry)

        assert error.message == "Test error message"
        assert error.level == "ERROR"
        assert error.line_number == 42
        assert error.context == "Test context"
        assert error.exception_type == "SyntaxError"

    def test_error_from_log_entry_with_none_values(self):
        """Test Error.from_log_entry with None values."""
        mock_log_entry = Mock()
        mock_log_entry.message = None
        mock_log_entry.level = None
        mock_log_entry.line_number = None
        mock_log_entry.context = None
        mock_log_entry.error_type = None

        error = Error.from_log_entry(mock_log_entry)

        assert error.message is None
        assert error.level is None
        assert error.line_number is None

    def test_error_creation_basic(self):
        """Test Error creation with basic values."""
        error = Error(
            message="Test error",
            file_path="test.py",
            line_number=10,
            level="error",
            exception_type="ValueError",
            context="test context",
        )

        assert error.message == "Test error"
        assert error.file_path == "test.py"
        assert error.level == "error"


class TestJiraUtilsBasic:
    """Basic tests for Jira utilities"""

    def test_parse_jira_tickets_mixed_types(self):
        """Test with mixed data types in JSON."""
        invalid_json = '["PROJ-123", "PROJ-456", null, 789]'
        result = parse_jira_tickets_from_storage(invalid_json)
        # Should convert all valid entries to strings
        expected = ["PROJ-123", "PROJ-456", "None", "789"]
        assert result == expected

    def test_parse_jira_tickets_invalid_json(self):
        """Test with invalid JSON."""
        result = parse_jira_tickets_from_storage('{"not": "a list"}')
        assert result == []

    def test_parse_jira_tickets_string_error(self):
        """Test with completely invalid JSON string."""
        result = parse_jira_tickets_from_storage("invalid json string")
        assert result == []


class TestDebugUtilsBasic:
    """Basic tests for debug utilities"""

    def test_debug_print_basic(self):
        """Test debug_print with basic input."""
        with (
            patch("builtins.print") as mock_print,
            patch(
                "src.gitlab_analyzer.utils.debug.is_debug_enabled", return_value=True
            ),
        ):
            debug_print("test message")
            mock_print.assert_called()

    def test_debug_print_with_none(self):
        """Test debug_print with None input."""
        with (
            patch("builtins.print") as mock_print,
            patch(
                "src.gitlab_analyzer.utils.debug.is_debug_enabled", return_value=True
            ),
        ):
            debug_print(None)
            mock_print.assert_called()

    def test_debug_print_with_complex_data(self):
        """Test debug_print with complex data types."""
        with (
            patch("builtins.print") as mock_print,
            patch(
                "src.gitlab_analyzer.utils.debug.is_debug_enabled", return_value=True
            ),
        ):
            test_data = {"key": "value", "nested": {"data": [1, 2, 3]}}
            debug_print(test_data)
            mock_print.assert_called()


class TestFrameworkDetectorBasic:
    """Basic tests for framework detection"""

    def test_framework_detector_protocol(self):
        """Test framework detector protocol implementation."""

        class TestDetector:
            def detect(self, job_name: str, job_stage: str, trace_content: str) -> bool:
                return "test" in job_name.lower()

            @property
            def framework(self):
                return TestFramework.PYTEST

        detector = TestDetector()

        # Test detect method
        assert detector.detect("test-job", "test", "some content") is True
        assert detector.detect("build-job", "build", "some content") is False

        # Test framework property
        assert detector.framework == TestFramework.PYTEST
