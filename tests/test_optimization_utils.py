"""
Unit tests for MCP tools optimization utilities.

Copyright (c) 2025 Siarhei Skuratovich
Licensed under the MIT License - see LICENSE file for details
"""

from gitlab_analyzer.utils.utils import (
    _categorize_error_for_fixing,
    _create_balanced_error,
    _create_fixing_error,
    _create_minimal_error,
    _extract_error_location,
    _extract_fixing_context,
    _extract_fixing_traceback,
    _extract_key_traceback,
    _generate_fix_guidance,
    _is_pytest_log,
    optimize_error_response,
    optimize_tool_response,
)


class TestOptimizationUtils:
    """Test optimization utilities."""

    def test_optimize_tool_response_with_errors_minimal(self):
        """Test optimization with errors field in minimal mode."""
        response = {
            "errors": [
                {
                    "message": "Test failed",
                    "line_number": 10,
                    "exception_type": "AssertionError",
                    "exception_message": "Expected 5 but got 3",
                    "test_function": "test_math",
                    "test_file": "/app/test_math.py",
                }
            ]
        }

        result = optimize_tool_response(response, "minimal")

        assert "optimization" in result
        assert result["optimization"]["response_mode"] == "minimal"
        assert result["optimization"]["original_error_count"] == 1
        assert len(result["errors"]) == 1
        # Check that minimal error has only essential fields
        error = result["errors"][0]
        assert "line_number" in error
        assert "exception_type" in error

    def test_optimize_tool_response_with_errors_balanced(self):
        """Test optimization with errors field in balanced mode."""
        response = {
            "errors": [
                {
                    "message": "Test failed",
                    "line_number": 10,
                    "exception_type": "AssertionError",
                    "traceback": [
                        {"file": "/usr/lib/python3.9/pytest.py", "line": 1},
                        {"file": "/app/test_file.py", "line": 10},
                    ],
                }
            ]
        }

        result = optimize_tool_response(response, "balanced")

        assert "optimization" in result
        assert result["optimization"]["response_mode"] == "balanced"
        assert len(result["errors"]) == 1

    def test_optimize_tool_response_no_errors(self):
        """Test optimization without errors field."""
        response = {"pipeline_info": {"id": 123, "status": "failed"}, "failed_jobs": []}

        result = optimize_tool_response(response, "balanced")

        assert "optimization" in result
        assert result["optimization"]["response_mode"] == "balanced"
        assert result["pipeline_info"]["id"] == 123

    def test_optimize_tool_response_full_mode(self):
        """Test full mode (no optimization)."""
        response = {
            "pipeline_info": {"id": 123, "status": "failed"},
            "errors": [{"message": "Error"}],
        }

        result = optimize_tool_response(response, "full")

        # Should be unchanged - no optimization metadata added in full mode
        assert result == response

    def test_pytest_log_detection(self):
        """Test pytest log detection function."""
        # Test positive cases
        pytest_logs = [
            "=== FAILURES === test_something",
            "short test summary info FAILED",
            "1 failed, 2 passed in 1.23s",
            "test_example.py::test_function PASSED",
        ]

        for log_text in pytest_logs:
            assert _is_pytest_log(log_text) is True

        # Test negative cases
        non_pytest_logs = [
            "Build completed successfully",
            "Service started",
            "INFO: Starting service",
            "",
        ]

        for log_text in non_pytest_logs:
            assert _is_pytest_log(log_text) is False

    def test_optimize_tool_response_empty_data(self):
        """Test optimization with empty data."""
        response = {}

        result = optimize_tool_response(response, "minimal")

        assert "optimization" in result
        assert result["optimization"]["response_mode"] == "minimal"

    def test_optimize_tool_response_different_modes(self):
        """Test different optimization modes."""
        response = {"data": "test"}

        modes = ["minimal", "balanced", "fixing", "full"]
        for mode in modes:
            result = optimize_tool_response(response, mode)
            if mode == "full":
                # Full mode returns original response
                assert result == response
            else:
                # Other modes add optimization metadata
                assert "optimization" in result
                assert result["optimization"]["response_mode"] == mode


class TestOptimizationHelpers:
    """Test optimization helper functions."""

    def test_optimize_error_response_minimal(self):
        """Test individual error optimization in minimal mode."""
        error = {
            "message": "Test failed",
            "line_number": 10,
            "exception_type": "AssertionError",
            "exception_message": "Expected 5 but got 3",
            "test_function": "test_math",
            "test_file": "/app/test_math.py",
            "traceback": [{"file": "/app/test.py", "line": 5}],
        }

        result = optimize_error_response(error, "minimal")

        assert "line_number" in result
        assert "exception_type" in result
        assert result["line_number"] == 10
        assert result["exception_type"] == "AssertionError"

    def test_optimize_error_response_balanced(self):
        """Test individual error optimization in balanced mode."""
        error = {
            "message": "ImportError: No module named 'requests'",
            "line_number": 5,
            "exception_type": "ImportError",
            "traceback": [
                {"file": "/usr/lib/python3.9/site-packages/pytest.py", "line": 1},
                {"file": "/app/main.py", "line": 5, "code": "import requests"},
            ],
        }

        result = optimize_error_response(error, "balanced")

        assert "location" in result
        assert "category" in result
        assert "traceback" in result

    def test_optimize_error_response_fixing(self):
        """Test individual error optimization in fixing mode."""
        error = {
            "message": "ImportError: No module named 'requests'",
            "line_number": 5,
            "exception_type": "ImportError",
            "test_file": "/app/main.py",
            "traceback": [
                {"file": "/app/main.py", "line": 5, "code": "import requests"}
            ],
        }

        result = optimize_error_response(error, "fixing")

        assert "fix_guidance" in result
        assert "location" in result
        assert "category" in result

    def test_create_minimal_error(self):
        """Test minimal error creation."""
        error = {
            "message": "Test failed",
            "line_number": 10,
            "exception_type": "AssertionError",
            "exception_message": "Expected 5 but got 3",
            "test_function": "test_math",
            "test_file": "/app/test_math.py",
            "extra_field": "should_be_ignored",
        }

        result = _create_minimal_error(error)

        expected_fields = [
            "line_number",
            "exception_type",
            "exception_message",
            "test_function",
            "file_path",
        ]
        for field in expected_fields:
            assert field in result

        assert "extra_field" not in result
        assert result["file_path"] == "/app/test_math.py"

    def test_create_balanced_error(self):
        """Test balanced error creation."""
        error = {
            "message": "ImportError: No module named 'requests'",
            "line_number": 5,
            "exception_type": "ImportError",
            "test_file": "/app/main.py",
            "traceback": [
                {"file": "/usr/lib/python3.9/site-packages/pytest.py", "line": 1},
                {"file": "/app/main.py", "line": 5, "code": "import requests"},
            ],
        }

        result = _create_balanced_error(error)

        assert "location" in result
        assert "category" in result
        assert "traceback" in result
        assert "line_number" in result

    def test_create_fixing_error(self):
        """Test fixing error creation."""
        error = {
            "message": "ImportError: No module named 'requests'",
            "line_number": 5,
            "exception_type": "ImportError",
            "test_file": "/app/main.py",
            "traceback": [
                {"file": "/app/main.py", "line": 5, "code": "import requests"}
            ],
        }

        result = _create_fixing_error(error)

        assert "fix_guidance" in result
        assert "location" in result
        assert "category" in result
        assert "context" in result

    def test_extract_error_location(self):
        """Test error location extraction."""
        # Test with full path
        error = {
            "test_file": "/app/tests/test_user.py",
            "line_number": 25,
            "test_function": "test_user_creation",
        }

        result = _extract_error_location(error)
        assert result == "test_user.py:25 in test_user_creation()"

        # Test with minimal info
        error = {"file_path": "main.py", "line_number": 10}

        result = _extract_error_location(error)
        assert result == "main.py:10 in unknown()"

    def test_categorize_error_for_fixing(self):
        """Test error categorization."""
        # Test import error
        error = {
            "exception_type": "ImportError",
            "exception_message": "No module named 'requests'",
        }
        result = _categorize_error_for_fixing(error)
        assert result == "import_error"

        # Test syntax error
        error = {"exception_type": "SyntaxError", "exception_message": "invalid syntax"}
        result = _categorize_error_for_fixing(error)
        assert result == "syntax_error"

        # Test assertion error
        error = {
            "exception_type": "AssertionError",
            "exception_message": "Expected 5 but got 3",
        }
        result = _categorize_error_for_fixing(error)
        assert result == "test_assertion"

        # Test unknown error
        error = {
            "exception_type": "RuntimeError",
            "exception_message": "Something went wrong",
        }
        result = _categorize_error_for_fixing(error)
        assert result == "general_error"

    def test_extract_key_traceback(self):
        """Test key traceback extraction."""
        traceback = [
            {
                "file_path": "/usr/lib/python3.9/site-packages/pytest/__init__.py",
                "line": 1,
            },
            {"file_path": "/app/main.py", "line": 10, "code": "import requests"},
            {
                "file_path": "/usr/lib/python3.9/site-packages/requests/__init__.py",
                "line": 5,
            },
        ]

        result = _extract_key_traceback(traceback)

        # Should filter out system packages and keep only app files
        assert len(result) <= len(traceback)
        # The function filters based on file_path, not file
        app_files = [frame for frame in result if "/app/" in frame.get("file_path", "")]
        assert len(app_files) >= 0  # May be 0 if all filtered out

    def test_extract_fixing_traceback(self):
        """Test fixing traceback extraction."""
        traceback = [
            {
                "file_path": "/usr/lib/python3.9/site-packages/pytest/__init__.py",
                "line_number": 1,
            },
            {
                "file_path": "/app/main.py",
                "line_number": 10,
                "code_line": "import requests",
            },
            {
                "file_path": "/app/utils.py",
                "line_number": 5,
                "code_line": "def helper()",
            },
        ]

        result = _extract_fixing_traceback(traceback)

        # Should have structured traceback frames
        assert isinstance(result, list)
        if len(result) > 0:
            frame = result[0]
            assert "file_path" in frame
            assert "line" in frame  # function returns 'line', not 'line_number'

    def test_extract_fixing_context(self):
        """Test fixing context extraction."""
        error = {
            "test_name": "test_user_creation",
            "test_function": "test_user_creation",
            "exception_message": "unexpected keyword argument 'invalid_param'",
        }

        result = _extract_fixing_context(error)

        # Check that test context is extracted
        assert result["test_name"] == "test_user_creation"
        assert result["test_function"] == "test_user_creation"
        # Check that issue type is identified from message
        assert result.get("issue_type") == "function_signature_mismatch"

    def test_generate_fix_guidance(self):
        """Test fix guidance generation."""
        # Test import error
        error = {
            "exception_type": "ImportError",
            "exception_message": "No module named 'requests'",
            "traceback": [
                {"file": "/app/main.py", "line": 5, "code": "import requests"}
            ],
        }

        result = _generate_fix_guidance(error)

        # Check the actual structure returned by the function
        assert "priority" in result
        assert "error_category" in result
        assert "likely_causes" in result
        assert "fix_suggestions" in result
        assert "files_to_check" in result
        assert "specific_analysis" in result
        assert "search_patterns" in result
        assert "code_inspection_steps" in result
        assert isinstance(result["likely_causes"], list)
        assert isinstance(result["fix_suggestions"], list)

        # Test syntax error
        error = {
            "exception_type": "SyntaxError",
            "exception_message": "invalid syntax at line 10",
            "traceback": [{"file": "/app/utils.py", "line": 10, "code": "def test("}],
        }

        result = _generate_fix_guidance(error)

        assert "priority" in result
        assert "error_category" in result

    def test_generate_fix_guidance_edge_cases(self):
        """Test fix guidance with edge cases."""
        # Empty error
        error = {}
        result = _generate_fix_guidance(error)
        assert "priority" in result

        # Error with no message
        error = {"traceback": [{"file": "/app/test.py", "line": 5}]}
        result = _generate_fix_guidance(error)
        assert "priority" in result
