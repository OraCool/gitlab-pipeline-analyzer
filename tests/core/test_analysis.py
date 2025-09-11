"""
Tests for src/gitlab_analyzer/core/analysis.py

This module tests the core analysis functions that handle pipeline failure investigation.
"""

import pytest

from gitlab_analyzer.core.analysis import (
    get_optimal_parser,
    is_pytest_job,
)


@pytest.fixture
def sample_trace_content():
    """Sample trace content for testing."""
    return """
Running tests...
Traceback (most recent call last):
  File "src/main.py", line 10, in <module>
    import missing_module
ImportError: No module named 'missing_module'
FAILED tests/test_main.py::test_function - ImportError: No module named 'missing_module'
"""


@pytest.fixture
def sample_pytest_trace():
    """Sample pytest trace content."""
    return """
============================= test session starts ==============================
collecting ... collected 5 items

tests/test_example.py::test_addition PASSED                             [ 20%]
tests/test_example.py::test_subtraction FAILED                          [ 40%]
"""


class TestIsPytestJob:
    """Test the is_pytest_job function."""

    def test_is_pytest_job_with_pytest_name(self):
        """Test detection with pytest in job name."""
        result = is_pytest_job(
            job_name="pytest-runner", job_stage="test", trace_content=""
        )
        assert result is True

    def test_is_pytest_job_with_test_name(self):
        """Test detection with test in job name."""
        result = is_pytest_job(
            job_name="unit-test", job_stage="build", trace_content=""
        )
        assert result is True

    def test_is_pytest_job_with_regular_job(self):
        """Test detection with regular job name."""
        result = is_pytest_job(
            job_name="build-app", job_stage="build", trace_content=""
        )
        assert result is False

    def test_is_pytest_job_case_insensitive(self):
        """Test case insensitive detection."""
        result = is_pytest_job(
            job_name="PYTEST-RUNNER", job_stage="deploy", trace_content=""
        )
        assert result is True


class TestGetOptimalParser:
    """Test the get_optimal_parser function."""

    def test_get_optimal_parser_for_pytest_job(self):
        """Test parser selection for pytest job."""
        parser = get_optimal_parser(
            job_name="pytest-runner",
            job_stage="test",
            trace_content="pytest collected 5 items",
        )
        assert parser == "pytest"

    def test_get_optimal_parser_for_regular_job(self):
        """Test parser selection for regular job."""
        parser = get_optimal_parser(
            job_name="build-app",
            job_stage="build",
            trace_content="Building application...",
        )
        assert parser == "generic"

    def test_get_optimal_parser_with_pytest_indicators(self):
        """Test parser selection based on trace content."""
        parser = get_optimal_parser(
            job_name="build",
            job_stage="build",
            trace_content="Running pytest... collected 10 items",
        )
        assert parser == "pytest"


class TestAnalysisIntegration:
    """Integration tests for analysis workflow."""

    def test_full_analysis_workflow_pytest_job(self, sample_pytest_trace):
        """Test full analysis workflow for pytest job."""
        # Test is_pytest_job detection
        assert (
            is_pytest_job(
                job_name="pytest-runner",
                job_stage="test",
                trace_content=sample_pytest_trace,
            )
            is True
        )

        # Test parser selection
        parser_type = get_optimal_parser(
            job_name="pytest-runner",
            job_stage="test",
            trace_content=sample_pytest_trace,
        )
        assert parser_type == "pytest"

    def test_full_analysis_workflow_regular_job(self, sample_trace_content):
        """Test full analysis workflow for regular job."""
        # Test is_pytest_job detection
        # Note: sample_trace_content contains "FAILED tests/test_main.py::test_function"
        # which is a pytest failure format, so it should be detected as pytest
        assert (
            is_pytest_job(
                job_name="build-app",
                job_stage="build",
                trace_content=sample_trace_content,
            )
            is True
        )

        # Test parser selection - should use pytest parser due to trace content
        parser_type = get_optimal_parser(
            job_name="build-app", job_stage="build", trace_content=sample_trace_content
        )
        assert parser_type == "pytest"
