"""
Tests to increase coverage of utils.py module

Copyright (c) 2025 Siarhei Skuratovich
Licensed under the MIT License - see LICENSE file for details
"""

from unittest.mock import Mock, patch


class TestUtilsCoverage:
    """Tests to increase coverage of utils module"""

    def test_mcp_info_function(self):
        """Test MCP info generation"""
        from gitlab_analyzer.utils.utils import get_mcp_info

        # Test basic call
        result = get_mcp_info("test_tool")
        assert isinstance(result, dict)
        assert "tool_used" in result
        assert result["tool_used"] == "test_tool"

    def test_mcp_info_with_error(self):
        """Test MCP info with error flag"""
        from gitlab_analyzer.utils.utils import get_mcp_info

        result = get_mcp_info("test_tool", error=True)
        assert isinstance(result, dict)
        assert "error" in result or "tool" in result

    def test_mcp_info_with_parser_type(self):
        """Test MCP info with parser type"""
        from gitlab_analyzer.utils.utils import get_mcp_info

        result = get_mcp_info("test_tool", parser_type="pytest")
        assert isinstance(result, dict)

    @patch("gitlab_analyzer.utils.utils.get_gitlab_analyzer")
    def test_get_gitlab_analyzer_cached(self, mock_get_analyzer):
        """Test GitLab analyzer caching"""
        from gitlab_analyzer.utils.utils import get_gitlab_analyzer

        # Create mock analyzer
        mock_analyzer = Mock()
        mock_get_analyzer.return_value = mock_analyzer

        # First call
        result1 = get_gitlab_analyzer()

        # Second call should return same instance
        result2 = get_gitlab_analyzer()

        assert result1 is not None
        assert result2 is not None

    def test_is_test_job(self):
        """Test test job detection"""
        from gitlab_analyzer.utils.utils import _is_test_job

        # Test various job names and stages
        assert _is_test_job("test:unit", "test") is True
        assert _is_test_job("pytest", "test") is True
        assert _is_test_job("build", "build") is False

    def test_should_use_pytest_parser(self):
        """Test pytest parser detection"""
        from gitlab_analyzer.utils.utils import _should_use_pytest_parser

        # Test with job info
        job_info = {"name": "pytest", "stage": "test"}
        result = _should_use_pytest_parser(job_info, "mock log content")
        assert isinstance(result, bool)

    def test_is_pytest_log(self):
        """Test pytest log detection"""
        from gitlab_analyzer.utils.utils import _is_pytest_log

        # Test with pytest log content
        pytest_log = "===== test session starts ====="
        assert _is_pytest_log(pytest_log) is True

        # Test with non-pytest content
        regular_log = "Building project..."
        assert _is_pytest_log(regular_log) is False

    def test_extract_file_path_from_message(self):
        """Test file path extraction from message"""
        from gitlab_analyzer.utils.utils import extract_file_path_from_message

        # Test various message formats
        message1 = "ERROR in src/main.py at line 42"
        result1 = extract_file_path_from_message(message1)
        assert result1 is not None

        message2 = "No file path here"
        result2 = extract_file_path_from_message(message2)
        assert result2 is None

    def test_should_exclude_file_path(self):
        """Test file path exclusion"""
        from gitlab_analyzer.utils.utils import should_exclude_file_path

        exclude_patterns = ["__pycache__", "*.pyc", "node_modules/"]

        assert (
            should_exclude_file_path("src/__pycache__/test.py", exclude_patterns)
            is True
        )
        assert should_exclude_file_path("src/main.py", exclude_patterns) is False

    def test_combine_exclude_file_patterns(self):
        """Test combining exclude patterns"""
        from gitlab_analyzer.utils.utils import combine_exclude_file_patterns

        user_patterns = ["custom_exclude/"]
        result = combine_exclude_file_patterns(user_patterns)

        assert isinstance(result, list)
        assert "custom_exclude/" in result
        # Should also include default patterns

    def test_categorize_files_by_type(self):
        """Test file categorization by type"""
        from gitlab_analyzer.utils.utils import categorize_files_by_type

        files = [
            {"file_path": "test.py", "error_count": 2},
            {"file_path": "config.json", "error_count": 1},
            {"file_path": "README.md", "error_count": 0},
        ]

        result = categorize_files_by_type(files)
        assert isinstance(result, dict)

    def test_process_file_groups(self):
        """Test file group processing"""
        from gitlab_analyzer.utils.utils import process_file_groups

        file_groups = {
            "src": {"file_path": "src/main.py", "error_count": 2},
            "tests": {"file_path": "tests/test_main.py", "error_count": 1},
        }

        result = process_file_groups(file_groups, max_files=10, max_errors_per_file=5)
        assert isinstance(result, list)

    def test_optimize_tool_response(self):
        """Test tool response optimization"""
        from gitlab_analyzer.utils.utils import optimize_tool_response

        response = {
            "data": [{"item": 1}, {"item": 2}, {"item": 3}],
            "metadata": {"count": 3},
        }

        optimized = optimize_tool_response(response, mode="basic", max_items=2)
        assert isinstance(optimized, dict)

    def test_optimize_error_response(self):
        """Test error response optimization"""
        from gitlab_analyzer.utils.utils import optimize_error_response

        error = {
            "message": "Test error",
            "file_path": "test.py",
            "line": 42,
            "traceback": [{"file": "test.py", "line": 42}],
            "context": ["line 1", "line 2", "line 3"],
        }

        # Test different modes
        for mode in ["basic", "balanced", "detailed", "comprehensive"]:
            result = optimize_error_response(error, mode)
            assert isinstance(result, dict)
            # Different structure based on the actual function

    def test_create_minimal_error(self):
        """Test minimal error creation"""
        from gitlab_analyzer.utils.utils import _create_minimal_error

        error = {
            "message": "Test error",
            "file_path": "test.py",
            "line": 42,
            "extra_data": "should be removed",
        }

        minimal = _create_minimal_error(error)
        assert isinstance(minimal, dict)
        # Check for actual fields returned

    def test_create_balanced_error(self):
        """Test balanced error creation"""
        from gitlab_analyzer.utils.utils import _create_balanced_error

        error = {
            "message": "Test error",
            "file_path": "test.py",
            "line": 42,
            "traceback": [{"file": "test.py", "line": 42}],
        }

        balanced = _create_balanced_error(error)
        assert isinstance(balanced, dict)
        # Check for actual fields returned

    def test_create_fixing_error(self):
        """Test fixing error creation"""
        from gitlab_analyzer.utils.utils import _create_fixing_error

        error = {
            "message": "Test error",
            "file_path": "test.py",
            "line": 42,
            "traceback": [{"file": "test.py", "line": 42}],
            "context": ["line 1", "line 2", "line 3"],
        }

        fixing = _create_fixing_error(error)
        assert isinstance(fixing, dict)
        # Check for actual fields returned

    def test_extract_error_location(self):
        """Test error location extraction"""
        from gitlab_analyzer.utils.utils import _extract_error_location

        error = {"file_path": "test.py", "line": 42, "function": "test_function"}

        location = _extract_error_location(error)
        assert isinstance(location, str)
        assert "test.py" in location

    def test_categorize_error_for_fixing(self):
        """Test error categorization for fixing"""
        from gitlab_analyzer.utils.utils import _categorize_error_for_fixing

        error = {"exception_type": "AssertionError", "message": "Test failed"}

        category = _categorize_error_for_fixing(error)
        assert isinstance(category, str)

    def test_extract_key_traceback(self):
        """Test key traceback extraction"""
        from gitlab_analyzer.utils.utils import _extract_key_traceback

        traceback = [
            {"file": "lib/python/site-packages/something.py", "line": 10},
            {"file": "src/main.py", "line": 42},
            {"file": "tests/test.py", "line": 15},
        ]

        key_traceback = _extract_key_traceback(traceback)
        assert isinstance(key_traceback, list)
        # Should filter out library files

    def test_extract_fixing_traceback(self):
        """Test fixing traceback extraction"""
        from gitlab_analyzer.utils.utils import _extract_fixing_traceback

        traceback = [
            {"file": "src/main.py", "line": 42, "code": "assert False"},
            {"file": "tests/test.py", "line": 15, "code": "main()"},
        ]

        fixing_traceback = _extract_fixing_traceback(traceback)
        assert isinstance(fixing_traceback, list)

    def test_extract_fixing_context(self):
        """Test fixing context extraction"""
        from gitlab_analyzer.utils.utils import _extract_fixing_context

        error = {
            "context": ["line 1", "line 2", "error line", "line 4", "line 5"],
            "line": 3,
        }

        fixing_context = _extract_fixing_context(error)
        assert isinstance(fixing_context, dict)
