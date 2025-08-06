"""
Enhanced pytest log parser for extracting detailed test failures, short summaries, and statistics

Copyright (c) 2025 Siarhei Skuratovich
Licensed under the MIT License - see LICENSE file for details
"""

import re

from ..models.pytest_models import (
    PytestFailureDetail,
    PytestLogAnalysis,
    PytestShortSummary,
    PytestStatistics,
    PytestTraceback,
)
from .base_parser import BaseParser


class PytestLogParser(BaseParser):
    """Enhanced parser for pytest logs with detailed failure extraction"""

    @classmethod
    def parse_pytest_log(cls, log_text: str) -> PytestLogAnalysis:
        """
        Parse a pytest log and extract detailed failures, short summary, and statistics

        Args:
            log_text: The complete pytest log text

        Returns:
            Complete pytest log analysis with all extracted information
        """
        # Clean ANSI sequences first
        cleaned_log = cls.clean_ansi_sequences(log_text)

        # Extract different sections
        detailed_failures = cls._extract_detailed_failures(cleaned_log)
        short_summary = cls._extract_short_summary(cleaned_log)
        statistics = cls._extract_statistics(cleaned_log)

        # Check for section presence
        has_failures_section = "=== FAILURES ===" in cleaned_log
        has_short_summary_section = "short test summary info" in cleaned_log.lower()

        return PytestLogAnalysis(
            detailed_failures=detailed_failures,
            short_summary=short_summary,
            statistics=statistics,
            has_failures_section=has_failures_section,
            has_short_summary_section=has_short_summary_section,
        )

    @classmethod
    def _extract_detailed_failures(cls, log_text: str) -> list[PytestFailureDetail]:
        """Extract detailed test failures from ALL FAILURES sections"""
        failures: list[PytestFailureDetail] = []

        # Find ALL FAILURES sections using finditer instead of search
        failures_pattern = r"=+\s*FAILURES\s*=+(.*?)(?:=+\s*(?:short test summary info|ERRORS|={20,}|$))"
        failures_matches = re.finditer(
            failures_pattern, log_text, re.DOTALL | re.IGNORECASE
        )

        for failures_match in failures_matches:
            failures_section = failures_match.group(1)

            # Split by test failure headers (lines with underscores)
            test_pattern = r"_{10,}\s+(.+?)\s+_{10,}"
            test_matches = re.split(test_pattern, failures_section)

            # Process each test failure in this section
            for i in range(1, len(test_matches), 2):
                if i + 1 < len(test_matches):
                    test_header = test_matches[i].strip()
                    test_content = test_matches[i + 1].strip()

                    failure_detail = cls._parse_single_failure(
                        test_header, test_content
                    )
                    if failure_detail:
                        failures.append(failure_detail)

        return failures

    @classmethod
    def _parse_single_failure(
        cls, header: str, content: str
    ) -> PytestFailureDetail | None:
        """Parse a single test failure from its header and content"""
        # Filter out non-test sections (coverage reports, etc.)
        if not cls._is_valid_test_header(header):
            return None

        # Parse test name and parameters
        test_match = re.match(r"(.+?)(?:\[(.+?)\])?$", header)
        if not test_match:
            return None

        test_name = test_match.group(1).strip()
        test_parameters = test_match.group(2) if test_match.group(2) else None

        # Extract test file and function name
        # First try to find the file path from the content (test/test_failures.py:10: in test_function)
        file_line_match = re.search(
            r"([^/\s]+/[^:\s]+\.py):(\d+):\s+in\s+(\w+)", content
        )

        if file_line_match:
            test_file = file_line_match.group(1)
            test_function = file_line_match.group(3)
            # Reconstruct full test name with file path if it's not already included
            if "::" not in test_name:
                test_name = f"{test_file}::{test_function}"
        elif "::" in test_name:
            # Fallback to parsing from test_name if it contains the full path
            parts = test_name.split("::")
            test_file = parts[0]
            test_function = parts[-1]
        else:
            # Last resort - use unknowns
            test_file = "unknown"
            test_function = test_name

        # Extract platform info
        platform_match = re.search(
            r"\[gw\d+\]\s+(.+?)\s+--\s+Python\s+([\d.]+)", content
        )
        platform_info = platform_match.group(1) if platform_match else None
        python_version = platform_match.group(2) if platform_match else None

        # Extract the main exception
        # Look for exception patterns in different formats:
        # 1. Direct format: ExceptionType: message
        # 2. Pytest format with E prefix: E   ExceptionType: message
        # 3. Exception without "Error" suffix: Exception: message
        exception_patterns = [
            r"(?:E\s+)?(\w+(?:\.\w+)*(?:Exception|Error)): (.+?)(?:\n|$)",  # Standard Error/Exception types
            r"(?:E\s+)?(Exception): (.+?)(?:\n|$)",  # Plain "Exception" type
            r"(?:E\s+)?(\w+Error): (.+?)(?:\n|$)",  # Any *Error type
            r"(?:E\s+)?(\w+Exception): (.+?)(?:\n|$)",  # Any *Exception type
        ]

        exception_type = "Unknown"
        exception_message = "Unknown error"

        for pattern in exception_patterns:
            exception_match = re.search(pattern, content, re.MULTILINE)
            if exception_match:
                exception_type = exception_match.group(1)
                exception_message = exception_match.group(2).strip()
                break

        # Parse traceback
        traceback = cls._parse_traceback(content)

        return PytestFailureDetail(
            test_name=test_name,
            test_file=test_file,
            test_function=test_function,
            test_parameters=test_parameters,
            platform_info=platform_info,
            python_version=python_version,
            exception_type=exception_type,
            exception_message=exception_message,
            traceback=traceback,
            full_error_text=content,
        )

    @classmethod
    def _is_valid_test_header(cls, header: str) -> bool:
        """Check if a header represents a valid test failure"""
        header = header.strip()

        # Must not be empty
        if not header:
            return False

        # Filter out coverage reports and other non-test sections
        invalid_patterns = [
            r"^coverage:",
            r"^platform\s+",
            r"^Name\s+Stmts",
            r"^-+$",
            r"^=+$",
            r"^\s*$",
        ]

        for pattern in invalid_patterns:
            if re.match(pattern, header, re.IGNORECASE):
                return False

        # Valid test headers should either:
        # 1. Start with "test_" (function name)
        # 2. Contain "::" indicating a test path (e.g., "path/test_file.py::test_function")
        # 3. Be a simple test function name

        if header.startswith("test_"):
            return True

        if "::" in header and "test_" in header:
            return True

        # Additional check: if it contains common non-test words, reject it
        non_test_words = ["coverage", "platform", "summary", "report", "stmts", "miss"]
        if any(word in header.lower() for word in non_test_words):
            return False

        # If it looks like a simple identifier and doesn't contain spaces, it might be a test
        return re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*$", header) is not None

    @classmethod
    def _parse_traceback(cls, content: str) -> list[PytestTraceback]:
        """Parse traceback entries from failure content"""
        traceback_entries: list[PytestTraceback] = []

        # Look for traceback entries in both formats:
        # 1. Standard Python format: File "path", line N, in function
        # 2. Pytest format: path:line: in function
        traceback_pattern_standard = r'File "([^"]+)", line (\d+), in (\w+)'
        traceback_pattern_pytest = r"([^/\s]+/[^:\s]+\.py):(\d+):\s+in\s+(\w+)"
        code_pattern = r"^\s{4,}(.+)$"  # Code lines are indented

        lines = content.split("\n")
        i = 0

        while i < len(lines):
            line = lines[i]

            # Try standard Python traceback format first
            traceback_match = re.search(traceback_pattern_standard, line)
            if not traceback_match:
                # Try pytest format
                traceback_match = re.search(traceback_pattern_pytest, line)

            if traceback_match:
                file_path = traceback_match.group(1)
                line_number = int(traceback_match.group(2))
                function_name = traceback_match.group(3)

                # Get the code line (usually the next line)
                code_line = None
                if i + 1 < len(lines):
                    next_line = lines[i + 1]
                    code_match = re.match(code_pattern, next_line)
                    if code_match:
                        code_line = code_match.group(1).strip()

                # For pytest format, also try to get code from current line after the ':'
                if not code_line and ":" in line:
                    # Look for code after the location info
                    parts = line.split(":", 3)  # Split on first 3 colons
                    if len(parts) > 3:
                        potential_code = parts[3].strip()
                        if potential_code and not potential_code.startswith("in "):
                            code_line = potential_code

                # Look for error info in nearby lines
                error_type = None
                error_message = None
                for j in range(max(0, i - 2), min(len(lines), i + 5)):
                    error_match = re.search(r"(\w+(?:Exception|Error)): (.+)", lines[j])
                    if error_match:
                        error_type = error_match.group(1)
                        error_message = error_match.group(2)
                        break

                traceback_entries.append(
                    PytestTraceback(
                        file_path=file_path,
                        line_number=line_number,
                        function_name=function_name,
                        code_line=code_line,
                        error_type=error_type,
                        error_message=error_message,
                    )
                )

            i += 1

        return traceback_entries

    @classmethod
    def _extract_short_summary(cls, log_text: str) -> list[PytestShortSummary]:
        """Extract test failures from ALL short test summary info sections"""
        short_summary: list[PytestShortSummary] = []

        # Find ALL short test summary sections using finditer instead of search
        summary_pattern = r"=+\s*short test summary info\s*=+(.*?)(?==+|$)"
        summary_matches = re.finditer(
            summary_pattern, log_text, re.DOTALL | re.IGNORECASE
        )

        for summary_match in summary_matches:
            summary_section = summary_match.group(1)

            # Improved pattern: match lines starting with FAILED, capturing everything up to the next line that starts with FAILED or a separator
            failed_pattern = r"^FAILED\s+(.+?)(?:\s+-\s+)(.+?)(?=^FAILED\s+|^=+|\Z)"
            for match in re.finditer(
                failed_pattern, summary_section, re.DOTALL | re.MULTILINE
            ):
                test_spec = match.group(1).strip()
                error_info = match.group(2).strip()

                # Parse test specification
                test_file = "unknown"
                test_function = "unknown"
                test_parameters = None

                if "::" in test_spec:
                    parts = test_spec.split("::")
                    test_file = parts[0]
                    func_part = parts[-1]

                    # Check for parameters
                    param_match = re.match(r"(.+?)\[(.+?)\]$", func_part)
                    if param_match:
                        test_function = param_match.group(1)
                        test_parameters = param_match.group(2)
                    else:
                        test_function = func_part

                # Parse error type and message
                error_match = re.match(
                    r"(\w+(?:\.\w+)*(?:Exception|Error)): (.+)", error_info, re.DOTALL
                )
                if error_match:
                    error_type = error_match.group(1)
                    error_message = error_match.group(2)
                else:
                    # Handle cases where the error format is different
                    error_type = "Unknown"
                    error_message = error_info

                short_summary.append(
                    PytestShortSummary(
                        test_name=test_spec,
                        test_file=test_file,
                        test_function=test_function,
                        test_parameters=test_parameters,
                        error_type=error_type,
                        error_message=error_message,
                    )
                )

        return short_summary

    @classmethod
    def _extract_statistics(cls, log_text: str) -> PytestStatistics:
        """Extract pytest run statistics from the final summary line"""
        # Look for pytest final summary line with various possible formats
        # Examples:
        # "= 9 failed, 96 passed, 7 skipped in 798.19s (0:13:18) ="
        # "= 4 failed, 9 passed, 1 xfailed in 5.56s ="
        # With ANSI sequences: "[31m= [31m[1m4 failed[0m, [32m9 passed[0m, [33m1 xfailed[0m[31m in 5.56s[0m[31m =[0m"

        # First, let's try to find the summary line with a more flexible approach
        summary_lines = []

        # Look for lines containing "failed" and "passed" and time information
        for line in log_text.split("\n"):
            if (
                ("failed" in line.lower() or "passed" in line.lower())
                and ("in " in line and "s" in line)
                and "=" in line
            ):
                summary_lines.append(line)

        # Process the most likely summary line (usually the last one)
        if summary_lines:
            summary_line = summary_lines[-1]

            # Extract individual components with more flexible patterns
            failed = 0
            passed = 0
            skipped = 0
            errors = 0
            warnings = 0
            xfailed = 0
            duration_seconds = None
            duration_formatted = None

            # Extract each statistic individually
            failed_match = re.search(r"(\d+)\s+failed", summary_line, re.IGNORECASE)
            if failed_match:
                failed = int(failed_match.group(1))

            passed_match = re.search(r"(\d+)\s+passed", summary_line, re.IGNORECASE)
            if passed_match:
                passed = int(passed_match.group(1))

            skipped_match = re.search(r"(\d+)\s+skipped", summary_line, re.IGNORECASE)
            if skipped_match:
                skipped = int(skipped_match.group(1))

            error_match = re.search(r"(\d+)\s+errors?", summary_line, re.IGNORECASE)
            if error_match:
                errors = int(error_match.group(1))

            warning_match = re.search(r"(\d+)\s+warnings?", summary_line, re.IGNORECASE)
            if warning_match:
                warnings = int(warning_match.group(1))

            # Handle xfailed (expected failures)
            xfailed_match = re.search(r"(\d+)\s+xfailed", summary_line, re.IGNORECASE)
            if xfailed_match:
                xfailed = int(xfailed_match.group(1))

            # Extract duration
            duration_match = re.search(r"in\s+([\d.]+)s", summary_line, re.IGNORECASE)
            if duration_match:
                duration_seconds = float(duration_match.group(1))

            # Extract formatted duration (if present)
            formatted_match = re.search(r"\(([\d:]+)\)", summary_line)
            if formatted_match:
                duration_formatted = formatted_match.group(1)

            # Total tests includes xfailed
            total_tests = failed + passed + skipped + errors + xfailed

            return PytestStatistics(
                total_tests=total_tests,
                passed=passed,
                failed=failed,
                skipped=skipped + xfailed,  # Count xfailed as skipped for consistency
                errors=errors,
                warnings=warnings,
                duration_seconds=duration_seconds,
                duration_formatted=duration_formatted,
            )

        # Fallback: if no summary line found, return empty statistics
        return PytestStatistics(
            total_tests=0,
            passed=0,
            failed=0,
            skipped=0,
            errors=0,
            warnings=0,
            duration_seconds=None,
            duration_formatted=None,
        )
