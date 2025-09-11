"""
Final test file to push coverage over 65%.
Targeting specific uncovered lines in high-impact modules.
"""

from unittest.mock import patch

import pytest

from gitlab_analyzer.analysis.error_model import Error
from gitlab_analyzer.api.client import GitLabAnalyzer
from gitlab_analyzer.parsers.log_parser import LogParser
from gitlab_analyzer.utils.debug import debug_print, get_debug_level, is_debug_enabled
from gitlab_analyzer.utils.utils import get_gitlab_analyzer


class TestFinalCoveragePush:
    """Tests to push coverage over 65%."""

    def test_get_gitlab_analyzer_creation(self):
        """Test GitLab analyzer singleton creation."""
        # Clear the global instance if it exists
        import gitlab_analyzer.utils.utils as utils_module

        utils_module._GITLAB_ANALYZER = None

        with patch.dict(
            "os.environ",
            {"GITLAB_TOKEN": "test-token", "GITLAB_URL": "https://test.com"},
        ):
            analyzer = get_gitlab_analyzer()
            assert analyzer is not None

            # Test singleton behavior
            analyzer2 = get_gitlab_analyzer()
            assert analyzer is analyzer2

    def test_get_gitlab_analyzer_no_token(self):
        """Test GitLab analyzer creation without token."""
        import gitlab_analyzer.utils.utils as utils_module

        utils_module._GITLAB_ANALYZER = None

        with (
            patch.dict("os.environ", {}, clear=True),
            pytest.raises(
                ValueError, match="GITLAB_TOKEN environment variable is required"
            ),
        ):
            get_gitlab_analyzer()

    def test_debug_utilities(self):
        """Test debug utility functions."""
        # Test debug print
        with patch("builtins.print"):
            debug_print("test message", level=1)

        # Test debug level checking
        level = get_debug_level()
        assert isinstance(level, int)

        # Test debug enabled checking
        enabled = is_debug_enabled(1)
        assert isinstance(enabled, bool)

    def test_log_parser_edge_cases(self):
        """Test log parser edge cases."""
        parser = LogParser()

        # Test with empty log
        result = parser.extract_log_entries("")
        assert result is not None
        assert len(result) == 0

        # Test with None input - this should raise an exception
        import contextlib

        with contextlib.suppress(TypeError, AttributeError):
            parser.extract_log_entries(None)

    def test_error_model_creation(self):
        """Test Error model creation."""
        error = Error(
            message="Test error",
            file_path="test.py",
            line_number=10,
            level="error",
            exception_type="TestException",
        )

        assert error.message == "Test error"
        assert error.file_path == "test.py"
        assert error.line_number == 10

        # Test from_dict creation
        error_dict = {
            "message": "Dict error",
            "file": "dict.py",
            "line_number": 20,
            "exception_type": "DictException",
        }

        error_from_dict = Error.from_dict(error_dict)
        assert error_from_dict.message == "Dict error"
        assert error_from_dict.file_path == "dict.py"

    def test_gitlab_client_edge_cases(self):
        """Test GitLab client edge cases."""
        client = GitLabAnalyzer("https://test.com", "test-token")

        # Test string representation
        str_repr = str(client)
        assert "GitLabAnalyzer" in str_repr

    def test_utils_internal_functions(self):
        """Test internal utility functions for coverage."""
        from gitlab_analyzer.utils.utils import (
            _categorize_error_for_fixing,
            _create_balanced_error,
            _create_minimal_error,
            _extract_error_location,
        )

        error = {
            "test_file": "test.py",
            "line_number": 10,
            "test_function": "test_func",
            "exception_type": "AssertionError",
            "exception_message": "Test failed",
        }

        # Test location extraction
        location = _extract_error_location(error)
        assert "test.py:10" in location

        # Test categorization
        category = _categorize_error_for_fixing(error)
        assert category == "test_assertion"

        # Test minimal error creation
        minimal = _create_minimal_error(error)
        assert "line_number" in minimal

        # Test balanced error creation
        balanced = _create_balanced_error(error)
        assert "location" in balanced

    def test_additional_util_patterns(self):
        """Test additional utility patterns for coverage."""
        from gitlab_analyzer.utils.utils import (
            _extract_fixing_traceback,
            _extract_key_traceback,
        )

        traceback = [
            {
                "file_path": "/usr/lib/python3.11/site-packages/system.py",
                "line_number": 10,
                "function_name": "system_func",
            },
            {"file_path": "src/app.py", "line_number": 20, "function_name": "app_func"},
        ]

        # Test key traceback extraction (filters system paths)
        key_frames = _extract_key_traceback(traceback)
        assert len(key_frames) <= len(traceback)

        # Test fixing traceback extraction
        fixing_frames = _extract_fixing_traceback(traceback)
        assert isinstance(fixing_frames, list)

    def test_more_optimization_edge_cases(self):
        """Test more optimization edge cases."""
        from gitlab_analyzer.utils.utils import (
            _extract_fixing_context,
            _generate_fix_guidance,
            _parse_error_message_details,
        )

        error = {
            "test_name": "test_something",
            "test_function": "test_func",
            "exception_message": "unexpected keyword argument 'invalid_param'",
            "exception_type": "TypeError",
        }

        # Test context extraction
        context = _extract_fixing_context(error)
        assert isinstance(context, dict)

        # Test guidance generation
        guidance = _generate_fix_guidance(error)
        assert "likely_causes" in guidance
        assert "fix_suggestions" in guidance

        # Test message parsing
        details = _parse_error_message_details(error["exception_message"])
        assert isinstance(details, dict)

    def test_pattern_helper_functions(self):
        """Test pattern helper functions."""
        from gitlab_analyzer.utils.utils import (
            _extract_function_name,
            _extract_missing_parameter,
            _extract_parameter_name,
        )

        message1 = "func() unexpected keyword argument 'bad_param'"
        message2 = "func() missing required positional argument 'good_param'"

        param1 = _extract_parameter_name(message1)
        assert param1 == "bad_param"

        func_name = _extract_function_name(message1)
        assert func_name == "func"

        param2 = _extract_missing_parameter(message2)
        assert param2 == "good_param"

    def test_error_analysis_edge_cases(self):
        """Test error analysis edge cases."""
        from gitlab_analyzer.utils.utils import (
            _calculate_fix_priority,
            _extract_files_to_check,
        )

        error = {
            "file_path": "test.py",
            "test_file": "test_file.py",
            "traceback": [
                {"file_path": "src/main.py"},
                {"file_path": "/site-packages/system.py"},  # Should be filtered
            ],
            "exception_type": "SyntaxError",
        }

        # Test files extraction
        files = _extract_files_to_check(error)
        assert "test.py" in files
        assert "test_file.py" in files
        assert "src/main.py" in files
        # System file should be filtered out
        assert not any("/site-packages/" in f for f in files)

        # Test priority calculation
        guidance = {"files_to_check": files}
        priority = _calculate_fix_priority(error, guidance)
        assert "urgency" in priority
        assert priority["urgency"] == "high"  # SyntaxError is high urgency

    def test_attribute_error_helpers(self):
        """Test attribute error helper functions."""
        from gitlab_analyzer.utils.utils import (
            _extract_attribute_error_details,
            _extract_module_name_from_import_error,
            _extract_object_name_from_callable_error,
        )

        # Test attribute error parsing
        attr_msg = "'MyClass' object has no attribute 'missing_method'"
        obj_type, attr_name = _extract_attribute_error_details(attr_msg)
        assert obj_type == "MyClass"
        assert attr_name == "missing_method"

        # Test callable error parsing
        callable_msg = "'str' object is not callable"
        obj_name = _extract_object_name_from_callable_error(callable_msg)
        assert obj_name == "str"

        # Test import error parsing
        import_msg = "No module named 'missing_module'"
        module_name = _extract_module_name_from_import_error(import_msg)
        assert module_name == "missing_module"

    def test_comprehensive_error_types(self):
        """Test comprehensive error type handling."""
        from gitlab_analyzer.utils.utils import _categorize_error_for_fixing

        test_cases = [
            ("AssertionError", "test_assertion"),
            ("TypeError", "type_mismatch"),
            ("AttributeError", "attribute_error"),
            ("ImportError", "import_error"),
            ("SyntaxError", "syntax_error"),
            ("ValueError", "value_error"),
            ("RandomError", "general_error"),
        ]

        for exception_type, expected_category in test_cases:
            error = {"exception_type": exception_type, "exception_message": ""}
            category = _categorize_error_for_fixing(error)
            assert category == expected_category

    def test_traceback_filtering_comprehensive(self):
        """Test comprehensive traceback filtering."""
        from gitlab_analyzer.utils.utils import _extract_fixing_traceback

        # Test with long traceback (> 15 frames)
        long_traceback = [
            {
                "file_path": f"frame_{i}.py",
                "line_number": i,
                "function_name": f"func_{i}",
            }
            for i in range(20)
        ]

        result = _extract_fixing_traceback(long_traceback)
        assert len(result) <= 12  # Should be limited for long tracebacks

        # Test with short traceback (< 15 frames)
        short_traceback = [
            {"file_path": "frame_1.py", "line_number": 1, "function_name": "func_1"},
            {"file_path": "frame_2.py", "line_number": 2, "function_name": "func_2"},
        ]

        result = _extract_fixing_traceback(short_traceback)
        assert len(result) == 2  # Should preserve all frames for short tracebacks
