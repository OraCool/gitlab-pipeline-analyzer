"""
Pytest data models for log parsing and analysis

Copyright (c) 2025 Siarhei Skuratovich
Licensed under the MIT License - see LICENSE file for details
"""

from dataclasses import dataclass


@dataclass
class PytestTraceback:
    """Represents a single traceback entry in a test failure"""

    file_path: str
    line_number: int | None
    function_name: str | None
    code_line: str | None
    error_type: str | None
    error_message: str | None


@dataclass
class PytestFailureDetail:
    """Represents a detailed test failure with full traceback"""

    test_name: str
    test_file: str
    test_function: str
    test_parameters: str | None
    platform_info: str | None
    python_version: str | None
    exception_type: str
    exception_message: str
    traceback: list[PytestTraceback]
    full_error_text: str


@dataclass
class PytestShortSummary:
    """Represents a test failure from the short summary section"""

    test_name: str
    test_file: str
    test_function: str
    test_parameters: str | None
    error_type: str
    error_message: str


@dataclass
class PytestStatistics:
    """Represents pytest run statistics"""

    total_tests: int
    passed: int
    failed: int
    skipped: int
    errors: int
    warnings: int
    duration_seconds: float | None
    duration_formatted: str | None


@dataclass
class PytestLogAnalysis:
    """Complete pytest log analysis"""

    detailed_failures: list[PytestFailureDetail]
    short_summary: list[PytestShortSummary]
    statistics: PytestStatistics
    has_failures_section: bool
    has_short_summary_section: bool
