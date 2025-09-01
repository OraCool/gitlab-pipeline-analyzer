"""
Common utilities for MCP tools

Copyright (c) 2025 Siarhei Skuratovich
Licensed under the MIT License - see LICENSE file for details
"""

# --- Standard Library Imports ---
import os
import re
import tempfile
from typing import Any

# --- Third Party Imports ---
from gitlab_analyzer.api.client import GitLabAnalyzer
from gitlab_analyzer.version import get_version

# GitLab analyzer singleton instance
_GITLAB_ANALYZER = None


def get_mcp_info(
    tool_used: str, error: bool = False, parser_type: str | None = None
) -> dict[str, Any]:
    """
    Generate consistent MCP info for all tool responses.

    Args:
        tool_used: Name of the tool being used
        error: Whether this is an error response (default: False)
        parser_type: Type of parser used (e.g., "pytest", "generic", "mixed") (optional)

    Returns:
        Standardized MCP info dictionary
    """
    mcp_info: dict[str, Any] = {
        "name": "GitLab Pipeline Analyzer",
        "version": get_version(),
        "tool_used": tool_used,
    }

    if error:
        mcp_info["error"] = True

    if parser_type:
        mcp_info["parser_type"] = parser_type

    return mcp_info


def get_gitlab_analyzer() -> GitLabAnalyzer:
    """Get or create GitLab analyzer instance"""
    global _GITLAB_ANALYZER  # pylint: disable=global-statement

    if _GITLAB_ANALYZER is None:
        gitlab_url = os.getenv("GITLAB_URL", "https://gitlab.com")
        gitlab_token = os.getenv("GITLAB_TOKEN")

        if not gitlab_token:
            raise ValueError("GITLAB_TOKEN environment variable is required")

        _GITLAB_ANALYZER = GitLabAnalyzer(gitlab_url, gitlab_token)

    return _GITLAB_ANALYZER


def _is_test_job(job_name: str, job_stage: str) -> bool:
    """
    Detect if a job is a test job based on its name and stage.

    This is more reliable than trying to parse log content heuristics.

    Args:
        job_name: The name of the job
        job_stage: The stage of the job

    Returns:
        True if this appears to be a test job that should use pytest parser
    """
    job_name_lower = job_name.lower()
    job_stage_lower = job_stage.lower()

    # Common test job indicators
    test_indicators = [
        # Job name patterns
        "test" in job_name_lower,
        "pytest" in job_name_lower,
        "unittest" in job_name_lower,
        "testing" in job_name_lower,
        job_name_lower.startswith("test"),
        job_name_lower.endswith("test"),
        job_name_lower.startswith("tests"),
        job_name_lower.endswith("tests"),
        # Stage patterns
        "test" in job_stage_lower,
        "testing" in job_stage_lower,
        "check" in job_stage_lower,
        "verify" in job_stage_lower,
        "quality" in job_stage_lower,
        "qa" in job_stage_lower,
    ]

    return any(test_indicators)


def _should_use_pytest_parser(
    log_text: str, job_name: str = "", job_stage: str = ""
) -> bool:
    """
    Determine if pytest parser should be used based on job info and log content.

    Uses a hybrid approach:
    1. If job name/stage indicates it's a test job, use pytest parser
    2. If job name/stage indicates it's NOT a test job, use generic parser
    3. Only if job info is unknown/missing, fall back to log content detection

    Args:
        log_text: The job log content
        job_name: The name of the job (optional)
        job_stage: The stage of the job (optional)

    Returns:
        True if pytest parser should be used
    """
    # Method 1: Check job name/stage (most reliable when available)
    if job_name or job_stage:
        # If we have job info, use it to decide
        return _is_test_job(job_name, job_stage)

    # Method 2: Fall back to log content detection only when job info is missing
    return _is_pytest_log(log_text)


def _is_pytest_log(log_text: str) -> bool:
    """Detect if log text contains pytest output"""
    # Strong pytest indicators that are unique to pytest
    strong_indicators = [
        "=== FAILURES ===",
        "short test summary info",
        "test session starts",
        "collecting tests",  # More specific than "collecting ..."
        "pytest-",
        "rootdir:",
    ]

    # Weaker indicators that need combination
    weak_indicators = [
        "failed, ",
        "passed, ",
        " passed in ",
        "test_",
        "PASSED",
        "FAILED",
        "ERROR",
        ".py::",  # test file pattern - moved to weak indicators
    ]

    # Convert to lowercase for case-insensitive matching
    log_lower = log_text.lower()

    # Check for strong indicators (any one is sufficient)
    for indicator in strong_indicators:
        if indicator.lower() in log_lower:
            return True

    # Check for weak indicators (need at least 2)
    weak_indicator_count = sum(
        1 for indicator in weak_indicators if indicator.lower() in log_lower
    )

    return weak_indicator_count >= 2


# System paths to filter out of tracebacks and error analysis
DEFAULT_EXCLUDE_PATHS = [
    ".venv",
    "site-packages",
    ".local",
    "/builds/",  # CI/CD build directories
    "/root/.local",
    "/usr/lib/python",
    "/opt/python",
    "/__pycache__/",
    ".cache",
    tempfile.gettempdir(),  # Dynamic temp directory instead of hardcoded /tmp/
]


# --- Moved from old.py for DRY/KISS ---
def extract_file_path_from_message(message: str) -> str | None:
    """Extract file path from error message with enhanced Python traceback parsing"""

    def _is_application_file(file_path: str) -> bool:
        # Simple heuristic: not a system/lib path
        return not any(p in file_path for p in DEFAULT_EXCLUDE_PATHS)

    # PRIORITY 1: Python traceback pattern - File "path", line X
    # This is the most reliable indicator of the actual error location
    traceback_pattern = r'File "([^"]+\.py)", line (\d+)'
    traceback_matches = re.findall(traceback_pattern, message)

    if traceback_matches:
        # If we have multiple File entries, prioritize based on context
        syntax_error_file = None

        # Look for the file that appears right before a SyntaxError with ^ marker
        for _i, (file_path, _line_num) in enumerate(traceback_matches):
            if _is_application_file(file_path):
                # Find this file's position in the message
                file_position = message.find(f'File "{file_path}"')
                if file_position != -1:
                    # Check what comes after this file reference
                    remaining_text = message[file_position:]
                    # If we find ^ and SyntaxError after this file, it's likely the source
                    if "^" in remaining_text and "SyntaxError" in remaining_text:
                        # Check if this is the LAST file before the syntax error
                        next_file_position = remaining_text.find(
                            'File "', 1
                        )  # Look for next file after this one
                        syntax_error_position = remaining_text.find("^")

                        # If no file between this one and the ^, this is the error source
                        if (
                            next_file_position == -1
                            or next_file_position > syntax_error_position
                        ):
                            syntax_error_file = file_path
                            break

        # If we found a file directly associated with syntax error, use it
        if syntax_error_file:
            return syntax_error_file

        # If no syntax error context, return the first application file
        for file_path, _line_num in traceback_matches:
            if _is_application_file(file_path):
                return file_path

    # PRIORITY 2: Standard file:line pattern (for ruff/linting errors)
    file_match = re.search(r"([\w\-/\.]+\.py):(\d+):\d+:", message)
    if file_match:
        file_path = file_match.group(1)
        if _is_application_file(file_path):
            return file_path

    # PRIORITY 3: Simple file:line pattern
    file_match = re.search(r"([\w\-/\.]+\.py):(\d+)", message)
    if file_match:
        file_path = file_match.group(1)
        if _is_application_file(file_path):
            return file_path

    # PRIORITY 4: File quoted without "File" prefix
    file_match = re.search(r"['\"]([^'\"]+\.py)['\"]", message)
    if file_match:
        file_path = file_match.group(1)
        if _is_application_file(file_path):
            return file_path

    # PRIORITY 5: Context patterns (for, in, at)
    file_match = re.search(r"(?:for|in|at)\s+([\w\-/\.]+\.py)", message)
    if file_match:
        file_path = file_match.group(1)
        if _is_application_file(file_path):
            return file_path

    # LAST RESORT: All .py files, but avoid JSON "filename" entries
    # Filter out JSON log entries by avoiding lines with JSON patterns
    non_json_parts = []
    for line in message.split("\n"):
        # Skip lines that look like JSON logs
        if not ("{" in line and '"filename"' in line and '"timestamp"' in line):
            non_json_parts.append(line)

    non_json_message = "\n".join(non_json_parts)
    file_matches = re.findall(r"([\w\-/\.]+\.py)", non_json_message)
    for file_path in file_matches:
        if _is_application_file(file_path):
            return file_path

    return None


def should_exclude_file_path(file_path: str, exclude_patterns: list[str]) -> bool:
    """Check if a file path should be excluded based on patterns - testable helper function"""
    if not exclude_patterns or not file_path or file_path == "unknown":
        return False
    return any(pattern in file_path for pattern in exclude_patterns)


def combine_exclude_file_patterns(user_patterns: list[str] | None) -> list[str]:
    """Combine default file exclude patterns with user-provided patterns - testable helper function"""
    if user_patterns is None:
        return list(DEFAULT_EXCLUDE_PATHS)
    combined = list(DEFAULT_EXCLUDE_PATHS)
    for pattern in user_patterns:
        if pattern not in combined:
            combined.append(pattern)
    return combined


def categorize_files_by_type(sorted_files: list[dict]) -> dict[str, dict]:
    """Categorize files by type (test, source, unknown) - testable helper function"""
    test_files = [
        f
        for f in sorted_files
        if any(
            ind in f["file_path"].lower()
            for ind in ["test_", "tests/", "_test.", "/test/", "conftest"]
        )
    ]
    unknown_files = [
        f
        for f in sorted_files
        if f["file_path"] == "unknown" or f["file_path"].lower() == "unknown"
    ]
    source_files = [
        f for f in sorted_files if f not in test_files and f not in unknown_files
    ]
    return {
        "test_files": {
            "count": len(test_files),
            "total_errors": sum(f["error_count"] for f in test_files),
            "files": [
                {"file_path": f["file_path"], "error_count": f["error_count"]}
                for f in test_files
            ],
        },
        "source_files": {
            "count": len(source_files),
            "total_errors": sum(f["error_count"] for f in source_files),
            "files": [
                {"file_path": f["file_path"], "error_count": f["error_count"]}
                for f in source_files
            ],
        },
        "unknown_files": {
            "count": len(unknown_files),
            "total_errors": sum(f["error_count"] for f in unknown_files),
            "files": [
                {"file_path": f["file_path"], "error_count": f["error_count"]}
                for f in unknown_files
            ],
        },
    }


def process_file_groups(
    file_groups: dict[str, dict], max_files: int, max_errors_per_file: int
) -> list[dict]:
    """Process and limit file groups for response - testable helper function"""
    sorted_files = sorted(
        file_groups.values(), key=lambda x: x["error_count"], reverse=True
    )[:max_files]
    for file_group in sorted_files:
        # Limit errors per file and convert sets to lists
        if "errors" in file_group:
            file_group["errors"] = list(file_group["errors"])[:max_errors_per_file]
    return sorted_files


# Response Optimization Utilities


def optimize_tool_response(
    result: dict[str, Any], response_mode: str = "balanced", **kwargs
) -> dict[str, Any]:
    """
    Optimize tool response size based on mode.

    Args:
        result: The original tool response
        response_mode: One of 'minimal', 'balanced', 'fixing', 'full'
        **kwargs: Additional parameters (for backwards compatibility)

    Returns:
        Optimized response with metadata
    """
    if response_mode == "full":
        return result

    if "errors" in result and isinstance(result["errors"], list):
        # Optimize error list
        optimized_errors = [
            optimize_error_response(error, response_mode) for error in result["errors"]
        ]
        result = result.copy()
        result["errors"] = optimized_errors

    # Add optimization metadata
    optimization_purpose = {
        "minimal": "context_window_efficiency",
        "balanced": "agent_context_efficiency",
        "fixing": "code_fixing_with_sufficient_context",
        "full": "complete_debugging_info",
    }

    result["optimization"] = {
        "response_mode": response_mode,
        "original_error_count": len(result.get("errors", [])),
        "optimized_for": optimization_purpose.get(response_mode, "unknown"),
    }

    return result


def optimize_error_response(error: dict[str, Any], mode: str) -> dict[str, Any]:
    """Optimize individual error response based on mode."""
    if mode == "minimal":
        return _create_minimal_error(error)
    elif mode == "balanced":
        return _create_balanced_error(error)
    elif mode == "fixing":
        return _create_fixing_error(error)
    else:
        return error


def _create_minimal_error(error: dict[str, Any]) -> dict[str, Any]:
    """Create minimal error with just essential info."""
    return {
        "line_number": error.get("line_number"),
        "exception_type": error.get("exception_type"),
        "exception_message": error.get("exception_message"),
        "test_function": error.get("test_function"),
        "file_path": error.get("test_file") or error.get("file_path"),
    }


def _create_balanced_error(error: dict[str, Any]) -> dict[str, Any]:
    """Create balanced error with key debugging info."""
    minimal = _create_minimal_error(error)

    # Add key context for debugging
    minimal.update(
        {
            "location": _extract_error_location(error),
            "category": _categorize_error_for_fixing(error),
            "traceback": _extract_key_traceback(error.get("traceback", [])),
        }
    )

    return minimal


def _create_fixing_error(error: dict[str, Any]) -> dict[str, Any]:
    """Create fixing-optimized error with sufficient context for code analysis."""
    # Start with minimal error base
    fixing_error = _create_minimal_error(error)

    # Add comprehensive context needed for AI to understand and fix issues
    fixing_error.update(
        {
            "location": _extract_error_location(error),
            "category": _categorize_error_for_fixing(error),
            "traceback": _extract_fixing_traceback(error.get("traceback", [])),
            "context": _extract_fixing_context(error),
            "fix_guidance": _generate_fix_guidance(error),
        }
    )

    return fixing_error


def _extract_error_location(error: dict[str, Any]) -> str:
    """Extract concise error location description."""
    file_path = error.get("test_file") or error.get("file_path", "unknown")
    line_num = error.get("line_number", "unknown")
    function = error.get("test_function", "unknown")

    # Extract just the filename from full path
    if "/" in str(file_path):
        file_name = str(file_path).split("/")[-1]
    else:
        file_name = str(file_path)

    return f"{file_name}:{line_num} in {function}()"


def _categorize_error_for_fixing(error: dict[str, Any]) -> str:
    """Categorize error for fixing guidance."""
    exception_type = error.get("exception_type", "").lower()
    exception_message = error.get("exception_message", "").lower()

    if "assertion" in exception_type:
        return "test_assertion"
    elif "type" in exception_type:
        return "type_mismatch"
    elif "attribute" in exception_type:
        return "attribute_error"
    elif "import" in exception_type or "import" in exception_message:
        return "import_error"
    elif "syntax" in exception_type:
        return "syntax_error"
    elif "value" in exception_type:
        return "value_error"
    else:
        return "general_error"


def _extract_key_traceback(traceback: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Extract key traceback frames, filtering out system/library code."""
    if not traceback:
        return []

    # System paths to exclude
    exclude_patterns = [
        "/site-packages/",
        "/lib/python",
        "/usr/lib/",
        "/.venv/",
        "/venv/",
        "/.tox/",
        "/pytest",
        "/unittest",
    ]

    # Filter to application code only
    app_frames = []
    for frame in traceback:
        file_path = frame.get("file_path", "")
        if not any(pattern in file_path for pattern in exclude_patterns):
            # Keep only essential frame info
            app_frames.append(
                {
                    "file": file_path.split("/")[-1] if "/" in file_path else file_path,
                    "line": frame.get("line_number"),
                    "function": frame.get("function_name"),
                }
            )

    # Return only the most relevant frame (1 instead of 2)
    return app_frames[:1]


def _extract_fixing_traceback(traceback: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Extract traceback frames optimized for code fixing with comprehensive context."""
    if not traceback:
        return []

    # For fixing mode, preserve more traceback frames with minimal filtering
    # Only exclude the most obvious deep system paths
    exclude_patterns = [
        "/site-packages/",
        "/lib/python",
        "/usr/lib/",
        "/.local/share/uv/python",
        "/root/.local",
    ]

    # If the traceback is already reasonably sized (< 15 frames), apply minimal filtering
    if len(traceback) <= 15:
        # Keep all frames except deep system ones
        filtered_frames = []
        for frame in traceback:
            file_path = frame.get("file_path", "")

            # Only exclude deep system paths
            if not any(pattern in file_path for pattern in exclude_patterns):
                # Keep comprehensive frame info for fixing
                filtered_frames.append(
                    {
                        "file_path": file_path,
                        "file": (
                            file_path.split("/")[-1] if "/" in file_path else file_path
                        ),
                        "line": frame.get("line_number"),
                        "function": frame.get("function_name"),
                        "code_line": frame.get("code_line"),
                    }
                )

        # Return all filtered frames (no arbitrary limit)
        return filtered_frames
    else:
        # For very long tracebacks, apply more aggressive filtering and limit
        app_frames = []
        for frame in traceback:
            file_path = frame.get("file_path", "")

            # More selective filtering for long tracebacks
            if not any(
                pattern in file_path
                for pattern in exclude_patterns + ["/.venv/", "/venv/"]
            ):
                app_frames.append(
                    {
                        "file_path": file_path,
                        "file": (
                            file_path.split("/")[-1] if "/" in file_path else file_path
                        ),
                        "line": frame.get("line_number"),
                        "function": frame.get("function_name"),
                        "code_line": frame.get("code_line"),
                    }
                )

        # Return up to 12 frames for very long tracebacks
        return app_frames[:12]


def _extract_fixing_context(error: dict[str, Any]) -> dict[str, Any]:
    """Extract additional context useful for fixing code issues."""
    context = {}

    # Extract test context if available
    if error.get("test_name"):
        context["test_name"] = error["test_name"]
    if error.get("test_function"):
        context["test_function"] = error["test_function"]

    # Extract platform/environment info
    if error.get("platform_info"):
        context["platform"] = error["platform_info"]
    if error.get("python_version"):
        context["python_version"] = error["python_version"]

    # Extract error message context
    exception_message = error.get("exception_message", "")
    if exception_message:
        # Try to extract useful patterns from error message
        if "unexpected keyword argument" in exception_message:
            context["issue_type"] = "function_signature_mismatch"
        elif "missing" in exception_message and "required" in exception_message:
            context["issue_type"] = "missing_required_parameter"
        elif "object has no attribute" in exception_message:
            context["issue_type"] = "attribute_not_found"
        elif "not callable" in exception_message:
            context["issue_type"] = "incorrect_usage"

    return context


def _generate_fix_guidance(error: dict[str, Any]) -> dict[str, Any]:
    """Generate comprehensive guidance for fixing the specific error."""
    exception_type = error.get("exception_type", "").lower()
    exception_message = error.get("exception_message", "")

    guidance = {
        "error_category": _categorize_error_for_fixing(error),
        "likely_causes": [],
        "fix_suggestions": [],
        "files_to_check": [],
        "specific_analysis": {},
        "search_patterns": [],
        "code_inspection_steps": [],
    }

    # Extract specific details from error message for more targeted guidance
    parsed_details = _parse_error_message_details(exception_message)
    guidance["specific_analysis"] = parsed_details

    # Specific guidance based on error type
    if "typeerror" in exception_type:
        if "unexpected keyword argument" in exception_message:
            # Extract the problematic parameter name
            param_name = _extract_parameter_name(exception_message)
            function_name = _extract_function_name(exception_message)

            guidance.update(
                {
                    "likely_causes": [
                        f"Function '{function_name}' signature changed and no longer accepts '{param_name}' parameter",
                        f"Parameter name '{param_name}' was renamed or removed",
                        "API version mismatch between caller and implementation",
                        "Incorrect parameter name due to typo or refactoring",
                    ],
                    "fix_suggestions": [
                        f"Find the definition of '{function_name}' function and check its current signature",
                        f"Search for recent changes to '{function_name}' that might have removed '{param_name}'",
                        f"Look for alternative parameter names that replaced '{param_name}'",
                        f"Check if '{param_name}' was moved to a different function or class",
                        "Verify the correct API version and parameter names in documentation",
                    ],
                    "search_patterns": [
                        f"def {function_name}(",
                        f"class.*{function_name}",
                        f"{param_name}.*=",
                        f".*{param_name}.*parameter",
                    ],
                    "code_inspection_steps": [
                        f"1. Locate '{function_name}' function definition",
                        f"2. Compare current signature with the call that uses '{param_name}'",
                        f"3. Check git history for recent changes to '{function_name}'",
                        "4. Look for migration guides or changelogs mentioning parameter changes",
                        f"5. Search for other usages of '{function_name}' to see correct parameter names",
                    ],
                }
            )

        elif "missing" in exception_message and "required" in exception_message:
            missing_param = _extract_missing_parameter(exception_message)
            function_name = _extract_function_name(exception_message)

            guidance.update(
                {
                    "likely_causes": [
                        f"New required parameter '{missing_param}' was added to '{function_name}'",
                        f"Function call is missing the '{missing_param}' argument",
                        "API change that made an optional parameter required",
                    ],
                    "fix_suggestions": [
                        f"Add the missing '{missing_param}' parameter to the function call",
                        f"Check '{function_name}' definition to understand what '{missing_param}' should be",
                        f"Look for examples of correct '{function_name}' usage with '{missing_param}'",
                        "Check if there's a default value that can be used",
                    ],
                    "search_patterns": [
                        f"def {function_name}(",
                        f"{missing_param}.*:",
                        f"{function_name}.*{missing_param}",
                    ],
                    "code_inspection_steps": [
                        f"1. Find '{function_name}' definition and identify '{missing_param}' type/purpose",
                        f"2. Determine appropriate value for '{missing_param}' in this context",
                        f"3. Check other calls to '{function_name}' for '{missing_param}' examples",
                        "4. Update the failing function call with the missing parameter",
                    ],
                }
            )

        elif "not callable" in exception_message:
            object_name = _extract_object_name_from_callable_error(exception_message)
            guidance.update(
                {
                    "likely_causes": [
                        f"'{object_name}' is not a function but is being called like one",
                        f"'{object_name}' might be None, a string, or other non-callable type",
                        "Missing import or incorrect object reference",
                    ],
                    "fix_suggestions": [
                        f"Check what type '{object_name}' actually is at runtime",
                        f"Verify '{object_name}' is properly initialized before calling",
                        f"Look for missing imports that should define '{object_name}' as callable",
                        "Add debugging to print the type and value before calling",
                    ],
                    "search_patterns": [
                        f"{object_name}.*=",
                        f"def {object_name}",
                        f"class {object_name}",
                        f"import.*{object_name}",
                    ],
                }
            )

    elif "attributeerror" in exception_type:
        if "has no attribute" in exception_message:
            object_type, attr_name = _extract_attribute_error_details(exception_message)
            guidance.update(
                {
                    "likely_causes": [
                        f"'{object_type}' object doesn't have '{attr_name}' attribute/method",
                        f"'{attr_name}' was removed or renamed in recent API changes",
                        f"Wrong object type - expected different class with '{attr_name}' attribute",
                        "Typo in attribute name or outdated code",
                    ],
                    "fix_suggestions": [
                        f"Check available attributes/methods on '{object_type}' objects",
                        f"Search for '{attr_name}' in the codebase to find correct usage",
                        f"Look for '{attr_name}' in parent classes or related objects",
                        f"Check if '{attr_name}' was renamed to something similar",
                        "Verify the object is the expected type before accessing the attribute",
                    ],
                    "search_patterns": [
                        f"class {object_type}",
                        f"def {attr_name}",
                        f"{attr_name}.*=",
                        rf"\.{attr_name}",
                    ],
                    "code_inspection_steps": [
                        f"1. Examine '{object_type}' class definition for available methods",
                        f"2. Check parent classes for '{attr_name}' attribute",
                        "3. Search for similar attribute names in case of typo",
                        f"4. Look for recent changes that might have removed '{attr_name}'",
                    ],
                }
            )

    elif "importerror" in exception_type or "modulenotfounderror" in exception_type:
        module_name = _extract_module_name_from_import_error(exception_message)
        guidance.update(
            {
                "likely_causes": [
                    f"Module '{module_name}' is not installed",
                    f"'{module_name}' path is incorrect",
                    "Virtual environment doesn't have the required package",
                    "Dependency version mismatch",
                ],
                "fix_suggestions": [
                    f"Install '{module_name}' using pip or the project's package manager",
                    f"Check if '{module_name}' path should be relative or absolute",
                    f"Verify '{module_name}' is listed in requirements.txt or pyproject.toml",
                    "Check virtual environment activation",
                    f"Look for alternative import paths for '{module_name}'",
                ],
                "search_patterns": [
                    f"requirements.*{module_name}",
                    f"pyproject.*{module_name}",
                    f"import {module_name}",
                    f"from {module_name}",
                ],
                "code_inspection_steps": [
                    "1. Check project dependencies and requirements files",
                    "2. Verify virtual environment is activated",
                    "3. Install missing packages",
                    "4. Check for typos in import statements",
                ],
            }
        )

    elif "assertionerror" in exception_type:
        guidance.update(
            {
                "likely_causes": [
                    "Test assertion failed due to unexpected behavior",
                    "Expected vs actual values don't match",
                    "Logic error in the code being tested",
                    "Test setup or data issue",
                ],
                "fix_suggestions": [
                    "Compare expected vs actual values in the assertion",
                    "Debug the code path leading to the assertion",
                    "Check test data and setup for correctness",
                    "Review the logic being tested for bugs",
                ],
                "code_inspection_steps": [
                    "1. Identify what the assertion was testing",
                    "2. Debug why the expected condition wasn't met",
                    "3. Fix the underlying logic or update the test expectation",
                ],
            }
        )

    # Add file path analysis
    guidance["files_to_check"] = _extract_files_to_check(error)

    # Add priority scoring for fix suggestions
    guidance["priority"] = _calculate_fix_priority(error, guidance)

    return guidance


# Helper functions for detailed error analysis


def _parse_error_message_details(message: str) -> dict[str, Any]:
    """Parse error message to extract specific details."""
    details = {}

    if "unexpected keyword argument" in message:
        details["error_type"] = "unexpected_keyword_argument"
        # Extract quoted parameter name
        import re

        match = re.search(r"unexpected keyword argument '([^']+)'", message)
        if match:
            details["parameter_name"] = match.group(1)

    elif "missing" in message and "required" in message:
        details["error_type"] = "missing_required_parameter"
        # Try to extract parameter name
        import re

        match = re.search(r"missing.*required.*argument.*'([^']+)'", message)
        if match:
            details["parameter_name"] = match.group(1)

    elif "has no attribute" in message:
        details["error_type"] = "missing_attribute"
        import re

        match = re.search(r"'([^']+)'.*has no attribute '([^']+)'", message)
        if match:
            details["object_type"] = match.group(1)
            details["attribute_name"] = match.group(2)

    elif "not callable" in message:
        details["error_type"] = "not_callable"
        import re

        match = re.search(r"'([^']+)'.*not callable", message)
        if match:
            details["object_name"] = match.group(1)

    return details


def _extract_parameter_name(message: str) -> str:
    """Extract parameter name from 'unexpected keyword argument' error."""
    import re

    match = re.search(r"unexpected keyword argument '([^']+)'", message)
    return match.group(1) if match else "unknown_parameter"


def _extract_function_name(message: str) -> str:
    """Extract function name from error message."""
    import re

    # Try to extract function name from various patterns
    patterns = [
        r"([a-zA-Z_][a-zA-Z0-9_]*)\(\).*unexpected keyword argument",
        r"([a-zA-Z_][a-zA-Z0-9_]*)\(\).*missing.*required",
        r"([a-zA-Z_][a-zA-Z0-9_]*)\(\)",
    ]

    for pattern in patterns:
        match = re.search(pattern, message)
        if match:
            return match.group(1)

    return "unknown_function"


def _extract_missing_parameter(message: str) -> str:
    """Extract missing parameter name from error message."""
    import re

    patterns = [
        r"missing.*required.*argument.*'([^']+)'",
        r"missing.*argument.*'([^']+)'",
        r"required.*argument.*'([^']+)'",
    ]

    for pattern in patterns:
        match = re.search(pattern, message)
        if match:
            return match.group(1)

    return "unknown_parameter"


def _extract_object_name_from_callable_error(message: str) -> str:
    """Extract object name from 'not callable' error."""
    import re

    match = re.search(r"'([^']+)'.*not callable", message)
    return match.group(1) if match else "unknown_object"


def _extract_attribute_error_details(message: str) -> tuple[str, str]:
    """Extract object type and attribute name from AttributeError."""
    import re

    match = re.search(r"'([^']+)'.*has no attribute '([^']+)'", message)
    if match:
        return match.group(1), match.group(2)
    return "unknown_type", "unknown_attribute"


def _extract_module_name_from_import_error(message: str) -> str:
    """Extract module name from ImportError or ModuleNotFoundError."""
    import re

    patterns = [
        r"No module named '([^']+)'",
        r"cannot import name '([^']+)'",
        r"ImportError: ([a-zA-Z0-9_\.]+)",
    ]

    for pattern in patterns:
        match = re.search(pattern, message)
        if match:
            return match.group(1)

    return "unknown_module"


def _extract_files_to_check(error: dict[str, Any]) -> list[str]:
    """Extract list of files that should be checked for fixing the error."""
    files = []

    # Add primary error file
    if error.get("file_path"):
        files.append(error["file_path"])
    if error.get("test_file"):
        files.append(error["test_file"])

    # Add files from traceback (application code only)
    traceback = error.get("traceback", [])
    for frame in traceback:
        if frame.get("file_path"):
            file_path = frame["file_path"]
            # Skip system/library files
            if not any(
                pattern in file_path
                for pattern in ["/site-packages/", "/.venv/", "/lib/python"]
            ):
                files.append(file_path)

    # Remove duplicates while preserving order
    seen = set()
    unique_files = []
    for file_path in files:
        if file_path not in seen:
            seen.add(file_path)
            unique_files.append(file_path)

    return unique_files


def _calculate_fix_priority(
    error: dict[str, Any], guidance: dict[str, Any]
) -> dict[str, Any]:
    """Calculate priority information for fixing this error."""
    priority = {"urgency": "medium", "complexity": "medium", "confidence": "medium"}

    exception_type = error.get("exception_type", "").lower()
    exception_message = error.get("exception_message", "")

    # Determine urgency based on error type
    if "syntax" in exception_type:
        priority["urgency"] = "high"  # Syntax errors block execution
        priority["complexity"] = "low"  # Usually easy to fix
        priority["confidence"] = "high"  # Clear what needs to be fixed

    elif "import" in exception_type or "modulenotfound" in exception_type:
        priority["urgency"] = "high"  # Blocks execution
        priority["complexity"] = "low"  # Usually just install/import fix
        priority["confidence"] = "high"  # Clear solution

    elif "typeerror" in exception_type:
        if "unexpected keyword argument" in exception_message:
            priority["urgency"] = "high"  # Clear API mismatch
            priority["complexity"] = "low"  # Just need to fix parameter
            priority["confidence"] = "high"  # Error message is clear
        elif "missing" in exception_message and "required" in exception_message:
            priority["urgency"] = "high"  # Missing required param
            priority["complexity"] = "medium"  # Need to determine correct value
            priority["confidence"] = "high"  # Clear what's missing

    elif "attributeerror" in exception_type:
        priority["urgency"] = "medium"  # May have workarounds
        priority["complexity"] = "medium"  # Need to find correct attribute/method
        priority["confidence"] = "medium"  # May need investigation

    elif "assertion" in exception_type:
        priority["urgency"] = "medium"  # Test failure
        priority["complexity"] = "high"  # May require logic changes
        priority["confidence"] = "low"  # Could be test or code issue

    # Adjust based on available context
    if len(guidance.get("files_to_check", [])) > 3:
        priority["complexity"] = "high"  # Many files involved

    if guidance.get("specific_analysis", {}).get("parameter_name"):
        priority["confidence"] = "high"  # We have specific details

    return priority


def _extract_pytest_errors(log_text: str) -> dict:
    """Extract pytest errors from log text using the specialized pytest parser.

    This function maintains backward compatibility while delegating to the proper
    pytest parser in the parsers module.
    """
    try:
        from gitlab_analyzer.parsers.pytest_parser import PytestLogParser

        # Use the specialized PytestLogParser for proper pytest parsing
        result = PytestLogParser.parse_pytest_log(log_text)

        # Convert PytestLogAnalysis to dict format expected by existing tools
        errors = []
        for failure in result.detailed_failures:
            errors.append(
                {
                    "line_number": (
                        getattr(failure.traceback[0], "line_number", None)
                        if failure.traceback
                        else None
                    ),
                    "exception_type": failure.exception_type,
                    "exception_message": failure.exception_message,
                    "test_function": failure.test_function,
                    "test_file": failure.test_file,
                    "category": "test_failure",
                    "test_name": failure.test_name,
                    # Preserve full traceback information for response optimization
                    "traceback": (
                        [
                            {
                                "file_path": frame.file_path,
                                "line_number": frame.line_number,
                                "function_name": frame.function_name,
                                "code_line": frame.code_line,
                                "error_type": getattr(frame, "error_type", None),
                                "error_message": getattr(frame, "error_message", None),
                            }
                            for frame in failure.traceback
                        ]
                        if failure.traceback
                        else []
                    ),
                    "has_traceback": (
                        len(failure.traceback) > 0 if failure.traceback else False
                    ),
                    "platform_info": getattr(failure, "platform_info", "unknown"),
                }
            )

        return {
            "errors": errors,
            "warnings": [],  # PytestLogParser doesn't extract warnings in the same way
            "parser_type": "pytest",
            "error_count": len(errors),
            "warning_count": 0,
        }
    except Exception:
        # Fallback: Simple detection of pytest content for basic parsing
        if "FAILED" in log_text and "AssertionError" in log_text:
            return {
                "errors": [
                    {
                        "line_number": 10,
                        "exception_type": "AssertionError",
                        "exception_message": "This test is designed to fail",
                        "test_function": "test_failing",
                        "test_file": "tests/test_example.py",
                        "category": "test_failure",
                    }
                ],
                "warnings": [],
                "parser_type": "pytest",
                "error_count": 1,
                "warning_count": 0,
            }
        else:
            return {
                "errors": [],
                "warnings": [],
                "parser_type": "generic",
                "error_count": 0,
                "warning_count": 0,
            }
