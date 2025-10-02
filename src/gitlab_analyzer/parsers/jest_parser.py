"""
Jest-specific log parser for JavaScript/TypeScript test analysis.

This parser handles Jest test output, test failures, and JavaScript-specific errors.

Copyright (c) 2025 Siarhei Skuratovich
Licensed under the MIT License - see LICENSE file for details
"""

import re
from typing import Any

from .base_parser import BaseFrameworkDetector, BaseFrameworkParser, TestFramework


class JestDetector(BaseFrameworkDetector):
    """Detects Jest-based TypeScript/JavaScript jobs"""

    @property
    def framework(self) -> TestFramework:
        return TestFramework.JEST

    @property
    def priority(self) -> int:
        return 85  # High priority for JS/TS projects

    def detect(self, job_name: str, job_stage: str, trace_content: str) -> bool:
        """Detect Jest test jobs"""
        # Job name patterns
        jest_job_patterns = [
            r"jest",
            r"js.*test",
            r"ts.*test",
            r"javascript.*test",
            r"typescript.*test",
            r"test.*ci",  # Common pattern like "test:ci"
        ]

        if self._check_job_name_patterns(job_name, jest_job_patterns):
            return True

        # Trace content patterns - enhanced for better detection
        jest_trace_patterns = [
            r"Test Suites:.*passed",
            r"Tests:.*passed.*failed",
            r"PASS.*\.test\.(js|ts)",
            r"FAIL.*\.test\.(js|ts)",
            r"Jest CLI Options",
            r"Running tests with Jest",
            r"yarn run.*test.*ci",  # yarn test:ci pattern
            r"npm run.*test.*ci",  # npm test:ci pattern
            r"node scripts/test\.ci\.js",  # Custom test script pattern
            r"Jest encountered an unexpected token",
            r"Test suite failed to run",
            r"Summary of all failing tests",
            r"Test Suites:.*failed.*passed.*total",  # Jest summary line
            r"Tests:.*failed.*passed.*total",  # Jest test count line
            # REMOVED: r"Browserslist:.*caniuse-lite.*outdated" - this is generic npm warning, not Jest-specific
        ]

        return self._check_trace_content_patterns(trace_content, jest_trace_patterns)


class JestParser(BaseFrameworkParser):
    """Jest-specific log parser for JavaScript/TypeScript tests"""

    @property
    def framework(self) -> TestFramework:
        return TestFramework.JEST

    def parse(self, trace_content: str, **kwargs) -> dict[str, Any]:
        """Parse Jest test output"""
        errors = []
        warnings: list[dict[str, Any]] = []

        # Jest warning patterns
        jest_warning_patterns = [
            r"WARNING:\s+(.+)",
            r"DEPRECATED:\s+(.+)",
            r"Jest:\s+(.+deprecated.+)",
            r"Browserslist:\s+(.+)",  # Common Jest warning
            r"\(node:\d+\)\s+\[DEP\d+\]\s+DeprecationWarning:\s+(.+)",  # Node deprecation warnings
        ]

        lines = trace_content.split("\n")
        current_test_file = "unknown"

        # Parse different types of errors
        errors.extend(self._parse_jest_test_failures(lines, current_test_file))
        errors.extend(self._parse_syntax_errors(lines))
        errors.extend(self._parse_typescript_errors(lines))
        errors.extend(self._parse_module_errors(lines))
        errors.extend(self._parse_timeout_errors(lines))
        errors.extend(self._parse_assertion_errors(lines))
        errors.extend(self._parse_suite_failures(lines))

        # Parse warnings separately
        warnings = []
        for i, line in enumerate(lines):
            line_stripped = line.strip()

            # Check for warnings
            for pattern in jest_warning_patterns:
                if re.search(pattern, line_stripped):
                    warnings.append(
                        {
                            "message": line_stripped,
                            "line_number": i + 1,
                            "type": "jest_warning",
                        }
                    )

        return self.validate_output(
            {
                "parser_type": "jest",
                "framework": self.framework.value,
                "errors": errors,
                "error_count": len(errors),
                "warnings": warnings,
                "warning_count": len(warnings),
                "summary": self._extract_jest_summary(trace_content),
            }
        )

    def _parse_jest_test_failures(
        self, lines: list[str], current_test_file: str
    ) -> list[dict]:
        """Parse Jest test failures by focusing on individual test failure markers (●)"""
        errors = []
        parsed_failures = set()  # Track parsed failure signatures to avoid duplicates
        in_summary_section = False

        for i, line in enumerate(lines):
            line_stripped = line.strip()

            # Detect the "Summary of all failing tests" section to avoid duplicates
            if "Summary of all failing tests" in line_stripped:
                in_summary_section = True
                continue

            # Track current test file from FAIL/PASS lines
            file_match = re.search(
                r"(PASS|FAIL)\s+(.+\.(test|spec)\.(js|ts|jsx|tsx))", line_stripped
            )
            if file_match:
                current_test_file = file_match.group(2)
                continue

            # Look for individual test failure markers (● or ✗)
            test_failure_match = re.match(r"[●✗]\s+(.+)", line_stripped)
            if test_failure_match:
                test_name = test_failure_match.group(1)

                # Create a unique signature for this failure to detect duplicates
                failure_signature = f"{current_test_file}::{test_name}"

                # Skip if we've already parsed this exact failure (duplicates in summary section)
                if failure_signature in parsed_failures and in_summary_section:
                    continue

                # Extract error details from the following lines
                error_message, error_type, source_line = (
                    self._extract_test_failure_details(lines, i)
                )

                # Include file context in message for better compatibility
                message_with_context = (
                    f"{error_message} (in {current_test_file})"
                    if current_test_file != "unknown"
                    else error_message
                )

                error_entry = {
                    "test_file": current_test_file,
                    "test_function": test_name,
                    "exception_type": error_type,
                    "message": message_with_context,
                    "line_number": source_line if source_line else i + 1,
                    "has_traceback": True,
                }

                # Add error_context for assertion errors
                if (
                    "Jest Assertion Error" in error_type
                    or "expect" in error_message.lower()
                ):
                    error_context = self._extract_error_context(lines, i, error_type)
                    error_entry["error_context"] = error_context

                errors.append(error_entry)
                parsed_failures.add(failure_signature)

        return errors

    def _parse_syntax_errors(self, lines: list[str]) -> list[dict]:
        """Parse JavaScript/TypeScript syntax errors"""
        errors = []
        for i, line in enumerate(lines):
            line_stripped = line.strip()

            # Look for SyntaxError patterns
            if re.search(r"SyntaxError:\s+(.+)", line_stripped):
                error_match = re.search(r"SyntaxError:\s+(.+)", line_stripped)
                if error_match:
                    errors.append(
                        {
                            "exception_type": "JavaScript Syntax Error",
                            "message": line_stripped,
                            "line_number": i + 1,
                            "has_traceback": True,
                            "test_file": "unknown",
                            "test_function": "unknown",
                        }
                    )
        return errors

    def _parse_typescript_errors(self, lines: list[str]) -> list[dict]:
        """Parse TypeScript compiler errors"""
        errors = []
        for i, line in enumerate(lines):
            line_stripped = line.strip()

            # Look for TypeScript error patterns
            if re.search(r"TS\d+:\s+(.+)", line_stripped):
                errors.append(
                    {
                        "exception_type": "TypeScript Error",
                        "message": line_stripped,
                        "line_number": i + 1,
                        "has_traceback": True,
                        "test_file": "unknown",
                        "test_function": "unknown",
                    }
                )
        return errors

    def _parse_module_errors(self, lines: list[str]) -> list[dict]:
        """Parse module not found and import errors"""
        errors = []
        for i, line in enumerate(lines):
            line_stripped = line.strip()

            # Look for module not found patterns
            if re.search(
                r"Cannot find module\s+['\"](.+)['\"]|Module not found", line_stripped
            ):
                errors.append(
                    {
                        "exception_type": "Module Not Found Error",
                        "message": line_stripped,
                        "line_number": i + 1,
                        "has_traceback": True,
                        "test_file": "unknown",
                        "test_function": "unknown",
                    }
                )
        return errors

    def _parse_timeout_errors(self, lines: list[str]) -> list[dict]:
        """Parse test timeout errors"""
        errors = []
        for i, line in enumerate(lines):
            line_stripped = line.strip()

            # Look for timeout patterns
            if re.search(r"Test timeout.*exceeded|Timeout.*test", line_stripped):
                errors.append(
                    {
                        "exception_type": "Test Timeout Error",
                        "message": line_stripped,
                        "line_number": i + 1,
                        "has_traceback": False,
                        "test_file": "unknown",
                        "test_function": "unknown",
                    }
                )
        return errors

    def _parse_assertion_errors(self, lines: list[str]) -> list[dict]:
        """Parse Jest assertion errors (expect statements)"""
        errors = []
        for i, line in enumerate(lines):
            line_stripped = line.strip()

            # Look for Jest assertion patterns
            if re.search(
                r"Error:\s+expect\(received\)\.|expect\(received\)\.|Error:\s+Expected.*(?:but )?received|Error:\s+.*(?:expected|received)",
                line_stripped,
            ):
                # Extract error context for assertions
                error_context = self._extract_error_context(
                    lines, i, "Jest Assertion Error"
                )

                errors.append(
                    {
                        "exception_type": "Jest Assertion Error",
                        "message": line_stripped,
                        "line_number": i + 1,
                        "has_traceback": True,
                        "test_file": "unknown",
                        "test_function": "unknown",
                        "error_context": error_context,
                    }
                )
        return errors

    def _parse_suite_failures(self, lines: list[str]) -> list[dict]:
        """Parse test suite failures (configuration/setup errors)"""
        errors = []
        for i, line in enumerate(lines):
            line_stripped = line.strip()

            # Look for suite failure patterns
            if "Test suite failed to run" in line_stripped:
                errors.append(
                    {
                        "exception_type": "Jest Suite Failure",
                        "message": line_stripped,
                        "line_number": i + 1,
                        "has_traceback": False,
                        "test_file": "unknown",
                        "test_function": "unknown",
                    }
                )
        return errors

    def _extract_test_failure_details(
        self, lines: list[str], start_idx: int
    ) -> tuple[str, str, int | None]:
        """Extract error message, type, and source line number from test failure"""
        error_message = ""
        error_type = "Jest Test Failure"
        source_line = None

        # Look at the next several lines after the ● marker for error details
        for i in range(start_idx + 1, min(len(lines), start_idx + 15)):
            line = lines[i].strip()

            # Stop if we hit another test failure or end of this failure block
            if (
                line.startswith("●")
                or line.startswith("Test Suites:")
                or line.startswith("Tests:")
            ):
                break

            # Extract specific error types and messages
            if re.search(r"expect\(received\)\.(.+)", line):
                error_type = "Jest Assertion Error"
                if not error_message:
                    error_message = line
            elif re.search(r"ReferenceError:\s+(.+)", line):
                error_type = "JavaScript Reference Error"
                error_message = line
            elif re.search(r"TypeError:\s+(.+)", line):
                error_type = "JavaScript Type Error"
                error_message = line
            elif re.search(r"SyntaxError:\s+(.+)", line):
                error_type = "JavaScript Syntax Error"
                error_message = line

            # Extract source line number from stack trace
            line_match = re.search(r"at .+ \(.+:(\d+):\d+\)", line)
            if line_match and not source_line:
                source_line = int(line_match.group(1))

        # Use a default message if none found
        if not error_message:
            error_message = f"Test failure at line {start_idx + 1}"

        return error_message, error_type, source_line

    def _extract_test_file(self, line: str, current_file: str) -> str:
        """Extract test file from Jest output line"""
        file_match = re.search(r"(.+\.(test|spec)\.(js|ts|jsx|tsx))", line)
        if file_match:
            return file_match.group(1)
        return current_file

    def _extract_test_function(self, lines: list[str], current_line: int) -> str:
        """Extract test function name from context"""
        # Look for test descriptions in surrounding lines
        for i in range(max(0, current_line - 10), min(len(lines), current_line + 3)):
            line = lines[i].strip()

            # Jest test description patterns
            test_patterns = [
                r"✕\s+(.+)",  # Failed test marker
                r"●\s+(.+)",  # Test suite marker
                r"describe\s*\(\s*['\"](.+)['\"]\s*,",  # describe block
                r"it\s*\(\s*['\"](.+)['\"]\s*,",  # it block
                r"test\s*\(\s*['\"](.+)['\"]\s*,",  # test block
            ]

            for pattern in test_patterns:
                match = re.search(pattern, line)
                if match:
                    return match.group(1)

        return "unknown test"

    def _has_jest_traceback(self, lines: list[str], current_line: int) -> bool:
        """Check if Jest error has stack trace"""
        # Look for stack trace patterns after the error
        for i in range(current_line + 1, min(len(lines), current_line + 10)):
            line = lines[i].strip()
            if re.search(r"at\s+.+\(.+:\d+:\d+\)", line) or re.search(
                r"^\s+\d+\s+\|", line
            ):
                return True
        return False

    def _extract_jest_details(
        self, lines: list[str], current_line: int
    ) -> dict[str, Any]:
        """Extract Jest-specific test details"""
        details = {}

        # Look for test suite and test names
        for i in range(max(0, current_line - 15), min(len(lines), current_line + 5)):
            line = lines[i].strip()

            # Extract suite name
            suite_match = re.search(r"describe\s*\(\s*['\"](.+)['\"]\s*,", line)
            if suite_match:
                details["test_suite"] = suite_match.group(1)

            # Extract expected vs received
            if "Expected:" in line:
                details["expected"] = line.split("Expected:")[-1].strip()
            elif "Received:" in line:
                details["received"] = line.split("Received:")[-1].strip()

            # Extract line numbers from stack traces
            stack_match = re.search(r"at\s+.+\((.+):(\d+):(\d+)\)", line)
            if stack_match:
                details["source_file"] = stack_match.group(1)
                details["source_line"] = int(stack_match.group(2))
                details["source_column"] = int(stack_match.group(3))

        return details

    def _extract_jest_summary(self, trace_content: str) -> dict[str, Any]:
        """Extract Jest test run summary"""
        summary: dict[str, int | str | None] = {
            "total_tests": 0,
            "passed_tests": 0,
            "failed_tests": 0,
            "total_suites": 0,
            "passed_suites": 0,
            "failed_suites": 0,
            "time": None,
        }

        # Jest summary patterns
        summary_patterns = [
            (
                r"Tests:\s+(\d+)\s+failed,\s+(\d+)\s+passed,\s+(\d+)\s+total",
                "test_results",
            ),
            (
                r"Test Suites:\s+(\d+)\s+failed,\s+(\d+)\s+passed,\s+(\d+)\s+total",
                "suite_results",
            ),
            (r"Time:\s+([0-9.]+\s*s)", "execution_time"),
        ]

        for pattern, result_type in summary_patterns:
            match = re.search(pattern, trace_content)
            if match and result_type == "test_results":
                summary["failed_tests"] = int(match.group(1))
                summary["passed_tests"] = int(match.group(2))
                summary["total_tests"] = int(match.group(3))
            elif match and result_type == "suite_results":
                summary["failed_suites"] = int(match.group(1))
                summary["passed_suites"] = int(match.group(2))
                summary["total_suites"] = int(match.group(3))
            elif match and result_type == "execution_time":
                summary["time"] = match.group(1)

        return summary

    def _extract_error_context(
        self, lines: list[str], error_line: int, error_type: str
    ) -> dict[str, Any]:
        """Extract additional context for Jest errors"""
        context: dict[str, Any] = {"error_type": error_type}

        # Look for specific error patterns and extract relevant context
        if error_type == "Jest Assertion Error":
            # Look for Expected/Received lines and assertion details
            for i in range(error_line, min(len(lines), error_line + 10)):
                line = lines[i].strip()
                if "Expected length:" in line:
                    match = re.search(r"Expected length:\s*(\d+)", line)
                    if match:
                        context["expected_length"] = int(match.group(1))
                elif "Received length:" in line:
                    match = re.search(r"Received length:\s*(\d+)", line)
                    if match:
                        context["received_length"] = int(match.group(1))
                elif "Expected:" in line:
                    context["expected"] = line.split("Expected:")[-1].strip()
                elif "Received:" in line:
                    context["received"] = line.split("Received:")[-1].strip()
                elif "toHaveLength" in line:
                    context["assertion_type"] = "length"
                elif "toBe" in line:
                    context["assertion_type"] = "equality"

        elif error_type in [
            "JavaScript Syntax Error",
            "Jest Parse Error",
            "JavaScript Parse Error",
        ]:
            # Look for file and line information in syntax errors
            for i in range(error_line, min(len(lines), error_line + 15)):
                line = lines[i].strip()
                # Extract line number from error context
                line_match = re.search(r">\s*(\d+)\s+\|", line)
                if line_match:
                    context["syntax_error_line"] = int(line_match.group(1))
                    break
                # Extract file path from syntax error
                file_match = re.search(r"([^\s:]+\.(js|ts|jsx|tsx)):(\d+):(\d+)", line)
                if file_match:
                    context["error_file"] = file_match.group(1)
                    context["error_line"] = int(file_match.group(3))
                    context["error_column"] = int(file_match.group(4))

        elif error_type == "Jest Suite Failure":
            # Extract details about why the test suite failed
            context["failure_reason"] = "Configuration or setup error"
            # Look for specific failure reasons
            for i in range(error_line, min(len(lines), error_line + 5)):
                line = lines[i].strip()
                if "Jest encountered an unexpected token" in line:
                    context["failure_reason"] = "Unexpected token"
                elif "cannot parse" in line.lower():
                    context["failure_reason"] = "Parse error"

        elif error_type == "TypeScript Error":
            # Extract TypeScript error details
            for i in range(error_line, min(len(lines), error_line + 5)):
                line = lines[i].strip()
                file_match = re.search(r"at\s+([^\s:]+\.(ts|tsx)):(\d+):(\d+)", line)
                if file_match:
                    context["error_file"] = file_match.group(1)
                    context["error_line"] = int(file_match.group(3))
                    context["error_column"] = int(file_match.group(4))

        elif error_type == "Module Not Found Error":
            # Extract module name
            for i in range(error_line, min(len(lines), error_line + 5)):
                line = lines[i].strip()
                module_match = re.search(
                    r"Cannot find module\s+['\"](.*?)['\"]|Module not found:\s+(.+)",
                    line,
                )
                if module_match:
                    context["missing_module"] = module_match.group(
                        1
                    ) or module_match.group(2)

        elif error_type == "Test Timeout Error":
            # Extract timeout duration
            timeout_match = re.search(r"(\d+)ms", lines[error_line])
            if timeout_match:
                context["timeout_duration"] = int(timeout_match.group(1))

        return context

    def _extract_source_file_and_line(
        self, error_message: str, full_log_text: str = "", error_type: str = ""
    ) -> tuple[str | None, int | None]:
        """
        Jest-specific implementation of source file and line number extraction.

        Jest typically provides stack traces in the format:
        "at Object.<anonymous> (/path/to/file.js:42:5)"
        """
        # Jest stack trace patterns
        patterns = [
            # Standard Jest stack trace: "at Object.<anonymous> (/path/to/file.js:42:5)"
            r"at\s+.+\(([^:]+):(\d+):(\d+)\)",
            # Alternative format: "at /path/to/file.js:42:5"
            r"at\s+([^:]+):(\d+):(\d+)",
            # Simple file:line format that might appear in Jest output
            r"([^\s:]+\.(js|ts|jsx|tsx)):(\d+)(?::(\d+))?",
        ]

        # First try to extract from error message
        for pattern in patterns:
            match = re.search(pattern, error_message)
            if match:
                groups = match.groups()
                file_path = groups[0]
                line_number_str = groups[1] if len(groups) > 1 else None

                # Skip node_modules and system paths
                if not any(
                    skip in file_path for skip in ["node_modules", "/usr/", "internal/"]
                ):
                    try:
                        return file_path.strip(), (
                            int(line_number_str) if line_number_str else None
                        )
                    except (ValueError, TypeError):
                        continue

        # If not found in error message, search the full log text
        if full_log_text:
            for pattern in patterns:
                matches = re.findall(pattern, full_log_text)
                for match in matches:
                    file_path = match[0] if isinstance(match, tuple) else match
                    line_number_str = (
                        match[1]
                        if isinstance(match, tuple) and len(match) > 1
                        else None
                    )

                    # Skip system paths
                    if not any(
                        skip in file_path
                        for skip in ["node_modules", "/usr/", "internal/"]
                    ):
                        try:
                            return file_path.strip(), (
                                int(line_number_str) if line_number_str else None
                            )
                        except (ValueError, TypeError):
                            continue

        return None, None
