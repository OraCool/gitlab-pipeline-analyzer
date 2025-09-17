"""
SonarQube-specific log parser for CI/CD analysis.

This parser handles SonarQube static analysis output, quality gate failures,
coverage issues, and Node.js runtime errors.

Copyright (c) 2025 Siarhei Skuratovich
Licensed under the MIT License - see LICENSE file for details
"""

import re
from typing import Any

from .base_parser import BaseFrameworkDetector, BaseFrameworkParser, TestFramework


class SonarQubeDetector(BaseFrameworkDetector):
    """Detects SonarQube analysis jobs"""

    @property
    def framework(self) -> TestFramework:
        return TestFramework.SONARQUBE

    @property
    def priority(self) -> int:
        return 95  # Highest priority - very specific patterns

    def detect(self, job_name: str, job_stage: str, trace_content: str) -> bool:
        """Detect SonarQube jobs"""
        # Job name patterns
        sonar_job_patterns = [
            r"sonar",
            r"quality.*gate",
            r"code.*quality",
            r"static.*analysis",
            r"coverage.*report",
        ]

        if self._check_job_name_patterns(job_name, sonar_job_patterns):
            return True

        # Trace content patterns - very specific to SonarQube
        sonar_trace_patterns = [
            r"SonarScanner.*execution",
            r"QUALITY GATE STATUS:",
            r"sonar\..*\.reportPath",
            r"Sensor.*\[python\]",
            r"sonarqube-ce\.infra\.pandadoc\.com",
            r"org\.sonar\.plugins\.",
        ]

        return self._check_trace_content_patterns(trace_content, sonar_trace_patterns)


class SonarQubeParser(BaseFrameworkParser):
    """SonarQube-specific log parser"""

    @property
    def framework(self) -> TestFramework:
        return TestFramework.SONARQUBE

    def parse(self, trace_content: str, **kwargs) -> dict[str, Any]:
        """Parse SonarQube analysis output"""
        errors = []
        warnings = []

        # Terminal failure patterns - only real errors that cause job failure
        terminal_error_patterns = [
            # Quality gate failures - these are actual failures
            (
                r"ERROR:.*QUALITY GATE STATUS: FAILED.*dashboard\?id=([^&]+)",
                "Quality Gate Failure",
            ),
            # Authentication/permission failures
            (r"ERROR:.*Unauthorized", "Authentication Failure"),
            (r"ERROR:.*Permission denied", "Permission Failure"),
            # Configuration errors that prevent execution
            (r"ERROR:.*sonar-project.properties.*not found", "Configuration Error"),
        ]

        # Processing messages to ignore (between INFO lines, part of normal workflow)
        processing_patterns_to_ignore = [
            r"ERROR: Cannot resolve the file path.*coverage report.*ambiguity",  # Coverage path resolution attempts
            r"ERROR: Cannot find.*coverage.xml",  # Coverage file discovery attempts
            r"ERROR: Parsing.*failed",  # Individual file parsing attempts
            r"ERROR: Error relocating.*node:.*symbol not found",  # Node.js runtime processing attempts
            r"ERROR: Error during SonarScanner execution",  # Generic execution failure message (meaningless)
            r"WARNING:.*No report was found",  # Report discovery attempts
            r"WARNING:.*Embedded Node\.js failed",  # Internal Node.js attempts
        ]

        lines = trace_content.split("\n")

        for i, line in enumerate(lines):
            # Skip processing messages that are part of normal SonarQube workflow
            if self._is_processing_message(
                line, lines, i, processing_patterns_to_ignore
            ):
                continue

            # Only capture terminal errors that actually cause job failure
            for pattern, error_type in terminal_error_patterns:
                match = re.search(pattern, line)
                if match:
                    errors.append(
                        {
                            "test_file": self._extract_file_path(line, match),
                            "test_function": "SonarQube Analysis",
                            "exception_type": error_type,
                            "message": line.strip(),
                            "line_number": i + 1,
                            "has_traceback": self._has_sonar_context(lines, i),
                            "sonar_details": self._extract_sonar_details(line, match),
                        }
                    )

        # Extract meaningful warnings (not processing noise)
        sonar_warning_patterns = [
            r"WARN:.*Quality gate.*threshold",  # Quality threshold warnings
            r"WARN:.*Coverage.*below minimum",  # Coverage warnings
            r"INFO:.*time=\d+ms",  # Performance warnings (keep for slow analysis detection)
        ]

        for i, line in enumerate(lines):
            for pattern in sonar_warning_patterns:
                if re.search(pattern, line):
                    warnings.append(
                        {
                            "message": line.strip(),
                            "line_number": i + 1,
                            "type": "sonar_warning",
                        }
                    )

        return self.validate_output(
            {
                "parser_type": "sonarqube",
                "framework": self.framework.value,
                "errors": errors,
                "error_count": len(errors),
                "warnings": warnings,
                "warning_count": len(warnings),
                "summary": self._extract_sonar_summary(trace_content),
            }
        )

    def _is_processing_message(
        self,
        line: str,
        lines: list[str],
        current_index: int,
        ignore_patterns: list[str],
    ) -> bool:
        """
        Determine if an ERROR message is just a processing message (workflow noise) rather than a terminal failure.

        SonarQube often shows ERROR messages during normal processing that aren't actual failures.
        These typically occur between INFO lines as part of the analysis workflow.
        """
        # Check if the line matches any of the processing patterns we want to ignore
        for pattern in ignore_patterns:
            if re.search(pattern, line):
                # Additional context check: is this surrounded by INFO lines?
                # This indicates it's part of normal processing workflow
                return self._is_between_info_lines(lines, current_index)

        return False

    def _is_between_info_lines(self, lines: list[str], current_index: int) -> bool:
        """
        Check if the current line is between INFO lines, indicating it's part of processing workflow.

        Example:
        INFO: Parsing report '/builds/product/gwpy-core/coverage.xml'
        ERROR: Cannot resolve the file path '__init__.py' of the coverage report, ambiguity...
        INFO: Sensor Cobertura Sensor for Python coverage [python] (done) | time=957ms

        The ERROR above is processing noise, not a terminal failure.
        """
        # Look for INFO lines before and after (within reasonable range)
        before_range = max(0, current_index - 5)
        after_range = min(len(lines), current_index + 5)

        has_info_before = any(
            line.strip().startswith("INFO:")
            for line in lines[before_range:current_index]
        )

        has_info_after = any(
            line.strip().startswith("INFO:")
            for line in lines[current_index + 1 : after_range]
        )

        return has_info_before and has_info_after

    def _extract_file_path(self, line: str, match: re.Match) -> str:
        """Extract file path from SonarQube error"""
        if match.groups():
            return match.group(1)
        return "unknown"

    def _has_sonar_context(self, lines: list[str], current_line: int) -> bool:
        """Check if error has additional context"""
        # Look for INFO/ERROR context around the line
        for i in range(max(0, current_line - 3), min(len(lines), current_line + 3)):
            if "INFO:" in lines[i] or "ERROR:" in lines[i]:
                return True
        return False

    def _extract_sonar_details(self, line: str, match: re.Match) -> dict[str, Any]:
        """Extract SonarQube-specific details"""
        details = {}

        # Extract project ID from quality gate URLs
        if "dashboard?id=" in line:
            project_match = re.search(r"id=([^&]+)", line)
            if project_match:
                details["sonar_project_id"] = project_match.group(1)

        # Extract pull request ID
        if "pullRequest=" in line:
            pr_match = re.search(r"pullRequest=(\d+)", line)
            if pr_match:
                details["pull_request_id"] = pr_match.group(1)

        return details

    def _extract_sonar_summary(self, trace_content: str) -> dict[str, Any]:
        """Extract SonarQube analysis summary"""
        summary = {
            "total_time": None,
            "memory_usage": None,
            "status": "unknown",
            "quality_gate": "unknown",
        }

        # Extract execution time
        time_match = re.search(r"Total time: ([0-9.]+s)", trace_content)
        if time_match:
            summary["total_time"] = time_match.group(1)

        # Extract memory usage
        memory_match = re.search(r"Final Memory: ([0-9M/]+)", trace_content)
        if memory_match:
            summary["memory_usage"] = memory_match.group(1)

        # Extract quality gate status
        if "QUALITY GATE STATUS: FAILED" in trace_content:
            summary["quality_gate"] = "failed"
        elif "QUALITY GATE STATUS: PASSED" in trace_content:
            summary["quality_gate"] = "passed"

        # Overall status
        if "Error during SonarScanner execution" in trace_content:
            summary["status"] = "failed"
        elif "EXECUTION SUCCESS" in trace_content:
            summary["status"] = "success"

        return summary

    def _extract_source_file_and_line(
        self, error_message: str, full_log_text: str = "", error_type: str = ""
    ) -> tuple[str | None, int | None]:
        """
        SonarQube-specific implementation of source file and line number extraction.

        SonarQube typically provides issues in the format:
        "src/main/java/com/example/Class.java:42: Error message"
        or references files in quality gate failures.
        """
        # SonarQube file reference patterns
        patterns = [
            # Standard SonarQube issue format: "path/to/file.ext:line: message"
            r"([^\s:]+\.(java|js|ts|py|php|cpp|c|cs)):(\d+):\s*",
            # Quality gate file references: "src/main/java/Class.java"
            r"([^\s:]+\.(java|js|ts|py|php|cpp|c|cs))(?:\s|$)",
            # Generic file path in error messages
            r"file\s+'([^']+)'",
            r"File\s+\"([^\"]+)\"",
        ]

        # First try to extract from error message
        for pattern in patterns:
            match = re.search(pattern, error_message)
            if match:
                groups = match.groups()
                file_path = groups[0]
                line_number = groups[2] if len(groups) > 2 else None

                # Skip system paths and focus on source code
                if not any(
                    skip in file_path for skip in ["/usr/", "/opt/", "/.sonar/"]
                ):
                    try:
                        return file_path.strip(), (
                            int(line_number) if line_number else None
                        )
                    except (ValueError, TypeError):
                        return file_path.strip(), None

        # If not found in error message, search the full log text
        if full_log_text:
            for pattern in patterns:
                matches = re.findall(pattern, full_log_text)
                for match in matches:
                    file_path = match[0] if isinstance(match, tuple) else match
                    line_number = (
                        match[2]
                        if isinstance(match, tuple) and len(match) > 2
                        else None
                    )

                    # Skip system paths
                    if not any(
                        skip in file_path for skip in ["/usr/", "/opt/", "/.sonar/"]
                    ):
                        try:
                            return file_path.strip(), (
                                int(line_number) if line_number else None
                            )
                        except (ValueError, TypeError):
                            return file_path.strip(), None

        return None, None
