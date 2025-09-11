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

        # Filter out infrastructure noise lines
        filtered_lines = []
        for line in cleaned_log.split("\n"):
            if line.strip() and not any(
                re.search(pattern, line, re.IGNORECASE)
                for pattern in cls.EXCLUDE_PATTERNS
            ):
                filtered_lines.append(line)

        # Rejoin the filtered content
        cleaned_log = "\n".join(filtered_lines)

        # Extract different sections
        detailed_failures = cls._extract_detailed_failures(cleaned_log)
        short_summary = cls._extract_short_summary(cleaned_log)
        statistics = cls._extract_statistics(cleaned_log)

        # Deduplicate between detailed failures and short summary
        deduplicated_failures, deduplicated_summary = cls._deduplicate_test_failures(
            detailed_failures, short_summary
        )

        # Check for section presence
        has_failures_section = "=== FAILURES ===" in cleaned_log
        has_short_summary_section = "short test summary info" in cleaned_log.lower()

        return PytestLogAnalysis(
            detailed_failures=deduplicated_failures,
            short_summary=deduplicated_summary,
            statistics=statistics,
            has_failures_section=has_failures_section,
            has_short_summary_section=has_short_summary_section,
        )

    @classmethod
    def _deduplicate_test_failures(
        cls,
        detailed_failures: list[PytestFailureDetail],
        short_summary: list[PytestShortSummary],
    ) -> tuple[list[PytestFailureDetail], list[PytestShortSummary]]:
        """
        Deduplicate test failures between detailed failures and short summary sections.

        Priority: Keep detailed failures (more information) over short summary entries.
        Remove duplicates based on:
        1. Same test function name
        2. Same exception type and message
        3. Same file path and approximate line number
        """
        # Create a set to track seen test failures
        seen_failures = set()
        deduplicated_detailed = []
        deduplicated_summary = []

        # First pass: Process detailed failures (higher priority)
        for detailed in detailed_failures:
            # Create a fingerprint for this failure
            fingerprint = cls._create_test_failure_fingerprint(detailed)

            if fingerprint not in seen_failures:
                seen_failures.add(fingerprint)
                deduplicated_detailed.append(detailed)

        # Second pass: Process short summary, skip duplicates
        for summary in short_summary:
            # Create a fingerprint for this summary
            fingerprint = cls._create_summary_failure_fingerprint(summary)

            if fingerprint not in seen_failures:
                seen_failures.add(fingerprint)
                deduplicated_summary.append(summary)

        return deduplicated_detailed, deduplicated_summary

    @classmethod
    def _create_test_failure_fingerprint(cls, failure: PytestFailureDetail) -> str:
        """Create a unique fingerprint for a detailed test failure"""
        # Use test function name, exception type, and core error message
        test_func = failure.test_function or "unknown"
        test_file = failure.test_file or "unknown"
        exception_type = failure.exception_type or "unknown"

        # Extract core error message without file paths and line numbers
        core_message = failure.exception_message or ""
        # Remove common pytest noise and make it more generic
        core_message = re.sub(r"'[^']*\.py'", "'file.py'", core_message)
        core_message = re.sub(r"line \d+", "line N", core_message)
        core_message = re.sub(r":\d+:", ":N:", core_message)

        # Include both test file and function to ensure unique fingerprints for different tests
        # This prevents deduplication of different test functions with similar errors
        return f"{test_file}::{test_func}|{exception_type}|{core_message[:100]}"

    @classmethod
    def _create_summary_failure_fingerprint(cls, summary: PytestShortSummary) -> str:
        """Create a unique fingerprint for a short summary failure"""
        # Use test function name, exception type, and core error message
        test_func = summary.test_function or "unknown"
        test_file = summary.test_file or "unknown"
        exception_type = summary.error_type or "unknown"

        # Extract core error message without file paths and line numbers
        core_message = summary.error_message or ""
        # Remove common pytest noise and make it more generic
        core_message = re.sub(r"'[^']*\.py'", "'file.py'", core_message)
        core_message = re.sub(r"line \d+", "line N", core_message)
        core_message = re.sub(r":\d+:", ":N:", core_message)

        # Include both test file and function to ensure unique fingerprints for different tests
        return f"{test_file}::{test_func}|{exception_type}|{core_message[:100]}"

    @classmethod
    def _extract_detailed_failures(cls, log_text: str) -> list[PytestFailureDetail]:
        """Extract detailed test failures from ALL FAILURES sections AND collection errors from ERRORS sections"""
        failures: list[PytestFailureDetail] = []

        # Extract from FAILURES sections
        failures_pattern = r"=+\s*FAILURES\s*=+(.*?)(?:=+\s*(?:short test summary info|ERRORS|={20,}|$))"
        failures_matches = re.finditer(
            failures_pattern, log_text, re.DOTALL | re.IGNORECASE
        )

        for failures_match in failures_matches:
            failures_section = failures_match.group(1)

            # Split by test failure headers (flexible underscore patterns)
            # Pattern 1: Long underscores: __________ test_name __________
            # Must have at least 5 consecutive underscores to avoid matching traceback separators
            test_pattern = r"_{5,}\s+(.+?)\s+_{5,}"
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

        # Extract from ERRORS sections (collection errors, import errors, etc.)
        errors_pattern = r"=+\s*ERRORS\s*=+(.*?)(?:=+\s*(?:short test summary info|FAILURES|={20,}|$))"
        errors_matches = re.finditer(
            errors_pattern, log_text, re.DOTALL | re.IGNORECASE
        )

        for errors_match in errors_matches:
            errors_section = errors_match.group(1)

            # Collection errors have format: _ ERROR collecting path/to/test_file.py _
            error_pattern = r"_\s*ERROR\s+collecting\s+(.+?)\s+_"
            error_matches = re.finditer(error_pattern, errors_section)

            for error_match in error_matches:
                test_file_path = error_match.group(1).strip()

                # Extract the content after this error header until the next error or end
                start_pos = error_match.end()
                next_error_match = re.search(
                    r"_\s*ERROR\s+collecting", errors_section[start_pos:]
                )

                if next_error_match:
                    end_pos = start_pos + next_error_match.start()
                    error_content = errors_section[start_pos:end_pos]
                else:
                    error_content = errors_section[start_pos:]

                # Parse collection error as a failure
                collection_failure = cls._parse_collection_error(
                    test_file_path, error_content
                )
                if collection_failure:
                    failures.append(collection_failure)

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
        # Strategy: Find the actual test file by looking for the test invocation in traceback
        # Priority: 1) Test files (contain "test"), 2) Files with test methods, 3) Fallback to any file

        # Look for all file references in the content
        file_line_matches = re.findall(
            r"([^/\s]+/[^:\s]+\.py):(\d+):\s+(?:in\s+(\w+)|(\w+(?:Exception|Error)))",
            content,
        )

        # Also look for the actual test file line which often appears as:
        # "test_file.py:line_number:"
        test_file_matches = re.findall(
            r"([^/\s]+/[^:\s]*test[^:\s]*\.py):(\d+):", content
        )

        test_file = None
        test_function = None

        # PRIORITY 1: Look for project test files (domains/, src/, tests/, etc.) - exclude system paths
        all_file_matches = file_line_matches + [
            (match[0], match[1], None) for match in test_file_matches
        ]

        for match in all_file_matches:
            file_path = match[0] if isinstance(match, tuple) else match
            func_name = (
                match[2] if len(match) > 2 and isinstance(match, tuple) else None
            )

            # Skip system files (anything with site-packages, python install paths, etc.)
            if any(
                sys_path in file_path
                for sys_path in [
                    "site-packages",
                    ".venv",
                    "/usr/",
                    "/root/.local",
                    "python3.",
                    "/opt/",
                    "cpython-",
                ]
            ):
                continue

            # Prioritize actual test files
            if "test" in file_path.lower() and file_path.endswith(".py"):
                test_file = file_path
                # Extract function name from header if not found in traceback
                if "::" in test_name:
                    test_function = test_name.split("::")[-1]
                elif func_name and not func_name.endswith(("Error", "Exception")):
                    test_function = func_name
                break

        # PRIORITY 2: If no test file found, look for any project file (non-system)
        if not test_file:
            for match in all_file_matches:
                file_path = match[0] if isinstance(match, tuple) else match
                func_name = (
                    match[2] if len(match) > 2 and isinstance(match, tuple) else None
                )

                # Skip system files
                if any(
                    sys_path in file_path
                    for sys_path in [
                        "site-packages",
                        ".venv",
                        "/usr/",
                        "/root/.local",
                        "python3.",
                        "/opt/",
                        "cpython-",
                    ]
                ):
                    continue

                # Use any project file
                test_file = file_path
                if func_name and not func_name.endswith(("Error", "Exception")):
                    test_function = func_name
                break

        # PRIORITY 3: Fallback to system files only if no project files found
        if not test_file and file_line_matches:
            first_match = file_line_matches[0]
            test_file = first_match[0]
            func_name = first_match[2] if first_match[2] else None
            if func_name and not func_name.endswith(("Error", "Exception")):
                test_function = func_name

        # If we still don't have a test function, extract from test_name
        if not test_function:
            if "::" in test_name:
                test_function = test_name.split("::")[-1]
            else:
                # The header IS the test function for class-based tests like TestHandlers.test_name
                if "." in test_name:
                    test_function = test_name.split(".")[-1]
                else:
                    test_function = test_name

        # Final fallback handling
        if not test_file:
            if "::" in test_name:
                # Fallback to parsing from test_name if it contains the full path
                parts = test_name.split("::")
                test_file = parts[0]
                test_function = parts[-1]
            else:
                # Last resort - use unknowns
                test_file = "unknown"
                if not test_function:
                    test_function = test_name

        # Reconstruct full test name with file path if it's not already included
        if "::" not in test_name and test_file != "unknown":
            test_name = f"{test_file}::{test_function}"

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

        exception_type = "unknown"
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
    def _parse_collection_error(
        cls, test_file_path: str, content: str
    ) -> PytestFailureDetail | None:
        """Parse a collection error (import errors, syntax errors during test collection)"""

        # Extract the actual error from the content
        # Look for Python traceback with the actual error location
        # Use pytest format: file.py:line: in function
        traceback_pattern = r"([^:\s]+\.py):(\d+): in (.+)"
        traceback_matches = re.findall(traceback_pattern, content)

        # Find the error in the test file itself (not in system/library files)
        actual_error_file = None
        actual_error_line = None

        for file_path, line_num, _function_name in traceback_matches:
            # The test file path should match or be contained in the file_path
            if test_file_path in file_path or file_path.endswith(
                test_file_path.split("/")[-1]
            ):
                actual_error_file = file_path
                actual_error_line = int(line_num)
                break

        # If no specific line found in test file, use the last traceback entry (usually the actual source)
        if not actual_error_file and traceback_matches:
            actual_error_file = traceback_matches[-1][0]
            actual_error_line = int(traceback_matches[-1][1])

        # Extract exception type and message
        exception_patterns = [
            r"(\w+Error): (.+?)(?:\n|$)",
            r"(\w+Exception): (.+?)(?:\n|$)",
        ]

        exception_type = "CollectionError"
        exception_message = "Failed to collect test"

        for pattern in exception_patterns:
            exception_match = re.search(pattern, content, re.MULTILINE)
            if exception_match:
                exception_type = exception_match.group(1)
                exception_message = exception_match.group(2).strip()
                break

        # Parse traceback for collection errors
        traceback = cls._parse_traceback(content)

        # Override traceback to ensure correct line number for the actual error
        # For collection errors, create a prioritized traceback with the actual error location first
        if actual_error_file and actual_error_line:
            # Create a new traceback entry for the actual error location
            actual_error_entry = None

            # Look for existing traceback entry that matches our error location
            for tb_entry in traceback:
                if (
                    tb_entry.file_path == actual_error_file
                    and tb_entry.line_number == actual_error_line
                ):
                    actual_error_entry = tb_entry
                    break

            # If no matching entry found, create one
            if not actual_error_entry:
                actual_error_entry = PytestTraceback(
                    file_path=actual_error_file,
                    line_number=actual_error_line,
                    function_name="<module>",  # Collection errors are at module level
                    code_line=None,  # We don't have the actual code line
                    error_type=exception_type,
                    error_message=exception_message,
                )

            # Put the actual error location first in the traceback
            other_entries = [tb for tb in traceback if tb != actual_error_entry]
            traceback = [actual_error_entry] + other_entries

        return PytestFailureDetail(
            test_name=f"Collection error in {test_file_path.split('/')[-1]}",
            test_file=actual_error_file or test_file_path,
            test_function="<module>",  # Collection errors happen at module level
            test_parameters=None,
            platform_info=None,
            python_version=None,
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

        # Reject single characters or very short strings (these are usually traceback artifacts)
        if len(header) <= 2:
            return False

        # Reject traceback separator lines (single underscores, spaces, etc.)
        if re.match(r"^[_\s]+$", header):
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
        # 3. Be a pytest class-based test (e.g., "TestClassName.test_method")
        # 4. Be a simple test function name

        if header.startswith("test_"):
            return True

        # For paths with ::, be more strict - the function name after :: must be a test
        if "::" in header:
            parts = header.split("::")
            if len(parts) >= 2:
                function_name = parts[-1]
                # Function must start with "test_" or be a test class method
                if (
                    function_name.startswith("test_")
                    or re.match(
                        r"^Test[A-Z][a-zA-Z0-9_]*\.test_[a-zA-Z0-9_]*$", function_name
                    )
                    or "test_" in function_name
                ):
                    # Also check that the file path looks like a test file
                    file_path = parts[0]
                    if "test" in file_path.lower() and file_path.endswith(".py"):
                        return True

                # Special case: simple class::method format like TestClass::test_method
                if len(parts) == 2:
                    class_name, method_name = parts
                    if class_name.startswith("Test") and method_name.startswith(
                        "test_"
                    ):
                        return True
            return False

        # Check for pytest class-based tests: TestClassName.test_method
        if re.match(r"^Test[A-Z][a-zA-Z0-9_]*\.test_[a-zA-Z0-9_]*$", header):
            return True

        # Additional check: if it contains common non-test words, reject it
        non_test_words = ["coverage", "platform", "summary", "report", "stmts", "miss"]
        if any(word in header.lower() for word in non_test_words):
            return False

        # Reject anything that looks like a file path without test indicators
        if "/" in header and not (
            "test" in header.lower() and header.endswith("test_")
        ):
            return False

        # If it looks like a simple identifier and doesn't contain spaces, it might be a test
        # But be more restrictive - it should contain "test" somewhere
        if re.match(r"^[a-zA-Z_][a-zA-Z0-9_.]*$", header):
            return "test" in header.lower()

        return False

    @classmethod
    def _parse_traceback(cls, content: str) -> list[PytestTraceback]:
        """Parse traceback entries from failure content"""
        traceback_entries: list[PytestTraceback] = []

        # Look for traceback entries in multiple formats:
        # 1. Standard Python format: File "path", line N, in function
        # 2. Pytest format: path:line: in function
        # 3. Simple pytest format: path:line: ExceptionType
        traceback_pattern_standard = r'File "([^"]+)", line (\d+), in (\w+)'
        traceback_pattern_pytest = r"([^/\s]+/[^:\s]+\.py):(\d+):\s+in\s+(\w+)"
        traceback_pattern_simple = (
            r"([^/\s]+/[^:\s]+\.py):(\d+):\s+(\w+(?:Exception|Error))"
        )
        code_pattern = r"^\s{4,}(.+)$"  # Code lines are indented

        lines = content.split("\n")
        i = 0

        while i < len(lines):
            line = lines[i]

            # Try standard Python traceback format first
            traceback_match = re.search(traceback_pattern_standard, line)
            function_name = None

            if not traceback_match:
                # Try pytest format with 'in function'
                traceback_match = re.search(traceback_pattern_pytest, line)

            if not traceback_match:
                # Try simple pytest format: file.py:line: ExceptionType
                traceback_match = re.search(traceback_pattern_simple, line)
                if traceback_match:
                    # For simple format, try to extract function name from context
                    # Look backwards for a 'def function_name():' line
                    for j in range(i - 1, max(0, i - 10), -1):
                        if j < len(lines):
                            def_match = re.search(r"def\s+(\w+)\s*\(", lines[j])
                            if def_match:
                                function_name = def_match.group(1)
                                break

            if traceback_match:
                file_path = traceback_match.group(1)
                line_number = int(traceback_match.group(2))

                # Function name handling based on format
                if function_name is None:
                    if len(traceback_match.groups()) >= 3:
                        function_name = traceback_match.group(3)
                    else:
                        function_name = "unknown"

                # Get the code line (usually the next line or look for '>   ' prefix)
                code_line = None

                # Look for code lines with '>' prefix in surrounding lines
                for j in range(max(0, i - 3), min(len(lines), i + 3)):
                    if j < len(lines) and lines[j].strip().startswith(">"):
                        code_line = (
                            lines[j].strip()[1:].strip()
                        )  # Remove '>' and whitespace
                        break

                # Fallback: look for indented code lines
                if not code_line and i + 1 < len(lines):
                    next_line = lines[i + 1]
                    code_match = re.match(code_pattern, next_line)
                    if code_match:
                        code_line = code_match.group(1).strip()

                # Look for error info in nearby lines
                error_type = None
                error_message = None
                for j in range(max(0, i - 2), min(len(lines), i + 5)):
                    if j < len(lines):
                        error_match = re.search(
                            r"(\w+(?:Exception|Error)): (.+)", lines[j]
                        )
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
                    error_type = "unknown"
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
            # More flexible matching - don't require '=' character
            if (
                ("failed" in line.lower() or "passed" in line.lower())
                and ("in " in line and "s" in line)
                # Remove the '=' requirement to catch clean summary lines
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
