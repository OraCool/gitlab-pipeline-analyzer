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


def _is_pytest_log(log_text: str) -> bool:
    """Detect if log text contains pytest output"""
    pytest_indicators = [
        "=== FAILURES ===",
        "short test summary info",
        "failed, ",
        "passed, ",
        " in ",
        ".py::",
        "test_",
        "pytest",
        "PASSED",
        "FAILED",
        "ERROR",
        "collecting ...",
    ]

    # Convert to lowercase for case-insensitive matching
    log_lower = log_text.lower()

    # Check if at least 2 pytest indicators are present
    indicator_count = sum(
        1 for indicator in pytest_indicators if indicator.lower() in log_lower
    )

    return indicator_count >= 2
