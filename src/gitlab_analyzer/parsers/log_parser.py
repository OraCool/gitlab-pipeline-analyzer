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
        # Generic GitLab CI failure messages (not meaningful for analysis)
        r"Job failed: command terminated with exit code",
        r": Job failed: exit code",
        r"ERROR: Job failed: exit code",
        r"Cleaning up project directory and file based variables",
        r"upload project directory and file based variables",
        # GitLab runner script errors (infrastructure, not user code)
        r"/scripts-.*get_sources: line .* export:.*not a valid identifier",
        r"/scripts-.*upload_artifacts_on_failure: line .* export:.*not a valid identifier",
        r"/scripts-.*: line .* export:.*not a valid identifier",
        r"line \d+: export:.*not a valid identifier",
        # GitLab runner internal scripts (broad exclusion)
        r"/scripts-\d+-\d+/.*:",
        r"bash: line \d+:",
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

    @classmethod
    def categorize_error(cls, message: str, context: str = "") -> dict[str, str]:
        """Categorize an error and provide detailed information"""
        message_lower = message.lower()

        # Code formatting errors
        if "would reformat" in message_lower or (
            "files would be reformatted" in message_lower
        ):
            if (
                "files would be reformatted" in message_lower
                or "file would be left unchanged" in message_lower
            ):
                # Extract number details from summary message
                numbers = re.findall(r"(\d+) files? would be reformatted", message)
                unchanged = re.findall(r"(\d+) files? would be left unchanged", message)

                reformatted_count = numbers[0] if numbers else "Multiple"
                unchanged_count = unchanged[0] if unchanged else "0"

                return {
                    "category": "Code Formatting Summary",
                    "severity": "medium",
                    "description": "Multiple files need code formatting with Black formatter",
                    "details": f"Black formatter detected {reformatted_count} files requiring reformatting, {unchanged_count} files already properly formatted",
                    "solution": "Run 'black .' to auto-format all files",
                    "impact": "Code style consistency issues",
                }
            else:
                # Extract filename from individual file message
                file_match = re.search(r"would reformat (.+)", message)
                file_path = file_match.group(1) if file_match else "unknown file"

                return {
                    "category": "Code Formatting",
                    "severity": "medium",
                    "description": "File needs formatting with Black formatter",
                    "details": f"Black formatter detected formatting issues in: {file_path}",
                    "solution": f"Run 'black {file_path}' to auto-format this file",
                    "impact": "Code style inconsistency",
                }

        # Python syntax errors
        elif "syntaxerror" in message_lower:
            # Extract specific syntax error details
            error_match = re.search(r"SyntaxError:\s*(.+)", message, re.IGNORECASE)
            file_match = re.search(r'File "([^"]+)"', message) or re.search(
                r"\(([^,]+),", message
            )  # Handle (filename, line) format
            line_match = re.search(r"line (\d+)", message)

            error_detail = error_match.group(1) if error_match else "syntax error"
            file_path = file_match.group(1) if file_match else "unknown file"
            line_num = line_match.group(1) if line_match else "unknown line"

            return {
                "category": "Python Syntax Error",
                "severity": "high",
                "description": "Invalid Python syntax that prevents code execution",
                "details": f"Syntax error in {file_path} at line {line_num}: {error_detail}",
                "solution": f"Fix the syntax error in {file_path} at line {line_num}",
                "impact": "Code cannot be executed or imported",
            }

        # Import errors
        elif "importerror" in message_lower or "modulenotfounderror" in message_lower:
            # Extract module name and import details
            module_match = (
                re.search(r"No module named '([^']+)'", message)
                or re.search(r"cannot import name '([^']+)'", message)
                or re.search(r"ImportError:\s*(.+)", message, re.IGNORECASE)
                or re.search(r"ModuleNotFoundError:\s*(.+)", message, re.IGNORECASE)
            )

            module_detail = module_match.group(1) if module_match else "unknown module"

            return {
                "category": "Python Import Error",
                "severity": "high",
                "description": "Missing module or package dependency",
                "details": f"Failed to import: {module_detail}",
                "solution": f"Install the missing package: pip install {module_detail.split('.')[0]}",
                "impact": "Code cannot access required dependencies",
            }

        # Test failures
        elif (
            "failed" in message_lower
            and ("test" in message_lower or "assertion" in message_lower)
        ) or re.match(r".+\.py:\d+: in test_.+", message):
            # Extract test details with enhanced parsing for source line numbers

            # Check context for pytest line format first (most accurate)
            source_line_from_context = None
            if context:
                # Look for pytest format in context: test_user_model.py:15: AssertionError
                context_line_match = re.search(r"([^/\s]+\.py):(\d+):\s*(.*)", context)
                if context_line_match:
                    source_line_from_context = {
                        "file": context_line_match.group(1),
                        "line": int(context_line_match.group(2)),
                        "error": context_line_match.group(3),
                    }

            # First check for pytest format: test/test_failures.py:10: in test_intentional_failure
            source_line_match = re.match(
                r"([^/\s]+/)?([^/\s]+\.py):(\d+):\s+in\s+(\w+)", message
            )

            if source_line_match:
                source_file = source_line_match.group(2)  # Just the filename
                source_line = source_line_match.group(3)
                test_function = source_line_match.group(4)
                details = f"Test case '{test_function}' in '{source_file}' failed at line {source_line}"

                return {
                    "category": "Test Failure",
                    "severity": "high",
                    "description": "Unit test or integration test failed",
                    "details": details,
                    "solution": f"Review {source_file} at line {source_line} and fix the failing test or code",
                    "impact": "Code quality issues, potential bugs",
                    "source_file": source_file,
                    "source_line": int(source_line),
                    "test_function": test_function,
                }

            test_match = (
                re.search(r"FAILED (.+)", message)
                or re.search(r"AssertionError:\s*(.+)", message)
                or re.search(r"Test failed:\s*(.+)", message)
            )

            # Try to extract source file and line number from pytest format in test_match content
            if test_match:
                test_detail = test_match.group(1)
                source_line_match = re.search(
                    r"([^/\s]+\.py):(\d+):\s+in\s+(\w+)", test_detail
                )

                if source_line_match:
                    source_file = source_line_match.group(1)
                    source_line = source_line_match.group(2)
                    test_function = source_line_match.group(3)
                    details = f"Test case '{test_function}' in '{source_file}' failed at line {source_line}"

                    # Try to extract the specific error reason from the context
                    error_reason_match = re.search(
                        r"(AssertionError|Exception|.*Error):\s*(.+)", message
                    )
                    if error_reason_match:
                        error_type = error_reason_match.group(1)
                        error_msg = error_reason_match.group(2)
                        details += f" - {error_type}: {error_msg}"

                    return {
                        "category": "Test Failure",
                        "severity": "high",
                        "description": "Unit test or integration test failed",
                        "details": details,
                        "solution": f"Review {source_file} at line {source_line} and fix the failing test or code",
                        "impact": "Code quality issues, potential bugs",
                        "source_file": source_file,
                        "source_line": int(source_line),
                        "test_function": test_function,
                    }

                # More descriptive details
                if "::" in test_detail:
                    parts = test_detail.split("::")
                    test_file = parts[0] if parts else "unknown file"
                    test_function = (
                        parts[1].split(" ")[0] if len(parts) > 1 else "unknown test"
                    )

                    # Use context source line if available (most accurate)
                    if source_line_from_context:
                        details = f"Test case '{test_function}' in '{source_line_from_context['file']}' failed at line {source_line_from_context['line']}"
                        if " - " in test_detail:
                            failure_reason = test_detail.split(" - ", 1)[1]
                            details += f" - Reason: {failure_reason}"

                        return {
                            "category": "Test Failure",
                            "severity": "high",
                            "description": "Unit test or integration test failed",
                            "details": details,
                            "solution": f"Review {source_line_from_context['file']} at line {source_line_from_context['line']} and fix the failing test or code",
                            "impact": "Code quality issues, potential bugs",
                            "source_file": source_line_from_context["file"],
                            "source_line": source_line_from_context["line"],
                            "test_function": test_function,
                        }

                    # Fallback to standard processing
                    details = (
                        f"Test case '{test_function}' in '{test_file}' failed execution"
                    )
                    if " - " in test_detail:
                        failure_reason = test_detail.split(" - ", 1)[1]
                        details += f" - Reason: {failure_reason}"
                else:
                    details = f"Test execution failed: {test_detail}"
            else:
                details = (
                    "Test failure detected but specific details could not be extracted"
                )

            return {
                "category": "Test Failure",
                "severity": "high",
                "description": "Unit test or integration test failed",
                "details": details,
                "solution": "Review test output and fix the failing test or code",
                "impact": "Code quality issues, potential bugs",
            }

        # Build/compilation errors
        elif "compilation error" in message_lower or "build failed" in message_lower:
            # Extract build failure details

            error_match = (
                re.search(r"compilation error:\s*(.+)", message, re.IGNORECASE)
                or re.search(r"build failed:\s*(.+)", message, re.IGNORECASE)
                or re.search(r"fatal error:\s*(.+)", message, re.IGNORECASE)
            )

            error_detail = (
                error_match.group(1) if error_match else "build process failed"
            )

            return {
                "category": "Build Error",
                "severity": "high",
                "description": "Code compilation or build process failed",
                "details": f"Build failure: {error_detail}",
                "solution": "Check build logs for specific compilation issues",
                "impact": "Cannot create executable or deployable artifacts",
            }

        # Permission/access errors
        elif "permission denied" in message_lower or "no such file" in message_lower:
            # Extract file/path details

            file_match = (
                re.search(r"Permission denied:\s*(.+)", message, re.IGNORECASE)
                or re.search(
                    r"No such file or directory:\s*(.+)", message, re.IGNORECASE
                )
                or re.search(r"'([^']+)'", message)
            )

            file_detail = file_match.group(1) if file_match else "file system resource"

            return {
                "category": "File System Error",
                "severity": "medium",
                "description": "File access or permission issue",
                "details": f"Cannot access: {file_detail}",
                "solution": f"Check file permissions and paths for: {file_detail}",
                "impact": "Cannot access required files or directories",
            }

        # Linting errors
        elif "lint" in message_lower and "failed" in message_lower:
            # Extract linting tool and details

            tool_match = re.search(r"(\w+)\s+.*lint.*failed", message, re.IGNORECASE)
            error_match = re.search(
                r"Lint check failed:\s*(.+)", message, re.IGNORECASE
            )

            tool_name = tool_match.group(1) if tool_match else "linter"
            error_detail = (
                error_match.group(1) if error_match else "code quality issues found"
            )

            return {
                "category": "Code Quality Error",
                "severity": "medium",
                "description": "Code quality checks failed",
                "details": f"{tool_name} found: {error_detail}",
                "solution": f"Fix linting issues reported by {tool_name}",
                "impact": "Code quality and maintainability concerns",
            }

        # Generic errors
        elif "error:" in message_lower:
            # Extract error details after "ERROR:"

            error_match = re.search(r"ERROR:\s*(.+)", message, re.IGNORECASE)
            error_detail = error_match.group(1) if error_match else message.strip()

            # Provide more specific details based on error type
            if "no files to upload" in error_detail.lower():
                details = "GitLab CI attempted to upload artifacts but no matching files were found"
            elif "compilation" in error_detail.lower():
                details = f"Build compilation process failed: {error_detail}"
            elif "permission" in error_detail.lower():
                details = f"File system permission error encountered: {error_detail}"
            elif (
                "connection" in error_detail.lower()
                or "network" in error_detail.lower()
            ):
                details = f"Network or connection error occurred: {error_detail}"
            elif "timeout" in error_detail.lower():
                details = f"Operation timed out: {error_detail}"
            else:
                details = f"Job execution error: {error_detail}"

            return {
                "category": "General Error",
                "severity": "medium",
                "description": "An error occurred during job execution",
                "details": details,
                "solution": "Review the error message and relevant logs for specific resolution steps",
                "impact": "Job execution interrupted",
            }

        # Default fallback
        else:
            return {
                "category": "Unknown Error",
                "severity": "medium",
                "description": "Unrecognized error pattern",
                "details": f"Original message: {message}",
                "solution": "Review the full error message and context",
                "impact": "Potential job execution issue",
            }
