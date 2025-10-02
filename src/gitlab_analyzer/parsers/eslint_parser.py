"""
ESLint-specific log parser for JavaScript/TypeScript linting analysis.

This parser handles ESLint output, linting warnings and errors, and provides
structured analysis for code quality issues.

Copyright (c) 2025 Siarhei Skuratovich
Licensed under the MIT License - see LICENSE file for details
"""

import re
from typing import Any

from .base_parser import BaseFrameworkDetector, BaseFrameworkParser, TestFramework


class ESLintDetector(BaseFrameworkDetector):
    """Detects ESLint-based linting jobs"""

    @property
    def framework(self) -> TestFramework:
        return TestFramework.ESLINT

    @property
    def priority(self) -> int:
        return 80  # High priority for linting jobs

    def detect(self, job_name: str, job_stage: str, trace_content: str) -> bool:
        """Detect ESLint linting jobs"""
        # Job name patterns
        eslint_job_patterns = [
            r"lint",
            r"eslint",
            r"code.*quality",
            r"style.*check",
            r"format.*check",
        ]

        if self._check_job_name_patterns(
            job_name, eslint_job_patterns
        ) and self._has_eslint_content(trace_content):
            return True

        # Strong ESLint trace content indicators
        eslint_trace_patterns = [
            r"eslint\s+[\"'].*[\"'].*--cache",
            r"yarn run.*eslint",
            r"npm run.*eslint",
            r"\d+:\d+\s+(warning|error)\s+.*@typescript-eslint",
            r"✖\s+\d+\s+problems?\s+\(\d+\s+errors?,\s+\d+\s+warnings?\)",
            r"potentially fixable with the `--fix` option",
        ]

        return self._check_trace_content_patterns(trace_content, eslint_trace_patterns)

    def _has_eslint_content(self, trace_content: str) -> bool:
        """Check for ESLint-specific content patterns"""
        eslint_indicators = [
            r"@typescript-eslint/",
            r"eslint.*--cache",
            r"\d+:\d+\s+(warning|error)\s+",
            r"✖.*problems",
            r"potentially fixable with.*--fix",
        ]

        # Need at least 2 indicators for strong ESLint detection
        matches = sum(
            1
            for pattern in eslint_indicators
            if re.search(pattern, trace_content, re.IGNORECASE)
        )
        return matches >= 2


class ESLintParser(BaseFrameworkParser):
    """ESLint-specific log parser for JavaScript/TypeScript linting"""

    @property
    def framework(self) -> TestFramework:
        return TestFramework.ESLINT

    def parse(self, trace_content: str, **kwargs) -> dict[str, Any]:
        """Parse ESLint output"""
        errors = []
        warnings = []
        current_file = "unknown"

        # Clean ANSI escape sequences first
        cleaned_content = self._clean_ansi_sequences(trace_content)
        lines = cleaned_content.split("\n")

        for i, line in enumerate(lines):
            original_line = line
            line_stripped = line.strip()

            # Check if this line is a file path (ESLint format: absolute path on its own line)
            if self._is_file_path(original_line):
                current_file = self._extract_file_path(original_line)
                continue

            # Check for ESLint warning/error pattern
            # ESLint format: "  line:col  severity  message  rule"
            eslint_match = re.search(
                r"^\s*(\d+):(\d+)\s+(warning|error)\s+(.+?)\s+(@?\S+)$",
                line_stripped,
            )

            if eslint_match:
                line_number = int(eslint_match.group(1))
                column = int(eslint_match.group(2))
                severity = eslint_match.group(3)
                message = eslint_match.group(4).strip()
                rule = eslint_match.group(5) if eslint_match.group(5) else "unknown"

                issue_data = {
                    "test_file": current_file,
                    "test_function": "linting",
                    "message": f"{message} ({rule})" if rule != "unknown" else message,
                    "line_number": i + 1,  # Line in trace
                    "source_line": line_number,  # Line in source file
                    "source_column": column,
                    "eslint_rule": rule,
                    "severity": severity,
                    "has_traceback": False,
                }

                if severity == "error":
                    issue_data["exception_type"] = "ESLint Error"
                    errors.append(issue_data)
                else:
                    issue_data["type"] = "eslint_warning"
                    warnings.append(issue_data)

        return self.validate_output(
            {
                "parser_type": "eslint",
                "framework": self.framework.value,
                "errors": errors,
                "error_count": len(errors),
                "warnings": warnings,
                "warning_count": len(warnings),
                "summary": self._extract_eslint_summary(trace_content),
            }
        )

    def _is_file_path(self, line: str) -> bool:
        """Check if line contains a file path"""
        # ESLint file path patterns - must be at start of line, no leading spaces
        line_stripped = line.strip()

        # ESLint prints file paths on their own line, starting from column 0
        # Must end with a supported file extension
        patterns = [
            r"^/.*\.(ts|tsx|js|jsx)$",  # Absolute paths like /builds/project/src/file.ts
            r"^\./.*\.(ts|tsx|js|jsx)$",  # Relative paths like ./src/file.ts
            r"^src/.*\.(ts|tsx|js|jsx)$",  # Source paths like src/file.ts
            r"^[a-zA-Z]:.*\.(ts|tsx|js|jsx)$",  # Windows paths like C:/path/file.ts
        ]

        # File path lines have no leading whitespace in ESLint output
        if line.startswith(" ") or line.startswith("\t"):
            return False

        return any(re.search(pattern, line_stripped) for pattern in patterns)

    def _clean_ansi_sequences(self, text: str) -> str:
        """Remove ANSI escape sequences from text"""
        # ANSI escape sequence pattern
        ansi_escape = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")
        return ansi_escape.sub("", text)

    def _extract_file_path(self, line: str) -> str:
        """Extract clean file path from ESLint output"""
        # Remove build directory prefixes for cleaner paths
        clean_path = re.sub(r"^/builds/[^/]+/[^/]+/", "", line)
        return clean_path.strip()

    def _extract_eslint_summary(self, trace_content: str) -> dict[str, Any]:
        """Extract ESLint summary statistics"""
        summary: dict[str, int | str | None] = {
            "total_problems": 0,
            "total_errors": 0,
            "total_warnings": 0,
            "fixable_problems": 0,
            "files_with_issues": 0,
        }

        # ESLint summary patterns
        summary_patterns = [
            # ✖ 191 problems (3 errors, 188 warnings)
            (
                r"✖\s+(\d+)\s+problems?\s+\((\d+)\s+errors?,\s+(\d+)\s+warnings?\)",
                "main_summary",
            ),
            # 2 errors and 0 warnings potentially fixable with the `--fix` option
            (
                r"(\d+)\s+errors?\s+and\s+(\d+)\s+warnings?\s+potentially fixable",
                "fixable_summary",
            ),
        ]

        for pattern, summary_type in summary_patterns:
            match = re.search(pattern, trace_content, re.IGNORECASE)
            if match and summary_type == "main_summary":
                summary["total_problems"] = int(match.group(1))
                summary["total_errors"] = int(match.group(2))
                summary["total_warnings"] = int(match.group(3))
            elif match and summary_type == "fixable_summary":
                summary["fixable_problems"] = int(match.group(1)) + int(match.group(2))

        # Count unique files with issues
        file_paths = set()
        lines = trace_content.split("\n")
        for line in lines:
            if self._is_file_path(line.strip()):
                file_paths.add(self._extract_file_path(line.strip()))

        summary["files_with_issues"] = len(file_paths)

        return summary

    def _extract_source_file_and_line(
        self, error_message: str, full_log_text: str = "", error_type: str = ""
    ) -> tuple[str | None, int | None]:
        """
        ESLint-specific implementation of source file and line number extraction.

        ESLint provides errors in format:
        "line:column  severity  message  rule"
        """
        # Extract from ESLint format message if it contains source info
        eslint_pattern = r"(\d+):(\d+)\s+(warning|error)\s+(.+)"
        match = re.search(eslint_pattern, error_message)
        if match:
            line_number = int(match.group(1))
            return None, line_number  # File path is tracked separately

        # Look for file context in full log around this error
        if full_log_text:
            lines = full_log_text.split("\n")
            error_line_idx = None

            # Find the error message in the log
            for i, line in enumerate(lines):
                if error_message in line:
                    error_line_idx = i
                    break

            if error_line_idx is not None:
                # Look backwards for the file path
                for i in range(error_line_idx - 1, max(0, error_line_idx - 10), -1):
                    if self._is_file_path(lines[i].strip()):
                        file_path = self._extract_file_path(lines[i].strip())
                        # Try to extract line number from the error message
                        match = re.search(r"(\d+):(\d+)", error_message)
                        if match:
                            return file_path, int(match.group(1))
                        return file_path, None

        return None, None
