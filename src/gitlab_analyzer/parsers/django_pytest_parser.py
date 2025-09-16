"""
Django-aware pytest parser for extracting Django-specific errors from pytest logs

This parser extends the LogParser to better handle Django framework errors
that occur during test setup, execution, and teardown phases.

Copyright (c) 2025 Siarhei Skuratovich
Licensed under the MIT License - see LICENSE file for details
"""

import re
from typing import Any

from ..models import LogEntry
from .log_parser import LogParser


class DjangoAwarePytestParser(LogParser):
    """
    Django-aware pytest parser that extends PytestLogParser to handle Django-specific errors.

    Specifically designed to catch:
    - Django ValidationError exceptions during test setup
    - Django IntegrityError database constraint violations
    - Django model and form validation failures
    - Django framework errors in test context
    """

    # Django-specific error patterns for pytest context
    DJANGO_ERROR_PATTERNS = [
        # Django ValidationError patterns
        (r"django\.core\.exceptions\.ValidationError: (.+)", "error"),
        (r"ValidationError: (.+)", "error"),
        (r"E\s+django\.core\.exceptions\.ValidationError: (.+)", "error"),
        (r"E\s+ValidationError: (.+)", "error"),
        # Django IntegrityError patterns
        (r"django\.db\.utils\.IntegrityError: (.+)", "error"),
        (r"IntegrityError: (.+)", "error"),
        (r"E\s+django\.db\.utils\.IntegrityError: (.+)", "error"),
        (r"E\s+IntegrityError: (.+)", "error"),
        # Database constraint violations
        (r"UNIQUE constraint failed: (.+)", "error"),
        (r"duplicate key value violates unique constraint \"(.+)\"", "error"),
        (r"E\s+UNIQUE constraint failed: (.+)", "error"),
        (r"E\s+duplicate key value violates unique constraint \"(.+)\"", "error"),
        # Other Django framework errors
        (r"django\.[a-zA-Z_.]+\.([A-Za-z]+(?:Error|Exception)): (.+)", "error"),
        (r"E\s+django\.[a-zA-Z_.]+\.([A-Za-z]+(?:Error|Exception)): (.+)", "error"),
    ]

    @classmethod
    def extract_log_entries(cls, log_content: str) -> list[LogEntry]:
        """
        Extract log entries with Django-aware error detection.

        Args:
            log_content: Raw CI/CD log content

        Returns:
            List of LogEntry objects with enhanced Django error detection
        """
        # Start with base log parsing for general CI/CD errors
        entries = super().extract_log_entries(log_content)

        # Enhance with Django-specific error detection
        django_errors = cls._extract_django_errors(log_content)

        # Combine and deduplicate entries
        all_entries = entries + django_errors
        return cls._deduplicate_entries(all_entries)

    @classmethod
    def _extract_django_errors(cls, log_text: str) -> list[LogEntry]:
        """Extract Django-specific errors that might be missed by standard pytest parsing"""
        cleaned_log_text = cls.clean_ansi_sequences(log_text)
        entries: list[LogEntry] = []
        lines = cleaned_log_text.split("\n")

        for line_num, log_line in enumerate(lines, 1):
            log_line = log_line.strip()
            if not log_line:
                continue

            # Skip GitLab CI infrastructure messages
            if any(
                re.search(pattern, log_line, re.IGNORECASE)
                for pattern in cls.EXCLUDE_PATTERNS
            ):
                continue

            # Check for Django-specific errors
            for pattern, level in cls.DJANGO_ERROR_PATTERNS:
                match = re.search(pattern, log_line, re.IGNORECASE)
                if match:
                    # Extract actual Python file line number if available
                    actual_line_number = cls._extract_source_line_number(
                        lines, line_num, log_line
                    )

                    entry = LogEntry(
                        level=level,
                        message=log_line,
                        line_number=actual_line_number,
                        context=cls._get_django_context(lines, line_num),
                        error_type=cls._classify_django_error_type(log_line),
                    )
                    entries.append(entry)
                    break

        return entries

    @classmethod
    def _extract_source_line_number(
        cls, lines: list[str], current_line: int, log_line: str
    ) -> int:
        """Extract the actual source code line number from Django traceback"""
        # Look for Python file:line patterns in current line or context
        file_line_patterns = [
            r'^\s*File\s+"([^"]+)",\s+line\s+(\d+)',  # Python traceback format
            r"^\s*([^:\s]+):(\d+):\s*in\s+",  # pytest format
            r"^\s*([^:\s]+):(\d+):\s*",  # Generic file:line format
        ]

        # Check current line first
        for pattern in file_line_patterns:
            file_match = re.search(pattern, log_line)
            if file_match and len(file_match.groups()) >= 2:
                file_path = file_match.group(1)
                # Prefer user code over system files
                if not any(
                    sys_path in file_path
                    for sys_path in [
                        "/root/.local/share/uv/python/",
                        "site-packages",
                        "/usr/lib",
                    ]
                ):
                    try:
                        return int(file_match.group(2))
                    except (ValueError, IndexError):
                        pass

        # Check context around current line
        context_start = max(0, current_line - 5)
        context_end = min(len(lines), current_line + 5)

        for i in range(context_start, context_end):
            context_line = lines[i].strip()
            for pattern in file_line_patterns:
                file_match = re.search(pattern, context_line)
                if file_match and len(file_match.groups()) >= 2:
                    file_path = file_match.group(1)
                    # Prefer user code over system files
                    if not any(
                        sys_path in file_path
                        for sys_path in [
                            "/root/.local/share/uv/python/",
                            "site-packages",
                            "/usr/lib",
                        ]
                    ):
                        try:
                            return int(file_match.group(2))
                        except (ValueError, IndexError):
                            pass

        # Fallback to trace line number
        return current_line

    @classmethod
    def _get_django_context(
        cls, lines: list[str], current_line: int, context_size: int = 8
    ) -> str:
        """Get surrounding context for Django errors with enhanced traceback information"""
        start = max(0, current_line - context_size - 1)
        end = min(len(lines), current_line + context_size)
        context_lines = lines[start:end]

        # For Django errors, preserve more context to capture full tracebacks
        filtered_lines = []
        for line in context_lines:
            line = line.strip()
            if not line:
                continue

            # Keep Django-related lines and test setup context
            should_keep = True

            # Only exclude the most obvious infrastructure noise
            infrastructure_patterns = [
                r"Running with gitlab-runner",
                r"Preparing the.*executor",
                r"Using Kubernetes",
                r"section_start:",
                r"section_end:",
            ]

            for pattern in infrastructure_patterns:
                if re.search(pattern, line, re.IGNORECASE):
                    should_keep = False
                    break

            if should_keep:
                filtered_lines.append(line)

        return "\n".join(filtered_lines)

    @classmethod
    def _classify_django_error_type(cls, message: str) -> str:
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

    @classmethod
    def _deduplicate_entries(cls, entries: list[LogEntry]) -> list[LogEntry]:
        """Remove duplicate log entries based on message similarity"""
        seen_entries = {}
        deduplicated = []

        for entry in entries:
            # Create a fingerprint based on error type and core message
            core_message = entry.message
            # Normalize file paths and line numbers for comparison
            core_message = re.sub(r"'[^']*\.py'", "'file.py'", core_message)
            core_message = re.sub(r"line \d+", "line N", core_message)
            core_message = re.sub(r":\d+:", ":N:", core_message)

            fingerprint = f"{entry.error_type}|{core_message[:100]}"

            if fingerprint not in seen_entries:
                seen_entries[fingerprint] = entry
                deduplicated.append(entry)

        return deduplicated

    @classmethod
    def categorize_error(cls, message: str, context: str = "") -> dict[str, Any]:
        """Categorize Django errors with detailed information"""
        message_lower = message.lower()

        # Django ValidationError
        if "validationerror" in message_lower:
            return cls._categorize_django_validation_error(message, context)

        # Django IntegrityError
        elif "integrityerror" in message_lower:
            return cls._categorize_django_integrity_error(message, context)

        # Database constraint violations
        elif "constraint" in message_lower and (
            "failed" in message_lower or "violates" in message_lower
        ):
            return cls._categorize_database_constraint_error(message, context)

        # Other Django framework errors
        elif "django" in message_lower:
            return cls._categorize_django_framework_error(message, context)

        # Fallback to parent categorization
        else:
            return super().categorize_error(message, context)

    @classmethod
    def _categorize_django_validation_error(
        cls, message: str, context: str = ""
    ) -> dict[str, Any]:
        """Categorize Django ValidationError exceptions"""
        # Extract constraint/validation details
        constraint_match = re.search(r"constraint \"([^\"]+)\"", message) or re.search(
            r"unique.*constraint.*failed.*([a-zA-Z_][a-zA-Z0-9_]*)", message
        )
        field_match = re.search(r"field '([^']+)'", message) or re.search(
            r"Key \(([^)]+)\)", message
        )

        if constraint_match:
            constraint_name = constraint_match.group(1)
            details = f"Django model validation failed: unique constraint '{constraint_name}' violation during test setup"
            solution = f"Ensure test data doesn't violate unique constraint '{constraint_name}' or use transaction rollback"
        elif field_match:
            field_name = field_match.group(1)
            details = f"Django field validation failed for field '{field_name}' during test execution"
            solution = f"Check test data validity for field '{field_name}'"
        else:
            details = "Django model validation failed during test execution"
            solution = "Review Django model constraints and test data setup"

        return {
            "category": "Django ValidationError",
            "severity": "high",
            "description": "Django model or form validation failed in test context",
            "details": details,
            "solution": solution,
            "impact": "Test execution blocked by Django validation rules",
        }

    @classmethod
    def _categorize_django_integrity_error(
        cls, message: str, context: str = ""
    ) -> dict[str, Any]:
        """Categorize Django IntegrityError exceptions"""
        # Extract constraint details
        constraint_match = (
            re.search(r"unique constraint \"([^\"]+)\"", message)
            or re.search(r"constraint failed: (.+)", message)
            or re.search(r"duplicate key.*\"([^\"]+)\"", message)
        )

        if constraint_match:
            constraint_name = constraint_match.group(1)
            details = f"Database integrity constraint violation: '{constraint_name}' during test execution"
            solution = f"Fix test data conflicts for constraint '{constraint_name}' or use proper test isolation"
        else:
            details = "Database integrity constraint violation during test execution"
            solution = "Review database constraints and test data conflicts"

        return {
            "category": "Django IntegrityError",
            "severity": "high",
            "description": "Database constraint violation in Django test",
            "details": details,
            "solution": solution,
            "impact": "Test database operations blocked due to constraint violations",
        }

    @classmethod
    def _categorize_database_constraint_error(
        cls, message: str, context: str = ""
    ) -> dict[str, Any]:
        """Categorize database constraint violations"""
        constraint_match = re.search(r"constraint \"([^\"]+)\"", message) or re.search(
            r"constraint failed: (.+)", message
        )

        if constraint_match:
            constraint_name = constraint_match.group(1)
            details = f"Database constraint '{constraint_name}' violated during test execution"
            solution = f"Fix test data to satisfy constraint '{constraint_name}'"
        else:
            details = "Database constraint violation during test execution"
            solution = "Review database constraints and test data"

        return {
            "category": "Database Constraint Violation",
            "severity": "high",
            "description": "Database constraint violated in test context",
            "details": details,
            "solution": solution,
            "impact": "Test database operations failed due to constraint violations",
        }

    @classmethod
    def _categorize_django_framework_error(
        cls, message: str, context: str = ""
    ) -> dict[str, Any]:
        """Categorize other Django framework errors"""
        django_error_match = re.search(
            r"django\.[a-zA-Z_.]+\.([A-Za-z]+(?:Error|Exception))", message
        )

        if django_error_match:
            error_type = django_error_match.group(1)
            details = f"Django framework {error_type} occurred during test execution"
            solution = f"Review Django documentation for {error_type} and test context"
        else:
            details = "Django framework error occurred during test execution"
            solution = "Review Django error context and test setup"

        return {
            "category": "Django Framework Error",
            "severity": "high",
            "description": "Django framework error in test context",
            "details": details,
            "solution": solution,
            "impact": "Django test functionality affected",
        }
