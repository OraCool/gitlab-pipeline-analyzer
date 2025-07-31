"""
Parser for extracting errors and warnings from CI/CD logs
"""

import re
from typing import List
from ..models import LogEntry


class LogParser:
    """Parser for extracting errors and warnings from CI/CD logs"""

    # Common error patterns for Python projects
    ERROR_PATTERNS = [
        # Python errors
        (r"(.*)Error: (.+)", "error"),
        (r"(.*)Exception: (.+)", "error"),
        (r"(.*)Traceback \(most recent call last\):", "error"),
        (r"(.*)FAILED (.+)", "error"),
        (r"(.*)FAIL: (.+)", "error"),
        (r"(.*)E\s+(.+)", "error"),  # pytest errors
        # Build/compilation errors
        (r"(.*)fatal error: (.+)", "error"),
        (r"(.*)error: (.+)", "error"),
        (r"(.*)ERROR: (.+)", "error"),
        # Linting errors
        (r"(.*)pylint: (.+)", "error"),
        (r"(.*)flake8: (.+)", "error"),
        (r"(.*)mypy: (.+)", "error"),
        # Test framework errors
        (r"(.*)AssertionError: (.+)", "error"),
        (r"(.*)Test failed: (.+)", "error"),
        # General failure patterns
        (r"(.*)Command failed with exit code (\d+)", "error"),
        (r"(.*)Process exited with code (\d+)", "error"),
    ]

    WARNING_PATTERNS = [
        (r"(.*)Warning: (.+)", "warning"),
        (r"(.*)WARNING: (.+)", "warning"),
        (r"(.*)WARN: (.+)", "warning"),
        (r"(.*)DeprecationWarning: (.+)", "warning"),
        (r"(.*)UserWarning: (.+)", "warning"),
        (r"(.*)FutureWarning: (.+)", "warning"),
    ]

    @classmethod
    def extract_log_entries(cls, log_text: str) -> List[LogEntry]:
        """Extract error and warning entries from log text"""
        entries = []
        lines = log_text.split("\n")

        for line_num, log_line in enumerate(lines, 1):
            log_line = log_line.strip()
            if not log_line:
                continue

            # Check for errors
            for pattern, level in cls.ERROR_PATTERNS:
                match = re.search(pattern, log_line, re.IGNORECASE)
                if match:
                    entry = LogEntry(
                        level=level,
                        message=log_line,
                        line_number=line_num,
                        context=cls._get_context(lines, line_num),
                    )
                    entries.append(entry)
                    break

            # Check for warnings
            for pattern, level in cls.WARNING_PATTERNS:
                match = re.search(pattern, log_line, re.IGNORECASE)
                if match:
                    entry = LogEntry(
                        level=level,
                        message=log_line,
                        line_number=line_num,
                        context=cls._get_context(lines, line_num),
                    )
                    entries.append(entry)
                    break

        return entries

    @classmethod
    def _get_context(
        cls, lines: List[str], current_line: int, context_size: int = 2
    ) -> str:
        """Get surrounding context for a log entry"""
        start = max(0, current_line - context_size - 1)
        end = min(len(lines), current_line + context_size)
        context_lines = lines[start:end]
        return "\n".join(context_lines)
