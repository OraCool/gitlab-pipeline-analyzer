"""
Base parser utilities and abstract interfaces for log analysis.

This module defines the common interface that all framework-specific parsers must implement,
following SOLID principles for consistent and extensible parser architecture.

Copyright (c) 2025 Siarhei Skuratovich
Licensed under the MIT License - see LICENSE file for details
"""

import re
from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Protocol


class TestFramework(Enum):
    """Supported test frameworks and CI/CD tools"""

    PYTEST = "pytest"
    JEST = "jest"
    MOCHA = "mocha"
    JUNIT = "junit"
    VITEST = "vitest"
    SONARQUBE = "sonarqube"
    ESLINT = "eslint"
    TYPESCRIPT = "typescript"
    GENERIC = "generic"


class FrameworkDetector(Protocol):
    """Protocol for framework detection - Interface Segregation Principle"""

    def detect(self, job_name: str, job_stage: str, trace_content: str) -> bool:
        """Detect if trace content matches this framework"""
        ...

    @property
    def framework(self) -> TestFramework:
        """Return the framework this detector identifies"""
        ...

    @property
    def priority(self) -> int:
        """Detection priority (higher = checked first)"""
        ...


class BaseFrameworkParser(ABC):
    """
    Abstract base class for all framework-specific parsers.

    This class defines the common interface that all parsers must implement,
    following the Template Method pattern and Interface Segregation Principle.
    """

    @property
    @abstractmethod
    def framework(self) -> TestFramework:
        """Return the framework this parser handles"""
        pass

    @abstractmethod
    def parse(self, trace_content: str, **kwargs) -> dict[str, Any]:
        """
        Parse trace content and return standardized results.

        Args:
            trace_content: Raw log content from CI/CD job
            **kwargs: Parser-specific options (include_traceback, exclude_paths, etc.)

        Returns:
            Standardized parsing results with consistent structure:
            {
                "parser_type": str,
                "framework": str,
                "errors": List[Dict[str, Any]],
                "error_count": int,
                "warnings": List[Dict[str, Any]],
                "warning_count": int,
                "summary": Dict[str, Any]  # Framework-specific summary
            }
        """
        pass

    @abstractmethod
    def _extract_source_file_and_line(
        self, error_message: str, full_log_text: str = "", error_type: str = ""
    ) -> tuple[str | None, int | None]:
        """
        Extract source file path and line number from error messages.

        This method should be implemented by each parser to handle framework-specific
        error message formats and traceback structures.

        Args:
            error_message: The error message text from the test output
            full_log_text: Complete log content for searching traceback information
            error_type: The error type (e.g., "AttributeError", "TypeError") if already extracted

        Returns:
            Tuple of (source_file_path, line_number) or (None, None) if not found

        Examples:
            For pytest: Extract from "domains/gwpy-document/services.py:1101: AttributeError"
            For jest: Extract from "at Object.<anonymous> (/path/to/file.js:42:5)"
            For generic: Extract line numbers from stack traces or error messages
        """
        pass

    def validate_output(self, result: dict[str, Any]) -> dict[str, Any]:
        """
        Validate and normalize parser output to ensure consistency.

        This method enforces the common output structure across all parsers.
        """
        # Ensure required fields exist
        result.setdefault("parser_type", self.framework.value)
        result.setdefault("framework", self.framework.value)
        result.setdefault("errors", [])
        result.setdefault("error_count", len(result["errors"]))
        result.setdefault("warnings", [])
        result.setdefault("warning_count", len(result["warnings"]))
        result.setdefault("summary", {})

        # Validate error structure
        for error in result["errors"]:
            error.setdefault("test_file", "unknown")
            error.setdefault("test_function", "unknown")
            error.setdefault("exception_type", "Unknown Error")
            error.setdefault("message", "No message")
            error.setdefault("line_number", 0)
            error.setdefault("has_traceback", False)

        # Validate warning structure
        for warning in result["warnings"]:
            warning.setdefault("message", "No message")
            warning.setdefault("line_number", 0)
            warning.setdefault("type", "unknown_warning")

        return result

    def parse_with_validation(self, trace_content: str, **kwargs) -> dict[str, Any]:
        """
        Parse content and validate output structure.

        This template method ensures all parsers produce consistent output.
        """
        result = self.parse(trace_content, **kwargs)
        return self.validate_output(result)


class BaseFrameworkDetector(ABC):
    """
    Abstract base class for framework detectors.

    Provides common detection patterns and follows Single Responsibility Principle.
    """

    @property
    @abstractmethod
    def framework(self) -> TestFramework:
        """Return the framework this detector identifies"""
        pass

    @property
    @abstractmethod
    def priority(self) -> int:
        """Detection priority (higher = checked first)"""
        pass

    @abstractmethod
    def detect(self, job_name: str, job_stage: str, trace_content: str) -> bool:
        """Detect if trace content matches this framework"""
        pass

    def _check_job_name_patterns(self, job_name: str, patterns: list[str]) -> bool:
        """Common utility for job name pattern matching"""
        return any(re.search(pattern, job_name.lower()) for pattern in patterns)

    def _check_trace_content_patterns(
        self, trace_content: str, patterns: list[str]
    ) -> bool:
        """Common utility for trace content pattern matching"""
        return any(
            re.search(pattern, trace_content, re.IGNORECASE) for pattern in patterns
        )

    def _exclude_by_patterns(self, content: str, exclude_patterns: list[str]) -> bool:
        """Common utility for exclusion pattern matching"""
        return any(
            re.search(pattern, content, re.IGNORECASE) for pattern in exclude_patterns
        )


class BaseParser:
    """Base parser with common utilities for log analysis"""

    # Focused CI/CD infrastructure exclusions - only exclude clear infrastructure noise
    EXCLUDE_PATTERNS = [
        # GitLab Runner infrastructure (keep these as they're clearly not job failures)
        r"Running with gitlab-runner",
        r"on GCP Ocean",
        r"system ID:",
        r"shared k8s runner",
        r"please use cache",
        r"per job and.*per service",
        # Kubernetes/Docker infrastructure setup (not failures)
        r"the \"kubernetes\" executor",
        r"Using Kubernetes",
        r"Using attach strategy",
        r"Pod activeDeadlineSeconds",
        r"Waiting for pod",
        r"Running on runner-",
        r"gitlab-managed-apps",
        r"via gitlab-runner",
        # Kubernetes policy warnings (infrastructure, not code issues)
        r"WARNING.*Event retrieved from the cluster.*policy.*require-labels",
        r"WARNING.*policy require-labels.*fail.*validation error",
        r"WARNING.*labels.*\w+\.\w+.*are required",
        r".*rule require-labels failed at path",
        r"WARNING.*Event retrieved from the cluster.*policy.*",
        # Git operations (infrastructure, not code issues)
        r"Getting source from Git",
        r"source from Git repository",
        r"Fetching changes with git",
        r"Initialized empty Git repository",
        r"Skipping Git submodules",
        # Cache operations (successful)
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
        # GitLab CI internal scripts (infrastructure, not user code issues)
        r"/scripts-.*/get_sources:",
        # Package installation (successful operations only)
        r"Requirement already satisfied:",
        r"Collecting ",
        r"Installing collected packages:",
        r"Successfully installed",
        r"Downloading.*packages",
        r"Installing.*packages",
        # Success messages (not errors)
        r"Successfully",
        r"✅",
        r"🔍",
        # GitLab CI section markers and formatting
        r"section_start:",
        r"section_end:",
        # Generic GitLab CI completion messages (not specific errors)
        r"Cleaning up project directory and file based variables",
        r"upload project directory and file based variables",
    ]

    # Shared error type classification patterns
    ERROR_TYPE_PATTERNS = [
        # Test failures
        (r"FAILED.*test.*", "test_failure"),
        (r".*AssertionError.*", "test_failure"),
        (r".*Test failed.*", "test_failure"),
        (r".*assert.*", "test_failure"),
        # Python syntax/runtime errors
        (r"SyntaxError.*", "python_error"),
        (r"ImportError.*", "python_error"),
        (r"ModuleNotFoundError.*", "python_error"),
        (r"IndentationError.*", "python_error"),
        (r"NameError.*", "python_error"),
        (r"TypeError.*", "python_error"),
        (r"ValueError.*", "python_error"),
        (r"KeyError.*", "python_error"),
        (r"AttributeError.*", "python_error"),
        # Linting errors
        (r".*ruff.*", "linting_error"),
        (r".*\.py:\d+:\d+:.*[A-Z]\d+.*", "linting_error"),  # Ruff format
        (r".*would reformat.*", "linting_error"),
        (r".*formatting.*issues.*", "linting_error"),
        (r"No matches for ignored import.*", "import_linting_error"),
        (r".*import.*not allowed.*", "import_linting_error"),
        # Note: Removed "Found \d+ error" pattern to avoid duplicate error extraction
        # The summary line should not be treated as a separate error
        # Build system errors - exclude linting and test-related make failures
        (
            r"make: \*\*\* \[(?!.*(?:lint|test|check|format))(.+)\] Error (\d+)",
            "build_error",
        ),  # make command failures (but not for linting/testing)
        (r".*build failed.*", "build_error"),
        (r".*compilation error.*", "build_error"),
        # Docker/infrastructure errors
        (r"Error response from daemon.*", "infrastructure_error"),
        (r"Failed to pull image.*", "infrastructure_error"),
        (r".*Permission denied.*", "infrastructure_error"),
        # Policy/security warnings (but exclude Kubernetes policy validation warnings)
        (
            r"WARNING.*policy.*require-labels.*",
            "infrastructure_warning",
        ),  # Kubernetes policy - not a code issue
        (
            r"WARNING.*Event retrieved from the cluster.*policy.*",
            "infrastructure_warning",
        ),  # Kubernetes policy - not a code issue
        (r"WARNING.*policy.*", "policy_warning"),  # General policy warnings
        (r".*security issue.*", "security_error"),
        (r".*vulnerability.*", "security_error"),
        # Generic patterns (lower priority)
        (r"ERROR:.*", "generic_error"),
        (r"CRITICAL:.*", "critical_error"),
    ]

    @classmethod
    def classify_error_type(cls, message: str) -> str:
        """Classify error type based on message pattern"""
        for pattern, error_type in cls.ERROR_TYPE_PATTERNS:
            if re.search(pattern, message, re.IGNORECASE):
                return error_type
        return "unknown"

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
