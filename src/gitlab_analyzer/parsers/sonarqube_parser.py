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

        # SonarQube error patterns
        sonar_error_patterns = [
            # Quality gate failures
            (
                r"QUALITY GATE STATUS: FAILED.*dashboard\?id=([^&]+)",
                "Quality Gate Failure",
            ),
            # Coverage report issues
            (
                r"Cannot resolve the file path '([^']+)'.*ambiguity",
                "Coverage Resolution Error",
            ),
            # Node.js runtime errors
            (r"Error relocating.*node:.*symbol not found", "Node.js Runtime Error"),
            # General SonarScanner errors
            (r"Error during SonarScanner execution", "SonarScanner Execution Error"),
            # Sensor failures
            (r"Sensor.*failed", "Sensor Failure"),
        ]

        lines = trace_content.split("\n")
        for i, line in enumerate(lines):
            for pattern, error_type in sonar_error_patterns:
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

        # Extract SonarQube-specific warnings
        sonar_warning_patterns = [
            r"WARN:.*No report was found",
            r"WARN:.*Embedded Node\.js failed",
            r"INFO:.*time=\d+ms",  # Performance warnings
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
