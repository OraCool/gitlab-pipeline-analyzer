"""
Common utilities for MCP tools

Copyright (c) 2025 Siarhei Skuratovich
Licensed under the MIT License - see LICENSE file for details
"""

import os

from gitlab_analyzer.api.client import GitLabAnalyzer

# GitLab analyzer singleton instance
_GITLAB_ANALYZER = None


def get_gitlab_analyzer() -> GitLabAnalyzer:
    """Get or create GitLab analyzer instance"""
    global _GITLAB_ANALYZER  # pylint: disable=global-statement

    if _GITLAB_ANALYZER is None:
        gitlab_url = os.getenv("GITLAB_URL", "https://gitlab.com")
        gitlab_token = os.getenv("GITLAB_TOKEN")

        if not gitlab_token:
            raise ValueError("GITLAB_TOKEN environment variable is required")

        _GITLAB_ANALYZER = GitLabAnalyzer(gitlab_url, gitlab_token)

    return _GITLAB_ANALYZER


def _is_test_job(job_name: str, job_stage: str) -> bool:
    """
    Detect if a job is a test job based on its name and stage.

    This is more reliable than trying to parse log content heuristics.

    Args:
        job_name: The name of the job
        job_stage: The stage of the job

    Returns:
        True if this appears to be a test job that should use pytest parser
    """
    job_name_lower = job_name.lower()
    job_stage_lower = job_stage.lower()

    # Common test job indicators
    test_indicators = [
        # Job name patterns
        "test" in job_name_lower,
        "pytest" in job_name_lower,
        job_name_lower.startswith("unit"),
        job_name_lower.startswith("integration"),
        job_name_lower.startswith("e2e"),
        job_name_lower.endswith("test"),
        job_name_lower.endswith("tests"),
        "test-" in job_name_lower,
        "testing" in job_name_lower,
        # Stage patterns
        "test" in job_stage_lower,
        "testing" in job_stage_lower,
        job_stage_lower == "test",
        job_stage_lower == "tests",
        job_stage_lower == "unit-test",
        job_stage_lower == "integration-test",
    ]

    return any(test_indicators)


def _should_use_pytest_parser(
    log_text: str, job_name: str = "", job_stage: str = ""
) -> bool:
    """
    Determine if pytest parser should be used based on job info and log content.

    Uses a hybrid approach:
    1. If job name/stage indicates it's a test job, use pytest parser
    2. If job name/stage indicates it's NOT a test job, use generic parser
    3. Only if job info is unknown/missing, fall back to log content detection

    Args:
        log_text: The job log content
        job_name: The name of the job (optional)
        job_stage: The stage of the job (optional)

    Returns:
        True if pytest parser should be used
    """
    # Method 1: Check job name/stage (most reliable when available)
    if job_name or job_stage:
        # If we have job info, use it to decide
        return _is_test_job(job_name, job_stage)

    # Method 2: Fall back to log content detection only when job info is missing
    return _is_pytest_log(log_text)


def _is_pytest_log(log_text: str) -> bool:
    """Detect if log text contains pytest output"""
    # Strong pytest indicators that are unique to pytest
    strong_indicators = [
        "=== FAILURES ===",
        "short test summary info",
        "test session starts",
        "collecting tests",  # More specific than "collecting ..."
        "pytest-",
        "rootdir:",
    ]

    # Weaker indicators that need combination
    weak_indicators = [
        "failed, ",
        "passed, ",
        " passed in ",
        "test_",
        "PASSED",
        "FAILED",
        "ERROR",
        ".py::",  # test file pattern - moved to weak indicators
    ]

    # Convert to lowercase for case-insensitive matching
    log_lower = log_text.lower()

    # Check for strong indicators (any one is sufficient)
    for indicator in strong_indicators:
        if indicator.lower() in log_lower:
            return True

    # Check for weak indicators (need at least 2)
    weak_indicator_count = sum(
        1 for indicator in weak_indicators if indicator.lower() in log_lower
    )

    return weak_indicator_count >= 2
