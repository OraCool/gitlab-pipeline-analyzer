"""
Framework-agnostic parser registry for scalable CI/CD log analysis.

This module provides a registry system that can automatically detect and parse
different test frameworks and CI/CD tools including pytest, Jest, SonarQube, etc.

Following SOLID principles with proper separation of concerns.
"""

from typing import Any

from .base_parser import BaseFrameworkDetector, BaseFrameworkParser, TestFramework


class ParserRegistry:
    """Registry for framework detectors and parsers"""

    def __init__(self):
        self._detectors: list[BaseFrameworkDetector] = []
        self._parsers: dict[TestFramework, type] = {}

    def register_detector(self, detector: BaseFrameworkDetector):
        """Register a framework detector"""
        self._detectors.append(detector)
        # Sort by priority (highest first)
        self._detectors.sort(key=lambda d: d.priority, reverse=True)

    def register_parser(self, framework: TestFramework, parser_class: type):
        """Register a parser for a framework"""
        self._parsers[framework] = parser_class

    def detect_framework(
        self, job_name: str, job_stage: str, trace_content: str
    ) -> TestFramework:
        """Detect the test framework for a job"""
        for detector in self._detectors:
            if detector.detect(job_name, job_stage, trace_content):
                return detector.framework

        return TestFramework.GENERIC

    def get_parser(self, framework: TestFramework) -> BaseFrameworkParser | None:
        """Get parser instance for framework"""
        parser_class = self._parsers.get(framework)
        if parser_class:
            return parser_class()
        return None

    def list_frameworks(self) -> list[TestFramework]:
        """List all registered frameworks"""
        return [detector.framework for detector in self._detectors]


# Global registry instance
parser_registry = ParserRegistry()

# Import and register all parsers
try:
    from .sonarqube_parser import SonarQubeDetector, SonarQubeParser

    parser_registry.register_detector(SonarQubeDetector())  # 95 - highest priority
    parser_registry.register_parser(TestFramework.SONARQUBE, SonarQubeParser)
except ImportError:
    pass  # Graceful degradation

try:
    from .pytest_parser import PytestDetector, PytestParser

    parser_registry.register_detector(PytestDetector())  # 90 - high priority
    parser_registry.register_parser(TestFramework.PYTEST, PytestParser)
except ImportError:
    pass  # Graceful degradation

try:
    from .jest_parser import JestDetector, JestParser

    parser_registry.register_detector(JestDetector())  # 85 - high priority
    parser_registry.register_parser(TestFramework.JEST, JestParser)
except ImportError:
    pass  # Graceful degradation

try:
    from .log_parser import GenericLogDetector, GenericLogParser

    parser_registry.register_detector(
        GenericLogDetector()
    )  # 1 - lowest priority (fallback)
    parser_registry.register_parser(TestFramework.GENERIC, GenericLogParser)
except ImportError:
    pass  # Graceful degradation


def detect_job_framework(
    job_name: str, job_stage: str, trace_content: str
) -> TestFramework:
    """
    Detect the framework for a CI/CD job.

    Args:
        job_name: Name of the CI/CD job
        job_stage: Stage of the CI/CD job
        trace_content: Raw log content from the job

    Returns:
        Detected TestFramework enum
    """
    return parser_registry.detect_framework(job_name, job_stage, trace_content)


def parse_with_framework(
    trace_content: str, framework: TestFramework, **kwargs
) -> dict[str, Any]:
    """
    Parse logs using framework-specific parser.

    Args:
        trace_content: Raw log content
        framework: Detected test framework
        **kwargs: Parser-specific options

    Returns:
        Standardized parsing results
    """
    parser = parser_registry.get_parser(framework)

    if parser:
        return parser.parse_with_validation(trace_content, **kwargs)

    # This should never happen since GenericLogParser handles all cases
    # But kept for ultimate safety
    return {
        "parser_type": "fallback",
        "framework": framework.value,
        "errors": [],
        "error_count": 0,
        "warnings": [],
        "warning_count": 0,
        "summary": {},
    }
