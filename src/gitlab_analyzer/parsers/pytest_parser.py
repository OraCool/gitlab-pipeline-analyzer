"""
Unified pytest parser implementing SOLID principles.

This parser handles all pytest scenarios including:
- Standard pytest test output
- Django-specific pytest errors
- Test failures, collection errors, and setup/teardown issues
- Detailed failure analysis with tracebacks

Implements BaseFrameworkParser interface for consistent architecture.

Copyright (c) 2025 Siarhei Skuratovich
Licensed under the MIT License - see LICENSE file for details
"""

import re
from typing import Any

from ..models import LogEntry
from ..models.pytest_models import (
    PytestFailureDetail,
    PytestLogAnalysis,
    PytestShortSummary,
    PytestStatistics,
    PytestTraceback,
)
from ..utils.debug import debug_print, verbose_debug_print
from .base_parser import (
    BaseFrameworkDetector,
    BaseFrameworkParser,
    BaseParser,
    TestFramework,
)


class PytestDetector(BaseFrameworkDetector):
    """Detects pytest-based jobs"""

    @property
    def framework(self) -> TestFramework:
        return TestFramework.PYTEST

    @property
    def priority(self) -> int:
        return 90  # High priority for Python projects

    def detect(self, job_name: str, job_stage: str, trace_content: str) -> bool:
        """Detect pytest jobs using comprehensive logic"""
        # Exclude linting jobs first
        linting_indicators = [
            r"make:.*\[.*lint.*\].*Error",
            r"lint.*failed",
            r"ruff.*check.*failed",
            r"black.*check.*failed",
        ]

        if self._exclude_by_patterns(trace_content, linting_indicators):
            return False

        # Exclude JavaScript/Node.js/Jest jobs
        js_indicators = [
            r"\$ node\s",  # Node.js execution
            r"npm\s+(run\s+)?test",  # npm test commands
            r"yarn\s+(run\s+)?test",  # yarn test commands
            r"jest",  # Jest framework mentions
            r"Test Suites:",  # Jest output pattern
            r"Browserslist:",  # Common in JS projects
            r"\.spec\.(js|ts)",  # JS/TS test files
            r"\.test\.(js|ts)",  # JS/TS test files
        ]

        if self._exclude_by_patterns(trace_content, js_indicators):
            return False

        # Check job name patterns
        pytest_patterns = [
            r"test",
            r"pytest",
            r"unit.*test",
            r"integration.*test",
            r"e2e.*test",
        ]

        if self._check_job_name_patterns(job_name, pytest_patterns):
            return True

        # Check trace content for pytest indicators (comprehensive)
        if trace_content:
            import re

            # High-confidence pytest indicators
            high_confidence_indicators = [
                r"=+\s*FAILURES\s*=+",  # pytest FAILURES section
                r"=+\s*test session starts\s*=+",  # pytest session start
                r"collected \d+ items?",  # pytest collection message
                r"::\w+.*FAILED",  # pytest test failure format
                r"FAILED.*::\w+",  # Alternative FAILED pattern
                r"conftest\.py",  # pytest configuration file
                r"short test summary info",  # pytest summary section
            ]

            for indicator in high_confidence_indicators:
                if re.search(indicator, trace_content, re.IGNORECASE):
                    return True

            # Command indicators
            command_indicators = [
                r"uv run.*pytest",
                r"coverage run -m pytest",
                r"python -m pytest",
                r"pytest.*\.py",
            ]

            for indicator in command_indicators:
                if re.search(indicator, trace_content, re.IGNORECASE):
                    return True

        return False


class PytestParser(BaseFrameworkParser):
    """Unified pytest parser with Django awareness"""

    # Django-specific error patterns for pytest context
    DJANGO_ERROR_PATTERNS = [
        (r"django\.core\.exceptions\.ValidationError: (.+)", "error"),
        (r"ValidationError: (.+)", "error"),
        (r"E\s+django\.core\.exceptions\.ValidationError: (.+)", "error"),
        (r"E\s+ValidationError: (.+)", "error"),
        (r"django\.db\.utils\.IntegrityError: (.+)", "error"),
        (r"IntegrityError: (.+)", "error"),
        (r"E\s+django\.db\.utils\.IntegrityError: (.+)", "error"),
        (r"E\s+IntegrityError: (.+)", "error"),
        (r"UNIQUE constraint failed: (.+)", "error"),
        (r"duplicate key value violates unique constraint \"(.+)\"", "error"),
        (r"E\s+UNIQUE constraint failed: (.+)", "error"),
        (r"E\s+duplicate key value violates unique constraint \"(.+)\"", "error"),
        (r"django\.[a-zA-Z_.]+\.([A-Za-z]+(?:Error|Exception)): (.+)", "error"),
        (r"E\s+django\.[a-zA-Z_.]+\.([A-Za-z]+(?:Error|Exception)): (.+)", "error"),
        # General Python errors that commonly occur in Django projects
        (r"TypeError: (.+)", "error"),
        (r"AttributeError: (.+)", "error"),
        (r"ValueError: (.+)", "error"),
        (r"KeyError: (.+)", "error"),
        (r"NameError: (.+)", "error"),
        (r"ImportError: (.+)", "error"),
        (r"ModuleNotFoundError: (.+)", "error"),
    ]

    @property
    def framework(self) -> TestFramework:
        return TestFramework.PYTEST

    def parse(self, trace_content: str, **kwargs) -> dict[str, Any]:
        """Parse pytest logs with comprehensive Django and standard pytest support"""
        # Check if Django patterns are present
        django_indicators = [
            "django.core.exceptions.ValidationError",
            "UNIQUE constraint failed",
            "django.db.utils.IntegrityError",
            "manage.py",
            "django.conf",
        ]

        is_django = any(
            indicator.lower() in trace_content.lower()
            for indicator in django_indicators
        )

        if is_django:
            return self._parse_django_pytest(trace_content)
        else:
            return self._parse_standard_pytest(trace_content)

    def _parse_django_pytest(self, trace_content: str) -> dict[str, Any]:
        """Parse Django-aware pytest logs"""
        # Use the comprehensive pytest analysis first
        pytest_analysis = PytestLogParser.parse_pytest_log(trace_content)

        # Extract Django-specific errors using dedicated patterns
        django_errors = self._extract_django_errors(trace_content)

        # Convert all to standardized format
        errors = []

        # Process detailed failures from pytest analysis
        if pytest_analysis.detailed_failures:
            for failure in pytest_analysis.detailed_failures:
                errors.append(
                    {
                        "test_file": failure.test_file or "unknown",
                        "test_function": failure.test_function or "unknown",
                        "exception_type": failure.exception_type or "Pytest Failure",
                        "message": failure.exception_message or "No message",
                        "line_number": getattr(failure, "line_number", None),
                        "has_traceback": bool(failure.traceback),
                    }
                )

        # Add Django-specific errors from LogEntry format
        for entry in django_errors:
            errors.append(
                {
                    "test_file": entry.file_path or "Django Setup",
                    "test_function": f"Django Error (Line {entry.line_number or 'Unknown'})",
                    "exception_type": "Django ValidationError",
                    "message": entry.message,
                    "line_number": entry.line_number or 0,
                    "has_traceback": False,
                }
            )

        # Get statistics from pytest analysis
        stats = pytest_analysis.statistics or PytestStatistics()

        return self.validate_output(
            {
                "parser_type": "pytest",
                "framework": self.framework.value,
                "errors": errors,
                "error_count": len(errors),
                "warnings": [],
                "warning_count": 0,
                "summary": {
                    "total_tests": stats.total_tests or len(errors),
                    "failed": stats.failed or len(errors),
                    "passed": stats.passed or 0,
                    "skipped": stats.skipped or 0,
                },
            }
        )

    def _parse_standard_pytest(self, trace_content: str) -> dict[str, Any]:
        """Parse standard pytest logs using detailed analysis"""
        pytest_analysis = PytestLogParser.parse_pytest_log(trace_content)

        # Convert to standardized format
        errors = []

        # Process detailed failures
        if pytest_analysis.detailed_failures:
            for failure in pytest_analysis.detailed_failures:
                errors.append(
                    {
                        "test_file": failure.test_file or "unknown",
                        "test_function": failure.test_function or "unknown",
                        "exception_type": failure.exception_type or "Pytest Failure",
                        "message": failure.exception_message or "No message",
                        "line_number": getattr(failure, "line_number", None),
                        "has_traceback": bool(failure.traceback),
                    }
                )

        # Process short summary if no detailed failures
        if not errors and pytest_analysis.short_summary:
            for summary in pytest_analysis.short_summary:
                errors.append(
                    {
                        "test_file": summary.test_file or "unknown",
                        "test_function": summary.test_function or "unknown",
                        "exception_type": summary.error_type or "Pytest Error",
                        "message": summary.error_message or "No message",
                        "line_number": summary.line_number,
                        "file_path": summary.test_file,  # Use the test_file which now contains source file path
                        "has_traceback": False,
                    }
                )

        # Get statistics
        stats = pytest_analysis.statistics or PytestStatistics()

        return self.validate_output(
            {
                "parser_type": "pytest",
                "framework": self.framework.value,
                "errors": errors,
                "error_count": len(errors),
                "warnings": [],
                "warning_count": 0,
                "summary": {
                    "total_tests": stats.total_tests or len(errors),
                    "failed": stats.failed or len(errors),
                    "passed": stats.passed or 0,
                    "skipped": stats.skipped or 0,
                },
            }
        )

    def _extract_django_errors(self, log_text: str) -> list[LogEntry]:
        """Extract Django-specific errors that might be missed by standard pytest parsing"""
        cleaned_log_text = BaseParser.clean_ansi_sequences(log_text)
        entries: list[LogEntry] = []
        lines = cleaned_log_text.split("\n")

        # Standard exclude patterns from LogParser
        EXCLUDE_PATTERNS = [
            r"Running with gitlab-runner",
            r"Preparing the.*executor",
            r"Using.*kubernetes.*executor",
            r"section_start:",
            r"section_end:",
        ]

        for line_num, log_line in enumerate(lines, 1):
            log_line = log_line.strip()
            if not log_line:
                continue

            # Skip GitLab CI infrastructure messages
            if any(
                re.search(pattern, log_line, re.IGNORECASE)
                for pattern in EXCLUDE_PATTERNS
            ):
                continue

            # Check for Django-specific errors
            for pattern, level in self.DJANGO_ERROR_PATTERNS:
                match = re.search(pattern, log_line, re.IGNORECASE)
                if match:
                    # Extract actual Python file line number and file path if available
                    file_info = self._extract_file_info_from_traceback(
                        lines, line_num, log_line
                    )
                    actual_line_number = file_info["line_number"]
                    actual_file_path = file_info["file_path"]

                    # Look for file:line pattern in preceding lines if not found in current line
                    if not actual_file_path:
                        # Check a few lines before for file:line patterns
                        for check_line in range(max(0, line_num - 3), line_num):
                            check_line_content = lines[check_line].strip()
                            check_file_info = self._extract_file_info_from_traceback(
                                lines, check_line, check_line_content
                            )
                            if check_file_info["file_path"]:
                                actual_file_path = check_file_info["file_path"]
                                actual_line_number = check_file_info["line_number"]
                                break

                    entry = LogEntry(
                        level=level,
                        message=log_line,
                        line_number=actual_line_number,
                        file_path=actual_file_path,
                        context=self._get_context(lines, line_num),
                        error_type=self._classify_django_error_type(log_line),
                    )
                    entries.append(entry)
                    break

        return entries

    def _extract_source_line_number(
        self, lines: list[str], current_line: int, log_line: str
    ) -> int:
        """Extract the actual source code line number from Django traceback"""
        file_info = self._extract_file_info_from_traceback(
            lines, current_line, log_line
        )
        return file_info["line_number"]

    def _extract_file_info_from_traceback(
        self, lines: list[str], current_line: int, log_line: str
    ) -> dict[str, Any]:
        """Extract both file path and line number from Django traceback (legacy method)"""
        file_line_patterns = [
            r'^\s*File\s+"([^"]+)",\s+line\s+(\d+)',
            r"^\s*([^:\s]+):(\d+):\s*in\s+",
            r"^\s*([^:\s]+):(\d+):\s*",
        ]

        # Check current line first
        for pattern in file_line_patterns:
            file_match = re.search(pattern, log_line)
            if file_match and len(file_match.groups()) >= 2:
                file_path = file_match.group(1)
                if not any(
                    sys_path in file_path
                    for sys_path in [
                        "/root/.local/share/uv/python/",
                        "site-packages",
                        "/usr/lib",
                    ]
                ):
                    try:
                        return {
                            "file_path": file_path,
                            "line_number": int(file_match.group(2)),
                        }
                    except (ValueError, IndexError):
                        pass

        return {"file_path": None, "line_number": current_line}

    def _get_context(
        self, lines: list[str], current_line: int, context_size: int = 5
    ) -> str:
        """Get surrounding context for error with infrastructure noise filtering"""
        start = max(0, current_line - context_size - 1)
        end = min(len(lines), current_line + context_size)
        context_lines = lines[start:end]

        filtered_lines = []
        for line in context_lines:
            line = line.strip()
            if not line:
                continue

            # Keep relevant context, exclude only obvious infrastructure noise
            infrastructure_patterns = [
                r"Running with gitlab-runner",
                r"Preparing the.*executor",
                r"Using Kubernetes",
                r"section_start:",
                r"section_end:",
            ]

            should_keep = True
            for pattern in infrastructure_patterns:
                if re.search(pattern, line, re.IGNORECASE):
                    should_keep = False
                    break

            if should_keep:
                filtered_lines.append(line)

        return "\n".join(filtered_lines)

    def _classify_django_error_type(self, message: str) -> str:
        """Classify Django error types for better categorization"""
        message_lower = message.lower()

        if "validationerror" in message_lower:
            return "django_validation"
        elif "integrityerror" in message_lower:
            return "django_integrity"
        elif "constraint" in message_lower:
            return "database_constraint"
        elif "django" in message_lower:
            return "django_framework"
        else:
            return "unknown"

    def _extract_source_file_and_line(
        self, error_message: str, full_log_text: str = "", error_type: str = ""
    ) -> tuple[str | None, int | None]:
        """
        Pytest-specific implementation of source file and line number extraction.

        Delegates to the PytestLogParser utility for consistent behavior across all pytest parsing.
        """
        return PytestLogParser._extract_source_file_and_line(
            error_message, full_log_text, error_type
        )


# Preserve the existing detailed parsing logic as a utility class
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
        Additionally, enhance short summary entries with line numbers from matching detailed failures.

        Remove duplicates based on:
        1. Same test function name
        2. Same exception type and message
        3. Same file path and approximate line number
        """
        # Create a set to track seen test failures and a map for line number enhancement
        seen_failures = set()
        deduplicated_detailed = []
        deduplicated_summary = []
        detailed_failure_map = {}  # Maps fingerprint to detailed failure for line number lookup

        # First pass: Process detailed failures (higher priority)
        for detailed in detailed_failures:
            # Create a fingerprint for this failure
            fingerprint = cls._create_test_failure_fingerprint(detailed)

            if fingerprint not in seen_failures:
                seen_failures.add(fingerprint)
                deduplicated_detailed.append(detailed)
                # Store the detailed failure for potential line number enhancement
                detailed_failure_map[fingerprint] = detailed

        # Second pass: Process short summary, skip duplicates but enhance with line numbers
        for summary in short_summary:
            # Create a fingerprint for this summary
            fingerprint = cls._create_summary_failure_fingerprint(summary)

            if fingerprint not in seen_failures:
                # Check if we have a matching detailed failure with line number info
                if fingerprint in detailed_failure_map:
                    detailed_match = detailed_failure_map[fingerprint]
                    # Enhance the summary with line number info from detailed failure
                    if detailed_match.line_number and not summary.line_number:
                        # Create enhanced summary with line number from detailed failure
                        enhanced_summary = PytestShortSummary(
                            test_name=summary.test_name,
                            test_file=detailed_match.test_file
                            or summary.test_file,  # Prefer detailed file path
                            test_function=summary.test_function,
                            test_parameters=summary.test_parameters,
                            error_type=summary.error_type,
                            error_message=summary.error_message,
                            line_number=detailed_match.line_number,  # Use line number from detailed failure
                        )
                        deduplicated_summary.append(enhanced_summary)
                    else:
                        deduplicated_summary.append(summary)
                else:
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

            # Handle different ERROR formats:
            # 1. Collection errors: _ ERROR collecting path/to/test_file.py _
            # 2. Setup errors: _ ERROR at setup of TestClass.test_method _
            # 3. Teardown errors: _ ERROR at teardown of TestClass.test_method _

            # Collection errors pattern
            collection_error_pattern = r"_\s*ERROR\s+collecting\s+(.+?)\s+_"
            collection_matches = re.finditer(collection_error_pattern, errors_section)

            for error_match in collection_matches:
                test_file_path = error_match.group(1).strip()

                # Extract the content after this error header until the next error or end
                start_pos = error_match.end()
                next_error_match = re.search(
                    r"_\s*ERROR\s+(?:collecting|at\s+(?:setup|teardown))",
                    errors_section[start_pos:],
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

            # Setup/Teardown errors pattern
            setup_error_pattern = r"_\s*ERROR\s+at\s+(setup|teardown)\s+of\s+(.+?)\s+_"
            setup_matches = re.finditer(setup_error_pattern, errors_section)

            for error_match in setup_matches:
                error_phase = error_match.group(1).strip()  # "setup" or "teardown"
                test_name = error_match.group(2).strip()

                # Extract the content after this error header until the next error or end
                start_pos = error_match.end()
                next_error_match = re.search(
                    r"_\s*ERROR\s+(?:collecting|at\s+(?:setup|teardown))",
                    errors_section[start_pos:],
                )

                if next_error_match:
                    end_pos = start_pos + next_error_match.start()
                    error_content = errors_section[start_pos:end_pos]
                else:
                    error_content = errors_section[start_pos:]

                # Parse setup/teardown error as a failure
                setup_failure = cls._parse_setup_teardown_error(
                    test_name, error_content, error_phase
                )
                if setup_failure:
                    failures.append(setup_failure)

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
        # 4. Django specific exceptions with full module paths
        exception_patterns = [
            r"(?:E\s+)?(django\.core\.exceptions\.\w+): (.+?)(?:\n|$)",  # Django exceptions with full path
            r"(?:E\s+)?(django\.db\.utils\.\w+): (.+?)(?:\n|$)",  # Django database exceptions
            r"(?:E\s+)?(\w+(?:\.\w+)*(?:Exception|Error)): (.+?)(?:\n|$)",  # Standard Error/Exception types
            r"(?:E\s+)?(ValidationError): (.+?)(?:\n|$)",  # Django ValidationError (short form)
            r"(?:E\s+)?(IntegrityError): (.+?)(?:\n|$)",  # Database IntegrityError (short form)
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

        # Extract line number from traceback or error content
        line_number = None
        if traceback:
            # Try to get line number from the first traceback entry in the test file
            for tb_entry in traceback:
                if tb_entry.file_path and test_file and tb_entry.file_path == test_file:
                    line_number = tb_entry.line_number
                    break

            # If no exact match, use the first traceback entry's line number
            if line_number is None and traceback:
                line_number = traceback[0].line_number

        # If still no line number, try extracting from exception message or content
        if line_number is None:
            _, extracted_line = cls._extract_source_file_and_line(
                exception_message, content, exception_type
            )
            if extracted_line:
                line_number = extracted_line

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
            line_number=line_number,
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
            r"(django\.core\.exceptions\.\w+): (.+?)(?:\n|$)",  # Django exceptions with full path
            r"(django\.db\.utils\.\w+): (.+?)(?:\n|$)",  # Django database exceptions
            r"(ValidationError): (.+?)(?:\n|$)",  # Django ValidationError (short form)
            r"(IntegrityError): (.+?)(?:\n|$)",  # Database IntegrityError (short form)
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

        # Extract line number from traceback or error location
        line_number = None
        if actual_error_line is not None:
            line_number = actual_error_line
        elif traceback and traceback[0].line_number:
            line_number = traceback[0].line_number

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
            line_number=line_number,
        )

    @classmethod
    def _parse_setup_teardown_error(
        cls, test_name: str, content: str, error_phase: str
    ) -> PytestFailureDetail | None:
        """Parse setup or teardown errors from the ERRORS section"""
        if not content.strip():
            return None

        # Extract exception information
        exception_match = re.search(
            r"([A-Za-z][A-Za-z0-9_]*(?:Error|Exception)):\s*(.+?)(?=\n|$)",
            content,
        )

        if exception_match:
            exception_type = exception_match.group(1).strip()
            exception_message = exception_match.group(2).strip()
        else:
            exception_type = f"{error_phase.title()} Error"
            # Try to extract a meaningful error from Django ValidationError format
            django_error_match = re.search(
                r"ValidationError:\s*\{'__all__':\s*\['(.+?)'\]\}",
                content,
                re.DOTALL,
            )
            if django_error_match:
                exception_message = django_error_match.group(1).strip()
                exception_type = "Django ValidationError"
            else:
                exception_message = "Error during test setup/teardown"

        # Extract the actual error file and line from traceback
        actual_error_file = None
        actual_error_line = None

        # Look for file references in the content that are NOT in system paths
        file_matches = re.findall(r'File\s+"([^"]+)",\s+line\s+(\d+)', content)

        for file_path, line_num in file_matches:
            # Skip system files and prefer user code
            if not any(
                sys_path in file_path
                for sys_path in [
                    "site-packages",
                    ".venv",
                    "/usr/",
                    "/root/.local",
                    "cpython-",
                ]
            ):
                actual_error_file = file_path
                try:
                    actual_error_line = int(line_num)
                    break  # Use first user code file found
                except ValueError:
                    pass

        # Parse test name components
        test_file = None
        test_function = test_name

        if "::" in test_name:
            parts = test_name.split("::")
            if len(parts) >= 2:
                test_file = parts[0] if parts[0].endswith(".py") else None
                test_function = parts[-1]
        elif "." in test_name and not test_name.startswith("test_"):
            # Class.method format like "DocumentOrganizerTest.test_method"
            parts = test_name.split(".")
            test_function = parts[-1] if len(parts) > 1 else test_name

        # Parse traceback
        traceback = cls._parse_traceback(content)

        # Override traceback to ensure correct line number for the actual error
        if actual_error_file and actual_error_line:
            # Create a new traceback entry for the actual error location
            actual_error_entry = PytestTraceback(
                file_path=actual_error_file,
                line_number=actual_error_line,
                function_name=error_phase,  # "setup" or "teardown"
                code_line=None,
                error_type=exception_type,
                error_message=exception_message,
            )

            # Put the actual error location first in the traceback
            traceback = [actual_error_entry] + [
                tb
                for tb in traceback
                if not (
                    tb.file_path == actual_error_file
                    and tb.line_number == actual_error_line
                )
            ]

        # Extract line number from error location or traceback
        line_number = None
        if actual_error_line is not None:
            line_number = actual_error_line
        elif traceback and traceback[0].line_number:
            line_number = traceback[0].line_number

        return PytestFailureDetail(
            test_name=f"{error_phase.title()} error: {test_name}",
            test_file=actual_error_file or test_file or "unknown",
            test_function=test_function,
            test_parameters=None,
            platform_info=None,
            python_version=None,
            exception_type=exception_type,
            exception_message=exception_message,
            traceback=traceback,
            full_error_text=content,
            line_number=line_number,
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

                # Extract line number from error message using Django patterns
                line_number = None
                source_file_path = None

                # Try to extract source file and line number from the error message
                if error_message:
                    source_file_path, line_number = cls._extract_source_file_and_line(
                        error_message, log_text, error_type
                    )

                short_summary.append(
                    PytestShortSummary(
                        test_name=test_spec,
                        test_file=source_file_path if source_file_path else test_file,
                        test_function=test_function,
                        test_parameters=test_parameters,
                        error_type=error_type,
                        error_message=error_message,
                        line_number=line_number,
                    )
                )

        return short_summary

    @classmethod
    def _extract_source_file_and_line(
        cls, error_message: str, full_log_text: str = "", error_type: str = ""
    ) -> tuple[str | None, int | None]:
        """
        Extract source file path and line number from Django/Python error messages.
        First tries to extract from error message directly, then searches full log for traceback summaries.

        Examples:
        - "domains/gwpy-document/document/apps/documents/views/actions.py:712: TypeError"
        - "/builds/product/gwpy-core/domains/gwpy-document/document/apps/documents/access_management/services.py:1101: AttributeError"
        """
        debug_print(
            f"[PYTEST] Extracting source file/line - error_message: '{error_message}', error_type: '{error_type}', log_text_length: {len(full_log_text)}"
        )

        # First, try to extract from the error message itself
        patterns = [
            # Standard Django/Python traceback format: path:line: ErrorType
            r"([^\s:]+(?:\.py|\.pyx?|\.pyi))[:：]\s*(\d+)[:：]\s*(?:\w+Error|\w+Exception|\w+)",
            # Alternative format with just path:line
            r"([^\s:]+(?:\.py|\.pyx?|\.pyi))[:：]\s*(\d+)(?:\s|$)",
            # Format with "line" keyword: "line 123 in file.py"
            r"line\s+(\d+)\s+in\s+([^\s]+(?:\.py|\.pyx?|\.pyi))",
            # Alternative "in file.py, line 123"
            r"in\s+([^\s,]+(?:\.py|\.pyx?|\.pyi)),?\s+line\s+(\d+)",
        ]

        for i, pattern in enumerate(patterns):
            verbose_debug_print(f"[PYTEST] Trying pattern {i}: {pattern}")
            match = re.search(pattern, error_message, re.MULTILINE)
            if match:
                debug_print(f"[PYTEST] Pattern {i} matched: {match.groups()}")
                groups = match.groups()
                if len(groups) == 2:
                    # For patterns that capture (file, line) or (line, file)
                    if pattern.startswith("line") or "in" in pattern:
                        # These patterns have (line, file) or special order
                        if pattern.startswith("line"):
                            line_num, file_path = groups
                        else:  # "in file.py, line 123"
                            file_path, line_num = groups
                    else:
                        # Standard (file, line) order
                        file_path, line_num = groups

                    try:
                        result_file, result_line = file_path.strip(), int(line_num)
                        debug_print(
                            f"[PYTEST] Direct pattern match found: file='{result_file}', line={result_line}"
                        )
                        return result_file, result_line
                    except ValueError:
                        debug_print(
                            f"[PYTEST] ValueError converting line number: {line_num}"
                        )
                        continue

        debug_print("[PYTEST] No direct pattern matches found in error message")

        # If not found in error message and we have full log text, search for traceback summary lines
        if full_log_text and error_type:
            debug_print(
                f"[PYTEST] Searching for traceback summaries with error_type: {error_type}"
            )
            # Search for traceback summary lines that match this error type
            # Format: "file.py:123: ErrorType"
            traceback_pattern = rf"([^\s:]+\.py):(\d+):\s*{re.escape(error_type)}"
            verbose_debug_print(f"[PYTEST] Traceback pattern: {traceback_pattern}")
            traceback_matches = re.findall(traceback_pattern, full_log_text)
            debug_print(
                f"[PYTEST] Found {len(traceback_matches)} traceback matches: {traceback_matches}"
            )

            if traceback_matches:
                # Return the first match (could be enhanced to find the best match)
                file_path, line_num = traceback_matches[0]
                try:
                    result_file, result_line = file_path.strip(), int(line_num)
                    debug_print(
                        f"[PYTEST] Traceback match found: file='{result_file}', line={result_line}"
                    )
                    return result_file, result_line
                except ValueError:
                    debug_print(f"[PYTEST] ValueError in traceback match: {line_num}")
                    pass

        # Fallback: if we have full log text but no error type, try to extract from error message
        elif full_log_text and error_message:
            debug_print(
                "[PYTEST] Fallback: trying to extract error type from error message"
            )
            # Look for error type from the error message
            error_type_match = re.match(
                r"(\w+(?:\.\w+)*(?:Exception|Error))", error_message.strip()
            )
            if error_type_match:
                extracted_error_type = error_type_match.group(1)
                debug_print(
                    f"[PYTEST] Extracted error type from message: {extracted_error_type}"
                )

                # Search for traceback summary lines that match this error type
                # Format: "file.py:123: ErrorType"
                traceback_pattern = (
                    rf"([^\s:]+\.py):(\d+):\s*{re.escape(extracted_error_type)}"
                )
                traceback_matches = re.findall(traceback_pattern, full_log_text)
                debug_print(
                    f"[PYTEST] Fallback found {len(traceback_matches)} traceback matches: {traceback_matches}"
                )

                if traceback_matches:
                    # Return the first match (could be enhanced to find the best match)
                    file_path, line_num = traceback_matches[0]
                    try:
                        result_file, result_line = file_path.strip(), int(line_num)
                        debug_print(
                            f"[PYTEST] Fallback match found: file='{result_file}', line={result_line}"
                        )
                        return result_file, result_line
                    except ValueError:
                        debug_print(
                            f"[PYTEST] ValueError in fallback match: {line_num}"
                        )
                        pass
            else:
                debug_print(
                    "[PYTEST] No error type found in error message for fallback"
                )

        debug_print("[PYTEST] No source file/line found, returning None, None")
        return None, None

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
