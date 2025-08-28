"""
Unit tests for utility functions in utils.py.

Copyright (c) 2025 Siarhei Skuratovich
Licensed under the MIT License - see LICENSE file for details
"""

import os
import tempfile
from unittest.mock import Mock, patch

import pytest

from gitlab_analyzer.utils.utils import (
    DEFAULT_EXCLUDE_PATHS,
    _is_pytest_log,
    _is_test_job,
    _should_use_pytest_parser,
    categorize_files_by_type,
    combine_exclude_file_patterns,
    extract_file_path_from_message,
    get_gitlab_analyzer,
    get_mcp_info,
    process_file_groups,
    should_exclude_file_path,
)


class TestMCPInfo:
    """Test MCP info generation."""

    def test_get_mcp_info_basic(self):
        """Test basic MCP info generation."""
        result = get_mcp_info("test_tool")

        assert result["name"] == "GitLab Pipeline Analyzer"
        assert "version" in result
        assert result["tool_used"] == "test_tool"
        assert "error" not in result
        assert "parser_type" not in result

    def test_get_mcp_info_with_error(self):
        """Test MCP info generation with error flag."""
        result = get_mcp_info("test_tool", error=True)

        assert result["name"] == "GitLab Pipeline Analyzer"
        assert result["tool_used"] == "test_tool"
        assert result["error"] is True

    def test_get_mcp_info_with_parser_type(self):
        """Test MCP info generation with parser type."""
        result = get_mcp_info("test_tool", parser_type="pytest")

        assert result["name"] == "GitLab Pipeline Analyzer"
        assert result["tool_used"] == "test_tool"
        assert result["parser_type"] == "pytest"

    def test_get_mcp_info_with_all_params(self):
        """Test MCP info generation with all parameters."""
        result = get_mcp_info("test_tool", error=True, parser_type="mixed")

        assert result["name"] == "GitLab Pipeline Analyzer"
        assert result["tool_used"] == "test_tool"
        assert result["error"] is True
        assert result["parser_type"] == "mixed"


class TestGitLabAnalyzer:
    """Test GitLab analyzer singleton."""

    def setUp(self):
        """Reset the global analyzer instance."""
        import gitlab_analyzer.utils.utils

        gitlab_analyzer.utils.utils._GITLAB_ANALYZER = None

    def tearDown(self):
        """Clean up after tests."""
        import gitlab_analyzer.utils.utils

        gitlab_analyzer.utils.utils._GITLAB_ANALYZER = None

    @patch.dict(
        os.environ,
        {"GITLAB_URL": "https://test.gitlab.com", "GITLAB_TOKEN": "test_token"},
    )
    @patch("gitlab_analyzer.utils.utils.GitLabAnalyzer")
    def test_get_gitlab_analyzer_creates_instance(self, mock_analyzer_class):
        """Test GitLab analyzer instance creation."""
        mock_instance = Mock()
        mock_analyzer_class.return_value = mock_instance

        # Reset global instance
        import gitlab_analyzer.utils.utils

        gitlab_analyzer.utils.utils._GITLAB_ANALYZER = None

        result = get_gitlab_analyzer()

        mock_analyzer_class.assert_called_once_with(
            "https://test.gitlab.com", "test_token"
        )
        assert result == mock_instance

    @patch.dict(
        os.environ,
        {"GITLAB_URL": "https://test.gitlab.com", "GITLAB_TOKEN": "test_token"},
    )
    @patch("gitlab_analyzer.utils.utils.GitLabAnalyzer")
    def test_get_gitlab_analyzer_returns_singleton(self, mock_analyzer_class):
        """Test GitLab analyzer returns same instance."""
        mock_instance = Mock()
        mock_analyzer_class.return_value = mock_instance

        # Reset global instance
        import gitlab_analyzer.utils.utils

        gitlab_analyzer.utils.utils._GITLAB_ANALYZER = None

        result1 = get_gitlab_analyzer()
        result2 = get_gitlab_analyzer()

        # Should only create once
        mock_analyzer_class.assert_called_once()
        assert result1 == result2 == mock_instance

    @patch.dict(os.environ, {}, clear=True)
    def test_get_gitlab_analyzer_missing_token(self):
        """Test GitLab analyzer with missing token."""
        # Reset global instance
        import gitlab_analyzer.utils.utils

        gitlab_analyzer.utils.utils._GITLAB_ANALYZER = None

        with pytest.raises(
            ValueError, match="GITLAB_TOKEN environment variable is required"
        ):
            get_gitlab_analyzer()

    @patch.dict(os.environ, {"GITLAB_TOKEN": "test_token"})
    @patch("gitlab_analyzer.utils.utils.GitLabAnalyzer")
    def test_get_gitlab_analyzer_default_url(self, mock_analyzer_class):
        """Test GitLab analyzer with default URL."""
        mock_instance = Mock()
        mock_analyzer_class.return_value = mock_instance

        # Reset global instance
        import gitlab_analyzer.utils.utils

        gitlab_analyzer.utils.utils._GITLAB_ANALYZER = None

        result = get_gitlab_analyzer()

        mock_analyzer_class.assert_called_once_with("https://gitlab.com", "test_token")
        assert result == mock_instance


class TestJobDetection:
    """Test job detection utilities."""

    def test_is_test_job_by_name(self):
        """Test test job detection by job name."""
        # Positive cases - job names that indicate test jobs
        test_job_names = [
            "test",
            "tests",
            "pytest",
            "unittest",
            "testing",
            "test-suite",
            "unit-tests",
            "integration-tests",
            "my-test-job",
            "test_something",
            "run_tests",
        ]

        for job_name in test_job_names:
            assert _is_test_job(job_name, "build"), f"Failed for job name: {job_name}"

    def test_is_test_job_by_stage(self):
        """Test test job detection by stage name."""
        # Positive cases - stage names that indicate test stages
        test_stages = [
            "test",
            "testing",
            "check",
            "verify",
            "quality",
            "qa",
            "unit-test",
            "integration-test",
        ]

        for stage in test_stages:
            assert _is_test_job("build", stage), f"Failed for stage: {stage}"

    def test_is_test_job_negative_cases(self):
        """Test test job detection negative cases."""
        # Negative cases - job names and stages that should NOT be test jobs
        non_test_jobs = [
            ("build", "build"),
            ("compile", "compile"),
            ("deploy", "deploy"),
            ("package", "package"),
            ("docker-build", "build"),
            ("lint", "lint"),
            ("format", "format"),
        ]

        for job_name, stage in non_test_jobs:
            assert not _is_test_job(job_name, stage), f"Failed for: {job_name}/{stage}"

    def test_is_test_job_case_insensitive(self):
        """Test test job detection is case insensitive."""
        assert _is_test_job("TEST", "BUILD")
        assert _is_test_job("Test", "Build")
        assert _is_test_job("build", "TEST")
        assert _is_test_job("build", "Test")


class TestPytestLogDetection:
    """Test pytest log detection."""

    def test_is_pytest_log_strong_indicators(self):
        """Test pytest log detection with strong indicators."""
        strong_pytest_logs = [
            "=== FAILURES === test_something",
            "short test summary info FAILED",
            "test session starts",
            "collecting tests in directory",
            "pytest-html plugin detected",
            "rootdir: /app",
        ]

        for log_text in strong_pytest_logs:
            assert _is_pytest_log(log_text), f"Failed for: {log_text}"

    def test_is_pytest_log_weak_indicators(self):
        """Test pytest log detection with weak indicators (need multiple)."""
        # Two weak indicators should be sufficient
        assert _is_pytest_log("test_something.py failed, 1 passed")
        assert _is_pytest_log("PASSED test_user.py::test_creation")
        assert _is_pytest_log("ERROR in test_file.py::test_method")

        # One weak indicator should not be sufficient
        assert not _is_pytest_log("failed")
        assert not _is_pytest_log("PASSED")
        assert not _is_pytest_log("test_something.py")

    def test_is_pytest_log_negative_cases(self):
        """Test pytest log detection negative cases."""
        non_pytest_logs = [
            "Build completed successfully",
            "Service started",
            "INFO: Starting service",
            "Compilation finished",
            "",
            "Docker build in progress",
            "Uploading artifacts",
        ]

        for log_text in non_pytest_logs:
            assert not _is_pytest_log(log_text), f"Failed for: {log_text}"

    def test_is_pytest_log_case_insensitive(self):
        """Test pytest log detection is case insensitive."""
        assert _is_pytest_log("=== failures === test_something")
        assert _is_pytest_log("SHORT TEST SUMMARY INFO FAILED")
        assert _is_pytest_log("TEST SESSION STARTS")


class TestPytestParserSelection:
    """Test pytest parser selection logic."""

    def test_should_use_pytest_parser_with_job_info(self):
        """Test parser selection when job info is available."""
        # Test job - should use pytest parser regardless of log content
        assert _should_use_pytest_parser("Build output", "test-job", "test")
        assert _should_use_pytest_parser("Random log", "unit-tests", "build")

        # Non-test job - should use generic parser regardless of log content
        assert not _should_use_pytest_parser("=== FAILURES ===", "build", "build")
        assert not _should_use_pytest_parser("pytest output", "compile", "compile")

    def test_should_use_pytest_parser_fallback_to_log(self):
        """Test parser selection falls back to log detection when no job info."""
        # No job info - should fall back to log content detection
        assert _should_use_pytest_parser("=== FAILURES === test_something")
        assert _should_use_pytest_parser("test session starts")
        assert not _should_use_pytest_parser("Build completed successfully")

    def test_should_use_pytest_parser_empty_job_info(self):
        """Test parser selection with empty job info."""
        # Empty strings should fall back to log detection
        assert _should_use_pytest_parser("=== FAILURES ===", "", "")
        assert not _should_use_pytest_parser("Build output", "", "")


class TestFilePathExtraction:
    """Test file path extraction utilities."""

    def test_extract_file_path_from_message_patterns(self):
        """Test file path extraction with different message patterns."""
        # Test pattern 1: file.py:line_number
        message1 = "Error in main.py:42: something went wrong"
        result1 = extract_file_path_from_message(message1)
        assert result1 == "main.py"

        # Test pattern 2: File "path"
        message2 = 'File "src/utils.py" not found'
        result2 = extract_file_path_from_message(message2)
        assert result2 == "src/utils.py"

        # Test pattern 3: in/for/at filename.py
        message3 = "Error in main.py while processing"
        result3 = extract_file_path_from_message(message3)
        assert result3 == "main.py"

    def test_extract_file_path_from_message_with_path(self):
        """Test file path extraction with directory path."""
        message = "Error in src/utils/helper.py:123: function failed"
        result = extract_file_path_from_message(message)
        assert result == "src/utils/helper.py"

    def test_extract_file_path_from_message_system_paths(self):
        """Test file path extraction excludes system paths."""
        system_messages = [
            "Error in .venv/lib/python3.9/site-packages/requests.py:42",
            "Error in /usr/lib/python3.9/unittest.py:123",
            "Error in /opt/python/lib/something.py:456",
            "Error in /__pycache__/module.py:789",
        ]

        for message in system_messages:
            result = extract_file_path_from_message(message)
            assert result is None, f"Should exclude system path: {message}"

    def test_extract_file_path_from_message_no_match(self):
        """Test file path extraction with no matching pattern."""
        messages = [
            "General error message",
            "Error occurred",
            "No file reference here",
            "Error in file.txt:42",  # Not .py file
        ]

        for message in messages:
            result = extract_file_path_from_message(message)
            assert result is None, f"Should not match: {message}"

    def test_extract_file_path_from_message_temp_dir(self):
        """Test file path extraction excludes temp directory."""
        temp_dir = tempfile.gettempdir()
        message = f"Error in {temp_dir}/test_file.py:42: temp file error"
        result = extract_file_path_from_message(message)
        assert result is None


class TestDefaultExcludePaths:
    """Test default exclude paths configuration."""

    def test_default_exclude_paths_contains_expected(self):
        """Test that default exclude paths contain expected system paths."""
        expected_paths = [
            ".venv",
            "site-packages",
            ".local",
            "/root/.local",
            "/usr/lib/python",
            "/opt/python",
            "/__pycache__/",
            ".cache",
        ]

        for path in expected_paths:
            assert path in DEFAULT_EXCLUDE_PATHS, f"Missing expected path: {path}"

    def test_default_exclude_paths_includes_temp_dir(self):
        """Test that default exclude paths include system temp directory."""
        temp_dir = tempfile.gettempdir()
        assert temp_dir in DEFAULT_EXCLUDE_PATHS


class TestFileExclusion:
    """Test file exclusion utilities."""

    def test_should_exclude_file_path_basic(self):
        """Test basic file path exclusion."""
        exclude_patterns = [".venv", "site-packages", "__pycache__"]

        # Should exclude
        assert should_exclude_file_path("/path/.venv/module.py", exclude_patterns)
        assert should_exclude_file_path(
            "/usr/lib/python3.9/site-packages/requests.py", exclude_patterns
        )
        assert should_exclude_file_path("/app/__pycache__/module.pyc", exclude_patterns)

        # Should not exclude
        assert not should_exclude_file_path("/app/src/main.py", exclude_patterns)
        assert not should_exclude_file_path("main.py", exclude_patterns)

    def test_should_exclude_file_path_edge_cases(self):
        """Test file path exclusion edge cases."""
        exclude_patterns = [".venv", "test"]

        # Empty or None patterns
        assert not should_exclude_file_path("/app/main.py", [])
        assert not should_exclude_file_path("/app/main.py", None)

        # Empty or special file paths
        assert not should_exclude_file_path("", exclude_patterns)
        assert not should_exclude_file_path("unknown", exclude_patterns)

    def test_combine_exclude_file_patterns(self):
        """Test combining exclude file patterns."""
        # No user patterns
        result = combine_exclude_file_patterns(None)
        assert result == list(DEFAULT_EXCLUDE_PATHS)

        # With user patterns
        user_patterns = ["custom_exclude", "another_pattern"]
        result = combine_exclude_file_patterns(user_patterns)

        # Should contain all defaults plus user patterns
        for pattern in DEFAULT_EXCLUDE_PATHS:
            assert pattern in result
        for pattern in user_patterns:
            assert pattern in result

        # Should not have duplicates
        assert len(result) == len(set(result))

    def test_combine_exclude_file_patterns_duplicates(self):
        """Test combining exclude patterns with duplicates."""
        # User patterns that overlap with defaults
        user_patterns = [".venv", "site-packages", "new_pattern"]
        result = combine_exclude_file_patterns(user_patterns)

        # Should not have duplicates
        assert result.count(".venv") == 1
        assert result.count("site-packages") == 1
        assert "new_pattern" in result


class TestFileCategorization:
    """Test file categorization utilities."""

    def test_categorize_files_by_type_basic(self):
        """Test basic file categorization."""
        files = [
            {"file_path": "test_user.py", "error_count": 3},
            {"file_path": "src/main.py", "error_count": 2},
            {"file_path": "tests/test_auth.py", "error_count": 1},
            {"file_path": "unknown", "error_count": 1},
            {"file_path": "conftest.py", "error_count": 1},
        ]

        result = categorize_files_by_type(files)

        # Test files
        assert result["test_files"]["count"] == 3
        assert result["test_files"]["total_errors"] == 5  # 3 + 1 + 1
        test_file_paths = [f["file_path"] for f in result["test_files"]["files"]]
        assert "test_user.py" in test_file_paths
        assert "tests/test_auth.py" in test_file_paths
        assert "conftest.py" in test_file_paths

        # Source files
        assert result["source_files"]["count"] == 1
        assert result["source_files"]["total_errors"] == 2
        assert result["source_files"]["files"][0]["file_path"] == "src/main.py"

        # Unknown files
        assert result["unknown_files"]["count"] == 1
        assert result["unknown_files"]["total_errors"] == 1
        assert result["unknown_files"]["files"][0]["file_path"] == "unknown"

    def test_categorize_files_by_type_test_patterns(self):
        """Test file categorization with different test patterns."""
        files = [
            {"file_path": "test_module.py", "error_count": 1},
            {"file_path": "module_test.py", "error_count": 1},
            {"file_path": "tests/unit/test_api.py", "error_count": 1},
            {"file_path": "src/test/helpers.py", "error_count": 1},
            {"file_path": "app/conftest.py", "error_count": 1},
        ]

        result = categorize_files_by_type(files)

        # All should be categorized as test files
        assert result["test_files"]["count"] == 5
        assert result["source_files"]["count"] == 0
        assert result["unknown_files"]["count"] == 0

    def test_categorize_files_by_type_case_insensitive(self):
        """Test file categorization is case insensitive."""
        files = [
            {"file_path": "TEST_MODULE.py", "error_count": 1},
            {"file_path": "TESTS/unit.py", "error_count": 1},
            {"file_path": "src/Main.py", "error_count": 1},
        ]

        result = categorize_files_by_type(files)

        assert result["test_files"]["count"] == 2
        assert result["source_files"]["count"] == 1

    def test_categorize_files_by_type_empty(self):
        """Test file categorization with empty input."""
        result = categorize_files_by_type([])

        assert result["test_files"]["count"] == 0
        assert result["test_files"]["total_errors"] == 0
        assert result["test_files"]["files"] == []

        assert result["source_files"]["count"] == 0
        assert result["source_files"]["total_errors"] == 0
        assert result["source_files"]["files"] == []

        assert result["unknown_files"]["count"] == 0
        assert result["unknown_files"]["total_errors"] == 0
        assert result["unknown_files"]["files"] == []


class TestFileGroupProcessing:
    """Test file group processing utilities."""

    def test_process_file_groups_basic(self):
        """Test basic file group processing."""
        file_groups = {
            "file1": {"error_count": 5, "errors": ["error1", "error2", "error3"]},
            "file2": {"error_count": 3, "errors": ["error4", "error5"]},
            "file3": {"error_count": 1, "errors": ["error6"]},
        }

        result = process_file_groups(file_groups, max_files=2, max_errors_per_file=2)

        # Should be sorted by error count (highest first)
        assert len(result) == 2
        assert result[0]["error_count"] == 5
        assert result[1]["error_count"] == 3

        # Should limit errors per file
        assert len(result[0]["errors"]) == 2
        assert len(result[1]["errors"]) == 2

    def test_process_file_groups_no_errors_field(self):
        """Test file group processing without errors field."""
        file_groups = {
            "file1": {"error_count": 5},
            "file2": {"error_count": 3},
        }

        result = process_file_groups(file_groups, max_files=2, max_errors_per_file=2)

        assert len(result) == 2
        assert result[0]["error_count"] == 5
        assert result[1]["error_count"] == 3
        # No errors field should be added

    def test_process_file_groups_set_conversion(self):
        """Test file group processing converts sets to lists."""
        file_groups = {
            "file1": {"error_count": 3, "errors": {"error1", "error2", "error3"}},
        }

        result = process_file_groups(file_groups, max_files=1, max_errors_per_file=2)

        assert len(result) == 1
        assert isinstance(result[0]["errors"], list)
        assert len(result[0]["errors"]) == 2

    def test_process_file_groups_empty(self):
        """Test file group processing with empty input."""
        result = process_file_groups({}, max_files=10, max_errors_per_file=5)
        assert result == []

    def test_process_file_groups_limits(self):
        """Test file group processing respects limits."""
        file_groups = {
            f"file{i}": {
                "error_count": 10 - i,
                "errors": [f"error{j}" for j in range(10)],
            }
            for i in range(5)
        }

        result = process_file_groups(file_groups, max_files=3, max_errors_per_file=2)

        # Should limit files
        assert len(result) == 3

        # Should limit errors per file
        for file_group in result:
            assert len(file_group["errors"]) == 2
