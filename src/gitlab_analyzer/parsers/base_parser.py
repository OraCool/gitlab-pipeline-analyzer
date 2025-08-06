"""
Base parser utilities for log analysis

Copyright (c) 2025 Siarhei Skuratovich
Licensed under the MIT License - see LICENSE file for details
"""

import re


class BaseParser:
    """Base parser with common utilities for log analysis"""

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
