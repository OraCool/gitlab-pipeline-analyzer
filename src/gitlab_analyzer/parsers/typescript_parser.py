"""
TypeScript compiler (tsc) parser for GitLab CI/CD pipeline analysis.

This parser handles TypeScript compilation errors and warnings from `tsc` output,
extracting file paths, line numbers, column numbers, error codes, and messages.

Copyright (c) 2025 Siarhei Skuratovich
Licensed under the MIT License - see LICENSE file for details
"""

import re
from typing import Any

from .base_parser import BaseFrameworkDetector, BaseFrameworkParser, TestFramework


class TypeScriptDetector(BaseFrameworkDetector):
    """Detector for TypeScript compilation jobs"""

    @property
    def framework(self) -> TestFramework:
        return TestFramework.TYPESCRIPT

    @property
    def priority(self) -> int:
        return 82  # Higher than ESLint (80), lower than Jest (85)

    def detect(self, job_name: str, job_stage: str, trace_content: str) -> bool:
        """
        Detect TypeScript compilation jobs.

        Args:
            job_name: Name of the CI/CD job
            job_stage: Stage name (e.g., 'test', 'build')
            trace_content: Raw log content from the job

        Returns:
            True if this appears to be a TypeScript compilation job
        """
        # Look for TypeScript compiler command
        if "tsc " in trace_content or "tsc\n" in trace_content:
            return True

        # Look for TypeScript error patterns
        typescript_error_patterns = [
            r"error TS\d+:",  # TypeScript error codes like TS2554, TS2339
            r"\.ts\(\d+,\d+\): error",  # TypeScript error format
            r"\.tsx\(\d+,\d+\): error",  # TypeScript React error format
        ]

        for pattern in typescript_error_patterns:
            if re.search(pattern, trace_content):
                return True

        return False


class TypeScriptParser(BaseFrameworkParser):
    """Parser for TypeScript compilation output"""

    def __init__(self):
        super().__init__()
        # TypeScript error format: filename(line,col): error TSxxxx: message
        self.error_pattern = re.compile(
            r"^(.+?)\((\d+),(\d+)\):\s+(error|warning)\s+(TS\d+):\s*(.+?)\.?\s*$",
            re.MULTILINE,
        )

    @property
    def framework(self) -> TestFramework:
        """Return the framework this parser handles"""
        return TestFramework.TYPESCRIPT

    def parse(self, trace_content: str, **kwargs) -> dict[str, Any]:
        """
        Parse TypeScript compilation output for errors and warnings.

        Args:
            trace_content: Raw trace content from TypeScript compiler
            **kwargs: Additional parsing options

        Returns:
            Standardized parsing results with errors, warnings, and metadata
        """
        errors = []
        warnings = []

        # Find all TypeScript errors and warnings
        matches = self.error_pattern.findall(trace_content)

        for match in matches:
            file_path, line_str, col_str, level, error_code, message = match

            # Clean up file path
            cleaned_path = self._clean_file_path(file_path)

            error_entry = {
                "message": f"{error_code}: {message.strip()}",
                "level": level.lower(),
                "line_number": int(line_str),
                "column_number": int(col_str),
                "test_file": cleaned_path,  # Use test_file instead of file_path
                "error_code": error_code,
                "exception_type": f"TypeScript {level.title()}",
                "test_function": "compilation",
                "detail": {
                    "typescript_code": error_code,
                    "column": int(col_str),
                    "raw_message": message.strip(),
                },
            }

            if level == "error":
                errors.append(error_entry)
            else:
                warnings.append(error_entry)

        # Generate summary
        summary = {
            "total_problems": len(errors) + len(warnings),
            "errors": len(errors),
            "warnings": len(warnings),
            "files_with_issues": len(
                {entry["test_file"] for entry in errors + warnings}
            ),
            "typescript_version": self._extract_typescript_version(trace_content),
            "compilation_command": self._extract_compilation_command(trace_content),
        }

        return {
            "parser_type": "typescript",
            "framework": TestFramework.TYPESCRIPT.value,
            "errors": errors,
            "error_count": len(errors),
            "warnings": warnings,
            "warning_count": len(warnings),
            "summary": summary,
        }

    def _clean_file_path(self, file_path: str) -> str:
        """
        Clean and normalize file paths from TypeScript output.

        Args:
            file_path: Raw file path from TypeScript error

        Returns:
            Cleaned file path
        """
        # Remove common build prefixes
        if file_path.startswith("/builds/"):
            parts = file_path.split("/builds/", 1)
            if len(parts) > 1:
                # Find the first meaningful path segment after /builds/
                remaining = parts[1]
                segments = remaining.split("/")
                if len(segments) >= 3:  # Skip project/repo segments
                    return "/".join(segments[2:])
                return remaining

        # Handle relative paths
        if file_path.startswith("./"):
            return file_path[2:]

        return file_path.strip()

    def _extract_typescript_version(self, trace_content: str) -> str | None:
        """Extract TypeScript version from trace if available"""
        # Look for TypeScript version patterns
        version_patterns = [
            r"typescript@([0-9.]+)",
            r"tsc\s+--version\s*\n.*?([0-9.]+)",
        ]

        for pattern in version_patterns:
            match = re.search(pattern, trace_content, re.IGNORECASE)
            if match:
                return match.group(1)

        return None

    def _extract_compilation_command(self, trace_content: str) -> str | None:
        """Extract the TypeScript compilation command used"""
        # Look for tsc command with options
        patterns = [
            r"\$ (tsc[^\n]+)",
            r"yarn run.*?\n\$ (tsc[^\n]+)",
            r"npm run.*?\n.*?(tsc[^\n]+)",
        ]

        for pattern in patterns:
            match = re.search(pattern, trace_content)
            if match:
                return match.group(1).strip()

        return None

    def _extract_source_file_and_line(
        self, error_message: str, full_log_text: str = "", error_type: str = ""
    ) -> tuple[str | None, int | None]:
        """
        Extract source file path and line number from TypeScript error messages.

        TypeScript errors have format: filename(line,col): error TSxxxx: message

        Args:
            error_message: The error message text from TypeScript compiler
            full_log_text: Complete log content (not used for TypeScript)
            error_type: The error type (not used for TypeScript)

        Returns:
            Tuple of (source_file_path, line_number) or (None, None) if not found
        """
        # Try to match TypeScript error format
        match = self.error_pattern.search(error_message)
        if match:
            file_path, line_str, col_str, level, error_code, message = match.groups()
            return self._clean_file_path(file_path), int(line_str)

        return None, None

    def _is_file_path(self, path: str) -> bool:
        """
        Check if a string looks like a file path.

        Args:
            path: String to check

        Returns:
            True if it looks like a file path
        """
        # TypeScript files typically end with .ts, .tsx, .d.ts
        return (
            path.endswith((".ts", ".tsx", ".d.ts"))
            and not path.startswith("http")
            and "/" in path
        )
