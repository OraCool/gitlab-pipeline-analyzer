"""
Clean coverage push tests to reach 65% threshold.
"""

from src.gitlab_analyzer.utils.utils import (
    _is_test_job,
    categorize_files_by_type,
    get_mcp_info,
    should_exclude_file_path,
)


class TestUtilityFunctions:
    """Test utility functions for coverage boost."""

    def test_get_mcp_info_returns_dict(self):
        """Test get_mcp_info returns a dictionary."""
        info = get_mcp_info("test_tool")
        assert isinstance(info, dict)
        assert "name" in info
        assert info["name"] == "GitLab Pipeline Analyzer"
        assert "version" in info
        assert "tool_used" in info

    def test_get_mcp_info_with_error(self):
        """Test get_mcp_info with error flag."""
        info = get_mcp_info("test_tool", error=True)
        assert isinstance(info, dict)
        assert "error" in info
        assert info["error"] is True

    def test_get_mcp_info_with_parser_type(self):
        """Test get_mcp_info with parser type."""
        info = get_mcp_info("test_tool", parser_type="pytest")
        assert isinstance(info, dict)
        assert "parser_type" in info
        assert info["parser_type"] == "pytest"

    def test_should_exclude_file_path_none(self):
        """Test should_exclude_file_path with None."""
        result = should_exclude_file_path(None, [])
        assert result is False  # None should not match any patterns

    def test_should_exclude_file_path_empty(self):
        """Test should_exclude_file_path with empty string."""
        result = should_exclude_file_path("", [])
        assert result is False  # Empty string should not match patterns

    def test_should_exclude_file_path_venv(self):
        """Test should_exclude_file_path excludes .venv paths."""
        result = should_exclude_file_path(
            "/.venv/lib/python3.8/site-packages/module.py", [".venv/"]
        )
        assert result is True

    def test_should_exclude_file_path_site_packages(self):
        """Test should_exclude_file_path excludes site-packages."""
        result = should_exclude_file_path(
            "/usr/local/lib/python3.8/site-packages/module.py", ["site-packages/"]
        )
        assert result is True

    def test_should_exclude_file_path_valid_file(self):
        """Test should_exclude_file_path allows valid source files."""
        result = should_exclude_file_path(
            "src/gitlab_analyzer/utils/utils.py", [".venv/", "site-packages/"]
        )
        assert result is False

    def test_categorize_files_by_type_empty(self):
        """Test categorize_files_by_type with empty list."""
        result = categorize_files_by_type([])
        assert isinstance(result, dict)
        assert "source_files" in result
        assert "test_files" in result
        assert len(result["source_files"]["files"]) == 0
        assert len(result["test_files"]["files"]) == 0

    def test_categorize_files_by_type_source_files(self):
        """Test categorize_files_by_type categorizes source files."""
        files = [
            {"file_path": "src/main.py", "error_count": 1},
            {"file_path": "lib/utils.py", "error_count": 0},
        ]
        result = categorize_files_by_type(files)
        assert len(result["source_files"]["files"]) == 2
        assert any(
            f["file_path"] == "src/main.py" for f in result["source_files"]["files"]
        )

    def test_categorize_files_by_type_test_files(self):
        """Test categorize_files_by_type categorizes test files."""
        files = [
            {"file_path": "tests/test_main.py", "error_count": 2},
            {"file_path": "test/unit_test.py", "error_count": 1},
        ]
        result = categorize_files_by_type(files)
        assert len(result["test_files"]["files"]) == 2
        assert any(
            f["file_path"] == "tests/test_main.py"
            for f in result["test_files"]["files"]
        )

    def test_is_test_job_basic(self):
        """Test _is_test_job recognizes basic test job names."""
        assert _is_test_job("test", "test") is True
        assert _is_test_job("tests", "test") is True
        assert _is_test_job("pytest", "test") is True

    def test_is_test_job_non_test(self):
        """Test _is_test_job rejects non-test job names."""
        assert _is_test_job("build", "build") is False
        assert _is_test_job("deploy", "deploy") is False
        assert _is_test_job("lint", "lint") is False

    def test_is_test_job_case_insensitive(self):
        """Test _is_test_job is case insensitive."""
        assert _is_test_job("TEST", "test") is True
        assert _is_test_job("PyTest", "test") is True
