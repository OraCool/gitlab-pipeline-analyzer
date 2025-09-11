"""
Additional tests to boost utils coverage.
"""

from gitlab_analyzer.utils.utils import (
    categorize_files_by_type,
    combine_exclude_file_patterns,
    extract_file_path_from_message,
    get_mcp_info,
    optimize_error_response,
    optimize_tool_response,
    process_file_groups,
    should_exclude_file_path,
)


class TestUtilsCoverage:
    """Test cases to increase utils coverage."""

    def test_get_mcp_info_basic(self):
        """Test basic MCP info generation."""
        result = get_mcp_info("test_tool")
        assert result["name"] == "GitLab Pipeline Analyzer"
        assert "version" in result
        assert result["tool_used"] == "test_tool"
        assert "error" not in result

    def test_get_mcp_info_with_error(self):
        """Test MCP info generation with error flag."""
        result = get_mcp_info("test_tool", error=True)
        assert result["error"] is True

    def test_get_mcp_info_with_parser_type(self):
        """Test MCP info generation with parser type."""
        result = get_mcp_info("test_tool", parser_type="pytest")
        assert result["parser_type"] == "pytest"

    def test_should_exclude_file_path_basic(self):
        """Test basic file path exclusion."""
        # Test with no patterns
        assert not should_exclude_file_path("test.py", [])
        assert not should_exclude_file_path("test.py", None)

        # Test with patterns
        patterns = [".venv", "site-packages"]
        assert should_exclude_file_path("/path/.venv/test.py", patterns)
        assert should_exclude_file_path("/path/site-packages/test.py", patterns)
        assert not should_exclude_file_path("/path/src/test.py", patterns)

    def test_should_exclude_file_path_edge_cases(self):
        """Test file path exclusion edge cases."""
        patterns = ["test"]
        assert not should_exclude_file_path("", patterns)
        assert not should_exclude_file_path("unknown", patterns)
        assert should_exclude_file_path("test_file.py", patterns)

    def test_combine_exclude_file_patterns_basic(self):
        """Test combining exclude patterns."""
        # Test with None
        result = combine_exclude_file_patterns(None)
        assert ".venv" in result
        assert "site-packages" in result

        # Test with additional patterns
        result = combine_exclude_file_patterns(["custom", "patterns"])
        assert ".venv" in result
        assert "custom" in result
        assert "patterns" in result

    def test_combine_exclude_file_patterns_no_duplicates(self):
        """Test that combining patterns doesn't create duplicates."""
        result = combine_exclude_file_patterns([".venv", "new_pattern"])
        # Count occurrences of .venv
        venv_count = result.count(".venv")
        assert venv_count == 1

    def test_extract_file_path_from_message_traceback(self):
        """Test file path extraction from Python traceback."""
        message = 'File "src/test.py", line 10, in test_function'
        result = extract_file_path_from_message(message)
        assert result == "src/test.py"

    def test_extract_file_path_from_message_ruff_format(self):
        """Test file path extraction from ruff/linting format."""
        message = "src/main.py:15:10: E501 line too long"
        result = extract_file_path_from_message(message)
        assert result == "src/main.py"

    def test_extract_file_path_from_message_no_match(self):
        """Test file path extraction when no valid path found."""
        message = "Some error message without file path"
        result = extract_file_path_from_message(message)
        assert result is None

    def test_extract_file_path_filters_system_paths(self):
        """Test that system paths are filtered out."""
        message = 'File "/usr/lib/python3.11/site-packages/test.py", line 10'
        result = extract_file_path_from_message(message)
        assert result is None

    def test_categorize_files_by_type_basic(self):
        """Test basic file categorization."""
        files = [
            {"file_path": "src/main.py", "error_count": 5},
            {"file_path": "tests/test_main.py", "error_count": 3},
            {"file_path": "unknown", "error_count": 1},
        ]

        result = categorize_files_by_type(files)
        assert "test_files" in result
        assert "source_files" in result
        assert "unknown_files" in result

        assert result["test_files"]["count"] == 1
        assert result["source_files"]["count"] == 1
        assert result["unknown_files"]["count"] == 1

    def test_categorize_files_by_type_comprehensive(self):
        """Test comprehensive file categorization."""
        files = [
            {"file_path": "src/module.py", "error_count": 2},
            {"file_path": "test_something.py", "error_count": 1},
            {"file_path": "tests/conftest.py", "error_count": 1},
            {"file_path": "app/test/runner.py", "error_count": 1},
            {"file_path": "unknown", "error_count": 3},
            {"file_path": "Unknown", "error_count": 1},
        ]

        result = categorize_files_by_type(files)

        # Test files should include various test patterns
        test_count = result["test_files"]["count"]
        assert test_count >= 3  # test_, tests/, conftest patterns

        # Source files
        assert result["source_files"]["count"] >= 1

        # Unknown files (case insensitive)
        assert result["unknown_files"]["count"] == 2

    def test_process_file_groups_basic(self):
        """Test basic file group processing."""
        file_groups = {
            "file1.py": {"error_count": 5, "errors": ["error1", "error2", "error3"]},
            "file2.py": {"error_count": 2, "errors": ["error4", "error5"]},
        }

        result = process_file_groups(file_groups, max_files=10, max_errors_per_file=2)

        assert len(result) == 2
        # Should be sorted by error count (descending)
        assert result[0]["error_count"] == 5
        assert result[1]["error_count"] == 2

        # Errors should be limited and converted to lists
        assert len(result[0]["errors"]) == 2  # Limited to max_errors_per_file

    def test_process_file_groups_limits(self):
        """Test file group processing with limits."""
        file_groups = {
            f"file{i}.py": {"error_count": i, "errors": [f"error{j}" for j in range(i)]}
            for i in range(1, 10)
        }

        result = process_file_groups(file_groups, max_files=3, max_errors_per_file=2)

        # Should limit number of files
        assert len(result) <= 3

        # Should be sorted by error count (highest first)
        if len(result) > 1:
            assert result[0]["error_count"] >= result[1]["error_count"]

    def test_optimize_tool_response_minimal(self):
        """Test tool response optimization in minimal mode."""
        response = {
            "errors": [
                {
                    "line_number": 10,
                    "exception_type": "TestError",
                    "exception_message": "Test message",
                    "test_function": "test_func",
                    "file_path": "test.py",
                    "extra_data": "should be removed in minimal mode",
                }
            ]
        }

        result = optimize_tool_response(response, "minimal")

        assert "optimization" in result
        assert result["optimization"]["response_mode"] == "minimal"
        assert len(result["errors"]) == 1

        # Check that error was optimized
        error = result["errors"][0]
        assert "line_number" in error
        assert "exception_type" in error
        assert "extra_data" not in error

    def test_optimize_tool_response_full(self):
        """Test tool response optimization in full mode."""
        response = {"errors": [{"data": "should be preserved"}]}

        result = optimize_tool_response(response, "full")

        # Full mode should return original response
        assert result == response

    def test_optimize_error_response_modes(self):
        """Test individual error optimization modes."""
        error = {
            "line_number": 10,
            "exception_type": "TestError",
            "exception_message": "Test message",
            "test_function": "test_func",
            "file_path": "test.py",
            "traceback": [{"file_path": "test.py", "line_number": 10}],
            "extra_field": "extra_data",
        }

        # Test minimal mode
        minimal = optimize_error_response(error, "minimal")
        assert "line_number" in minimal
        assert "exception_type" in minimal
        assert "extra_field" not in minimal

        # Test balanced mode
        balanced = optimize_error_response(error, "balanced")
        assert "location" in balanced
        assert "category" in balanced

        # Test fixing mode
        fixing = optimize_error_response(error, "fixing")
        assert "fix_guidance" in fixing
        assert "context" in fixing

        # Test unknown mode (should return original)
        unknown = optimize_error_response(error, "unknown")
        assert unknown == error

    def test_optimize_response_with_no_errors(self):
        """Test optimization with responses that have no errors."""
        response = {"status": "success", "data": "some data"}

        result = optimize_tool_response(response, "minimal")

        assert "optimization" in result
        assert result["optimization"]["original_error_count"] == 0

    def test_file_categorization_edge_cases(self):
        """Test file categorization with edge cases."""
        # Empty list
        result = categorize_files_by_type([])
        assert result["test_files"]["count"] == 0
        assert result["source_files"]["count"] == 0
        assert result["unknown_files"]["count"] == 0

        # Files with various test indicators
        files = [
            {"file_path": "my_test.py", "error_count": 1},  # _test. pattern
            {"file_path": "testing_file.py", "error_count": 1},  # not a test pattern
        ]

        result = categorize_files_by_type(files)
        assert result["test_files"]["count"] == 1  # Only my_test.py is a test file
        assert result["source_files"]["count"] == 1  # testing_file.py is source

    def test_error_optimization_with_missing_fields(self):
        """Test error optimization when some fields are missing."""
        error = {
            "exception_type": "TestError",
            # Missing other fields
        }

        # Should not crash with missing fields
        minimal = optimize_error_response(error, "minimal")
        assert "exception_type" in minimal

        balanced = optimize_error_response(error, "balanced")
        assert "category" in balanced

        fixing = optimize_error_response(error, "fixing")
        assert "fix_guidance" in fixing

    def test_extract_file_path_complex_traceback(self):
        """Test file path extraction from complex traceback."""
        message = """
        Traceback (most recent call last):
          File "/usr/lib/python3.11/site-packages/something.py", line 100, in system_func
            raise Exception("system error")
          File "src/my_app.py", line 50, in my_function
            some_code()
        SyntaxError: invalid syntax
                ^
        """

        result = extract_file_path_from_message(message)
        # Should prefer application file over system file
        assert result == "src/my_app.py"

    def test_combine_patterns_preserves_order(self):
        """Test that combining patterns preserves default patterns first."""
        user_patterns = ["user1", "user2"]
        result = combine_exclude_file_patterns(user_patterns)

        # Default patterns should come first
        assert result[0] == ".venv"  # First default pattern

        # User patterns should be at the end
        assert "user1" in result
        assert "user2" in result
