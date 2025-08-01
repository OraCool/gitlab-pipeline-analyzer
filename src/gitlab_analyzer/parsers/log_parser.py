"""
Parser for extracting errors and warnings from CI/CD logs

Copyright (c) 2025 Siarhei Skuratovich
Licensed under the MIT License - see LICENSE file for details
"""

import re

from ..models import LogEntry


class LogParser:
    """Parser for extracting errors and warnings from CI/CD logs"""

    # Common error patterns for Python projects
    ERROR_PATTERNS = [
        # Critical shell script errors (common in CI/CD)
        (r"(.*)not a valid identifier", "error"),
        (r"(.*)command not found", "error"),
        (r"(.*)No such file or directory", "error"),
        (r"(.*)Permission denied", "error"),
        (r"(.*)Job failed: command terminated with exit code", "error"),
        # Specific error messages
        (r"(.*)ERROR: (.+)", "error"),
        (r"(.*)FATAL: (.+)", "error"),
        (r"(.*)FAILED (.+)", "error"),
        (r"(.*)FAIL: (.+)", "error"),
        # Python errors
        (r"(.*)Error: (.+)", "error"),
        (r"(.*)Exception: (.+)", "error"),
        (r"(.*)Traceback \(most recent call last\):", "error"),
        (r"(.*)E\s+(.+)", "error"),  # pytest errors
        # Build/compilation errors
        (r"(.*)fatal error: (.+)", "error"),
        # Linting specific errors
        (r"(.*)pylint: (.+)", "error"),
        (r"(.*)flake8: (.+)", "error"),
        (r"(.*)mypy: (.+)", "error"),
        (r"(.*)would reformat", "error"),  # black formatting error
        (r"(.*)Lint check failed", "error"),
        # Test framework errors
        (r"(.*)AssertionError: (.+)", "error"),
        (r"(.*)Test failed: (.+)", "error"),
        # General failure patterns (be more specific)
        (r"(.*)Command failed with exit code (\d+)", "error"),
        (r"(.*)Process exited with code (\d+)", "error"),
    ]

    WARNING_PATTERNS = [
        # Kubernetes/Docker warnings
        (r"(.*)MountVolume\.SetUp failed", "warning"),
        (r"(.*)Unable to retrieve.*image pull secrets", "warning"),
        (r"(.*)timed out waiting for the condition", "warning"),
        (r"(.*)may not succeed", "warning"),
        # Python warnings
        (r"(.*)WARNING: (.+)", "warning"),
        (r"(.*)WARN: (.+)", "warning"),
        (r"(.*)DeprecationWarning: (.+)", "warning"),
        (r"(.*)UserWarning: (.+)", "warning"),
        (r"(.*)FutureWarning: (.+)", "warning"),
        # Pip warnings
        (r"(.*)Running pip as the 'root' user", "warning"),
    ]

    # Patterns to exclude (GitLab CI infrastructure messages)
    EXCLUDE_PATTERNS = [
        r"Running with gitlab-runner",
        r"on GCP EPAM Ocean",
        r"system ID:",
        r"the \"kubernetes\" executor",
        r"Using Kubernetes",
        r"Using attach strategy",
        r"Pod activeDeadlineSeconds",
        r"Waiting for pod",
        r"Running on runner-",
        r"Getting source from Git",
        r"source from Git repository",
        r"Fetching changes with git",
        r"Initialized empty Git repository",
        r"Skipping Git submodules",
        r"Checking cache for",
        r"Downloading cache from",
        r"Successfully extracted cache",
        r"Executing \"step_script\"",
        r"\"step_script\" stage of the job script",
        r"Starting .* validation stage",
        r"Installed .* tools",
        r"Running .* checks",
        r"Cleaning up project directory",
        r"ContainersNotReady:",
        r"^\$ ",  # Shell command echoes
        r"Requirement already satisfied:",
        r"Collecting ",
        r"Installing collected packages:",
        r"Successfully installed",
        r"Oh no! 💥 💔 💥",
        r"1 file would be reformatted\.",  # This is just output, not the error itself
    ]

    @classmethod
    def extract_log_entries(cls, log_text: str) -> list[LogEntry]:
        """Extract error and warning entries from log text"""
        # First, clean the log text from ANSI escape sequences
        cleaned_log_text = cls._clean_ansi_sequences(log_text)

        entries = []
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
    def _clean_ansi_sequences(cls, text: str) -> str:
        """Clean ANSI escape sequences and control characters from log text"""
        # Comprehensive 7-bit C1 ANSI sequences removal
        ansi_escape = re.compile(
            r"""
            \x1B  # ESC
            (?:   # 7-bit C1 Fe (except CSI)
                [@-Z\\-_]
            |     # or [ for CSI, followed by a control sequence
                \[
                [0-?]*  # Parameter bytes
                [ -/]*  # Intermediate bytes
                [@-~]   # Final byte
            )
        """,
            re.VERBOSE,
        )

        clean = ansi_escape.sub("", text)

        # Remove control characters like \r but preserve meaningful line breaks
        clean = re.sub(r"\r", "", clean)  # Remove carriage returns

        # Remove GitLab CI section markers
        clean = re.sub(r"section_start:\d+:\w+\r?", "", clean)
        clean = re.sub(r"section_end:\d+:\w+\r?", "", clean)

        return clean

    @classmethod
    def _get_context(
        cls, lines: list[str], current_line: int, context_size: int = 2
    ) -> str:
        """Get surrounding context for a log entry"""
        start = max(0, current_line - context_size - 1)
        end = min(len(lines), current_line + context_size)
        context_lines = lines[start:end]
        return "\n".join(context_lines)
