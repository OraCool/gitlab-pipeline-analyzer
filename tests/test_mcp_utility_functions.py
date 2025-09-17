"""
Tests for MCP utility functions in utils/utils.py

This test file focuses on testing MCP-specific utility functions that provide
core functionality for the GitLab Pipeline Analyzer MCP server, including:
- MCP info generation
- Job classification for parser selection
- GitLab analyzer instance management
- Test job detection logic

The goal is to achieve comprehensive coverage of utility functions that support
the MCP server operations and ensure robust functionality.
"""

from gitlab_analyzer.utils.utils import (
    _is_test_job,
    _should_use_pytest_parser,
    get_mcp_info,
)


class TestMcpUtilityFunctions:
    """Test MCP utility functions for comprehensive coverage"""

    def test_get_mcp_info_basic_usage(self):
        """Test basic MCP info generation"""
        result = get_mcp_info("test_tool")

        assert result["name"] == "GitLab Pipeline Analyzer"
        assert result["tool_used"] == "test_tool"
        assert "version" in result
        assert "error" not in result
        assert "parser_type" not in result

    def test_get_mcp_info_with_error_flag(self):
        """Test MCP info generation with error flag"""
        result = get_mcp_info("test_tool", error=True)

        assert result["name"] == "GitLab Pipeline Analyzer"
        assert result["tool_used"] == "test_tool"
        assert result["error"] is True
        assert "parser_type" not in result

    def test_get_mcp_info_with_parser_type(self):
        """Test MCP info generation with parser type"""
        result = get_mcp_info("test_tool", parser_type="pytest")

        assert result["name"] == "GitLab Pipeline Analyzer"
        assert result["tool_used"] == "test_tool"
        assert result["parser_type"] == "pytest"
        assert "error" not in result

    def test_get_mcp_info_with_all_parameters(self):
        """Test MCP info generation with all optional parameters"""
        result = get_mcp_info("test_tool", error=True, parser_type="mixed")

        assert result["name"] == "GitLab Pipeline Analyzer"
        assert result["tool_used"] == "test_tool"
        assert result["error"] is True
        assert result["parser_type"] == "mixed"

    def test_is_test_job_by_job_name_patterns(self):
        """Test test job detection based on job name patterns"""
        # Test prefix patterns
        assert _is_test_job("test_integration", "build") is True
        assert _is_test_job("tests_unit", "build") is True
        assert _is_test_job("pytest_suite", "build") is True
        assert _is_test_job("unittest_runner", "build") is True
        assert _is_test_job("testing_framework", "build") is True

        # Test suffix patterns
        assert _is_test_job("integration_test", "build") is True
        assert _is_test_job("unit_tests", "build") is True

        # Non-test job names
        assert _is_test_job("build_app", "build") is False
        assert _is_test_job("deploy_prod", "deploy") is False

    def test_is_test_job_by_stage_patterns(self):
        """Test test job detection based on stage patterns"""
        # Test stage patterns
        assert _is_test_job("my_job", "test") is True
        assert _is_test_job("my_job", "testing") is True
        assert _is_test_job("my_job", "check") is True
        assert _is_test_job("my_job", "verify") is True
        assert _is_test_job("my_job", "quality") is True
        assert _is_test_job("my_job", "qa") is True

        # Non-test stages
        assert _is_test_job("my_job", "build") is False
        assert _is_test_job("my_job", "deploy") is False

    def test_is_test_job_case_sensitivity(self):
        """Test that test job detection is case insensitive"""
        # Mixed case job names
        assert _is_test_job("Test_Integration", "BUILD") is True
        assert _is_test_job("PYTEST_Suite", "build") is True
        assert _is_test_job("my_job", "TEST") is True
        assert _is_test_job("my_job", "Quality") is True

    def test_is_test_job_combined_patterns(self):
        """Test test job detection with both job name and stage indicators"""
        # Both indicators present
        assert _is_test_job("test_runner", "testing") is True
        assert _is_test_job("pytest_job", "qa") is True

        # One indicator present (should still return True)
        assert _is_test_job("test_runner", "build") is True
        assert _is_test_job("deploy_job", "testing") is True

    def test_should_use_pytest_parser_with_test_job(self):
        """Test pytest parser selection for test jobs"""
        # Test job by name
        result = _should_use_pytest_parser("some log content", "test_runner", "build")
        assert result is True

        # Test job by stage
        result = _should_use_pytest_parser("some log content", "my_job", "testing")
        assert result is True

    def test_should_use_pytest_parser_with_non_test_job(self):
        """Test pytest parser selection for non-test jobs"""
        # Non-test job
        result = _should_use_pytest_parser("some log content", "build_app", "build")
        assert result is False

        result = _should_use_pytest_parser("some log content", "deploy_job", "deploy")
        assert result is False

    def test_should_use_pytest_parser_empty_job_info(self):
        """Test pytest parser selection with empty job info (falls back to log analysis)"""
        # With pytest indicators in log
        pytest_log = """
        ============================= test session starts ==============================
        collected 5 items
        test_file.py::test_example PASSED
        """
        result = _should_use_pytest_parser(pytest_log, "", "")
        assert result is True

        # Without pytest indicators in log
        generic_log = "Building application... Compilation successful"
        result = _should_use_pytest_parser(generic_log, "", "")
        assert result is False

    def test_should_use_pytest_parser_mixed_scenarios(self):
        """Test pytest parser selection with mixed job info scenarios"""
        # Test job with generic log (job info takes precedence)
        generic_log = "Building application..."
        result = _should_use_pytest_parser(generic_log, "test_suite", "testing")
        assert result is True

        # Non-test job with pytest log (job info takes precedence)
        pytest_log = "===== test session starts ====="
        result = _should_use_pytest_parser(pytest_log, "build_app", "build")
        assert result is False

    def test_get_mcp_info_different_tool_names(self):
        """Test MCP info generation with different tool names"""
        tools = [
            "failed_pipeline_analysis",
            "job_analysis",
            "search_repository_code",
            "get_mcp_resource",
            "clear_cache",
        ]

        for tool in tools:
            result = get_mcp_info(tool)
            assert result["tool_used"] == tool
            assert result["name"] == "GitLab Pipeline Analyzer"

    def test_get_mcp_info_parser_type_variations(self):
        """Test MCP info generation with different parser types"""
        parser_types = ["pytest", "generic", "mixed", "jest", "sonarqube"]

        for parser_type in parser_types:
            result = get_mcp_info("test_tool", parser_type=parser_type)
            assert result["parser_type"] == parser_type

    def test_is_test_job_edge_cases(self):
        """Test edge cases for test job detection"""
        # Empty strings
        assert _is_test_job("", "") is False

        # Whitespace
        assert _is_test_job("   ", "   ") is False

        # These contain "test" as substring so they match (this is expected behavior)
        assert _is_test_job("contest", "build") is True  # contains "test"
        assert _is_test_job("latest", "build") is True  # contains "test"

        # These should not match
        assert _is_test_job("build", "deploy") is False
        assert _is_test_job("compile", "package") is False

    def test_is_test_job_substring_matches(self):
        """Test that substring matching works correctly for test job detection"""
        # These should match because they contain test indicators as substrings
        assert _is_test_job("integration_test_suite", "build") is True
        assert _is_test_job("run_pytest_with_coverage", "build") is True
        assert _is_test_job("my_job", "integration_testing") is True
        assert _is_test_job("my_job", "quality_check") is True
