"""
Parser for extracting errors and warnings from CI/CD logs

Copyright (c) 2025 Siarhei Skuratovich
Licensed under the MIT License - see LICENSE file for details
"""

import re

from ..models import LogEntry


class LogParser:
    """Parser for extracting errors and warnings from CI/CD logs"""

    # Job verification error patterns - focus ONLY on actual job failures
    ERROR_PATTERNS = [
        # Shell script errors that affect job execution
        (r"(.*)not a valid identifier", "error"),
        (r"(.*)command not found", "error"),
        (r"(.*)No such file or directory", "error"),
        (r"(.*)Permission denied", "error"),
        # Linting tool failures
        (r"(.*)would reformat", "error"),  # black formatting issues
        (r"(.*)Lint check failed", "error"),
        (r"(.*)formatting.*issues", "error"),
        (r"(.*)files would be reformatted", "error"),
        # Test failures
        (r"(.*)FAILED (.+test.*)", "error"),  # Test failures
        (r"(.*)AssertionError: (.+)", "error"),
        (r"(.*)Test failed: (.+)", "error"),
        (r"(.*)E\s+(.+test.*)", "error"),  # pytest errors (only test-related)
        # Build/compilation failures
        (r"(.*)compilation error", "error"),
        (r"(.*)build failed", "error"),
        (r"(.*)fatal error: (.+)", "error"),
        # Python code errors in actual application code
        (r"(.*)Traceback \(most recent call last\):", "error"),
        (r"(.*)SyntaxError: (.+)", "error"),
        (r"(.*)ImportError: (.+)", "error"),
        (r"(.*)ModuleNotFoundError: (.+)", "error"),
        (r"(.*)NameError: (.+)", "error"),
        (r"(.*)TypeError: (.+)", "error"),
        (r"(.*)ValueError: (.+)", "error"),
        (r"(.*)KeyError: (.+)", "error"),
        (r"(.*)AttributeError: (.+)", "error"),
        # Specific linter errors (but exclude infrastructure)
        (r"(?!.*Running pip)(?!.*Event retrieved)(.*)ERROR: (.+)", "error"),
        # Security/vulnerability errors
        (r"(.*)vulnerability", "error"),
        (r"(.*)security issue", "error"),
        # Package/dependency errors that affect the job
        (r"(.*)could not find", "error"),
        (r"(.*)missing", "error"),
        # Job termination errors
        (r"(.*)Job failed: command terminated with exit code", "error"),
    ]

    WARNING_PATTERNS = [
        # Code quality warnings
        (r"(.*)DeprecationWarning: (.+)", "warning"),
        (r"(.*)UserWarning: (.+)", "warning"),
        (r"(.*)FutureWarning: (.+)", "warning"),
        (r"(.*)WARNING: (.+)", "warning"),  # Will be filtered by excludes
        (r"(.*)WARN: (.+)", "warning"),  # Will be filtered by excludes
        # Linter warnings
        (r"(.*)warning: (.+)", "warning"),
    ]

    # Comprehensive CI/CD infrastructure exclusions - exclude ALL runner/infrastructure messages
    EXCLUDE_PATTERNS = [
        # GitLab Runner infrastructure
        r"Running with gitlab-runner",
        r"on GCP EPAM Ocean",
        r"system ID:",
        r"shared k8s runner",
        r"please use cache",
        r"per job and.*per service",
        # Kubernetes/Docker infrastructure
        r"the \"kubernetes\" executor",
        r"Using Kubernetes",
        r"Using attach strategy",
        r"Pod activeDeadlineSeconds",
        r"Waiting for pod",
        r"Running on runner-",
        r"ContainersNotReady:",
        r"containers with unready status:",
        r"gitlab-managed-apps",
        r"via gitlab-runner",
        # Git operations (infrastructure, not code issues)
        r"Getting source from Git",
        r"source from Git repository",
        r"Fetching changes with git",
        r"Initialized empty Git repository",
        r"Skipping Git submodules",
        # Cache operations
        r"Checking cache for",
        r"Downloading cache from",
        r"Successfully extracted cache",
        r"storage\.googleapis\.com",
        # Job execution framework
        r"Executing \"step_script\"",
        r"\"step_script\" stage of the job script",
        r"Preparing the.*executor",
        r"Preparing environment",
        r"Cleaning up project directory",
        r"cleanup_file_variables",
        # Shell command echoes (not the actual errors)
        r"^\$ ",
        r"echo \".*\"",
        # Package installation (successful operations)
        r"Requirement already satisfied:",
        r"Collecting ",
        r"Installing collected packages:",
        r"Successfully installed",
        r"Downloading.*packages",
        r"Installing.*packages",
        # Docker/K8s warnings (infrastructure, not job-related)
        r"MountVolume\.SetUp failed",
        r"Unable to retrieve.*image pull secrets",
        r"timed out waiting for the condition",
        r"may not succeed",
        r"artifactory.*attempting to pull",
        r"Event retrieved from the cluster:",
        # Python installation/pip warnings (not code issues)
        r"Running pip as the 'root' user",
        r"broken permissions and conflicting behaviour",
        r"recommended to use a virtual environment",
        # GitLab CI section markers and formatting
        r"section_start:",
        r"section_end:",
        r"Oh no! 💥 💔 💥",
        r"Starting.*stage\.\.\.",
        r"validation stage",
        r"Installed.*tools",
        r"Running.*checks",
        # Success messages (not errors)
        r"Successfully",
        r"✅",
        r"🔍",
        # Specific to this test case - simulation messages
        r"SIMULATING.*FAILURE",
        r"Creating intentional.*issues",
        r"Running.*on intentionally bad code",
        r"as expected!",
        # Output formatting and informational
        r"1 file would be reformatted\.$",  # This is just output, not the error
        r"^[0-9]+ files? would be reformatted\.$",
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
        """Get surrounding context for a log entry, filtered of infrastructure noise"""
        start = max(0, current_line - context_size - 1)
        end = min(len(lines), current_line + context_size)
        context_lines = lines[start:end]

        # Filter out infrastructure noise from context
        filtered_lines = []
        for line in context_lines:
            line = line.strip()
            if not line:
                continue

            # Skip infrastructure messages in context
            if any(
                re.search(pattern, line, re.IGNORECASE)
                for pattern in cls.EXCLUDE_PATTERNS
            ):
                continue

            filtered_lines.append(line)

        return "\n".join(filtered_lines)
