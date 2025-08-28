"""
Base parser utilities for log analysis

Copyright (c) 2025 Siarhei Skuratovich
Licensed under the MIT License - see LICENSE file for details
"""

import re


class BaseParser:
    """Base parser with common utilities for log analysis"""

    # Shared error type classification patterns
    ERROR_TYPE_PATTERNS = [
        # Test failures
        (r"FAILED.*test.*", "test_failure"),
        (r".*AssertionError.*", "test_failure"),
        (r".*Test failed.*", "test_failure"),
        (r".*assert.*", "test_failure"),
        # Python syntax/runtime errors
        (r"SyntaxError.*", "python_error"),
        (r"ImportError.*", "python_error"),
        (r"ModuleNotFoundError.*", "python_error"),
        (r"IndentationError.*", "python_error"),
        (r"NameError.*", "python_error"),
        (r"TypeError.*", "python_error"),
        (r"ValueError.*", "python_error"),
        (r"KeyError.*", "python_error"),
        (r"AttributeError.*", "python_error"),
        # Linting errors
        (r".*ruff.*", "linting_error"),
        (r".*\.py:\d+:\d+:.*[A-Z]\d+.*", "linting_error"),  # Ruff format
        (r".*would reformat.*", "linting_error"),
        (r".*formatting.*issues.*", "linting_error"),
        (r"No matches for ignored import.*", "import_linting_error"),
        (r".*import.*not allowed.*", "import_linting_error"),
        (r"Found \d+ error", "linting_error"),
        # Build system errors
        (r"make: \*\*\*.*Error.*", "build_error"),
        (r".*build failed.*", "build_error"),
        (r".*compilation error.*", "build_error"),
        # Docker/infrastructure errors
        (r"Error response from daemon.*", "infrastructure_error"),
        (r"Failed to pull image.*", "infrastructure_error"),
        (r".*Permission denied.*", "infrastructure_error"),
        # Policy/security warnings
        (r"WARNING.*policy.*", "policy_warning"),
        (r".*security issue.*", "security_error"),
        (r".*vulnerability.*", "security_error"),
        # Generic patterns (lower priority)
        (r"ERROR:.*", "generic_error"),
        (r"CRITICAL:.*", "critical_error"),
    ]

    @classmethod
    def classify_error_type(cls, message: str) -> str:
        """Classify error type based on message pattern"""
        for pattern, error_type in cls.ERROR_TYPE_PATTERNS:
            if re.search(pattern, message, re.IGNORECASE):
                return error_type
        return "unknown"

    @classmethod
    def clean_ansi_sequences(cls, text: str) -> str:
        """Clean ANSI escape sequences and control characters from log text"""
        # Enhanced ANSI sequence removal
        ansi_escape = re.compile(
            r"""
            \x1B    # ESC character
            (?:     # Non-capturing group for different ANSI sequence types
                \[  # CSI (Control Sequence Introducer) sequences
                [0-9;]*  # Parameters (numbers and semicolons)
                [A-Za-z]  # Final character
            |       # OR
                \[  # CSI sequences with additional complexity
                [0-9;?]*  # Parameters with optional question mark
                [A-Za-z@-~]  # Final character range
            |       # OR
                [@-Z\\-_]  # 7-bit C1 Fe sequences
            )
        """,
            re.VERBOSE,
        )

        # Apply ANSI cleaning
        clean = ansi_escape.sub("", text)

        # Remove control characters but preserve meaningful whitespace
        clean = re.sub(r"\r", "", clean)  # Remove carriage returns
        clean = re.sub(r"\x08", "", clean)  # Remove backspace
        clean = re.sub(r"\x0c", "", clean)  # Remove form feed

        # Remove GitLab CI section markers
        clean = re.sub(r"section_start:\d+:\w+\r?", "", clean)
        clean = re.sub(r"section_end:\d+:\w+\r?", "", clean)

        # Clean up pytest error prefixes that remain after ANSI removal
        # These are the "E   " prefixes that pytest uses for error highlighting
        clean = re.sub(r"^E\s+", "", clean, flags=re.MULTILINE)

        # Clean up other pytest formatting artifacts
        clean = re.sub(
            r"^\s*\+\s*", "", clean, flags=re.MULTILINE
        )  # pytest diff additions
        clean = re.sub(
            r"^\s*-\s*", "", clean, flags=re.MULTILINE
        )  # pytest diff removals

        # Remove excessive whitespace while preserving structure
        clean = re.sub(r"\n\s*\n\s*\n", "\n\n", clean)  # Reduce multiple blank lines

        return clean
